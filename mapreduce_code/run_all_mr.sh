#!/bin/bash
# Chạy lần lượt 8 bài toán MapReduce bằng Hadoop Streaming trên YARN (chạy bên trong container namenode)
#   docker exec -it namenode bash
#   bash /mapreduce_code/run_all_mr.sh            # chạy cả 8 bài
#   bash /mapreduce_code/run_all_mr.sh 5          # chỉ chạy MR5
#   bash /mapreduce_code/run_all_mr.sh "2 6"      # chạy MR2 và MR6
# Yêu cầu: container nodemanager phải có python3 (map/reduce chạy trên nodemanager).

INPUT=${INPUT:-/user/hadoop/hive/warehouse/products}     # thư mục Sqoop đã import
OUT_BASE=${OUT_BASE:-/user/root/mr_output}
CODE=/mapreduce_code
HADOOP_HOME=${HADOOP_HOME:-/opt/hadoop-3.2.1}
STREAMING_JAR=$(ls $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar 2>/dev/null | head -n 1)

# Chuyển CRLF (Windows) -> LF (Linux) và cấp quyền chạy
sed -i 's/\r$//' $CODE/mapper.py $CODE/reducer.py
chmod +x $CODE/mapper.py $CODE/reducer.py
mkdir -p $CODE/results

TASKS=${1:-"1 2 3 4 5 6 7 8"}
for i in $TASKS; do
  echo "================ DANG CHAY MR$i ================"
  hdfs dfs -rm -r -f -skipTrash ${OUT_BASE}_$i > /dev/null 2>&1

  # MR1, MR4 là phép đếm -> dùng reducer làm combiner để giảm dữ liệu shuffle
  COMBINER=()
  if [ "$i" = "1" ] || [ "$i" = "4" ]; then
    COMBINER=(-combiner "python3 reducer.py")
  fi

  # Job chạy trên YARN nhờ cấu hình MAPRED_CONF_* của service namenode trong docker-compose.yml
  # (theo dõi tại YARN UI http://localhost:8088)
  hadoop jar "$STREAMING_JAR" \
    -D mapreduce.job.name="Ecommerce_MR$i" \
    -D mapreduce.job.reduces=1 \
    -files $CODE/mapper.py,$CODE/reducer.py \
    -cmdenv MR_TASK=MR$i \
    -cmdenv PYTHONIOENCODING=utf-8 \
    -mapper "python3 mapper.py" \
    "${COMBINER[@]}" \
    -reducer "python3 reducer.py" \
    -input $INPUT \
    -output ${OUT_BASE}_$i

  echo "---------------- KET QUA MR$i ----------------"
  # Lưu 1 bản ra thư mục chia sẻ với Windows (mapreduce_code/results) để làm báo cáo / dashboard
  hdfs dfs -cat ${OUT_BASE}_$i/part-* > $CODE/results/MR$i.txt
  head -n 20 $CODE/results/MR$i.txt
done
