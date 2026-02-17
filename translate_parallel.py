#!/usr/bin/env python3
"""同時並行翻譯多個 SRT 檔案。"""

import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

# 載入 .env
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

from translate_srt import translate_file

FILES = [
    ("translate/FSDSS-703/FSDSS-703.ja.srt", "translate/FSDSS-703/FSDSS-703.zh-TW.srt"),
    ("translate/SONE-247/SONE-247.ja.srt", "translate/SONE-247/SONE-247.zh-TW.srt"),
    ("translate/200GANA-3001/200GANA-3001.ja.srt", "translate/200GANA-3001/200GANA-3001.zh-TW.srt"),
    ("translate/8192 TG频道@TBBAD/8192 TG频道@TBBAD.ja.srt", "translate/8192 TG频道@TBBAD/8192 TG频道@TBBAD.zh-TW.srt"),
    ("translate/FC25月素人最佳新片抢先看/FC25月素人最佳新片抢先看.ja.srt", "translate/FC25月素人最佳新片抢先看/FC25月素人最佳新片抢先看.zh-TW.srt"),
]


def run_translate(args):
    """在子進程中翻譯單一檔案。"""
    input_srt, output_srt = args
    name = os.path.basename(input_srt).replace(".ja.srt", "")
    print(f"\n{'='*50}")
    print(f"開始翻譯: {name}")
    print(f"{'='*50}")

    if not os.path.exists(input_srt):
        print(f"跳過：{input_srt}（檔案不存在）")
        return name, False

    success = translate_file(input_srt, output_srt)
    return name, success


def main():
    # 刪除舊的翻譯檔
    for _, output_srt in FILES:
        if os.path.exists(output_srt):
            os.remove(output_srt)

    print(f"同時翻譯 {len(FILES)} 個檔案...\n")

    with ProcessPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(run_translate, f): f for f in FILES}

        for future in as_completed(futures):
            name, success = future.result()
            status = "成功" if success else "失敗"
            print(f"\n>>> {name} 翻譯{status}")

    print(f"\n{'='*50}")
    print("全部翻譯完成！")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
