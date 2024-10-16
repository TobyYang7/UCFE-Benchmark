#!/bin/bash

# 定义log文件夹路径和数据源路径
LOG_DIR="./log"
DATASOURCE_PATH="UCFE_bench.json"
RESULT_DIR="./res"

# 获取目标模型名称作为参数
TARGET_MODEL=20241012_005605_Meta-Llama-3.1-70B-Instruct_eng.json
if [ ! -f "$LOG_DIR/$TARGET_MODEL" ]; then
  cp "./log/$TARGET_MODEL" "$LOG_DIR"
fi

# 检查是否提供了目标模型
if [ -z "$TARGET_MODEL" ]; then
  echo "Please specify a target model."
  exit 1
fi

# 检查log文件夹是否存在
if [ ! -d "$LOG_DIR" ]; then
  echo "Log directory does not exist: $LOG_DIR"
  exit 1
fi

# 检查目标模型文件是否存在
TARGET_MODEL_PATH="$LOG_DIR/$TARGET_MODEL"
if [ ! -f "$TARGET_MODEL_PATH" ]; then
  echo "Target model file does not exist: $TARGET_MODEL_PATH"
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

# 让目标模型与其他所有模型进行比较
for ((j=0; j<${#JSON_FILES[@]}; j++)); do
  BASE_MODEL_PATH="${JSON_FILES[$j]}"
  BASE_MODEL_NAME=$(basename "$BASE_MODEL_PATH" .json)
  
  # 跳过与自身的比较
  if [ "$BASE_MODEL_NAME" == "$TARGET_MODEL" ]; then
    continue
  fi
  
  # 打印当前正在对比的模型
  echo -e "\e[32mComparing $TARGET_MODEL with $BASE_MODEL_NAME\e[0m"
  
  # 调用Python评估脚本，执行两两对比
  python3 eval_elo.py \
    --target_model_path "$TARGET_MODEL_PATH" \
    --base_model_path "$BASE_MODEL_PATH" \
    --datasource_path "$DATASOURCE_PATH"
  
  # 检查评估是否成功
  if [ $? -eq 0 ]; then
    echo -e "\e[32mEvaluation completed for $TARGET_MODEL vs $BASE_MODEL_NAME\e[0m"
  else
    echo -e "\e[31mEvaluation failed for $TARGET_MODEL vs $BASE_MODEL_NAME\e[0m"
  fi
done


echo -e "\e[32mAll pairwise evaluations completed.\e[0m"
