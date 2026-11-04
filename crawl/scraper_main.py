import csv
import os
import re
import time
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from parsel import Selector
from db_cleaner import (
    init_db, clean_price, extract_specs, detect_brand,
    clean_product_name, clean_rating_reviews
)

# ==============================================================================
# CẤU HÌNH SỐ LƯỢNG QUÉT
# - Để test nhanh cả 3 sàn trong 3-4 phút: Đặt MAX_PRODUCTS_PER_SITE = 10, MAX_LOAD_MORE_CLICKS = 2
# - Để lấy > 1.000 bản ghi thực tế nộp bài: Đặt MAX_PRODUCTS_PER_SITE = 65, MAX_LOAD_MORE_CLICKS = 10
# ==============================================================================
MAX_PRODUCTS_PER_SITE = 50
MAX_LOAD_MORE_CLICKS = 5

def get_driver():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def click_load_more(driver, xpath_btn, max_clicks=4):
    for i in range(max_clicks):
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.75);")
            time.sleep(1.5)
            btns = driver.find_elements(By.XPATH, xpath_btn)
            visible_btn = next((b for b in btns if b.is_displayed()), None)
            if visible_btn:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", visible_btn)
                time.sleep(0.8)
                driver.execute_script("arguments[0].click();", visible_btn)
                print(f"   -> Đã bấm 'Xem thêm' danh sách lần {i+1}/{max_clicks}...")
                time.sleep(2.2)
            else:
                break
        except Exception:
            break

