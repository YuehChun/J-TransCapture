#!/usr/bin/env python3
"""補翻譯：將 zh-TW.srt 中仍為日文的段落重新翻譯。分批送出。"""

import os
import sys
import unicodedata

from openai import OpenAI
import srt

BATCH_SIZE = 50
API_TIMEOUT = 120
MODEL = "z-ai/glm-4.5-air:free"


def contains_japanese(text):
    """檢測文字是否包含日文（平假名或片假名）。"""
    for ch in text:
        name = unicodedata.name(ch, "")
        if "HIRAGANA" in name or "KATAKANA" in name:
            return True
    return False


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


def retranslate_file(client, srt_path):
    """分批送出 SRT 檔案翻譯。"""
    with open(srt_path, "r", encoding="utf-8") as f:
        subtitles = list(srt.parse(f.read()))

    texts = [sub.content.strip() for sub in subtitles]
    jp_count = sum(1 for t in texts if contains_japanese(t))

    if jp_count == 0:
        print(f"  全部已翻譯，無需補翻")
        return 0

    print(f"  共 {len(texts)} 段，其中 {jp_count} 段含日文，翻譯中...")

    total = len(texts)
    all_results = {}

    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        batch = texts[start:end]
        batch_num = start // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

        if total_batches > 1:
            print(f"  批次 {batch_num}/{total_batches}（第 {start}-{end-1} 段）...")

        numbered = "\n".join(f"[{start + i}] {t}" for i, t in enumerate(batch))
        prompt = f"""請將以下日文字幕翻譯為繁體中文。

規則：
1. 每行格式為 [編號] 文字，請保持相同格式輸出
2. 將日文語音內容翻譯為對應的繁體中文語音內容
3. 保留 [編號] 不變，不要跳過任何一行
4. 不要加任何說明，只輸出翻譯結果
5. 語氣感嘆詞（如「ん」「はぁ」「うっ」「ああ」）翻譯為對應的中文感嘆詞
6. 過濾掉重複無意義的字詞（如連續重複的「ああああ」簡化為「啊」，「永永永永...」簡化為「永」）

{numbered}"""

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            for line in response.choices[0].message.content.strip().split("\n"):
                line = line.strip()
                if line.startswith("[") and "]" in line:
                    bracket_end = line.index("]")
                    try:
                        idx = int(line[1:bracket_end])
                        text = line[bracket_end + 1:].strip()
                        all_results[idx] = text
                    except ValueError:
                        continue
        except Exception as e:
            print(f"  批次 {batch_num} 翻譯錯誤：{e}")

    changed = 0
    for i in range(len(texts)):
        trans = all_results.get(i, texts[i])
        old = subtitles[i].content.strip()
        if trans != old:
            subtitles[i].content = trans
            changed += 1
            print(f"  [{subtitles[i].index}] {old} → {trans}")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(subtitles))

    print(f"  補翻譯 {changed} 段，已儲存")
    return changed


def main():
    files = [
        "translate/FSDSS-703/FSDSS-703.zh-TW.srt",
        "translate/SONE-247/SONE-247.zh-TW.srt",
        "translate/200GANA-3001/200GANA-3001.zh-TW.srt",
        "translate/8192 TG频道@TBBAD/8192 TG频道@TBBAD.zh-TW.srt",
        "translate/FC25月素人最佳新片抢先看/FC25月素人最佳新片抢先看.zh-TW.srt",
    ]

    client = init_client()
    total = 0
    for f in files:
        if not os.path.exists(f):
            print(f"跳過：{f}（檔案不存在）")
            continue
        print(f"\n處理：{f}")
        count = retranslate_file(client, f)
        total += count

    print(f"\n全部完成！共補翻譯 {total} 段")


if __name__ == "__main__":
    main()
