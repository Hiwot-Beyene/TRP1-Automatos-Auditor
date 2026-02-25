"""Unit tests for detective nodes (contract: input state, output evidences shape)."""

import pytest
from src.state import Evidence
from src.nodes.detectives import (
    RepoInvestigatorNode,
    DocAnalystNode,
    VisionInspectorNode,
    _dimensions_for_artifact,
)


def test_dimensions_for_artifact_filters():
    dims = [
        {"id": "a", "target_artifact": "github_repo"},
        {"id": "b", "target_artifact": "pdf_report"},
        {"id": "c", "target_artifact": "github_repo"},
    ]
    assert len(_dimensions_for_artifact(dims, "github_repo")) == 2
    assert _dimensions_for_artifact(dims, "pdf_report")[0]["id"] == "b"
    assert _dimensions_for_artifact(None, "github_repo") == []
    assert _dimensions_for_artifact([], "github_repo") == []


def test_repo_investigator_no_url_returns_evidences():
    state = {"repo_url": "", "rubric_dimensions": [{"id": "d1", "target_artifact": "github_repo"}]}
    out = RepoInvestigatorNode(state)
    assert "evidences" in out
    assert "d1" in out["evidences"]
    assert len(out["evidences"]["d1"]) == 1
    ev = out["evidences"]["d1"][0]
    assert isinstance(ev, Evidence) and ev.found is False and "No repo_url" in ev.rationale


def test_repo_investigator_with_dimensions_keys_by_id():
    state = {
        "repo_url": "",
        "rubric_dimensions": [{"id": "git_forensic", "target_artifact": "github_repo"}, {"id": "graph_arch", "target_artifact": "github_repo"}],
    }
    out = RepoInvestigatorNode(state)
    assert set(out["evidences"].keys()) == {"git_forensic", "graph_arch"}


def test_doc_analyst_no_pdf_path_returns_evidences():
    state = {"pdf_path": "", "rubric_dimensions": [{"id": "th", "target_artifact": "pdf_report"}]}
    out = DocAnalystNode(state)
    assert "evidences" in out
    assert "th" in out["evidences"]
    assert out["evidences"]["th"][0].found is False
    assert "No pdf_path" in out["evidences"]["th"][0].rationale


def test_vision_inspector_no_pdf_path_returns_evidences():
    state = {"pdf_path": "", "rubric_dimensions": [{"id": "swarm", "target_artifact": "pdf_images"}]}
    out = VisionInspectorNode(state)
    assert "evidences" in out
    assert "swarm" in out["evidences"]
    assert out["evidences"]["swarm"][0].found is False
