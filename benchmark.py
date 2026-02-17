#!/usr/bin/env python3
"""Benchmark: faster-whisper (CPU) vs mlx-whisper (Apple Silicon GPU)

比較兩種 Whisper 引擎的轉錄速度與結果差異。
用法: python benchmark.py <audio.wav> [-m large-v3] [--duration 60]
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import timedelta
from difflib import SequenceMatcher

import srt


def get_audio_duration(audio_path: str) -> float:
    """用 ffprobe 取得音訊總長度（秒）。"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def run_faster_whisper(audio_path, model_name, beam_size, clip_duration=None):
    """使用 faster-whisper (CTranslate2, CPU INT8) 轉錄。"""
    from collections import Counter
    import re
    from faster_whisper import WhisperModel

    try:
        import torch
        if torch.cuda.is_available():
            device, compute_type = "cuda", "float16"
        else:
            device, compute_type = "cpu", "int8"
    except ImportError:
        device, compute_type = "cpu", "int8"

    print(f"  裝置: {device} ({compute_type})")
    print(f"  載入模型中...")

    t_load = time.time()
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    load_time = time.time() - t_load

    print(f"  模型載入: {load_time:.1f}s")
    print(f"  轉錄中...")

    t_start = time.time()
    segments, info = model.transcribe(
        audio_path,
        language="ja",
        task="transcribe",
        beam_size=beam_size,
        condition_on_previous_text=False,
        no_speech_threshold=0.5,
        compression_ratio_threshold=2.4,
    )

    # 收集結果
    seen = Counter()
    subtitles = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        normalized = re.sub(r'\s+', '', text)
        if not normalized:
            continue
        seen[normalized] += 1
        if seen[normalized] > 3:
            continue
        if (seg.end - seg.start) < 0.3 and len(text) <= 2:
            continue
        # 如果有指定 clip_duration，只取前 N 秒
        if clip_duration and seg.start >= clip_duration:
            break
        subtitles.append(srt.Subtitle(
            index=len(subtitles) + 1,
            start=timedelta(seconds=seg.start),
            end=timedelta(seconds=seg.end),
            content=text,
        ))

    transcribe_time = time.time() - t_start

    return {
        "engine": "faster-whisper",
        "device": f"{device} ({compute_type})",
        "load_time": load_time,
        "transcribe_time": transcribe_time,
        "total_time": load_time + transcribe_time,
        "segments": len(subtitles),
        "subtitles": subtitles,
        "text": " ".join(s.content for s in subtitles),
    }


def run_mlx_whisper(audio_path, model_name, beam_size, clip_duration=None):
    """使用 mlx-whisper (Apple Silicon GPU) 轉錄。"""
    from collections import Counter
    import re
    import mlx_whisper

    MLX_MODELS = {
        "tiny": "mlx-community/whisper-tiny",
        "small": "mlx-community/whisper-small",
        "medium": "mlx-community/whisper-medium",
        "large-v3": "mlx-community/whisper-large-v3-mlx",
    }

    model_repo = MLX_MODELS.get(model_name, model_name)
    print(f"  裝置: Apple Silicon GPU (MLX Metal)")
    print(f"  載入模型中...")

    t_load = time.time()
    # mlx-whisper 在 transcribe 時才載入，先做一次 warmup
    clip_arg = f"0,{clip_duration}" if clip_duration else "0"

    t_start = time.time()
    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model_repo,
        language="ja",
        task="transcribe",
        beam_size=beam_size,
        condition_on_previous_text=False,
        no_speech_threshold=0.5,
        compression_ratio_threshold=2.4,
        verbose=False,
        clip_timestamps=clip_arg,
    )
    total_time = time.time() - t_start

    # 過濾
    seen = Counter()
    subtitles = []
    for seg in result.get("segments", []):
        text = seg["text"].strip()
        if not text:
            continue
        normalized = re.sub(r'\s+', '', text)
        if not normalized:
            continue
        seen[normalized] += 1
        if seen[normalized] > 3:
            continue
        if (seg["end"] - seg["start"]) < 0.3 and len(text) <= 2:
            continue
        subtitles.append(srt.Subtitle(
            index=len(subtitles) + 1,
            start=timedelta(seconds=seg["start"]),
            end=timedelta(seconds=seg["end"]),
            content=text,
        ))

    return {
        "engine": "mlx-whisper",
        "device": "Apple Silicon GPU (MLX Metal)",
        "load_time": 0,  # mlx 合併在 transcribe 中
        "transcribe_time": total_time,
        "total_time": total_time,
        "segments": len(subtitles),
        "subtitles": subtitles,
        "text": " ".join(s.content for s in subtitles),
    }


