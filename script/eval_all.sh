#!/bin/bash

# 定义log文件夹路径和数据源路径
LOG_DIR="./log"
DATASOURCE_PATH="UCFE_bench.json"
RESULT_DIR="./res"

# 检查log文件夹是否存在
if [ ! -d "$LOG_DIR" ]; then
  echo "Log directory does not exist: $LOG_DIR"
  exit 1
fi

# 创建结果文件夹（如果不存在）
if [ ! -d "$RESULT_DIR" ]; then
  mkdir -p "$RESULT_DIR"
fi

# 获取log文件夹中的所有json文件列表
JSON_FILES=("$LOG_DIR"/*.json)

# 检查是否有足够的文件进行比较
if [ ${#JSON_FILES[@]} -lt 2 ]; then
  echo "Not enough model files to perform pairwise comparison"
  exit 1
fi

# 两两比较所有模型
for ((i=0; i<${#JSON_FILES[@]}; i++)); do
  TARGET_MODEL_PATH="${JSON_FILES[$i]}"
  TARGET_MODEL_NAME=$(basename "$TARGET_MODEL_PATH" .json)
  
  for ((j=i+1; j<${#JSON_FILES[@]}; j++)); do
    BASE_MODEL_PATH="${JSON_FILES[$j]}"
    BASE_MODEL_NAME=$(basename "$BASE_MODEL_PATH" .json)
    
    # 打印当前正在对比的模型
    echo "Comparing $TARGET_MODEL_NAME with $BASE_MODEL_NAME"
    
    # 调用Python评估脚本，执行两两对比
    python3 eval_elo.py \
      --target_model_path "$TARGET_MODEL_PATH" \
      --base_model_path "$BASE_MODEL_PATH" \
      --datasource_path "$DATASOURCE_PATH"
    
    # 检查评估是否成功
    if [ $? -eq 0 ]; then
      echo "Evaluation completed for $TARGET_MODEL_NAME vs $BASE_MODEL_NAME"
    else
      echo "Evaluation failed for $TARGET_MODEL_NAME vs $BASE_MODEL_NAME"
    fi
  done
done

echo "All pairwise evaluations completed."
