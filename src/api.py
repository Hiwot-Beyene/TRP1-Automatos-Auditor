"""FastAPI backend: POST /api/run with rubric from rubric.json; GET /api/rubric."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.graph import build_detective_graph
from src.parallelism_checks import run_parallelism_checks
from src.state import Evidence

app = FastAPI(title="Automaton Auditor API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUBRIC_PATH = Path(__file__).resolve().parent.parent / "rubric.json"


def load_rubric_dimensions():
    """Load dimensions from rubric.json (documentation-defined constitution)."""
    if not RUBRIC_PATH.is_file():
        return []
    try:
        data = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))
        return data.get("dimensions", [])
    except (json.JSONDecodeError, OSError):
        return []


class RunRequest(BaseModel):
    repo_url: str = ""
    pdf_path: str = ""
    rubric_dimensions: list[dict] | None = Field(default=None, description="Optional override; if omitted, rubric.json dimensions are used.")


class RunResponse(BaseModel):
    evidences: dict[str, list[dict]]


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
def get_rubric():
    """Return the machine-readable rubric from rubric.json (dimensions + synthesis_rules)."""
    if not RUBRIC_PATH.is_file():
        return {"dimensions": [], "synthesis_rules": {}}
    try:
        return json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"dimensions": [], "synthesis_rules": {}}


@app.post("/api/run", response_model=RunResponse)
def run_audit(req: RunRequest) -> RunResponse:
    if not req.repo_url.strip() and not req.pdf_path.strip():
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of repo_url or pdf_path",
        )
    rubric_dimensions = req.rubric_dimensions if req.rubric_dimensions is not None else load_rubric_dimensions()
    if not rubric_dimensions:
        raise HTTPException(
            status_code=500,
            detail="No rubric dimensions (rubric.json missing or empty)",
        )
    graph = build_detective_graph()
    state = graph.invoke({
        "repo_url": req.repo_url.strip(),
        "pdf_path": req.pdf_path.strip(),
        "rubric_dimensions": rubric_dimensions,
    })
    evidences = state.get("evidences") or {}
    return RunResponse(evidences=serialize_evidences(evidences))


@app.get("/api/parallelism-tests", response_model=ParallelismTestsResponse)
def parallelism_tests() -> ParallelismTestsResponse:
    results = run_parallelism_checks()
    out = [ParallelismTestResult(name=r["name"], passed=r["passed"], message=r["message"]) for r in results]
    return ParallelismTestsResponse(results=out, all_passed=all(r.passed for r in out))
