# Detective graph contract (Phase 1–2 interim)

**Scope:** START → Detectives (parallel) → EvidenceAggregator → END. No Judges or Chief Justice.

## Nodes

| Node | Input from state | Writes to state | Notes |
|------|------------------|-----------------|--------|
| RepoInvestigator | repo_url, rubric_dimensions | evidences (reducer: ior) | Filters dimensions by target_artifact=github_repo; calls repo_tools |
| DocAnalyst | pdf_path, rubric_dimensions | evidences (reducer: ior) | Filters by target_artifact=pdf_report; calls doc_tools |
| VisionInspector | pdf_path, rubric_dimensions | evidences (reducer: ior) | Filters by target_artifact=pdf_images; calls doc_tools (extract_images) + optional vision |
| EvidenceAggregator | evidences | evidences (optional normalize/merge) | Fan-in; may re-key or merge lists per dimension |

## Edges

- **START → RepoInvestigator:** entrypoint.
- **START → DocAnalyst:** entrypoint (parallel).
- **START → VisionInspector:** entrypoint (parallel).
- **RepoInvestigator → EvidenceAggregator:** after node completes.
- **DocAnalyst → EvidenceAggregator:** after node completes.
- **VisionInspector → EvidenceAggregator:** after node completes.
- **EvidenceAggregator → END:** terminal.

All three detectives run in parallel; EvidenceAggregator runs once after all complete (LangGraph semantics: multiple edges into one node = sync when all predecessors done).

## Conditional edges (optional for interim)

- On clone failure or critical tool error: may route to EvidenceAggregator with partial evidences and error in state (or skip conditional and always proceed to EvidenceAggregator with whatever evidences exist).

## State schema (relevant keys)

- **Input:** repo_url, pdf_path, rubric_dimensions (loaded at graph build or entry).
- **Output:** evidences (Dict[str, List[Evidence]]) populated by detectives and aggregator.
- opinions, final_report: present in TypedDict but unused; may be empty.

## Invariant

- Detectives do not opinionate; they only produce Evidence (goal, found, content, location, rationale, confidence). No scores or judicial fields in detective output.
