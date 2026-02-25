# Research: Automaton Auditor Phase 1–2

**Branch**: `002-phase1-production-env` | **Phase 0 output**

## 1. LangGraph parallel fan-out and fan-in

**Decision:** Use LangGraph `StateGraph` with a single parallel fan-out to multiple detective nodes (RepoInvestigator, DocAnalyst, VisionInspector), then one sync node (EvidenceAggregator) to merge evidences using the `evidences` reducer (`operator.ior`).

**Rationale:** Spec and constitution require "Detectives fan-out; sync node (fan-in) before Judges." For interim we stop at EvidenceAggregator. LangGraph supports this via `add_node` for each detective and one aggregator; edges: START → all detectives (parallel), all detectives → EvidenceAggregator → END. Reducers on state prevent overwrites when multiple nodes write to the same key.

**Alternatives considered:** Linear chain (rejected: violates constitution). Manual threading (rejected: StateGraph is the required abstraction).

## 2. State reducers (TypedDict + Annotated)

**Decision:** `evidences: Annotated[Dict[str, List[Evidence]], operator.ior]` and `opinions: Annotated[List[JudicialOpinion], operator.add]` so parallel nodes merge instead of overwrite.

**Rationale:** technical-spec §2.4 and constitution §IV. `operator.ior` merges dicts; `operator.add` concatenates lists. Pydantic models for Evidence, JudicialOpinion; TypedDict for AgentState.

**Alternatives considered:** Single writer (rejected: no parallelism). Custom reducer (rejected: stdlib sufficient).

## 3. Tool contracts and sandboxing

**Decision:** RepoInvestigator: `tempfile.TemporaryDirectory()` for clone; subprocess with timeout and stderr/stdout capture; no `os.system`; URL from state, not user string in shell. DocAnalyst: PDF path from state; chunked ingest; optional RAG-lite. VisionInspector: implement `extract_images_from_pdf`; vision call optional for interim.

**Rationale:** functional-spec §3 and technical-spec §4; constitution security (sandboxed clone, no raw os.system).

**Alternatives considered:** Clone into cwd (rejected: security). Regex for code analysis (rejected: spec requires AST).

## 4. Dependency and observability

**Decision:** uv for install and lockfile; `.env` for `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY` (or provider keys); `.env.example` documents all vars.

**Rationale:** technical-spec §1 and phase1 spec; constitution §V.

**Alternatives considered:** pip (rejected: spec mandates uv). Console-only logging (rejected: LangSmith required for multi-agent debugging).

## 5. Interim graph boundary

**Decision:** Graph ends at EvidenceAggregator. State may include `rubric_dimensions` and `evidences`; `opinions` and `final_report` exist in schema but unused until Phase 3–4.

**Rationale:** functional-spec §9 interim submission: "graph (detectives parallel + EvidenceAggregator; Judges not required yet)."

**Alternatives considered:** Stub judges (rejected: out of scope). Omit EvidenceAggregator (rejected: fan-in is required).
