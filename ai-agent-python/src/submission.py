"""Claim submission building and API response formatting."""

from __future__ import annotations

import json
import uuid
from typing import Any

from member_messages import build_member_reason
from schemas import (
    AdjudicationResponse,
    ClaimDocument,
    ClaimSubmission,
    DecisionType,
    TraceEntry,
)


def content_dict_to_summary(content: dict) -> str:
    lines = []
    for key, value in content.items():
        if key == "line_items":
            lines.append(f"line_items: {json.dumps(value)}")
        elif isinstance(value, list):
            lines.append(f"{key.replace('_', ' ').title()}: {', '.join(str(v) for v in value)}")
        else:
            label = key.replace("_", " ").title()
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        return default


def _require_str(data: dict[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"Missing required field: {label}")
    return str(value).strip()


def build_submission_from_dict(data: dict[str, Any]) -> ClaimSubmission:
    documents = []
    for doc in data.get("documents", []):
        content_summary = doc.get("content_summary")
        if not content_summary and doc.get("content"):
            content_summary = content_dict_to_summary(doc["content"])

        content_source = doc.get("content_source")
        if not content_source and content_summary and doc.get("content"):
            content_source = "prefilled"

        documents.append(
            ClaimDocument(
                file_id=doc.get("file_id", str(uuid.uuid4())[:8]),
                file_name=doc.get("file_name", doc.get("file_id", "document")),
                actual_type=doc.get("actual_type"),
                mime_type=doc.get("mime_type"),
                file_content_base64=doc.get("file_content_base64"),
                content_summary=content_summary,
                content_source=content_source,
                quality=doc.get("quality"),
                patient_name_on_doc=doc.get("patient_name_on_doc"),
            )
        )

    return ClaimSubmission(
        member_id=_require_str(data, "member_id", "member_id"),
        policy_id=str(data.get("policy_id") or "PLUM_GHI_2024"),
        claim_category=_require_str(data, "claim_category", "claim_category"),
        treatment_date=_require_str(data, "treatment_date", "treatment_date"),
        claimed_amount=_safe_float(data.get("claimed_amount"), default=-1.0),
        documents=documents,
        ytd_claims_amount=_safe_float(data.get("ytd_claims_amount"), default=0.0),
        claims_history=data.get("claims_history") or [],
        hospital_name=data.get("hospital_name"),
        simulate_component_failure=bool(data.get("simulate_component_failure", False)),
        pre_authorization_id=data.get("pre_authorization_id") or None,
        claim_for=(str(data.get("claim_for")).strip().upper() if data.get("claim_for") else None),
        patient_name=(str(data.get("patient_name")).strip() if data.get("patient_name") else None),
    )


def initial_graph_state(submission: ClaimSubmission) -> dict[str, Any]:
    claim_id = f"CLM_{uuid.uuid4().hex[:8].upper()}"
    return {
        "submission": submission,
        "claim_id": claim_id,
        "documents": submission.documents,
        "execution_trace": [],
        "degraded_steps": [],
        "confidence_score": 1.0,
    }


def state_to_response(state: dict[str, Any]) -> AdjudicationResponse:
    policy = state.get("policy_result")
    trace = state.get("execution_trace") or []
    trace = [TraceEntry(**t) if isinstance(t, dict) else t for t in trace]

    decision = state.get("decision", DecisionType.MANUAL_REVIEW)
    rejection_reasons = state.get("rejection_reasons") or (policy.rejection_reasons if policy else [])
    line_item_decisions = policy.line_item_decisions if policy else []
    financial_breakdown = policy.financial_breakdown if policy else {}

    return AdjudicationResponse(
        claim_id=state.get("claim_id", "UNKNOWN"),
        decision=decision,
        approved_amount=float(state.get("approved_amount", 0)),
        reason=state.get("reason", ""),
        member_reason=build_member_reason(
            decision=decision,
            approved_amount=float(state.get("approved_amount", 0)),
            rejection_reasons=rejection_reasons,
            line_item_decisions=line_item_decisions,
            financial_breakdown=financial_breakdown,
            ops_reason=state.get("reason", ""),
        ),
        confidence_score=float(state.get("confidence_score", 1.0)),
        execution_trace=trace,
        rejection_reasons=rejection_reasons,
        line_item_decisions=line_item_decisions,
        financial_breakdown=financial_breakdown,
    )
