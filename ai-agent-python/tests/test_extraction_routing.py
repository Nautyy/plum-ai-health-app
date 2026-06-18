"""Tests for LLM-first extraction routing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents import _document_uses_llm_extraction, _should_use_llm
from schemas import ClaimDocument, ClaimSubmission


def test_structured_prefilled_skips_llm():
    doc = ClaimDocument(
        file_id="F1",
        content_summary=(
            "Doctor Name: Dr. Arun Sharma\n"
            "Patient Name: Rajesh Kumar\n"
            "line_items: [{\"description\": \"Consultation Fee\", \"amount\": 1000}]\n"
            "Total: 1500"
        ),
        content_source="prefilled",
    )
    assert not _document_uses_llm_extraction(doc)


def test_ocr_document_uses_llm():
    doc = ClaimDocument(
        file_id="F1",
        content_summary="Patient Name: Rajesh Kumar\nTotal Amount: Rs 1500",
        content_source="groq_vision",
    )
    assert _document_uses_llm_extraction(doc)


def test_free_form_text_without_source_uses_llm():
    doc = ClaimDocument(
        file_id="F1",
        content_summary="Some clinic bill\nRajesh Kumar\nConsultation Rs 1000",
    )
    assert _document_uses_llm_extraction(doc)


def test_should_use_llm_when_any_doc_is_ocr():
    submission = ClaimSubmission(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
        documents=[
            ClaimDocument(
                file_id="F1",
                content_summary="Doctor Name: Dr. X\nPatient Name: Rajesh Kumar\nTotal: 1500",
                content_source="prefilled",
            ),
            ClaimDocument(
                file_id="F2",
                content_summary="Hospital bill OCR text",
                content_source="groq_vision",
            ),
        ],
    )
    assert _should_use_llm(submission)
