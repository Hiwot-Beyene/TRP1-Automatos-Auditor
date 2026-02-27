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

    # 1. run_detectives and evidence_aggregator
    try:
        nodes = set(G.nodes()) if G else set()
        expected = {"run_detectives", "evidence_aggregator"}
        passed = expected.issubset(nodes)
        results.append({
            "name": "Graph has run_detectives and evidence_aggregator",
            "passed": passed,
            "message": f"Expected {expected}" if not passed else f"Found {expected}",
        })
    except Exception as e:
        results.append({"name": "Graph has run_detectives and evidence_aggregator", "passed": False, "message": str(e)})

    if not G:
        results.append({
            "name": "Remaining checks (graph structure)",
            "passed": False,
            "message": "get_graph() not available or returned None",
        })
        return results

    # 2. START → run_detectives
    try:
        start = _start_node(G)
        if not start:
            results.append({"name": "START → run_detectives", "passed": False, "message": "Could not find start node"})
        else:
            succ = set(G.successors(start)) if hasattr(G, "successors") else {e[1] for e in G.edges() if e[0] == start}
            passed = "run_detectives" in succ
            results.append({
                "name": "START → run_detectives",
                "passed": passed,
                "message": f"START → run_detectives" if passed else f"Expected START → run_detectives, got {succ}",
            })
    except Exception as e:
        results.append({"name": "START → run_detectives", "passed": False, "message": str(e)})

    # 3. run_detectives → evidence_aggregator
    try:
        preds = set(G.predecessors("evidence_aggregator")) if hasattr(G, "predecessors") else {e[0] for e in G.edges() if e[1] == "evidence_aggregator"}
        passed = "run_detectives" in preds
        results.append({
            "name": "run_detectives → evidence_aggregator",
            "passed": passed,
            "message": "run_detectives → evidence_aggregator" if passed else f"Expected run_detectives, got {preds}",
        })
    except Exception as e:
        results.append({"name": "run_detectives → evidence_aggregator", "passed": False, "message": str(e)})

    # 4. evidence_aggregator has conditional edges (proceed/skip)
    try:
        end = _end_node(G)
        succ = set(G.successors("evidence_aggregator")) if hasattr(G, "successors") else {e[1] for e in G.edges() if e[0] == "evidence_aggregator"}
        passed = end is not None and (end in succ or "report_accuracy" in succ)
        results.append({
            "name": "evidence_aggregator → report_accuracy or END",
            "passed": passed,
            "message": f"evidence_aggregator → {succ}" if passed else f"Expected path to report_accuracy or END, got {succ}",
        })
    except Exception as e:
        results.append({"name": "evidence_aggregator → report_accuracy or END", "passed": False, "message": str(e)})

    # 5a. Repo-only: only repo detective runs; evidences contain only repo dimensions
    try:
        rubric = [
            {"id": "r1", "name": "Repo", "target_artifact": "github_repo"},
            {"id": "d1", "name": "Doc", "target_artifact": "pdf_report"},
            {"id": "v1", "name": "Vision", "target_artifact": "pdf_images"},
        ]
        state = compiled.invoke({
            "repo_url": "https://github.com/octocat/Hello-World",
            "pdf_path": "",
            "rubric_dimensions": rubric,
        })
        evidences = state.get("evidences") or {}
        passed = "r1" in evidences and "d1" not in evidences and "v1" not in evidences
        results.append({
            "name": "Repo-only: only repo tools run (repo dimensions only)",
            "passed": passed,
            "message": f"Evidences: {list(evidences.keys())}" if passed else f"Expected only r1, got {list(evidences.keys())}",
        })
    except Exception as e:
        results.append({"name": "Repo-only: only repo tools run", "passed": False, "message": str(e)})

    # 5b. Doc-only: only doc/vision detectives run; evidences contain only doc dimensions
    try:
        rubric = [
            {"id": "r1", "name": "Repo", "target_artifact": "github_repo"},
            {"id": "d1", "name": "Doc", "target_artifact": "pdf_report"},
            {"id": "v1", "name": "Vision", "target_artifact": "pdf_images"},
        ]
        state = compiled.invoke({
            "repo_url": "",
            "pdf_path": "https://example.com/nonexistent.pdf",
            "rubric_dimensions": rubric,
        })
        evidences = state.get("evidences") or {}
        passed = "d1" in evidences and "v1" in evidences and "r1" not in evidences
        results.append({
            "name": "Doc-only: only doc/vision tools run (report dimensions only)",
            "passed": passed,
            "message": f"Evidences: {list(evidences.keys())}" if passed else f"Expected only d1, v1, got {list(evidences.keys())}",
        })
    except Exception as e:
        results.append({"name": "Doc-only: only doc/vision tools run", "passed": False, "message": str(e)})

    # 5c. Both: repo and doc detectives run; evidences contain repo and doc dimensions
    try:
        rubric = [
            {"id": "r1", "name": "Repo", "target_artifact": "github_repo"},
            {"id": "d1", "name": "Doc", "target_artifact": "pdf_report"},
            {"id": "v1", "name": "Vision", "target_artifact": "pdf_images"},
        ]
        state = compiled.invoke({
            "repo_url": "https://github.com/octocat/Hello-World",
            "pdf_path": "https://example.com/nonexistent.pdf",
            "rubric_dimensions": rubric,
        })
        evidences = state.get("evidences") or {}
        passed = "r1" in evidences and "d1" in evidences and "v1" in evidences
        results.append({
            "name": "Repo + Doc: repo and doc tools run in parallel",
            "passed": passed,
            "message": f"Evidences: {list(evidences.keys())}" if passed else f"Expected r1, d1, v1, got {list(evidences.keys())}",
        })
    except Exception as e:
        results.append({"name": "Repo + Doc: repo and doc tools run in parallel", "passed": False, "message": str(e)})

    return results
