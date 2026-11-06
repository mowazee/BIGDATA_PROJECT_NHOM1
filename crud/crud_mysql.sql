-- ======================================================================
-- MINH HỌA CRUD TRÊN MYSQL (ecommerce_db.products)
--   docker exec -i mysql-db mysql -uroot -proot -t < crud/crud_mysql.sql
-- Dùng 1 sản phẩm thử nghiệm id = 99999, cuối script xóa đi -> dữ liệu thật không đổi.
-- ======================================================================
USE ecommerce_db;

SELECT '--- 0. Trước khi thao tác ---' AS buoc;
SELECT COUNT(*) AS tong_san_pham FROM products;

-- C: CREATE (thêm mới)
SELECT '--- 1. CREATE: thêm sản phẩm thử nghiệm ---' AS buoc;
INSERT INTO products (id, source, category, brand, raw_name, clean_name, ram_gb, storage_gb,
                      original_price, sale_price, discount_pct, rating, review_count)
VALUES (99999, 'TGDD', 'Phone', 'Samsung', 'Samsung Galaxy Demo CRUD 8GB/256GB',
        'Samsung Galaxy Demo CRUD 8GB/256GB (Đen)', 8, 256, 10000000, 9000000, 10.0, 4.5, 12);
SELECT id, source, brand, clean_name, original_price, sale_price, discount_pct
FROM products WHERE id = 99999;

-- R: READ (truy vấn)
SELECT '--- 2. READ: truy vấn thống kê theo sàn ---' AS buoc;
SELECT source, COUNT(*) AS so_sp, ROUND(AVG(sale_price)) AS gia_tb, ROUND(AVG(discount_pct), 2) AS giam_tb
FROM products GROUP BY source ORDER BY so_sp DESC;

SELECT '--- 2b. READ: 5 sản phẩm Apple rẻ nhất ---' AS buoc;
SELECT id, source, clean_name, sale_price FROM products
WHERE brand = 'Apple' ORDER BY sale_price ASC LIMIT 5;

-- U: UPDATE (cập nhật giá khuyến mãi, tính lại % giảm)
SELECT '--- 3. UPDATE: giảm giá xuống 8.500.000 ---' AS buoc;
UPDATE products
SET sale_price = 8500000,
    discount_pct = ROUND((original_price - 8500000) / original_price * 100, 2)
WHERE id = 99999;
SELECT id, clean_name, original_price, sale_price, discount_pct FROM products WHERE id = 99999;

-- D: DELETE (xóa)
SELECT '--- 4. DELETE: xóa sản phẩm thử nghiệm ---' AS buoc;
DELETE FROM products WHERE id = 99999;
SELECT COUNT(*) AS con_lai_id_99999 FROM products WHERE id = 99999;
SELECT COUNT(*) AS tong_san_pham FROM products;
