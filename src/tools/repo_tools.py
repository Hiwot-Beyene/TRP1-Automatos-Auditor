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
    """Clone repo (main branch) into a temp directory. Yields path. Raises RepoCloneError on failure."""
    url = _sanitize_url(repo_url)
    if not url:
        raise RepoCloneError("Repo URL is empty")
    if not _GIT_URL_PATTERN.match(url) and not url.startswith("git@"):
        if "github.com" not in url and "gitlab" not in url and "bitbucket" not in url:
            raise RepoCloneError(
                f"Invalid repo URL: not a recognized git URL (e.g. https://github.com/owner/repo)"
            )
    tmp = tempfile.TemporaryDirectory(prefix="auditor_clone_")
    last_error: str | None = None
    result = None
    try:
        for attempt in range(MAX_CLONE_RETRIES + 1):
            for branch in ("main", "master", None):
                try:
                    cmd = ["git", "clone", "--depth", "200", url, tmp.name]
                    if branch:
                        cmd.insert(2, "--branch")
                        cmd.insert(3, branch)
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=CLONE_TIMEOUT_SEC,
                        cwd=None,
                    )
                except subprocess.TimeoutExpired:
                    last_error = "Clone timed out"
                    result = None
                    break
                if result.returncode == 0:
                    yield tmp.name
                    return
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                last_error = stderr or stdout or "no output"
                if branch and ("not found" in stderr.lower() or "does not exist" in stderr.lower()):
                    continue
                if "could not read Username" in stderr or "Authentication failed" in stderr:
                    raise RepoCloneError(f"Git authentication failed: {stderr[:300]}")
                if "Repository not found" in stderr or "404" in stderr:
                    raise RepoCloneError(f"Repository not found or inaccessible: {stderr[:300]}")
                if not branch:
                    break
            if (result is None or result.returncode != 0) and (not _is_transient_clone_error(last_error or "", "") or attempt >= MAX_CLONE_RETRIES):
                raise RepoCloneError(f"git clone failed: {(last_error or '')[:400]}")
            if attempt < MAX_CLONE_RETRIES:
                time.sleep(INITIAL_BACKOFF_SEC * (2**attempt))
        raise RepoCloneError(f"git clone failed: {last_error or 'unknown'}")
    finally:
        tmp.cleanup()


def extract_git_history(repo_path: str) -> list[dict[str, Any]]:
    """Run git log on current (main) branch; return list of {message, timestamp}."""
    path = Path(repo_path)
    if not path.is_dir():
        return []
    result = subprocess.run(
        ["git", "log", "--oneline", "--reverse", "-n", "500", "--format=%h %s%n%ci"],
        capture_output=True,
        text=True,
        timeout=GIT_LOG_TIMEOUT_SEC,
        cwd=str(path),
    )
    if result.returncode != 0:
        return []
    out = (result.stdout or "").strip()
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    entries = []
    i = 0
    while i + 1 < len(lines):
        first = lines[i]
        ts = lines[i + 1]
        parts = first.split(" ", 1)
        message = parts[1] if len(parts) > 1 else first
        entries.append({"message": message, "timestamp": ts})
        i += 2
    return entries


