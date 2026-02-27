"""ReportAccuracyNode: cross-reference file paths in PDF with repo evidence (runs after EvidenceAggregator)."""

from typing import Any

from src.state import Evidence
from src.tools.doc_tools import extract_file_paths_from_text, ingest_pdf


def ReportAccuracyNode(state: dict[str, Any]) -> dict[str, Any]:
    """Cross-reference file paths mentioned in PDF with repo evidence. Requires aggregated evidences and pdf_path."""
    pdf_path = state.get("pdf_path") or ""
    evidences = state.get("evidences") or {}
    rubric_dimensions = state.get("rubric_dimensions") or []
    report_accuracy_dim = next((d for d in rubric_dimensions if d.get("id") == "report_accuracy"), None)
    if not report_accuracy_dim:
        return {}

    repo_content_parts: list[str] = []
    for dim_id, elist in evidences.items():
        if dim_id == "report_accuracy":
            continue
        for e in elist or []:
            if isinstance(e, Evidence):
                repo_content_parts.append(e.content or "")
                repo_content_parts.append(e.location or "")
            elif isinstance(e, dict):
                repo_content_parts.append(e.get("content") or "")
                repo_content_parts.append(e.get("location") or "")
    repo_text = " ".join(repo_content_parts)

    if not pdf_path:
        return {
            "evidences": {
                "report_accuracy": [
                    Evidence(
                        goal="report_accuracy",
                        found=False,
                        content=None,
                        location="",
                        rationale="No pdf_path; cross-reference skipped",
                        confidence=0.0,
                    )
                ]
            }
        }

    try:
        chunks = ingest_pdf(pdf_path)
        pdf_text = " ".join(c.get("text", "") for c in chunks)
    except Exception as e:
        return {
            "evidences": {
                "report_accuracy": [
                    Evidence(
                        goal="report_accuracy",
                        found=False,
                        content=None,
                        location=pdf_path,
                        rationale=f"PDF ingest failed: {e!s}"[:200],
                        confidence=0.0,
                    )
                ]
            }
        }

    paths_in_pdf = extract_file_paths_from_text(pdf_text)
    paths_in_repo = set()
    for p in extract_file_paths_from_text(repo_text):
        paths_in_repo.add(p)
        paths_in_repo.add(p.split("/")[-1])

    verified = [p for p in paths_in_pdf if p in paths_in_repo or p.split("/")[-1] in paths_in_repo]
    hallucinated = [p for p in paths_in_pdf if p not in verified]

    found = len(hallucinated) == 0
    content = f"Verified: {verified[:15]}; Hallucinated: {hallucinated[:15]}"
    rationale = f"Paths in PDF: {len(paths_in_pdf)}; verified: {len(verified)}; hallucinated: {len(hallucinated)}"
    confidence = 0.9 if found and paths_in_pdf else (0.5 if paths_in_pdf else 0.0)

    return {
        "evidences": {
            "report_accuracy": [
                Evidence(
                    goal="report_accuracy",
                    found=found,
                    content=content,
                    location=pdf_path,
                    rationale=rationale,
                    confidence=confidence,
                )
            ]
        }
    }
