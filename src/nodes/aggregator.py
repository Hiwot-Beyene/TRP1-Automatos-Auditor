"""EvidenceAggregator: fan-in node that collects and optionally normalizes evidences from all detectives.
Only dimensions whose target_artifact matches the run's inputs (repo and/or document) are in scope."""

from typing import Any

from src.config import SUPPORTED_ARTIFACT_TOOLS, get_missing_tools_rationale
from src.state import Evidence


def _in_scope_dimensions(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Only evaluate dimensions for artifacts we have: doc-only → pdf_report + pdf_images only; repo-only → github_repo only; both → all. report_accuracy needs both repo and PDF."""
    rubric_dimensions = state.get("rubric_dimensions") or []
    repo_url = (state.get("repo_url") or "").strip()
    pdf_path = (state.get("pdf_path") or "").strip()
    active_artifacts: list[str] = []
    if repo_url:
        active_artifacts.append("github_repo")
    if pdf_path:
        active_artifacts.append("pdf_report")
        active_artifacts.append("pdf_images")
    if not active_artifacts:
        return []
    in_scope = [d for d in rubric_dimensions if d.get("target_artifact") in active_artifacts]
    if not in_scope:
        return []
    report_accuracy_needs_both = repo_url and pdf_path
    return [d for d in in_scope if d.get("id") != "report_accuracy" or report_accuracy_needs_both]


def EvidenceAggregatorNode(state: dict[str, Any]) -> dict[str, Any]:
    """Fan-in: merge evidences; only in-scope dimensions (by repo_url/pdf_path) get evidence and pass to judges."""
    evidences = state.get("evidences") or {}
    rubric_dimensions = state.get("rubric_dimensions") or []
    in_scope = _in_scope_dimensions(state)
    out: dict[str, list[Evidence]] = {}
    for dim in in_scope:
        dim_id = dim.get("id", "unknown")
        elist = evidences.get(dim_id)
        if isinstance(elist, list):
            out[dim_id] = [e for e in elist if isinstance(e, Evidence)]
        else:
            out[dim_id] = []
    for d in in_scope:
        dim_id = d.get("id", "unknown")
        if dim_id in out and out[dim_id]:
            continue
        target_artifact = d.get("target_artifact", "")
        if target_artifact not in SUPPORTED_ARTIFACT_TOOLS:
            rationale = get_missing_tools_rationale(target_artifact)
        else:
            rationale = "No evidence collected for this criterion (tool not run for this input)."
        out[dim_id] = [
            Evidence(goal=dim_id, found=False, content=None, location="", rationale=rationale, confidence=0.0)
        ]
    result: dict[str, Any] = {"evidences": out, "rubric_dimensions": in_scope}
    return result
