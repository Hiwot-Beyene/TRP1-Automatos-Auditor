"""Sandboxed repo clone, git history, and AST-based graph structure analysis."""

import ast
import re
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class RepoCloneError(Exception):
    """Raised when clone fails: bad URL, auth, or timeout (after retries)."""


CLONE_TIMEOUT_SEC = 120
GIT_LOG_TIMEOUT_SEC = 30
MAX_CLONE_RETRIES = 2
INITIAL_BACKOFF_SEC = 2.0

_GIT_URL_PATTERN = re.compile(
    r"^https?://([^/]+/)+[^/]+/?$|^git@[^:]+:[^/]+/[^/]+\.git$"
)


def _is_transient_clone_error(stderr: str, stdout: str) -> bool:
    s = (stderr + " " + stdout).lower()
    if "timed out" in s or "timeout" in s:
        return True
    if "connection refused" in s or "connection reset" in s:
        return True
    if "could not resolve host" in s or "name or service not known" in s:
        return True
    return False


def _sanitize_url(url: str) -> str:
    s = (url or "").strip()
    if "\n" in url or "\r" in url or " " in url:
        raise RepoCloneError("Invalid repo URL: contains disallowed characters")
    return s


@contextmanager
def sandboxed_clone(repo_url: str):
    """Clone repo into a temp directory. Yields path. Raises RepoCloneError on failure.
    Transient errors (timeout, connection) are retried with backoff; permanent errors (auth, not found) fail immediately."""
    url = _sanitize_url(repo_url)
    if not url:
        raise RepoCloneError("Repo URL is empty")
    if not _GIT_URL_PATTERN.match(url) and not url.startswith("git@"):
        if "github.com" not in url and "gitlab" not in url and "bitbucket" not in url:
            raise RepoCloneError(
                f"Invalid repo URL: not a recognized git URL (e.g. https://github.com/owner/repo)"
            )
    tmp = tempfile.TemporaryDirectory(prefix="auditor_clone_")
    result = None
    last_error: str | None = None
    try:
        for attempt in range(MAX_CLONE_RETRIES + 1):
            try:
                result = subprocess.run(
                    ["git", "clone", "--depth", "50", url, tmp.name],
                    capture_output=True,
                    text=True,
                    timeout=CLONE_TIMEOUT_SEC,
                    cwd=None,
                )
            except subprocess.TimeoutExpired:
                last_error = "Clone timed out"
                if attempt >= MAX_CLONE_RETRIES:
                    raise RepoCloneError(
                        f"git clone failed after {MAX_CLONE_RETRIES + 1} attempts: {last_error}"
                    )
                if attempt < MAX_CLONE_RETRIES:
                    time.sleep(INITIAL_BACKOFF_SEC * (2**attempt))
                continue
            if result.returncode == 0:
                yield tmp.name
                return
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            last_error = stderr or stdout or "no output"
            if "could not read Username" in stderr or "Authentication failed" in stderr:
                raise RepoCloneError(f"Git authentication failed: {stderr[:300]}")
            if "Repository not found" in stderr or "404" in stderr:
                raise RepoCloneError(f"Repository not found or inaccessible: {stderr[:300]}")
            if not _is_transient_clone_error(stderr, stdout) or attempt >= MAX_CLONE_RETRIES:
                raise RepoCloneError(
                    f"git clone failed (exit {result.returncode}): {last_error[:400]}"
                )
            if attempt < MAX_CLONE_RETRIES:
                time.sleep(INITIAL_BACKOFF_SEC * (2**attempt))
        raise RepoCloneError(
            f"git clone failed: {last_error or 'unknown'}"
        )
    finally:
        tmp.cleanup()


def extract_git_history(repo_path: str) -> list[dict[str, Any]]:
    """Run git log --oneline --reverse; return list of {message, timestamp}."""
    path = Path(repo_path)
    if not path.is_dir():
        return []
    result = subprocess.run(
        ["git", "log", "--oneline", "--reverse", "--format=%h %s%n%ci"],
        capture_output=True,
        text=True,
        timeout=GIT_LOG_TIMEOUT_SEC,
        cwd=str(path),
    )
    if result.returncode != 0:
        return []
    out = (result.stdout or "").strip()
    entries = []
    for block in out.split("\n\n"):
        lines = block.strip().split("\n")
        if not lines:
            continue
        first = lines[0]
        parts = first.split(" ", 1)
        message = parts[1] if len(parts) > 1 else first
        ts = lines[1].strip() if len(lines) > 1 else ""
        entries.append({"message": message, "timestamp": ts})
    return entries


def analyze_graph_structure(repo_path: str) -> dict[str, Any]:
    """
    Use AST to inspect graph structure: StateGraph usage, add_edge/add_conditional_edges,
    decorators, inheritance (BaseModel, TypedDict). Returns edges, nodes, has_state_graph,
    has_conditional_edges, reducers, state_classes.
    """
    path = Path(repo_path)
    graph_file = path / "src" / "graph.py"
    state_file = path / "src" / "state.py"
    out: dict[str, Any] = {
        "has_state_graph": False,
        "nodes": [],
        "edges": [],
        "has_conditional_edges": False,
        "state_classes": [],
        "reducers": [],
    }
    for file_path in (graph_file, state_file):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = []
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        bases.append(b.id)
                    elif isinstance(b, ast.Attribute):
                        bases.append(ast.unparse(b) if hasattr(ast, "unparse") else b.attr)
                if "StateGraph" in bases or "TypedDict" in bases or "BaseModel" in bases:
                    out["state_classes"].append(node.name)
                if "TypedDict" in bases or "BaseModel" in bases:
                    for stmt in node.body:
                        if isinstance(stmt, ast.AnnAssign) and stmt.annotation:
                            _collect_reducers(stmt.annotation, out["reducers"])
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name):
                        var = func.value.id
                    else:
                        var = getattr(ast.unparse(func.value), "__call__", "") if hasattr(ast, "unparse") else ""
                    if func.attr == "add_edge":
                        out["has_state_graph"] = True
                        args = node.args
                        if len(args) >= 2:
                            src = _arg_to_str(args[0])
                            tgt = _arg_to_str(args[1])
                            if src and tgt:
                                out["edges"].append((src, tgt))
                    elif func.attr == "add_conditional_edges":
                        out["has_state_graph"] = True
                        out["has_conditional_edges"] = True
                        if node.args:
                            src = _arg_to_str(node.args[0])
                            if src:
                                out["edges"].append((src, "__conditional__"))
                    elif func.attr == "add_node" and node.args:
                        out["has_state_graph"] = True
                        name = _arg_to_str(node.args[0])
                        if name:
                            out["nodes"].append(name)
    out["nodes"] = list(dict.fromkeys(out["nodes"]))
    out["edges"] = list(dict.fromkeys(out["edges"]))
    return out


def _collect_reducers(ann: ast.expr, reducers: list[str]) -> None:
    if isinstance(ann, ast.Subscript):
        sl = ann.slice
        if isinstance(sl, ast.Tuple):
            for s in sl.elts:
                if isinstance(s, ast.Attribute) and getattr(s.value, "id", None) == "operator":
                    reducers.append(s.attr)
    for child in ast.iter_child_nodes(ann):
        _collect_reducers(child, reducers)


def _arg_to_str(arg: ast.expr) -> str:
    if isinstance(arg, ast.Constant):
        return str(arg.value) if arg.value is not None else ""
    if isinstance(arg, ast.Name):
        return arg.id
    if hasattr(ast, "unparse"):
        return ast.unparse(arg)
    return ""