def analyze_git_forensic(history: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyze commit history for rubric git_forensic_analysis: progression story vs bulk upload.
    Returns: count, progression_story (bool), bulk_upload (bool), message_sample, timestamp_sample, summary (str).
    """
    out: dict[str, Any] = {
        "count": len(history),
        "progression_story": False,
        "bulk_upload": False,
        "message_sample": [],
        "timestamp_sample": [],
        "summary": "",
    }
    if not history:
        out["summary"] = "No commits found."
        return out
    out["message_sample"] = [h.get("message", "")[:60] for h in history[:20]]
    out["timestamp_sample"] = [h.get("timestamp", "") for h in history[:10]]
    lower_msgs = " ".join(h.get("message", "").lower() for h in history)
    setup = "setup" in lower_msgs or "env" in lower_msgs or "init" in lower_msgs
    tools = "tool" in lower_msgs or "repo" in lower_msgs or "clone" in lower_msgs
    graph = "graph" in lower_msgs or "state" in lower_msgs or "orchestrat" in lower_msgs or "judge" in lower_msgs
    iterative = "feat" in lower_msgs or "fix" in lower_msgs or "refactor" in lower_msgs or "chore" in lower_msgs or "docs" in lower_msgs or "add" in lower_msgs or "implement" in lower_msgs
    out["progression_story"] = (out["count"] > 3) and (setup or tools or graph or iterative)
    if out["count"] >= 3:
        try:
            from datetime import datetime
            times = []
            for h in history:
                ts = (h.get("timestamp") or "").strip()
                if not ts:
                    continue
                parts = ts.split()
                if len(parts) >= 2:
                    date_part = parts[0]
                    time_part = parts[1][:8]
                    try:
                        times.append(datetime.fromisoformat(f"{date_part} {time_part}"))
                    except Exception:
                        pass
                elif parts:
                    try:
                        times.append(datetime.fromisoformat(parts[0]))
                    except Exception:
                        pass
            if len(times) >= 2:
                span_sec = (max(times) - min(times)).total_seconds()
                out["bulk_upload"] = span_sec < 1800 and out["count"] >= 15
        except Exception:
            pass
    if out["count"] <= 2:
        out["bulk_upload"] = True
    if out["bulk_upload"]:
        out["summary"] = f"{out['count']} commits; timestamps clustered (likely bulk upload)."
    elif out["progression_story"]:
        out["summary"] = f"{out['count']} commits; progression story (iterative/setup/tool/graph themes)."
    else:
        out["summary"] = f"{out['count']} commits; limited progression indicators."
    return out


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


def scan_forensic_evidence(repo_path: str) -> dict[str, str]:
    """Scan clone for rubric-aligned evidence: safe_tool, structured_output, judicial_nuance, chief_justice_synthesis."""
    path = Path(repo_path)
    out: dict[str, str] = {}
    tools_file = path / "src" / "tools" / "repo_tools.py"
    judges_file = path / "src" / "nodes" / "judges.py"
    justice_file = path / "src" / "nodes" / "justice.py"
    if tools_file.is_file():
        try:
            t = tools_file.read_text(encoding="utf-8", errors="replace")
            has_tempfile = "TemporaryDirectory" in t and "tempfile" in t
            has_subprocess = "subprocess.run" in t
            # Use regex so this file does not contain literal "os.system(" (would trigger false positive)
            has_os_system = bool(re.search(r"os\.system\s*\(", t))
            out["safe_tool_engineering"] = (
                f"tempfile.TemporaryDirectory()={has_tempfile}; "
                f"subprocess.run() with capture_output/timeout={has_subprocess}; "
                f"os.system() (unsafe)={has_os_system}"
            )
        except OSError:
            pass
    if judges_file.is_file():
        try:
            j = judges_file.read_text(encoding="utf-8", errors="replace")
            has_structured = "with_structured_output" in j or "bind_tools" in j
            has_judicial_opinion = "JudicialOpinion" in j
            has_retry = "retry" in j.lower() and ("JUDGE_RETRY" in j or "attempt" in j)
            out["structured_output_enforcement"] = (
                f"with_structured_output/bind_tools={has_structured}; JudicialOpinion_schema={has_judicial_opinion}; retry_logic={has_retry}"
            )
            if "Prosecutor" in j and "Defense" in j and "TechLead" in j:
                out["judicial_nuance"] = "Prosecutor, Defense, TechLead personas present; distinct prompts"
        except OSError:
            pass
    if justice_file.is_file():
        try:
            j = justice_file.read_text(encoding="utf-8", errors="replace")
            has_security = "Rule of Security" in j or "security" in j.lower() and "cap" in j.lower()
            has_evidence = "Rule of Evidence" in j or "overruled" in j
            has_variance = "variance" in j and "2" in j
            out["chief_justice_synthesis"] = f"Rule_of_Security={has_security}; Rule_of_Evidence={has_evidence}; variance_re_evaluation={has_variance}"
        except OSError:
            pass
    return out
