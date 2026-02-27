# Implementation Plan: Automaton Auditor (TRP1 Week 2)

**Branch**: `011-implementation-judicial-layer-and-synthesis` | **Date**: 2025-02-27  
**Input**: [specs/spec.md](../spec.md), [specs/technical-spec.md](../technical-spec.md), [specs/multi-model-stack-spec.md](../multi-model-stack-spec.md)

**Existing branches (no new branches created):** Phase branches 002–009 per phase specs; **010** (spec / multi-model alignment), **011** (judicial layer + synthesis implementation).

---

## Summary

The Automaton Auditor runs a Digital Courtroom agent graph: parallel detectives (RepoInvestigator, DocAnalyst, VisionInspector) collect evidence; EvidenceAggregator fans in; conditional edges route to a judicial panel (Prosecutor, Defense, TechLead) then Chief Justice for deterministic synthesis. Output is a Markdown audit report. The **multi-model stack** (free-tier only) assigns Groq Llama 3.1 70B to RepoInvestigator optional LLM and all Judges; Google Gemini 1.5 Flash to DocAnalyst and VisionInspector; Chief Justice uses no LLM. Observability via LangSmith.

---

## Technical Context

**Language/Version**: Python 3.10+ (pyproject.toml `requires-python = ">=3.10"`)  
**Primary Dependencies**: LangGraph, LangChain, Pydantic ≥2, pypdf; **LLM**: langchain-groq (Groq), langchain-google-genai (Gemini); langchain-openai optional override only.  
**Storage**: N/A (state in memory; rubric.json, .env; audit/reports written to filesystem)  
**Testing**: pytest (unit, contract, integration); uv run pytest tests/ -v  
**Target Platform**: Linux/macOS; CLI `uv run python scripts/run_audit.py <repo_url> [pdf_path]`; optional FastAPI + Next.js frontend  
**Project Type**: CLI / agent graph (LangGraph StateGraph); optional web API for UI  
**Performance Goals**: Sandbox clone timeout and retry per repo_tools; free-tier rate limits (Groq 30 RPM, Gemini ~10 RPM) respected by design  
**Constraints**: Free-tier APIs only for default stack; no secrets in repo; .env.example documents all keys  
**Scale/Scope**: Single-operator runs; 10 rubric dimensions; one repo + one PDF per run

---

## Multi-Model Stack Integration

From [specs/multi-model-stack-spec.md](../multi-model-stack-spec.md):

| Node(s) | Model / Service | Env | Contract |
|---------|-----------------|-----|----------|
| RepoInvestigator (optional LLM) | Groq — Llama 3.1 70B | GROQ_API_KEY | Tool-only when unset; when set, LLM for summary/interpretation MUST use Groq |
| Prosecutor, Defense, TechLead | Groq — Llama 3.1 70B | GROQ_API_KEY | `.with_structured_output(JudicialOpinion)`; placeholder when unset |
| DocAnalyst | Google Gemini 1.5 Flash | GOOGLE_API_KEY | RAG-lite/theoretical depth; local fallback when unset |
| VisionInspector | Google Gemini 1.5 Flash (vision) | GOOGLE_API_KEY | Image input from extract_images_from_pdf; required for deliverable |
| Chief Justice | No LLM | — | Hardcoded rules only |
| Observability | LangSmith | LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY | Traces for full graph |

**Dependencies:** langchain-groq, langchain-google-genai (or equivalent); default stack MUST NOT require OpenAI.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|--------|
| I. Rubric is Constitution | PASS | rubric.json loaded at runtime; forensic_instruction, synthesis_rules drive behavior |
| II. Forensic vs Judicial Separation | PASS | Detectives emit Evidence only; Judges emit JudicialOpinion; Chief Justice applies synthesis rules |
| III. Dialectical Bench | PASS | Three personas (Prosecutor, Defense, TechLead); Chief Justice deterministic |
| IV. Typed State and Reducers | PASS | AgentState TypedDict; operator.add (opinions), operator.ior (evidences); JudicialOpinion schema |
| V. Production-Grade Infrastructure | PASS | StateGraph, uv, .env, LangSmith; sandboxed clone |
| VI. Phase-Based Implementation | PASS | Phases 1–4 per curriculum; branches 002–009; 010/011 already in use |

No violations. Complexity Tracking table not required.

---

## Project Structure

### Documentation (this feature)

