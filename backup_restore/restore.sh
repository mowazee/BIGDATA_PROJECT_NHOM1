#!/bin/bash
# PHỤC HỒI dữ liệu dự án từ một bản sao lưu do backup.sh tạo ra.
#   bash backup_restore/restore.sh               # dùng bản sao lưu mới nhất
#   bash backup_restore/restore.sh 20261106_1300 # dùng bản sao lưu chỉ định
#   bash backup_restore/restore.sh <ma> --snapshot   # khôi phục HDFS từ snapshot thay vì từ file trên máy
set -e
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."

TS=${1:-$(ls shared_data/backups 2>/dev/null | sort | tail -n 1)}
MODE=$2
HOST_DIR="shared_data/backups/$TS"
CT_DIR="/shared_data/backups/$TS"
HDFS_DATA=/user/hadoop/hive/warehouse/products
if [ -z "$TS" ] || [ ! -f "$HOST_DIR/ecommerce_db.sql" ]; then
  echo "Khong tim thay ban sao luu '$TS' trong shared_data/backups/"; exit 1
fi
echo "Khoi phuc tu ban sao luu: $TS"

echo "=== [1/2] Phục hồi MySQL ==="
docker exec -i mysql-db sh -c "mysql -uroot -proot 2>/dev/null" < "$HOST_DIR/ecommerce_db.sql"
docker exec mysql-db sh -c "mysql -uroot -proot -N -e 'SELECT CONCAT(\"    -> ecommerce_db.products: \", COUNT(*), \" dong\") FROM ecommerce_db.products' 2>/dev/null"

echo "=== [2/2] Phục hồi HDFS ==="
if [ "$MODE" = "--snapshot" ]; then
  # Chép đè từ snapshot (dữ liệu snapshot chỉ đọc nằm trong .snapshot/)
  docker exec namenode bash -c "
    hdfs dfs -rm -f -skipTrash $HDFS_DATA/part-* >/dev/null 2>&1
    hdfs dfs -cp $HDFS_DATA/.snapshot/snap_$TS/part-* $HDFS_DATA/ 2>/dev/null"
else
  # Thư mục có snapshot thì không xóa được -> chỉ xóa file bên trong rồi đưa file từ bản sao lưu lên lại
  docker exec namenode bash -c "
    hdfs dfs -mkdir -p $HDFS_DATA
    hdfs dfs -rm -f -skipTrash $HDFS_DATA/part-* >/dev/null 2>&1
    hdfs dfs -put -f $CT_DIR/hdfs_products/part-* $HDFS_DATA/ 2>/dev/null
    for d in $CT_DIR/hdfs_mr_output/*; do
      [ -d \"\$d\" ] || continue
      n=\$(basename \$d); hdfs dfs -rm -r -f -skipTrash /user/root/\$n >/dev/null 2>&1
      hdfs dfs -put \$d /user/root/\$n 2>/dev/null
    done"
fi
docker exec namenode bash -c "echo \"    -> HDFS $HDFS_DATA: \$(hdfs dfs -cat $HDFS_DATA/part-* 2>/dev/null | wc -l) dong\""
echo "HOAN TAT."
