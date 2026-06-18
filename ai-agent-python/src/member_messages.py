"""Member-facing claim decision copy — separate from ops/adjudication reason strings."""

from __future__ import annotations

from typing import Any, Optional

from schemas import DecisionType, LineItem

REJECTION_MEMBER_MESSAGES: dict[str, str] = {
    "MEMBER_NOT_FOUND": (
        "The member ID you entered doesn't match anyone on your company's health policy."
    ),
    "PRIMARY_MEMBER_NOT_FOUND": (
        "Your dependent profile is linked to a primary member we couldn't verify."
    ),
    "CATEGORY_NOT_COVERED": "This type of expense isn't covered under your current policy.",
    "PER_CLAIM_EXCEEDED": "The claim amount is above the limit allowed for a single claim.",
    "NO_COVERED_ITEMS": "None of the items on your bill are covered under your policy.",
    "INVALID_TREATMENT_DATE": "The treatment date is missing or invalid.",
    "INVALID_CLAIM_AMOUNT": "Please enter a claim amount greater than zero.",
    "TREATMENT_DATE_MISMATCH": (
        "The treatment date you entered doesn't match the date on your uploaded documents."
    ),
    "DOCUMENT_DATE_INCONSISTENT": (
        "Your documents show different treatment dates from the same visit."
    ),
    "HOSPITAL_NAME_MISMATCH": (
        "The hospital name you entered doesn't match the hospital on your bill."
    ),
    "WAITING_PERIOD": (
        "This treatment falls within a waiting period on your policy."
    ),
    "PRE_AUTH_MISSING": (
        "This claim needs pre-authorization from Plum before the treatment."
    ),
    "EXCLUDED_CONDITION": "This treatment isn't covered under your policy exclusions.",
    "COSMETIC_EXCLUSION": (
        "Cosmetic dental procedures like teeth whitening aren't covered under your policy."
    ),
    "NOT_COVERED": "This item isn't listed as a covered benefit under your policy.",
    "EXCLUSION": "This item isn't covered under your policy.",
    "POLICY_EVALUATION_ERROR": (
        "We couldn't fully process your claim automatically. Our team will review it manually."
    ),
}


def _format_inr(amount: float) -> str:
    rounded = round(float(amount))
    return f"₹{rounded:,}"


def member_rejection_message(code: str) -> str:
    if code in REJECTION_MEMBER_MESSAGES:
        return REJECTION_MEMBER_MESSAGES[code]
    if code.isupper() and "_" in code:
        return code.replace("_", " ").lower().capitalize() + "."
    return code


def _amount_mismatch_note(financial_breakdown: dict[str, Any]) -> str:
    submitted = financial_breakdown.get("submitted_claimed_amount")
    document_total = financial_breakdown.get("document_total_amount")
    if submitted is None or document_total is None:
        return ""
    try:
        submitted_f = float(submitted)
        document_f = float(document_total)
    except (TypeError, ValueError):
        return ""
    if abs(submitted_f - document_f) < 1.0:
        return ""
    return (
        f"The amount you entered ({_format_inr(submitted_f)}) was different from what we read "
        f"on your documents ({_format_inr(document_f)}). We used the amounts on your bill "
        f"for this decision."
    )


def build_member_reason(
    *,
    decision: DecisionType | str,
    approved_amount: float,
    rejection_reasons: list[str],
    line_item_decisions: list[LineItem],
    financial_breakdown: dict[str, Any],
) -> str:
    decision_value = decision.value if isinstance(decision, DecisionType) else str(decision)
    mismatch = _amount_mismatch_note(financial_breakdown)
    rejected_items = [item for item in line_item_decisions if not item.approved]
    approved_amount = float(approved_amount or 0)

    if decision_value == DecisionType.PARTIAL.value:
        parts: list[str] = []
        if approved_amount > 0:
            parts.append(
                f"We approved {_format_inr(approved_amount)} for the covered parts of your bill."
            )
        else:
            parts.append("Part of your claim was reviewed.")
        for item in rejected_items:
            reason = member_rejection_message(item.rejection_reason or "NOT_COVERED")
            parts.append(f"{item.description} wasn't covered — {reason}")
        if mismatch:
            parts.append(mismatch)
        return " ".join(parts)

    if decision_value == DecisionType.APPROVED.value:
        parts: list[str] = []
        if approved_amount > 0:
            parts.append(
                f"Your claim is approved. You'll receive {_format_inr(approved_amount)}."
            )
        else:
            parts.append("Your claim is approved.")
        copay = financial_breakdown.get("copay_amount")
        network = financial_breakdown.get("network_discount_amount")
        if isinstance(network, (int, float)) and network > 0:
            parts.append("This includes your network hospital discount.")
        if isinstance(copay, (int, float)) and copay > 0:
            pct = financial_breakdown.get("copay_percent")
            if isinstance(pct, (int, float)):
                parts.append(f"Your co-pay ({pct}%) has been deducted as per your policy.")
            else:
                parts.append("Your co-pay has been deducted as per your policy.")
        if mismatch:
            parts.append(mismatch)
        return " ".join(parts)

    if decision_value == DecisionType.REJECTED.value:
        if rejection_reasons:
            return " ".join(member_rejection_message(code) for code in rejection_reasons)
        return "Your claim couldn't be approved under your current policy."

    if decision_value == DecisionType.MANUAL_REVIEW.value:
        return (
            "We need a specialist on our team to review your claim. "
            "We'll get back to you within 2–3 business days."
        )

    if decision_value == DecisionType.PENDING.value:
        if rejection_reasons:
            return " ".join(member_rejection_message(code) for code in rejection_reasons)
        return "We need a bit more information before we can process your claim."

    return "We've processed your claim."
