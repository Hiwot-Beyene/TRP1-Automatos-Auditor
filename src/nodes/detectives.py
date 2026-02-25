"""Detective nodes for the Automaton Auditor."""

import base64
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.state import Evidence
from src.config import get_detective_workers

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


def RunRelevantDetectivesNode(state: dict[str, Any]) -> dict[str, Any]:
    """Repo + doc run in parallel: repo branch uses only github_repo tools; report branch uses only pdf_report + pdf_images tools."""
    repo_url = (state.get("repo_url") or "").strip()
    pdf_path = (state.get("pdf_path") or "").strip()
    repo_tasks: list[tuple[str, type, dict[str, Any]]] = []
    report_tasks: list[tuple[str, type, dict[str, Any]]] = []
    state_pdf: dict[str, Any] | None = None

    if repo_url:
        repo_tasks.append(("repo", RepoInvestigatorNode, state))

    if pdf_path:
        state_pdf = dict(state)
        if state.get("pdf_chunks") is None and state.get("pdf_images") is None:
            try:
                from src.tools.doc_tools import extract_images_from_pdf, ingest_pdf, pdf_to_binary
                pdf_bytes = pdf_to_binary(pdf_path)
                state_pdf["pdf_chunks"] = ingest_pdf(pdf_path=pdf_path, pdf_bytes=pdf_bytes)
                state_pdf["pdf_images"] = extract_images_from_pdf(pdf_path=pdf_path, pdf_bytes=pdf_bytes)
            except Exception as e:
                state_pdf["pdf_path"] = ""
                state_pdf["pdf_fetch_error"] = str(e).strip()[:250]
        report_tasks.append(("doc", DocAnalystNode, state_pdf))
        report_tasks.append(("vision", VisionInspectorNode, state_pdf))

    tasks = repo_tasks + report_tasks
    merged: dict[str, list[Evidence]] = {}
    if not tasks:
        return {"evidences": merged}

    max_workers = min(get_detective_workers(), len(tasks))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fn, s): name for name, fn, s in tasks}
        for future in as_completed(futures):
            out = future.result()
            for k, v in (out.get("evidences") or {}).items():
                merged.setdefault(k, []).extend(v)

    result: dict[str, Any] = {"evidences": merged}
    if state_pdf is not None:
        if state_pdf.get("pdf_chunks") is not None:
            result["pdf_chunks"] = state_pdf["pdf_chunks"]
        if state_pdf.get("pdf_images") is not None:
            result["pdf_images"] = state_pdf["pdf_images"]
    return result


