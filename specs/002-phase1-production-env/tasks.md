# Tasks: Automaton Auditor — Interim Submission

**Input**: plan.md, specs/spec.md, specs/technical-spec.md, phase1/phase2/phase3 (partial) specs  
**Scope**: Phase 1 (002), Phase 2 (003, 004, 005), Phase 3 partial (007: detectives + EvidenceAggregator only). README and reports/interim_report.pdf included.

**Format**: `[ID] [P?] [Branch] Description`

- **[P]**: Can run in parallel within same branch (different files, no dependencies)
- **[Branch]**: 002 | 003 | 004 | 005 | 007

---

## Branch 002-phase1-production-env

**Purpose**: Typed state, uv, .env, observability, README, reports dir and interim report placeholder.

- [X] T001 [002] Add Pydantic models in `src/state.py`: Evidence, JudicialOpinion, CriterionResult, AuditReport (fields per data-model.md and technical-spec §2).
- [X] T002 [002] Add AgentState TypedDict in `src/state.py` with reducers: evidences `Annotated[Dict[str, List[Evidence]], operator.ior]`, opinions `Annotated[List[JudicialOpinion], operator.add]`; repo_url, pdf_path, rubric_dimensions, final_report.
- [X] T003 [002] Add `pyproject.toml` with Python 3.10+, LangGraph, LangChain, Pydantic; configure uv and generate lockfile.
- [X] T004 [002] Add `.env.example` documenting LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY (and any other API keys for PDF/vision); no secrets in repo.
- [ ] T005 [002] Add README.md: project description, setup (uv sync, cp .env.example .env), install, how to run detective graph vs target repo URL, reference to reports/interim_report.pdf.
- [ ] T006 [002] Create `reports/` directory and add placeholder or generated `reports/interim_report.pdf` for interim deliverable.

---

## Branch 003-phase2-repo-tools

**Purpose**: Sandboxed clone, git history, AST-based graph/structure analysis. Depends on 002 (state, deps).

- [ ] T007 [003] Implement sandboxed git clone in `src/tools/repo_tools.py`: tempfile.TemporaryDirectory(), subprocess with timeout and stderr/stdout capture, no os.system; sanitize repo_url; return clone path or raise/handle errors per contract.
- [ ] T008 [003] Implement `extract_git_history(path)` in `src/tools/repo_tools.py`: run git log --oneline --reverse; return list of commit/message/timestamp; handle non-git or missing path.
- [ ] T009 [003] Implement `analyze_graph_structure(path)` in `src/tools/repo_tools.py`: use Python ast (or tree-sitter) to detect StateGraph usage, add_edge/add_conditional_edges, node names; no regex for code structure; return structured description per contract.

---

## Branch 004-phase2-doc-tools

**Purpose**: PDF ingest, RAG-lite, cross-reference. Depends on 002.

- [ ] T010 [004] Implement `ingest_pdf(pdf_path: str)` in `src/tools/doc_tools.py`: parse PDF, chunk text for RAG-lite; return chunked representation (e.g. list of chunks + optional metadata); handle missing/unreadable file.
- [ ] T011 [004] Implement chunked query / RAG-lite in `src/tools/doc_tools.py`: search chunks for terms (e.g. theoretical_depth keywords); return matching content or Evidence-ready structure.
- [ ] T012 [004] Implement cross_reference in `src/tools/doc_tools.py`: take file paths extracted from report and repo evidence; return verified_paths vs hallucinated_paths per contract.

---

## Branch 005-phase2-detective-nodes

**Purpose**: RepoInvestigator, DocAnalyst, VisionInspector nodes; EvidenceAggregator. Depends on 002, 003, 004.

- [ ] T013 [005] Add RepoInvestigator node in `src/nodes/detectives.py`: read repo_url, rubric_dimensions (filter target_artifact=github_repo); call repo_tools (clone, extract_git_history, analyze_graph_structure); emit Evidence list into state.evidences via reducer.
- [ ] T014 [005] Add DocAnalyst node in `src/nodes/detectives.py`: read pdf_path, rubric_dimensions (target_artifact=pdf_report); call doc_tools (ingest_pdf, query, cross_reference); emit Evidence into state.evidences.
- [ ] T015 [005] Add VisionInspector node in `src/nodes/detectives.py`: read pdf_path, rubric_dimensions (target_artifact=pdf_images); call extract_images_from_pdf (implement in doc_tools or detectives); optional vision model call for swarm_visual; implementation required, execution optional for interim; emit Evidence into state.evidences.
- [ ] T016 [005] Implement `extract_images_from_pdf(pdf_path)` (in `src/tools/doc_tools.py` or `src/nodes/detectives.py`): return list of image bytes/paths; required for VisionInspector contract.
- [ ] T017 [005] Add EvidenceAggregator in `src/nodes/aggregator.py`: input state.evidences from all detectives; optionally normalize/merge by dimension; write back to state.evidences (reducer.ior); fan-in only, no opinions.

---

## Branch 007-phase3-graph-orchestration (interim: detectives + EvidenceAggregator only)

**Purpose**: StateGraph with detectives in parallel and EvidenceAggregator; no Judges or Chief Justice. Depends on 002, 005 (003/004 via 005).

- [ ] T018 [007] Wire graph in `src/graph.py`: build StateGraph with nodes RepoInvestigator, DocAnalyst, VisionInspector, EvidenceAggregator; START → all three detectives (parallel), all detectives → EvidenceAggregator → END; use LangGraph semantics so EvidenceAggregator runs after all detectives complete.
- [ ] T019 [007] Add graph entrypoint: invoke with repo_url, pdf_path, rubric_dimensions (load rubric.json if present or pass minimal dimensions); return state with populated evidences.
- [ ] T020 [007] Ensure rubric.json exists and is loadable (minimal 10-dimension structure with id, name, target_artifact, forensic_instruction) for detective dispatch; optional stub acceptable for interim if 006 not merged.

---

## Dependencies & execution order

| Branch | Depends on | Merge order |
|--------|------------|-------------|
| 002 | — | First |
| 003 | 002 | After 002 |
| 004 | 002 | After 002 |
| 005 | 002, 003, 004 | After 003 and 004 |
| 007 | 002, 005 | After 005 |

**Checkpoints**

- After 002: State, uv, .env.example, README, reports/interim_report.pdf in place; no graph yet.
- After 003/004: repo_tools and doc_tools implementable and testable independently.
- After 005: All detective nodes and EvidenceAggregator exist; can be unit-tested with mock state.
- After 007: Full detective graph runnable: `graph.invoke({"repo_url": "...", "pdf_path": "...", "rubric_dimensions": [...]})` → state with aggregated evidences.

---

## Interim deliverable checklist

- [X] state.py (Evidence, AgentState, reducers)
- [X] pyproject.toml + uv lock
- [X] .env.example
- [ ] src/tools/repo_tools.py (clone, extract_git_history, analyze_graph_structure)
- [ ] src/tools/doc_tools.py (ingest_pdf, RAG-lite, cross_reference, extract_images_from_pdf)
- [ ] src/nodes/detectives.py (RepoInvestigator, DocAnalyst, VisionInspector)
- [ ] src/nodes/aggregator.py (EvidenceAggregator)
- [ ] src/graph.py (detectives parallel → EvidenceAggregator → END)
- [ ] README (setup, install, run detective graph vs target repo URL)
- [ ] reports/interim_report.pdf
