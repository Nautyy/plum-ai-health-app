"""Graph routing logic."""

from __future__ import annotations

from graph.state import ClaimGraphState, NodeName


def route_after_gatekeeper(state: ClaimGraphState) -> str:
    if state.get("skip_to_decision") or not state.get("gatekeeper_passed", True):
        return NodeName.DECISION.value
    return NodeName.EXTRACTION.value


def route_after_submission_validator(state: ClaimGraphState) -> str:
    if state.get("skip_to_decision"):
        return NodeName.DECISION.value
    return NodeName.POLICY.value
