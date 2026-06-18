"""Structured data extraction from document text.

Regex/label parsing is a fast gap-fill for structured test fixtures only.
OCR and free-form uploads are handled by the LLM extraction tier in agents.py.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from schemas import ExtractedMedicalData, LineItem


def _parse_amount(value: str) -> float:
    cleaned = re.sub(r"[₹,\s]", "", value)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _clean_line(line: str) -> str:
    cleaned = re.sub(r"^[\s*\-•]+", "", line).strip()
    return re.sub(r"\*+", "", cleaned).strip()


def _extract_field(text: str, labels: list[str]) -> Optional[str]:
    for line in text.splitlines():
        cleaned = _clean_line(line)
        for label in sorted(labels, key=len, reverse=True):
            match = re.search(rf"{re.escape(label)}\s*:?\s*(.+)", cleaned, re.IGNORECASE)
            if match:
                return match.group(1).strip().strip("*")
    return None


def _parse_line_item(row: str) -> Optional[LineItem]:
    cleaned = _clean_line(row)
    if not cleaned or cleaned.lower().startswith(("description", "subtotal", "gst", "payment")):
        return None
    if "total" in cleaned.lower() and ":" in cleaned:
        return None

    match = re.search(
        r"^(.+?)\s+(?:Rs\.?|₹|INR)\s*([\d,]+(?:\.\d{1,2})?)\s*$",
        cleaned,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(r"^(.+?)\s+([\d,]+\.\d{2})\s*$", cleaned)
    if not match:
        match = re.search(r"^(.+?)\s+([\d,]+)\s*$", cleaned)
    if not match:
        return None

    description = match.group(1).strip().strip("*").rstrip(":")
    if not description or description.lower().startswith("total"):
        return None
    return LineItem(description=description, amount=_parse_amount(match.group(2)))


def normalize_ocr_text(text: str) -> str:
    return re.sub(r"\*+", "", text)


_INVALID_PATIENT_CAPTURES = frozenset(
    {"details", "information", "name", "details:", "information:", "name:"}
)


def is_plausible_person_name(value: str) -> bool:
    cleaned = _clean_line(value).strip(": ").strip()
    if not cleaned or len(cleaned) < 3:
        return False
    if cleaned.lower() in _INVALID_PATIENT_CAPTURES:
        return False
    if re.match(r"^(details|information|name)\s*:?\s*$", cleaned, re.IGNORECASE):
        return False
    parts = [part for part in cleaned.split() if re.search(r"[A-Za-z]", part)]
    return len(parts) >= 2


def extract_patient_name(text: str) -> Optional[str]:
    """Extract patient name from OCR text; ignores header lines like 'Patient Details:'."""
    normalized = normalize_ocr_text(text)
    for label in ("Patient Name", "Patient"):
        for line in normalized.splitlines():
            cleaned = _clean_line(line)
            match = re.search(rf"{re.escape(label)}\s*:?\s*(.+)", cleaned, re.IGNORECASE)
            if not match:
                continue
            candidate = match.group(1).strip()
            if is_plausible_person_name(candidate):
                return _clean_line(candidate)
    return None


def parse_text_summary(text: str) -> ExtractedMedicalData:
    text = normalize_ocr_text(text)
    patient = extract_patient_name(text) or _extract_field(text, ["Patient Name"])
    diagnosis = _extract_field(text, ["Diagnosis"])
    treatment = _extract_field(text, ["Treatment", "Procedure"])
    doctor = _extract_field(text, ["Doctor", "Doctor Name"])
    registration = _extract_field(text, ["Registration", "Doctor Registration", "Reg. No"])
    hospital = _extract_field(text, ["Hospital", "Hospital Name"])
    date = _extract_field(text, ["Date", "Treatment Date"])

    line_items: list[LineItem] = []
    total: Optional[float] = None

    if "line_items" in text:
        try:
            match = re.search(r"line_items:\s*(\[.*?\])", text, re.DOTALL | re.IGNORECASE)
            if match:
                items = json.loads(match.group(1))
                line_items = [
                    LineItem(description=i.get("description", ""), amount=float(i.get("amount", 0)))
                    for i in items
                ]
        except (json.JSONDecodeError, ValueError):
            pass

    if not line_items:
        for line in text.splitlines():
            item = _parse_line_item(line)
            if item:
                line_items.append(item)

    total_match = re.search(
        r"total\s*amount\s*:?\s*(?:Rs\.?|₹|INR)?\s*([\d,.]+)", text, re.IGNORECASE
    )
    if not total_match:
        total_match = re.search(r"total\s*:?\s*₹?\s*([\d,.]+)", text, re.IGNORECASE)
    if total_match:
        total = _parse_amount(total_match.group(1))

    if not doctor:
        doc_match = re.search(r"(Dr\.\s+[A-Za-z][A-Za-z .]+)", text)
        if doc_match:
            doctor = doc_match.group(1).strip()

    if not hospital:
        hosp_match = re.search(
            r"^([A-Z][A-Z0-9\s&]+(?:CENTRE|CENTER|CLINIC|HOSPITAL|PHARMACY))\s*$",
            text,
            re.MULTILINE,
        )
        if hosp_match and "bill" not in hosp_match.group(1).lower():
            hospital = hosp_match.group(1).strip()

    tests: list[str] = []
    tests_field = _extract_field(text, ["Tests Ordered", "Tests"])
    if tests_field:
        tests = [t.strip() for t in tests_field.split(",")]

    return ExtractedMedicalData(
        patient_name=patient,
        diagnosis=diagnosis,
        treatment=treatment,
        doctor_name=doctor,
        doctor_registration=registration,
        hospital_name=hospital,
        treatment_date=date,
        line_items=line_items,
        total_amount=total,
        tests_ordered=tests,
        extraction_tier="tier-1-regex",
        confidence=0.9 if patient or diagnosis else 0.7,
    )


def is_extraction_sufficient(data: ExtractedMedicalData) -> bool:
    has_clinical = bool(data.diagnosis or data.treatment or data.line_items)
    has_financial = bool(data.total_amount or data.line_items)
    if has_clinical and has_financial:
        return True
    if data.line_items and data.total_amount:
        return True
    return data.confidence >= 0.85 and has_clinical and has_financial


def merge_llm_with_regex(llm: ExtractedMedicalData, regex: ExtractedMedicalData) -> ExtractedMedicalData:
    """Prefer LLM fields; fill gaps from regex tier-1."""
    merged = llm.model_copy()
    for field in (
        "patient_name",
        "diagnosis",
        "treatment",
        "doctor_name",
        "doctor_registration",
        "hospital_name",
        "treatment_date",
        "total_amount",
    ):
        if getattr(merged, field) is None and getattr(regex, field) is not None:
            setattr(merged, field, getattr(regex, field))
    if not merged.line_items and regex.line_items:
        merged.line_items = regex.line_items
    if not merged.tests_ordered and regex.tests_ordered:
        merged.tests_ordered = regex.tests_ordered
    if not merged.medicines and regex.medicines:
        merged.medicines = regex.medicines
    return merged


def merge_extractions(parts: list[ExtractedMedicalData]) -> ExtractedMedicalData:
    merged = ExtractedMedicalData(extraction_tier="tier-1-regex", confidence=1.0)
    for part in parts:
        for field in (
            "patient_name",
            "diagnosis",
            "treatment",
            "doctor_name",
            "doctor_registration",
            "hospital_name",
            "treatment_date",
            "total_amount",
        ):
            if getattr(merged, field) is None and getattr(part, field) is not None:
                setattr(merged, field, getattr(part, field))
        merged.line_items.extend(part.line_items)
        merged.tests_ordered.extend(part.tests_ordered)
        merged.medicines.extend(part.medicines)
        merged.confidence = min(merged.confidence, part.confidence)
    merged.tests_ordered = list(dict.fromkeys(merged.tests_ordered))
    return merged
