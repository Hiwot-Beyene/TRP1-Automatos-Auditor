"""Integration test: build graph, invoke with minimal state, assert result shape."""

import pytest
from src.graph import build_detective_graph
from src.state import Evidence


def test_graph_invoke_returns_evidences():
    compiled = build_detective_graph()
    rubric = [
        {"id": "r1", "name": "Repo", "target_artifact": "github_repo"},
        {"id": "d1", "name": "Doc", "target_artifact": "pdf_report"},
        {"id": "v1", "name": "Vision", "target_artifact": "pdf_images"},
    ]
    state = compiled.invoke({
        "repo_url": "",
        "pdf_path": "",
        "rubric_dimensions": rubric,
    })
    assert "evidences" in state
    evidences = state["evidences"]
    assert "r1" in evidences and "d1" in evidences and "v1" in evidences
    for dim_id, elist in evidences.items():
        assert isinstance(elist, list)
        for e in elist:
            assert isinstance(e, Evidence)
            assert hasattr(e, "goal") and hasattr(e, "found") and hasattr(e, "rationale")


def test_graph_invoke_empty_rubric():
    compiled = build_detective_graph()
    state = compiled.invoke({"repo_url": "", "pdf_path": "", "rubric_dimensions": []})
    assert "evidences" in state
    assert state["evidences"] == {}
