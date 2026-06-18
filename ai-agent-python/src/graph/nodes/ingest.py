"""Ingest submission — normalize API input into graph state."""

from __future__ import annotations

from graph.state import ClaimGraphState, NodeName, append_trace
from schemas import ClaimSubmission
from submission import build_submission_from_dict, initial_graph_state


def ingest_submission(state: ClaimGraphState) -> dict:
    raw = state.get("submission")
    try:
        if isinstance(raw, dict):
            submission = build_submission_from_dict(raw)
        elif isinstance(raw, ClaimSubmission):
            submission = raw
        else:
            submission = build_submission_from_dict(dict(state))
    except (ValueError, KeyError, TypeError) as exc:
        from schemas import DecisionType

        return {
            **initial_graph_state(
                ClaimSubmission(
                    member_id="UNKNOWN",
                    policy_id="PLUM_GHI_2024",
                    claim_category="CONSULTATION",
                    treatment_date="1970-01-01",
                    claimed_amount=-1,
                )
            ),
            "skip_to_decision": True,
            "decision": DecisionType.PENDING,
            "approved_amount": 0.0,
            "reason": f"Invalid claim submission: {exc}",
            **append_trace(
                NodeName.INGEST.value,
                "FAILED",
                f"Invalid claim submission: {exc}",
                {"error": str(exc)},
            ),
        }

    init = initial_graph_state(submission)
    return {
        **init,
        **append_trace(
            NodeName.INGEST.value,
            "SUCCESS",
            f"Claim ingested for member {submission.member_id} ({submission.claim_category})",
            {
                "member_id": submission.member_id,
                "claim_category": submission.claim_category,
                "document_count": len(submission.documents),
                "claimed_amount": submission.claimed_amount,
            },
        ),
    }
