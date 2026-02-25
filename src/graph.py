"""Detective graph: parallel detectives fan-in to EvidenceAggregator."""

from langgraph.graph import END, START, StateGraph

from src.state import AgentState
from src.nodes.aggregator import EvidenceAggregatorNode
from src.nodes.detectives import DocAnalystNode, RepoInvestigatorNode, VisionInspectorNode


def build_detective_graph():
    """Build compiled graph: START -> repo_investigator, doc_analyst, vision_inspector (parallel) -> evidence_aggregator -> END."""
    g = StateGraph(AgentState)
    g.add_node("repo_investigator", RepoInvestigatorNode)
    g.add_node("doc_analyst", DocAnalystNode)
    g.add_node("vision_inspector", VisionInspectorNode)
    g.add_node("evidence_aggregator", EvidenceAggregatorNode)

    g.add_edge(START, "repo_investigator")
    g.add_edge(START, "doc_analyst")
    g.add_edge(START, "vision_inspector")
    g.add_edge("repo_investigator", "evidence_aggregator")
    g.add_edge("doc_analyst", "evidence_aggregator")
    g.add_edge("vision_inspector", "evidence_aggregator")
    g.add_edge("evidence_aggregator", END)

    return g.compile()
