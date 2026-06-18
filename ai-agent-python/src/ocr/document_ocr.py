"""OCR and document text extraction."""

from __future__ import annotations

import base64
import io
from typing import Optional

from ocr.preprocess import preprocess_image_base64
from ocr.prompts import OCR_VISION_PROMPT
from schemas import ClaimDocument

DEFAULT_OCR_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

OCR_SOURCES = frozenset({"groq_vision", "groq_vision_pdf", "pypdf", "text_decode", "ocr"})


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


def _parse_vision_response(text: str) -> tuple[str, bool, bool]:
    """Returns (text, is_unreadable, is_degraded)."""
    cleaned = str(text).strip()
    if not cleaned:
        return "", True, True
    if cleaned.upper().startswith("UNREADABLE"):
        return "", True, True
    degraded = "OCR_NOTE:" in cleaned
    return cleaned, False, degraded


def _invoke_vision_ocr(content_base64: str, mime: str) -> tuple[str, Optional[str], bool]:
    """Returns (text, error, degraded)."""
    try:
        from langchain_core.messages import HumanMessage
        from llm.client import get_chat_model

        llm = get_chat_model("OCR_MODEL", DEFAULT_OCR_MODEL)
        if llm is None:
            return "", "OCR unavailable: GROQ_API_KEY not configured", False

        message = HumanMessage(
            content=[
                {"type": "text", "text": OCR_VISION_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{content_base64}"},
                },
            ]
        )
        response = llm.invoke([message])
        raw = response.content if hasattr(response, "content") else str(response)
        text, unreadable, degraded = _parse_vision_response(raw)
        if unreadable:
            return "", None, True
        return text, None, degraded
    except Exception as exc:
        return "", str(exc), True


def _extract_scanned_pdf_with_vision(content_base64: str) -> tuple[str, Optional[str], str]:
    """Rasterize PDF pages and OCR each with vision (multi-page scanned bills)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "", "PyMuPDF not installed for scanned PDF OCR", "pypdf"

    try:
        raw = base64.b64decode(content_base64)
        pdf = fitz.open(stream=raw, filetype="pdf")
        parts: list[str] = []
        any_degraded = False

        for index, page in enumerate(pdf):
            pix = page.get_pixmap(dpi=150)
            png_b64 = base64.b64encode(pix.tobytes("png")).decode()
            page_text, error, degraded = _invoke_vision_ocr(png_b64, "image/png")
            any_degraded = any_degraded or degraded
            if error and not page_text:
                continue
            if page_text:
                parts.append(f"--- Page {index + 1} ---\n{page_text}")

        combined = "\n\n".join(parts).strip()
        if combined:
            return combined, None, "groq_vision_pdf"
        return "", "Scanned PDF vision OCR returned no text", "groq_vision_pdf"
    except Exception as exc:
        return "", str(exc), "groq_vision_pdf"


def _extract_image_with_vision(content_base64: str, mime: str) -> tuple[str, Optional[str], str, bool]:
    """Preprocess image then vision OCR. Returns (text, error, method, degraded)."""
    if mime.startswith("image/"):
        content_base64 = preprocess_image_base64(content_base64, mime)
    text, error, degraded = _invoke_vision_ocr(content_base64, mime or "image/jpeg")
    return text, error, "groq_vision", degraded


def extract_document_text(doc: ClaimDocument) -> tuple[str, Optional[str], str, bool]:
    """Returns (text, error, method, degraded)."""
    if doc.content_summary:
        return doc.content_summary, None, "prefilled", False

    if not doc.file_content_base64:
        return "", None, "skipped", False

    mime = (doc.mime_type or "").lower()

    if mime.startswith("text/"):
        try:
            return decode_text_file(doc.file_content_base64), None, "text_decode", False
        except Exception as exc:
            return "", str(exc), "text_decode", True

    if mime == "application/pdf":
        text, err = extract_pdf_text(doc.file_content_base64)
        if text.strip():
            return text, None, "pypdf", False
        # Scanned / image-only PDF — fall back to per-page vision OCR
        text, err, method = _extract_scanned_pdf_with_vision(doc.file_content_base64)
        if text:
            degraded = "OCR_NOTE:" in text
            return text, None, method, degraded
        return "", err, method if method else "pypdf", True

    if mime.startswith("image/") or not mime:
        text, error, method, degraded = _extract_image_with_vision(
            doc.file_content_base64, mime or "image/jpeg"
        )
        return text, error, method, degraded

    # Unknown mime — try as image
    text, error, method, degraded = _extract_image_with_vision(
        doc.file_content_base64, mime or "image/jpeg"
    )
    return text, error, method, degraded


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

        text, error, method, step_degraded = extract_document_text(doc)
        degraded = degraded or step_degraded

        if error and not text:
            degraded = True
            logs.append(f"{doc.file_id}: OCR {method} failed — {error}")
            updated.append(doc)
            continue

        if text:
            updated.append(
                doc.model_copy(update={"content_summary": text, "content_source": method})
            )
            note = " (partial/low-confidence fields)" if step_degraded else ""
            logs.append(f"{doc.file_id}: OCR via {method} ({len(text)} chars){note}")
        elif method in ("groq_vision", "groq_vision_pdf"):
            updated.append(
                doc.model_copy(update={"content_source": method, "quality": "UNREADABLE"})
            )
            degraded = True
            logs.append(f"{doc.file_id}: vision OCR marked UNREADABLE")
        else:
            updated.append(doc)
            logs.append(f"{doc.file_id}: no content extracted")

    return updated, logs, degraded
