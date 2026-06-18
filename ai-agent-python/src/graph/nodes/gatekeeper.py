"""Gatekeeper node — early document validation."""

from __future__ import annotations

from agents import GatekeeperAgent
from graph.async_helpers import run_in_thread
from graph.state import ClaimGraphState, ConfidencePenalty, NodeName, append_trace
from schemas import DecisionType


def _gatekeeper_agent_sync(state: ClaimGraphState) -> dict:
    submission = state["submission"]
    agent = GatekeeperAgent()
    result, degraded, error = agent.run(submission)

    updates: dict = {
        "gatekeeper": result,
        "gatekeeper_passed": result.passed,
        **append_trace(
            NodeName.GATEKEEPER.value,
            "FAILED" if not result.passed else ("DEGRADED" if degraded else "SUCCESS"),
            result.message,
            {
                "detected_types": result.detected_types,
                "missing_types": result.missing_types,
                "patient_names": result.patient_names_found,
                "used_llm": result.used_llm,
                "error": error,
            },
            degraded=degraded,
        ),
    }

    if not result.passed:
        updates["skip_to_decision"] = True
        updates["decision"] = DecisionType.PENDING
        updates["approved_amount"] = 0.0
        updates["reason"] = result.message
        updates["confidence_score"] = 1.0

    if degraded and not result.passed:
        updates["decision"] = DecisionType.MANUAL_REVIEW
        updates["reason"] = result.message
        updates["confidence_score"] = 1.0 - ConfidencePenalty.GATEKEEPER_LLM_FAILURE.value
        updates["degraded_steps"] = (state.get("degraded_steps") or []) + ["gatekeeper_llm"]

    return updates


async def gatekeeper_agent(state: ClaimGraphState) -> dict:
    return await run_in_thread(_gatekeeper_agent_sync, state)
