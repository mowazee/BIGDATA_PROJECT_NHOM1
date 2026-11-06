# Apache Kafka – Truyền dữ liệu sản phẩm dạng luồng (công cụ ngoài chương trình)

Luồng dữ liệu:

```
products_cleaned.csv ──► producer.py ──► Kafka topic "products_stream" ──► consumer ──► HDFS ──► Hive
     (Windows)          (localhost:9094)      (3 partition, key = sàn)                /user/root/kafka_stream   ecommerce_warehouse.kafka_products_raw
```

- **Producer** (`producer.py`, chạy trên Windows): đọc từng sản phẩm, gửi 1 tin nhắn JSON / sản phẩm, key là tên sàn
  (cùng sàn → cùng partition), thêm trường `event_time` để mô phỏng dữ liệu đến theo thời gian thực.
- **Consumer** (`kafka-console-consumer`, consumer group `hdfs_sink`): đọc toàn bộ topic và ghi vào HDFS.
- **Hive**: bảng external `ecommerce_warehouse.kafka_products_raw` đọc file JSON trên HDFS bằng `get_json_object`.

Kafka chạy ở chế độ **KRaft** (không cần ZooKeeper), khai báo trong `docker-compose.yml` (service `kafka`):
trong mạng docker dùng `kafka:9092`, từ Windows dùng `localhost:9094`.

## Cách chạy (Git Bash, tại thư mục project, cụm đang chạy)

```bash
pip install kafka-python
docker compose up -d kafka
bash kafka/run_kafka_demo.sh
```

Gửi chậm để quan sát luồng trực tiếp (mở thêm 1 terminal chạy consumer):

```bash
docker exec -it kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic products_stream
python kafka/producer.py --delay 0.2
```

## Minh chứng đã chạy (`logs/demo_kafka.txt`)

- Producer gửi **1239** tin nhắn: TGDD 535, CellphoneS 399, FPTShop 305.
- Consumer đọc lại đủ **1239** tin nhắn → `/user/root/kafka_stream/products.jsonl` trên HDFS.
- Hive đếm theo sàn trên dữ liệu đi qua Kafka khớp với MySQL/MR1.
- Partition 2 trống là bình thường: chỉ có 3 key (3 sàn) và Kafka chia partition theo hash của key,
  nên 2 sàn có thể rơi vào cùng 1 partition.
