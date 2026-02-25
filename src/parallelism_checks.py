"""Run parallelism contract checks (same logic as tests/contract) and return results for API/UI."""

from typing import Any

from src.graph import build_detective_graph


def _get_graph(compiled: Any):
    g = getattr(compiled, "get_graph", None)
    if g is None:
        return None
    return g()


def _start_node(G: Any) -> str | None:
    nodes = list(G.nodes())
    for name in ("__start__", "start"):
        if name in nodes:
            return name
    return None


def _end_node(G: Any) -> str | None:
    nodes = list(G.nodes())
    for name in ("__end__", "end"):
        if name in nodes:
            return name
    return None


def run_parallelism_checks() -> list[dict[str, Any]]:
    """Run all parallelism contract checks; return list of {name, passed, message}."""
    results: list[dict[str, Any]] = []
    compiled = build_detective_graph()
    G = _get_graph(compiled)

    # 1. Four detective nodes
    try:
        nodes = set(G.nodes()) if G else set()
        expected = {"repo_investigator", "doc_analyst", "vision_inspector", "evidence_aggregator"}
        passed = expected.issubset(nodes)
        results.append({
            "name": "Graph has four detective nodes",
            "passed": passed,
            "message": f"Expected {expected}" if not passed else f"Found {expected}",
        })
    except Exception as e:
        results.append({"name": "Graph has four detective nodes", "passed": False, "message": str(e)})

    if not G:
        results.append({
            "name": "Remaining checks (graph structure)",
            "passed": False,
            "message": "get_graph() not available or returned None",
        })
        return results

    # 2. Fan-out from START
    try:
        start = _start_node(G)
        if not start:
            results.append({"name": "Fan-out from START", "passed": False, "message": "Could not find start node"})
        else:
            succ = set(G.successors(start)) if hasattr(G, "successors") else {e[1] for e in G.edges() if e[0] == start}
            detectives = {"repo_investigator", "doc_analyst", "vision_inspector"}
            passed = detectives.issubset(succ)
            results.append({
                "name": "Fan-out from START",
                "passed": passed,
                "message": f"START → {detectives}" if passed else f"Expected START → {detectives}, got {succ}",
            })
    except Exception as e:
        results.append({"name": "Fan-out from START", "passed": False, "message": str(e)})

    # 3. Fan-in to evidence_aggregator
    try:
        preds = set(G.predecessors("evidence_aggregator")) if hasattr(G, "predecessors") else {e[0] for e in G.edges() if e[1] == "evidence_aggregator"}
        detectives = {"repo_investigator", "doc_analyst", "vision_inspector"}
        passed = detectives.issubset(preds)
        results.append({
            "name": "Fan-in to EvidenceAggregator",
            "passed": passed,
            "message": f"All three detectives → evidence_aggregator" if passed else f"Expected {detectives}, got {preds}",
        })
    except Exception as e:
        results.append({"name": "Fan-in to EvidenceAggregator", "passed": False, "message": str(e)})

    # 4. EvidenceAggregator → END (conditional_edges may create multiple paths to END)
    try:
        end = _end_node(G)
        succ = set(G.successors("evidence_aggregator")) if hasattr(G, "successors") else {e[1] for e in G.edges() if e[0] == "evidence_aggregator"}
        passed = end is not None and end in succ
        results.append({
            "name": "EvidenceAggregator → END",
            "passed": passed,
            "message": f"evidence_aggregator → {end}" if passed else f"Expected path to END, got {succ}",
        })
    except Exception as e:
        results.append({"name": "EvidenceAggregator → END", "passed": False, "message": str(e)})

    # 5. Invoke merges evidences from all detectives
    try:
        rubric = [
            {"id": "r1", "name": "Repo", "target_artifact": "github_repo"},
            {"id": "d1", "name": "Doc", "target_artifact": "pdf_report"},
            {"id": "v1", "name": "Vision", "target_artifact": "pdf_images"},
        ]
        state = compiled.invoke({"repo_url": "", "pdf_path": "", "rubric_dimensions": rubric})
        evidences = state.get("evidences") or {}
        repo_dims = {"r1"}
        doc_dims = {"d1"}
        vision_dims = {"v1"}
        passed = repo_dims.issubset(evidences) and doc_dims.issubset(evidences) and vision_dims.issubset(evidences)
        results.append({
            "name": "Invoke merges evidences from all detectives",
            "passed": passed,
            "message": f"Evidences from repo, doc, vision: {list(evidences.keys())}" if passed else f"Expected r1, d1, v1 in evidences, got {list(evidences.keys())}",
        })
    except Exception as e:
        results.append({"name": "Invoke merges evidences from all detectives", "passed": False, "message": str(e)})

    return results
