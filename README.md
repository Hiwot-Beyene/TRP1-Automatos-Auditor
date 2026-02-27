# TRP1-Automatos-Auditor

Automaton Auditor — Digital Courtroom agent graph. Graph flow: START → entry → [doc_gate, repo_gate, vision_gate] (parallel fan-out) → [doc_analyst, repo_investigator, vision_inspector] → evidence_aggregator (fan-in) → [defense, prosecutor, tech_lead] (parallel fan-out) → chief_justice (fan-in) → END. Conditional routing handles missing artifacts and evidence validation.

**Default LLM stack:** All nodes use **Ollama (qwen2.5:7b)** running locally. No API keys required. LangSmith optional for observability. See [ENV_SETUP.md](ENV_SETUP.md) for configuration.

## Supported Python and lock file

- **Python:** 3.10, 3.11, 3.12 (see `requires-python` in `pyproject.toml`). Use one of these for compatibility.
- **Dependency lock files:** `uv.lock` (Python) and `frontend/package-lock.json` (Node) are committed for reproducible installs. Run `uv sync` (and `npm install` in frontend); after dependency changes run `uv lock` / `npm install` and commit the updated lock file(s).

## Scripts and optional tooling

| Tool / script | Purpose |
|---------------|---------|
| **uv** | Package manager and runner: `uv sync`, `uv run pytest`, `uv run python scripts/run_audit.py ...`. Required. |
| **scripts/run_audit.py** | CLI: full audit (detectives → judges → Chief Justice); writes Markdown to `audit/` and, by `--mode`, to `audit/report_onself_generated/` or `audit/report_onpeer_generated/`. |
| **Frontend (Next.js)** | Optional: run API then `cd frontend && npm run dev` for the Web UI. |
| **pytest** | `uv run pytest tests/ -v` for unit, contract, and integration tests. |
| **Makefile** | None; use `uv` and the scripts above for common tasks. |

## Final submission (challenge deliverables)

The repository contains all required source code for the challenge:

| Requirement | Location | Notes |
|-------------|----------|--------|
| **State definitions** | `src/state.py` | `Evidence`, `JudicialOpinion`, `CriterionResult`, `AuditReport`, `AgentState` (TypedDict) with reducers `operator.ior` (evidences), `operator.add` (opinions). |
| **Forensic tools (repo)** | `src/tools/repo_tools.py` | Sandboxed clone (`tempfile.TemporaryDirectory`, `subprocess.run`), `extract_git_history`, `analyze_graph_structure` (AST), `analyze_git_forensic`, `scan_forensic_evidence`. `RepoCloneError` for bad URL/auth. |
| **PDF / cross-reference tools** | `src/tools/doc_tools.py` | `ingest_pdf`, `pdf_to_binary`, `extract_images_from_pdf`, RAG-lite search, cross-reference helpers. |
| **Detectives** | `src/nodes/detectives.py` | **RepoInvestigator** (repo tools only), **DocAnalyst** (PDF chunks + theoretical depth), **VisionInspector** (extract images + vision model). VisionInspector: implementation required, execution when PDF provided. |
| **Judges** | `src/nodes/judges.py` | **Prosecutor**, **Defense**, **Tech Lead** with distinct system prompts. Uses `.with_structured_output(JudicialOpinion)` (and JSON fallback). Bound to Pydantic `JudicialOpinion` schema. |
| **Chief Justice** | `src/nodes/justice.py` | **ChiefJusticeNode**: hardcoded deterministic rules (security override, fact supremacy, dissent when variance > 2). Produces `AuditReport`; serialized to Markdown; `final_report` in state. |
| **Graph** | `src/graph.py` | **StateGraph**: START → `entry` → [doc_gate, repo_gate, vision_gate] (parallel fan-out) → conditional routing → [doc_analyst, repo_investigator, vision_inspector] → `evidence_aggregator` (fan-in) → conditional (proceed → defense | skip → END) + direct edges to prosecutor, tech_lead → [defense, prosecutor, tech_lead] → `chief_justice` (fan-in) → END. Conditional edges handle missing artifacts and evidence validation. End-to-end: repo URL (+ optional PDF) input → Markdown report in `audit/`. |

## Interim submission checklist

