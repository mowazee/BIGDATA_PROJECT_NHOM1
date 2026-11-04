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

def extract_specs(name_str, raw_specs_str=""):
    combined = f"{name_str} {raw_specs_str}".upper()
    ram, rom = 0, 0

    if "2TB" in combined or "2 TB" in combined:
        rom = 2048
    elif "1TB" in combined or "1 TB" in combined:
        rom = 1024

    # Bắt định dạng cặp RAM/ROM phổ biến: 12GB/256GB, 8GB-512GB, 8GB 256GB
    pair = re.search(r"(\d+)\s*GB\s*[/\-\s]\s*(\d+)\s*GB", combined)
    if pair:
        r1, r2 = int(pair.group(1)), int(pair.group(2))
        if r1 < r2:
            ram, rom = r1, r2

    if ram == 0 or rom == 0:
        matches = re.findall(r"(\d+)\s*GB", combined)
        for m in matches:
            n = int(m)
            if n in [2, 3, 4, 6, 8, 12, 16, 18, 24] and ram == 0:
                ram = n
            elif n in [32, 64, 128, 256, 512, 1024] and rom == 0:
                rom = n

    # Các dòng iPhone thường không ghi RAM trên tiêu đề web bán lẻ
    if ram == 0:
        ram = 8
    if rom == 0:
        rom = 128
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

def clean_product_name(raw_name, storage_gb=0, color=""):
    noise = r"(Điện thoại|ĐTDĐ|Chính hãng|VN/A|Ibox|\||\(.*?\))"
    cleaned = re.sub(noise, "", str(raw_name), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if storage_gb > 0:
        rom_label = f"{storage_gb // 1024}TB" if storage_gb >= 1024 else f"{storage_gb}GB"
        if rom_label not in cleaned.upper().replace(" ", ""):
            cleaned = f"{cleaned} {rom_label}"

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