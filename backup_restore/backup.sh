#!/bin/bash
# SAO LƯU dữ liệu dự án (MySQL + HDFS).
#   Cách chạy (Git Bash / WSL, tại thư mục project):  bash backup_restore/backup.sh
# Kết quả: shared_data/backups/<thời_gian>/
#   - ecommerce_db.sql : bản dump MySQL (cấu trúc + dữ liệu bảng products)
#   - hdfs_products/   : bản sao thư mục Sqoop trên HDFS (/user/hadoop/hive/warehouse/products)
#   - hdfs_mr_output/  : bản sao kết quả 8 bài MapReduce trên HDFS
# Đồng thời tạo HDFS snapshot (khôi phục nhanh ngay trên HDFS, không cần copy ra ngoài).
set -e
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."

TS=$(date +%Y%m%d_%H%M%S)
HOST_DIR="shared_data/backups/$TS"      # trên Windows
CT_DIR="/shared_data/backups/$TS"       # cùng thư mục đó, nhìn từ container namenode
DB=ecommerce_db
HDFS_DATA=/user/hadoop/hive/warehouse/products
mkdir -p "$HOST_DIR"

echo "=== [1/3] Sao lưu MySQL ($DB) ==="
docker exec mysql-db sh -c "mysqldump -uroot -proot --single-transaction --routines --databases $DB 2>/dev/null" > "$HOST_DIR/ecommerce_db.sql"
echo "    -> $HOST_DIR/ecommerce_db.sql ($(wc -c < "$HOST_DIR/ecommerce_db.sql") bytes)"

echo "=== [2/3] Sao lưu HDFS ra máy (hdfs dfs -get) ==="
docker exec namenode bash -c "
  hdfs dfs -get $HDFS_DATA $CT_DIR/hdfs_products 2>/dev/null
  mkdir -p $CT_DIR/hdfs_mr_output
  for d in \$(hdfs dfs -ls -C /user/root 2>/dev/null | grep mr_output_); do
    hdfs dfs -get \$d $CT_DIR/hdfs_mr_output/ 2>/dev/null
  done
  echo \"    -> \$(cat $CT_DIR/hdfs_products/part-* | wc -l) dong du lieu, \$(ls $CT_DIR/hdfs_mr_output | wc -l) thu muc ket qua MR\""

echo "=== [3/3] Tạo HDFS snapshot ==="
docker exec namenode bash -c "
  hdfs dfsadmin -allowSnapshot $HDFS_DATA >/dev/null 2>&1
  hdfs dfs -createSnapshot $HDFS_DATA snap_$TS 2>/dev/null
  hdfs dfs -ls $HDFS_DATA/.snapshot 2>/dev/null | tail -n +2 | awk '{print \"    -> \" \$NF}'"

echo "HOAN TAT. Ma ban sao luu: $TS"
echo "Khoi phuc bang:  bash backup_restore/restore.sh $TS"
