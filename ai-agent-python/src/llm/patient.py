"""LLM helpers for semantic field extraction from OCR text."""

from __future__ import annotations

from pydantic import BaseModel

from llm.client import invoke_structured


class PatientNameExtract(BaseModel):
    patient_name: str | None = None


PATIENT_NAME_SYSTEM = """Extract the patient's full name from Indian medical document OCR text.
Return null when the text has only section labels, clinic names, or no clear person name.
Do not return doctor names, facility names, or pharmacy names."""


def extract_patient_name_llm(text: str) -> str | None:
    """Semantic patient-name extraction when label/regex parsing is unreliable."""
    if not text.strip():
        return None
    result, _ = invoke_structured(
        "EXTRACTION_MODEL",
        "llama-3.1-8b-instant",
        PATIENT_NAME_SYSTEM,
        text[:6000],
        PatientNameExtract,
    )
    if not result or not result.patient_name:
        return None
    return result.patient_name.strip()
