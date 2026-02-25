# Technical Specification: Automaton Auditor

**Feature**: Automaton Auditor | **Source**: TRP1 Challenge Week 2 — The Automaton Auditor  
**Purpose**: Defines *how* the system is built: state schema, file layout, tools, graph topology, and implementation phases. Complements [functional-spec.md](functional-spec.md).

**Note:** This is production-grade infrastructure, not a toy model. A simple script is insufficient; a robust StateGraph is required.

---

## 1. Technical Context

| Item | Choice |
|------|--------|
| Language | Python 3.10+ |
| Package manager | uv (lockfile required; strictly manage dependencies) |
| Orchestration | LangGraph (StateGraph; nodes, parallel execution, conditional_edges) |
| State / output typing | Pydantic BaseModel, TypedDict (no simple Python dicts for AgentState) |
| Observability | LangSmith; set `LANGCHAIN_TRACING_V2=true` (console logs insufficient for multi-agent debugging) |
| Secrets | .env only; .env.example documents all required API keys and env vars; never hardcode secrets |

---

## 2. State Schema (Pydantic / TypedDict)

Exact structures from the challenge document. Use reducers so parallel agents do not overwrite each other's data.

### 2.1 Detective Output

```text
Evidence (BaseModel)
  - goal: str
  - found: bool (whether the artifact exists)
  - content: Optional[str]
  - location: str (file path or commit hash)
  - rationale: str (rationale for confidence on this goal)
  - confidence: float
```

### 2.2 Judge Output

```text
JudicialOpinion (BaseModel)
  - judge: Literal["Prosecutor", "Defense", "TechLead"]
  - criterion_id: str
  - score: int (ge=1, le=5)
  - argument: str (reasoning)
  - cited_evidence: List[str]
```

Judge LLM must return JSON with: score (int), reasoning (str), citations (list). If Judge returns free text, node treats as parser error and forces retry.

### 2.3 Chief Justice Output

```text
CriterionResult (BaseModel)
  - dimension_id: str
  - dimension_name: str
  - final_score: int (ge=1, le=5)
  - judge_opinions: List[JudicialOpinion]
  - dissent_summary: Optional[str] (required when score variance > 2)
  - remediation: str (specific file-level instructions for improvement)

AuditReport (BaseModel)
  - repo_url: str
  - executive_summary: str
  - overall_score: float
  - criteria: List[CriterionResult]
  - remediation_plan: str
```

### 2.4 Graph State

```text
AgentState (TypedDict)
  - repo_url: str
  - pdf_path: str
  - rubric_dimensions: List[Dict]
  - evidences: Annotated[Dict[str, List[Evidence]], operator.ior]   # reducer
  - opinions: Annotated[List[JudicialOpinion], operator.add]       # reducer
  - final_report: AuditReport
```

---

## 3. File and Folder Layout

See phase specs for phase-specific files. Full layout: src/state.py, src/tools/repo_tools.py, src/tools/doc_tools.py, src/nodes/detectives.py, src/nodes/judges.py, src/nodes/justice.py, src/graph.py; pyproject.toml, .env.example, rubric.json; README.md, reports/, audit/.

---

## 4. Tool Contracts

RepoInvestigator: sandboxed clone, extract_git_history(path), analyze_graph_structure(path); AST or tree-sitter; no Regex. DocAnalyst: ingest_pdf(path), RAG-lite, cross-reference. VisionInspector: extract_images_from_pdf(path), vision model; implementation required, execution optional.

---

## 5. Graph Topology

START → [RepoInvestigator || DocAnalyst || VisionInspector] → EvidenceAggregator → [per criterion: Prosecutor || Defense || TechLead] → ChiefJusticeNode → END. Conditional edges for Evidence Missing / Node Failure.

---

## 6–7. Judicial and Chief Justice Requirements

Judges: .with_structured_output(JudicialOpinion) or .bind_tools(); distinct personas; retry on free text. ChiefJustice: hardcoded rules only; AuditReport → Markdown file.

---

## 8. Rubric JSON Structure

rubric_metadata, dimensions (id, name, target_artifact, forensic_instruction, success_pattern, failure_pattern), synthesis_rules. Ten dimensions. Load via json.load().

---

## 9. Implementation Phases (Curriculum)

| Phase | Spec folder |
|-------|-------------|
| Phase 1: Production Environment | [phase1-production-environment/](phase1-production-environment/spec.md) |
| Phase 2: Advanced Tool Engineering (Detective Layer) | [phase2-detective-layer/](phase2-detective-layer/spec.md) |
| Phase 3: Orchestrating the Bench (Judicial Layer) | [phase3-judicial-layer/](phase3-judicial-layer/spec.md) |
| Phase 4: Supreme Court & Feedback Loop | [phase4-supreme-court-and-feedback-loop/](phase4-supreme-court-and-feedback-loop/spec.md) |

**Git branch and commit approach:** See [spec.md](spec.md) and each phase folder for branch names and atomic commits. Merge order: Phase 1 → Phase 2 → Phase 3 → Phase 4.

---

## 10–12. Deliverables, Security, References

Interim/Final per challenge document. Security: no os.system; sandbox; env-only secrets. References: [functional-spec.md](functional-spec.md), [spec.md](spec.md), challenge document.
