"""Shared intent-phrase matching for policy rules."""

from __future__ import annotations

import re


def word_boundary_match(text: str, keyword: str) -> bool:
    pattern = rf"\b{re.escape(keyword)}\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def phrase_matches(text: str, phrase: str) -> bool:
    text_lower = text.lower()
    phrase_lower = phrase.lower().strip()
    if not phrase_lower:
        return False
    if " " in phrase_lower or "(" in phrase_lower:
        return phrase_lower in text_lower
    return word_boundary_match(text_lower, phrase_lower)


def matches_any_intent(text: str, intent_phrases: list[str]) -> bool:
    if not text.strip():
        return False
    return any(phrase_matches(text, phrase) for phrase in intent_phrases)


def count_intent_matches(text: str, intent_phrases: list[str]) -> int:
    if not text.strip():
        return 0
    return sum(1 for phrase in intent_phrases if phrase_matches(text, phrase))
