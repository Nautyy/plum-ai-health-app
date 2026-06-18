"""Policy engine node — deterministic rules from policy_terms.json."""

from __future__ import annotations

import logging

from engine import DynamicPolicyEngine
from graph.state import ClaimGraphState, NodeName, append_trace
from schemas import DecisionType, ExtractedMedicalData, PolicyEvaluationResult

logger = logging.getLogger(__name__)


def policy_engine(state: ClaimGraphState) -> dict:
    submission = state["submission"]
    extracted = state.get("extracted")
    engine = DynamicPolicyEngine()

    if extracted is None:
        extracted = ExtractedMedicalData(total_amount=submission.claimed_amount)

    try:
        result = engine.evaluate(submission, extracted)
    except Exception as exc:
        logger.exception("Policy evaluation failed")
        result = PolicyEvaluationResult(
            decision=DecisionType.MANUAL_REVIEW,
            reason="Policy evaluation encountered an unexpected error. Routed for manual review.",
            rejection_reasons=["POLICY_EVALUATION_ERROR"],
        )
        return {
            "policy_result": result,
            **append_trace(
                NodeName.POLICY.value,
                DecisionType.MANUAL_REVIEW.value,
                result.reason,
                {"error": str(exc), "rejection_reasons": result.rejection_reasons},
                degraded=True,
            ),
        }

    return {
        "policy_result": result,
        **append_trace(
            NodeName.POLICY.value,
            result.decision.value,
            result.reason,
            {
                "rejection_reasons": result.rejection_reasons,
                "approved_amount": result.approved_amount,
                "fraud_signals": result.fraud_signals,
                "financial_breakdown": result.financial_breakdown,
            },
        ),
    }
