"""Submission validator — cross-check form fields against extracted document data."""

from __future__ import annotations

from graph.state import ClaimGraphState, NodeName, append_trace
from schemas import DecisionType, ExtractedMedicalData
from validators.submission_validator import validate_submission_against_extracted


def submission_validator(state: ClaimGraphState) -> dict:
    submission = state["submission"]
    extracted = state.get("extracted") or ExtractedMedicalData(
        total_amount=submission.claimed_amount,
    )

    result = validate_submission_against_extracted(submission, extracted)

    updates: dict = {
        "submission_validation": result,
        **append_trace(
            NodeName.SUBMISSION_VALIDATOR.value,
            "FAILED" if not result.passed else "SUCCESS",
            result.message,
            {
                "rejection_reasons": result.rejection_reasons,
                "submitted_treatment_date": result.submitted_treatment_date,
                "document_dates": result.document_dates,
                "submitted_hospital_name": result.submitted_hospital_name,
                "document_hospital_names": result.document_hospital_names,
            },
        ),
    }

    if not result.passed:
        updates.update(
            {
                "skip_to_decision": True,
                "decision": DecisionType.PENDING,
                "approved_amount": 0.0,
                "reason": result.message,
                "confidence_score": 1.0,
                "rejection_reasons": result.rejection_reasons,
            }
        )

    return updates
