#!/usr/bin/env python3
"""批次重新翻譯 translate/ 下所有 UUID 資料夾的字幕，使用 OpenRouter 付費 Grok 模型。"""

import os
import sys
import time

# 載入 .env
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

import translate_srt

# 覆蓋模型為付費 Grok
translate_srt.MODEL = "x-ai/grok-4.1-fast"

TRANSLATE_DIR = os.path.join(os.path.dirname(__file__), "translate")

UUID_FOLDERS = [
    "0b497f71-7a5c-46a4-b70f-148e844ddc7c",
    "0f2dd79e-b3cb-4b7c-ad7e-a3f5d05ef442",
    "3e5cb790-a17f-4417-abde-7fef22891fe8",
    "3f3b930f-cd46-4373-866a-32b7a2c13bdc",
    "4a7761b7-86c2-419b-9c78-ff0daf828a2c",
    "54e6b06e-d325-4651-be00-fd9f65a24238",
    "55e581eb-cbb4-4b74-a493-abe68b5adc94",
    "7b23a15a-50c0-419b-9829-d632874f8939",
    "9dd27a17-4a9e-461c-b983-50bac8f8f3c7",
    "9f45cf19-262b-4d96-a0f3-62acb9e4c130",
    "cf04a5f2-b53b-48de-8551-2df3065af3bf",
    "d3264723-3cbc-4993-b01b-f01567be1b0a",
    "dd49a063-87f8-430c-b94c-f5019ea7bdc6",
    "fdf6ab8a-fbb8-4b76-bfbe-67b35640ac79",
]


def main():
    total = len(UUID_FOLDERS)
    print(f"使用模型：{translate_srt.MODEL}")
    print(f"共 {total} 個 UUID 資料夾待重新翻譯\n")

    results = {}
    start_time = time.time()

    for i, uuid in enumerate(UUID_FOLDERS, 1):
        folder = os.path.join(TRANSLATE_DIR, uuid)
        ja_srt = os.path.join(folder, f"{uuid}.ja.srt")
        zh_srt = os.path.join(folder, f"{uuid}.zh-TW.srt")

        print(f"\n{'='*60}")
        print(f"[{i}/{total}] {uuid}")
        print(f"{'='*60}")

        if not os.path.exists(ja_srt):
            print(f"  跳過：找不到日文字幕 {ja_srt}")
            results[uuid] = "跳過（無日文字幕）"
            continue

        try:
            success = translate_srt.translate_file(ja_srt, zh_srt)
            results[uuid] = "成功" if success else "失敗"
        except Exception as e:
            print(f"  錯誤：{e}")
            results[uuid] = f"錯誤: {e}"

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"全部完成！耗時 {elapsed/60:.1f} 分鐘")
    print(f"{'='*60}")
    for uuid, status in results.items():
        print(f"  {uuid}: {status}")


if __name__ == "__main__":
    main()
