#!/usr/bin/env python3
"""使用 mlx-whisper 透過 Apple Silicon GPU 加速轉錄音訊為 SRT 字幕檔。

加速技術：
- Apple MLX 框架：原生支援 Apple Silicon GPU (Metal)
- 比 CPU 推理快約 3 倍
- 內建幻覺過濾：移除重複/無意義的轉錄段落
"""

import argparse
import os
import re
import sys
from collections import Counter
from datetime import timedelta

import mlx_whisper
import srt

# MLX 模型對應表（HuggingFace Hub）
MLX_MODELS = {
    "tiny": "mlx-community/whisper-tiny",
    "small": "mlx-community/whisper-small",
    "medium": "mlx-community/whisper-medium",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
}


def is_hallucination(text: str, seen_texts: Counter, threshold: int = 3) -> bool:
    """偵測 Whisper 幻覺（重複出現相同文字超過閾值）。"""
    normalized = re.sub(r'\s+', '', text)
    if not normalized:
        return True
    seen_texts[normalized] += 1
    return seen_texts[normalized] > threshold


def transcribe(
    audio_path: str,
    output_srt: str,
    model_name: str = "large-v3",
    beam_size: int = 5,
) -> None:
    """使用 mlx-whisper 將音訊轉錄為 SRT 字幕。

    Args:
        audio_path: 輸入音訊檔案路徑
        output_srt: 輸出 SRT 檔案路徑
        model_name: 模型名稱（tiny, small, medium, large-v3）
        beam_size: Beam search 大小（越大越精確但越慢）
    """
    if not os.path.exists(audio_path):
        print(f"錯誤：找不到音訊檔案 '{audio_path}'")
        sys.exit(1)

    model_repo = MLX_MODELS.get(model_name, model_name)
    print(f"使用裝置：Apple Silicon GPU (MLX)")
    print(f"載入模型：{model_repo}...")
    print(f"正在轉錄 '{audio_path}'...")

    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model_repo,
        language="ja",
        task="transcribe",
        condition_on_previous_text=False,
        no_speech_threshold=0.5,
        compression_ratio_threshold=2.4,
        verbose=False,
    )

    detected_lang = result.get("language", "ja")
    print(f"偵測語言：{detected_lang}")

    raw_segments = result.get("segments", [])
    print(f"原始段數：{len(raw_segments)}")

    seen_texts = Counter()
    subtitles = []
    for segment in raw_segments:
        text = segment["text"].strip()
        if not text:
            continue

        if is_hallucination(text, seen_texts):
            continue

        duration = segment["end"] - segment["start"]
        if duration < 0.3 and len(text) <= 2:
            continue

        sub = srt.Subtitle(
            index=len(subtitles) + 1,
            start=timedelta(seconds=segment["start"]),
            end=timedelta(seconds=segment["end"]),
            content=text,
        )
        subtitles.append(sub)

    srt_content = srt.compose(subtitles)

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt_content)

    filtered = len(raw_segments) - len(subtitles)
    print(f"轉錄完成！共 {len(subtitles)} 段字幕（過濾 {filtered} 段幻覺），已儲存至 '{output_srt}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用 mlx-whisper (Apple Silicon GPU) 轉錄音訊為 SRT 字幕")
    parser.add_argument("audio", help="輸入音訊檔案路徑")
    parser.add_argument("-o", "--output", default="audio.srt", help="輸出 SRT 檔案路徑 (預設: audio.srt)")
    parser.add_argument(
        "-m", "--model",
        default="large-v3",
        help="模型名稱 (預設: large-v3，可用: tiny, small, medium, large-v3)",
    )
    parser.add_argument(
        "-b", "--beam-size",
        type=int, default=5,
        help="Beam search 大小 (預設: 5，設 1 最快但精度略降)",
    )
    args = parser.parse_args()

    transcribe(args.audio, args.output, args.model, args.beam_size)
