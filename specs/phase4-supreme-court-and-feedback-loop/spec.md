# Phase 4: The Supreme Court & Feedback Loop

**Source**: TRP1 Challenge Week 2 — The Automaton Auditor (Implementation Curriculum)  
**Folder**: `specs/phase4-supreme-court-and-feedback-loop/`

## Objective

Synthesize conflict and operationalize the swarm. ChiefJusticeNode with hardcoded conflict resolution; final output as Markdown file; conditional edges; full deliverables.

## Scope

- **Synthesis engine:** ChiefJusticeNode with hardcoded deterministic Python logic (security override, fact supremacy, functionality weight, dissent when variance > 2, variance re-evaluation). No LLM for synthesis. Output: AuditReport serialized to Markdown (Executive Summary → Criterion Breakdown → Remediation Plan).
- **Report generation:** Markdown file, not console print. Write to state.final_report and to chosen audit dir.
- **Graph complete:** Conditional edges for error handling (Evidence Missing, Node Failure); end-to-end repo URL input to rendered Markdown report.
- **Deliverables:** README (run swarm vs any target repo URL and PDF); reports/ and audit/ structure; optional Dockerfile.

## Branches and commits

| Branch | Commits |
|--------|---------|
| `008-phase4-supreme-court` | 1. Add ChiefJusticeNode with hardcoded conflict resolution and AuditReport → Markdown in src/nodes/justice.py |
| `009-phase4-deliverables` | 1. Add conditional edges for error handling and end-to-end flow in src/graph.py 2. Add README (setup, install, run detective graph / swarm) 3. Add reports/ and audit/ structure; interim_report.pdf and final_report.pdf placeholders |

## Key files

- `src/nodes/justice.py`
- `src/graph.py` (complete)
- `README.md`
- `reports/`, `audit/`

## References

- Master spec: [../spec.md](../spec.md)
- Functional: [../functional-spec.md](../functional-spec.md)
- Technical: [../technical-spec.md](../technical-spec.md)
- Multi-model stack: [../multi-model-stack-spec.md](../multi-model-stack-spec.md)
- Challenge: `TRP1 Challenge Week 2_ The Automaton Auditor.md`
