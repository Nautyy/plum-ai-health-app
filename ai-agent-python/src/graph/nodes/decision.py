"""Decision consolidator — final decision, reason, confidence."""

from __future__ import annotations

from graph.state import ClaimGraphState, ConfidencePenalty, NodeName, append_trace
from schemas import DecisionType


def decision_consolidator(state: ClaimGraphState) -> dict:
    degraded_steps = state.get("degraded_steps") or []

    if state.get("skip_to_decision") and state.get("decision") == DecisionType.PENDING:
        return append_trace(
            NodeName.DECISION.value,
            DecisionType.PENDING.value,
            state.get("reason", "Document validation failed"),
            {"early_stop": True},
        )

    if state.get("skip_to_decision") and state.get("decision") == DecisionType.MANUAL_REVIEW:
        return append_trace(
            NodeName.DECISION.value,
            DecisionType.MANUAL_REVIEW.value,
            state.get("reason", "Manual review required"),
            {"gatekeeper_llm_failure": True},
            degraded=True,
        )

    policy = state.get("policy_result")
    extracted = state.get("extracted")
    confidence = state.get("confidence_score", 1.0)

    if policy is None:
        return {
            "decision": DecisionType.MANUAL_REVIEW,
            "approved_amount": 0.0,
            "reason": "Policy evaluation did not complete.",
            "confidence_score": 0.5,
            **append_trace(NodeName.DECISION.value, "MANUAL_REVIEW", "No policy result"),
        }

    decision = policy.decision
    reason = policy.reason
    approved = policy.approved_amount

    if degraded_steps:
        penalty = ConfidencePenalty.COMPONENT_FAILURE.value * len(degraded_steps)
        confidence = max(0.5, min(confidence, 1.0) - penalty)
        if decision == DecisionType.APPROVED and confidence < 0.75:
            reason += " Manual review recommended due to incomplete processing."
        degraded = confidence < 0.75
    else:
        degraded = False
        if extracted and extracted.confidence < 1.0:
            confidence = min(confidence, extracted.confidence)

    if policy.confidence < 1.0:
        confidence = min(confidence, policy.confidence)

    return {
        "decision": decision,
        "approved_amount": approved,
        "reason": reason,
        "confidence_score": round(confidence, 2),
        "rejection_reasons": policy.rejection_reasons,
        "line_item_decisions": policy.line_item_decisions,
        "financial_breakdown": policy.financial_breakdown,
        **append_trace(
            NodeName.DECISION.value,
            decision.value,
            reason,
            {
                "approved_amount": approved,
                "confidence_score": round(confidence, 2),
                "degraded_steps": degraded_steps,
                "line_item_decisions": [li.model_dump() for li in policy.line_item_decisions],
                "financial_breakdown": policy.financial_breakdown,
            },
            degraded=degraded,
        ),
    }
