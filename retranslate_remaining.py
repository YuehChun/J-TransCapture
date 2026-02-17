#!/usr/bin/env python3
"""補翻譯剩餘日文段落，使用 OpenRouter。"""

import os
import sys
import time
import unicodedata

from openai import OpenAI
import srt

from text_cleaner import clean_source_text, clean_translated_text

BATCH_SIZE = 5
API_TIMEOUT = 120
MAX_RETRIES = 5
MODEL = "z-ai/glm-4.5-air:free"


def has_jp(text):
    for ch in text:
        name = unicodedata.name(ch, "")
        if "HIRAGANA" in name or "KATAKANA" in name:
            return True
    return False


def init_client():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("錯誤：請設定 OPENROUTER_API_KEY")
        sys.exit(1)
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=API_TIMEOUT,
    )


def translate_batch(client, items):
    # 預處理：清理原文重複雜訊
    cleaned_items = [(idx, clean_source_text(text)) for idx, text in items]
    numbered = "\n".join(f"[{idx}] {text}" for idx, text in cleaned_items)
    prompt = f"""請將以下日文字幕翻譯為繁體中文。

規則：
1. 每行格式為 [編號] 文字，請保持相同格式輸出
2. 保留 [編號] 不變，不要跳過任何一行
3. 只輸出翻譯結果，不加任何說明或註解
4. 語氣感嘆詞翻譯為對應中文感嘆詞（如「嗯」「哈」「嗚」「啊」）
5. 若原文是語音辨識雜訊，翻譯為最接近的簡短中文表達，不要保留重複
6. 翻譯結果應自然流暢，不應出現同一個字或詞連續重複三次以上

{numbered}"""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            results = {}
            for line in response.choices[0].message.content.strip().split("\n"):
                line = line.strip()
                if line.startswith("[") and "]" in line:
                    bracket_end = line.index("]")
                    try:
                        idx = int(line[1:bracket_end])
                        text = line[bracket_end + 1:].strip()
                        results[idx] = text
                    except ValueError:
                        continue
            return results
        except Exception as e:
            wait = 10 * (attempt + 1)
            print(f"\n    retry {attempt+1}/{MAX_RETRIES} (等 {wait}s): {e}")
            time.sleep(wait)
    return {}


def retranslate_file(client, srt_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        subtitles = list(srt.parse(f.read()))

    texts = [sub.content.strip() for sub in subtitles]
    jp_items = [(i, texts[i]) for i in range(len(texts)) if has_jp(texts[i])]

    if not jp_items:
        print(f"  全部已翻譯")
        return 0

    total_batches = (len(jp_items) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"  {len(jp_items)} 段含日文，分 {total_batches} 批")

    changed = 0
    for i in range(0, len(jp_items), BATCH_SIZE):
        batch = jp_items[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"  批次 {batch_num}/{total_batches}...", end=" ", flush=True)

        results = translate_batch(client, batch)
        batch_changed = 0
        for idx, raw_text in results.items():
            new_text = clean_translated_text(raw_text)
            if idx < len(subtitles) and new_text != subtitles[idx].content.strip():
                subtitles[idx].content = new_text
                batch_changed += 1
                changed += 1

        print(f"翻譯 {batch_changed} 段")

        # 每批存檔
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt.compose(subtitles))

    print(f"  完成，共補翻譯 {changed} 段")
    return changed


def main():
    files = [
        "translate/FC25月素人最佳新片抢先看/FC25月素人最佳新片抢先看.zh-TW.srt",
        "translate/FSDSS-703/FSDSS-703.zh-TW.srt",
        "translate/SONE-247/SONE-247.zh-TW.srt",
        "translate/200GANA-3001/200GANA-3001.zh-TW.srt",
    ]

    client = init_client()
    total = 0
    for f in files:
        if not os.path.exists(f):
            print(f"跳過：{f}")
            continue
        print(f"\n處理：{f}")
        total += retranslate_file(client, f)

    print(f"\n全部完成！共補翻譯 {total} 段")


if __name__ == "__main__":
    main()
