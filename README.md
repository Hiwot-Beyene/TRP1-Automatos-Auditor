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

Invoke the graph with a target repo URL (and optionally a PDF report path and rubric dimensions). State is returned with aggregated `evidences`.

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

## Deliverables

- **Interim report**: `reports/interim_report.pdf` (placeholder for interim submission).
- Final report and audit outputs will be written under `reports/` and `audit/` in later phases.
