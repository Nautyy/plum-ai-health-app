"""Line-item adjudication using existing opd_categories lists in policy."""

from __future__ import annotations

from policy.exclusion_intent import line_item_matches_coverage, line_item_matches_exclusion
from policy.rules_config import LINE_ITEM_CATEGORY_KEYS
from schemas import ExtractedMedicalData, LineItem


def _normalize_category(category: str) -> str:
    return category.lower().replace(" ", "_")


def category_supports_line_items(policy: dict, category: str) -> bool:
    cat_key = _normalize_category(category)
    if cat_key not in LINE_ITEM_CATEGORY_KEYS:
        return False
    keys = LINE_ITEM_CATEGORY_KEYS[cat_key]
    cat_rules = policy.get("opd_categories", {}).get(cat_key, {})
    return bool(cat_rules.get(keys["covered_key"]) and cat_rules.get(keys["excluded_key"]))


def _line_item_lists(policy: dict, cat_key: str) -> tuple[list[str], list[str], str]:
    keys = LINE_ITEM_CATEGORY_KEYS[cat_key]
    cat_rules = policy.get("opd_categories", {}).get(cat_key, {})
    covered = cat_rules.get(keys["covered_key"]) or []
    excluded = cat_rules.get(keys["excluded_key"]) or []
    return covered, excluded, keys["excluded_reason"]


def evaluate_category_line_items(
    policy: dict,
    category: str,
    extracted: ExtractedMedicalData,
) -> tuple[list[LineItem], float]:
    cat_key = _normalize_category(category)
    covered, excluded, excluded_reason = _line_item_lists(policy, cat_key)

    decisions: list[LineItem] = []
    approved_total = 0.0

    for item in extracted.line_items:
        if line_item_matches_exclusion(item.description, excluded):
            decisions.append(
                LineItem(
                    description=item.description,
                    amount=item.amount,
                    approved=False,
                    rejection_reason=excluded_reason,
                )
            )
        elif line_item_matches_coverage(item.description, covered):
            decisions.append(
                LineItem(description=item.description, amount=item.amount, approved=True)
            )
            approved_total += item.amount or 0
        else:
            decisions.append(
                LineItem(
                    description=item.description,
                    amount=item.amount,
                    approved=False,
                    rejection_reason="NOT_COVERED",
                )
            )

    return decisions, approved_total
