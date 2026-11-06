# Dashboard – Kết quả MapReduce (Nhóm 1)

Dashboard web trực quan hóa kết quả 8 bài toán MapReduce và dữ liệu sản phẩm đã làm sạch.
Không cần cài thêm thư viện: HTML + CSS + JavaScript thuần, biểu đồ dùng **Apache ECharts 5.5** (tải từ CDN).

## Cấu trúc thư mục

```
dashboard/
├── index.html              # Trang dashboard
├── build_data.py           # Chuyển kết quả MapReduce + CSV -> data/dashboard_data.js
├── data/
│   └── dashboard_data.js   # Dữ liệu cho dashboard (sinh tự động, không sửa tay)
├── assets/
│   ├── style.css           # Giao diện (sáng / tối)
│   └── app.js              # Vẽ biểu đồ, bộ lọc, bảng tra cứu
└── README.md
```

## Cách chạy

1. Chạy 8 bài MapReduce (trong container namenode):
   ```bash
   docker exec -it namenode bash
   bash /mapreduce_code/run_all_mr.sh
   ```
   Kết quả được lưu ra `mapreduce_code/results/MR1.txt … MR8.txt`.

2. Tạo file dữ liệu cho dashboard (tại thư mục project, trên Windows):
   ```bash
   python dashboard/build_data.py
   # hoặc đọc trực tiếp kết quả mới nhất trên HDFS:
   python dashboard/build_data.py --from-hdfs
   ```

3. Mở dashboard: nhấp đúp `dashboard/index.html`, hoặc chạy web server:
   ```bash
   python -m http.server 8000 --directory dashboard
   # mở http://localhost:8000
   ```
   Cần Internet để tải thư viện ECharts từ CDN lần đầu.

## Nội dung dashboard

| Khu vực | Nguồn | Dạng biểu đồ |
|---|---|---|
| Thẻ KPI | products_cleaned.csv, MR5 | Số liệu tổng quan |
| Số sản phẩm theo hãng & sàn | MR1 | Cột ngang chồng |
| Phân khúc giá | MR4 | Cột (thang màu thứ tự) |
| Khoảng giá theo hãng | MR2 | Range plot (min–max + chấm trung bình) |
| Mức giảm giá theo sàn | MR3 | Cột, chọn được 3 chỉ số |
| So sánh giá cùng mẫu máy giữa các sàn | MR5 | Dumbbell (chấm theo sàn) |
| Giá TB theo RAM × ROM | MR6 | Heatmap |
| Điểm & lượt đánh giá theo hãng | MR7 | Scatter / bubble (trục log) |
| Top 5 giảm giá theo hãng | MR8 | Cột ngang, chọn hãng |
| Tra cứu sản phẩm | products_cleaned.csv | Bảng tìm kiếm, lọc, sắp xếp |

Tính năng chung: lọc theo sàn (TGDĐ / CellphoneS / FPT Shop), tooltip khi rê chuột,
nút **Xem bảng** cho từng biểu đồ, giao diện sáng/tối, hiển thị tốt trên điện thoại.

Quy ước màu: mỗi sàn có một màu cố định (TGDĐ xanh dương, CellphoneS cam, FPT Shop xanh ngọc)
và giữ nguyên khi lọc; các biểu đồ theo độ lớn dùng một thang màu xanh dương nhạt → đậm.
