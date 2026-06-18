"""Unit tests for policy engine financial calculations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from engine import DynamicPolicyEngine
from schemas import ClaimSubmission, ExtractedMedicalData, LineItem


def test_consultation_copay():
    engine = DynamicPolicyEngine()
    submission = ClaimSubmission(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
        ytd_claims_amount=5000,
    )
    extracted = ExtractedMedicalData(
        patient_name="Rajesh Kumar",
        diagnosis="Viral Fever",
        total_amount=1500,
        line_items=[
            LineItem(description="Consultation Fee", amount=1000),
            LineItem(description="CBC Test", amount=300),
        ],
    )
    result = engine.evaluate(submission, extracted)
    assert result.decision.value == "APPROVED"
    assert result.approved_amount == 1350
    assert result.financial_breakdown.get("submitted_claimed_amount") == 1500
    assert result.financial_breakdown.get("document_total_amount") == 1500


def test_dental_mismatch_note_when_submitted_differs_from_documents():
    engine = DynamicPolicyEngine()
    submission = ClaimSubmission(
        member_id="EMP002",
        policy_id="PLUM_GHI_2024",
        claim_category="DENTAL",
        treatment_date="2024-10-15",
        claimed_amount=800,
    )
    extracted = ExtractedMedicalData(
        patient_name="Priya Singh",
        total_amount=12000,
        line_items=[
            LineItem(description="Root Canal Treatment", amount=8000),
            LineItem(description="Teeth Whitening", amount=4000),
        ],
    )
    result = engine.evaluate(submission, extracted)
    assert result.decision.value == "PARTIAL"
    assert result.approved_amount == 8000
    assert result.financial_breakdown["submitted_claimed_amount"] == 800
    assert result.financial_breakdown["document_total_amount"] == 12000
    assert "differs from document total" in result.reason


def test_network_discount_before_copay():
    engine = DynamicPolicyEngine()
    submission = ClaimSubmission(
        member_id="EMP010",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-03",
        claimed_amount=4500,
        hospital_name="Apollo Hospitals",
        ytd_claims_amount=8000,
    )
    extracted = ExtractedMedicalData(
        hospital_name="Apollo Hospitals",
        total_amount=4500,
    )
    result = engine.evaluate(submission, extracted)
    assert result.approved_amount == 3240
