# -*- coding: utf-8 -*-
"""Lọc giá bất thường khi so sánh giữa các sàn.

Quy tắc: gom sản phẩm theo (hãng, mẫu máy, dung lượng ROM, màu cơ bản) – cùng khóa với bài MR9. Trong mỗi nhóm có
từ 2 sàn trở lên, nếu giá bán của một dòng THẤP HƠN giá thấp nhất của các sàn khác quá 10% thì xóa dòng đó
(thường là crawler đọc nhầm khối giá khác trên trang, ví dụ giá thu cũ đổi mới, không phải giá bán thật).

  python crawl/loc_chenh_lech.py              # xem trước, không ghi
  python crawl/loc_chenh_lech.py --apply      # ghi đè dataset/products_cleaned.csv, lưu danh sách dòng bị xóa
"""
import csv
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "mapreduce_code"))
NGUONG = 0.10       # thấp hơn các sàn khác quá 10% -> xóa

# Dùng lại đúng hàm tạo khóa của mapper.py để kết quả khớp với MR5/MR9
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("mapper_funcs", os.path.join(ROOT, "mapreduce_code", "mapper.py"))
_src = open(os.path.join(ROOT, "mapreduce_code", "mapper.py"), encoding="utf-8").read().split("\nfor raw in stdin:")[0]
_ns = {}
exec(compile(_src, "mapper.py", "exec"), _ns)          # chỉ nạp phần định nghĩa hàm, không chạy vòng đọc stdin
model_key, base_color = _ns["model_key"], _ns["base_color"]

CSV_IN = os.path.join(ROOT, "dataset", "products_cleaned.csv")
CSV_DEL = os.path.join(ROOT, "dataset", "products_removed_price_outliers.csv")


def one_pass(rows):
    """Trả về {chỉ số dòng: (khóa, giá sàn khác thấp nhất, % thấp hơn)} cần xóa trong 1 lượt."""
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        color = base_color(r["clean_name"])
        key = model_key(r["brand"], r["clean_name"], int(float(r["storage_gb"]))) + "|" + color
        groups[key].append(i)

    drop = {}
    for key, idx in groups.items():
        srcs = {rows[i]["source"] for i in idx}
        if len(srcs) < 2:
            continue
        for i in idx:
            me = rows[i]["source"]
            others = [int(rows[j]["sale_price"]) for j in idx if rows[j]["source"] != me]
            ref = min(others)
            p = int(rows[i]["sale_price"])
            if p < ref * (1 - NGUONG):
                drop[i] = (key, ref, round(100.0 * (ref - p) / ref, 1))
    return drop


def run(apply=False):
    with open(CSV_IN, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0].keys())
    total = len(rows)
    removed = []                 # (dòng, giá sàn khác thấp nhất, %)
    lap = 0
    while True:                  # lặp tới khi không còn dòng nào thấp hơn sàn khác quá 10%
        drop = one_pass(rows)
        if not drop:
            break
        lap += 1
        removed += [(rows[i], ref, pct) for i, (key, ref, pct) in drop.items()]
        rows = [r for i, r in enumerate(rows) if i not in drop]
    kept = rows
    by_src = defaultdict(int)
    for r, _, _ in removed:
        by_src[r["source"]] += 1
    print("Tổng: {} dòng | xóa {} dòng sau {} lượt (thấp hơn sàn khác > {:.0f}%) | còn {} dòng".format(
        total, len(removed), lap, NGUONG * 100, len(kept)))
    print("Xóa theo sàn:", dict(by_src))
    for r, ref, pct in sorted(removed, key=lambda x: -x[2])[:15]:
        print("  - {:10} {:48.48} {:>12,} < {:>12,} (-{}%)".format(r["source"], r["clean_name"], int(r["sale_price"]), ref, pct))

    if apply and removed:
        with open(CSV_DEL, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields + ["gia_san_khac_thap_nhat", "thap_hon_pct"])
            w.writeheader()
            for r, ref, pct in removed:
                w.writerow(dict(r, gia_san_khac_thap_nhat=ref, thap_hon_pct=pct))
        for n, r in enumerate(kept, 1):       # đánh lại id liên tục
            r["id"] = str(n)
        with open(CSV_IN, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(kept)
        print("Đã ghi", CSV_IN, "và", CSV_DEL)
    return kept, drop


if __name__ == "__main__":
    run(apply="--apply" in sys.argv)
