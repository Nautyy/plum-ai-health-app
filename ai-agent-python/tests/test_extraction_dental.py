"""Tests for dental bill OCR text parsing and partial approval."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from engine import DynamicPolicyEngine
from extractors.structured_parser import parse_text_summary
from schemas import ClaimSubmission, ExtractedMedicalData


DENTAL_OCR_TEXT = """**DENTAL TREATMENT BILL**

* **Clinic:** Smile Dental Clinic
* **Patient Name:** Priya Singh
* **Date:** 2024-10-15
* Root Canal Treatment      Rs 8000
* Teeth Whitening           Rs 4000
* **Total Amount:** Rs 12000
"""


def test_parse_dental_ocr_markdown():
    extracted = parse_text_summary(DENTAL_OCR_TEXT)
    assert extracted.patient_name == "Priya Singh"
    assert extracted.total_amount == 12000
    assert len(extracted.line_items) == 2
    assert extracted.line_items[0].description == "Root Canal Treatment"
    assert extracted.line_items[0].amount == 8000


def test_dental_partial_approval():
    engine = DynamicPolicyEngine()
    submission = ClaimSubmission(
        member_id="EMP002",
        policy_id="PLUM_GHI_2024",
        claim_category="DENTAL",
        treatment_date="2024-10-15",
        claimed_amount=12000,
    )
    extracted = parse_text_summary(DENTAL_OCR_TEXT)
    result = engine.evaluate(submission, extracted)
    assert result.decision.value == "PARTIAL"
    assert result.approved_amount == 8000


def test_dental_partial_approval_with_cosmetic_label():
    """OCR may include '(cosmetic)' on line items; must not blanket-reject the claim."""
    engine = DynamicPolicyEngine()
    submission = ClaimSubmission(
        member_id="EMP002",
        policy_id="PLUM_GHI_2024",
        claim_category="DENTAL",
        treatment_date="2024-10-15",
        claimed_amount=12000,
    )
    extracted = ExtractedMedicalData(
        patient_name="Priya Singh",
        hospital_name="Smile Dental Clinic",
        treatment_date="2024-10-15",
        total_amount=12000,
        line_items=[
            {"description": "Root Canal Treatment (molar)", "amount": 8000},
            {"description": "Teeth Whitening (cosmetic)", "amount": 4000},
        ],
    )
    result = engine.evaluate(submission, extracted)
    assert result.decision.value == "PARTIAL"
    assert result.approved_amount == 8000


def test_llm_null_lists_coerced():
    data = ExtractedMedicalData.model_validate(
        {
            "patient_name": "Priya Singh",
            "line_items": [{"description": "Root Canal Treatment", "amount": 8000}],
            "total_amount": 8000,
            "tests_ordered": None,
            "medicines": None,
        }
    )
    assert data.tests_ordered == []
    assert data.medicines == []
