#!/usr/bin/env python3
from collections import defaultdict
import os
import sys

task = os.environ.get("MR_TASK", "MR1")
data = defaultdict(list)

for line in sys.stdin:
    line = line.strip()
    if not line or "\t" not in line:
        continue
    key, val = line.split("\t", 1)
    data[key].append(val)

for key in sorted(data.keys()):
    vals = data[key]
    if task in ["MR1", "MR4"]:
        print(f"{key}\t{ sum(int(x) for x in vals) }")
    elif task == "MR2":
        prices = [int(x) for x in vals]
        avg_p = int(sum(prices) / len(prices))
        print(f"{key}\tCount:{len(prices)} | Min:{min(prices)} | Max:{max(prices)} | Avg:{avg_p}")
    elif task == "MR3":
        discs = [float(x) for x in vals]
        print(f"{key}\tAvg_Discount:{round(sum(discs)/len(discs), 2)}%")
    elif task == "MR5":
        source_prices = {}
        for item in vals:
            s, p = item.split(":")
            p = int(p)
            if s not in source_prices or p < source_prices[s]:
                source_prices[s] = p
        if len(source_prices) >= 2:
            min_s = min(source_prices, key=source_prices.get)
            max_s = max(source_prices, key=source_prices.get)
            diff = source_prices[max_s] - source_prices[min_s]
            print(f"{key}\tRe_Nhat:{min_s}({source_prices[min_s]}) | Dat_Nhat:{max_s}({source_prices[max_s]}) | Chenh_Lech:{diff}")
    elif task == "MR6":
        prices = [int(x) for x in vals]
        print(f"{key}\tSo_Luong:{len(prices)} | Gia_TB:{int(sum(prices)/len(prices))}")
    elif task == "MR7":
        ratings = [float(x.split(":")[0]) for x in vals]
        reviews = [int(x.split(":")[1]) for x in vals]
        print(f"{key}\tDiem_TB:{round(sum(ratings)/len(ratings), 2)}⭐ | Tong_Danh_Gia:{sum(reviews)}")
    elif task == "MR8":
        items = []
        for x in vals:
            saved_str, name_info = x.split(":", 1)
            items.append((int(saved_str), name_info))
        items.sort(reverse=True)
        for saved, name_info in items[:5]:  # Top 5 mỗi danh mục
            print(f"{key}\tGiam:{saved}VND | {name_info}")