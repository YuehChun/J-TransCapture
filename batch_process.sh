#!/bin/bash
set -e

# 載入 .env
export $(grep -v '^#' .env | xargs)

FILES=(
  "FSDSS-703"
  "SONE-247"
  "200GANA-3001"
  "8192 TG频道@TBBAD"
  "FC25月素人最佳新片抢先看"
)

for f in "${FILES[@]}"; do
  DIR="translate/${f}"
  echo ""
  echo "=========================================="
  echo "處理: ${f}"
  echo "=========================================="

  # 如果 .ja.srt 已存在則跳過轉錄
  if [ -f "${DIR}/${f}.ja.srt" ]; then
    echo "[1/2] 轉錄已存在，跳過"
  else
    echo "[1/2] 轉錄中..."
    python transcribe.py "${DIR}/${f}.wav" -o "${DIR}/${f}.ja.srt" -m large-v3
  fi

  # 如果 .zh-TW.srt 已存在則跳過翻譯
  if [ -f "${DIR}/${f}.zh-TW.srt" ]; then
    echo "[2/2] 翻譯已存在，跳過"
  else
    echo "[2/2] 翻譯中..."
    export INPUT_SRT_PATH="${DIR}/${f}.ja.srt"
    export OUTPUT_SRT_PATH="${DIR}/${f}.zh-TW.srt"
    export TARGET_LANG_CODE="zh-TW"
    python translate_srt.py
  fi

  echo "完成: ${DIR}/${f}.zh-TW.srt"
  echo ""
done

echo "=========================================="
echo "全部完成！"
echo "=========================================="
