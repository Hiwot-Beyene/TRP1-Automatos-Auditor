"""Supported artifact types and their required tools. Used for rubric-agnostic runs and missing-tool reporting."""

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


def get_missing_tools_rationale(target_artifact: str) -> str:
    """Return rationale listing required tool names when artifact type is unsupported."""
    tools = SUPPORTED_ARTIFACT_TOOLS.get(target_artifact)
    if tools is not None:
        return "Required tools not available: " + ", ".join(tools)
    return f"Required tools not available: {target_artifact!r} (unsupported artifact type; no handler for this target_artifact)."
