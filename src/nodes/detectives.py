"""Detective nodes for the Automaton Auditor."""

from typing import Any

from src.state import Evidence

GITHUB_REPO_ARTIFACT = "github_repo"
PDF_REPORT_ARTIFACT = "pdf_report"
PDF_IMAGES_ARTIFACT = "pdf_images"


def _dimensions_for_artifact(rubric_dimensions: list[dict[str, Any]] | None, target_artifact: str) -> list[dict[str, Any]]:
    if not rubric_dimensions:
        return []
    return [d for d in rubric_dimensions if d.get("target_artifact") == target_artifact]


def _evidence(dimension_id: str, found: bool, content: str | None, location: str, rationale: str, confidence: float = 0.0) -> Evidence:
    return Evidence(
        goal=dimension_id,
        found=found,
        content=content,
        location=location,
        rationale=rationale,
        confidence=confidence,
    )


def RepoInvestigatorNode(state: dict[str, Any]) -> dict[str, Any]:
    """Run repo tools (sandboxed clone, git history, graph structure); emit Evidence keyed by dimension."""
    dimensions = _dimensions_for_artifact(state.get("rubric_dimensions"), GITHUB_REPO_ARTIFACT)
    repo_url = state.get("repo_url") or ""
    if not repo_url:
        evidences = {
            d.get("id", "unknown"): [_evidence(d.get("id", "unknown"), False, None, "", "No repo_url in state", 0.0)]
            for d in dimensions
        } if dimensions else {}
        return {"evidences": evidences}

    try:
        from src.tools import repo_tools
    except ImportError:
        evidences = {
            d.get("id", "unknown"): [_evidence(d.get("id", "unknown"), False, None, repo_url, "repo_tools not available", 0.0)]
            for d in dimensions
        } if dimensions else {}
        return {"evidences": evidences}

    evidences: dict[str, list[Evidence]] = {}
    try:
        with repo_tools.sandboxed_clone(repo_url) as path:
            history = repo_tools.extract_git_history(path)
            graph_info = repo_tools.analyze_graph_structure(path)
            for d in dimensions:
                dim_id = d.get("id", "unknown")
                if dim_id == "git_forensic_analysis":
                    content = f"{len(history)} commits" + (f"; messages: {[h.get('message','')[:40] for h in history[:5]]}" if history else "")
                    evidences[dim_id] = [_evidence(dim_id, len(history) > 0, content, repo_url, "git log extracted", 0.9 if len(history) > 3 else 0.5)]
                elif dim_id == "graph_orchestration":
                    content = f"has_state_graph={graph_info.get('has_state_graph')}; nodes={graph_info.get('nodes', [])}; edges={graph_info.get('edges', [])}"
                    evidences[dim_id] = [_evidence(dim_id, graph_info.get("has_state_graph", False), content, path, "AST analysis", 0.8 if graph_info.get("has_state_graph") else 0.3)]
                else:
                    content = f"git_history_len={len(history)}; graph={graph_info.get('has_state_graph')}"
                    evidences[dim_id] = [_evidence(dim_id, True, content, path, "Repo tools run", 0.7)]
    except repo_tools.RepoCloneError as e:
        for d in dimensions:
            dim_id = d.get("id", "unknown")
            evidences[dim_id] = [_evidence(dim_id, False, None, repo_url, str(e)[:200], 0.0)]
    return {"evidences": evidences}


def DocAnalystNode(state: dict[str, Any]) -> dict[str, Any]:
    """Ingest PDF, run RAG-lite search for theoretical_depth; emit Evidence."""
    dimensions = _dimensions_for_artifact(state.get("rubric_dimensions"), PDF_REPORT_ARTIFACT)
    pdf_path = state.get("pdf_path") or ""
    if not pdf_path:
        evidences = {
            d.get("id", "unknown"): [_evidence(d.get("id", "unknown"), False, None, "", "No pdf_path in state", 0.0)]
            for d in dimensions
        } if dimensions else {}
        return {"evidences": evidences}

    from src.tools.doc_tools import DocIngestError, ingest_pdf, search_theoretical_depth

    evidences: dict[str, list[Evidence]] = {}
    try:
        chunks = ingest_pdf(pdf_path)
        result = search_theoretical_depth(chunks)
        for d in dimensions:
            dim_id = d.get("id", "unknown")
            if dim_id == "theoretical_depth":
                content = "; ".join(result.get("sentences_with_terms", [])[:3]) or "No matching terms"
                in_detail = result.get("in_detailed_explanation", False)
                evidences[dim_id] = [_evidence(dim_id, result.get("term_count", 0) > 0, content, pdf_path, f"in_detailed_explanation={in_detail}", 0.8 if in_detail else 0.4)]
            else:
                evidences[dim_id] = [_evidence(dim_id, True, str(result)[:500], pdf_path, "PDF ingested and queried", 0.6)]
    except DocIngestError as e:
        for d in dimensions:
            dim_id = d.get("id", "unknown")
            evidences[dim_id] = [_evidence(dim_id, False, None, pdf_path, str(e)[:200], 0.0)]
    return {"evidences": evidences}


def VisionInspectorNode(state: dict[str, Any]) -> dict[str, Any]:
    """Extract images from PDF; optionally run vision model. Execution optional for interim."""
    dimensions = _dimensions_for_artifact(state.get("rubric_dimensions"), PDF_IMAGES_ARTIFACT)
    pdf_path = state.get("pdf_path") or ""
    if not pdf_path:
        evidences = {
            d.get("id", "unknown"): [_evidence(d.get("id", "unknown"), False, None, "", "No pdf_path in state", 0.0)]
            for d in dimensions
        } if dimensions else {}
        return {"evidences": evidences}

    from src.tools.doc_tools import extract_images_from_pdf

    evidences: dict[str, list[Evidence]] = {}
    images = extract_images_from_pdf(pdf_path)
    for d in dimensions:
        dim_id = d.get("id", "unknown")
        if images:
            content = f"Extracted {len(images)} image(s) from PDF; vision analysis not run (interim)"
            evidences[dim_id] = [_evidence(dim_id, True, content, pdf_path, "extract_images_from_pdf succeeded; vision call skipped", 0.5)]
        else:
            evidences[dim_id] = [_evidence(dim_id, False, None, pdf_path, "Vision analysis not run (interim); no images or extract failed", 0.0)]
    return {"evidences": evidences}
