#!/bin/bash

# --- 配置 ---
VIDEO_FILE="$1" # 從第一個參數讀取影片檔案路徑
BASE_NAME=$(basename "${VIDEO_FILE%.*}") # 提取不含副檔名的主檔名
TARGET_LANG="zh-TW" # 目標語言 (zh-TW 或 zh-CN)
SAMPLE_RATE=16000 # 音訊取樣率 (Hz)
ASR_MODEL="large-v3" # ASR 模型 (large-v3 + CTranslate2 INT8 加速)
# --- 結束配置 ---

# 檢查是否提供了影片檔案
if [ -z "$VIDEO_FILE" ]; then
  echo "錯誤：請提供影片檔案路徑作為參數。"
  echo "用法: ./run.sh /path/to/your_video.mp4"
  exit 1
fi

# 檢查 GEMINI_API_KEY（步驟 3 翻譯需要）
if [ -z "$GEMINI_API_KEY" ]; then
  echo "錯誤：請設定 GEMINI_API_KEY 環境變數（翻譯步驟需要）。"
  echo "  export GEMINI_API_KEY='your-api-key-here'"
  exit 1
fi

# --- 步驟 1: 音訊提取與頻率調整 ---
echo "=========================================="
echo "步驟 1: 提取音訊並調整頻率至 ${SAMPLE_RATE}Hz"
echo "=========================================="
python extract_audio.py "$VIDEO_FILE" -o "${BASE_NAME}.wav" -r "$SAMPLE_RATE"
if [ $? -ne 0 ]; then
  echo "錯誤：音訊提取失敗。"
  exit 1
fi

# --- 步驟 2: 本地模型轉錄 ---
echo ""
echo "=========================================="
echo "步驟 2: 使用 faster-whisper (${ASR_MODEL}) 轉錄音訊為逐字稿"
echo "=========================================="
python transcribe.py "${BASE_NAME}.wav" -o "${BASE_NAME}.ja.srt" -m "$ASR_MODEL"
if [ $? -ne 0 ]; then
  echo "錯誤：轉錄失敗。"
  exit 1
fi

# --- 步驟 3: 翻譯字幕 ---
echo ""
echo "=========================================="
echo "步驟 3: 翻譯日語字幕為${TARGET_LANG}"
echo "=========================================="
export INPUT_SRT_PATH="${BASE_NAME}.ja.srt"
export OUTPUT_SRT_PATH="${BASE_NAME}.${TARGET_LANG}.srt"
export TARGET_LANG_CODE="${TARGET_LANG}"

python translate_srt.py
if [ $? -ne 0 ]; then
  echo "錯誤：翻譯失敗。"
  exit 1
fi

echo ""
echo "=========================================="
echo "所有步驟已完成！"
echo "=========================================="
echo "日語字幕：${BASE_NAME}.ja.srt"
echo "中文字幕：${BASE_NAME}.${TARGET_LANG}.srt"
echo "將字幕檔與影片放在同一資料夾，VLC 會自動載入。"