# ==============================================================================
# 1. THẾ GIỚI DI ĐỘNG (Chuẩn DOM: grid-cols-5, a[data-disable-progress='true'])
# ==============================================================================
def crawl_tgdd(driver):
    base_url = "https://www.thegioididong.com"
    list_url = "https://www.thegioididong.com/dtdd"
    print(f"\n[TGDD] 1. Đang lấy danh sách link sản phẩm gốc từ: {list_url}")
    driver.get(list_url)
    time.sleep(3.5)

    driver.execute_script("window.scrollTo(0, 700);")
    time.sleep(1.5)

    tgdd_load_more_xpath = (
        "//div[contains(@class, 'view-more')]//a | "
        "//a[contains(text(), 'Xem thêm')] | "
        "//button[contains(., 'Xem thêm')] | "
        "//div[contains(text(), 'Xem thêm') and contains(@class, 'cursor-pointer')]"
    )
    click_load_more(driver, tgdd_load_more_xpath, max_clicks=MAX_LOAD_MORE_CLICKS)

    # Lấy CHÍNH XÁC link các card sản phẩm trong lưới grid-cols-5 (theo đúng file Phân tích DOM)
    # Mỗi card sản phẩm đều có thẻ <img> với thuộc tính alt là tên máy, loại bỏ hoàn toàn logo hãng
    raw_links = driver.execute_script("""
        let hrefs = [];
        let links = document.querySelectorAll('div[class*="grid-cols"] a[href^="/dtdd/"], ul.listproduct li.item a[href^="/dtdd/"]');
        if (links.length === 0) {
            links = document.querySelectorAll('main a[href^="/dtdd/"]');
        }
        links.forEach(a => {
            let h = a.getAttribute('href');
            let img = a.querySelector('img[alt]');
            // Card sản phẩm thật luôn có ảnh sản phẩm kích thước lớn hoặc nằm trong khối card
            if (h && img && img.getAttribute('alt').trim().length > 4) {
                hrefs.push(h);
            }
        });
        return hrefs;
    """)

    product_base_links = []
    ignore_slugs = {
        "apple-iphone", "samsung", "oppo", "xiaomi", "vivo", "realme", "honor",
        "tcl", "tecno", "nokia", "masstel", "mobell", "itel", "viettel", "benco", "nubia", "motorola"
    }
    ignore_keywords = [
        "tra-gop", "khuyen-mai", "so-sanh", "tin-tuc", "hoi-dap",
        "may-doi-tra", "dong-ho", "phu-kien", "series", "moi-ra-mat"
    ]

    for href in raw_links:
        path = re.sub(r"^https?://[^/]+", "", href.strip()).split("?")[0].split("#")[0].rstrip("/")
        if re.match(r"^/dtdd/[a-zA-Z0-9\-]+$", path):
            slug = path.split("/dtdd/")[1].lower()
            if slug not in ignore_slugs and not any(kw in slug for kw in ignore_keywords):
                full_link = urljoin(base_url, path)
                if full_link not in product_base_links:
                    product_base_links.append(full_link)

    if MAX_PRODUCTS_PER_SITE:
        product_base_links = product_base_links[:MAX_PRODUCTS_PER_SITE]

    print(f"[TGDD] Tìm thấy {len(product_base_links)} mẫu điện thoại gốc:")
    for idx_dbg, link_dbg in enumerate(product_base_links, 1):
        print(f"   ({idx_dbg}) {link_dbg}")

    results = []
    visited_variant_urls = set()

    # Hàm trích xuất dữ liệu trực tiếp từ DOM <main> bằng JavaScript (miễn nhiễm với comment <!-- --> của React)
    def extract_tgdd_page(current_url, fallback_spec="", fallback_color=""):
        data = driver.execute_script("""
            let h1 = document.querySelector('main h1') || document.querySelector('h1');
            let title = h1 ? h1.innerText.trim() : document.title;

            // 1. Lấy Dung lượng & Màu sắc đang active (!border-primary-600)
            let activeSpec = '';
            let activeColor = '';
            document.querySelectorAll('a[data-disable-progress="true"]').forEach(a => {
                let cls = a.className || '';
                let href = a.getAttribute('href') || '';
                if (cls.includes('border-primary')) {
                    if (href.includes('code=')) {
                        activeColor = a.innerText.trim();
                    } else {
                        activeSpec = a.innerText.trim();
                    }
                }
            });

            // 2. Lấy thêm RAM và Dung lượng lưu trữ trong bảng #spec (nếu có)
            let specRam = '';
            let specRom = '';
            document.querySelectorAll('#spec li').forEach(li => {
                let txt = li.innerText || '';
                if (txt.includes('RAM:')) {
                    let m = txt.match(/(\\d+\\s*GB)/i);
                    if (m) specRam = m[1];
                }
                if (txt.includes('Dung lượng lưu trữ:')) {
                    let m = txt.match(/(\\d+\\s*(GB|TB))/i);
                    if (m) specRom = m[1];
                }
            });

            // 3. Lấy Giá khuyến mãi và Giá gốc (innerText tự động bỏ qua <!-- -->)
            let saleEl = document.querySelector('span.text-24.font-700.text-red-5, div.box-price-present, span.text-red-5.font-700');
            let origEl = document.querySelector('del.text-14.text-gray-5, p.box-price-old, main del');
            let saleStr = saleEl ? saleEl.innerText.trim() : '';
            let origStr = origEl ? origEl.innerText.trim() : saleStr;

            // 4. Lấy Điểm đánh giá (Rating) và Số lượng đánh giá (Reviews) từ #feedback hoặc đầu trang
            let ratingEl = document.querySelector('#feedback span.text-36.font-600, span.text-36.font-600, i.icon__row-6-col-1 + span');
            let ratingStr = ratingEl ? ratingEl.innerText.trim() : '';

            let reviewStr = '';
            document.querySelectorAll('#feedback div.text-gray-5, main div.text-gray-5, main span.text-grey-400').forEach(el => {
                let t = el.innerText.trim();
                if (t.includes('đánh giá')) {
                    reviewStr = t;
                }
            });

            return {
                title: title,
                activeSpec: activeSpec,
                activeColor: activeColor,
                specRam: specRam,
                specRom: specRom,
                saleStr: saleStr,
                origStr: origStr,
                ratingStr: ratingStr,
                reviewStr: reviewStr
            };
        """)

        title = re.sub(r"(- Thế Giới Di Động.*|\|.*)", "", data.get("title", "")).strip()
        if not title or len(title) < 3:
            return None

        active_spec = data.get("activeSpec") or fallback_spec or data.get("specRom") or ""
        if not active_spec:
            m_spec = re.search(r"(\d+\s*(GB|TB))", title, re.IGNORECASE)
            active_spec = m_spec.group(1) if m_spec else "Mặc định"

        # Ghép thêm RAM từ bảng #spec vào chuỗi raw_specs nếu tiêu đề chưa có RAM
        spec_ram = data.get("specRam", "")
        combined_specs = f"{spec_ram} {active_spec}".strip() if spec_ram and spec_ram.upper() not in active_spec.upper() else active_spec

        active_color = data.get("activeColor") or fallback_color or "Mặc định"
        sale_str = data.get("saleStr", "")
        orig_str = data.get("origStr", "") or sale_str
        rating_str = data.get("ratingStr", "")
        review_str = data.get("reviewStr", "")

        if clean_price(sale_str) > 0:
            return (
                "TGDD", "Phone", title, active_color.strip(), combined_specs.strip(),
                orig_str.strip(), sale_str.strip(), rating_str.strip(),
                review_str.strip(), current_url
            )
        return None

    for idx, base_item_url in enumerate(product_base_links, 1):
        try:
            driver.get(base_item_url)
            time.sleep(2.2)
            sel_p = Selector(text=driver.page_source)

            # BƯỚC 1: Lấy tất cả các tùy chọn Dung lượng (thẻ a[data-disable-progress='true'] KHÔNG chứa ?code=)
            storage_options = []
            s_nodes = sel_p.css("a[data-disable-progress='true']:not([href*='code='])")
            for node in s_nodes:
                href = node.attrib.get("href", "").strip()
                s_txt = node.xpath("normalize-space(.)").get() or ""
                if href.startswith("/dtdd/"):
                    full_s = urljoin(base_url, href.split("?")[0])
                    if all(full_s != u for u, _ in storage_options):
                        storage_options.append((full_s, s_txt))

            if not storage_options:
                storage_options = [(base_item_url, "")]

            # BƯỚC 2: Duyệt qua từng phiên bản Dung lượng
            for s_url, s_label in storage_options:
                if driver.current_url.split("?")[0] != s_url.split("?")[0]:
                    driver.get(s_url)
                    time.sleep(1.8)

                sel_s = Selector(text=driver.page_source)

                # BƯỚC 3: Lấy tất cả các tùy chọn Màu sắc (?code=...) của dung lượng hiện tại
                color_options = []
                c_nodes = sel_s.css("a[data-disable-progress='true'][href*='code=']")
                for c_node in c_nodes:
                    c_href = c_node.attrib.get("href", "").strip()
                    c_txt = c_node.xpath("normalize-space(.)").get() or "Mặc định"
                    if c_href.startswith("/dtdd/"):
                        full_c = urljoin(base_url, c_href)
                        if all(full_c != u for u, _ in color_options):
                            color_options.append((full_c, c_txt))

                if not color_options:
                    color_options = [(s_url, "Mặc định")]

                # BƯỚC 4: Truy cập từng link Màu sắc để lấy trọn bộ thông tin
                for c_url, c_label in color_options:
                    if c_url in visited_variant_urls:
                        continue
                    visited_variant_urls.add(c_url)

                    if driver.current_url != c_url:
                        driver.get(c_url)
                        time.sleep(1.4)

                    item_data = extract_tgdd_page(c_url, fallback_spec=s_label, fallback_color=c_label)
                    if item_data:
                        results.append(item_data)
                        print(
                            f"   [TGDD #{idx}] + {item_data[2]} | Specs: {item_data[4]} | "
                            f"Màu: {item_data[3]} | Giá: {item_data[6]} | "
                            f"Sao: {item_data[7]} ({item_data[8]})"
                        )
        except Exception as e:
            print(f"   [TGDD] Bỏ qua link lỗi {base_item_url}: {e}")

    return results
