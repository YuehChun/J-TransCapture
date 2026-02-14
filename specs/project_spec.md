# 專案規格書：日語影片轉中文SRT字幕產生器

## 1. 專案目標 (Objective)

本專案的目標是建立一個標準化流程（或自動化腳本），將包含日語對話的 MP4 影片檔案，轉換為可供 VLC 等播放器使用的繁體中文 (zh-TW) 或簡體中文 (zh-CN) 的 `.srt` 字幕檔案。

## 2. 核心流程 (Core Workflow)

如你所定義，流程分為三個主要階段：

1.  **音訊提取 (Audio Extraction)**：從 MP4 檔案中分離出音訊，並將其轉換為 AI 模型易於處理的格式（如 16kHz 的
    單聲道 WAV）。
2.  **轉錄與翻譯 (Transcription & Translation)**：
      * **2a. 語音轉文字 (ASR)**：使用 AI 模型將日語音訊轉錄為帶有時間戳的日語字幕。
      * **2b. 機器翻譯 (MT)**：將日語字幕翻譯為中文。
3.  **播放與驗證 (Playback)**：將原始 MP4 影片與新生成的中文 `.srt` 字幕檔在 VLC 中一同播放。

## 3. 技術棧 (Technical Stack)

| 任務 | 推薦工具 | 備註 |
| :--- | :--- | :--- |
| **音訊提取** | `FFmpeg` | 跨平台、開源的音影片處理工具，必備。 |
| **語音轉錄 (ASR)** | `OpenAI Whisper` | 目前最強大的開源 ASR 模型之一，能處理日語並生成高質量的時間戳。 |
| **機器翻譯 (MT)** | **選項A (推薦):** `DeepL` / `Google Cloud Translation API` <br> **選項B (免費):** `LLM` (如 GPT-4, Claude 3, Gemini) | 選項A 質量高且易於自動化。 <br> 選項B 需手動複製貼上，或編寫更複雜的 API 腳本。 |
| **腳本語言 (自動化)** | `Python` 或 `Bash Shell` | Python 用於串接 API；Bash 用於執行簡單的 CLI 命令。 |
| **播放器** | `VLC Media Player` | 如你所指定。 |

## 4. 詳細執行步驟 (Detailed Implementation)

這部分將詳細說明每個步驟的具體指令和操作。

### 步驟 1：音訊提取 (使用 FFmpeg)

這是你的第一步。我們需要將 MP4 轉為 `WAV` 格式，因為 `WAV` 是未壓縮的，最適合 ASR 模型。

  * **安裝：** 確保你的系統已安裝 `FFmpeg`。
  * **指令：**
    ```bash
    # -i: 輸入檔案
    # -vn: (Video No) 移除影片軌
    # -ar 16000: (Audio Rate) 設置採樣率為 16kHz (Whisper 的標準)
    # -ac 1: (Audio Channels) 設置為單聲道 (Mono)
    # -c:a pcm_s16le: (Codec Audio) 存為標準的 16-bit PCM WAV 格式

    ffmpeg -i "your_video.mp4" -vn -ar 16000 -ac 1 -c:a pcm_s16le "audio.wav"
    ```
  * **輸出：** 一個名為 `audio.wav` 的音訊檔案。

### 步驟 2：轉錄與翻譯 (核心步驟)

這是你的第二步。這個步驟最為關鍵，我們需要將 `audio.wav` 轉為中文 `.srt`。

**方法 A：Whisper 直接轉錄 (獲取日語 SRT)**

我們首先使用 Whisper 將日語語音轉錄為 *日語* 字幕。

  * **安裝：** `pip install openai-whisper`
  * **指令：**
    ```bash
    # "audio.wav": 輸入的音訊檔
    # --language Japanese: 明確指定語言為日語，提高準確性
    # --model large: 使用大型模型以獲得最佳質量 (也可選 medium, base)
    # --task transcribe: 執行「轉錄」任務
    # --output_format srt: 輸出為 SRT 格式

    whisper "audio.wav" --language Japanese --model large --task transcribe --output_format srt
    ```
  * **輸出：** 一個 `audio.srt` 檔案。此檔案內容是*日語*，但時間戳已完美對齊。