def compare_text(text1, text2):
    """比較兩段文字的相似度。"""
    return SequenceMatcher(None, text1, text2).ratio()


def format_time(seconds):
    """格式化秒數。"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(seconds, 60)
    return f"{int(m)}m {s:.1f}s"


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark: faster-whisper (CPU) vs mlx-whisper (Apple Silicon GPU)"
    )
    parser.add_argument("audio", help="輸入音訊檔案路徑")
    parser.add_argument("-m", "--model", default="large-v3",
                        help="模型名稱 (預設: large-v3)")
    parser.add_argument("-b", "--beam-size", type=int, default=5,
                        help="Beam search 大小 (預設: 5)")
    parser.add_argument("--duration", type=float, default=60,
                        help="只測試前 N 秒的音訊 (預設: 60，設 0 測試全部)")
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        print(f"錯誤：找不到音訊檔案 '{args.audio}'")
        sys.exit(1)

    audio_duration = get_audio_duration(args.audio)
    clip = args.duration if args.duration > 0 else None
    test_duration = clip or audio_duration

    print("=" * 60)
    print("  Whisper Benchmark: faster-whisper vs mlx-whisper")
    print("=" * 60)
    print(f"  音訊檔案: {args.audio}")
    print(f"  音訊總長: {format_time(audio_duration)}")
    print(f"  測試範圍: 前 {format_time(test_duration)}")
    print(f"  模型:     {args.model}")
    print(f"  Beam:     {args.beam_size}")
    print("=" * 60)

    # --- Run faster-whisper ---
    print(f"\n[1/2] faster-whisper (CTranslate2)")
    print("-" * 40)
    result_fw = run_faster_whisper(args.audio, args.model, args.beam_size, clip)

    # --- Run mlx-whisper ---
    print(f"\n[2/2] mlx-whisper (MLX Metal)")
    print("-" * 40)
    result_mlx = run_mlx_whisper(args.audio, args.model, args.beam_size, clip)

    # --- 結果比較 ---
    similarity = compare_text(result_fw["text"], result_mlx["text"]) * 100

    if result_mlx["total_time"] > 0:
        speedup = result_fw["total_time"] / result_mlx["total_time"]
    else:
        speedup = 0

    fw_rtf = result_fw["total_time"] / test_duration if test_duration > 0 else 0
    mlx_rtf = result_mlx["total_time"] / test_duration if test_duration > 0 else 0

    print("\n")
    print("=" * 60)
    print("  BENCHMARK RESULTS")
    print("=" * 60)
    print(f"  {'':30s} {'faster-whisper':>14s} {'mlx-whisper':>14s}")
    print(f"  {'-'*30} {'-'*14} {'-'*14}")
    print(f"  {'Engine':30s} {'CTranslate2':>14s} {'MLX Metal':>14s}")
    print(f"  {'Device':30s} {'CPU (INT8)':>14s} {'GPU (Apple)':>14s}")
    print(f"  {'Total Time':30s} {format_time(result_fw['total_time']):>14s} {format_time(result_mlx['total_time']):>14s}")
    print(f"  {'Segments':30s} {result_fw['segments']:>14d} {result_mlx['segments']:>14d}")
    print(f"  {'Real-Time Factor (RTF)':30s} {fw_rtf:>13.2f}x {mlx_rtf:>13.2f}x")
    print(f"  {'-'*30} {'-'*14} {'-'*14}")
    print(f"  {'Speedup (MLX vs CPU)':30s} {speedup:>14.2f}x")
    print(f"  {'Text Similarity':30s} {similarity:>13.1f}%")
    print("=" * 60)

    if speedup > 1:
        print(f"\n  mlx-whisper 比 faster-whisper 快 {speedup:.1f} 倍")
    else:
        print(f"\n  faster-whisper 比 mlx-whisper 快 {1/speedup:.1f} 倍")

    # --- 顯示文字差異樣本 ---
    if similarity < 100:
        print(f"\n  文字差異範例（前 5 段）：")
        print(f"  {'-'*56}")
        shown = 0
        for i in range(min(len(result_fw["subtitles"]), len(result_mlx["subtitles"]))):
            fw_text = result_fw["subtitles"][i].content
            mlx_text = result_mlx["subtitles"][i].content
            if fw_text != mlx_text:
                print(f"  [{i+1}] faster : {fw_text}")
                print(f"       mlx    : {mlx_text}")
                print()
                shown += 1
                if shown >= 5:
                    break

    print()


if __name__ == "__main__":
    main()
