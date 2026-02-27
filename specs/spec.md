# Master Specification: Automaton Auditor (TRP1 Week 2)

**Created**: 2025-02-25  
**Status**: Draft  
**Source**: TRP1 Challenge Week 2_ The Automaton Auditor.md

**Specs folder structure (phases from challenge document only):**

- **[phase1-production-environment/](phase1-production-environment/spec.md)** — The Production Environment (Infrastructure)
- **[phase2-detective-layer/](phase2-detective-layer/spec.md)** — Advanced Tool Engineering (The Detective Layer)
- **[phase3-judicial-layer/](phase3-judicial-layer/spec.md)** — Orchestrating the Bench (The Judicial Layer)
- **[phase4-supreme-court-and-feedback-loop/](phase4-supreme-court-and-feedback-loop/spec.md)** — The Supreme Court & Feedback Loop

**Related specs (at specs root):**

- **[functional-spec.md](functional-spec.md)** — *What* the system does: inputs/outputs, Protocol A (Forensic Evidence), Protocol B (Judicial Sentencing), synthesis rules, report structure, Tenx rubric.
- **[technical-spec.md](technical-spec.md)** — *How* it is built: state schema, file layout, tool contracts, graph topology, rubric JSON, implementation phases, security.
- **[multi-model-stack-spec.md](multi-model-stack-spec.md)** — *Which* model powers which node: Groq (RepoInvestigator + Judges), Gemini (DocAnalyst + VisionInspector), LangSmith (observability). Free-tier only; use for speckit.analyse and TDD.

## User Scenarios & Testing

### User Story 1 - Run Auditor on Target Repo and PDF (P1)

Operator provides a GitHub repository URL and a PDF report path. The system runs the Digital Courtroom: Detectives collect evidence, Judges deliberate in parallel per rubric criterion, Chief Justice synthesizes a verdict. Output is a Markdown audit report.

**Acceptance:** Given valid repo URL and PDF, graph produces state with aggregated evidences, opinions per criterion, and serialized AuditReport. Invalid repo URL yields safe failure. Each rubric dimension receives three JudicialOpinion objects (Prosecutor, Defense, TechLead).

### User Story 2 - Self-Audit and Peer Audit Deliverables (P2)

Operator runs agent against own repo and peer repo; reports go to `audit/report_onself_generated/`, `audit/report_onpeer_generated/`; peer's report on this repo to `audit/report_bypeer_received/`.

### User Story 3 - Observability and Reproducibility (P3)

LangSmith tracing; .env.example documents keys; uv sync installs and runs graph.

## Folder Structure & File Paths

**Source:** src/state.py, src/tools/repo_tools.py, src/tools/doc_tools.py, src/nodes/detectives.py, src/nodes/judges.py, src/nodes/justice.py, src/graph.py  
**Config:** pyproject.toml, .env.example, rubric.json  
**Documentation:** README.md, reports/interim_report.pdf, reports/final_report.pdf  
**Audit output:** audit/report_onself_generated/, audit/report_onpeer_generated/, audit/report_bypeer_received/  
**Optional:** tests/, Dockerfile

(Full detail in [technical-spec.md](technical-spec.md).)

## Feature Branches & Git History (Phase-Based)

Branches and commits are defined by the **four implementation phases** in the challenge document. Each phase has its own spec folder; branch/commit detail is in the phase spec.

| Phase | Spec folder | Branch(es) |
|-------|-------------|------------|
| Phase 1: Production Environment | [phase1-production-environment/](phase1-production-environment/spec.md) | 002-phase1-production-env |
| Phase 2: Detective Layer | [phase2-detective-layer/](phase2-detective-layer/spec.md) | 003, 004, 005 |
| Phase 3: Judicial Layer | [phase3-judicial-layer/](phase3-judicial-layer/spec.md) | 006, 007 |
| Phase 4: Supreme Court & Feedback Loop | [phase4-supreme-court-and-feedback-loop/](phase4-supreme-court-and-feedback-loop/spec.md) | 008, 009 |

**Merge order:** Phase 1 → Phase 2 (003→004→005) → Phase 3 (006→007) → Phase 4 (008→009). Atomic commit messages are listed in each phase's spec.md.

## Requirements Summary

FR-001–FR-012 and key entities are in [functional-spec.md](functional-spec.md) and [technical-spec.md](technical-spec.md). Success criteria: operator can run auditor and get Markdown report; all 10 dimensions get three opinions + one CriterionResult; reducers prevent overwrites; report has remediation and dissent when variance > 2; setup from README and .env.example.

## Cursor Commands

- **/speckit.plan** — Input: this spec (`specs/spec.md`) and `specs/technical-spec.md`. Output: plan with project structure and contracts.
- **/speckit.tasks** — Input: plan.md, this spec, technical-spec. Output: tasks grouped by phase/branch (see phase folders).
- **/speckit.implement** — Create phase-based branches 002–009 per phase specs; apply atomic commits per branch; merge in phase order; produce all source, config, audit dirs, README, reports.

## Rubric-to-Project Mapping

| Rubric dimension | Primary file(s) | Phase |
|------------------|----------------|------|
| git_forensic_analysis, state_management_rigor, safe_tool_engineering | repo_tools.py, state.py, detectives.py | 1, 2 |
| graph_orchestration, structured_output_enforcement, judicial_nuance | graph.py, judges.py, rubric.json | 3 |
| chief_justice_synthesis | justice.py | 4 |
| theoretical_depth, report_accuracy, swarm_visual | doc_tools.py, detectives.py, reports | 2, 4 |

## Assumptions

Python 3.10+; uv; LangSmith; rubric.json 10 dimensions. **Multi-model stack:** free-tier only — Groq (Llama 3.1 70B) for RepoInvestigator optional LLM and Judges; Google Gemini (1.5 Flash) for DocAnalyst and VisionInspector; LangSmith for observability. VisionInspector implementation and execution required for final deliverable. Peer-gradable repo. Full behavior in [functional-spec.md](functional-spec.md); full technical detail in [technical-spec.md](technical-spec.md); model assignment in [multi-model-stack-spec.md](multi-model-stack-spec.md).
