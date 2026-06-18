"""Unit tests for OCR."""

import base64
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ocr.document_ocr import (
    decode_text_file,
    extract_document_text,
    run_ocr_on_documents,
    _parse_vision_response,
)
from ocr.preprocess import preprocess_image_base64
from ocr.prompts import OCR_VISION_PROMPT
from schemas import ClaimDocument


def test_ocr_prompt_covers_indian_document_types():
    assert "Prescription" in OCR_VISION_PROMPT
    assert "Lab / diagnostic report" in OCR_VISION_PROMPT
    assert "drug license" in OCR_VISION_PROMPT.lower()
    assert "medical shorthand" in OCR_VISION_PROMPT.lower()
    assert "UNREADABLE" in OCR_VISION_PROMPT
    assert "OCR_NOTE:" in OCR_VISION_PROMPT


def test_parse_vision_response_unreadable():
    text, unreadable, degraded = _parse_vision_response("UNREADABLE")
    assert unreadable
    assert not text


def test_parse_vision_response_partial_with_note():
    raw = "Patient: Rajesh Kumar\nOCR_NOTE: registration partially obscured"
    text, unreadable, degraded = _parse_vision_response(raw)
    assert not unreadable
    assert degraded
    assert "Rajesh Kumar" in text


def test_prefilled_content_summary_skips_ocr():
    doc = ClaimDocument(
        file_id="F1",
        file_name="rx.txt",
        content_summary="Patient: Rajesh Kumar\nDiagnosis: Fever",
    )
    updated, logs, degraded = run_ocr_on_documents([doc])
    assert updated[0].content_summary.startswith("Patient:")
    assert not degraded
    assert "pre-filled" in logs[0]


def test_vision_ocr_marks_unreadable_quality():
    doc = ClaimDocument(
        file_id="F1",
        file_name="bill.jpg",
        actual_type="PHARMACY_BILL",
        mime_type="image/jpeg",
        file_content_base64="ZmFrZQ==",
    )

    mock_response = MagicMock()
    mock_response.content = "UNREADABLE"

    with patch("ocr.document_ocr._invoke_vision_ocr", return_value=("", None, True)):
        updated, logs, degraded = run_ocr_on_documents([doc])

    assert updated[0].quality == "UNREADABLE"
    assert updated[0].content_source == "groq_vision"
    assert degraded
    assert any("UNREADABLE" in log for log in logs)


def test_vision_ocr_partial_text_not_marked_unreadable():
    doc = ClaimDocument(
        file_id="F1",
        file_name="rx.jpg",
        mime_type="image/jpeg",
        file_content_base64="ZmFrZQ==",
    )
    partial = "Patient: Rajesh Kumar\nOCR_NOTE: partial document"

    with patch(
        "ocr.document_ocr._extract_image_with_vision",
        return_value=(partial, None, "groq_vision", True),
    ):
        updated, logs, degraded = run_ocr_on_documents([doc])

    assert updated[0].content_summary == partial
    assert updated[0].quality != "UNREADABLE"
    assert degraded
    assert "partial" in logs[0]


def test_pdf_text_used_when_pypdf_succeeds():
    doc = ClaimDocument(
        file_id="F1",
        file_name="bill.pdf",
        mime_type="application/pdf",
        file_content_base64=base64.b64encode(b"dummy").decode(),
    )
    with patch("ocr.document_ocr.extract_pdf_text", return_value=("Patient: Test\nTotal: 100", None)):
        text, error, method, degraded = extract_document_text(doc)
    assert text.startswith("Patient:")
    assert method == "pypdf"
    assert not degraded


def test_scanned_pdf_falls_back_to_vision():
    doc = ClaimDocument(
        file_id="F1",
        file_name="scan.pdf",
        mime_type="application/pdf",
        file_content_base64=base64.b64encode(b"dummy").decode(),
    )
    with patch("ocr.document_ocr.extract_pdf_text", return_value=("", "no text")):
        with patch(
            "ocr.document_ocr._extract_scanned_pdf_with_vision",
            return_value=("--- Page 1 ---\nPatient: Rajesh", None, "groq_vision_pdf"),
        ):
            text, error, method, degraded = extract_document_text(doc)
    assert "Rajesh" in text
    assert method == "groq_vision_pdf"


def test_preprocess_image_returns_base64():
    from PIL import Image

    buf = __import__("io").BytesIO()
    Image.new("RGB", (40, 40), "white").save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    out = preprocess_image_base64(b64, "image/jpeg")
    assert isinstance(out, str)
    assert len(out) > 0


def test_text_file_decode():
    text = "Patient: Test User"
    encoded = base64.b64encode(text.encode()).decode()
    assert decode_text_file(encoded) == text
