# -*- coding: utf-8 -*-
"""
Chuyển kết quả 8 bài MapReduce (mapreduce_code/results/MR1..MR8.txt) và dữ liệu sạch
(dataset/products_cleaned.csv) thành file dashboard/data/dashboard_data.js cho dashboard.

Chạy lại mỗi khi có kết quả MapReduce mới:
    python dashboard/build_data.py
Lấy kết quả mới nhất trực tiếp từ HDFS (container namenode đang chạy):
    python dashboard/build_data.py --from-hdfs
"""
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS_DIR = os.path.join(ROOT, "mapreduce_code", "results")
CSV_PATH = os.path.join(ROOT, "dataset", "products_cleaned.csv")
OUT_PATH = os.path.join(HERE, "data", "dashboard_data.js")


# ---------------------------------------------------------------- đọc file kết quả
def read_mr(task):
    """Trả về list (key, value) của bài MRx. Ưu tiên HDFS nếu có cờ --from-hdfs."""
    text = None
    if "--from-hdfs" in sys.argv:
        try:
            text = subprocess.run(
                ["docker", "exec", "namenode", "bash", "-c",
                 "hdfs dfs -cat /user/root/mr_output_{}/part-* 2>/dev/null".format(task)],
                stdout=subprocess.PIPE, check=True, env=dict(os.environ, MSYS_NO_PATHCONV="1"),
            ).stdout.decode("utf-8")
        except Exception as e:
            print("  ! Không đọc được HDFS cho MR{} ({}), dùng file local".format(task, e))
    if not text:
        path = os.path.join(RESULTS_DIR, "MR{}.txt".format(task))
        if not os.path.exists(path):
            print("  ! Thiếu", path)
            return []
        with open(path, encoding="utf-8") as f:
            text = f.read()
    rows = []
    for line in text.splitlines():
        if "\t" in line:
            k, v = line.rstrip("\r").split("\t", 1)
            rows.append((k, v))
    return rows


def money(s):
    """'11.800.000' / '13.520.000d' -> 11800000"""
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0


def fields(value):
    """'So_Luong:2 | Min:3.190.000' -> {'So_Luong': '2', 'Min': '3.190.000'}"""
    out = {}
    for part in value.split(" | "):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def num(s):
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace(",", "."))
    return float(m.group(0)) if m else 0.0


# ---------------------------------------------------------------- từng bài toán
def mr1():   # Số sản phẩm theo Sàn & Hãng
    return [{"source": k.split("_", 1)[0], "brand": k.split("_", 1)[1], "count": int(v)}
            for k, v in read_mr(1)]


def mr2():   # Giá Min/Max/TB theo Hãng
    out = []
    for k, v in read_mr(2):
        f = fields(v)
        out.append({"brand": k.split("_", 1)[1], "count": int(f["So_Luong"]),
                    "min": money(f["Min"]), "max": money(f["Max"]), "avg": money(f["TB"])})
    return out


def mr3():   # Giảm giá theo Sàn
    out = []
    for k, v in read_mr(3):
        f = fields(v)
        m = re.match(r"(\d+)\s*\(([\d.]+)%\)", f["Dang_Giam_Gia"])
        out.append({"source": k, "total": int(f["So_SP"]), "discounted": int(m.group(1)),
                    "discounted_pct": float(m.group(2)), "avg_discount": num(f["Giam_TB"]),
                    "avg_discount_discounted": num(f["Giam_TB_SP_Co_Giam"])})
    return out


def mr4():   # Phân khúc giá
    labels = {"1": "Giá rẻ (< 7 triệu)", "2": "Tầm trung (7–15 triệu)",
              "3": "Cận cao cấp (15–25 triệu)", "4": "Cao cấp (> 25 triệu)"}
    return [{"order": int(k[0]), "segment": labels.get(k[0], k), "count": int(v)}
            for k, v in sorted(read_mr(4))]


def mr5(n=5):   # So sánh giá cùng máy giữa các sàn (MR9: thêm cùng màu – khóa có phần "|màu")
    out = []
    if not os.path.exists(os.path.join(RESULTS_DIR, "MR{}.txt".format(n))):
        return out
    for k, v in read_mr(n):
        brand, model, rom, color = (k.split("|") + ["", "", "", ""])[:4]
        detail = v.split(" | ")[-1]
        prices = {}
        for item in detail.split(", "):
            if "=" in item:
                s, p = item.split("=", 1)
                prices[s.strip()] = money(p)
        if len(prices) < 2:
            continue
        rom_gb = int(re.sub(r"\D", "", rom) or 0)
        rom_lbl = "{}TB".format(rom_gb // 1024) if rom_gb >= 1024 else "{}GB".format(rom_gb)
        label = "{} {}".format(model.title().replace("Iphone", "iPhone"), rom_lbl) + (" · " + color if color else "")
        out.append({"brand": brand, "model": label, "color": color,
                    "prices": prices, "diff": max(prices.values()) - min(prices.values()),
                    "same_price": v.startswith("Bang_Gia")})
    out.sort(key=lambda r: -r["diff"])
    return out


def mr6():   # Cấu hình RAM-ROM
    out = []
    for k, v in read_mr(6):
        m = re.match(r"(\d+)GB_(\d+)GB", k)
        f = fields(v)
        out.append({"ram": int(m.group(1)), "rom": int(m.group(2)),
                    "count": int(f["So_Luong"]), "avg": money(f["Gia_TB"])})
    return out


def mr7():   # Đánh giá theo Hãng
    out = []
    for k, v in read_mr(7):
        f = fields(v)
        out.append({"brand": k, "count": int(f["So_SP"]), "rated": int(f["SP_Co_Danh_Gia"]),
                    "rating": num(f["Sao_TB"]), "rating_weighted": num(f["Sao_TB_Trong_So"]),
                    "reviews": int(f["Tong_Luot_DG"])})
    return out


def mr8():   # Top 5 giảm giá theo Hãng
    out = []
    for k, v in read_mr(8):
        parts = v.split(" | ")
        info = parts[2] if len(parts) > 2 else ""
        name, _, src = info.rpartition(" (")
        out.append({"brand": k, "rank": int(re.sub(r"\D", "", parts[0]) or 0),
                    "saved": money(parts[1]), "name": name, "source": src.rstrip(")")})
    return out


def products():
    rows = []
    if not os.path.exists(CSV_PATH):
        return rows
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                rows.append([r["source"], r["brand"], r["clean_name"], int(r["ram_gb"]), int(r["storage_gb"]),
                             int(r["original_price"]), int(r["sale_price"]), float(r["discount_pct"]),
                             float(r["rating"]), int(r["review_count"])])
            except (ValueError, KeyError):
                continue
    return rows


if __name__ == "__main__":
    data = {
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "mr1": mr1(), "mr2": mr2(), "mr3": mr3(), "mr4": mr4(),
        "mr5": mr5(), "mr6": mr6(), "mr7": mr7(), "mr8": mr8(), "mr9": mr5(9),
        "products_columns": ["source", "brand", "name", "ram", "rom", "original_price",
                             "sale_price", "discount_pct", "rating", "reviews"],
        "products": products(),
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        # Ghi dạng biến JS để mở index.html trực tiếp (file://) không bị chặn CORS như fetch JSON
        f.write("window.DASHBOARD_DATA = ")
        json.dump(data, f, ensure_ascii=False)
        f.write(";\n")
    print("Đã tạo {} ({} sản phẩm, MR5: {} mẫu máy, MR9: {} mẫu máy + màu)".format(
        OUT_PATH, len(data["products"]), len(data["mr5"]), len(data["mr9"])))
