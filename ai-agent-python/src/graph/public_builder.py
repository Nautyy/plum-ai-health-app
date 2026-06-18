"""Production graph — all pipeline steps visible in LangGraph Studio."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from graph.nodes.decision import decision_consolidator
from graph.nodes.extraction import extraction_agent
from graph.nodes.format_response import format_response
from graph.nodes.gatekeeper import gatekeeper_agent
from graph.nodes.ingest import ingest_submission
from graph.nodes.ocr import ocr_agent
from graph.nodes.policy import policy_engine
from graph.nodes.submission_validator import submission_validator
from graph.routing import route_after_gatekeeper, route_after_submission_validator
from graph.state import ClaimGraphState, NodeName


def build_public_graph():
    """
    Visible pipeline (Studio + production):

    ingest_submission → ocr_agent → gatekeeper_agent
          ├─ (fail) ──────────────────────→ decision_consolidator → format_response
          └─ (pass) → extraction_agent → submission_validator
                ├─ (fail) ──────────────→ decision_consolidator → format_response
                └─ (pass) → policy_engine → decision_consolidator → format_response
    """
    graph = StateGraph(ClaimGraphState)

    graph.add_node(NodeName.INGEST.value, ingest_submission)
    graph.add_node(NodeName.OCR.value, ocr_agent)
    graph.add_node(NodeName.GATEKEEPER.value, gatekeeper_agent)
    graph.add_node(NodeName.EXTRACTION.value, extraction_agent)
    graph.add_node(NodeName.SUBMISSION_VALIDATOR.value, submission_validator)
    graph.add_node(NodeName.POLICY.value, policy_engine)
    graph.add_node(NodeName.DECISION.value, decision_consolidator)
    graph.add_node(NodeName.FORMAT.value, format_response)

    graph.add_edge(START, NodeName.INGEST.value)
    graph.add_edge(NodeName.INGEST.value, NodeName.OCR.value)
    graph.add_edge(NodeName.OCR.value, NodeName.GATEKEEPER.value)
    graph.add_conditional_edges(
        NodeName.GATEKEEPER.value,
        route_after_gatekeeper,
        {
            NodeName.EXTRACTION.value: NodeName.EXTRACTION.value,
            NodeName.DECISION.value: NodeName.DECISION.value,
        },
    )
    graph.add_edge(NodeName.EXTRACTION.value, NodeName.SUBMISSION_VALIDATOR.value)
    graph.add_conditional_edges(
        NodeName.SUBMISSION_VALIDATOR.value,
        route_after_submission_validator,
        {
            NodeName.POLICY.value: NodeName.POLICY.value,
            NodeName.DECISION.value: NodeName.DECISION.value,
        },
    )
    graph.add_edge(NodeName.POLICY.value, NodeName.DECISION.value)
    graph.add_edge(NodeName.DECISION.value, NodeName.FORMAT.value)
    graph.add_edge(NodeName.FORMAT.value, END)

    return graph.compile()


graph = build_public_graph()
