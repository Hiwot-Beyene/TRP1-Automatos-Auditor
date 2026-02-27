"""Detective graph: parallel detectives fan-in to EvidenceAggregator.

Graph flow:
  START -> [repo_investigator, doc_analyst, vision_inspector] (parallel fan-out)
       -> evidence_aggregator (fan-in)
       -> conditional: proceed -> END | skip -> END (skip = Evidence Missing / Node Failure)

Error handling: Skip is the primary path for missing evidence (fail fast). Transient failures
(e.g. clone timeout) are retried with backoff inside sandboxed_clone; after retries exhausted we still skip.

Judicial layer attachment (planned):
  evidence_aggregator -> conditional_edges:
    - "proceed" -> [prosecutor, defense, tech_lead] (parallel fan-out) -> chief_justice (fan-in) -> END
    - "skip" -> END (when evidence missing or node failure)
"""

from langgraph.graph import END, START, StateGraph

from src.state import AgentState
from src.nodes.aggregator import EvidenceAggregatorNode
from src.nodes.detectives import DocAnalystNode, RepoInvestigatorNode, VisionInspectorNode
from src.nodes.judges import JudicialPanelNode
from src.nodes.justice import ChiefJusticeNode
from src.nodes.report_accuracy import ReportAccuracyNode


def _route_after_aggregator(state: dict) -> str:
    """Conditional edge: proceed when we have evidence; skip when no evidence (unavailable artifacts)."""
    evidences = state.get("evidences") or {}
    has_any = bool(evidences and any(evidences.values()))
    return "proceed" if has_any else "skip"


def build_detective_graph():
    """Build compiled graph: detectives -> aggregator -> conditional(proceed -> judges -> chief_justice | skip -> END)."""
    g = StateGraph(AgentState)
    g.add_node("repo_investigator", RepoInvestigatorNode)
    g.add_node("doc_analyst", DocAnalystNode)
    g.add_node("vision_inspector", VisionInspectorNode)
    g.add_node("evidence_aggregator", EvidenceAggregatorNode)
    g.add_node("report_accuracy", ReportAccuracyNode)
    g.add_node("judicial_panel", JudicialPanelNode)
    g.add_node("chief_justice", ChiefJusticeNode)

    g.add_edge(START, "repo_investigator")
    g.add_edge(START, "doc_analyst")
    g.add_edge(START, "vision_inspector")
    g.add_edge("repo_investigator", "evidence_aggregator")
    g.add_edge("doc_analyst", "evidence_aggregator")
    g.add_edge("vision_inspector", "evidence_aggregator")
    g.add_conditional_edges(
        "evidence_aggregator",
        _route_after_aggregator,
        {"proceed": "report_accuracy", "skip": END},
    )
    g.add_edge("report_accuracy", "judicial_panel")
    g.add_edge("judicial_panel", "chief_justice")
    g.add_edge("chief_justice", END)

    return g.compile()
