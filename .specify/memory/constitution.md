# Automaton Auditor Constitution

**Project**: TRP1 Week 2 — The Automaton Auditor (Digital Courtroom)  
**Source**: TRP1 Challenge Week 2_ The Automaton Auditor.md

## Core Principles

### I. The Rubric Is the Constitution

The Week 2 Rubric (`rubric.json`) is the binding law for the agent swarm. Detectives must execute the **forensic_instruction** per dimension; Judges must cite **judicial_logic** when rendering verdicts; the Chief Justice must apply **synthesis_rules**. The rubric is loaded at runtime and can be updated without redeploying agent code. No agent may grade outside or ignore these standards.

### II. Forensic vs Judicial Separation

**Detectives do not opinionate.** They only collect facts and produce structured Evidence (goal, found, content, location, rationale, confidence). Opinions and scores belong to the Judicial layer. Objective evidence (file exists, AST shows fan-out) always overrules judicial interpretation when synthesis rules say so (Rule of Evidence / fact supremacy).

### III. Dialectical Bench (Three Personas)

The Judicial layer is not a single “Grader.” For each rubric criterion, three distinct personas (Prosecutor, Defense, Tech Lead) must analyze the **same evidence** independently and produce one JudicialOpinion each. Synthesis is **deterministic** (hardcoded rules), not an LLM average. The Chief Justice resolves conflict using named rules: security override, fact supremacy, functionality weight, dissent when variance > 2.

### IV. Typed State and Reducers

State is not plain Python dicts. AgentState uses Pydantic models and TypedDict; Evidence and JudicialOpinion are BaseModel. Parallel agents must not overwrite each other: use `operator.add` (opinions) and `operator.ior` (evidences). All Judge output must be validated against the JudicialOpinion schema (e.g. `.with_structured_output()` or `.bind_tools()`); freeform-only response triggers retry or error.

### V. Production-Grade Infrastructure

This is not a toy script. Use a robust StateGraph with clear fan-out/fan-in (Detectives → EvidenceAggregator → Judges → ChiefJustice). Dependencies are managed with **uv** and locked; API keys live in `.env` only (document names in `.env.example`). Observability: **LangSmith** (`LANGCHAIN_TRACING_V2=true`). Git operations run in a sandboxed temporary directory; no raw `os.system()` with unsanitized input.

### VI. Phase-Based Implementation

Implementation follows the four curriculum phases: (1) Production Environment — state, uv, .env, LangSmith; (2) Advanced Tool Engineering — repo_tools, doc_tools, detective nodes; (3) Orchestrating the Bench — Judges, rubric.json, graph wiring; (4) Supreme Court & Feedback Loop — ChiefJusticeNode, conditional edges, report generation, deliverables. Branches and commits align to these phases; merge order respects phase dependencies.

## Constraints

- **Security:** Sandboxed clone only; subprocess with error handling; no secrets in repo.
- **Output:** Final deliverable is a **Markdown file** (AuditReport: Executive Summary → Criterion Breakdown → Remediation Plan), not console print.
- **Scope:** 10 rubric dimensions; each receives forensic evidence (where target_artifact matches), three JudicialOpinions, and one CriterionResult with remediation.

## Governance

- All implementation and PRs must comply with the rubric and this constitution. The challenge document and **specs/** (spec.md, functional-spec.md, technical-spec.md, and the four phase folders: **phase1-production-environment**, **phase2-detective-layer**, **phase3-judicial-layer**, **phase4-supreme-court-and-feedback-loop**) are the authoritative reference for behavior and technical choices.
- Amendments to this constitution require alignment with the TRP1 Challenge Week 2 document and updates to the spec files where relevant.

**Version**: 1.0.0 | **Ratified**: 2025-02-25 | **Source**: TRP1 Challenge Week 2_ The Automaton Auditor.md
