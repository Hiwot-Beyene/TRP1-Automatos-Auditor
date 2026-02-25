# Implementation Plan: Automaton Auditor (Phase 1–2, Detective Graph)

**Branch**: `002-phase1-production-env` | **Date**: 2025-02-25 | **Spec**: [specs/spec.md](../spec.md), [specs/technical-spec.md](../technical-spec.md)
**Input**: Feature specification from `specs/spec.md`, `specs/technical-spec.md`, `specs/phase1-production-environment/spec.md`, `specs/phase2-detective-layer/spec.md`

**Scope (interim submission):** Phase 1 (Production Environment) + Phase 2 (Detective Layer); graph = Detectives (parallel) → EvidenceAggregator only. Judges and Chief Justice are out of scope until Phase 3–4.

## Summary

Establish a typed, observable runtime and forensic detective layer for the Automaton Auditor. Deliver: Pydantic state (AgentState, Evidence, reducers), uv-managed deps, LangSmith, repo_tools (sandboxed clone, git history, AST), doc_tools (PDF ingest, RAG-lite), VisionInspector stub, detective nodes (RepoInvestigator, DocAnalyst, VisionInspector), and a LangGraph with fan-out to detectives and fan-in at EvidenceAggregator. Output: aggregated evidences in state; no judicial layer yet.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: LangGraph, LangChain, Pydantic; uv for package management  
**Storage**: N/A (in-memory state; file-based rubric.json, PDF input)  
**Testing**: pytest (optional for interim); contract tests in tests/contract/  
**Target Platform**: Linux/macOS CLI; sandboxed git clone in temp dir  
**Project Type**: cli (orchestrated agent graph)  
**Performance Goals**: Single repo + PDF run in reasonable time; LangSmith traces for debugging  
**Constraints**: No os.system; sandboxed clone only; secrets in .env only; reducers for parallel writes  
**Scale/Scope**: 10 rubric dimensions; 3 detectives; 1 EvidenceAggregator; interim = detective graph only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|--------|
| I. Rubric Is the Constitution | PASS | rubric.json loaded at runtime; detectives use forensic_instruction per dimension |
| II. Forensic vs Judicial Separation | PASS | Detectives produce Evidence only; no opinions/scores in detective layer |
| III. Dialectical Bench | DEFER | Judges/Chief Justice out of scope for interim |
| IV. Typed State and Reducers | PASS | AgentState TypedDict; Evidence BaseModel; operator.ior for evidences, operator.add for opinions |
| V. Production-Grade Infrastructure | PASS | StateGraph, fan-out detectives → EvidenceAggregator; uv, .env, LangSmith |
| VI. Phase-Based Implementation | PASS | Plan scoped to Phase 1–2; branches 002, 003–005 per phase specs |

**Post–Phase 1 design re-check:** All gates still pass. data-model.md and contracts/ align with constitution (typed state, reducers, forensic-only detectives, graph topology). Complexity Tracking table left empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-phase1-production-env/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (tool + graph contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks - not created by plan)
```

### Source Code (repository root)

```text
src/
├── state.py             # AgentState TypedDict, Evidence, JudicialOpinion, CriterionResult, AuditReport, reducers
├── tools/
│   ├── repo_tools.py    # sandboxed clone, extract_git_history, analyze_graph_structure (AST)
│   └── doc_tools.py     # ingest_pdf, RAG-lite, cross-reference
├── nodes/
│   ├── detectives.py    # RepoInvestigator, DocAnalyst, VisionInspector nodes
│   └── aggregator.py    # EvidenceAggregator (fan-in)
└── graph.py             # StateGraph: START → [RepoInvestigator||DocAnalyst||VisionInspector] → EvidenceAggregator → END

tests/
├── contract/            # Tool/graph contract tests
├── integration/
└── unit/

pyproject.toml           # uv, dependencies
.env.example             # LANGCHAIN_TRACING_V2, API keys
rubric.json              # 10 dimensions (phase 3+ use)
README.md
reports/                 # interim_report.pdf, final_report.pdf
audit/                   # report_onself_generated/, report_onpeer_generated/, report_bypeer_received/
```

**Structure Decision**: Single-project layout under repo root. `src/` holds state, tools, nodes, and graph; `tests/` for contract/integration/unit. Config and deliverables at root/reports/audit per technical-spec and functional-spec.

## Complexity Tracking

*(No violations; table empty.)*
