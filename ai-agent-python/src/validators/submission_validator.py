"""Cross-validate form fields against extracted document data."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from extractors.structured_parser import parse_text_summary
from schemas import ClaimDocument, ClaimSubmission, ExtractedMedicalData, SubmissionValidationResult


def _parse_date(value: str) -> Optional[datetime]:
    cleaned = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def _to_iso_date(value: str) -> Optional[str]:
    parsed = _parse_date(value)
    return parsed.strftime("%Y-%m-%d") if parsed else None


def _format_display_date(iso_date: str) -> str:
    parsed = _parse_date(iso_date)
    if not parsed:
        return iso_date
    return parsed.strftime("%d %b %Y")


def _extract_date_from_text(text: str) -> Optional[str]:
    if not text.strip():
        return None

    for line in text.splitlines():
        cleaned = line.strip()
        match = re.search(
            r"(?:date|treatment\s+date|visit\s+date)\s*:?\s*(.+)",
            cleaned,
            re.IGNORECASE,
        )
        if match:
            iso = _to_iso_date(match.group(1).strip())
            if iso:
                return iso

    parsed = parse_text_summary(text)
    if parsed.treatment_date:
        return _to_iso_date(parsed.treatment_date)
    return None


def _extract_hospital_from_text(text: str) -> Optional[str]:
    if not text.strip():
        return None

    parsed = parse_text_summary(text)
    if parsed.hospital_name:
        return parsed.hospital_name.strip()

    for line in text.splitlines():
        match = re.search(
            r"(?:hospital(?:\s+name)?|clinic|medical\s+centre)\s*:?\s*(.+)",
            line.strip(),
            re.IGNORECASE,
        )
        if match:
            name = match.group(1).strip()
            if name:
                return name
    return None


def _normalize_hospital(name: str) -> str:
    normalized = re.sub(r"[^\w\s]", "", name.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _hospitals_match(left: str, right: str) -> bool:
    a = _normalize_hospital(left)
    b = _normalize_hospital(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return a in b or b in a


def _collect_document_dates(submission: ClaimSubmission) -> list[str]:
    dates: list[str] = []
    for doc in submission.documents:
        summary = doc.content_summary or ""
        iso = _extract_date_from_text(summary)
        if iso:
            dates.append(iso)
    return dates


def _collect_document_hospitals(
    submission: ClaimSubmission,
    extracted: ExtractedMedicalData,
) -> list[str]:
    names: list[str] = []
    if extracted.hospital_name:
        names.append(extracted.hospital_name.strip())

    for doc in submission.documents:
        summary = doc.content_summary or ""
        hospital = _extract_hospital_from_text(summary)
        if hospital:
            names.append(hospital)

    return list(dict.fromkeys(names))


def validate_submission_against_extracted(
    submission: ClaimSubmission,
    extracted: ExtractedMedicalData,
) -> SubmissionValidationResult:
    submitted_date = _to_iso_date(submission.treatment_date)
    document_dates = _collect_document_dates(submission)

    if extracted.treatment_date:
        iso = _to_iso_date(extracted.treatment_date)
        if iso and iso not in document_dates:
            document_dates.append(iso)

    document_dates = list(dict.fromkeys(document_dates))

    if submitted_date and len(document_dates) > 1 and len(set(document_dates)) > 1:
        dates_display = ", ".join(_format_display_date(d) for d in sorted(set(document_dates)))
        return SubmissionValidationResult(
            passed=False,
            message=(
                f"Documents show different treatment dates ({dates_display}). "
                "All documents must be for the same visit. Please verify and re-upload."
            ),
            rejection_reasons=["DOCUMENT_DATE_INCONSISTENT"],
            submitted_treatment_date=submitted_date,
            document_dates=document_dates,
        )

    if submitted_date and document_dates:
        mismatched = sorted({d for d in document_dates if d != submitted_date})
        if mismatched:
            doc_display = ", ".join(_format_display_date(d) for d in mismatched)
            return SubmissionValidationResult(
                passed=False,
                message=(
                    f"Treatment date you entered ({_format_display_date(submitted_date)}) "
                    f"does not match the date on your document(s) ({doc_display}). "
                    "Please correct the treatment date or upload documents for the visit date you entered."
                ),
                rejection_reasons=["TREATMENT_DATE_MISMATCH"],
                submitted_treatment_date=submitted_date,
                document_dates=document_dates,
            )

    submitted_hospital = (submission.hospital_name or "").strip()
    document_hospitals = _collect_document_hospitals(submission, extracted)

    if submitted_hospital and document_hospitals:
        if not any(_hospitals_match(submitted_hospital, name) for name in document_hospitals):
            doc_display = document_hospitals[0]
            return SubmissionValidationResult(
                passed=False,
                message=(
                    f"Hospital name you entered ({submitted_hospital}) does not match "
                    f"the hospital on your bill ({doc_display}). "
                    "Please correct the hospital name or upload the matching bill."
                ),
                rejection_reasons=["HOSPITAL_NAME_MISMATCH"],
                submitted_hospital_name=submitted_hospital,
                document_hospital_names=document_hospitals,
            )

    return SubmissionValidationResult(
        passed=True,
        message="Submitted details match the extracted document data.",
        submitted_treatment_date=submitted_date,
        document_dates=document_dates,
        submitted_hospital_name=submitted_hospital or None,
        document_hospital_names=document_hospitals,
    )