**方法 B：將日語 SRT 翻譯為中文 SRT (自動化腳本)**

現在我們需要翻譯 `audio.srt`。手動複製貼上非常耗時，我們可以用 Python 腳本來自動化。

你需要安裝一個用於解析 SRT 的函式庫和一個翻譯 API 函式庫。

1.  **安裝依賴：**

    ```bash
    pip install srt
    pip install google-cloud-translate-v2 # 範例：使用 Google Translate API
    # 或者 pip install deepl # 範例：使用 DeepL API
    ```

2.  **Python 腳本 (translate_srt.py)：**
    這是一個使用 Google Translate API 的範例腳本。

    ```python
    import srt
    from google.cloud import translate_v2 as translate
    import os

    # --- 配置 ---
    # 1. 設置你的 Google Cloud API Key
    #    你需要在終端機執行: export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/your-key.json" 

    # 2. 檔案和語言
    INPUT_SRT = "audio.srt"      # Whisper 產生的日語 SRT
    OUTPUT_SRT = "audio.zh-TW.srt" # 最終的中文 SRT
    SOURCE_LANG = "ja"           # 來源語言：日語
    TARGET_LANG = "zh-TW"        # 目標語言：繁體中文 (或 "zh-CN" 簡體中文)
    # --- 結束配置 ---

    def translate_text(text, target_language, source_language):
        """調用 API 進行翻譯"""
        try:
            client = translate.Client()
            result = client.translate(text, target_language=target_language, source_language=source_language)
            return result['translatedText']
        except Exception as e:
            print(f"Error during translation: {e}")
            return text # 翻譯失敗時返回原文

    def process_srt_file():
        """讀取、翻譯並保存 SRT 檔案"""
        try:
            with open(INPUT_SRT, 'r', encoding='utf-8') as f:
                subtitle_generator = srt.parse(f.read())
                subtitles = list(subtitle_generator)
            
            print(f"Loaded {len(subtitles)} subtitle entries.")
            
            # 遍歷所有字幕條目並翻譯
            for sub in subtitles:
                original_text = sub.content
                translated_text = translate_text(original_text, TARGET_LANG, SOURCE_LANG)
                sub.content = translated_text
                print(f"JA: {original_text} 
=> {TARGET_LANG}: {translated_text}\n")
            
            # 將翻譯後的字幕內容寫入新檔案
            final_srt_content = srt.compose(subtitles)
            with open(OUTPUT_SRT, 'w', encoding='utf-8') as f:
                f.write(final_srt_content)
                
            print(f"Successfully translated and saved to {OUTPUT_SRT}")

        except FileNotFoundError:
            print(f"Error: Input file '{INPUT_SRT}' not found.")
        except Exception as e:
            print(f"An error occurred: {e}")

    if __name__ == "__main__":
        process_srt_file()

    ```

**替代方案 (免費但手動)：**
如果你不想設定 API，你可以：

1.  執行 `whisper "audio.wav" --language Japanese --model large --task transcribe --output_format txt` 獲取純日文 `audio.txt`。
2.  將 `audio.txt` 的全部內容貼到 ChatGPT / Gemini / Claude。
3.  **使用提示詞 (Prompt)：** "請將以下日文文本翻譯為繁體中文，保持原有的斷行。"
4.  這無法生成 `.srt`，只能得到純文本。**因此，翻譯 `.srt` 檔案的 Python 腳本（方法B）是最佳選擇。**

### 步驟 3：播放與驗證 (使用 VLC)

這是你的第三步，也是最後的驗證。

