"""LangGraph state and trace helpers."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Optional
import operator

from typing_extensions import TypedDict

from schemas import (
    ClaimDocument,
    ClaimSubmission,
    DecisionType,
    ExtractedMedicalData,
    GatekeeperResult,
    PolicyEvaluationResult,
    TraceEntry,
)


class NodeName(str, Enum):
    INGEST = "ingest_submission"
    OCR = "ocr_agent"
    GATEKEEPER = "gatekeeper_agent"
    EXTRACTION = "extraction_agent"
    SUBMISSION_VALIDATOR = "submission_validator"
    POLICY = "policy_engine"
    DECISION = "decision_consolidator"
    FORMAT = "format_response"


class ConfidencePenalty(float, Enum):
    OCR_FAILURE = 0.1
    GATEKEEPER_LLM_FAILURE = 0.25
    EXTRACTION_DEGRADED = 0.15
    COMPONENT_FAILURE = 0.25


class ClaimGraphState(TypedDict, total=False):
    submission: ClaimSubmission
    claim_id: str
    documents: list[ClaimDocument]
    gatekeeper: GatekeeperResult
    gatekeeper_passed: bool
    extracted: ExtractedMedicalData
    policy_result: PolicyEvaluationResult
    decision: DecisionType
    approved_amount: float
    reason: str
    confidence_score: float
    rejection_reasons: list[str]
    execution_trace: Annotated[list[TraceEntry], operator.add]
    degraded_steps: list[str]
    skip_to_decision: bool


def append_trace(
    step: str,
    status: str,
    message: str = "",
    details: Optional[dict[str, Any]] = None,
    degraded: bool = False,
) -> dict[str, list[TraceEntry]]:
    return {
        "execution_trace": [
            TraceEntry(
                step=step,
                status=status,
                message=message,
                details=details or {},
                degraded=degraded,
            )
        ]
    }
