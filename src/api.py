"""FastAPI backend: POST /api/run with rubric from rubric.json; GET /api/rubric."""

import re

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.graph import build_detective_graph
from src.parallelism_checks import run_parallelism_checks
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


class RunResponse(BaseModel):
    evidences: dict[str, list[dict]]
    final_report: dict | None = None
    overall_score: float | None = None


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


@app.post("/api/run", response_model=RunResponse)
def run_audit(req: RunRequest) -> RunResponse:
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
    graph = build_detective_graph()
    state = graph.invoke({
        "repo_url": repo_url,
        "pdf_path": pdf_path,
        "rubric_dimensions": rubric_dimensions,
    })
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


@app.get("/api/parallelism-tests", response_model=ParallelismTestsResponse)
def parallelism_tests() -> ParallelismTestsResponse:
    results = run_parallelism_checks()
    out = [ParallelismTestResult(name=r["name"], passed=r["passed"], message=r["message"]) for r in results]
    return ParallelismTestsResponse(results=out, all_passed=all(r.passed for r in out))