def RepoInvestigatorNode(state: dict[str, Any]) -> dict[str, Any]:
    """GitHub-repo tools only: sandboxed clone, git history, graph structure, forensic scan. No PDF/doc tools."""
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
            forensic_scan = repo_tools.scan_forensic_evidence(path)
            git_forensic = repo_tools.analyze_git_forensic(history) if history else {}
            llm_rationale: str | None = None
            llm = None
            try:
                from src.llm import get_repo_investigator_llm
                llm = get_repo_investigator_llm()
            except Exception:
                pass
            if llm:
                try:
                    summary_prompt = f"Summarize in one sentence: repo has {len(history)} commits; graph_analysis: {graph_info.get('has_state_graph')} (nodes: {graph_info.get('nodes', [])})."
                    resp = llm.invoke(summary_prompt)
                    if hasattr(resp, "content") and resp.content:
                        llm_rationale = resp.content.strip()
                except Exception as e:
                    from src.llm_errors import (
                        APIQuotaOrFailureError,
                        InvalidModelError,
                        NoModelProvidedError,
                        normalize_llm_exception,
                    )
                    if isinstance(e, (NoModelProvidedError, InvalidModelError, APIQuotaOrFailureError)):
                        raise
                    raise normalize_llm_exception(e)
            content_base = f"commits={len(history)}; has_state_graph={graph_info.get('has_state_graph')}; nodes={graph_info.get('nodes', [])}; edges={graph_info.get('edges', [])}"
            if history:
                content_base += f"; messages_sample={[h.get('message','')[:40] for h in history[:5]]}"
            base_rationale = "git log and AST analysis"
            if forensic_scan:
                content_base += "; forensic_scan=" + str(forensic_scan)
            rationale = base_rationale + (f"; {llm_rationale}" if llm_rationale else "")
            for d in dimensions:
                dim_id = d.get("id", "unknown")
                content = content_base
                if dim_id == "git_forensic_analysis" and git_forensic:
                    gf = git_forensic
                    content = (
                        f"git_forensic: count={gf.get('count', 0)}; "
                        f"progression_story={gf.get('progression_story')}; bulk_upload={gf.get('bulk_upload')}; "
                        f"summary={gf.get('summary', '')}; "
                        f"message_sample={gf.get('message_sample', [])[:10]}; "
                        f"timestamp_sample={gf.get('timestamp_sample', [])[:5]}"
                    )
                    content += "; " + content_base
                elif dim_id == "state_management_rigor":
                    classes = graph_info.get("state_classes", [])
                    reducers = graph_info.get("reducers", [])
                    has_evidence = "Evidence" in classes
                    has_opinion = "JudicialOpinion" in classes
                    has_reducers = "add" in reducers or "ior" in reducers
                    found = has_evidence and has_opinion and has_reducers
                    explicit = (
                        f"Pydantic_Evidence={has_evidence}; Pydantic_JudicialOpinion={has_opinion}; "
                        f"reducers_operator_add_ior={has_reducers}; state_classes={classes}; reducers={reducers}"
                    )
                    content = explicit + "; " + content_base
                elif dim_id in forensic_scan:
                    content = forensic_scan[dim_id] + "; " + content_base
                forensic = (d.get("forensic_instruction") or "").lower()
                if dim_id == "git_forensic_analysis":
                    found = bool(git_forensic.get("progression_story")) and not bool(git_forensic.get("bulk_upload"))
                    conf = 0.85 if found else (0.5 if git_forensic.get("count", 0) > 3 else 0.3)
                elif dim_id == "state_management_rigor":
                    classes = graph_info.get("state_classes") or []
                    reducers = graph_info.get("reducers") or []
                    has_evidence = "Evidence" in classes
                    has_opinion = "JudicialOpinion" in classes
                    has_reducers = "add" in reducers or "ior" in reducers
                    found = has_evidence and has_opinion and has_reducers
                    conf = 0.9 if found else (0.5 if (has_evidence or has_opinion) else 0.3)
                elif "git" in forensic or "commit" in forensic or "history" in forensic:
                    found = len(history) > 0
                    conf = 0.9 if len(history) > 3 else 0.5
                elif "graph" in forensic or "state" in forensic or "node" in forensic or "edge" in forensic:
                    found = graph_info.get("has_state_graph", False)
                    conf = 0.8 if found else 0.3
                elif dim_id == "safe_tool_engineering" and dim_id in forensic_scan:
                    s = forensic_scan[dim_id]
                    found = "tempfile.TemporaryDirectory()=True" in s and "os.system() (unsafe)=False" in s
                    conf = 0.85 if found else 0.4
                elif dim_id == "structured_output_enforcement" and dim_id in forensic_scan:
                    s = forensic_scan[dim_id]
                    found = "with_structured_output/bind_tools=True" in s
                    conf = 0.85 if found else 0.4
                elif dim_id in ("judicial_nuance", "chief_justice_synthesis") and dim_id in forensic_scan:
                    found = True
                    conf = 0.75
                else:
                    found = True
                    conf = 0.7
                evidences[dim_id] = [_evidence(dim_id, found, content, path, rationale, conf)]
    except repo_tools.RepoCloneError as e:
        for d in dimensions:
            dim_id = d.get("id", "unknown")
            evidences[dim_id] = [_evidence(dim_id, False, None, repo_url, str(e)[:200], 0.0)]
    return {"evidences": evidences}


def DocAnalystNode(state: dict[str, Any]) -> dict[str, Any]:
    """PDF-report tools only for theoretical_depth: ingest_pdf + search_theoretical_depth (rubric terms). No repo tools. report_accuracy is handled by ReportAccuracyNode."""
    dimensions = _dimensions_for_artifact(state.get("rubric_dimensions"), PDF_REPORT_ARTIFACT)
    dimensions = [d for d in dimensions if d.get("id") == "theoretical_depth"]
    pdf_path = state.get("pdf_path") or ""
    if not pdf_path and not state.get("pdf_chunks"):
        rationale = state.get("pdf_fetch_error") or "No pdf_path in state"
        evidences = {
            d.get("id", "unknown"): [_evidence(d.get("id", "unknown"), False, None, "", rationale, 0.0)]
            for d in dimensions
        } if dimensions else {}
        return {"evidences": evidences}

    from src.tools.doc_tools import DocIngestError, search_theoretical_depth, _terms_from_forensic_instruction

    evidences: dict[str, list[Evidence]] = {}
    try:
        chunks = state.get("pdf_chunks")
        if chunks is None:
            from src.tools.doc_tools import ingest_pdf
            chunks = ingest_pdf(pdf_path)
        dim = dimensions[0] if dimensions else {}
        terms = _terms_from_forensic_instruction(dim.get("forensic_instruction") or "")
        result = search_theoretical_depth(
            chunks,
            terms=terms,
            success_pattern=dim.get("success_pattern") or "",
            failure_pattern=dim.get("failure_pattern") or "",
        )
        content = "; ".join(result.get("sentences_with_terms", [])[:5]) or str(result)[:500]
        in_detail = result.get("in_detailed_explanation", False)
        rationale = result.get("llm_rationale") or f"in_detailed_explanation={in_detail}"
        if rationale and len(rationale) > 400:
            rationale = rationale[:400]
        term_count = result.get("term_count", 0)
        found = term_count > 0
        conf = 0.8 if in_detail else (0.4 if found else 0.2)
        evidence_content = f"term_count={term_count}, in_detailed_explanation={in_detail}. " + (content or "No matching sentences.")
        for d in dimensions:
            dim_id = d.get("id", "unknown")
            evidences[dim_id] = [_evidence(dim_id, found, evidence_content, pdf_path, rationale, conf)]
    except DocIngestError as e:
        for d in dimensions:
            dim_id = d.get("id", "unknown")
            evidences[dim_id] = [_evidence(dim_id, False, None, pdf_path or "", str(e)[:200], 0.0)]
    except Exception as e:
        for d in dimensions:
            dim_id = d.get("id", "unknown")
            evidences[dim_id] = [_evidence(dim_id, False, None, pdf_path or "", str(e).strip()[:200], 0.0)]
    return {"evidences": evidences}


