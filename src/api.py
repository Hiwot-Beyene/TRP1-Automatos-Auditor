"""FastAPI backend: POST /api/run (async job or sync with ?wait=true), GET /api/run/{run_id}, GET /api/rubric."""

import re

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.graph import build_detective_graph
from src.llm_errors import APIQuotaOrFailureError, InvalidModelError, LLMError, NoModelProvidedError, user_message_for_exception
from src.parallelism_checks import run_parallelism_checks
from src.run_store import get_run, submit_run
from src.rubric_loader import get_dimensions, get_rubric
from src.state import AuditReport, Evidence

app = FastAPI(title="Automaton Auditor API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPO_TO_PDF_PATH = "reports/final_report.pdf"
_GITHUB_REPO_RE = re.compile(
    r"(?:https?://(?:www\.)?github\.com/|git@github\.com:)([^/]+)/([^/#?\s]+?)(?:\.git)?/?$"
)


def default_pdf_url_from_repo(repo_url: str) -> str:
    """Derive raw GitHub PDF URL from repo (reports/final_report.pdf on main). Challenge: report committed to repo."""
    s = (repo_url or "").strip()
    m = _GITHUB_REPO_RE.search(s)
    if not m:
        return ""
    owner, repo = m.group(1), m.group(2)
    return f"https://raw.githubusercontent.com/{owner}/{repo}/main/{REPO_TO_PDF_PATH}"


class RunRequest(BaseModel):
    repo_url: str = ""
    pdf_path: str = ""
    rubric_dimensions: list[dict] | None = Field(default=None, description="Optional override; if omitted, rubric.json dimensions are used.")
    report_type: str | None = Field(default=None, description="One of: self, peer, peer_received. Affects report label and output subdir under audit/.")


class RunResponse(BaseModel):
    evidences: dict[str, list[dict]] | None = None
    final_report: dict | None = None
    overall_score: float | None = None


class RunSubmittedResponse(BaseModel):
    run_id: str
    status: str = "pending"
    message: str = "Run queued. Poll GET /api/run/{run_id} for status and result."


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    result: RunResponse | None = None
    error: str | None = None


class ParallelismTestResult(BaseModel):
    name: str
    passed: bool
    message: str


class ParallelismTestsResponse(BaseModel):
    results: list[ParallelismTestResult]
    all_passed: bool


def serialize_evidences(evidences: dict[str, list[Evidence]]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for dim_id, evs in evidences.items():
        out[dim_id] = [e.model_dump() if isinstance(e, Evidence) else e for e in evs]
    return out


@app.get("/api/rubric")
def api_get_rubric():
    """Return the machine-readable rubric from rubric.json (dimensions + synthesis_rules). Cached."""
    return get_rubric()


@app.get("/api/default-pdf-url")
def get_default_pdf_url(repo_url: str = "") -> dict:
    """Return default PDF URL for a GitHub repo (reports/final_report.pdf). Per challenge: report committed to repo."""
    return {"pdf_url": default_pdf_url_from_repo(repo_url)}


@app.post("/api/run")
def run_audit(
    req: RunRequest,
    wait: bool = Query(True, description="If true (default), block until run completes and return result. If false, return run_id; poll GET /api/run/{run_id} for result."),
):
    if not req.repo_url.strip() and not req.pdf_path.strip():
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of repo_url or pdf_path",
        )
    pdf_path = req.pdf_path.strip()
    repo_url = req.repo_url.strip()
    if repo_url and not pdf_path:
        default_url = default_pdf_url_from_repo(repo_url)
        if default_url:
            try:
                from src.tools.doc_tools import pdf_url_reachable
                if pdf_url_reachable(default_url):
                    pdf_path = default_url
            except Exception:
                pass
    rubric_dimensions = req.rubric_dimensions if req.rubric_dimensions is not None else get_dimensions()
    if not rubric_dimensions:
        raise HTTPException(
            status_code=500,
            detail="No rubric dimensions (rubric.json missing or empty)",
        )

    if wait:
        import uuid
        trace_id = str(uuid.uuid4())
        graph = build_detective_graph()
        state_input = {
            "repo_url": repo_url,
            "pdf_path": pdf_path,
            "rubric_dimensions": rubric_dimensions,
            "report_type": req.report_type or "self",  # Default to "self" if not provided
        }
        try:
            state = graph.invoke(
                state_input,
                config={
                    "run_name": "LangGraph",
                    "thread_id": trace_id,
                    "project_name": "week2-automato-auditor",
                    "tags": ["audit", "api", "sync"],
                    "metadata": {"repo_url": (repo_url or "")[:80], "has_pdf": bool(pdf_path), "trace_id": trace_id},
                },
            )
        except LLMError as e:
            status = 503 if isinstance(e, APIQuotaOrFailureError) else 400
            raise HTTPException(status_code=status, detail=e.message)
        except Exception as e:
            msg = user_message_for_exception(e)
            if msg:
                raise HTTPException(status_code=503, detail=msg)
            raise
        evidences = state.get("evidences") or {}
        final_report = state.get("final_report")
        if isinstance(final_report, AuditReport):
            final_report = final_report.model_dump()
        overall = None
        if isinstance(final_report, dict):
            overall = final_report.get("overall_score")
        return RunResponse(
            evidences=serialize_evidences(evidences),
            final_report=final_report if isinstance(final_report, dict) else None,
            overall_score=overall,
        )

    run_id = submit_run(repo_url, pdf_path, rubric_dimensions, req.report_type)
    return RunSubmittedResponse(run_id=run_id)


@app.get("/api/run/{run_id}", response_model=RunStatusResponse)
def get_run_status_result(run_id: str):
    """Return status and result for an async run. status: pending | running | completed | failed."""
    record = get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    result = None
    if record.get("result"):
        r = record["result"]
        result = RunResponse(
            evidences=r.get("evidences"),
            final_report=r.get("final_report"),
            overall_score=r.get("overall_score"),
        )
    return RunStatusResponse(
        run_id=run_id,
        status=record["status"],
        result=result,
        error=record.get("error"),
    )


@app.get("/api/parallelism-tests", response_model=ParallelismTestsResponse)
def parallelism_tests() -> ParallelismTestsResponse:
    results = run_parallelism_checks()
    out = [ParallelismTestResult(name=r["name"], passed=r["passed"], message=r["message"]) for r in results]
    return ParallelismTestsResponse(results=out, all_passed=all(r.passed for r in out))
