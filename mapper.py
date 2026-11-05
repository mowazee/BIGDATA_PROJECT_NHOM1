#!/usr/bin/env python3
import os
import sys

task = os.environ.get("MR_TASK", "MR1")

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    cols = line.split(",")
    if len(cols) < 13:
        continue

    try:
        src, cat, brand = cols[1], cols[2], cols[3]
        c_name = cols[5]
        ram, rom = int(cols[6]), int(cols[7])
        orig_p, sale_p = int(cols[8]), int(cols[9])
        disc_pct = float(cols[10])
        rating, reviews = float(cols[11]), int(cols[12])
    except ValueError:
        continue

    if task == "MR1":  # Đếm số sản phẩm theo Sàn & Thương hiệu
        print(f"{src}_{brand}\t1")
    elif task == "MR2":  # Giá Min/Max/Avg theo Danh mục & Thương hiệu
        print(f"{cat}_{brand}\t{sale_p}")
    elif task == "MR3":  # Phần trăm giảm giá trung bình theo Sàn
        print(f"{src}\t{disc_pct}")
    elif task == "MR4":  # Phân khúc giá sản phẩm
        if sale_p < 7000000:
            seg = "1_Gia_Re_(<7Tr)"
        elif sale_p <= 15000000:
            seg = "2_Tam_Trung_(7-15Tr)"
        elif sale_p <= 25000000:
            seg = "3_Can_Cao_Cap_(15-25Tr)"
        else:
            seg = "4_Cao_Cap_(>25Tr)"
        print(f"{seg}\t1")
    elif task == "MR5":  # So sánh chênh lệch giá cùng 1 máy giữa 3 sàn
        print(f"{c_name}\t{src}:{sale_p}")
    elif task == "MR6":  # Thống kê số lượng & giá TB theo cấu hình RAM-ROM
        print(f"{ram}GB_{rom}GB\t{sale_p}")
    elif task == "MR7":  # Tổng lượt đánh giá & Điểm sao TB theo Thương hiệu
        print(f"{brand}\t{rating}:{reviews}")
    elif task == "MR8":  # Top sản phẩm giảm giá sâu nhất (theo số tiền giảm)
        saved = orig_p - sale_p
        print(f"{cat}\t{saved}:{c_name} ({src})")