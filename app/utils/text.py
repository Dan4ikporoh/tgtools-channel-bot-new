from __future__ import annotations

import html
import re
from typing import Iterable


BAD_WORDS = {
    "бля", "бляд", "сука", "хуй", "нахуй", "пизд", "еб", "долбоеб", "дебил", "мразь", "шлюха",
    "fuck", "shit", "bitch", "asshole", "idiot", "moron",
}


URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ]+", re.IGNORECASE)


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def contains_bad_language(text: str, extra_words: Iterable[str] | None = None) -> bool:
    text = (text or "").lower().replace("ё", "е")
    tokens = WORD_RE.findall(text)
    vocabulary = set(BAD_WORDS)
    if extra_words:
        vocabulary.update(x.lower().replace("ё", "е") for x in extra_words)
    for token in tokens:
        if any(bad in token for bad in vocabulary):
            return True
    return False


def safe_caption(text: str, limit: int = 1024) -> str:
    text = normalize_text(strip_html(text))
    text = html.unescape(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def make_hashtags(*parts: str) -> str:
    tags = []
    for part in parts:
        cleaned = re.sub(r"[^a-zA-Zа-яА-Я0-9]+", "", part or "")
        if cleaned:
            tags.append(f"#{cleaned[:24]}")
    return " ".join(tags)
