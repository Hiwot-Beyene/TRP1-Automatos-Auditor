# Tasks: Automaton Auditor — Multi-Model Stack & Remaining Deliverables

**Input**: plan.md, [specs/spec.md](../../spec.md), [specs/technical-spec.md](../../technical-spec.md), [specs/multi-model-stack-spec.md](../../multi-model-stack-spec.md)  
**Branch**: `011-implementation-judicial-layer-and-synthesis`  
**Focus**: Multi-model implementation (Groq judges + optional RepoInvestigator, Gemini DocAnalyst + VisionInspector), .env.example, missing phase2–4 deliverables.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 = P1 Run auditor repo+PDF, US2 = P2 Audit dirs, US3 = P3 Observability/docs
- File paths are in the task descriptions

---

## Phase 1: Setup (Config & Env)

**Purpose**: Dependencies and env template per multi-model-stack-spec; no new branches.

- [x] T001 Add `langchain-groq` and `langchain-google-genai` to dependencies in pyproject.toml; run `uv lock` and commit uv.lock
- [x] T002 Update .env.example: add `GROQ_API_KEY=` with comment "Groq (Llama 3.1 70B) for Judges and optional RepoInvestigator"; add/uncomment `GOOGLE_API_KEY=` with comment "Gemini for DocAnalyst and VisionInspector"; keep LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY

---

## Phase 2: Foundational — Judges to Groq (Phase 3 / Branch 006–007)

**Purpose**: Judge nodes MUST use Groq Llama 3.1 70B when GROQ_API_KEY set; placeholder when unset. Blocks US1.

- [x] T003 In src/nodes/judges.py replace OpenAI with Groq: use `langchain_groq.ChatGroq`, model `llama-3.1-70b-versatile`, read `GROQ_API_KEY`; when unset return placeholder JudicialOpinion (score=3, argument="GROQ_API_KEY not set; placeholder opinion"); keep .with_structured_output(JudicialOpinion) and retry logic

---

## Phase 3: User Story 1 — Run Auditor on Repo and PDF (P1) — MVP

**Goal**: Operator runs graph with repo URL + PDF; output is Markdown audit report with evidences, three opinions per criterion, Chief Justice synthesis. Default stack = Groq + Gemini + LangSmith.

**Independent Test**: `uv run python scripts/run_audit.py <repo_url> <pdf_path>` produces state with evidences, opinions, and final_report; report written to reports/audit_report.md (or audit dir).

### Multi-model: DocAnalyst (Phase 2 / Branch 004–005)

- [x] T004 [P] [US1] In src/tools/doc_tools.py (or src/nodes/detectives.py) add Gemini 1.5 Flash call for RAG-lite/theoretical depth when GOOGLE_API_KEY set; use langchain_google_genai with model gemini-1.5-flash; when unset keep local keyword search or evidence with found=False per specs/multi-model-stack-spec.md §2.2

### Multi-model: VisionInspector (Phase 2 / Branch 005)

- [x] T005 [P] [US1] In src/nodes/detectives.py VisionInspectorNode when GOOGLE_API_KEY set call Gemini 1.5 Flash (vision) with image parts from extract_images_from_pdf (base64 or API format); prompt for classification (e.g. StateGraph vs flowchart) and flow description; when unset keep placeholder evidence per specs/multi-model-stack-spec.md §2.3

### Multi-model: RepoInvestigator optional LLM (Phase 2 / Branch 003–005)

- [x] T006 [P] [US1] Optional: In src/nodes/detectives.py RepoInvestigatorNode when GROQ_API_KEY set add optional Groq Llama 3.1 70B call to summarize git history or interpret AST results and append to rationale; when unset keep tool-only evidence per specs/multi-model-stack-spec.md §2.1

**Checkpoint**: US1 deliverable: graph uses Groq for Judges, Gemini for DocAnalyst and VisionInspector; .env.example and deps in place; run_audit produces report.

---

## Phase 4: User Story 2 — Self-Audit and Peer Audit Deliverables (P2)

**Goal**: Reports written to audit/report_onself_generated/, audit/report_onpeer_generated/, audit/report_bypeer_received/ per spec.

