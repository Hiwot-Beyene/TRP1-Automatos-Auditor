# Quickstart: Automaton Auditor (Phase 1–2 detective graph)

**Branch**: `002-phase1-production-env`

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) installed
- Optional: LangSmith account and API key for tracing

## Setup

1. Clone the repo and switch to branch `002-phase1-production-env`.
2. From repo root:
   ```bash
   uv sync
   ```
3. Copy env template and set variables:
   ```bash
   cp .env.example .env
   # Edit .env: set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY (or provider keys) for LangSmith
   ```

## Run detective graph (interim)

- **Input:** Repository URL and path to PDF report (e.g. interim report).
- **Execution:** Run the graph so that RepoInvestigator, DocAnalyst, and VisionInspector execute in parallel, then EvidenceAggregator runs once.
- **Output:** State with `evidences` populated; no Markdown report yet (that is Phase 4).

Example (exact entrypoint TBD by implementation):

```bash
# Example; replace with actual CLI or script
uv run python -m src.graph --repo-url https://github.com/org/repo --pdf-path reports/interim_report.pdf
```

Or from Python:

```python
from src.graph import build_detective_graph
graph = build_detective_graph()
result = graph.invoke({"repo_url": "...", "pdf_path": "...", "rubric_dimensions": [...]})
# result["evidences"] holds aggregated Evidence per dimension
```

## Verify

- LangSmith: Check trace for parallel detective nodes and single EvidenceAggregator.
- State: `evidences` is a dict keyed by dimension (or goal); each value is a list of Evidence objects.

## Deliverables (interim)

- state.py, repo_tools, doc_tools, detectives (RepoInvestigator + DocAnalyst + VisionInspector), graph (detectives + EvidenceAggregator), pyproject.toml, .env.example, README (setup, install, run detective graph vs target repo URL), reports/interim_report.pdf.
