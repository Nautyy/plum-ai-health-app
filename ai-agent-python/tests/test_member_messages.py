"""Tests for member-facing decision copy."""

from member_messages import build_member_reason
from schemas import DecisionType, LineItem


def test_partial_dental_uses_friendly_copy_not_codes():
    reason = build_member_reason(
        decision=DecisionType.PARTIAL,
        approved_amount=8000,
        rejection_reasons=[],
        line_item_decisions=[
            LineItem(description="Root Canal", amount=8000, approved=True),
            LineItem(
                description="Teeth Whitening",
                amount=4000,
                approved=False,
                rejection_reason="COSMETIC_EXCLUSION",
            ),
        ],
        financial_breakdown={
            "submitted_claimed_amount": 5000,
            "document_total_amount": 12000,
        },
    )

    assert "COSMETIC_EXCLUSION" not in reason
    assert "adjudication" not in reason.lower()
    assert "₹8,000" in reason
    assert "Teeth Whitening wasn't covered" in reason
    assert "whitening" in reason.lower()
    assert "₹5,000" in reason
    assert "₹12,000" in reason


def test_rejected_claim_uses_friendly_rejection_copy():
    reason = build_member_reason(
        decision=DecisionType.REJECTED,
        approved_amount=0,
        rejection_reasons=["WAITING_PERIOD"],
        line_item_decisions=[],
        financial_breakdown={},
    )

    assert "WAITING_PERIOD" not in reason
    assert "waiting period" in reason.lower()
