# Sao lưu & Phục hồi dữ liệu (Backup / Restore)

Sao lưu cả 2 nơi lưu dữ liệu của dự án: **MySQL** (`ecommerce_db`) và **HDFS** (dữ liệu Sqoop + kết quả MapReduce).

| Thành phần | Cách sao lưu | Cách phục hồi |
|---|---|---|
| MySQL `ecommerce_db` | `mysqldump` → file `.sql` | `mysql < ecommerce_db.sql` |
| HDFS `/user/hadoop/hive/warehouse/products` | `hdfs dfs -get` ra máy + **HDFS Snapshot** | `hdfs dfs -put` từ máy, hoặc chép lại từ `.snapshot/` |
| HDFS `/user/root/mr_output_1..8` | `hdfs dfs -get` ra máy | `hdfs dfs -put` |

Bản sao lưu nằm ở `shared_data/backups/<thời_gian>/` (thư mục này được mount vào container `namenode` tại `/shared_data`).

## Cách chạy (Git Bash, tại thư mục project, cụm đang chạy)

```bash
bash backup_restore/backup.sh                         # tạo bản sao lưu mới
bash backup_restore/restore.sh                        # phục hồi từ bản mới nhất
bash backup_restore/restore.sh 20261106_131329        # phục hồi từ bản chỉ định
bash backup_restore/restore.sh 20261106_131329 --snapshot   # HDFS phục hồi từ snapshot
```

## Minh chứng đã chạy

- `logs/demo_backup_restore.txt`: sao lưu → xóa dữ liệu TGDD trong MySQL (980 → 591 dòng) và xóa dữ liệu HDFS (980 → 0) → phục hồi (MySQL 980, HDFS 980).
- `logs/demo_restore_snapshot.txt`: xóa dữ liệu HDFS → phục hồi từ HDFS snapshot → 980 dòng.

Xem snapshot trên giao diện: Hue → Files → `/user/hadoop/hive/warehouse/products/.snapshot`,
hoặc NameNode UI http://localhost:9870 → Utilities → Browse the file system.
