"""Pydantic schemas for claims adjudication."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class DecisionType(str, Enum):
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    PENDING = "PENDING"


class ClaimDocument(BaseModel):
    file_id: str
    file_name: str = ""
    actual_type: Optional[str] = None
    mime_type: Optional[str] = None
    file_content_base64: Optional[str] = None
    content_summary: Optional[str] = None
    content_source: Optional[str] = None  # prefilled | groq_vision | pypdf | text_decode | user_paste
    quality: Optional[str] = None
    patient_name_on_doc: Optional[str] = None


class ClaimHistoryEntry(BaseModel):
    claim_id: str
    date: str
    amount: float
    provider: str = ""


class ClaimSubmission(BaseModel):
    member_id: str
    policy_id: str
    claim_category: str
    treatment_date: str
    claimed_amount: float
    documents: list[ClaimDocument] = Field(default_factory=list)
    ytd_claims_amount: float = 0
    claims_history: list[ClaimHistoryEntry] = Field(default_factory=list)
    hospital_name: Optional[str] = None
    simulate_component_failure: bool = False
    pre_authorization_id: Optional[str] = None
    claim_for: Optional[str] = None  # SELF | SPOUSE | CHILD | PARENT
    patient_name: Optional[str] = None


class LineItem(BaseModel):
    description: str
    amount: float
    approved: Optional[bool] = None
    rejection_reason: Optional[str] = None


class ExtractedMedicalData(BaseModel):
    patient_name: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    hospital_name: Optional[str] = None
    treatment_date: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)
    total_amount: Optional[float] = None
    tests_ordered: list[str] = Field(default_factory=list)
    medicines: list[str] = Field(default_factory=list)
    extraction_tier: str = "unknown"
    confidence: float = 1.0

    @model_validator(mode="before")
    @classmethod
    def coerce_llm_output(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        data = dict(data)
        treatment_raw = data.get("treatment")
        if isinstance(treatment_raw, list):
            meds = list(data.get("medicines") or [])
            items = list(data.get("line_items") or [])
            for entry in treatment_raw:
                if isinstance(entry, dict):
                    desc = entry.get("description") or entry.get("name") or "item"
                    meds.append(str(desc))
                    if entry.get("amount") is not None:
                        items.append({"description": str(desc), "amount": entry.get("amount")})
                elif entry:
                    meds.append(str(entry))
            data["medicines"] = meds
            data["line_items"] = items
            data["treatment"] = None

        for field in (
            "patient_name",
            "diagnosis",
            "treatment",
            "doctor_name",
            "doctor_registration",
            "hospital_name",
            "treatment_date",
        ):
            value = data.get(field)
            if value is not None and not isinstance(value, str):
                if isinstance(value, list):
                    data[field] = "; ".join(str(v) for v in value) or None
                else:
                    data[field] = str(value)

        for field in ("tests_ordered", "medicines", "line_items"):
            value = data.get(field)
            if value is None:
                data[field] = []
            elif isinstance(value, str):
                if field == "line_items":
                    data[field] = []
                else:
                    data[field] = [part.strip() for part in value.split(",") if part.strip()]

        if data.get("total_amount") is not None and not isinstance(data["total_amount"], (int, float)):
            try:
                data["total_amount"] = float(
                    str(data["total_amount"]).replace(",", "").replace("₹", "").strip()
                )
            except ValueError:
                data["total_amount"] = None

        return data


class GatekeeperResult(BaseModel):
    passed: bool
    message: str = ""
    detected_types: list[str] = Field(default_factory=list)
    missing_types: list[str] = Field(default_factory=list)
    unreadable_files: list[str] = Field(default_factory=list)
    patient_names_found: list[str] = Field(default_factory=list)
    used_llm: bool = False


class SubmissionValidationResult(BaseModel):
    passed: bool
    message: str = ""
    rejection_reasons: list[str] = Field(default_factory=list)
    submitted_treatment_date: Optional[str] = None
    document_dates: list[str] = Field(default_factory=list)
    submitted_hospital_name: Optional[str] = None
    document_hospital_names: list[str] = Field(default_factory=list)


class PolicyEvaluationResult(BaseModel):
    decision: DecisionType
    approved_amount: float = 0
    reason: str = ""
    rejection_reasons: list[str] = Field(default_factory=list)
    line_item_decisions: list[LineItem] = Field(default_factory=list)
    financial_breakdown: dict[str, Any] = Field(default_factory=dict)
    eligible_from_date: Optional[str] = None
    fraud_signals: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class TraceEntry(BaseModel):
    step: str
    status: str
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    degraded: bool = False


class AdjudicationResponse(BaseModel):
    claim_id: str
    decision: DecisionType
    approved_amount: float = 0
    reason: str = ""
    member_reason: str = ""
    confidence_score: float = 1.0
    execution_trace: list[TraceEntry] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    line_item_decisions: list[LineItem] = Field(default_factory=list)
    financial_breakdown: dict[str, Any] = Field(default_factory=dict)
