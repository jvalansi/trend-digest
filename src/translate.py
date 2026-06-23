#!/usr/bin/env python3
"""
Translation pass — adds English equivalents to non-English titles/summaries.

For each item, if `title` or `summary` is not English, the translated form is
stored in `title_en` / `summary_en`. The original field is left untouched so
downstream display can choose which to render.

Backed by deep_translator + langdetect. Silent no-op if those packages are
unavailable (the pipeline still runs, just without translation).
"""

try:
    from deep_translator import GoogleTranslator
    from langdetect import detect
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False


def translate_to_english(text: str) -> str:
    if not TRANSLATION_AVAILABLE or not text:
        return text
    try:
        if detect(text) == "en":
            return text
        return GoogleTranslator(source="auto", target="en").translate(text) or text
    except Exception:
        return text


def translate_items(items: list[dict]) -> list[dict]:
    for item in items:
        title = item.get("title", "")
        if title:
            title_en = translate_to_english(title)
            if title_en != title:
                item["title_en"] = title_en
        summary = item.get("summary", "")
        if summary:
            summary_en = translate_to_english(summary)
            if summary_en != summary:
                item["summary_en"] = summary_en
    return items
