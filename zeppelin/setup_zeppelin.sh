#!/bin/bash
# Cấu hình Apache Zeppelin (http://localhost:8081) để truy vấn Hive và tạo notebook phân tích có biểu đồ.
#   Cách chạy (Git Bash, tại thư mục project):  docker compose up -d zeppelin && bash zeppelin/setup_zeppelin.sh
# Notebook được lưu ở zeppelin/notebook/ (mount vào container) nên giữ lại sau khi tạo lại container.
set -e
Z=${ZEPPELIN_URL:-http://localhost:8081}
NB_NAME="Ecommerce_Hive_Analysis"

echo "Cho Zeppelin khoi dong..."
for i in $(seq 1 60); do curl -sf "$Z/api/version" >/dev/null && break; sleep 5; done
curl -sf "$Z/api/version" | sed 's/.*"version":"\([^"]*\)".*/Zeppelin \1/'

echo "=== [1/3] Tao interpreter 'hive' (JDBC -> hive-server:10000) ==="
OLD=$(curl -s "$Z/api/interpreter/setting" | grep -o '"id":"[^"]*","name":"hive"' | sed 's/"id":"\([^"]*\)".*/\1/' || true)
[ -n "$OLD" ] && curl -s -X DELETE "$Z/api/interpreter/setting/$OLD" >/dev/null
curl -s -X POST "$Z/api/interpreter/setting" -H 'Content-Type: application/json' -d '{
  "name": "hive", "group": "jdbc",
  "properties": {
    "default.url":    {"name": "default.url",    "value": "jdbc:hive2://hive-server:10000/ecommerce_warehouse", "type": "string"},
    "default.driver": {"name": "default.driver", "value": "org.apache.hive.jdbc.HiveDriver", "type": "string"},
    "default.user":   {"name": "default.user",   "value": "root", "type": "string"},
    "default.password": {"name": "default.password", "value": "", "type": "password"},
    "common.max_count": {"name": "common.max_count", "value": "1000", "type": "number"}
  },
  "dependencies": [
    {"groupArtifactVersion": "org.apache.hive:hive-jdbc:2.3.2", "exclusions": ["org.apache.hive:hive-shims", "org.eclipse.jetty.aggregate:*", "org.apache.logging.log4j:*"]},
    {"groupArtifactVersion": "org.apache.hadoop:hadoop-common:2.7.3", "exclusions": ["*:*:jsp-api", "javax.servlet:*", "org.mortbay.jetty:*", "com.sun.jersey:*"]}
  ],
  "option": {"remote": true, "isExistingProcess": false, "perNote": "shared", "perUser": "shared", "isUserImpersonate": false}
}' | grep -o '"status":"[A-Z]*"'

# Zeppelin tải driver Hive JDBC từ Maven ở nền -> đợi tới khi interpreter READY rồi mới chạy notebook
echo "    Doi tai driver Hive JDBC..."
for i in $(seq 1 90); do
  st=$(curl -s "$Z/api/interpreter/setting" | grep -o '"name":"hive","group":"jdbc"[^}]*' | grep -o '"status":"[A-Z_]*"' | head -1)
  [ -z "$st" ] && st=$(curl -s "$Z/api/interpreter/setting" | tr '{' '\n' | grep -A0 '"name":"hive"' | grep -o '"status":"[A-Z_]*"' | head -1)
  case "$st" in *READY*) echo "    -> $st"; break;; *ERROR*) echo "    -> $st"; break;; esac
  sleep 5
done

