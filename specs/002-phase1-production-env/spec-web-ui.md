# Web UI & API (Automaton Auditor)

**Scope:** Frontend (Next.js + Tailwind) and backend API for running the detective graph. All graph logic remains as defined in the TRP1 Challenge and detective-graph contract; only the entrypoint and input source change.

## Requirements

1. **Input mode:** User provides **either** a Repo URL **or** a Doc URL (PDF path/URL), not both required. One audit type per run.
2. **Rubric from UI:** Rubric dimensions are supplied via the UI (e.g. paste JSON or structured form), not hardcoded in backend. Backend accepts `rubric_dimensions` in the request body.
3. **Backend:** REST API (FastAPI) that accepts `repo_url`, `pdf_path`, and `rubric_dimensions`; invokes the existing detective graph; returns serialized evidences. No change to state schema, reducers, or detective logic.
4. **Frontend:** Next.js with Tailwind only. Luxury, modern look. Form: choose Repo or Doc, enter URL, provide rubric (paste or form), submit, display results (evidences by dimension).

## API contract

- **POST /api/run**
  - Body: `{ "repo_url"?: string, "pdf_path"?: string, "rubric_dimensions": array }`
  - At least one of `repo_url` or `pdf_path` required; the other may be empty string.
  - `rubric_dimensions`: list of `{ id, name?, target_artifact, forensic_instruction? }` per challenge rubric format.
  - Response: `{ "evidences": { [dimension_id]: [ { goal, found, content, location, rationale, confidence } ] } }` (serialized Evidence).
  - Errors: 4xx/5xx with message.

## UI behavior

- Single page: mode selector (Audit by Repo | Audit by Doc), one URL input, rubric input (JSON textarea or link to default rubric), Run button.
- Results: display evidences grouped by dimension; luxury modern styling (Tailwind only).

## Out of scope

- No change to LangGraph state, detectives, EvidenceAggregator, or reducer semantics.
- No Judges or Chief Justice in this deliverable.
