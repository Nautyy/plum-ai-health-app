"""Public claims adjudication graph for NestJS / LangGraph SDK / Studio."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

# LangGraph dev loads this file directly; ensure `src/` is on the path.
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from graph.public_builder import graph
from schemas import AdjudicationResponse, ClaimSubmission
from submission import build_submission_from_dict, state_to_response

# Re-export for test runner and scripts
__all__ = ["graph", "build_submission_from_dict", "run_adjudication"]


def _invoke_graph(payload: dict[str, Any]) -> dict[str, Any]:
    """Sync entrypoint for scripts; graph nodes are async for LangGraph dev."""
    return asyncio.run(graph.ainvoke(payload))


def run_adjudication(submission: ClaimSubmission) -> AdjudicationResponse:
    state = _invoke_graph({"submission": submission.model_dump()})
    return state_to_response(state)