# ==============================================================================
# 2. CELLPHONES (Chuẩn DOM: #blockFilterSort, .list-linked, .list-variants)
# ==============================================================================
def crawl_cellphones(driver):
    base_url = "https://cellphones.com.vn"
    list_url = "https://cellphones.com.vn/mobile.html"
    print(f"\n[CellphoneS] 1. Đang lấy danh sách link sản phẩm từ: {list_url}")
    driver.get(list_url)
    time.sleep(3)
    click_load_more(
        driver,
        "//a[contains(@class, 'btn-show-more')] | //button[contains(@class, 'btn-show-more')]",
        max_clicks=MAX_LOAD_MORE_CLICKS
    )

    sel = Selector(text=driver.page_source)
    raw_links = sel.css("#blockFilterSort a.product__link::attr(href), div.product-info-container a.product__link::attr(href)").getall()
    product_links = []
    for href in raw_links:
        full_link = urljoin(base_url, href)
        if full_link not in product_links:
            product_links.append(full_link)

    if MAX_PRODUCTS_PER_SITE:
        product_links = product_links[:MAX_PRODUCTS_PER_SITE]

    print(f"[CellphoneS] Tìm thấy {len(product_links)} mẫu điện thoại gốc. Bắt đầu quét chiều sâu (Dung lượng x Màu sắc)...")

    results = []
    visited_storage_urls = set()

    for idx, p_url in enumerate(product_links, 1):
        try:
            driver.get(p_url)
            time.sleep(2.0)
            sel_p = Selector(text=driver.page_source)

            # Lấy tất cả các link phiên bản Dung lượng trong div.list-linked
            linked_nodes = sel_p.css("div.list-linked a.item-linked")
            storage_links = []
            for node in linked_nodes:
                href = node.attrib.get("href", "")
                spec_txt = node.xpath("normalize-space(.//strong)").get() or ""
                if href:
                    storage_links.append((urljoin(base_url, href), spec_txt))

            if not storage_links:
                storage_links = [(p_url, "Mặc định")]

            for s_url, spec_txt in storage_links:
                if s_url in visited_storage_urls:
                    continue
                visited_storage_urls.add(s_url)

                if s_url != driver.current_url:
                    driver.get(s_url)
                    time.sleep(1.8)

                sel_s = Selector(text=driver.page_source)
                base_title = sel_s.css("div.box-product-name h1::text, h1::text").get() or ""
                base_orig_price = sel_s.css("del.base-price::text, p.product__price--through::text").get() or ""
                rating_str = sel_s.css("span.average-rating::text").get() or ""
                review_str = sel_s.css("p.boxReview-score__count::text").get() or ""

                # Quét toàn bộ danh sách Màu sắc & Giá từng màu trong ul.list-variants
                variant_items = sel_s.css("ul.list-variants li.item-variant")
                if variant_items:
                    for v_item in variant_items:
                        color_name = v_item.css("strong.item-variant-name::text").get() or "Mặc định"
                        v_sale_price = v_item.css("span.item-variant-price::text").get() or sel_s.css("div.sale-price::text").get() or ""
                        v_href = urljoin(base_url, v_item.css("a.button__change-color::attr(href)").get() or s_url)
                        orig_p = base_orig_price if base_orig_price else v_sale_price

                        if base_title and clean_price(v_sale_price) > 0:
                            results.append((
                                "CellphoneS", "Phone", base_title.strip(), color_name.strip(),
                                spec_txt.strip(), orig_p.strip(), v_sale_price.strip(),
                                rating_str.strip(), review_str.strip(), v_href
                            ))
                            print(f"   [CellphoneS #{idx}] + {base_title.strip()} | Dung lượng: {spec_txt.strip()} | Màu: {color_name.strip()} | Giá: {v_sale_price.strip()}")
                else:
                    v_sale_price = sel_s.css("div.sale-price::text, p.product__price--show::text").get() or ""
                    if base_title and clean_price(v_sale_price) > 0:
                        results.append((
                            "CellphoneS", "Phone", base_title.strip(), "Mặc định",
                            spec_txt.strip(), base_orig_price.strip(), v_sale_price.strip(),
                            rating_str.strip(), review_str.strip(), s_url
                        ))
                        print(f"   [CellphoneS #{idx}] + {base_title.strip()} | Giá: {v_sale_price.strip()}")
        except Exception as e:
            print(f"   [CellphoneS] Bỏ qua link lỗi {p_url}: {e}")

    return results

