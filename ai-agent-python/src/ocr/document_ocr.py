"""OCR and document text extraction."""

from __future__ import annotations

import base64
import io
from typing import Optional

from schemas import ClaimDocument

DEFAULT_OCR_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def decode_text_file(content_base64: str) -> str:
    raw = base64.b64decode(content_base64)
    return raw.decode("utf-8", errors="replace")


def extract_pdf_text(content_base64: str) -> tuple[str, Optional[str]]:
    try:
        from pypdf import PdfReader

        raw = base64.b64decode(content_base64)
        reader = PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if text:
            return text, None
        return "", "PDF contained no extractable text"
    except Exception as exc:
        return "", str(exc)


def extract_document_text(doc: ClaimDocument) -> tuple[str, Optional[str], str]:
    """Returns (text, error, method)."""
    if doc.content_summary:
        return doc.content_summary, None, "prefilled"

    if not doc.file_content_base64:
        return "", None, "skipped"

    mime = (doc.mime_type or "").lower()

    if mime.startswith("text/"):
        try:
            return decode_text_file(doc.file_content_base64), None, "text_decode"
        except Exception as exc:
            return "", str(exc), "text_decode"

    if mime == "application/pdf":
        text, err = extract_pdf_text(doc.file_content_base64)
        return text, err, "pypdf"

    # Vision OCR via Groq — optional, degrades gracefully
    try:
        from llm.client import get_chat_model
        from langchain_core.messages import HumanMessage

        llm = get_chat_model("OCR_MODEL", DEFAULT_OCR_MODEL)
        if llm is None:
            return "", "OCR unavailable: GROQ_API_KEY not configured", "vision_skipped"

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        "Extract all visible text from this medical document. "
                        "Preserve labels like Patient, Diagnosis, line items, amounts. "
                        "If the image is too blurry, dark, cropped, or illegible to read "
                        "with confidence, respond with exactly: UNREADABLE"
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime or 'image/jpeg'};base64,{doc.file_content_base64}"
                    },
                },
            ]
        )
        response = llm.invoke([message])
        text = response.content if hasattr(response, "content") else str(response)
        text = str(text).strip()
        if text.upper().startswith("UNREADABLE"):
            return "", None, "groq_vision"
        return text, None, "groq_vision"
    except Exception as exc:
        return "", str(exc), "vision_failed"


OCR_SOURCES = frozenset({"groq_vision", "pypdf", "text_decode", "ocr"})


def run_ocr_on_documents(documents: list[ClaimDocument]) -> tuple[list[ClaimDocument], list[str], bool]:
    """Populate content_summary on documents. Returns updated docs, log lines, degraded flag."""
    updated: list[ClaimDocument] = []
    logs: list[str] = []
    degraded = False

    for doc in documents:
        if doc.content_summary:
            source = doc.content_source or "prefilled"
            updated.append(doc.model_copy(update={"content_source": source}))
            logs.append(f"{doc.file_id}: using pre-filled content_summary")
            continue

        text, error, method = extract_document_text(doc)
        if error and not text:
            degraded = True
            logs.append(f"{doc.file_id}: OCR {method} failed — {error}")
            updated.append(doc)
            continue

        if text:
            updated.append(
                doc.model_copy(update={"content_summary": text, "content_source": method})
            )
            logs.append(f"{doc.file_id}: OCR via {method} ({len(text)} chars)")
        elif doc.file_content_base64 and method == "groq_vision":
            updated.append(
                doc.model_copy(update={"content_source": "groq_vision", "quality": "UNREADABLE"})
            )
            degraded = True
            logs.append(f"{doc.file_id}: vision OCR marked UNREADABLE")
        else:
            updated.append(doc)
            logs.append(f"{doc.file_id}: no content extracted")

    return updated, logs, degraded
