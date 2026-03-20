#!/usr/bin/env python3
"""使用 OpenRouter (Grok 4 Fast) 將日語 SRT 字幕翻譯為中文。支援 CLI 及並行使用。"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
import srt

from text_cleaner import clean_source_text, clean_translated_text, is_noise_only

# --- 配置 ---
TARGET_LANG = os.getenv("TARGET_LANG_CODE", "zh-TW")
SOURCE_LANG = "ja"
BATCH_SIZE = 50
MAX_RETRIES = 5
API_TIMEOUT = 120
MAX_WORKERS = 5  # 並行請求數（rate limit 16/min，留點餘裕）
MODEL = "x-ai/grok-4.1-fast"
# --- 結束配置 ---

LANG_NAMES = {
    "zh-TW": "繁體中文",
    "zh-CN": "簡體中文",
}


def init_client():
    """初始化 OpenRouter API client。"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("錯誤：請設定 OPENROUTER_API_KEY 環境變數。")
        sys.exit(1)
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=API_TIMEOUT,
    )


def translate_batch(client, texts, start_idx, target_lang):
    """送出一批字幕給 Grok 翻譯，含重試機制。"""
    lang_name = LANG_NAMES.get(target_lang, target_lang)
    numbered = "\n".join(f"[{start_idx + i}] {t}" for i, t in enumerate(texts))

    prompt = f"""請將以下日文字幕翻譯為{lang_name}。

規則：
1. 每行格式為 [編號] 文字，請保持相同格式輸出
2. 保留 [編號] 不變，不要跳過任何一行
3. 只輸出翻譯結果，不加任何說明或註解
4. 語氣感嘆詞（如「ん」「はぁ」「うっ」「ああ」）翻譯為對應的{lang_name}感嘆詞（如「嗯」「哈」「嗚」「啊」）
5. 若原文是語音辨識雜訊（無意義的重複字、亂碼、不成句的片段），直接翻譯為最接近的簡短{lang_name}表達，不要保留重複
6. 每行翻譯結果應該是自然流暢的{lang_name}，不應出現同一個字或詞連續重複三次以上

{numbered}"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()
            result = {}
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("[") and "]" in line:
                    bracket_end = line.index("]")
                    try:
                        idx = int(line[1:bracket_end])
                        content = line[bracket_end + 1:].strip()
                        result[idx] = content
                    except ValueError:
                        continue
            return result
        except Exception as e:
            err_str = str(e)
            # 429 rate limit: 等待到 reset 時間
            if "429" in err_str and attempt < MAX_RETRIES:
                import re, json
                wait = 60  # 預設等 60 秒
                try:
                    err_data = json.loads(err_str.split(" - ", 1)[1])
                    reset_ms = int(err_data["error"]["metadata"]["headers"]["X-RateLimit-Reset"])
                    wait = max(1, (reset_ms / 1000) - time.time())
                except Exception:
                    pass
                wait = min(wait, 120)  # 最多等 2 分鐘
                print(f"    rate limit，等待 {wait:.0f}s 後重試 ({attempt}/{MAX_RETRIES})...")
                time.sleep(wait)
            elif attempt < MAX_RETRIES:
                wait = 2 ** attempt
                print(f"    重試 {attempt}/{MAX_RETRIES}（{e}），等待 {wait}s...")
                time.sleep(wait)
            else:
                print(f"    失敗（{e}）")
                return {}


def translate_all(client, texts, target_lang):
    """並行分批送出字幕翻譯。"""
    if not texts:
        return []

    total = len(texts)
    all_results = {}
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    # 建立所有批次任務
    batches = []
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        batch_num = start // BATCH_SIZE + 1
        batches.append((start, end, batch_num, texts[start:end]))

    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for start, end, batch_num, batch in batches:
            future = executor.submit(translate_batch, client, batch, start, target_lang)
            futures[future] = (start, end, batch_num)

        for future in as_completed(futures):
            start, end, batch_num = futures[future]
            done += 1
            result = future.result()
            all_results.update(result)
            print(f"  完成 {done}/{total_batches}（批次 {batch_num}，第 {start}-{end-1} 段，翻譯 {len(result)} 段）")

    return [all_results.get(i, texts[i]) for i in range(total)]


def translate_file(input_srt, output_srt, target_lang=None):
    """翻譯單一 SRT 檔案。可被外部呼叫。"""
    if target_lang is None:
        target_lang = TARGET_LANG

    try:
        with open(input_srt, "r", encoding="utf-8") as f:
            subtitles = list(srt.parse(f.read()))
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 '{input_srt}'")
        return False

    print(f"載入 {len(subtitles)} 段字幕，來源：{input_srt}")

    client = init_client()
    lang_name = LANG_NAMES.get(target_lang, target_lang)
    print(f"翻譯方向：日文 → {lang_name}（模型：{MODEL}）")

    raw_texts = [sub.content.strip() for sub in subtitles]

    # 預處理：清理原文中的重複雜訊
    texts = []
    noise_indices = set()
    for i, t in enumerate(raw_texts):
        cleaned = clean_source_text(t)
        if is_noise_only(t):
            noise_indices.add(i)
            texts.append(cleaned)  # 保留但標記為雜訊
        else:
            texts.append(cleaned)

    if noise_indices:
        print(f"預處理：偵測到 {len(noise_indices)} 段純雜訊字幕")
    print(f"共 {len(texts)} 段字幕，分 {(len(texts) + BATCH_SIZE - 1) // BATCH_SIZE} 批翻譯中...")

    translated = translate_all(client, texts, target_lang)

    # 後處理：清理翻譯結果中的重複雜訊
    translated = [clean_translated_text(t) for t in translated]

    changed = sum(1 for i, t in enumerate(translated) if t != raw_texts[i])
    for i, trans in enumerate(translated):
        subtitles[i].content = trans

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt.compose(subtitles))

    print(f"翻譯完成！{changed}/{len(texts)} 段已翻譯，儲存至 '{output_srt}'")
    return True


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        input_path = sys.argv[1]
        output_path = sys.argv[2]
    else:
        input_path = os.getenv("INPUT_SRT_PATH", "audio.srt")
        output_path = os.getenv("OUTPUT_SRT_PATH", "audio.zh-TW.srt")

    translate_file(input_path, output_path)
