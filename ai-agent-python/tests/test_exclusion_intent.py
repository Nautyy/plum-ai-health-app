"""Tests for intent-based policy exclusions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from engine import DynamicPolicyEngine
from policy.exclusion_intent import check_claim_exclusions
from schemas import ClaimSubmission, ExtractedMedicalData, LineItem


def test_dental_cosmetic_label_does_not_claim_reject():
    """Mixed dental bill: cosmetic line item must not trigger claim-level cosmetic exclusion."""
    from engine import load_policy

    policy = load_policy()
    extracted = ExtractedMedicalData(
        patient_name="Priya Singh",
        hospital_name="Smile Dental Clinic",
        line_items=[
            LineItem(description="Root Canal Treatment (molar)", amount=8000),
            LineItem(description="Teeth Whitening (cosmetic)", amount=4000),
        ],
        total_amount=12000,
    )
    assert check_claim_exclusions(policy, extracted, "DENTAL") is None

    engine = DynamicPolicyEngine()
    result = engine.evaluate(
        ClaimSubmission(
            member_id="EMP002",
            policy_id="PLUM_GHI_2024",
            claim_category="DENTAL",
            treatment_date="2024-10-15",
            claimed_amount=12000,
        ),
        extracted,
    )
    assert result.decision.value == "PARTIAL"
    assert result.approved_amount == 8000


def test_bariatric_consultation_claim_rejected_by_intent():
    from engine import load_policy

    policy = load_policy()
    extracted = ExtractedMedicalData(
        diagnosis="Morbid Obesity — BMI 37",
        treatment="Bariatric Consultation and Customised Diet Plan",
        line_items=[
            LineItem(description="Bariatric Consultation", amount=3000),
            LineItem(description="Personalised Diet and Nutrition Program", amount=5000),
        ],
        total_amount=8000,
    )
    match = check_claim_exclusions(policy, extracted, "CONSULTATION")
    assert match is not None
    assert match.reason_code == "EXCLUDED_CONDITION"

    engine = DynamicPolicyEngine()
    result = engine.evaluate(
        ClaimSubmission(
            member_id="EMP009",
            policy_id="PLUM_GHI_2024",
            claim_category="CONSULTATION",
            treatment_date="2024-10-18",
            claimed_amount=8000,
        ),
        extracted,
    )
    assert result.decision.value == "REJECTED"
    assert "EXCLUDED_CONDITION" in result.rejection_reasons


def test_cosmetic_surgery_primary_intent_rejected():
    from engine import load_policy

    policy = load_policy()
    extracted = ExtractedMedicalData(
        diagnosis="Aesthetic concern",
        treatment="Rhinoplasty consultation",
        total_amount=5000,
    )
    match = check_claim_exclusions(policy, extracted, "CONSULTATION")
    assert match is not None
    assert "cosmetic" in match.label.lower() or "aesthetic" in match.label.lower()
