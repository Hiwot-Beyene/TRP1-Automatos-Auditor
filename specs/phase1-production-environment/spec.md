# Phase 1: The Production Environment (Infrastructure)

**Source**: TRP1 Challenge Week 2 — The Automaton Auditor (Implementation Curriculum)  
**Folder**: `specs/phase1-production-environment/`

## Objective

Establish a typed, observable, and isolated runtime environment. A simple script is insufficient; you need a robust StateGraph-ready foundation.

## Scope

- **State definition (Pydantic):** AgentState using Pydantic models and TypedDict; Evidence, JudicialOpinion, CriterionResult, AuditReport; reducers (`operator.add`, `operator.ior`) so parallel agents do not overwrite data.
- **Environment isolation:** uv package manager; strictly manage dependencies; API keys via `.env` (never hardcoded).
- **Observability:** LangSmith tracing; set `LANGCHAIN_TRACING_V2=true`.
- **Secrets / env:** `.env.example` MUST document: `GROQ_API_KEY`, `GOOGLE_API_KEY`, `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`. No OpenAI key required for default (free-tier) stack. See [../multi-model-stack-spec.md](../multi-model-stack-spec.md).

## Branch and commits

| Branch | Commits |
|--------|---------|
| `002-phase1-production-env` | 1. Add Pydantic state and AgentState in src/state.py (Evidence, JudicialOpinion, CriterionResult, AuditReport, reducers) 2. Add pyproject.toml and uv lock 3. Add .env.example and document LangSmith (LANGCHAIN_TRACING_V2); document GROQ_API_KEY, GOOGLE_API_KEY, LANGCHAIN_API_KEY per multi-model-stack-spec |

## Key files

- `src/state.py`
- `pyproject.toml`
- `.env.example`

## References

- Master spec: [../spec.md](../spec.md)
- Functional: [../functional-spec.md](../functional-spec.md)
- Technical: [../technical-spec.md](../technical-spec.md)
- Multi-model stack: [../multi-model-stack-spec.md](../multi-model-stack-spec.md)
- Challenge: `TRP1 Challenge Week 2_ The Automaton Auditor.md`
