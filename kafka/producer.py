#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KAFKA PRODUCER: phát dữ liệu sản phẩm (dataset/products_cleaned.csv) vào topic Kafka như một luồng (stream),
mô phỏng việc các sàn liên tục đẩy giá mới lên hệ thống.

  pip install kafka-python
  python kafka/producer.py                 # gửi toàn bộ sản phẩm, nghỉ 5ms giữa 2 tin
  python kafka/producer.py --delay 0.2     # chậm hơn để quan sát luồng trực tiếp

Mỗi tin nhắn: key = tên sàn (TGDD / CellphoneS / FPTShop) -> cùng sàn vào cùng partition,
value = JSON 1 sản phẩm + thời điểm gửi (event_time).
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime

from kafka import KafkaProducer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument("--bootstrap", default="localhost:9094")
ap.add_argument("--topic", default="products_stream")
ap.add_argument("--csv", default=os.path.join(ROOT, "dataset", "products_cleaned.csv"))
ap.add_argument("--delay", type=float, default=0.005, help="giây nghỉ giữa 2 tin nhắn")
args = ap.parse_args()

producer = KafkaProducer(
    bootstrap_servers=args.bootstrap,
    key_serializer=lambda k: k.encode("utf-8"),
    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    acks="all",
)

INT_COLS = {"id", "ram_gb", "storage_gb", "original_price", "sale_price", "review_count"}
FLOAT_COLS = {"discount_pct", "rating"}

sent = {}
with open(args.csv, encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        rec = {k: (int(v) if k in INT_COLS else float(v) if k in FLOAT_COLS else v) for k, v in row.items()}
        rec["event_time"] = datetime.now().isoformat(timespec="milliseconds")
        producer.send(args.topic, key=rec["source"], value=rec)
        sent[rec["source"]] = sent.get(rec["source"], 0) + 1
        if args.delay:
            time.sleep(args.delay)

producer.flush()
producer.close()
print("Da gui {} tin nhan vao topic '{}': {}".format(sum(sent.values()), args.topic, sent))
