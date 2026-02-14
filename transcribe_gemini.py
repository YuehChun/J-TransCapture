#!/usr/bin/env python3
"""使用 Gemini 2.5 Pro 將音訊轉錄為 SRT 字幕檔。"""

import argparse
import os
import re
import sys
import time

import google.generativeai as genai


def upload_audio(audio_path: str) -> genai.types.File:
    """上傳音訊檔案到 Gemini File API。"""
    print(f"正在上傳 '{audio_path}' 到 Gemini...")
    audio_file = genai.upload_file(audio_path, mime_type="audio/wav")

    # 等待檔案處理完成
    while audio_file.state.name == "PROCESSING":
        print("  等待檔案處理中...")
        time.sleep(5)
        audio_file = genai.get_file(audio_file.name)

    if audio_file.state.name == "FAILED":
        print(f"錯誤：檔案處理失敗。")
        sys.exit(1)

    print(f"  上傳完成：{audio_file.name}")
    return audio_file


def clean_srt_response(text: str) -> str:
    """清理 Gemini 回應中的 markdown 格式標記。"""
    text = text.strip()
    # 移除 markdown code block 標記
    text = re.sub(r"^```(?:srt)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def transcribe(audio_path: str, output_srt: str, language: str = "Japanese", model_name: str = "gemini-2.5-pro") -> None:
    """使用 Gemini 將音訊轉錄為 SRT 字幕。

    Args:
        audio_path: 輸入音訊檔案路徑
        output_srt: 輸出 SRT 檔案路徑
        language: 音訊語言
        model_name: Gemini 模型名稱
    """
    if not os.path.exists(audio_path):
        print(f"錯誤：找不到音訊檔案 '{audio_path}'")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("錯誤：請設定 GEMINI_API_KEY 環境變數。")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        sys.exit(1)

    genai.configure(api_key=api_key)

    # 上傳音訊檔案
    audio_file = upload_audio(audio_path)

    prompt = f"""請將這段{language}音訊轉錄為 SRT 字幕格式。

要求：
1. 使用標準 SRT 格式，包含序號、時間戳和文字
2. 時間戳格式：HH:MM:SS,mmm --> HH:MM:SS,mmm
3. 保留原始{language}文字，不要翻譯
4. 每段字幕約 5-10 秒，包含 1-2 句話
5. 只輸出 SRT 內容，不要加任何說明文字

範例格式：
1
00:00:01,000 --> 00:00:05,000
[轉錄的文字]

2
00:00:05,500 --> 00:00:10,000
[轉錄的文字]"""

    print(f"正在使用 {model_name} 進行轉錄...")
    model = genai.GenerativeModel(model_name)

    try:
        response = model.generate_content(
            [prompt, audio_file],
            generation_config=genai.GenerationConfig(
                temperature=0.1,  # 低溫度以提高轉錄準確性
            ),
        )
    except Exception as e:
        print(f"錯誤：Gemini API 呼叫失敗：{e}")
        sys.exit(1)

    srt_content = clean_srt_response(response.text)

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt_content + "\n")

    # 計算字幕數量
    entry_count = len(re.findall(r"^\d+$", srt_content, re.MULTILINE))
    print(f"轉錄完成！共 {entry_count} 段字幕，已儲存至 '{output_srt}'")

    # 清理上傳的檔案
    try:
        genai.delete_file(audio_file.name)
        print("已清理上傳的暫存檔案。")
    except Exception:
        pass  # 清理失敗不影響結果


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用 Gemini 2.5 Pro 轉錄音訊為 SRT 字幕")
    parser.add_argument("audio", help="輸入音訊檔案路徑")
    parser.add_argument("-o", "--output", default="audio.srt", help="輸出 SRT 檔案路徑 (預設: audio.srt)")
    parser.add_argument("-l", "--language", default="Japanese", help="音訊語言 (預設: Japanese)")
    parser.add_argument("-m", "--model", default="gemini-2.5-pro", help="Gemini 模型名稱 (預設: gemini-2.5-pro)")
    args = parser.parse_args()

    transcribe(args.audio, args.output, args.language, args.model)
