"""Extraction node — structured data from documents."""

from __future__ import annotations

from agents import ExtractionAgent
from graph.async_helpers import run_in_thread
from graph.state import ClaimGraphState, ConfidencePenalty, NodeName, append_trace
from schemas import ExtractedMedicalData


def _extraction_agent_sync(state: ClaimGraphState) -> dict:
    submission = state["submission"]
    agent = ExtractionAgent()
    try:
        extracted, degraded, error = agent.run(
            submission,
            simulate_failure=submission.simulate_component_failure,
        )
    except Exception as exc:
        extracted = ExtractedMedicalData(
            total_amount=submission.claimed_amount,
            extraction_tier="tier-3-fallback",
            confidence=0.6,
        )
        degraded = True
        error = str(exc)

    return {
        "extracted": extracted,
        **append_trace(
            NodeName.EXTRACTION.value,
            "DEGRADED" if degraded else "SUCCESS",
            f"Extraction via {extracted.extraction_tier}",
            {
                "confidence": extracted.confidence,
                "error": error,
                "patient_name": extracted.patient_name,
                "diagnosis": extracted.diagnosis,
                "total_amount": extracted.total_amount,
            },
            degraded=degraded,
        ),
        "degraded_steps": (state.get("degraded_steps") or []) + (["extraction"] if degraded else []),
        "confidence_score": max(0.5, 1.0 - ConfidencePenalty.EXTRACTION_DEGRADED.value) if degraded else 1.0,
    }


async def extraction_agent(state: ClaimGraphState) -> dict:
    return await run_in_thread(_extraction_agent_sync, state)
