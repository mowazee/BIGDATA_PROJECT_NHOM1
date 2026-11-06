# -*- coding: utf-8 -*-
"""
Mô phỏng Hadoop Streaming trên máy (Windows/Linux) để kiểm tra trước khi chạy trên cụm:
   map -> sort theo key (shuffle) -> reduce
Cách dùng:  python test_local.py                (cả 8 bài, dữ liệu dataset/products_cleaned.csv)
            python test_local.py 5 path/to.csv  (chỉ MR5)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
tasks = sys.argv[1].split(",") if len(sys.argv) > 1 else [str(i) for i in range(1, 9)]
data_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "dataset", "products_cleaned.csv")

with open(data_path, "rb") as f:
    data = f.read().replace(b"\xef\xbb\xbf", b"")   # bỏ BOM của file CSV xuất từ Excel/Python

for t in tasks:
    env = dict(os.environ, MR_TASK="MR" + t, PYTHONIOENCODING="utf-8")
    mapped = subprocess.run([sys.executable, os.path.join(HERE, "mapper.py")],
                            input=data, stdout=subprocess.PIPE, env=env, check=True).stdout
    lines = [l for l in mapped.split(b"\n") if l]
    lines.sort(key=lambda l: l.split(b"\t", 1)[0])          # shuffle & sort theo key (byte order như Hadoop)
    reduced = subprocess.run([sys.executable, os.path.join(HERE, "reducer.py")],
                             input=b"\n".join(lines) + b"\n", stdout=subprocess.PIPE, env=env, check=True).stdout
    out = reduced.decode("utf-8").splitlines()
    print("=" * 20, "MR" + t, "| map:", len(lines), "dòng -> reduce:", len(out), "dòng", "=" * 20)
    for l in out[:15]:
        print(l)
    print()
