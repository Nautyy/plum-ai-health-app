"""Edge-case tests for policy engine defensive handling."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from engine import DynamicPolicyEngine, load_policy
from schemas import ClaimSubmission, ExtractedMedicalData, LineItem


def _consultation_extracted(**kwargs) -> ExtractedMedicalData:
    defaults = dict(
        patient_name="Rajesh Kumar",
        diagnosis="Viral Fever",
        total_amount=1500,
        line_items=[LineItem(description="Consultation Fee", amount=1500)],
    )
    defaults.update(kwargs)
    return ExtractedMedicalData(**defaults)


def test_dependent_without_join_date_inherits_primary():
    engine = DynamicPolicyEngine()
    submission = ClaimSubmission(
        member_id="DEP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
    )
    result = engine.evaluate(submission, _consultation_extracted(patient_name="Sunita Kumar"))
    assert result.decision.value == "APPROVED"
    assert result.approved_amount == 1350


def test_invalid_treatment_date_returns_pending():
    engine = DynamicPolicyEngine()
    submission = ClaimSubmission(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="not-a-date",
        claimed_amount=1500,
    )
    result = engine.evaluate(submission, _consultation_extracted())
    assert result.decision.value == "PENDING"
    assert "INVALID_TREATMENT_DATE" in result.rejection_reasons


def test_zero_claim_amount_returns_pending():
    engine = DynamicPolicyEngine()
    submission = ClaimSubmission(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=0,
    )
    result = engine.evaluate(submission, _consultation_extracted(total_amount=0))
    assert result.decision.value == "PENDING"
    assert "INVALID_CLAIM_AMOUNT" in result.rejection_reasons


def test_broken_primary_member_reference_manual_review():
    policy = load_policy()
    policy = {
        **policy,
        "members": policy["members"]
        + [
            {
                "member_id": "DEP_BROKEN",
                "name": "Broken Dependent",
                "relationship": "CHILD",
                "primary_member_id": "EMP_MISSING",
            }
        ],
    }
    engine = DynamicPolicyEngine(policy=policy)
    submission = ClaimSubmission(
        member_id="DEP_BROKEN",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
    )
    result = engine.evaluate(submission, _consultation_extracted(patient_name="Broken Dependent"))
    assert result.decision.value == "MANUAL_REVIEW"
    assert "PRIMARY_MEMBER_NOT_FOUND" in result.rejection_reasons


def test_null_ytd_claims_amount_treated_as_zero():
    engine = DynamicPolicyEngine()
    submission = ClaimSubmission(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
        ytd_claims_amount=0,
    )
    result = engine.evaluate(submission, _consultation_extracted())
    assert result.decision.value == "APPROVED"


def test_unknown_member_rejected_not_crash():
    engine = DynamicPolicyEngine()
    submission = ClaimSubmission(
        member_id="EMP999",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
    )
    result = engine.evaluate(submission, _consultation_extracted())
    assert result.decision.value == "REJECTED"
    assert "MEMBER_NOT_FOUND" in result.rejection_reasons
