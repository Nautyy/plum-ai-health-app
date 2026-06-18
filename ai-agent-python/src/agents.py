"""Agent wrappers for gatekeeper and extraction."""

from __future__ import annotations

from schemas import ClaimSubmission, ExtractedMedicalData, GatekeeperResult, LineItem
from validators.document_validator import validate_documents
from extractors.structured_parser import (
    is_extraction_sufficient,
    merge_extractions,
    merge_llm_with_regex,
    parse_text_summary,
)
from llm.client import invoke_json_prompt, invoke_structured
from ocr.document_ocr import OCR_SOURCES


GATEKEEPER_SYSTEM = """You verify medical claim documents. Only resolve semantic ambiguity about document types.
Return passed=false if documents are clearly wrong, unreadable, or belong to different patients."""


class GatekeeperAgent:
    def run(self, submission: ClaimSubmission) -> tuple[GatekeeperResult, bool, str | None]:
        """Returns (result, degraded, error)."""
        result = validate_documents(submission)
        if not result.passed:
            return result, False, None

        ambiguous = any(
            doc.content_summary and "document type:" in doc.content_summary.lower()
            for doc in submission.documents
        ) or "UNKNOWN" in result.detected_types

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
Documents may be handwritten, stamped, phone photos, or inconsistent formats.
Extract: patient_name, diagnosis, treatment, doctor_name, doctor_registration,
hospital_name, treatment_date, line_items (description + amount), total_amount,
tests_ordered, medicines.
Use medical shorthand (T2DM = Type 2 Diabetes, HTN = Hypertension).
Return numeric amounts without currency symbols."""


def _has_ocr_sourced_docs(submission: ClaimSubmission) -> bool:
    return any(
        doc.content_source in OCR_SOURCES for doc in submission.documents
    )


def _should_use_llm(regex_merged: ExtractedMedicalData, submission: ClaimSubmission) -> bool:
    all_prefilled = all(
        (not doc.content_summary) or doc.content_source in (None, "prefilled")
        for doc in submission.documents
        if doc.content_summary
    )
    if all_prefilled and is_extraction_sufficient(regex_merged):
        return False
    if _has_ocr_sourced_docs(submission):
        return True
    if not is_extraction_sufficient(regex_merged):
        return True
    return False


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

        # Tier-1: regex / label parsing
        parts = [parse_text_summary(doc.content_summary) for doc in submission.documents if doc.content_summary]
        regex_merged = merge_extractions(parts)

        # Tier-2: Groq LLM when OCR-sourced or regex confidence is low
        if _should_use_llm(regex_merged, submission):
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
