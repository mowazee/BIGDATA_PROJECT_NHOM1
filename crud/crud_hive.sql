-- ======================================================================
-- MINH HỌA CRUD TRÊN HIVE (database ecommerce_warehouse)
--   docker exec -i hive-server beeline -u jdbc:hive2://localhost:10000 -f /dev/stdin < crud/crud_hive.sql
--   (hoặc dán từng câu vào Hue -> Editor -> Hive)
-- Hive 2.3 không bật ACID mặc định, nên dùng cách chuẩn của Hive:
--   CREATE = INSERT INTO ; UPDATE/DELETE = INSERT OVERWRITE (ghi lại bảng với dữ liệu đã sửa/lọc)
-- Bảng nguồn products_hive (external, trỏ vào dữ liệu Sqoop) KHÔNG bị thay đổi.
-- ======================================================================
USE ecommerce_warehouse;

-- Bảng managed để thao tác (sao chép một phần dữ liệu: điện thoại Samsung)
DROP TABLE IF EXISTS products_crud;
CREATE TABLE products_crud STORED AS TEXTFILE AS
SELECT id, source, brand, clean_name, CAST(original_price AS BIGINT) AS original_price,
       CAST(sale_price AS BIGINT) AS sale_price, discount_pct
FROM products_hive WHERE brand = 'Samsung';

SELECT 'TRUOC', COUNT(*) FROM products_crud;

-- C: CREATE
INSERT INTO TABLE products_crud VALUES
  (99999, 'TGDD', 'Samsung', 'Samsung Galaxy Demo CRUD 8GB/256GB', 10000000, 9000000, 10.0);
SELECT * FROM products_crud WHERE id = 99999;

-- R: READ
SELECT source, COUNT(*) AS so_sp, CAST(AVG(sale_price) AS BIGINT) AS gia_tb
FROM products_crud GROUP BY source;

-- U: UPDATE (ghi đè bảng, đổi giá của id 99999)
INSERT OVERWRITE TABLE products_crud
SELECT id, source, brand, clean_name, original_price,
       IF(id = 99999, CAST(8500000 AS BIGINT), sale_price),
       IF(id = 99999, ROUND((original_price - 8500000) / original_price * 100, 2), discount_pct)
FROM products_crud;
SELECT * FROM products_crud WHERE id = 99999;

-- D: DELETE (ghi đè bảng, bỏ id 99999)
INSERT OVERWRITE TABLE products_crud
SELECT * FROM products_crud WHERE id <> 99999;
SELECT 'SAU', COUNT(*) FROM products_crud;