```text
specs/
├── spec.md
├── technical-spec.md
├── multi-model-stack-spec.md
├── phase1-production-environment/spec.md
├── phase2-detective-layer/spec.md
├── phase3-judicial-layer/spec.md
├── phase4-supreme-court-and-feedback-loop/spec.md
└── 011-implementation-judicial-layer-and-synthesis/
    ├── plan.md              # This file
    ├── research.md          # Phase 0 (if generated)
    ├── data-model.md        # Phase 1 (if generated)
    ├── quickstart.md        # Phase 1 (if generated)
    ├── contracts/           # Phase 1 (if generated)
    └── tasks.md             # Phase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── state.py                 # Evidence, JudicialOpinion, CriterionResult, AuditReport, AgentState (reducers)
├── graph.py                 # StateGraph: detectives → evidence_aggregator → conditional → judges → chief_justice → END
├── api.py                   # FastAPI (optional)
├── tools/
│   ├── repo_tools.py        # sandboxed_clone, extract_git_history, analyze_graph_structure; RepoCloneError
│   └── doc_tools.py         # ingest_pdf, search_theoretical_depth, extract_images_from_pdf
└── nodes/
    ├── detectives.py        # RepoInvestigatorNode, DocAnalystNode, VisionInspectorNode
    ├── aggregator.py        # EvidenceAggregatorNode
    ├── judges.py            # ProsecutorNode, DefenseNode, TechLeadNode, JudicialPanelNode (Groq + structured output)
    └── justice.py          # ChiefJusticeNode (no LLM; AuditReport → Markdown)

scripts/
└── run_audit.py             # CLI: uv run python scripts/run_audit.py <repo_url> [pdf_path]

tests/
├── unit/
├── contract/
└── integration/

pyproject.toml
uv.lock
.env.example
rubric.json
README.md
reports/
audit/
```

**Structure Decision**: Single Python package under `src/`; nodes and tools are the main extension points. Optional frontend in `frontend/` and API in `src/api.py` are out of scope for this plan’s deliverables.

---

## Contracts

- **State schema**: [technical-spec.md §2](technical-spec.md) — Evidence, JudicialOpinion, CriterionResult, AuditReport, AgentState with reducers. No external API contract beyond state typing.
- **Tool contracts**: [technical-spec.md §4](technical-spec.md) — RepoInvestigator (sandboxed clone, git/AST); DocAnalyst (ingest_pdf, RAG-lite, Gemini); VisionInspector (extract_images_from_pdf, Gemini vision).
- **Graph topology**: START → [repo_investigator || doc_analyst || vision_inspector] → evidence_aggregator → conditional(proceed → judicial_panel → chief_justice → END | skip → END).
- **Env contract**: .env.example and README MUST document GROQ_API_KEY, GOOGLE_API_KEY, LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY; default stack free-tier (Groq + Gemini + LangSmith).

If project exposes HTTP API or CLI as a formal contract, document in `specs/011-implementation-judicial-layer-and-synthesis/contracts/` (Phase 1). Current scope treats state and tools as the primary contracts.

---

## Phases 1–4 and Branches 010/011

| Phase | Spec folder | Branch(es) | Scope |
|-------|-------------|------------|--------|
| Phase 1 | phase1-production-environment | 002-phase1-production-env | State (Pydantic), pyproject.toml, .env.example (GROQ, GOOGLE, LANGCHAIN_*) |
| Phase 2 | phase2-detective-layer | 003, 004, 005 | repo_tools, doc_tools, detective nodes (Repo, Doc, Vision) |
| Phase 3 | phase3-judicial-layer | 006, 007 | rubric.json, judges (Groq, structured output), graph wiring |
| Phase 4 | phase4-supreme-court-and-feedback-loop | 008, 009 | ChiefJusticeNode, conditional edges, README, reports/audit/ |
| — | Existing | **010** | Spec / multi-model stack alignment (no new branch) |
| — | Existing | **011** | Judicial layer + synthesis implementation (current branch) |

**Merge order**: Phase 1 → Phase 2 (003→004→005) → Phase 3 (006→007) → Phase 4 (008→009). Branches 010 and 011 are already present; this plan does not create new branches or new files beyond updating this plan artifact.

---

## Deliverables Checklist (from specs)

- [ ] src/state.py — Pydantic state, reducers  
- [ ] src/tools/repo_tools.py — Sandboxed clone, git, AST  
- [ ] src/tools/doc_tools.py — PDF ingest, RAG-lite, Gemini for DocAnalyst; extract_images + Gemini vision for VisionInspector  
- [ ] src/nodes/detectives.py — RepoInvestigator (tool-only or Groq when GROQ_API_KEY), DocAnalyst (Gemini when GOOGLE_API_KEY), VisionInspector (Gemini vision when GOOGLE_API_KEY)  
- [ ] src/nodes/judges.py — Prosecutor, Defense, TechLead via Groq Llama 3.1 70B, .with_structured_output(JudicialOpinion)  
- [ ] src/nodes/justice.py — ChiefJusticeNode deterministic, AuditReport → Markdown  
- [ ] src/graph.py — Full topology with conditional edges  
- [ ] pyproject.toml — langchain-groq, langchain-google-genai; uv.lock  
- [ ] .env.example — GROQ_API_KEY, GOOGLE_API_KEY, LANGCHAIN_*  
- [ ] README — Default stack (Groq + Gemini + LangSmith), setup, run command  
- [ ] rubric.json, reports/, audit/

---

**Next**: Run `/speckit.tasks` to produce tasks.md from this plan and specs. No new branches or files created by this command; plan only.
