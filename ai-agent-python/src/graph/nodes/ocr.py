"""OCR node — populate content_summary from uploaded files."""

from __future__ import annotations

from graph.async_helpers import run_in_thread
from graph.state import ClaimGraphState, NodeName, append_trace
from ocr.document_ocr import run_ocr_on_documents


def _ocr_agent_sync(state: ClaimGraphState) -> dict:
    submission = state["submission"]
    documents = submission.documents

    updated, logs, degraded = run_ocr_on_documents(documents)
    updated_submission = submission.model_copy(update={"documents": updated})

    return {
        "submission": updated_submission,
        "documents": updated,
        **append_trace(
            NodeName.OCR.value,
            "DEGRADED" if degraded else "SUCCESS",
            "; ".join(logs) if logs else "OCR completed",
            {"logs": logs},
            degraded=degraded,
        ),
        "degraded_steps": (state.get("degraded_steps") or []) + (["ocr"] if degraded else []),
    }


async def ocr_agent(state: ClaimGraphState) -> dict:
    return await run_in_thread(_ocr_agent_sync, state)
