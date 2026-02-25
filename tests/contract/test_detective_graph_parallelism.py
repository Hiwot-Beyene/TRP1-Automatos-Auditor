"""
Contract tests for detective graph parallelism (TRP1 Challenge).

Verifies:
- Fan-out: START has edges to all three detectives (repo_investigator, doc_analyst, vision_inspector).
- Fan-in: All three detectives have an edge to evidence_aggregator; evidence_aggregator has edge to END.
- Integration: Invoking the graph with repo_url, pdf_path, and rubric for all artifacts yields
  evidences merged from all three detectives (reducer operator.ior).
"""

import pytest

from src.graph import build_detective_graph


def _get_graph_structure(compiled):
    """Return graph structure from LangGraph compiled graph. LangGraph returns Graph(nodes=dict, edges=list)."""
    get_graph = getattr(compiled, "get_graph", None)
    if get_graph is None:
        pytest.skip("Compiled graph does not expose get_graph()")
    G = get_graph()
    if G is None:
        pytest.skip("get_graph() returned None")
    return G


def _node_ids(G):
    """Node names: G.nodes is a dict in LangGraph."""
    nodes = getattr(G, "nodes", None)
    if nodes is None:
        return set()
    return set(nodes.keys()) if isinstance(nodes, dict) else set(nodes())


def _edges_list(G):
    """List of (source, target). LangGraph uses G.edges (list of Edge with .source, .target)."""
    edges = getattr(G, "edges", None)
    if edges is None:
        return []
    if callable(edges):
        edges = edges()
    return [(e.source, e.target) if hasattr(e, "source") else (e[0], e[1]) for e in edges]


def _start_node(G):
    for name in ("__start__", "start"):
        if name in _node_ids(G):
            return name
    pytest.skip("Could not find start node in graph")


def _end_node(G):
    for name in ("__end__", "end"):
        if name in _node_ids(G):
            return name
    pytest.skip("Could not find end node in graph")


def test_graph_has_four_detective_nodes():
    """Graph must define repo_investigator, doc_analyst, vision_inspector, evidence_aggregator."""
    compiled = build_detective_graph()
    G = _get_graph_structure(compiled)
    nodes = _node_ids(G)
    expected = {"repo_investigator", "doc_analyst", "vision_inspector", "evidence_aggregator"}
    assert expected.issubset(nodes), f"Expected nodes {expected}, got {nodes}"


def test_parallelism_fan_out_from_start():
    """START must have an edge to each of the three detectives (parallel fan-out)."""
    compiled = build_detective_graph()
    G = _get_graph_structure(compiled)
    start = _start_node(G)
    edge_list = _edges_list(G)
    successors = {t for s, t in edge_list if s == start}
    detectives = {"repo_investigator", "doc_analyst", "vision_inspector"}
    assert detectives.issubset(successors), f"START should fan-out to {detectives}, got {successors}"


def test_fan_in_to_evidence_aggregator():
    """All three detectives must have an edge to evidence_aggregator (fan-in)."""
    compiled = build_detective_graph()
    G = _get_graph_structure(compiled)
    edge_list = _edges_list(G)
    preds = {s for s, t in edge_list if t == "evidence_aggregator"}
    detectives = {"repo_investigator", "doc_analyst", "vision_inspector"}
    assert detectives.issubset(preds), f"evidence_aggregator should have incoming edges from {detectives}, got {preds}"


def test_evidence_aggregator_has_edge_to_end():
    """EvidenceAggregator must have single edge to END."""
    compiled = build_detective_graph()
    G = _get_graph_structure(compiled)
    end = _end_node(G)
    edge_list = _edges_list(G)
    succ = {t for s, t in edge_list if s == "evidence_aggregator"}
    assert succ == {end}, f"evidence_aggregator should point to END ({end}), got {succ}"


def test_invoke_merges_evidences_from_all_detectives():
    """Invoking with repo_url, pdf_path, and rubric for all artifacts yields evidences from all three detectives (reducer merge)."""
    compiled = build_detective_graph()
    rubric = [
        {"id": "r1", "name": "Repo", "target_artifact": "github_repo"},
        {"id": "d1", "name": "Doc", "target_artifact": "pdf_report"},
        {"id": "v1", "name": "Vision", "target_artifact": "pdf_images"},
    ]
    state = compiled.invoke({
        "repo_url": "",
        "pdf_path": "",
        "rubric_dimensions": rubric,
    })
    evidences = state.get("evidences") or {}
    repo_dims = {d["id"] for d in rubric if d.get("target_artifact") == "github_repo"}
    doc_dims = {d["id"] for d in rubric if d.get("target_artifact") == "pdf_report"}
    vision_dims = {d["id"] for d in rubric if d.get("target_artifact") == "pdf_images"}
    assert repo_dims.issubset(evidences.keys()), f"Expected repo dimensions {repo_dims} in evidences, got {list(evidences.keys())}"
    assert doc_dims.issubset(evidences.keys()), f"Expected doc dimensions {doc_dims} in evidences, got {list(evidences.keys())}"
    assert vision_dims.issubset(evidences.keys()), f"Expected vision dimensions {vision_dims} in evidences, got {list(evidences.keys())}"
