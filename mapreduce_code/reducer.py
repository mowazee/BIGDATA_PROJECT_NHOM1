#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REDUCER đa năng cho 8 bài toán MapReduce (Hadoop Streaming).
Hadoop đã sắp xếp đầu vào theo KEY -> xử lý tuần tự từng nhóm key bằng itertools.groupby,
không gom toàn bộ dữ liệu vào RAM (đúng tinh thần MapReduce, chạy được với dữ liệu lớn).

Tương thích Python 3.5 (không dùng f-string).
"""
import io
import os
import re
import sys
from itertools import groupby

TASK = os.environ.get("MR_TASK", "MR1").upper()
TOP_N = int(os.environ.get("TOP_N", "5"))

stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")


def read_pairs():
    for raw in stdin:
        line = raw.rstrip("\n")
        if "\t" not in line:
            continue
        key, val = line.split("\t", 1)
        yield key, val


def out(key, text):
    stdout.write("{}\t{}\n".format(key, text))


def fmt_money(v):
    return "{:,}".format(int(v)).replace(",", ".")


for key, group in groupby(read_pairs(), key=lambda kv: kv[0]):
    vals = [v for _, v in group]

    if TASK in ("MR1", "MR4"):
        out(key, sum(int(x) for x in vals))

    elif TASK == "MR2":
        prices = [int(x) for x in vals]
        out(key, "So_Luong:{} | Min:{} | Max:{} | TB:{}".format(
            len(prices), fmt_money(min(prices)), fmt_money(max(prices)),
            fmt_money(sum(prices) / len(prices))))

    elif TASK == "MR3":
        discs = [float(x) for x in vals]
        n_disc = sum(1 for d in discs if d > 0)
        out(key, "So_SP:{} | Dang_Giam_Gia:{} ({}%) | Giam_TB:{}% | Giam_TB_SP_Co_Giam:{}%".format(
            len(discs), n_disc, round(100.0 * n_disc / len(discs), 1),
            round(sum(discs) / len(discs), 2),
            round(sum(d for d in discs if d > 0) / n_disc, 2) if n_disc else 0))

    elif TASK == "MR5":
        # Giá thấp nhất của máy này trên từng sàn
        best = {}
        for item in vals:
            s, p = item.rsplit(":", 1)
            p = int(p)
            if s not in best or p < best[s]:
                best[s] = p
        if len(best) >= 2:     # chỉ in máy được bán ở ít nhất 2 sàn
            # Không dùng min()/max() trên dict: Python 3.5 không giữ thứ tự dict -> kết quả hòa giá
            # thay đổi giữa các lần chạy. Liệt kê đủ các sàn đồng giá, sắp xếp theo tên.
            p_lo, p_hi = min(best.values()), max(best.values())
            detail = ", ".join("{}={}".format(s, fmt_money(best[s])) for s in sorted(best))
            if p_lo == p_hi:
                out(key, "Bang_Gia | Chenh_Lech:0 | {}".format(detail))
            else:
                lo = "/".join(sorted(s for s in best if best[s] == p_lo))
                hi = "/".join(sorted(s for s in best if best[s] == p_hi))
                out(key, "Re_Nhat:{} | Dat_Nhat:{} | Chenh_Lech:{} | {}".format(
                    lo, hi, fmt_money(p_hi - p_lo), detail))

    elif TASK == "MR6":
        prices = [int(x) for x in vals]
        out(key, "So_Luong:{} | Gia_TB:{}".format(len(prices), fmt_money(sum(prices) / len(prices))))

    elif TASK == "MR7":
        pairs = [(float(x.split(":")[0]), int(x.split(":")[1])) for x in vals]
        rated = [(r, n) for r, n in pairs if r > 0]          # bỏ sản phẩm chưa có đánh giá (0 sao)
        total_reviews = sum(n for _, n in rated)
        if rated:
            simple_avg = sum(r for r, _ in rated) / len(rated)
            weighted = (sum(r * n for r, n in rated) / total_reviews) if total_reviews else simple_avg
        else:
            simple_avg = weighted = 0
        out(key, "So_SP:{} | SP_Co_Danh_Gia:{} | Sao_TB:{} | Sao_TB_Trong_So:{} | Tong_Luot_DG:{}".format(
            len(pairs), len(rated), round(simple_avg, 2), round(weighted, 2), total_reviews))

    elif TASK == "MR8":
        # Bỏ lặp màu: mỗi máy (tên không kèm màu + dung lượng + sàn) chỉ giữ dòng giảm nhiều nhất.
        # info có dạng "iPhone Air 1TB (Trắng Mây) (TGDD)" -> model = "iPhone Air 1TB|TGDD"
        best = {}
        for x in vals:
            saved, info = x.split(":", 1)
            saved = int(saved)
            name, _, src = info.rpartition(" (")
            model = re.sub(r"\s*\(.*?\)", "", name).strip().lower() + "|" + src
            if model not in best or (saved, info) > best[model]:
                best[model] = (saved, info)
        items = sorted(best.values(), key=lambda t: (-t[0], t[1]))  # giảm nhiều nhất trước; hòa thì theo tên
        for rank, (saved, info) in enumerate(items[:TOP_N], 1):
            out(key, "Top{} | Giam:{}d | {}".format(rank, fmt_money(saved), info))

stdout.flush()
