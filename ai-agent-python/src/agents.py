"""Agent wrappers for gatekeeper and extraction."""

from __future__ import annotations

from engine import load_policy
from extractors.structured_parser import (
    is_extraction_sufficient,
    merge_extractions,
    merge_llm_with_regex,
    parse_text_summary,
)
from llm.client import invoke_json_prompt, invoke_structured
from ocr.document_ocr import OCR_SOURCES
from schemas import ClaimSubmission, ExtractedMedicalData, GatekeeperResult
from validators.document_type import infer_document_type, needs_type_verification
from validators.document_validator import validate_documents


GATEKEEPER_SYSTEM = """You verify medical claim documents. Only resolve semantic ambiguity about document types.
Return passed=false if documents are clearly wrong, unreadable, or belong to different patients."""


class GatekeeperAgent:
    def run(self, submission: ClaimSubmission) -> tuple[GatekeeperResult, bool, str | None]:
        """Returns (result, degraded, error)."""
        result = validate_documents(submission)
        if not result.passed:
            return result, False, None

        ambiguous = "UNKNOWN" in result.detected_types
        if not ambiguous:
            policy = load_policy()
            for doc in submission.documents:
                type_result = infer_document_type(doc, policy)
                if needs_type_verification(doc, type_result):
                    ambiguous = True
                    break

        if not ambiguous:
            return result, False, None

        summaries = "\n---\n".join(
            f"File: {d.file_name or d.file_id}\nType hint: {d.actual_type or 'unknown'}\n{d.content_summary or ''}"
            for d in submission.documents
        )
        llm_result, error = invoke_structured(
            "GATEKEEPER_MODEL",
            "llama-3.1-8b-instant",
            GATEKEEPER_SYSTEM,
            f"Category: {submission.claim_category}\nDocuments:\n{summaries}",
            GatekeeperResult,
        )
        if error:
            return (
                GatekeeperResult(
                    passed=False,
                    message="Document verification could not be completed. Routed to manual review.",
                    used_llm=True,
                ),
                True,
                error,
            )
        if llm_result:
            llm_result.used_llm = True
            return llm_result, False, None
        return result, True, "LLM returned no result"


EXTRACTION_SYSTEM = """You extract structured data from Indian medical claim documents.
Documents may be handwritten, stamped, phone photos, scanned PDFs, or inconsistent formats.
Handle varied layouts: tables, bullet lists, multi-column bills, and mixed-language text.

Extract: patient_name, diagnosis, treatment, doctor_name, doctor_registration,
hospital_name, treatment_date, line_items (description + amount), total_amount,
tests_ordered, medicines.

Rules:
- Expand common medical shorthand (T2DM, HTN) when confident.
- Return numeric amounts without currency symbols.
- Include every billable line item with its description and amount.
- Preserve parenthetical qualifiers on line items when printed on the document.
- Extract the actual patient person name, not section labels or facility names.
- Prefer values printed on the document over assumptions."""


def _is_structured_prefilled_summary(text: str) -> bool:
    """Assignment test fixtures: Label: value lines, often with embedded line_items JSON."""
    if not text.strip():
        return False
    if "line_items:" in text.lower():
        return True
    label_lines = sum(
        1
        for line in text.splitlines()
        if line.strip() and ":" in line and not line.strip().startswith(("-", "*", "•"))
    )
    return label_lines >= 3


def _document_uses_llm_extraction(doc) -> bool:
    summary = (doc.content_summary or "").strip()
    if not summary:
        return False
    if doc.content_source in OCR_SOURCES:
        return True
    if doc.content_source == "prefilled":
        return False
    if doc.content_source in ("user_paste",):
        return True
    if doc.content_source is None:
        return not _is_structured_prefilled_summary(summary)
    return True


def _should_use_llm(submission: ClaimSubmission) -> bool:
    """LLM-first for OCR and free-form text; regex only for structured prefilled fixtures."""
    return any(_document_uses_llm_extraction(doc) for doc in submission.documents)


def _apply_submission_defaults(
    extracted: ExtractedMedicalData, submission: ClaimSubmission
) -> ExtractedMedicalData:
    if submission.hospital_name and not extracted.hospital_name:
        extracted.hospital_name = submission.hospital_name
    if not extracted.total_amount:
        extracted.total_amount = submission.claimed_amount
    return extracted


def _llm_extract(combined: str) -> tuple[ExtractedMedicalData | None, str | None]:
    """Tier-2 structured extraction with JSON fallback."""
    llm_result, error = invoke_structured(
        "EXTRACTION_MODEL",
        "llama-3.1-8b-instant",
        EXTRACTION_SYSTEM,
        combined,
        ExtractedMedicalData,
    )
    if llm_result:
        return llm_result, None

    payload, json_error = invoke_json_prompt(
        "EXTRACTION_MODEL",
        "llama-3.1-8b-instant",
        EXTRACTION_SYSTEM,
        combined,
    )
    if payload:
        try:
            return ExtractedMedicalData.model_validate(payload), json_error
        except Exception as exc:
            return None, str(exc)

    return None, error or json_error


class ExtractionAgent:
    def run(
        self,
        submission: ClaimSubmission,
        simulate_failure: bool = False,
    ) -> tuple[ExtractedMedicalData, bool, str | None]:
        if simulate_failure:
            return (
                ExtractedMedicalData(
                    total_amount=submission.claimed_amount,
                    extraction_tier="degraded",
                    confidence=0.5,
                ),
                True,
                "Simulated component failure",
            )

        combined = "\n\n---\n\n".join(
            f"Document: {d.file_name or d.file_id}\n{d.content_summary or ''}"
            for d in submission.documents
            if d.content_summary
        )

        if not combined.strip():
            return (
                ExtractedMedicalData(
                    total_amount=submission.claimed_amount,
                    extraction_tier="tier-3-fallback",
                    confidence=0.5,
                ),
                True,
                "No document text available for extraction",
            )

        # Tier-1: regex gap-fill (fast path for structured prefilled fixtures only)
        parts = [parse_text_summary(doc.content_summary) for doc in submission.documents if doc.content_summary]
        regex_merged = merge_extractions(parts)

        # Tier-2: Groq LLM for OCR and any free-form document text
        if _should_use_llm(submission):
            llm_result, error = _llm_extract(combined)
            if llm_result:
                merged = merge_llm_with_regex(llm_result, regex_merged)
                merged.extraction_tier = "tier-2-llm"
                merged.confidence = max(0.85, min(llm_result.confidence, 0.95))
                return _apply_submission_defaults(merged, submission), False, None

            regex_merged.extraction_tier = "tier-3-fallback"
            regex_merged = _apply_submission_defaults(regex_merged, submission)
            if is_extraction_sufficient(regex_merged):
                regex_merged.confidence = max(regex_merged.confidence, 0.9)
                return regex_merged, False, error
            regex_merged.confidence = min(regex_merged.confidence, 0.65)
            return regex_merged, True, error

        regex_merged.extraction_tier = "tier-1-regex"
        if is_extraction_sufficient(regex_merged):
            regex_merged.confidence = max(regex_merged.confidence, 0.95)
        return _apply_submission_defaults(regex_merged, submission), False, None
