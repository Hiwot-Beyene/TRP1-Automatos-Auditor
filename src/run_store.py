"""In-memory run store and background job runner. Enables async API: submit run, poll by run_id."""

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from src.config import get_max_concurrent_runs
from src.llm_errors import LLMError

logger = logging.getLogger(__name__)

_run_store: dict[str, dict[str, Any]] = {}
_store_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = None
_semaphore: threading.Semaphore | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=get_max_concurrent_runs() + 2, thread_name_prefix="auditor_run")
    return _executor


def _get_semaphore() -> threading.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = threading.Semaphore(get_max_concurrent_runs())
    return _semaphore


def _execute_run(run_id: str, repo_url: str, pdf_path: str, rubric_dimensions: list[dict], report_type: str | None = None) -> None:
    sem = _get_semaphore()
    sem.acquire()
    try:
        with _store_lock:
            if run_id in _run_store:
                _run_store[run_id]["status"] = "running"
        try:
            from src.graph import build_detective_graph
            graph = build_detective_graph()
            state_input = {
                "repo_url": repo_url,
                "pdf_path": pdf_path,
                "rubric_dimensions": rubric_dimensions,
                "report_type": report_type or "self",  # Default to "self" if not provided
            }
            state = graph.invoke(
                state_input,
                config={
                    "run_name": "LangGraph",
                    "thread_id": run_id,
                    "project_name": "week2-automato-auditor",
                    "tags": ["audit", "api", "async"],
                    "metadata": {"run_id": run_id, "repo_url": (repo_url or "")[:80], "has_pdf": bool(pdf_path)},
                },
            )
            evidences = state.get("evidences") or {}
            final_report = state.get("final_report")
            if final_report is not None and hasattr(final_report, "model_dump"):
                final_report = final_report.model_dump()
            overall = None
            if isinstance(final_report, dict):
                overall = final_report.get("overall_score")
            result = {
                "evidences": {k: [e.model_dump() if hasattr(e, "model_dump") else e for e in v] for k, v in evidences.items()},
                "final_report": final_report,
                "overall_score": overall,
            }
            with _store_lock:
                if run_id in _run_store:
                    _run_store[run_id]["status"] = "completed"
                    _run_store[run_id]["result"] = result
                    _run_store[run_id]["finished_at"] = time.time()
        except Exception as e:
            from src.llm_errors import user_message_for_exception

            with _store_lock:
                if run_id in _run_store:
                    _run_store[run_id]["status"] = "failed"
                    err_msg = getattr(e, "message", None) or user_message_for_exception(e) or str(e)
                    _run_store[run_id]["error"] = err_msg[:500]
                    _run_store[run_id]["finished_at"] = time.time()
            if isinstance(e, LLMError):
                logger.warning("Run %s failed (LLM): %s", run_id, e.message)
            else:
                logger.exception("Run %s failed", run_id)
    finally:
        sem.release()


def submit_run(repo_url: str, pdf_path: str, rubric_dimensions: list[dict], report_type: str | None = None) -> str:
    """Enqueue a run; returns run_id. Run executes in background."""
    run_id = str(uuid.uuid4())
    with _store_lock:
        _run_store[run_id] = {
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": time.time(),
            "finished_at": None,
        }
    _get_executor().submit(_execute_run, run_id, repo_url, pdf_path, rubric_dimensions, report_type)
    return run_id


def get_run(run_id: str) -> dict[str, Any] | None:
    """Return run record: status (pending|running|completed|failed), result, error."""
    with _store_lock:
        return _run_store.get(run_id)


def get_run_status(run_id: str) -> str:
    """Return status string or 'not_found'."""
    r = get_run(run_id)
    if r is None:
        return "not_found"
    return r["status"]
