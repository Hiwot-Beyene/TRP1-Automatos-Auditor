# TRP1-Automatos-Auditor

Automaton Auditor — Digital Courtroom agent graph. Runs parallel detective nodes (RepoInvestigator, DocAnalyst, VisionInspector) and aggregates evidence; judicial layer (Judges, Chief Justice) is planned for later phases.

## Setup

- **Python**: 3.10+
- **Package manager**: [uv](https://docs.astral.sh/uv/)

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter repo
cd TRP1-Automatos-Auditor

# Install dependencies
uv sync

# Copy env template and set API keys (optional; for LangSmith and PDF/vision)
cp .env.example .env
# Edit .env: set LANGCHAIN_API_KEY for tracing; add OPENAI/ANTHROPIC/GOOGLE keys if using PDF/vision.
```

## Run the project (Web UI)

Run audits and parallelism tests from the **Web UI**.

1. **Start the API** (from repo root):

```bash
uv run uvicorn src.api:app --reload --port 8000
```

2. **Start the frontend** (in another terminal):

```bash
cd frontend && npm install && npm run dev
```

3. Open **http://localhost:3000**. The UI has **3 tabs** (per TRP1 Challenge: each audit type can use its own rubric):

   - **Repository** — Repository URL + rubric (JSON). Run repo audit (RepoInvestigator). Result shown in the same tab.
   - **Document** — Document/PDF URL + rubric (JSON). Run document audit (DocAnalyst, VisionInspector). Result shown in the same tab.
   - **Parallelism** — Two blocks side by side: [Repo URL + rubric] and [Document URL + rubric]. One **Run repo + document together** sends both URLs and merges both rubrics in a single graph run (parallel detectives). Results are shown **for each**: repo result (evidences for `github_repo` dimensions) and document result (evidences for `pdf_report` / `pdf_images` dimensions).

Optional: in `frontend/.env.local` set `NEXT_PUBLIC_API_URL=http://localhost:8000` if the API runs on a different host/port.

**Programmatic use** (optional): `from src.graph import build_detective_graph` then `graph.invoke({...})` with `repo_url`, `pdf_path`, `rubric_dimensions`. State is returned with aggregated `evidences`.

## Parallelism tests (TRP1 Challenge)

Contract tests for graph structure (fan-out, fan-in, evidence merge) can be run via pytest:

```bash
uv run pytest tests/contract/test_detective_graph_parallelism.py -v
```

## Testing (TDD)

The project uses **Test-Driven Development**: write tests from contracts/specs first, then implement (Red–Green–Refactor). Test layout:

- **Unit** (`tests/unit/`): state models, aggregator, detective nodes with mock state.
- **Contract** (`tests/contract/`): graph topology and evidence merge from detective-graph contract.
- **Integration** (`tests/integration/`): full graph invoke with minimal state.

Run all tests:

```bash
uv sync   # installs pytest via dev-dependencies
uv run pytest tests/ -v
```

See `specs/002-phase1-production-env/docs-testing.md` for the full TDD guide.

## Deliverables

- **Interim report**: `reports/interim_report.pdf` (placeholder for interim submission).
- Final report and audit outputs will be written under `reports/` and `audit/` in later phases.
