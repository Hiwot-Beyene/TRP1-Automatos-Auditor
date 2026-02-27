"""EvidenceAggregator: fan-in node that collects and optionally normalizes evidences from all detectives."""

from typing import Any

from src.config import SUPPORTED_ARTIFACT_TOOLS, get_missing_tools_rationale
from src.state import Evidence


def EvidenceAggregatorNode(state: dict[str, Any]) -> dict[str, Any]:
    """Fan-in: state already has evidences merged (reducer) from parallel detectives. Normalize per dimension; add missing-tools evidence for dimensions whose target_artifact is not supported."""
    evidences = state.get("evidences") or {}
    rubric_dimensions = state.get("rubric_dimensions") or []
    out: dict[str, list[Evidence]] = {}
    for dim_id, elist in evidences.items():
        if not isinstance(elist, list):
            continue
        out[dim_id] = [e for e in elist if isinstance(e, Evidence)]
    for d in rubric_dimensions:
        dim_id = d.get("id", "unknown")
        if dim_id in out:
            continue
        target_artifact = d.get("target_artifact", "")
        if target_artifact not in SUPPORTED_ARTIFACT_TOOLS:
            rationale = get_missing_tools_rationale(target_artifact)
            out[dim_id] = [
                Evidence(goal=dim_id, found=False, content=None, location="", rationale=rationale, confidence=0.0)
            ]
    return {"evidences": out} if out else {}
