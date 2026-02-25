# Data Model: Automaton Auditor (Phase 1–2)

**Branch**: `002-phase1-production-env` | **Phase 1 output**

## 1. Detective output (Evidence)

| Field | Type | Validation | Notes |
|-------|------|------------|--------|
| goal | str | non-empty | Forensic goal / dimension id |
| found | bool | — | Artifact exists |
| content | Optional[str] | — | Snippet or extracted content |
| location | str | non-empty | File path or commit hash |
| rationale | str | non-empty | Why this confidence |
| confidence | float | 0 ≤ x ≤ 1 (advisory) | Detective confidence |

**Source:** technical-spec §2.1. Used by all three detectives; aggregated by EvidenceAggregator into state under `evidences` (keyed by dimension or goal).

## 2. Judge output (JudicialOpinion) — Phase 3+

| Field | Type | Validation | Notes |
|-------|------|------------|--------|
| judge | Literal["Prosecutor", "Defense", "TechLead"] | — | Persona |
| criterion_id | str | — | Rubric dimension id |
| score | int | ge=1, le=5 | 1–5 |
| argument | str | — | Reasoning |
| cited_evidence | List[str] | — | Evidence ids or refs |

**Source:** technical-spec §2.2. Not produced in Phase 1–2; schema present for state typing.

## 3. Chief Justice output — Phase 4

**CriterionResult:** dimension_id, dimension_name, final_score (1–5), judge_opinions, dissent_summary (optional, required when variance > 2), remediation.

**AuditReport:** repo_url, executive_summary, overall_score, criteria (List[CriterionResult]), remediation_plan.

**Source:** technical-spec §2.3. Not produced in interim.

## 4. Graph state (AgentState)

| Key | Type | Reducer | Phase 1–2 use |
|-----|------|---------|----------------|
| repo_url | str | — | Input; read by RepoInvestigator |
| pdf_path | str | — | Input; read by DocAnalyst, VisionInspector |
| rubric_dimensions | List[Dict] | — | Loaded from rubric.json; filter by target_artifact for detectives |
| evidences | Dict[str, List[Evidence]] | operator.ior | Written by detectives (keyed); merged by EvidenceAggregator |
| opinions | List[JudicialOpinion] | operator.add | Empty until Phase 3 |
| final_report | AuditReport | — | Empty until Phase 4 |

**Source:** technical-spec §2.4. TypedDict with Annotated reducers for parallel-safe writes.

## 5. State transitions (interim)

- **START → detectives:** State carries repo_url, pdf_path, rubric_dimensions. Each detective reads inputs and writes into `evidences` (reducer merges).
- **detectives → EvidenceAggregator:** Aggregator reads `evidences`, optionally normalizes/keys by dimension; may write back merged structure (same key, reducer.ior).
- **EvidenceAggregator → END:** State contains aggregated evidences; no opinions or final_report.

## 6. Rubric dimension (from rubric.json)

Structure: id, name, target_artifact (e.g. github_repo | pdf_report | pdf_images), forensic_instruction, success_pattern, failure_pattern. Used to dispatch forensic_instruction to the correct detective by target_artifact.
