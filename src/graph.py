"""LangGraph: detectives collecting evidence, judges arguing, and Chief Justice synthesizing the verdict.

State: AgentState (from src.state) is a TypedDict with Annotated reducers: operator.add for opinions,
operator.ior for evidences—parallel agents merge data instead of overwriting. Evidence and JudicialOpinion
are Pydantic BaseModel classes with typed fields.

Graph flow: Two parallel fan-out/fan-in patterns.
- Detectives: START -> entry -> [doc_gate, repo_gate, vision_gate] -> [doc_analyst, repo_investigator, vision_inspector]
  (concurrent). Synchronization node: evidence_aggregator (fan-in). Conditional edges: skip_doc/skip_repo/skip_vision.
- Judges: evidence_aggregator -> judge_panel -> [defense, prosecutor, tech_lead] (concurrent) -> chief_justice -> END.
Conditional edges: evidence_missing -> evidence_missing_handler -> END.
"""

from langgraph.graph import END, START, StateGraph

from src.audit_classifier import classify_audit_type, filter_dimensions_by_audit_type
from src.state import AgentState
from src.nodes.aggregator import EvidenceAggregatorNode
from src.nodes.detectives import DocAnalystNode, RepoInvestigatorNode, VisionInspectorNode
from src.nodes.judges import DefenseNode, ProsecutorNode, TechLeadNode
from src.nodes.justice import ChiefJusticeNode


def _route_doc(state: dict) -> str:
    """Route to doc_analyst if PDF is available."""
    pdf_path = (state.get("pdf_path") or "").strip()
    return "doc_analyst" if pdf_path else "skip_doc"


def _route_repo(state: dict) -> str:
    """Route to repo_investigator if repo URL is available."""
    repo_url = (state.get("repo_url") or "").strip()
    return "repo_investigator" if repo_url else "skip_repo"


def _route_vision(state: dict) -> str:
    """Route to vision_inspector if PDF is available."""
    pdf_path = (state.get("pdf_path") or "").strip()
    return "vision_inspector" if pdf_path else "skip_vision"


def _route_after_aggregator(state: dict) -> str:
    """Proceed when we have any evidence; else Evidence Missing path."""
    evidences = state.get("evidences") or {}
    has_any = bool(evidences and any(evidences.values()))
    return "proceed" if has_any else "evidence_missing"


def _evidence_missing_node(state: dict) -> dict:
    """Handle Evidence Missing: no evidence collected; skip judges and end with minimal report."""
    return {}


def _judge_panel_node(state: dict) -> dict:
    """Pass-through node to enable parallel fan-out to all judges."""
    return state


def _merge_judge_opinions(state: dict) -> dict:
    """Merge opinions from all judges."""
    opinions = state.get("opinions") or []
    return {"opinions": opinions}


def _classify_audit_node(state: dict) -> dict:
    """Pre-execution classification: determine audit type and filter dimensions.
    
    This ensures only relevant tools and dimensions are processed, eliminating
    unnecessary execution for repository-only or report-only audits.
    """
    repo_url = (state.get("repo_url") or "").strip()
    pdf_path = (state.get("pdf_path") or "").strip()
    rubric_dimensions = state.get("rubric_dimensions") or []
    
    try:
        audit_type = classify_audit_type(repo_url, pdf_path)
        filtered_dimensions = filter_dimensions_by_audit_type(
            rubric_dimensions, audit_type, repo_url, pdf_path
        )
        
        return {
            "rubric_dimensions": filtered_dimensions,
            "audit_type": audit_type,
        }
    except ValueError:
        return {"rubric_dimensions": []}


def _noop_node(_state: dict) -> dict:
    """No-op pass-through node: doesn't modify state to avoid concurrent update errors."""
    return {}


def _sync_node(state: dict) -> dict:
    """Sync node: ensures evidence_aggregator only runs once even when triggered from multiple skip paths."""
    return {}


def build_detective_graph():
    """Build LangGraph showing full reasoning loop: detectives -> judges -> chief justice.
    
    The graph implements context-aware tool selection:
    - Repository-only: Only repo_investigator executes
    - Report-only: Only doc_analyst and vision_inspector execute
    - Both: All detectives execute in parallel with strict tool isolation
    """
    g = StateGraph(AgentState)
    
    g.add_node("classify_audit", _classify_audit_node)
    g.add_node("entry", _noop_node)
    g.add_node("doc_gate", _noop_node)
    g.add_node("repo_gate", _noop_node)
    g.add_node("vision_gate", _noop_node)
    g.add_node("doc_analyst", DocAnalystNode)
    g.add_node("repo_investigator", RepoInvestigatorNode)
    g.add_node("vision_inspector", VisionInspectorNode)
    g.add_node("sync_aggregator", _sync_node)
    g.add_node("evidence_aggregator", EvidenceAggregatorNode)
    g.add_node("evidence_missing_handler", _evidence_missing_node)
    g.add_node("defense", DefenseNode)
    g.add_node("prosecutor", ProsecutorNode)
    g.add_node("tech_lead", TechLeadNode)
    g.add_node("chief_justice", ChiefJusticeNode)
    
    g.add_edge(START, "classify_audit")
    g.add_edge("classify_audit", "entry")
    g.add_edge("entry", "doc_gate")
    g.add_edge("entry", "repo_gate")
    g.add_edge("entry", "vision_gate")
    
    g.add_conditional_edges(
        "doc_gate",
        _route_doc,
        {"doc_analyst": "doc_analyst", "skip_doc": "sync_aggregator"},
    )
    g.add_conditional_edges(
        "repo_gate",
        _route_repo,
        {"repo_investigator": "repo_investigator", "skip_repo": "sync_aggregator"},
    )
    g.add_conditional_edges(
        "vision_gate",
        _route_vision,
        {"vision_inspector": "vision_inspector", "skip_vision": "sync_aggregator"},
    )
    
    g.add_edge("doc_analyst", "evidence_aggregator")
    g.add_edge("repo_investigator", "evidence_aggregator")
    g.add_edge("vision_inspector", "evidence_aggregator")
    g.add_edge("sync_aggregator", "evidence_aggregator")
    
    g.add_node("judge_panel", _judge_panel_node)
    
    g.add_conditional_edges(
        "evidence_aggregator",
        _route_after_aggregator,
        {
            "proceed": "judge_panel",
            "evidence_missing": "evidence_missing_handler",
        },
    )
    g.add_edge("evidence_missing_handler", END)
    
    g.add_edge("judge_panel", "defense")
    g.add_edge("judge_panel", "prosecutor")
    g.add_edge("judge_panel", "tech_lead")
    
    g.add_edge("defense", "chief_justice")
    g.add_edge("prosecutor", "chief_justice")
    g.add_edge("tech_lead", "chief_justice")
    g.add_edge("chief_justice", END)
    
    return g.compile()
