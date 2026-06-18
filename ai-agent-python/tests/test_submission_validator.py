"""Unit tests for submission cross-validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from schemas import ClaimDocument, ClaimSubmission, ExtractedMedicalData
from validators.submission_validator import validate_submission_against_extracted


def _submission(**kwargs):
    defaults = {
        "member_id": "EMP001",
        "policy_id": "PLUM_GHI_2024",
        "claim_category": "CONSULTATION",
        "treatment_date": "2024-11-01",
        "claimed_amount": 1500,
        "documents": [],
    }
    defaults.update(kwargs)
    return ClaimSubmission(**defaults)


def test_matching_treatment_date_passes():
    submission = _submission(
        documents=[
            ClaimDocument(
                file_id="F1",
                file_name="bill.jpg",
                actual_type="HOSPITAL_BILL",
                content_summary="Patient: Rajesh Kumar\nDate: 2024-11-01\nTotal Amount: Rs 1500",
            )
        ]
    )
    extracted = ExtractedMedicalData(treatment_date="2024-11-01", total_amount=1500)

    result = validate_submission_against_extracted(submission, extracted)
    assert result.passed


def test_treatment_date_mismatch_fails():
    submission = _submission(
        treatment_date="2024-11-01",
        documents=[
            ClaimDocument(
                file_id="F1",
                file_name="bill.jpg",
                actual_type="HOSPITAL_BILL",
                content_summary="Patient: Rajesh Kumar\nDate: 2024-10-15\nTotal Amount: Rs 1500",
            )
        ],
    )
    extracted = ExtractedMedicalData(treatment_date="2024-10-15", total_amount=1500)

    result = validate_submission_against_extracted(submission, extracted)
    assert not result.passed
    assert "TREATMENT_DATE_MISMATCH" in result.rejection_reasons
    assert "2024-11-01" in result.message or "01 Nov" in result.message
    assert "2024-10-15" in result.message or "15 Oct" in result.message


def test_inconsistent_document_dates_fail():
    submission = _submission(
        documents=[
            ClaimDocument(
                file_id="F1",
                actual_type="PRESCRIPTION",
                content_summary="Patient: Rajesh Kumar\nDate: 2024-11-01",
            ),
            ClaimDocument(
                file_id="F2",
                actual_type="HOSPITAL_BILL",
                content_summary="Patient: Rajesh Kumar\nDate: 2024-11-03\nTotal Amount: Rs 1500",
            ),
        ]
    )

    result = validate_submission_against_extracted(submission, ExtractedMedicalData())
    assert not result.passed
    assert "DOCUMENT_DATE_INCONSISTENT" in result.rejection_reasons


def test_missing_document_dates_skips_date_check():
    submission = _submission(
        documents=[
            ClaimDocument(
                file_id="F1",
                actual_type="HOSPITAL_BILL",
                content_summary="Patient: Rajesh Kumar\nTotal Amount: Rs 1500",
            )
        ]
    )

    result = validate_submission_against_extracted(submission, ExtractedMedicalData(total_amount=1500))
    assert result.passed


def test_matching_hospital_name_passes():
    submission = _submission(
        hospital_name="Apollo Hospitals",
        documents=[
            ClaimDocument(
                file_id="F1",
                actual_type="HOSPITAL_BILL",
                content_summary="Hospital Name: Apollo Hospitals\nDate: 2024-11-01\nTotal Amount: Rs 1500",
            )
        ],
    )
    extracted = ExtractedMedicalData(hospital_name="Apollo Hospitals", total_amount=1500)

    result = validate_submission_against_extracted(submission, extracted)
    assert result.passed


def test_hospital_name_mismatch_fails():
    submission = _submission(
        hospital_name="City Clinic",
        documents=[
            ClaimDocument(
                file_id="F1",
                actual_type="HOSPITAL_BILL",
                content_summary="Hospital Name: Apollo Hospitals\nDate: 2024-11-01\nTotal Amount: Rs 1500",
            )
        ],
    )
    extracted = ExtractedMedicalData(hospital_name="Apollo Hospitals", total_amount=1500)

    result = validate_submission_against_extracted(submission, extracted)
    assert not result.passed
    assert "HOSPITAL_NAME_MISMATCH" in result.rejection_reasons
    assert "City Clinic" in result.message
    assert "Apollo Hospitals" in result.message


def test_hospital_check_skipped_when_form_blank():
    submission = _submission(
        documents=[
            ClaimDocument(
                file_id="F1",
                actual_type="HOSPITAL_BILL",
                content_summary="Hospital Name: Apollo Hospitals\nDate: 2024-11-01\nTotal Amount: Rs 1500",
            )
        ]
    )

    result = validate_submission_against_extracted(
        submission,
        ExtractedMedicalData(hospital_name="Apollo Hospitals", total_amount=1500),
    )
    assert result.passed
