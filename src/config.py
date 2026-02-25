"""Supported artifact types and their required tools. Used for rubric-agnostic runs and missing-tool reporting."""

import os

SUPPORTED_ARTIFACT_TOOLS: dict[str, list[str]] = {
    "github_repo": [
        "sandboxed_clone",
        "extract_git_history",
        "analyze_graph_structure",
    ],
    "pdf_report": [
        "ingest_pdf",
        "search_theoretical_depth",
        "extract_file_paths_from_text",
        "cross_reference",
    ],
    "pdf_images": [
        "extract_images_from_pdf",
        "vision_analysis",
    ],
}


def get_detective_workers() -> int:
    """Max parallel workers for detective nodes (repo/doc/vision). Default 3."""
    v = os.environ.get("AUDITOR_DETECTIVE_WORKERS", "3").strip()
    try:
        n = int(v)
        return max(1, min(n, 8))
    except ValueError:
        return 3


def get_judge_workers() -> int:
    """Max parallel workers for judge panel (Prosecutor, Defense, TechLead). Default 3."""
    v = os.environ.get("AUDITOR_JUDGE_WORKERS", "3").strip()
    try:
        n = int(v)
        return max(1, min(n, 8))
    except ValueError:
        return 3


def get_max_concurrent_runs() -> int:
    """Max concurrent graph runs (rate limit). Default 2 to avoid bursting LLM APIs."""
    v = os.environ.get("AUDITOR_MAX_CONCURRENT_RUNS", "2").strip()
    try:
        n = int(v)
        return max(1, min(n, 32))
    except ValueError:
        return 2


def get_missing_tools_rationale(target_artifact: str) -> str:
    """Return rationale listing required tool names when artifact type is unsupported."""
    tools = SUPPORTED_ARTIFACT_TOOLS.get(target_artifact)
    if tools is not None:
        return "Required tools not available: " + ", ".join(tools)
    return f"Required tools not available: {target_artifact!r} (unsupported artifact type; no handler for this target_artifact)."
