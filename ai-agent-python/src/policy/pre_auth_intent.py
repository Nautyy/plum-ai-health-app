"""Policy-driven pre-authorization test detection."""

from __future__ import annotations

from typing import Optional

from policy.intent_match import matches_any_intent
from policy.rules_config import PRE_AUTH_TEST_INTENTS
from schemas import ExtractedMedicalData


def _clinical_text(extracted: ExtractedMedicalData) -> str:
    parts = [
        extracted.diagnosis or "",
        extracted.treatment or "",
        " ".join(extracted.tests_ordered),
        " ".join(item.description for item in extracted.line_items if item.description),
    ]
    return " ".join(p for p in parts if p).strip()


def check_pre_auth_required(
    policy: dict,
    category: str,
    extracted: ExtractedMedicalData,
    claimed_amount: float,
    pre_auth_id: Optional[str],
) -> Optional[str]:
    if pre_auth_id:
        return None

    text = _clinical_text(extracted)
    if not text:
        return None

    cat_key = category.lower().replace(" ", "_")
    cat_rules = policy.get("opd_categories", {}).get(cat_key, {})
    threshold = float(cat_rules.get("pre_auth_threshold", 0) or 0)
    tests = cat_rules.get("high_value_tests_requiring_pre_auth") or []

    for test in tests:
        phrases = PRE_AUTH_TEST_INTENTS.get(test, [test.lower()])
        if matches_any_intent(text, phrases) and claimed_amount > threshold:
            return test
    return None
