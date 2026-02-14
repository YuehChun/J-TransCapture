#!/usr/bin/env python3
"""使用 faster-whisper 加速轉錄音訊為 SRT 字幕檔。

加速技術：
- CTranslate2 引擎：優化的 KV Cache、INT8/FP16 量化推理
- 比原生 transformers pipeline 快 4 倍以上
- 記憶體使用量更低
- 內建幻覺過濾：移除重複/無意義的轉錄段落
"""

import argparse
import os
import re
import sys
from collections import Counter
from datetime import timedelta

import srt
from faster_whisper import WhisperModel


def get_device_and_compute():
    """自動偵測最佳運算裝置與量化類型。"""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass

    # Mac CPU 或無 GPU：使用 INT8 量化加速
    return "cpu", "int8"


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
    """使用 faster-whisper 將音訊轉錄為 SRT 字幕。

    Args:
        audio_path: 輸入音訊檔案路徑
        output_srt: 輸出 SRT 檔案路徑
        model_name: CTranslate2 模型名稱
        beam_size: Beam search 大小（越大越精確但越慢）
    """
    if not os.path.exists(audio_path):
        print(f"錯誤：找不到音訊檔案 '{audio_path}'")
        sys.exit(1)

    device, compute_type = get_device_and_compute()
    print(f"使用裝置：{device} (量化：{compute_type})")
    print(f"載入模型：{model_name}...")

    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )

    print(f"正在轉錄 '{audio_path}'...")
    segments, info = model.transcribe(
        audio_path,
        language="ja",
        task="transcribe",
        beam_size=beam_size,
        vad_filter=False,
        condition_on_previous_text=False,  # 防止幻覺連鎖
        no_speech_threshold=0.5,           # 過濾靜音段落
        compression_ratio_threshold=2.4,   # 過濾重複壓縮比過高的段落
    )

    print(f"偵測語言：{info.language} (機率 {info.language_probability:.2%})")

    # 收集所有 segments 並過濾幻覺
    seen_texts = Counter()
    raw_segments = list(segments)
    print(f"原始段數：{len(raw_segments)}")

    subtitles = []
    for segment in raw_segments:
        text = segment.text.strip()
        if not text:
            continue

        # 過濾幻覺：同一文字重複出現超過 3 次
        if is_hallucination(text, seen_texts):
            continue

        # 過濾過短的段落（可能是噪音誤判）
        duration = segment.end - segment.start
        if duration < 0.3 and len(text) <= 2:
            continue

        sub = srt.Subtitle(
            index=len(subtitles) + 1,
            start=timedelta(seconds=segment.start),
            end=timedelta(seconds=segment.end),
            content=text,
        )
        subtitles.append(sub)

    srt_content = srt.compose(subtitles)

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt_content)

    filtered = len(raw_segments) - len(subtitles)
    print(f"轉錄完成！共 {len(subtitles)} 段字幕（過濾 {filtered} 段幻覺），已儲存至 '{output_srt}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用 faster-whisper 加速轉錄音訊為 SRT 字幕")
    parser.add_argument("audio", help="輸入音訊檔案路徑")
    parser.add_argument("-o", "--output", default="audio.srt", help="輸出 SRT 檔案路徑 (預設: audio.srt)")
    parser.add_argument(
        "-m", "--model",
        default="large-v3",
        help="模型名稱 (預設: large-v3，可用: small, medium, large-v3, kotoba-tech/kotoba-whisper-v2.0-faster)",
    )
    parser.add_argument(
        "-b", "--beam-size",
        type=int, default=5,
        help="Beam search 大小 (預設: 5，設 1 最快但精度略降)",
    )
    args = parser.parse_args()

    transcribe(args.audio, args.output, args.model, args.beam_size)