1.  **檔案命名 (重要)：** 為了讓 VLC 自動載入字幕，請確保 MP4 檔案和 SRT 檔案的**主檔名相同**。

      * 影片檔： `your_video.mp4`
      * 字幕檔： `your_video.zh-TW.srt` (VLC 會識別 `zh-TW` 語言標籤)

2.  **播放：**

      * 將這兩個檔案放在同一個資料夾中。
      * 用 VLC 開啟 `your_video.mp4`。
      * VLC 應該會自動偵測並載入 `your_video.zh-TW.srt`。
      * 如果沒有，手動點擊 `字幕 (Subtitle) > 新增字幕軌 (Add Subtitle File...)` 並選擇你的 `.srt` 檔案。

## 5. 專案交付成果 (Deliverables)

1.  `audio.wav`：從 MP4 提取的 16kHz 單聲道音訊。
2.  `audio.srt`：(中間產物) 由 Whisper 生成的日語源字幕檔案。
3.  `audio.zh-TW.srt`：(最終產物) 經翻譯後的繁體中文字幕檔案。

## 6. 潛在挑戰與注意事項 (Considerations)

  * **處理速度：** Whisper 的 `large` 模型需要強大的 GPU (如 NVIDIA VRAM > 8GB) 才能快速運行。如果使用 CPU，一個小時的影片可能需要數十分鐘甚至數小時來轉錄。
  * **翻譯質量：** API 的機器翻譯可能無法完美處理專業術語、雙關語或強烈的情感語氣。
  * **API 成本：** Google Translate 或 DeepL API 是收費服務，按翻譯的字元數量計費。
  * **時間軸同步：** Whisper 產生的時間戳非常準確。翻譯過程 **絕對不能** 更改時間戳，只能替換文本內容。上面提供的 Python 腳本已遵守此規則。
  * **多說話者：** 此流程無法區分不同的說話者 (Speaker Diarization)。所有字幕都會顯示為單一軌道。

## 7. 全自動化腳本 (Fully Automated Script)

為了將整個流程串接起來，我們可以編寫一個簡單的 Bash 腳本 `run.sh`。這個腳本會自動執行 FFmpeg 提取、Whisper 轉錄，最後呼叫 Python 腳本進行翻譯。

**腳本範例 (`run.sh`):**

```bash
#!/bin/bash

# --- 配置 ---
VIDEO_FILE="$1" # 從第一個參數讀取影片檔案路徑
BASE_NAME=$(basename "${VIDEO_FILE%.*}") # 提取不含副檔名的主檔名
TARGET_LANG="zh-TW" # 目標語言 (zh-TW 或 zh-CN)
WHISPER_MODEL="large" # Whisper 模型 (large, medium, base)
# --- 結束配置 ---

# 檢查是否提供了影片檔案
if [ -z "$VIDEO_FILE" ]; then
  echo "錯誤：請提供影片檔案路徑作為參數。"
  echo "用法: ./run.sh /path/to/your_video.mp4"
  exit 1
fi

# --- 步驟 1: 音訊提取 ---
echo "步驟 1: 正在從 "$VIDEO_FILE" 提取音訊..."
ffmpeg -i "$VIDEO_FILE" -vn -ar 16000 -ac 1 -c:a pcm_s16le "${BASE_NAME}.wav" -y
if [ $? -ne 0 ]; then
  echo "錯誤：音訊提取失敗。"
  exit 1
fi
echo "音訊已提取至 ${BASE_NAME}.wav"

# --- 步驟 2a: Whisper 轉錄 ---
echo "步驟 2a: 正在使用 Whisper (${WHISPER_MODEL} 模型) 轉錄音訊..."
whisper "${BASE_NAME}.wav" --language Japanese --model "${WHISPER_MODEL}" --task transcribe --output_format srt
if [ $? -ne 0 ]; then
  echo "錯誤：Whisper 轉錄失敗。"
  exit 1
fi
# 將 whisper 產生的 srt 重新命名
mv "${BASE_NAME}.wav.srt" "${BASE_NAME}.ja.srt"
echo "日語字幕已生成：${BASE_NAME}.ja.srt"

# --- 步驟 2b: Python 翻譯 ---
echo "步驟 2b: 正在執行 Python 腳本翻譯字幕..."
# 執行前，請確保 translate_srt.py 中的 INPUT_SRT 和 OUTPUT_SRT 已修改為可接受參數
# 或者修改 Python 腳本以讀取環境變數
export INPUT_SRT_PATH="${BASE_NAME}.ja.srt"
export OUTPUT_SRT_PATH="${BASE_NAME}.${TARGET_LANG}.srt"
export TARGET_LANG_CODE="${TARGET_LANG}"

python translate_srt.py # 假設 translate_srt.py 已被修改為讀取環境變數
if [ $? -ne 0 ]; then
  echo "錯誤：Python 翻譯腳本執行失敗。"
  exit 1
fi
echo "翻譯完成！最終檔案：${OUTPUT_SRT_PATH}"

# --- 步驟 3: 檔案整理 ---
# 為了讓 VLC 自動載入，將最終的 srt 檔案與影片檔名對應
mv "${OUTPUT_SRT_PATH}" "${BASE_NAME}.${TARGET_LANG}.srt"
echo "字幕檔案已命名為 ${BASE_NAME}.${TARGET_LANG}.srt，可與影片一同播放。"

echo "所有步驟已完成！"
```

