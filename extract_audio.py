#!/usr/bin/env python3
"""從影片中提取音訊並調整頻率為指定取樣率。"""

import argparse
import subprocess
import sys
import os


def extract_audio(video_path: str, output_path: str, sample_rate: int = 16000) -> None:
    """使用 FFmpeg 從影片提取音訊並重新取樣。

    Args:
        video_path: 輸入影片檔案路徑
        output_path: 輸出音訊檔案路徑
        sample_rate: 目標取樣率 (Hz)
    """
    if not os.path.exists(video_path):
        print(f"錯誤：找不到影片檔案 '{video_path}'")
        sys.exit(1)

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",                    # 移除影片軌
        "-ar", str(sample_rate),  # 設定取樣率
        "-ac", "1",               # 單聲道
        "-c:a", "pcm_s16le",     # 16-bit PCM 編碼
        "-y",                     # 覆蓋已存在檔案
        output_path,
    ]

    print(f"正在從 '{video_path}' 提取音訊...")
    print(f"目標格式：{sample_rate}Hz, 單聲道, 16-bit PCM WAV")

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print("錯誤：找不到 ffmpeg 指令。請先安裝 FFmpeg。")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"錯誤：音訊提取失敗。\n{e.stderr}")
        sys.exit(1)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"音訊已提取至 '{output_path}' ({file_size_mb:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="從影片提取音訊並調整頻率")
    parser.add_argument("video", help="輸入影片檔案路徑")
    parser.add_argument("-o", "--output", default="audio.wav", help="輸出音訊檔案路徑 (預設: audio.wav)")
    parser.add_argument("-r", "--rate", type=int, default=16000, help="目標取樣率 Hz (預設: 16000)")
    args = parser.parse_args()

    extract_audio(args.video, args.output, args.rate)
