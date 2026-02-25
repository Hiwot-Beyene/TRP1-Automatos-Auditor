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

## Run the detective graph

**Interactive run (prompts for Repo URL and doc URL):**

```bash
uv run python -m src
```

You will be asked:
- **Enter Repo URL:** e.g. `https://github.com/owner/target-repo`
- **Enter doc URL:** path or URL to the PDF report (or leave blank to skip)

The graph then runs and prints a summary of evidences by dimension.

---

**Programmatic run:** invoke the graph with a target repo URL (and optionally a PDF report path and rubric dimensions). State is returned with aggregated `evidences`.

```bash
uv run python -c "
from src.graph import build_detective_graph

graph = build_detective_graph()
state = graph.invoke({
    \"repo_url\": \"https://github.com/owner/target-repo\",
    \"pdf_path\": \"/path/to/report.pdf\",   # or \"\" to skip PDF
    \"rubric_dimensions\": [                  # or load from rubric.json
        {\"id\": \"git_forensic_analysis\", \"name\": \"Git history\", \"target_artifact\": \"github_repo\"},
        {\"id\": \"graph_orchestration\", \"name\": \"Graph\", \"target_artifact\": \"github_repo\"},
    ],
})
print(\"Evidences:\", list(state.get(\"evidences\", {}).keys()))
"
```

Or from your own script:

```python
from src.graph import build_detective_graph

graph = build_detective_graph()
state = graph.invoke({
    "repo_url": "https://github.com/owner/target-repo",
    "pdf_path": "",
    "rubric_dimensions": [...],
})
# state["evidences"] — aggregated by dimension after all detectives + EvidenceAggregator
```

## Web UI

A Next.js frontend (Tailwind) lets you run audits by **Repo URL** or **Doc URL** and supply the rubric as JSON in the UI.

1. **Start the API** (from repo root):

```bash
uv run uvicorn src.api:app --reload --port 8000
```

2. **Start the frontend** (in another terminal):

```bash
cd frontend && npm install && npm run dev
```

3. Open **http://localhost:3000**. Choose **Repo URL** or **Doc URL**, enter the URL, paste or edit the rubric JSON (or use "Load default"), then click **Run audit**. Results appear as evidence by dimension.

Optional: in `frontend/.env.local` set `NEXT_PUBLIC_API_URL=http://localhost:8000` if the API runs on a different host/port.

## Parallelism tests (TRP1 Challenge)

Contract tests verify detective graph fan-out/fan-in and evidence merge per the challenge doc:

```bash
uv sync
uv run pytest tests/contract/test_detective_graph_parallelism.py -v
```

Tests assert: START fans out to all three detectives; all three feed into EvidenceAggregator; EvidenceAggregator → END; and invoking with rubric for repo/doc/vision yields evidences merged from all three (reducer `operator.ior`).

## Deliverables

- **Interim report**: `reports/interim_report.pdf` (placeholder for interim submission).
- Final report and audit outputs will be written under `reports/` and `audit/` in later phases.
