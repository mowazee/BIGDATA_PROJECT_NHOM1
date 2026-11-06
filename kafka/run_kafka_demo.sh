#!/bin/bash
# DEMO KAFKA: Producer (Windows) -> topic products_stream -> Consumer -> HDFS -> Hive
#   Cách chạy (Git Bash, tại thư mục project, cụm đang chạy):  bash kafka/run_kafka_demo.sh
# Yêu cầu: pip install kafka-python
set -e
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
PY=${PYTHON:-python}
TOPIC=products_stream
KBIN=/opt/kafka/bin
HDFS_DIR=/user/root/kafka_stream

echo "=== [1/5] Tạo topic $TOPIC (3 partition) ==="
docker exec kafka $KBIN/kafka-topics.sh --bootstrap-server kafka:9092 --delete --topic $TOPIC >/dev/null 2>&1 || true
sleep 3
docker exec kafka $KBIN/kafka-topics.sh --bootstrap-server kafka:9092 --create --topic $TOPIC --partitions 3 --replication-factor 1
docker exec kafka $KBIN/kafka-topics.sh --bootstrap-server kafka:9092 --describe --topic $TOPIC

echo "=== [2/5] Producer: phát dữ liệu sản phẩm vào Kafka ==="
"$PY" kafka/producer.py --topic $TOPIC

echo "=== [3/5] Số tin nhắn trong từng partition ==="
docker exec kafka $KBIN/kafka-get-offsets.sh --bootstrap-server kafka:9092 --topic $TOPIC

echo "=== [4/5] Consumer: đọc toàn bộ topic -> kafka/consumed_products.jsonl ==="
docker exec kafka $KBIN/kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic $TOPIC \
  --from-beginning --group hdfs_sink --timeout-ms 15000 2>/dev/null > kafka/consumed_products.jsonl || true
echo "    -> $(wc -l < kafka/consumed_products.jsonl) tin nhắn"

echo "=== [5/5] Ghi vào HDFS $HDFS_DIR và tạo bảng Hive ==="
docker exec namenode bash -c "hdfs dfs -mkdir -p $HDFS_DIR && hdfs dfs -rm -f -skipTrash $HDFS_DIR/* >/dev/null 2>&1; true"
docker exec -i namenode hdfs dfs -put -f - $HDFS_DIR/products.jsonl < kafka/consumed_products.jsonl
docker exec namenode hdfs dfs -ls $HDFS_DIR
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 --silent=true -e "
  CREATE DATABASE IF NOT EXISTS ecommerce_warehouse;
  CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_warehouse.kafka_products_raw (json STRING)
    LOCATION '$HDFS_DIR';
  SELECT get_json_object(json, '\$.source') AS source, COUNT(*) AS so_tin,
         CAST(AVG(CAST(get_json_object(json, '\$.sale_price') AS BIGINT)) AS BIGINT) AS gia_tb
  FROM ecommerce_warehouse.kafka_products_raw GROUP BY get_json_object(json, '\$.source');" 2>/dev/null
echo "HOAN TAT."