echo "=== [2/3] Tao notebook $NB_NAME ==="
OLDNB=$(curl -s "$Z/api/notebook" | grep -o "\"id\":\"[^\"]*\",\"path\":\"/$NB_NAME\"" | sed 's/"id":"\([^"]*\)".*/\1/' || true)
[ -n "$OLDNB" ] && curl -s -X DELETE "$Z/api/notebook/$OLDNB" >/dev/null
bar='{"results": {"0": {"graph": {"mode": "multiBarChart"}}}}'
pie='{"results": {"0": {"graph": {"mode": "pieChart"}}}}'
line='{"results": {"0": {"graph": {"mode": "lineChart"}}}}'
tbl='{"results": {"0": {"graph": {"mode": "table"}}}}'
NB=$(curl -s -X POST "$Z/api/notebook" -H 'Content-Type: application/json' -d "{
  \"name\": \"$NB_NAME\",
  \"paragraphs\": [
    {\"title\": \"Gioi thieu\", \"text\": \"%md\\n## Phan tich gia dien thoai 3 san (TGDD, CellphoneS, FPTShop)\\nDu lieu: bang Hive **ecommerce_warehouse.products_hive** (Sqoop tu MySQL len HDFS). Moi doan ben duoi la 1 truy van HiveQL chay tren YARN.\"},
    {\"title\": \"So san pham theo san\", \"text\": \"%hive\\nSELECT source, COUNT(*) AS so_san_pham FROM products_hive GROUP BY source\", \"config\": $bar},
    {\"title\": \"Ti le san pham theo phan khuc gia\", \"text\": \"%hive\\nSELECT CASE WHEN sale_price < 7000000 THEN '1. Gia re (<7tr)' WHEN sale_price <= 15000000 THEN '2. Tam trung (7-15tr)' WHEN sale_price <= 25000000 THEN '3. Can cao cap (15-25tr)' ELSE '4. Cao cap (>25tr)' END AS phan_khuc, COUNT(*) AS so_luong FROM products_hive GROUP BY CASE WHEN sale_price < 7000000 THEN '1. Gia re (<7tr)' WHEN sale_price <= 15000000 THEN '2. Tam trung (7-15tr)' WHEN sale_price <= 25000000 THEN '3. Can cao cap (15-25tr)' ELSE '4. Cao cap (>25tr)' END\", \"config\": $pie},
    {\"title\": \"Gia ban trung binh theo hang (trieu dong)\", \"text\": \"%hive\\nSELECT brand, ROUND(AVG(sale_price)/1000000, 2) AS gia_tb_trieu FROM products_hive GROUP BY brand ORDER BY gia_tb_trieu DESC\", \"config\": $bar},
    {\"title\": \"Gia trung binh theo dung luong ROM va san\", \"text\": \"%hive\\nSELECT storage_gb, source, ROUND(AVG(sale_price)/1000000, 2) AS gia_tb_trieu FROM products_hive WHERE storage_gb > 0 GROUP BY storage_gb, source ORDER BY storage_gb\", \"config\": $line},
    {\"title\": \"Top 10 san pham giam gia sau nhat\", \"text\": \"%hive\\nSELECT source, clean_name, CAST(original_price AS BIGINT) AS gia_goc, CAST(sale_price AS BIGINT) AS gia_ban, discount_pct FROM products_hive ORDER BY discount_pct DESC LIMIT 10\", \"config\": $tbl},
    {\"title\": \"Du lieu di qua Kafka (bang kafka_products_raw)\", \"text\": \"%hive\\nSELECT get_json_object(json, '\$.source') AS source, COUNT(*) AS so_tin_nhan FROM kafka_products_raw GROUP BY get_json_object(json, '\$.source')\", \"config\": $bar}
  ]}")
NB_ID=$(echo "$NB" | sed 's/.*"body":"\([^"]*\)".*/\1/')
echo "    -> notebook id: $NB_ID"

echo "=== [3/3] Chay toan bo notebook (moi truy van la 1 job tren YARN, co the mat vai phut) ==="
curl -s -X POST "$Z/api/notebook/job/$NB_ID?blocking=true" >/dev/null || true
curl -s "$Z/api/notebook/job/$NB_ID" | grep -o '"status":"[A-Z]*"' | sort | uniq -c
echo "Mo notebook: $Z/#/notebook/$NB_ID"
