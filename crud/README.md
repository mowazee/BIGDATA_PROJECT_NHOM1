# Truy vấn & thao tác dữ liệu (CRUD)

| Hệ thống | File | C – Create | R – Read | U – Update | D – Delete |
|---|---|---|---|---|---|
| MySQL `ecommerce_db.products` | `crud_mysql.sql` | `INSERT` | `SELECT … GROUP BY / ORDER BY` | `UPDATE` | `DELETE` |
| Hive `ecommerce_warehouse.products_crud` | `crud_hive.sql` | `INSERT INTO` | `SELECT … GROUP BY` | `INSERT OVERWRITE` (ghi lại bảng đã sửa) | `INSERT OVERWRITE` (ghi lại bảng đã lọc) |

Cả hai script dùng một sản phẩm thử nghiệm `id = 99999` và xóa nó ở cuối, nên dữ liệu thật không thay đổi.
Hive 2.3 không bật ACID mặc định nên `UPDATE/DELETE` được làm theo cách chuẩn của Hive là `INSERT OVERWRITE`.

## Cách chạy (Git Bash, tại thư mục project)

```bash
docker exec -i mysql-db mysql -uroot -proot -t --default-character-set=utf8mb4 < crud/crud_mysql.sql
MSYS_NO_PATHCONV=1 docker cp crud/crud_hive.sql hive-server:/tmp/crud_hive.sql
MSYS_NO_PATHCONV=1 docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -f /tmp/crud_hive.sql
```

Hoặc dán từng câu lệnh vào **Hue → Editor → Hive** để chụp màn hình cho báo cáo.

## Minh chứng đã chạy

- `logs/crud_mysql_output.txt`
- `logs/crud_hive_output.txt`
