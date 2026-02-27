"""Detective graph: only relevant detectives run, then aggregator -> report_accuracy -> judges -> chief_justice.

Graph flow:
  START -> run_detectives (repo and/or doc/vision by input)
       -> evidence_aggregator (fill missing dimensions)
       -> conditional: proceed -> report_accuracy -> judicial_panel -> chief_justice -> END | skip -> END
"""

from langgraph.graph import END, START, StateGraph

from src.state import AgentState
from src.nodes.aggregator import EvidenceAggregatorNode
from src.nodes.detectives import RunRelevantDetectivesNode
from src.nodes.judges import JudicialPanelNode
from src.nodes.justice import ChiefJusticeNode
from src.nodes.report_accuracy import ReportAccuracyNode


def _route_after_aggregator(state: dict) -> str:
    """Proceed when we have any evidence (aggregator fills missing dimensions)."""
    evidences = state.get("evidences") or {}
    has_any = bool(evidences and any(evidences.values()))
    return "proceed" if has_any else "skip"


def build_detective_graph():
    g = StateGraph(AgentState)
    g.add_node("run_detectives", RunRelevantDetectivesNode)
    g.add_node("evidence_aggregator", EvidenceAggregatorNode)
    g.add_node("report_accuracy", ReportAccuracyNode)
    g.add_node("judicial_panel", JudicialPanelNode)
    g.add_node("chief_justice", ChiefJusticeNode)

    g.add_edge(START, "run_detectives")
    g.add_edge("run_detectives", "evidence_aggregator")
    g.add_conditional_edges(
        "evidence_aggregator",
        _route_after_aggregator,
        {"proceed": "report_accuracy", "skip": END},
    )
    g.add_edge("report_accuracy", "judicial_panel")
    g.add_edge("judicial_panel", "chief_justice")
    g.add_edge("chief_justice", END)

    return g.compile()