**Independent Test**: After run, chosen audit dir contains generated Markdown report.

- [ ] T007 [US2] Ensure audit/report_onself_generated, audit/report_onpeer_generated, audit/report_bypeer_received exist; in src/nodes/justice.py or scripts/run_audit.py write AuditReport Markdown to chosen audit dir per run mode (self/peer) per specs/spec.md User Story 2

---

## Phase 5: User Story 3 — Observability and Reproducibility (P3)

**Goal**: LangSmith tracing; .env.example documents all keys; README states default stack; uv sync runs graph.

**Independent Test**: README setup section references GROQ_API_KEY and GOOGLE_API_KEY; .env.example lists all four vars; uv sync and run_audit succeed.

- [ ] T008 [US3] Update README.md: add subsection stating default LLM stack is free-tier (Groq for Judges and optional RepoInvestigator, Gemini 1.5 Flash for DocAnalyst and VisionInspector, LangSmith for tracing); in Setup replace mention of OPENAI/ANTHROPIC with GROQ_API_KEY and GOOGLE_API_KEY per specs/multi-model-stack-spec.md M6

---

## Phase 6: Polish & Cross-Cutting

**Purpose**: Final alignment with phase2–4 and multi-model spec.

- [ ] T009 Verify .env.example contains GROQ_API_KEY, GOOGLE_API_KEY, LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY with purpose comments; README states no OpenAI required for default stack
- [ ] T010 [P] Ensure reports/ and audit/ directory structure exists (reports/audit_report.md, audit/report_onself_generated, etc.); add .gitkeep or placeholder if needed per phase4 spec

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies. Run first.
- **Phase 2 (Judges Groq)**: Depends on Phase 1 (deps in pyproject). Blocks US1.
- **Phase 3 (US1)**: Depends on Phase 1 and Phase 2. T004, T005, T006 can run in parallel after T003.
- **Phase 4 (US2)**: Depends on US1 graph producing final_report; can follow Phase 3.
- **Phase 5 (US3)**: Can run in parallel with Phase 4; only README and env docs.
- **Phase 6 (Polish)**: After Phase 5; verification and dirs.

### User Story Dependencies

- **US1 (P1)**: Requires Phase 1 + Phase 2 + T004, T005 (and optionally T006). Delivers run_audit → Markdown report with correct models.
- **US2 (P2)**: Requires US1; adds audit dir routing.
- **US3 (P3)**: Independent of US1/US2 for content; documents env and default stack.

### Parallel Opportunities

- T004 (DocAnalyst Gemini), T005 (VisionInspector Gemini), T006 (RepoInvestigator Groq) are [P] within Phase 3.
- T008 (README) and T007 (audit dirs) can be done in parallel.
- T009, T010 in Phase 6 can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: T001, T002 (deps + .env.example)
2. Phase 2: T003 (Judges → Groq)
3. Phase 3: T004 (DocAnalyst Gemini), T005 (VisionInspector Gemini); optionally T006 (RepoInvestigator Groq)
4. Validate: run_audit with GROQ_API_KEY and GOOGLE_API_KEY set produces full report

### Incremental Delivery

1. After MVP: T007 (audit dirs) → US2 complete
2. T008 (README default stack) → US3 complete
3. T009, T010 → Polish

---

## Task Summary

| Phase        | Task IDs   | Story | Description |
|-------------|------------|-------|-------------|
| 1 Setup     | T001, T002 | —     | pyproject deps, .env.example |
| 2 Foundational | T003     | —     | Judges → Groq in src/nodes/judges.py |
| 3 US1       | T004–T006  | US1   | DocAnalyst Gemini, VisionInspector Gemini, optional RepoInvestigator Groq |
| 4 US2       | T007       | US2   | Audit dirs in justice/run_audit |
| 5 US3       | T008       | US3   | README default stack |
| 6 Polish    | T009, T010 | —     | Verify env/docs, reports/audit dirs |

**Total tasks**: 10  
**MVP scope**: T001–T005 (optionally T006).  
**Format**: All tasks use `- [ ] [ID] [P?] [Story?] Description` with file paths.