| Deliverable | Description |
|-------------|-------------|
| `src/state.py` | Pydantic/TypedDict state definitions (`Evidence`, `JudicialOpinion`, `AgentState`) with reducers `operator.add`, `operator.ior` |
| `src/tools/repo_tools.py` | Sandboxed git clone (tempfile), git log extraction, AST-based graph structure analysis |
| `src/tools/doc_tools.py` | PDF ingestion and chunked querying (RAG-lite approach) |
| `src/nodes/detectives.py` | RepoInvestigator, DocAnalyst, VisionInspector as LangGraph nodes outputting structured `Evidence` |
| `src/nodes/judges.py` | Prosecutor, Defense, TechLead with `.with_structured_output(JudicialOpinion)` (Ollama) |
| `src/nodes/justice.py` | ChiefJusticeNode: hardcoded synthesis rules, AuditReport → Markdown |
| `src/nodes/report_accuracy.py` | Cross-reference file paths in PDF with repo evidence (post-aggregator) |
| `src/graph.py` | Full StateGraph: detectives parallel → EvidenceAggregator → ReportAccuracy → Judges parallel → ChiefJustice; conditional proceed/skip |
| `pyproject.toml` | Locked dependencies via uv (`uv.lock` in repo) |
| `.env.example` | Environment variables (Ollama config, optional LangSmith, performance tuning) |
| `README.md` | Setup, install dependencies, run full audit against a target repo URL (below) |
| `audit/report_onself_generated/`, `audit/report_onpeer_generated/`, `audit/report_bypeer_received/` | Markdown reports from run_audit; place peer's report in `report_bypeer_received/`. For final submission add `reports/final_report.pdf`. |

## Requirements

- **Python**: 3.10+ (see `pyproject.toml` requires-python; 3.10, 3.11, 3.12 recommended)
- **Package manager**: [uv](https://docs.astral.sh/uv/)

## Scalability (API)

- **Sync vs async:** `POST /api/run` defaults to `?wait=true` (block until done, return result). Use `?wait=false` to get a `run_id` and poll `GET /api/run/{run_id}` for status and result so the HTTP worker isn’t blocked.
- **Rate limit:** At most `AUDITOR_MAX_CONCURRENT_RUNS` graph runs execute at once (default 2) to avoid overwhelming local Ollama instance.
- **Configurable workers:** `AUDITOR_DETECTIVE_WORKERS` and `AUDITOR_JUDGE_WORKERS` (default 3 each) control parallelism inside a run; set in `.env` or see `.env.example`.

## Setup

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter repo
cd TRP1-Automatos-Auditor

# Install dependencies (uses committed uv.lock for reproducible install)
uv sync

# Copy env template and configure (see .env.example)
cp .env.example .env
# Set OLLAMA_MODEL (default: qwen2.5:7b), OLLAMA_BASE_URL (default: http://localhost:11434)
# Optional: Set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY for observability

# Pull the Ollama model (required before first run)
ollama pull qwen2.5:7b
```

Keep `uv.lock` committed; after adding or upgrading dependencies, run `uv lock` and commit the updated `uv.lock`.

## Run the full audit (detectives → judges → Chief Justice → Markdown report)

```bash
# Repo only
uv run python scripts/run_audit.py https://github.com/owner/repo

# Repo + PDF report path (writes to audit/audit_report.md and, with script, to audit/report_onself_generated/ or audit/report_onpeer_generated/)
uv run python scripts/run_audit.py https://github.com/owner/repo /path/to/report.pdf

# Peer audit mode (report written to audit/report_onpeer_generated/)
uv run python scripts/run_audit.py https://github.com/peer/repo /path/to/report.pdf --mode peer
```

Uses `rubric.json`. Output is JSON with `evidences`, `final_report_path`, and `overall_score`. Markdown report: **Executive Summary → Criterion Breakdown → Remediation Plan**.

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

   After any run, the **Final report** section appears below with overall score (X/5), executive summary, per-criterion scores and judge opinions, and remediation plan.

Optional: in `frontend/.env.local` set `NEXT_PUBLIC_API_URL=http://localhost:8000` if the API runs on a different host/port.

### Step-by-step: Run backend + frontend for testing

1. **Terminal 1 — Backend**
   ```bash
   cd TRP1-Automatos-Auditor
   uv sync
   cp .env.example .env   # then set GROQ_API_KEY, GOOGLE_API_KEY (optional but needed for full judges/doc/vision)
   uv run uvicorn src.api:app --reload --port 8000
   ```
   Wait until you see `Uvicorn running on http://127.0.0.1:8000`.

2. **Terminal 2 — Frontend**
   ```bash
   cd TRP1-Automatos-Auditor/frontend
   npm install
   npm run dev
   ```
   Wait until you see `Ready on http://localhost:3000` (or the port shown).

3. **Browser**
   - Open **http://localhost:3000**.
   - If the rubric loads, the header will not show an error. If you see "Cannot reach API…", ensure the backend is running on port 8000.

4. **Run an audit**
   - **Repository tab:** Enter a repo URL (e.g. `https://github.com/owner/repo`), click **Run repo audit**. Wait for the run to finish. Check **Result** for evidences and **Final report** for overall score and criteria.
   - **Document tab:** Enter a PDF path or URL, click **Run document audit**. Check Result and Final report.
   - **Parallelism tab:** Enter both repo URL and document URL, click **Run repo + document together**. Check both evidence panels and the Final report below.

5. **Optional:** Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local` if the frontend runs on another host (e.g. in Docker) so it can reach the API.

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
