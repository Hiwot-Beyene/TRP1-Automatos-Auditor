"""EvidenceAggregator: fan-in node that collects and optionally normalizes evidences from all detectives."""

from typing import Any

from src.state import Evidence


def EvidenceAggregatorNode(state: dict[str, Any]) -> dict[str, Any]:
    """Fan-in: state already has evidences merged (reducer) from parallel detectives. Optionally normalize per dimension."""
    evidences = state.get("evidences") or {}
    if not evidences:
        return {}
    out: dict[str, list[Evidence]] = {}
    for dim_id, elist in evidences.items():
        if not isinstance(elist, list):
            continue
        out[dim_id] = [e for e in elist if isinstance(e, Evidence)]
    return {"evidences": out} if out else {}
