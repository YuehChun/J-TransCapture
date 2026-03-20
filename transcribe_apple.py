#!/usr/bin/env python3
"""使用 Apple 內建語音辨識 (SFSpeechRecognizer) 轉錄日文音訊為 SRT 字幕。

透過 Swift helper 腳本呼叫 Apple Speech framework，避免 PyObjC Run Loop 問題。

需求：
  - macOS（內建 Speech framework）
  - swift（macOS 內建）
  - ffmpeg（切割音訊）
  - pip install srt
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import timedelta

import srt

CHUNK_DURATION = 55  # 秒，Apple 辨識建議上限
APP_BUNDLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TranscribeHelper.app")


def get_audio_duration(audio_path: str) -> float:
    """使用 ffprobe 取得音訊總長度（秒）。"""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def extract_chunk(audio_path: str, start: float, duration: float, output_path: str) -> None:
    """用 ffmpeg 切出一段音訊，轉為 16kHz mono WAV。"""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(duration),
            "-i", audio_path,
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            output_path,
        ],
        capture_output=True, check=True,
    )


def recognize_chunk_swift(chunk_path: str, chunk_start: float) -> list[srt.Subtitle]:
    """呼叫 Swift helper 辨識單段音訊，回傳帶時間戳的字幕列表。"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        json_path = tf.name

    try:
        # 用 open -W 透過 LaunchServices 啟動，讓 TCC 正確識別 responsible process
        result = subprocess.run(
            ["open", "-W", APP_BUNDLE, "--args", chunk_path, json_path],
            capture_output=True, text=True, timeout=180,
        )

        if result.returncode != 0:
            print(f"  app 錯誤：{result.stderr.strip()}")
            return []

        with open(json_path, "r") as f:
            segments = json.load(f)

        subtitles = []
        for seg in segments:
            text = seg["text"].strip()
            if not text:
                continue
            t_start = chunk_start + seg["start"]
            t_end = t_start + max(seg["duration"], 0.3)
            subtitles.append(srt.Subtitle(
                index=0,
                start=timedelta(seconds=t_start),
                end=timedelta(seconds=t_end),
                content=text,
            ))
        return subtitles

    finally:
        if os.path.exists(json_path):
            os.unlink(json_path)


def merge_words_into_lines(subtitles: list[srt.Subtitle], gap_threshold: float = 1.0) -> list[srt.Subtitle]:
    """將逐字字幕依停頓合併成句子行。"""
    if not subtitles:
        return []

    groups = []
    current_group = [subtitles[0]]

    for sub in subtitles[1:]:
        prev_end = current_group[-1].end.total_seconds()
        curr_start = sub.start.total_seconds()
        if curr_start - prev_end > gap_threshold:
            groups.append(current_group)
            current_group = [sub]
        else:
            current_group.append(sub)
    groups.append(current_group)

    merged = []
    for i, group in enumerate(groups):
        text = "".join(s.content for s in group)
        merged.append(srt.Subtitle(
            index=i + 1,
            start=group[0].start,
            end=group[-1].end,
            content=text,
        ))
    return merged


def transcribe(audio_path: str, output_srt: str) -> None:
    if not os.path.exists(audio_path):
        print(f"錯誤：找不到音訊檔案 '{audio_path}'")
        sys.exit(1)

    if not os.path.exists(APP_BUNDLE):
        print(f"錯誤：找不到 app bundle '{APP_BUNDLE}'")
        sys.exit(1)

    print("使用：Apple 內建語音辨識（日文，透過 Swift helper）")
    print("取得音訊長度...")
    total_duration = get_audio_duration(audio_path)
    total_chunks = int(total_duration / CHUNK_DURATION) + 1
    print(f"總長度：{total_duration:.1f} 秒，分 {total_chunks} 段處理")

    all_word_subs = []

    with tempfile.TemporaryDirectory() as tmpdir:
        chunk_idx = 0
        start = 0.0
        while start < total_duration:
            chunk_idx += 1
            duration = min(CHUNK_DURATION, total_duration - start)
            chunk_path = os.path.join(tmpdir, f"chunk_{chunk_idx:04d}.wav")

            print(f"  [{chunk_idx}/{total_chunks}] 切割 {start:.0f}s–{start+duration:.0f}s...", end=" ", flush=True)
            extract_chunk(audio_path, start, duration, chunk_path)

            print("辨識中...", end=" ", flush=True)
            subs = recognize_chunk_swift(chunk_path, start)
            all_word_subs.extend(subs)
            print(f"得到 {len(subs)} 個詞")

            start += duration

    print("合併字詞為句子行...")
    merged = merge_words_into_lines(all_word_subs)

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt.compose(merged))

    print(f"轉錄完成！共 {len(merged)} 行字幕，儲存至 '{output_srt}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用 Apple 內建語音辨識轉錄日文音訊為 SRT")
    parser.add_argument("audio", help="輸入音訊檔案路徑（mp3/wav/m4a/mp4 等）")
    parser.add_argument("-o", "--output", default="audio.srt", help="輸出 SRT 檔案路徑（預設：audio.srt）")
    args = parser.parse_args()

    transcribe(args.audio, args.output)
