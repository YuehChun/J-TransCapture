#!/usr/bin/env python3
"""批次處理 todo/ 目錄下所有 MP4 檔案：提取音訊 → 日文轉錄 → 中文翻譯。"""

import glob
import os
import shutil
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

from extract_audio import extract_audio
from transcribe import transcribe
from translate_srt import translate_file


BS_ROFORMER_MODEL = "model_bs_roformer_ep_368_sdr_12.9628.ckpt"
TODO_DIR = os.path.join(os.path.dirname(__file__), "todo")
TRANSLATE_DIR = os.path.join(os.path.dirname(__file__), "translate")

# 模型載入一次，批次處理時重複使用
_separator = None


def _get_separator(output_dir: str):
    global _separator
    from audio_separator.separator import Separator
    if _separator is None:
        _separator = Separator(output_format="mp3", log_level=30)
        _separator.load_model(model_filename=BS_ROFORMER_MODEL)
    _separator.output_dir = output_dir
    return _separator


def separate_vocals(wav_path: str, output_dir: str) -> str:
    """用 BS-RoFormer 分離人聲，回傳 vocals 檔案路徑。"""
    os.makedirs(output_dir, exist_ok=True)
    separator = _get_separator(output_dir)
    output_files = separator.separate(wav_path)
    output_files = [os.path.join(output_dir, f) if not os.path.isabs(f) else f for f in output_files]
    vocals = next((f for f in output_files if "Vocals" in os.path.basename(f)), None)
    if not vocals or not os.path.exists(vocals):
        raise FileNotFoundError(f"BS-RoFormer 輸出找不到 Vocals: {output_files}")
    return vocals


def _find_existing_vocals(vocals_dir: str) -> str | None:
    """若 vocals_dir 已有分離好的人聲檔，回傳路徑；否則回傳 None。"""
    if not os.path.isdir(vocals_dir):
        return None
    return next(
        (os.path.join(vocals_dir, f) for f in os.listdir(vocals_dir) if "Vocals" in f),
        None,
    )


def process_one(mp4_path):
    """處理單一 MP4 檔案的完整 pipeline。"""
    base = os.path.splitext(mp4_path)[0]
    wav_path = base + ".wav"
    vocals_dir = base + ".vocals"
    ja_srt = base + ".ja.srt"
    zh_srt = base + ".zh-TW.srt"
    name = os.path.basename(base)

    if os.path.exists(zh_srt):
        print(f"[跳過] {name} - 已有中文字幕")
        return True

    if not os.path.exists(mp4_path):
        print(f"[跳過] {name} - MP4 檔案不存在")
        return False

    print(f"\n{'='*60}")
    print(f"處理中: {name}")
    print(f"{'='*60}")

    # Step 1: 提取音訊
    if not os.path.exists(wav_path):
        print(f"\n[1/4] 提取音訊...")
        extract_audio(mp4_path, wav_path)
    else:
        print(f"\n[1/4] 音訊已存在，跳過提取")

    # Step 2: 人聲分離
    vocals_path = _find_existing_vocals(vocals_dir)
    if vocals_path:
        print(f"\n[2/4] 人聲已分離，跳過")
    else:
        print(f"\n[2/4] 人聲分離中（BS-RoFormer）...")
        try:
            vocals_path = separate_vocals(wav_path, vocals_dir)
            print(f"      人聲分離完成：{vocals_path}")
        except Exception as e:
            print(f"      警告：人聲分離失敗（{e}），改用原始音訊")
            vocals_path = wav_path

    # Step 3: 日文轉錄
    if not os.path.exists(ja_srt):
        print(f"\n[3/4] 日文轉錄中...")
        transcribe(vocals_path, ja_srt)
    else:
        print(f"\n[3/4] 日文字幕已存在，跳過轉錄")

    # Step 4: 中文翻譯
    print(f"\n[4/4] 翻譯為中文...")
    success = translate_file(ja_srt, zh_srt)

    # 清理暫存檔（節省空間）
    try:
        os.remove(wav_path)
    except FileNotFoundError:
        pass
    shutil.rmtree(vocals_dir, ignore_errors=True)
    print(f"已清理暫存音訊")

    # 搬移到 translate/ 目錄
    if success:
        dest_dir = os.path.join(TRANSLATE_DIR, name)
        os.makedirs(dest_dir, exist_ok=True)
        for ext in (".mp4", ".ja.srt", ".zh-TW.srt"):
            src = base + ext
            if os.path.exists(src):
                shutil.move(src, os.path.join(dest_dir, name + ext))
        print(f"已搬移至: translate/{name}/")

    return success


def main():
    mp4_files = sorted(glob.glob(os.path.join(TODO_DIR, "*.mp4")))
    if not mp4_files:
        print("todo/ 目錄下沒有 MP4 檔案")
        sys.exit(1)

    total = len(mp4_files)
    print(f"找到 {total} 個 MP4 檔案待處理")

    results = {}
    start_time = time.time()

    for i, mp4 in enumerate(mp4_files, 1):
        name = os.path.basename(mp4)
        print(f"\n{'#'*60}")
        print(f"# 進度: {i}/{total} - {name}")
        print(f"{'#'*60}")

        try:
            success = process_one(mp4)
            results[name] = "成功" if success else "失敗"
        except SystemExit as e:
            print(f"錯誤（子模組呼叫 sys.exit）: {e}")
            results[name] = f"錯誤: sys.exit({e.code})"
        except Exception as e:
            print(f"錯誤: {e}")
            results[name] = f"錯誤: {e}"

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"全部處理完成！耗時 {elapsed/60:.1f} 分鐘")
    print(f"{'='*60}")
    for name, status in results.items():
        print(f"  {name}: {status}")


if __name__ == "__main__":
    main()