# ==============================================================================
# 3. FPT SHOP (Chuẩn DOM: a[href^='/dien-thoai/'], button Dung lượng & Màu sắc)
# ==============================================================================
def crawl_fptshop(driver):
    base_url = "https://fptshop.com.vn"
    list_url = "https://fptshop.com.vn/dien-thoai"
    print(f"\n[FPTShop] 1. Đang lấy danh sách link sản phẩm từ: {list_url}")
    driver.get(list_url)
    time.sleep(3.5)
    click_load_more(
        driver,
        "//button[contains(., 'Xem thêm') or contains(., 'kết quả')]",
        max_clicks=MAX_LOAD_MORE_CLICKS
    )

    # Chỉ lấy các thẻ a dẫn tới sản phẩm nằm trong lưới sản phẩm (có chứa img bên trong)
    raw_links = driver.execute_script("""
        let hrefs = [];
        document.querySelectorAll('div.grid a[href^="/dien-thoai/"]:has(img), a[title][href^="/dien-thoai/"]').forEach(a => {
            let h = a.getAttribute('href');
            if (h) hrefs.push(h);
        });
        return hrefs;
    """)

    product_links = []
    ignore_slugs = {
        "/dien-thoai/apple-iphone", "/dien-thoai/samsung", "/dien-thoai/xiaomi",
        "/dien-thoai/oppo", "/dien-thoai/honor", "/dien-thoai/vivo",
        "/dien-thoai/realme", "/dien-thoai/nokia", "/dien-thoai/masstel",
        "/dien-thoai/nubia", "/dien-thoai/tecno", "/dien-thoai/tcl",
        "/dien-thoai/motorola", "/dien-thoai/infinix", "/dien-thoai/itel",
        "/dien-thoai/benco", "/dien-thoai/zte", "/dien-thoai/ai"
    }
    for href in raw_links:
        clean_href = href.split("?")[0].rstrip("/")
        if clean_href not in ignore_slugs and clean_href.count("/") == 2:
            full_link = urljoin(base_url, clean_href)
            if full_link not in product_links:
                product_links.append(full_link)

    if MAX_PRODUCTS_PER_SITE:
        product_links = product_links[:MAX_PRODUCTS_PER_SITE]

    print(f"[FPTShop] Tìm thấy {len(product_links)} mẫu điện thoại gốc. Bắt đầu quét chiều sâu (Dung lượng x Màu sắc)...")

    results = []
    for idx, p_url in enumerate(product_links, 1):
        try:
            driver.get(p_url)
            time.sleep(2.2)

            storage_btns_xpath = "//span[contains(text(), 'Dung lượng')]/following-sibling::div[1]//button[not(@disabled)]"
            storage_btns = driver.find_elements(By.XPATH, storage_btns_xpath)
            num_storages = len(storage_btns) if storage_btns else 1

            for s_idx in range(num_storages):
                storage_label = "Mặc định"
                if len(storage_btns) > 0:
                    current_s_btns = driver.find_elements(By.XPATH, storage_btns_xpath)
                    if s_idx < len(current_s_btns):
                        storage_label = current_s_btns[s_idx].text.strip() or "Mặc định"
                        if num_storages > 1:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_s_btns[s_idx])
                            driver.execute_script("arguments[0].click();", current_s_btns[s_idx])
                            time.sleep(1.5)

                color_btns_xpath = "//span[contains(text(), 'Màu sắc')]/following-sibling::div[1]//button[not(@disabled)]"
                color_btns = driver.find_elements(By.XPATH, color_btns_xpath)
                num_colors = len(color_btns) if color_btns else 1

                for c_idx in range(num_colors):
                    color_label = "Mặc định"
                    if len(color_btns) > 0:
                        current_c_btns = driver.find_elements(By.XPATH, color_btns_xpath)
                        if c_idx < len(current_c_btns):
                            color_label = current_c_btns[c_idx].text.strip() or "Mặc định"
                            if num_colors > 1:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_c_btns[c_idx])
                                driver.execute_script("arguments[0].click();", current_c_btns[c_idx])
                                time.sleep(1.0)

                    sel_v = Selector(text=driver.page_source)
                    title = sel_v.css("h1::text").get() or ""
                    sale_str = sel_v.css("#price-product span.text-2xl::text, #price-product span[class*='bold']::text").get() or ""
                    orig_str = sel_v.css("#price-product span.line-through::text").get() or sale_str

                    rating_str = sel_v.xpath("//div[contains(text(), 'đánh giá')]/preceding-sibling::div[1]//div/text()").get() or ""
                    review_str = sel_v.xpath("//div[contains(text(), 'đánh giá')]/text()").get() or ""

                    if title and clean_price(sale_str) > 0:
                        variant_url = f"{driver.current_url}#s={storage_label}&c={color_label}"
                        results.append((
                            "FPTShop", "Phone", title.strip(), color_label, storage_label,
                            orig_str.strip(), sale_str.strip(), rating_str.strip(),
                            review_str.strip(), variant_url
                        ))
                        print(f"   [FPTShop #{idx}] + {title.strip()} | Dung lượng: {storage_label} | Màu: {color_label} | Giá: {sale_str.strip()}")
        except Exception as e:
            print(f"   [FPTShop] Bỏ qua link lỗi {p_url}: {e}")

    return results

