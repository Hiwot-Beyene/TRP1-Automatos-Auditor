"""Audit type classification and context-aware tool selection.

This module provides pre-execution classification to determine audit type
and select only relevant tools and dimensions, eliminating unnecessary execution.
"""

from typing import Any, Literal

GITHUB_REPO_ARTIFACT = "github_repo"
PDF_REPORT_ARTIFACT = "pdf_report"
PDF_IMAGES_ARTIFACT = "pdf_images"


AuditType = Literal["repo_only", "report_only", "both"]


def classify_audit_type(repo_url: str, pdf_path: str) -> AuditType:
    """Classify audit type based on available inputs.
    
    Args:
        repo_url: Repository URL (empty string if not provided)
        pdf_path: PDF path/URL (empty string if not provided)
        
    Returns:
        Audit type: 'repo_only', 'report_only', or 'both'
    """
    repo_url = (repo_url or "").strip()
    pdf_path = (pdf_path or "").strip()
    
    has_repo = bool(repo_url)
    has_pdf = bool(pdf_path)
    
    if has_repo and has_pdf:
        return "both"
    elif has_repo:
        return "repo_only"
    elif has_pdf:
        return "report_only"
    else:
        raise ValueError("At least one of repo_url or pdf_path must be provided")


def get_active_artifacts(audit_type: AuditType) -> list[str]:
    """Get list of active artifacts for the given audit type.
    
    Args:
        audit_type: The classified audit type
        
    Returns:
        List of artifact types that should be processed
    """
    if audit_type == "repo_only":
        return [GITHUB_REPO_ARTIFACT]
    elif audit_type == "report_only":
        return [PDF_REPORT_ARTIFACT, PDF_IMAGES_ARTIFACT]
    elif audit_type == "both":
        return [GITHUB_REPO_ARTIFACT, PDF_REPORT_ARTIFACT, PDF_IMAGES_ARTIFACT]
    else:
        raise ValueError(f"Unknown audit type: {audit_type}")


def filter_dimensions_by_audit_type(
    rubric_dimensions: list[dict[str, Any]],
    audit_type: AuditType,
    repo_url: str = "",
    pdf_path: str = "",
) -> list[dict[str, Any]]:
    """Filter rubric dimensions to only those relevant for the audit type.
    
    Args:
        rubric_dimensions: All available rubric dimensions
        audit_type: The classified audit type
        repo_url: Repository URL (for report_accuracy check)
        pdf_path: PDF path (for report_accuracy check)
        
    Returns:
        Filtered list of dimensions that should be evaluated
    """
    active_artifacts = get_active_artifacts(audit_type)
    
    filtered = [
        d for d in rubric_dimensions
        if d.get("target_artifact") in active_artifacts
    ]
    
    report_accuracy_needs_both = bool(repo_url) and bool(pdf_path)
    if not report_accuracy_needs_both:
        filtered = [d for d in filtered if d.get("id") != "report_accuracy"]
    
    return filtered


def get_required_detective_nodes(audit_type: AuditType) -> list[str]:
    """Get list of detective nodes that should execute for the audit type.
    
    Args:
        audit_type: The classified audit type
        
    Returns:
        List of node names that should be executed
    """
    if audit_type == "repo_only":
        return ["repo_investigator"]
    elif audit_type == "report_only":
        return ["doc_analyst", "vision_inspector"]
    elif audit_type == "both":
        return ["repo_investigator", "doc_analyst", "vision_inspector"]
    else:
        raise ValueError(f"Unknown audit type: {audit_type}")


def get_tool_scope_for_audit_type(audit_type: AuditType) -> dict[str, list[str]]:
    """Get the scope of tools that should be executed for the audit type.
    
    Args:
        audit_type: The classified audit type
        
    Returns:
        Dictionary mapping artifact types to their required tools
    """
    from src.config import SUPPORTED_ARTIFACT_TOOLS
    
    active_artifacts = get_active_artifacts(audit_type)
    
    return {
        artifact: SUPPORTED_ARTIFACT_TOOLS.get(artifact, [])
        for artifact in active_artifacts
    }