def VisionInspectorNode(state: dict[str, Any]) -> dict[str, Any]:
    """PDF-images tools only: extract images from PDF + vision model. No repo/github tools."""
    dimensions = _dimensions_for_artifact(state.get("rubric_dimensions"), PDF_IMAGES_ARTIFACT)
    pdf_path = state.get("pdf_path") or ""
    if not pdf_path and not state.get("pdf_images"):
        rationale = state.get("pdf_fetch_error") or "No pdf_path in state"
        evidences = {
            d.get("id", "unknown"): [_evidence(d.get("id", "unknown"), False, None, "", rationale, 0.0)]
            for d in dimensions
        } if dimensions else {}
        return {"evidences": evidences}

    from src.tools.doc_tools import extract_images_from_pdf

    evidences: dict[str, list[Evidence]] = {}
    images = state.get("pdf_images")
    if images is None and pdf_path:
        try:
            images = extract_images_from_pdf(pdf_path)
        except Exception as e:
            for d in dimensions:
                dim_id = d.get("id", "unknown")
                evidences[dim_id] = [_evidence(dim_id, False, None, pdf_path, str(e).strip()[:250], 0.0)]
            return {"evidences": evidences}
    images = images or []
    content: str | None = None
    rationale = "No images extracted from PDF"
    confidence = 0.5

    if images:
        try:
            from src.llm import get_vision_llm
            llm = get_vision_llm()
        except Exception:
            llm = None
        if llm:
            try:
                from langchain_core.messages import HumanMessage
                dim = dimensions[0] if dimensions else {}
                forensic = (dim.get("forensic_instruction") or "").strip()
                success = (dim.get("success_pattern") or "").strip()[:200]
                failure = (dim.get("failure_pattern") or "").strip()[:200]
                prompt = (
                    "Per rubric, classify this diagram from the PDF report. "
                    + (forensic if forensic else "Is it a LangGraph StateGraph diagram with parallel branches, a sequence diagram, or generic flowchart? Does it show START -> [Detectives in parallel] -> Evidence Aggregation -> [Judges in parallel] -> Chief Justice -> END?")
                )
                if success:
                    prompt += f" Success: {success}"
                if failure:
                    prompt += f" Flag as failure: {failure}"
                prompt += " Reply in 1-2 sentences."
                descriptions: list[str] = []
                for idx, img in enumerate(images[:5]):
                    raw = img.get("data") or b""
                    if not raw:
                        continue
                    ext = (img.get("ext") or "").lower()
                    if ext in ("jpg", "jpeg") or raw[:2] == b"\xff\xd8":
                        mime = "image/jpeg"
                    else:
                        mime = "image/png"
                    b64 = base64.b64encode(raw).decode("utf-8")
                    msg = HumanMessage(
                        content=[
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ]
                    )
                    response = llm.invoke([msg])
                    if hasattr(response, "content") and response.content:
                        descriptions.append(f"[Image {idx+1}]: {response.content.strip()}")
                if descriptions:
                    content = f"Extracted {len(images)} image(s). Vision: " + " ".join(descriptions)
                    rationale = "; ".join(descriptions)
                    confidence = 0.8
                else:
                    content = f"Extracted {len(images)} image(s); vision returned no content"
            except Exception as e:
                from src.llm_errors import (
                    APIQuotaOrFailureError,
                    InvalidModelError,
                    NoModelProvidedError,
                    normalize_llm_exception,
                )
                if isinstance(e, (NoModelProvidedError, InvalidModelError, APIQuotaOrFailureError)):
                    raise
                raise normalize_llm_exception(e)
    elif images:
        content = f"Extracted {len(images)} image(s) from PDF; Ollama not available, vision skipped"
        rationale = "Ollama not available; vision analysis skipped"

    for d in dimensions:
        dim_id = d.get("id", "unknown")
        if content:
            evidences[dim_id] = [_evidence(dim_id, True, content, pdf_path, rationale, confidence)]
        else:
            evidences[dim_id] = [_evidence(dim_id, False, None, pdf_path, rationale if images else "No images or extract failed", 0.0)]
    return {"evidences": evidences}
