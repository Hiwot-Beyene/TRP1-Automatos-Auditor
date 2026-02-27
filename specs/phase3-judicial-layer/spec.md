# Phase 3: Orchestrating the Bench (The Judicial Layer)

**Source**: TRP1 Challenge Week 2 — The Automaton Auditor (Implementation Curriculum)  
**Folder**: `specs/phase3-judicial-layer/`

## Objective

Force the LLM to adhere to the "Digital Courtroom" protocol without hallucination. Structured output for Judges; graph wiring for Detectives parallel → EvidenceAggregator → Judges parallel.

## Scope

- **Structured output:** Judges use `.with_structured_output(JudicialOpinion)` or `.bind_tools()`; return score (int), reasoning (str), citations (list). On 400 or parse failure, retry with JSON-only invocation. If Judge returns free text, parser error and retry. Judge LLM: **Groq** (configurable model, default llama-3.3-70b-versatile) or **Gemini** when JUDGE_PROVIDER=google or on 429/400 fallback; see [../multi-model-stack-spec.md](../multi-model-stack-spec.md).
- **Graph construction:** Detectives (Repo, Doc, Vision) run in parallel; EvidenceAggregator collects all evidence before Judges; Judges (Prosecutor, Defense, TechLead) run in parallel on same evidence per criterion.
- **Constitution:** System prompts dynamically load Week 2 Rubric; `rubric.json` provided and loaded at runtime.

## Branches and commits

| Branch | Commits |
|--------|---------|
| `006-phase3-judicial-layer` | 1. Add rubric.json and load in graph 2. Add Prosecutor, Defense, TechLead with .with_structured_output(JudicialOpinion) in src/nodes/judges.py |
| `007-phase3-graph-orchestration` | 1. Wire detectives in parallel and EvidenceAggregator in src/graph.py 2. Wire judges in parallel per criterion in src/graph.py |

## Key files

- `src/nodes/judges.py`
- `rubric.json`
- `src/graph.py` (partial: detectives + EvidenceAggregator + judges)

## References

- Master spec: [../spec.md](../spec.md)
- Functional: [../functional-spec.md](../functional-spec.md)
- Technical: [../technical-spec.md](../technical-spec.md)
- Multi-model stack: [../multi-model-stack-spec.md](../multi-model-stack-spec.md)
- Challenge: `TRP1 Challenge Week 2_ The Automaton Auditor.md`
