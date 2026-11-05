import re
import mysql.connector

def init_db():
    conn = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="root"
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS ecommerce_db;")
    cursor.execute("USE ecommerce_db;")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INT PRIMARY KEY AUTO_INCREMENT,
        source VARCHAR(50),
        category VARCHAR(50),
        brand VARCHAR(50),
        raw_name VARCHAR(255),
        clean_name VARCHAR(255),
        ram_gb INT,
        storage_gb INT,
        original_price BIGINT,
        sale_price BIGINT,
        discount_pct FLOAT,
        rating FLOAT,
        review_count INT
    );
    """)
    conn.commit()
    return conn

def clean_price(price_str):
    if not price_str:
        return 0
    # Chỉ lấy phần số đầu tiên nếu chuỗi bị dính cả giá trả góp hoặc % giảm
    first_part = str(price_str).strip().split("\n")[0]
    digits = re.sub(r"[^\d]", "", first_part)
    return int(digits) if digits else 0

# def extract_specs(name_str, raw_specs_str=""):
#     combined = f"{name_str} {raw_specs_str}".upper()
#     ram, rom = 0, 0

#     if "2TB" in combined or "2 TB" in combined:
#         rom = 2048
#     elif "1TB" in combined or "1 TB" in combined:
#         rom = 1024

#     # Bắt định dạng cặp RAM/ROM phổ biến: 12GB/256GB, 8GB-512GB, 8GB 256GB
#     pair = re.search(r"(\d+)\s*GB\s*[/\-\s]\s*(\d+)\s*GB", combined)
#     if pair:
#         r1, r2 = int(pair.group(1)), int(pair.group(2))
#         if r1 < r2:
#             ram, rom = r1, r2

#     if ram == 0 or rom == 0:
#         matches = re.findall(r"(\d+)\s*GB", combined)
#         for m in matches:
#             n = int(m)
#             if n in [2, 3, 4, 6, 8, 12, 16, 18, 24] and ram == 0:
#                 ram = n
#             elif n in [32, 64, 128, 256, 512, 1024] and rom == 0:
#                 rom = n

#     # Các dòng iPhone thường không ghi RAM trên tiêu đề web bán lẻ
#     if ram == 0:
#         ram = 8
#     if rom == 0:
#         rom = 128
#     return ram, rom

# RAM các đời iPhone (GB). Apple không công bố RAM; đây là số liệu được các trang
# công nghệ đo/đưa tin rộng rãi. Khóa: (đời máy, phiên bản).
IPHONE_RAM = {
    ("11", ""): 4, ("11", "PRO"): 4, ("11", "PRO MAX"): 4,
    ("12", ""): 4, ("12", "MINI"): 4, ("12", "PRO"): 6, ("12", "PRO MAX"): 6,
    ("13", ""): 4, ("13", "MINI"): 4, ("13", "PRO"): 6, ("13", "PRO MAX"): 6,
    ("14", ""): 6, ("14", "PLUS"): 6, ("14", "PRO"): 6, ("14", "PRO MAX"): 6,
    ("15", ""): 6, ("15", "PLUS"): 6, ("15", "PRO"): 8, ("15", "PRO MAX"): 8,
    ("16", ""): 8, ("16", "PLUS"): 8, ("16", "PRO"): 8, ("16", "PRO MAX"): 8, ("16", "E"): 8,
    ("17", ""): 8, ("17", "PRO"): 12, ("17", "PRO MAX"): 12,
    ("AIR", ""): 12, ("SE", ""): 4,
}
IPHONE_DEFAULT_RAM = 8      # đời iPhone mới chưa có trong bảng


def iphone_ram(text):
    """Trả về RAM (GB) của iPhone dựa vào tên máy; None nếu không phải iPhone."""
    if "IPHONE" not in text:
        return None
    if re.search(r"IPHONE\s+AIR\b", text):
        return IPHONE_RAM[("AIR", "")]
    if re.search(r"IPHONE\s+SE\b", text):
        return IPHONE_RAM[("SE", "")]
    m = re.search(r"IPHONE\s+(\d{1,2})\s*(PRO\s*MAX|PRO|PLUS|MINI|E\b)?", text)
    if not m:
        return IPHONE_DEFAULT_RAM
    gen = m.group(1)
    variant = re.sub(r"\s+", " ", m.group(2) or "").strip()
    return IPHONE_RAM.get((gen, variant), IPHONE_RAM.get((gen, ""), IPHONE_DEFAULT_RAM))


CAPACITY_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(TB|GB)\b", re.IGNORECASE)
RAM_LABEL_RE = re.compile(r"RAM\s*[:\-]?\s*(\d+)\s*GB", re.IGNORECASE)
ROM_LABEL_RE = re.compile(r"(?:ROM|BỘ NHỚ TRONG|DUNG LƯỢNG(?: LƯU TRỮ)?)\s*[:\-]?\s*(\d+)\s*(TB|GB)", re.IGNORECASE)
RAM_MAX_GB = 24          # RAM điện thoại hiện nay không vượt quá 24GB
ROM_MIN_GB = 32          # Bộ nhớ trong từ 32GB trở lên


def _capacities(text):
    """Trả về danh sách dung lượng (đơn vị GB) theo đúng thứ tự xuất hiện trong chuỗi."""
    out = []
    for num, unit in CAPACITY_RE.findall(str(text or "")):
        n = float(num.replace(",", "."))
        out.append(int(n * 1024) if unit.upper() == "TB" else int(n))
    return out


def extract_specs(name_str, raw_specs_str=""):
    """
    Tách RAM và ROM (GB).
    - ROM: ưu tiên dung lượng trong raw_specs (là phiên bản đang được chọn trên web),
      vì tên sản phẩm thường giữ phiên bản mặc định (VD: tên "iPhone 18 Pro 256GB"
      nhưng biến thể đang chọn là 512 GB).
    - RAM: ưu tiên nhãn "RAM: xGB", sau đó số nhỏ (<= 24GB) trong specs rồi trong tên;
      iPhone không ghi RAM -> tra bảng theo đời máy.
    - Không xác định được -> 0 (không đoán bừa).
    """
    name_u = str(name_str or "").upper()
    specs_u = str(raw_specs_str or "").upper()
    is_iphone = "IPHONE" in name_u or "IPHONE" in specs_u

    # ---------- ROM ----------
    rom = 0
    m = ROM_LABEL_RE.search(specs_u)
    if m:
        rom = int(m.group(1)) * (1024 if m.group(2).upper() == "TB" else 1)
    if rom == 0:
        for source in (specs_u, name_u):
            big = [c for c in _capacities(source) if c >= ROM_MIN_GB]
            if big:
                rom = big[0]          # dung lượng đầu tiên = phiên bản đang chọn
                break

    # ---------- RAM ----------
    ram = 0
    if is_iphone:
        ram = iphone_ram(name_u) or 0
    else:
        m = RAM_LABEL_RE.search(specs_u) or RAM_LABEL_RE.search(name_u)
        if m:
            ram = int(m.group(1))
        else:
            for source in (specs_u, name_u):
                small = [c for c in _capacities(source) if 0 < c <= RAM_MAX_GB]
                if small:
                    ram = small[0]
                    break

    # Kiểm tra hợp lý: RAM phải nhỏ hơn ROM
    if ram and rom and ram >= rom:
        ram = 0
    return ram, rom

def detect_brand(name_str):
    name_low = str(name_str).lower()
    brand_map = [
        ("iphone", "Apple"), ("apple", "Apple"),
        ("samsung", "Samsung"), ("galaxy", "Samsung"),
        ("xiaomi", "Xiaomi"), ("redmi", "Xiaomi"), ("poco", "Xiaomi"),
        ("oppo", "OPPO"), ("vivo", "Vivo"), ("realme", "Realme"),
        ("honor", "HONOR"), ("tecno", "Tecno"), ("motorola", "Motorola"),
        ("moto ", "Motorola"), ("nokia", "Nokia"), ("tcl", "TCL"),
        ("nubia", "Nubia"), ("zte", "ZTE"), ("asus", "ASUS"),
        ("rog", "ASUS"), ("sony", "Sony"), ("masstel", "Masstel"),
        ("itel", "Itel"), ("infinix", "Infinix"), ("benco", "Benco")
    ]
    for kw, brand in brand_map:
        if kw in name_low:
            return brand
    return "Other"

def clean_product_name(raw_name, storage_gb=0, color="", ram_gb=0):
    noise = r"(Điện thoại|ĐTDĐ|Chính hãng|VN/A|Ibox|\||\(.*?\))"
    cleaned = re.sub(noise, "", str(raw_name), flags=re.IGNORECASE)

    if storage_gb > 0:
        # Bỏ dung lượng mặc định có sẵn trong tên (VD "256GB") rồi gắn đúng ROM của biến thể
        cleaned = re.sub(r"\b\d+(?:[.,]\d+)?\s*(?:GB|TB)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -/")
        rom_label = f"{storage_gb // 1024}TB" if storage_gb >= 1024 else f"{storage_gb}GB"
        if ram_gb and "IPHONE" not in cleaned.upper():
            rom_label = f"{ram_gb}GB/{rom_label}"
        cleaned = f"{cleaned} {rom_label}"
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    clean_c = str(color).strip()
    if clean_c and clean_c.lower() not in ["mặc định", "default", ""] and clean_c.lower() not in cleaned.lower():
        cleaned = f"{cleaned} ({clean_c})"
    return cleaned

def clean_rating_reviews(raw_rating, raw_reviews):
    rating = 0.0
    if raw_rating:
        m_rate = re.search(r"(\d+[.,]\d+|\d+)", str(raw_rating))
        if m_rate:
            val = float(m_rate.group(1).replace(",", "."))
            if 0 < val <= 5.0:
                rating = round(val, 1)

    reviews = 0
    if raw_reviews:
        digits = re.sub(r"[^\d]", "", str(raw_reviews))
        if digits:
            reviews = int(digits)
    return rating, reviews