# ==============================================================================
# 4. XUẤT CSV (RAW + CLEANED) VÀ LƯU VÀO MYSQL
# ==============================================================================
def process_and_save(raw_items):
    dataset_dir = r"D:\BIGDATA_PRJ\dataset"
    os.makedirs(dataset_dir, exist_ok=True)
    raw_csv_path = os.path.join(dataset_dir, "products_raw.csv")
    clean_csv_path = os.path.join(dataset_dir, "products_cleaned.csv")

    # 1. Xuất file Dữ liệu thô (products_raw.csv)
    with open(raw_csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "source", "category", "raw_name", "raw_color", "raw_specs",
            "raw_original_price", "raw_sale_price", "raw_rating", "raw_reviews", "variant_url"
        ])
        writer.writerows(raw_items)
    print(f"\n[1/3] Đã xuất {len(raw_items)} bản ghi DỮ LIỆU THÔ ra: {raw_csv_path}")

    # 2. Làm sạch & chuẩn hóa dữ liệu
    cleaned_records = []
    seen = set()

    for src, cat, raw_name, raw_color, raw_specs, orig_str, sale_str, raw_rating, raw_reviews, v_url in raw_items:
        sale_p = clean_price(sale_str)
        if sale_p < 500000:
            continue
        orig_p = clean_price(orig_str)
        if orig_p < sale_p:
            orig_p = sale_p

        brand = detect_brand(raw_name)
        ram, rom = extract_specs(raw_name, raw_specs)
        c_name = clean_product_name(raw_name, rom, raw_color)
        rating, reviews = clean_rating_reviews(raw_rating, raw_reviews)

        # Khử trùng lặp chính xác theo Sàn + Tên chuẩn hóa (đã gồm Dung lượng & Màu) + Giá
        key = (src, c_name, sale_p)
        if key in seen:
            continue
        seen.add(key)

        disc_pct = round(((orig_p - sale_p) / orig_p) * 100, 2) if orig_p > sale_p else 0.0
        full_raw_title = f"{raw_name} | {raw_specs} | {raw_color}".strip(" |")
        cleaned_records.append((
            src, cat, brand, full_raw_title, c_name,
            ram, rom, orig_p, sale_p, disc_pct, rating, reviews
        ))

    # 3. Xuất file Dữ liệu sạch (products_cleaned.csv)
    with open(clean_csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "source", "category", "brand", "raw_name", "clean_name",
            "ram_gb", "storage_gb", "original_price", "sale_price",
            "discount_pct", "rating", "review_count"
        ])
        for idx, row in enumerate(cleaned_records, start=1):
            writer.writerow([idx] + list(row))
    print(f"[2/3] Đã xuất {len(cleaned_records)} bản ghi DỮ LIỆU SẠCH ra: {clean_csv_path}")

    # 4. Lưu vào MySQL (Xóa sạch bảng cũ trước khi nạp)
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE products;")
    if cleaned_records:
        cursor.executemany("""
        INSERT INTO products (
            source, category, brand, raw_name, clean_name,
            ram_gb, storage_gb, original_price, sale_price,
            discount_pct, rating, review_count
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, cleaned_records)
        conn.commit()
    print(f"[3/3] Đã nạp thành công {cursor.rowcount} bản ghi thực tế vào MySQL (Bảng products)!")
    conn.close()

if __name__ == "__main__":
    all_raw = []
    driver = get_driver()
    try:
        all_raw.extend(crawl_tgdd(driver))
        #all_raw.extend(crawl_cellphones(driver))
        #all_raw.extend(crawl_fptshop(driver))
    except Exception as e:
        print(f"Lưu ý trong quá trình điều khiển trình duyệt: {e}")
    finally:
        driver.quit()

    print(f"\nTổng số phiên bản sản phẩm thu thập trực tiếp: {len(all_raw)}")
    process_and_save(all_raw)