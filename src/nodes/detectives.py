"""Detective nodes for the Automaton Auditor."""

import base64
import os
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
            llm_rationale: str | None = None
            if os.environ.get("GROQ_API_KEY"):
                try:
                    from langchain_groq import ChatGroq
                    llm = ChatGroq(model="llama-3.1-70b-versatile", temperature=0.2)
                    summary_prompt = f"Summarize in one sentence: repo has {len(history)} commits; graph_analysis: {graph_info.get('has_state_graph')} (nodes: {graph_info.get('nodes', [])})."
                    resp = llm.invoke(summary_prompt)
                    if hasattr(resp, "content") and resp.content:
                        llm_rationale = resp.content.strip()
                except Exception:
                    pass
            for d in dimensions:
                dim_id = d.get("id", "unknown")
                base_rationale: str
                if dim_id == "git_forensic_analysis":
                    content = f"{len(history)} commits" + (f"; messages: {[h.get('message','')[:40] for h in history[:5]]}" if history else "")
                    base_rationale = "git log extracted"
                    evidences[dim_id] = [_evidence(dim_id, len(history) > 0, content, repo_url, base_rationale + (f"; {llm_rationale}" if llm_rationale else ""), 0.9 if len(history) > 3 else 0.5)]
                elif dim_id == "graph_orchestration":
                    content = f"has_state_graph={graph_info.get('has_state_graph')}; nodes={graph_info.get('nodes', [])}; edges={graph_info.get('edges', [])}"
                    base_rationale = "AST analysis"
                    evidences[dim_id] = [_evidence(dim_id, graph_info.get("has_state_graph", False), content, path, base_rationale + (f"; {llm_rationale}" if llm_rationale else ""), 0.8 if graph_info.get("has_state_graph") else 0.3)]
                else:
                    content = f"git_history_len={len(history)}; graph={graph_info.get('has_state_graph')}"
                    base_rationale = "Repo tools run"
                    evidences[dim_id] = [_evidence(dim_id, True, content, path, base_rationale + (f"; {llm_rationale}" if llm_rationale else ""), 0.7)]
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
                rationale = f"in_detailed_explanation={in_detail}"
                if result.get("llm_rationale"):
                    rationale = result["llm_rationale"][:300]
                evidences[dim_id] = [_evidence(dim_id, result.get("term_count", 0) > 0, content, pdf_path, rationale, 0.8 if in_detail else 0.4)]
            else:
                evidences[dim_id] = [_evidence(dim_id, True, str(result)[:500], pdf_path, "PDF ingested and queried", 0.6)]
    except DocIngestError as e:
        for d in dimensions:
            dim_id = d.get("id", "unknown")
            evidences[dim_id] = [_evidence(dim_id, False, None, pdf_path, str(e)[:200], 0.0)]
    return {"evidences": evidences}


def VisionInspectorNode(state: dict[str, Any]) -> dict[str, Any]:
    """Extract images from PDF; run Gemini vision when GOOGLE_API_KEY set."""
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
    content: str | None = None
    rationale = "extract_images_from_pdf succeeded; vision call skipped"
    confidence = 0.5

    if images and os.environ.get("GOOGLE_API_KEY"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
            img = images[0]
            b64 = base64.b64encode(img.get("data", b"")).decode("utf-8")
            prompt = "Classify this diagram: is it a StateGraph/fan-in fan-out style diagram or a generic flowchart? Describe the flow in 1-2 sentences."
            messages = [
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}
            ]
            response = llm.invoke(messages)
            if hasattr(response, "content") and response.content:
                content = f"Extracted {len(images)} image(s). Vision: {response.content.strip()}"
                rationale = response.content.strip()
                confidence = 0.8
        except Exception as e:
            content = f"Extracted {len(images)} image(s); vision call failed: {e!s}"
            rationale = f"Vision call failed: {e!s}"
    elif images:
        content = f"Extracted {len(images)} image(s) from PDF; GOOGLE_API_KEY not set, vision skipped"
        rationale = "GOOGLE_API_KEY not set; vision analysis skipped"

    for d in dimensions:
        dim_id = d.get("id", "unknown")
        if content:
            evidences[dim_id] = [_evidence(dim_id, True, content, pdf_path, rationale, confidence)]
        else:
            evidences[dim_id] = [_evidence(dim_id, False, None, pdf_path, "No images or extract failed", 0.0)]
    return {"evidences": evidences}
