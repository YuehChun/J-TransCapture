#!/usr/bin/env python3
"""字幕文字清理工具：移除重複字元、重複片段、無意義雜訊。

用於翻譯前清理日文原文，以及翻譯後清理中文結果。
"""

import re


def clean_source_text(text: str) -> str:
    """清理日文原文中的重複雜訊（翻譯前預處理）。

    處理：
    - 連續重複字元：ああああ → あ
    - 連續重複片段：すごいすごいすごい → すごい
    - 過多標點符號
    """
    if not text or not text.strip():
        return text

    # 連續重複單字元壓縮（3+ 次 → 1 次）
    text = re.sub(r'(.)\1{2,}', r'\1', text)

    # 連續重複片段壓縮（2-6 字的片段重複 2+ 次 → 1 次）
    text = re.sub(r'(.{2,6}?)\1{2,}', r'\1', text)

    # 連續相同標點壓縮
    text = re.sub(r'([。、！？…・])\1{2,}', r'\1', text)

    return text.strip()


def clean_translated_text(text: str) -> str:
    """清理翻譯結果中的重複雜訊（翻譯後後處理）。

    處理：
    - 連續重複字元：好好好好 → 好、啊啊啊啊 → 啊
    - 連續重複詞語：好厲害好厲害好厲害 → 好厲害
    - 過多標點符號
    """
    if not text or not text.strip():
        return text

    # 連續重複單字元壓縮（3+ 次 → 1 次）
    text = re.sub(r'(.)\1{2,}', r'\1', text)

    # 連續重複片段壓縮（2-8 字的片段重複 2+ 次 → 1 次）
    text = re.sub(r'(.{2,8}?)\1{2,}', r'\1', text)

    # 連續相同標點壓縮（保留最多 2 個）
    text = re.sub(r'([。、！？…])\1{2,}', r'\1\1', text)

    return text.strip()


def is_noise_only(text: str) -> bool:
    """判斷文字清理後是否只剩無意義雜訊。"""
    cleaned = clean_source_text(text)
    if not cleaned:
        return True
    # 清理後只剩 1 個字元，且是常見語氣詞/感嘆詞
    if len(cleaned) == 1 and cleaned in 'あえうおんはぁっ～':
        return True
    return False
