# Apache Zeppelin – Notebook phân tích trên Hive (công cụ ngoài chương trình)

Zeppelin là notebook web: mỗi đoạn (paragraph) là một truy vấn HiveQL chạy trên YARN, kết quả hiện thành
bảng hoặc biểu đồ (cột, tròn, đường…) ngay trên trình duyệt, chuyển kiểu biểu đồ bằng 1 cú nhấp.

- Giao diện: **http://localhost:8081** (cổng 8080 đã dùng cho Spark)
- Interpreter `hive` (nhóm JDBC) → `jdbc:hive2://hive-server:10000/ecommerce_warehouse`,
  driver `org.apache.hive:hive-jdbc:2.3.2` được Zeppelin tự tải từ Maven lần đầu (cần Internet).
- Notebook `notebook/Ecommerce_Hive_Analysis_*.zpln` được lưu trong repo (thư mục mount vào container).

## Nội dung notebook `Ecommerce_Hive_Analysis`

| Đoạn | Truy vấn | Biểu đồ |
|---|---|---|
| Giới thiệu | Markdown | – |
| Số sản phẩm theo sàn | `GROUP BY source` | Cột |
| Tỉ lệ sản phẩm theo phân khúc giá | `CASE WHEN sale_price …` | Tròn |
| Giá bán TB theo hãng | `AVG(sale_price) GROUP BY brand` | Cột |
| Giá TB theo dung lượng ROM và sàn | `GROUP BY storage_gb, source` | Đường |
| Top 10 giảm giá sâu nhất | `ORDER BY discount_pct DESC LIMIT 10` | Bảng |
| Dữ liệu đi qua Kafka | `get_json_object` trên `kafka_products_raw` | Cột |

## Cách chạy (Git Bash, tại thư mục project)

```bash
docker compose up -d zeppelin
bash zeppelin/setup_zeppelin.sh      # tạo interpreter hive + notebook; chạy lại mỗi khi container zeppelin bị tạo lại
```

Sau đó mở http://localhost:8081 → notebook **Ecommerce_Hive_Analysis** → nút ▶ **Run all paragraphs**.
Mỗi truy vấn là 1 job MapReduce trên YARN nên mất khoảng 1–2 phút/đoạn trên máy 2 nhân.

Yêu cầu: đã có bảng `ecommerce_warehouse.products_hive` (xem tài liệu nhóm, mục 4.4.1) và
`ecommerce_warehouse.kafka_products_raw` (tạo bởi `kafka/run_kafka_demo.sh`).
