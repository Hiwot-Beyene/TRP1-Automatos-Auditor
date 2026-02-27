# Phase 3: Orchestrating the Bench (The Judicial Layer)

**Source**: TRP1 Challenge Week 2 — The Automaton Auditor (Implementation Curriculum)  
**Folder**: `specs/phase3-judicial-layer/`

## Objective

Force the LLM to adhere to the "Digital Courtroom" protocol without hallucination. Structured output for Judges; graph wiring for Detectives parallel → EvidenceAggregator → Judges parallel.

## Scope

- **Structured output:** Judges use `.with_structured_output(JudicialOpinion)` or `.bind_tools()`; return score (int), reasoning (str), citations (list). On 400 or parse failure, retry with JSON-only invocation. If Judge returns free text, parser error and retry. Judge LLM: **Ollama (Llama 3.2, local default)** or **Groq** or **Gemini** when JUDGE_PROVIDER=groq or google; see [../multi-model-stack-spec.md](../multi-model-stack-spec.md). LLM clients in src/llm.py.
- **Graph construction:** 
  - Detectives: START → entry → [doc_gate, repo_gate, vision_gate] (parallel fan-out). Each gate conditionally routes to its detective (doc_analyst, repo_investigator, vision_inspector) if artifact available, or skips to evidence_aggregator. All detectives converge to evidence_aggregator (fan-in via individual edges).
  - EvidenceAggregator: Collects all evidence from detectives, then conditionally routes: "proceed" → defense, "skip" → END. Also fans out directly to prosecutor and tech_lead (parallel execution).
  - Judges: All three judges (defense, prosecutor, tech_lead) run in parallel on the same aggregated evidence. They converge to chief_justice (fan-in via individual edges).
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