**修改 `translate_srt.py` 以接受環境變數：**

為了讓 `run.sh` 能順利運作，需要稍微修改 `translate_srt.py`，讓它從環境變數讀取檔案路徑和語言設定，而不是寫死在程式碼中。

```python
# ... (imports)

# --- 配置 ---
# 從環境變數讀取，如果未設定則使用預設值
INPUT_SRT = os.getenv("INPUT_SRT_PATH", "audio.srt")
OUTPUT_SRT = os.getenv("OUTPUT_SRT_PATH", "audio.zh-TW.srt")
TARGET_LANG = os.getenv("TARGET_LANG_CODE", "zh-TW")
SOURCE_LANG = "ja"
# ... (其他配置)
# --- 結束配置 ---

# ... (其餘程式碼不變)
```

## 8. 未來改進方向 (Future Improvements)

1.  **圖形化使用者介面 (GUI):**
    *   使用 `PyQt`、`Tkinter` 或網頁框架 (如 `Flask`, `FastAPI`) 建立一個簡單的圖形介面，讓使用者可以透過點擊按鈕來選擇檔案、設定語言並開始轉換，而無需操作終端機。

2.  **說話者日誌 (Speaker Diarization):**
    *   整合 `pyannote.audio` 等函式庫來識別影片中的不同說話者。
    *   在產生的字幕中標示出「說話者 A」、「說話者 B」，增加字幕的可讀性。

3.  **錯誤處理與日誌紀錄:**
    *   為自動化腳本增加更完善的錯誤處理機制，例如檢查 FFmpeg 和 Whisper 是否已安裝。
    *   將每個步驟的輸出和潛在錯誤記錄到一個日誌檔案 (`log.txt`) 中，方便排查問題。

4.  **組態檔管理:**
    *   將 API 金鑰、模型大小、預設語言等設定項目移至一個獨立的組態檔 (如 `config.ini` 或 `config.yaml`)，而不是寫死在腳本中，方便使用者修改。

5.  **支援更多翻譯服務:**
    *   在 Python 腳本中增加對 `DeepL`、`Microsoft Azure Translator` 等其他翻譯服務的支援，並允許使用者透過組態檔選擇使用哪一個。

6.  **批次處理 (Batch Processing):**
    *   讓 `run.sh` 腳本可以接受多個影片檔案或整個資料夾作為輸入，一次性處理所有影片。
