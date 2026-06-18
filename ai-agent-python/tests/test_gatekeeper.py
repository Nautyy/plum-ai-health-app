"""Unit tests for gatekeeper document validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from schemas import ClaimDocument, ClaimSubmission
from validators.document_validator import validate_documents


def _submission(docs, category="CONSULTATION"):
    return ClaimSubmission(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category=category,
        treatment_date="2024-11-01",
        claimed_amount=1500,
        documents=docs,
    )


def test_missing_hospital_bill():
    docs = [
        ClaimDocument(file_id="F1", file_name="rx.jpg", actual_type="PRESCRIPTION"),
        ClaimDocument(file_id="F2", file_name="rx2.jpg", actual_type="PRESCRIPTION"),
    ]
    result = validate_documents(_submission(docs))
    assert not result.passed
    assert "HOSPITAL" in result.message.upper() or "Hospital" in result.message


def test_patient_mismatch():
    docs = [
        ClaimDocument(
            file_id="F1",
            actual_type="PRESCRIPTION",
            patient_name_on_doc="Rajesh Kumar",
        ),
        ClaimDocument(
            file_id="F2",
            actual_type="HOSPITAL_BILL",
            patient_name_on_doc="Arjun Mehta",
        ),
    ]
    result = validate_documents(_submission(docs))
    assert not result.passed
    assert "Rajesh" in result.message and "Arjun" in result.message


def test_patient_not_on_member_roster():
    docs = [
        ClaimDocument(
            file_id="F1",
            file_name="dental_bill_priya.jpg",
            actual_type="HOSPITAL_BILL",
            patient_name_on_doc="Priya Singh",
        ),
    ]
    result = validate_documents(_submission(docs, category="DENTAL"))
    assert not result.passed
    assert "EMP001" in result.message
    assert "EMP002" in result.message
    assert "Priya Singh" not in result.message
    assert "Sunita Kumar" not in result.message
    assert "Rajesh Kumar" not in result.message


def test_primary_member_can_claim_for_dependent():
    docs = [
        ClaimDocument(
            file_id="F1",
            actual_type="HOSPITAL_BILL",
            patient_name_on_doc="Arjun Kumar",
        ),
    ]
    result = validate_documents(_submission(docs, category="DENTAL"))
    assert result.passed


def test_dependent_member_own_documents():
    submission = ClaimSubmission(
        member_id="DEP002",
        policy_id="PLUM_GHI_2024",
        claim_category="DENTAL",
        treatment_date="2024-10-15",
        claimed_amount=12000,
        documents=[
            ClaimDocument(
                file_id="F1",
                actual_type="HOSPITAL_BILL",
                patient_name_on_doc="Arjun Kumar",
            ),
        ],
    )
    result = validate_documents(submission)
    assert result.passed


def test_claim_for_spouse_not_enrolled_fails():
    submission = ClaimSubmission(
        member_id="EMP002",
        policy_id="PLUM_GHI_2024",
        claim_category="DENTAL",
        treatment_date="2024-10-15",
        claimed_amount=5000,
        documents=[
            ClaimDocument(
                file_id="F1",
                actual_type="HOSPITAL_BILL",
                patient_name_on_doc="Someone Else",
            ),
        ],
        claim_for="SPOUSE",
    )
    result = validate_documents(submission)
    assert not result.passed
    assert "spouse" in result.message.lower()


def test_same_patient_with_ocr_whitespace_variants():
    docs = [
        ClaimDocument(
            file_id="F1",
            actual_type="PRESCRIPTION",
            content_summary="**Patient Name:** Rajesh Kumar\nDiagnosis: Viral Fever",
        ),
        ClaimDocument(
            file_id="F2",
            actual_type="HOSPITAL_BILL",
            content_summary="Patient:  Rajesh Kumar\nTotal Amount: Rs 1500",
        ),
    ]
    result = validate_documents(_submission(docs))
    assert result.passed


def test_hospital_bill_markdown_patient_details_header():
    """Groq OCR sometimes emits 'Patient Details:' headers — must not parse as a name."""
    docs = [
        ClaimDocument(
            file_id="F1",
            actual_type="PRESCRIPTION",
            content_summary="Patient: Rajesh Kumar\nDiagnosis: Viral Fever",
        ),
        ClaimDocument(
            file_id="F2",
            actual_type="HOSPITAL_BILL",
            content_summary=(
                "Patient Details:\n"
                "Patient Name: Rajesh Kumar\n"
                "Age/Gender: 39 / Male\n"
                "Total Amount: 1500"
            ),
        ),
    ]
    result = validate_documents(_submission(docs))
    assert result.passed
    assert "Rajesh Kumar" in result.patient_names_found


def test_infer_type_uses_content_not_filename():
    docs = [
        ClaimDocument(
            file_id="F1",
            file_name="blurry_pharmacy_bill.jpg",
            content_summary="Patient: Sneha Reddy\nDrug Lic: DL123\nTotal Amount: Rs 800",
        ),
    ]
    result = validate_documents(_submission(docs, category="PHARMACY"))
    assert "PHARMACY_BILL" in result.detected_types


def test_quality_unreadable_without_file_content():
    docs = [
        ClaimDocument(
            file_id="F003",
            file_name="prescription.jpg",
            actual_type="PRESCRIPTION",
            quality="GOOD",
        ),
        ClaimDocument(
            file_id="F004",
            file_name="blurry_bill.jpg",
            actual_type="PHARMACY_BILL",
            quality="UNREADABLE",
        ),
    ]
    result = validate_documents(_submission(docs, category="PHARMACY"))
    assert not result.passed
    assert "blurry_bill.jpg" in result.message
    assert "re-upload" in result.message.lower()


def test_ocr_pharmacy_bill_missing_amount_and_patient():
    docs = [
        ClaimDocument(
            file_id="F1",
            file_name="pharmacy_bill.jpg",
            actual_type="PHARMACY_BILL",
            mime_type="image/jpeg",
            file_content_base64="fake",
            content_summary="Some garbled text without patient or amounts",
            content_source="groq_vision",
        ),
    ]
    result = validate_documents(_submission(docs, category="PHARMACY"))
    assert not result.passed
    assert "could not be read" in result.message.lower()
    assert "pharmacy_bill.jpg" in result.message
    assert "re-upload" in result.message.lower()
