# TRP1-Automatos-Auditor

Automaton Auditor — Digital Courtroom agent graph. Parallel detective nodes (RepoInvestigator, DocAnalyst, VisionInspector) fan-in to EvidenceAggregator; conditional edges handle proceed/skip. Judicial layer (Judges, Chief Justice) is planned; attachment point documented in `src/graph.py`.

## Interim submission checklist

| Deliverable | Description |
|-------------|-------------|
| `src/state.py` | Pydantic/TypedDict state definitions (`Evidence`, `JudicialOpinion`, `AgentState`) with reducers `operator.add`, `operator.ior` |
| `src/tools/repo_tools.py` | Sandboxed git clone (tempfile), git log extraction, AST-based graph structure analysis |
| `src/tools/doc_tools.py` | PDF ingestion and chunked querying (RAG-lite approach) |
| `src/nodes/detectives.py` | RepoInvestigator and DocAnalyst (and VisionInspector) as LangGraph nodes outputting structured `Evidence` |
| `src/graph.py` | StateGraph: detectives in parallel (fan-out) → EvidenceAggregator (fan-in). Judges not required yet. |
| `pyproject.toml` | Locked dependencies via uv (`uv.lock` in repo) |
| `.env.example` | Required API keys and env vars (no secrets committed) |
| `README.md` | Setup, install dependencies, run detective graph against a target repo URL (below) |

## Requirements

- **Python**: 3.10+ (see `pyproject.toml` requires-python)
- **Package manager**: [uv](https://docs.astral.sh/uv/)

## Setup

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter repo
cd TRP1-Automatos-Auditor

# Install dependencies (creates/updates uv.lock)
uv sync

# Copy env template and set API keys (optional; for LangSmith and PDF/vision)
cp .env.example .env
# Edit .env: set LANGCHAIN_API_KEY for tracing; add OPENAI/ANTHROPIC/GOOGLE keys if using PDF/vision.
```

Commit `uv.lock` so dependencies are reproducible.

## Run the detective graph against a target repo

**Explicit command** (no API/frontend):

```bash
# Repo only
uv run python scripts/run_audit.py https://github.com/owner/repo

# Repo + PDF report path
uv run python scripts/run_audit.py https://github.com/owner/repo /path/to/report.pdf
```

Uses `rubric.json` (machine-readable rubric from TRP1 Challenge doc). Output is JSON with `evidences` keyed by dimension id.

**Typical audit workflow**: 1) Clone target repo locally or use URL. 2) Run `scripts/run_audit.py <repo_url> [pdf_path]`. 3) Inspect evidences; later phases add Judges and Chief Justice to produce the final Markdown report.

## Run the project (Web UI)

1. **Start the API** (from repo root):

```bash
uv run uvicorn src.api:app --reload --port 8000
```

2. **Start the frontend** (in another terminal):

```bash
cd frontend && npm install && npm run dev
```

3. Open **http://localhost:3000**. Rubric is loaded from **rubric.json** (no user-editable rubric in the UI). Tabs:

   - **Repository** — Repository URL. Run repo audit (RepoInvestigator). Result shows evidences for `github_repo` dimensions.
   - **Document** — Document/PDF path or URL. Run document audit (DocAnalyst, VisionInspector).
   - **Parallelism** — Repo URL + Document URL. One run executes both in parallel and shows merged evidences.

Optional: in `frontend/.env.local` set `NEXT_PUBLIC_API_URL=http://localhost:8000` if the API runs on a different host/port.

**Programmatic use**: `from src.graph import build_detective_graph` then `graph.invoke({"repo_url": "...", "pdf_path": "...", "rubric_dimensions": [...]})`. State is returned with aggregated `evidences`. Load `rubric_dimensions` from `rubric.json` (see `src/api.py` `load_rubric_dimensions()`).

## Parallelism tests (TRP1 Challenge)

Contract tests for graph structure (fan-out, fan-in, conditional_edges, evidence merge):

```bash
uv run pytest tests/contract/test_detective_graph_parallelism.py -v
```

## Testing

- **Unit** (`tests/unit/`): state models, aggregator, detective nodes, repo_tools (bad URL, auth failure, AST graph analysis).
- **Contract** (`tests/contract/`): graph topology, conditional edges, evidence merge.
- **Integration** (`tests/integration/`): full graph invoke with minimal state.

Run all tests:

```bash
uv sync
uv run pytest tests/ -v
```
