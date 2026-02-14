#!/usr/bin/env python3
"""使用 Gemini API 將日語 SRT 字幕翻譯為中文。"""

import os
import sys

from google import genai
from google.genai import types
import srt

# --- 配置 ---
INPUT_SRT = os.getenv("INPUT_SRT_PATH", "audio.srt")
OUTPUT_SRT = os.getenv("OUTPUT_SRT_PATH", "audio.zh-TW.srt")
TARGET_LANG = os.getenv("TARGET_LANG_CODE", "zh-TW")
SOURCE_LANG = "ja"
# --- 結束配置 ---

LANG_NAMES = {
    "zh-TW": "繁體中文",
    "zh-CN": "簡體中文",
}


def init_gemini():
    """初始化 Gemini API。"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("錯誤：請設定 GEMINI_API_KEY 環境變數。")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def translate_batch(client, texts, target_lang):
    """批次翻譯多段文字，減少 API 呼叫次數。"""
    if not texts:
        return []

    lang_name = LANG_NAMES.get(target_lang, target_lang)
    numbered = "\n".join(f"[{i}] {t}" for i, t in enumerate(texts))

    prompt = f"""請將以下日文逐行翻譯為{lang_name}。

規則：
1. 每行格式為 [編號] 文字，請保持相同格式輸出
2. 只翻譯文字部分，保留 [編號] 不變
3. 不要加任何說明，只輸出翻譯結果
4. 語氣感嘆詞（如「ん」「はぁ」「うっ」）直接翻譯對應的中文感嘆詞

{numbered}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3),
        )
        # 解析回應
        result = {}
        for line in response.text.strip().split("\n"):
            line = line.strip()
            if line.startswith("[") and "]" in line:
                bracket_end = line.index("]")
                try:
                    idx = int(line[1:bracket_end])
                    text = line[bracket_end + 1:].strip()
                    result[idx] = text
                except ValueError:
                    continue

        return [result.get(i, texts[i]) for i in range(len(texts))]
    except Exception as e:
        print(f"  翻譯錯誤：{e}")
        return texts  # 失敗時返回原文


def process_srt_file():
    """讀取、翻譯並保存 SRT 檔案。"""
    try:
        with open(INPUT_SRT, "r", encoding="utf-8") as f:
            subtitles = list(srt.parse(f.read()))
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 '{INPUT_SRT}'")
        sys.exit(1)

    print(f"載入 {len(subtitles)} 段字幕，來源：{INPUT_SRT}")

    client = init_gemini()
    lang_name = LANG_NAMES.get(TARGET_LANG, TARGET_LANG)
    print(f"翻譯方向：日文 → {lang_name}")

    # 批次翻譯（每批 20 段）
    batch_size = 20
    texts = [sub.content.strip() for sub in subtitles]

    for start in range(0, len(texts), batch_size):
        end = min(start + batch_size, len(texts))
        batch = texts[start:end]
        translated = translate_batch(client, batch, TARGET_LANG)

        for i, trans in enumerate(translated):
            idx = start + i
            original = subtitles[idx].content.strip()
            subtitles[idx].content = trans
            print(f"  [{idx + 1}] {original} → {trans}")

    # 寫入翻譯結果
    with open(OUTPUT_SRT, "w", encoding="utf-8") as f:
        f.write(srt.compose(subtitles))

    print(f"\n翻譯完成！已儲存至 '{OUTPUT_SRT}'")


if __name__ == "__main__":
    process_srt_file()
