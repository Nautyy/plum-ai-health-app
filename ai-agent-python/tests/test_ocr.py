"""Unit tests for OCR pass-through."""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ocr.document_ocr import decode_text_file, run_ocr_on_documents
from schemas import ClaimDocument


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
    from unittest.mock import MagicMock, patch

    doc = ClaimDocument(
        file_id="F1",
        file_name="bill.jpg",
        actual_type="PHARMACY_BILL",
        mime_type="image/jpeg",
        file_content_base64="ZmFrZQ==",
    )

    mock_response = MagicMock()
    mock_response.content = "UNREADABLE"

    with patch("llm.client.get_chat_model") as mock_get_model:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_model.return_value = mock_llm

        updated, logs, degraded = run_ocr_on_documents([doc])

    assert updated[0].quality == "UNREADABLE"
    assert updated[0].content_source == "groq_vision"
    assert degraded
    assert any("UNREADABLE" in log for log in logs)


def test_text_file_decode():
    text = "Patient: Test User"
    encoded = base64.b64encode(text.encode()).decode()
    assert decode_text_file(encoded) == text
