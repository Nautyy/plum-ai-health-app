"""Document type inference and readability checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from extractors.structured_parser import parse_text_summary
from policy.intent_match import count_intent_matches
from policy.rules_config import DOCUMENT_READABILITY, DOCUMENT_TYPE_SIGNALS
from schemas import ClaimDocument


@dataclass(frozen=True)
class DocumentTypeResult:
    doc_type: str
    confidence: float


def _has_parseable_amount(text: str) -> bool:
    return bool(
        re.search(
            r"(?:total\s*amount|total|amount|rs\.?|₹|inr)\s*:?\s*[\d,]+",
            text,
            re.IGNORECASE,
        )
    )


def infer_document_type(doc: ClaimDocument, policy: dict | None = None) -> DocumentTypeResult:
    if doc.actual_type and doc.actual_type.strip():
        return DocumentTypeResult(doc_type=doc.actual_type.strip().upper(), confidence=1.0)

    summary = (doc.content_summary or "").strip()
    if not summary:
        return DocumentTypeResult(doc_type="UNKNOWN", confidence=0.0)

    parsed = parse_text_summary(summary)
    text_lower = summary.lower()
    has_line_items = bool(parsed.line_items) or "line_items:" in text_lower
    has_amount = parsed.total_amount is not None or _has_parseable_amount(summary)
    has_clinical = bool(parsed.diagnosis or parsed.treatment or parsed.doctor_name)

    best_type = "UNKNOWN"
    best_score = 0.0

    for doc_type, rules in DOCUMENT_TYPE_SIGNALS.items():
        phrases = rules.get("intent_phrases") or []
        score = float(count_intent_matches(summary, phrases))

        if rules.get("boost_if_tests_ordered") and parsed.tests_ordered:
            score += 2.0
        if rules.get("boost_if_clinical_only") and has_clinical and not has_line_items and not has_amount:
            score += 2.0
        if rules.get("requires_amount") and not has_amount:
            score *= 0.25
        if doc_type == "HOSPITAL_BILL" and has_line_items and has_amount:
            score += 1.0

        normalized = score / max(len(phrases), 1)
        if normalized > best_score:
            best_score = normalized
            best_type = doc_type

    if best_type == "UNKNOWN" and has_clinical and not has_line_items:
        best_type = "PRESCRIPTION"
        best_score = 0.4
    elif best_type == "UNKNOWN" and has_line_items and has_amount:
        best_type = "HOSPITAL_BILL"
        best_score = 0.4

    return DocumentTypeResult(doc_type=best_type, confidence=min(best_score, 1.0))


def document_has_required_signals(
    doc: ClaimDocument,
    doc_type: str,
    policy: dict | None,
    patient_name: Optional[str],
) -> bool:
    rules = DOCUMENT_READABILITY.get(doc_type, {})
    required = rules.get("required_signals") or []
    if not required:
        return True

    summary = (doc.content_summary or "").strip()
    parsed = parse_text_summary(summary)

    for signal in required:
        if signal == "patient_name" and not patient_name:
            return False
        if signal == "amount" and parsed.total_amount is None and not _has_parseable_amount(summary):
            return False
        if signal == "diagnosis" and not parsed.diagnosis:
            return False
    return True


def is_document_unreadable(
    doc: ClaimDocument,
    doc_type: str,
    policy: dict | None,
    patient_name: Optional[str],
) -> bool:
    if doc.quality and doc.quality.upper() == "UNREADABLE":
        return True
    if doc.file_content_base64 and not (doc.content_summary or "").strip():
        return True

    summary = (doc.content_summary or "").strip()
    if not summary:
        return bool(doc.file_content_base64)

    if summary.upper().startswith("UNREADABLE"):
        return True

    if doc.content_source not in (None, "groq_vision", "groq_vision_pdf", "pypdf", "text_decode", "ocr"):
        return False

    if doc_type == "UNKNOWN":
        return len(summary) < 20

    return not document_has_required_signals(doc, doc_type, policy, patient_name)


def needs_type_verification(doc: ClaimDocument, result: DocumentTypeResult) -> bool:
    if doc.actual_type and doc.actual_type.strip():
        return False
    return result.doc_type == "UNKNOWN" or result.confidence < 0.35
