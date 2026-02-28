"""Unit tests for repo_tools: sandboxed clone, AST graph analysis, bad URL and auth handling."""

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.tools.repo_tools import (
    RepoCloneError,
    analyze_graph_structure,
    extract_git_history,
    sandboxed_clone,
)


def test_sandboxed_clone_empty_url_raises():
    with pytest.raises(RepoCloneError, match="empty"):
        with sandboxed_clone(""):
            pass


def test_sandboxed_clone_invalid_url_raises():
    with pytest.raises(RepoCloneError, match="Invalid repo URL"):
        with sandboxed_clone("not-a-url"):
            pass


def test_sandboxed_clone_disallowed_chars_raises():
    with pytest.raises(RepoCloneError, match="disallowed"):
        with sandboxed_clone("https://github.com/a/b\n"):
            pass


def test_sandboxed_clone_auth_failure_raises():
    with patch("src.tools.repo_tools.subprocess.run") as m:
        m.return_value = SimpleNamespace(
            returncode=1,
            stderr="fatal: could not read Username for 'https://github.com'",
            stdout="",
        )
        with pytest.raises(RepoCloneError, match="authentication"):
            with sandboxed_clone("https://github.com/owner/private-repo"):
                pass


def test_sandboxed_clone_repo_not_found_raises():
    with patch("src.tools.repo_tools.subprocess.run") as m:
        m.return_value = SimpleNamespace(returncode=1, stderr="Repository not found.", stdout="")
        with pytest.raises(RepoCloneError, match="not found"):
            with sandboxed_clone("https://github.com/owner/nonexistent-repo-xyz"):
                pass


def test_extract_git_history_empty_dir():
    with tempfile.TemporaryDirectory() as d:
        out = extract_git_history(d)
    assert out == []


def test_extract_git_history_nonexistent_path():
    assert extract_git_history("/nonexistent/path/xyz") == []


def test_analyze_graph_structure_nonexistent_path():
    out = analyze_graph_structure("/nonexistent/repo/path")
    assert out["has_state_graph"] is False
    assert out["nodes"] == []
    assert out["edges"] == []
    assert out["has_conditional_edges"] is False


def test_analyze_graph_structure_this_repo():
    repo_root = Path(__file__).resolve().parent.parent.parent
    out = analyze_graph_structure(str(repo_root))
    assert "has_state_graph" in out
    assert "nodes" in out
    assert "edges" in out
    assert "has_conditional_edges" in out
    assert "state_classes" in out
    assert "reducers" in out
    assert out["has_state_graph"] is True
    assert "evidence_aggregator" in out["nodes"] or any(
        "evidence_aggregator" in str(e) for e in out["edges"]
    )
    assert out["has_conditional_edges"] is True
