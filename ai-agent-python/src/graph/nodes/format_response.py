"""Format response — flatten state for API / LangGraph SDK consumers."""

from __future__ import annotations

from graph.state import ClaimGraphState, NodeName, append_trace
from submission import state_to_response


def format_response(state: ClaimGraphState) -> dict:
    response = state_to_response(state)
    data = response.model_dump()

    return {
        **data,
        "policy_result": state.get("policy_result"),
        "extracted": state.get("extracted"),
        "gatekeeper": state.get("gatekeeper"),
        **append_trace(
            NodeName.FORMAT.value,
            "SUCCESS",
            f"Response ready: {response.decision.value} — INR {response.approved_amount:,.0f}",
            {
                "decision": response.decision.value,
                "approved_amount": response.approved_amount,
                "confidence_score": response.confidence_score,
            },
        ),
    }
