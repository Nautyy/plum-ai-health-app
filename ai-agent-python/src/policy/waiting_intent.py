"""Policy-driven waiting period condition matching."""

from __future__ import annotations

from policy.intent_match import matches_any_intent
from policy.rules_config import WAITING_CONDITION_INTENTS


def matches_waiting_condition(policy: dict, clinical_text: str, condition: str) -> bool:
    intents = WAITING_CONDITION_INTENTS.get(condition)
    if not intents:
        fallback = condition.lower().replace("_", " ")
        return matches_any_intent(clinical_text, [fallback])
    return matches_any_intent(clinical_text, intents)
