#!/bin/bash
# Cài python3 (cần cho Hadoop Streaming / MapReduce Python) vào namenode và nodemanager.
# Chạy lại script này mỗi khi 2 container trên bị TẠO LẠI (docker compose up sau khi đổi cấu hình,
# hoặc down rồi up). docker compose stop/start/restart thì KHÔNG cần chạy lại.
#   Cách chạy (Git Bash / WSL, tại thư mục project):  bash setup_python3.sh

for c in namenode nodemanager; do
  echo "=== $c ==="
  MSYS_NO_PATHCONV=1 docker exec "$c" bash -c '
    if command -v python3 >/dev/null; then echo "da co: $(python3 --version)"; exit 0; fi
    # Debian Stretch đã hết hỗ trợ -> chuyển kho apt sang archive.debian.org
    sed -i "s/deb.debian.org/archive.debian.org/g" /etc/apt/sources.list
    sed -i "s|security.debian.org|archive.debian.org|g" /etc/apt/sources.list
    sed -i "/stretch-updates/d" /etc/apt/sources.list
    apt-get update -qq && apt-get install -y -qq python3 >/dev/null && python3 --version
  '
done
