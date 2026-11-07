#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAPPER đa năng cho 8 bài toán MapReduce (Hadoop Streaming).
Chọn bài toán bằng biến môi trường MR_TASK=MR1..MR8 (truyền qua -cmdenv MR_TASK=MRx).

Thứ tự cột (bảng products sau khi Sqoop import):
 0:id 1:source 2:category 3:brand 4:raw_name 5:clean_name 6:ram_gb 7:storage_gb
 8:original_price 9:sale_price 10:discount_pct 11:rating 12:review_count

Lưu ý: viết tương thích Python 3.5 (container bde2020 dùng Debian Stretch) -> KHÔNG dùng f-string.
"""
import csv
import io
import os
import re
import sys

TASK = os.environ.get("MR_TASK", "MR1").upper()

# Đọc/ghi UTF-8 bất kể locale của container (tránh lỗi tiếng Việt)
stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")


def emit(key, value):
    # Key/Value không được chứa TAB hoặc xuống dòng (TAB là ký tự phân tách của Streaming)
    key = str(key).replace("\t", " ").replace("\n", " ")
    value = str(value).replace("\t", " ").replace("\n", " ")
    stdout.write("{}\t{}\n".format(key, value))


def split_line(line):
    """Tự nhận dạng ký tự phân tách: TAB, '|' hoặc ',' (có hỗ trợ trường đặt trong dấu nháy)."""
    if "\t" in line:
        return line.split("\t")
    if line.count("|") >= 12 and "," not in line:
        return line.split("|")
    return next(csv.reader([line]))


# Hai thứ tự cột có thể gặp:
#  - CSV / bảng MySQL gốc: id, source, category, ...
#  - Thư mục Sqoop/Hive thực tế trên HDFS (/user/hadoop/hive/warehouse/products): cột theo ABC
COLS_ORIGINAL = ["id", "source", "category", "brand", "raw_name", "clean_name", "ram_gb", "storage_gb",
                 "original_price", "sale_price", "discount_pct", "rating", "review_count"]
COLS_ALPHA = sorted(COLS_ORIGINAL)
SOURCES = {"TGDD", "CellphoneS", "FPTShop"}


def to_record(cols):
    """Nhận dạng thứ tự cột dựa vào vị trí của cột source; trả về dict hoặc None."""
    if len(cols) != 13:
        return None
    if cols[1].strip() in SOURCES:
        names = COLS_ORIGINAL
    elif cols[COLS_ALPHA.index("source")].strip() in SOURCES:
        names = COLS_ALPHA
    else:
        return None
    return dict(zip(names, (c.strip() for c in cols)))


def model_key(brand, clean_name, rom):
    """Khóa so sánh cùng 1 máy giữa các sàn: bỏ màu (trong ngoặc), bỏ dung lượng, bỏ chữ thừa, gắn ROM."""
    name = re.sub(r"\(.*?\)", " ", clean_name)
    name = re.sub(r"\b\d+\s*(GB|TB)\b(\s*/\s*\d+\s*(GB|TB)\b)?", " ", name, flags=re.I)
    name = re.sub(r"\b(5G|4G|chính hãng|vn/a)\b", " ", name, flags=re.I)
    name = re.sub(r"[^0-9a-zA-ZÀ-ỹ ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip().lower()
    return "{}|{}|{}GB".format(brand, name, rom)


# Màu gốc: mỗi sàn đặt tên màu khác nhau ("Xanh Dương" / "Xanh dương nhạt" / "Xanh Navy", "Đen" / "Đen Không Gian")
# -> quy về nhóm màu cơ bản để so sánh được cùng một màu giữa các sàn. Thứ tự kiểm tra quan trọng.
COLOR_RULES = [
    ("Xanh lá", ("xanh lá", "xanh lục", "xanh bạc hà", "xanh mint", "xanh ngọc", "xanh rêu", "lục bảo")),
    ("Xanh", ("xanh", "navy", "băng thanh", "trời đêm", "lưu ly", "mòng két", "blue")),
    ("Titan", ("titan", "titanium")),
    ("Trắng", ("trắng", "white", "kem")),
    ("Đen", ("đen", "black", "graphite")),
    ("Bạc", ("bạc", "silver")),
    ("Xám", ("xám", "ghi", "gray", "grey")),
    ("Tím", ("tím", "purple", "lavender", "oải hương")),
    ("Hồng", ("hồng", "pink")),
    ("Vàng", ("vàng", "gold", "yellow")),
    ("Cam", ("cam", "orange")),
    ("Nâu", ("nâu", "brown")),
    ("Đỏ", ("đỏ", "red", "burgundy")),
]


def base_color(clean_name):
    """Lấy màu trong ngoặc cuối tên ("... (Xanh Dương nhạt)") và quy về nhóm màu cơ bản; không có màu -> ''."""
    m = re.search(r"\(([^()]*)\)\s*$", clean_name)
    if not m:
        return ""
    c = m.group(1).strip().lower()
    for base, words in COLOR_RULES:
        if any(c.startswith(w) or (" " + w) in (" " + c) for w in words):
            return base
    return c.title()


def price_segment(p):
    if p < 7000000:
        return "1_Gia_Re_(<7Tr)"
    if p <= 15000000:
        return "2_Tam_Trung_(7-15Tr)"
    if p <= 25000000:
        return "3_Can_Cao_Cap_(15-25Tr)"
    return "4_Cao_Cap_(>25Tr)"


for raw in stdin:
    line = raw.strip()
    if not line:
        continue
    try:
        cols = split_line(line)
    except Exception:
        continue
    rec = to_record(cols)        # bỏ dòng tiêu đề / dòng lỗi số cột
    if rec is None:
        continue

    try:
        src, cat, brand = rec["source"], rec["category"], rec["brand"]
        c_name = rec["clean_name"]
        ram, rom = int(float(rec["ram_gb"])), int(float(rec["storage_gb"]))
        orig_p, sale_p = int(float(rec["original_price"])), int(float(rec["sale_price"]))
        disc_pct = float(rec["discount_pct"])
        rating, reviews = float(rec["rating"]), int(float(rec["review_count"]))
    except (ValueError, KeyError):
        continue
    if sale_p <= 0:
        continue

    if TASK == "MR1":    # Số sản phẩm theo Sàn & Thương hiệu
        emit("{}_{}".format(src, brand), 1)

    elif TASK == "MR2":  # Giá Min/Max/Avg theo Danh mục & Thương hiệu
        emit("{}_{}".format(cat, brand), sale_p)

    elif TASK == "MR3":  # % giảm giá trung bình theo Sàn
        emit(src, disc_pct)

    elif TASK == "MR4":  # Số sản phẩm theo Phân khúc giá
        emit(price_segment(sale_p), 1)

    elif TASK == "MR5":  # So sánh giá cùng 1 máy (cùng ROM) giữa các sàn
        emit(model_key(brand, c_name, rom), "{}:{}".format(src, sale_p))

    elif TASK == "MR6":  # Số lượng & giá TB theo cấu hình RAM-ROM (bỏ máy không rõ cấu hình)
        if ram > 0 and rom > 0:
            emit("{}GB_{}GB".format(ram, rom), sale_p)

    elif TASK == "MR7":  # Điểm sao TB (có trọng số lượt đánh giá) & tổng lượt đánh giá theo Thương hiệu
        emit(brand, "{}:{}".format(rating, reviews))

    elif TASK == "MR8":  # Top 5 sản phẩm giảm nhiều tiền nhất theo Hãng
        saved = orig_p - sale_p
        if saved > 0:
            emit(brand, "{}:{} ({})".format(saved, c_name, src))

    elif TASK == "MR9":  # So sánh giá cùng 1 máy, cùng ROM VÀ cùng màu giữa các sàn
        color = base_color(c_name)
        if color:
            emit(model_key(brand, c_name, rom) + "|" + color, "{}:{}".format(src, sale_p))

stdout.flush()
