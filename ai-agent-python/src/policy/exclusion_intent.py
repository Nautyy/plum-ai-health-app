"""Intent-based claim exclusion evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from policy.intent_match import matches_any_intent
from policy.rules_config import EXCLUSION_RULES, LINE_ITEM_CATEGORY_KEYS
from schemas import ExtractedMedicalData


@dataclass(frozen=True)
class ExclusionMatch:
    reason_code: str
    label: str


def _normalize_category(category: str) -> str:
    return category.lower().replace(" ", "_")


def _category_has_line_exclusions(policy: dict, category: str) -> bool:
    cat_key = _normalize_category(category)
    if cat_key in LINE_ITEM_CATEGORY_KEYS:
        keys = LINE_ITEM_CATEGORY_KEYS[cat_key]
        cat_rules = policy.get("opd_categories", {}).get(cat_key, {})
        return bool(cat_rules.get(keys["excluded_key"]))
    return False


def _collect_field_text(extracted: ExtractedMedicalData, fields: list[str]) -> str:
    parts: list[str] = []
    if "diagnosis" in fields and extracted.diagnosis:
        parts.append(extracted.diagnosis)
    if "treatment" in fields and extracted.treatment:
        parts.append(extracted.treatment)
    if "line_items" in fields:
        parts.extend(item.description for item in extracted.line_items if item.description)
    return " ".join(parts)


def _primary_clinical_text(extracted: ExtractedMedicalData) -> str:
    return " ".join(filter(None, [extracted.diagnosis or "", extracted.treatment or ""])).strip()


def _rule_applies_to_category(rule: dict[str, Any], category: str, policy: dict) -> bool:
    cat_key = _normalize_category(category)
    defer = rule.get("defer_to_line_items_for_categories") or []
    if cat_key in defer and _category_has_line_exclusions(policy, cat_key):
        return False

    only_categories = rule.get("categories")
    if only_categories:
        return cat_key in {_normalize_category(c) for c in only_categories}
    return True


def _text_for_rule(rule: dict[str, Any], extracted: ExtractedMedicalData) -> str:
    scope = rule.get("scope", "claim")
    fields = rule.get("match_fields") or ["diagnosis", "treatment", "line_items"]

    if scope == "claim_primary_intent":
        primary = _primary_clinical_text(extracted)
        if primary:
            return primary
        if len(extracted.line_items) == 1:
            return extracted.line_items[0].description or ""
        return ""

    return _collect_field_text(extracted, fields)


def check_claim_exclusions(
    policy: dict,
    extracted: ExtractedMedicalData,
    claim_category: str,
) -> Optional[ExclusionMatch]:
    for rule in EXCLUSION_RULES:
        if not _rule_applies_to_category(rule, claim_category, policy):
            continue

        text = _text_for_rule(rule, extracted)
        phrases = rule.get("intent_phrases") or []
        if not matches_any_intent(text, phrases):
            continue

        return ExclusionMatch(
            reason_code=str(rule.get("reason_code", "EXCLUDED_CONDITION")),
            label=str(rule.get("label", "Excluded treatment")),
        )

    return None


def line_item_matches_exclusion(description: str, excluded_intents: list[str]) -> bool:
    if not description.strip():
        return False
    return matches_any_intent(description, excluded_intents)


def line_item_matches_coverage(description: str, covered_intents: list[str]) -> bool:
    if not description.strip():
        return False
    return matches_any_intent(description, covered_intents)
