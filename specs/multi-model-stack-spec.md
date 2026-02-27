# Multi-Model Stack Specification

**Feature**: Automaton Auditor | **Source**: TRP1 Challenge Week 2, interim report, free-tier research  
**Purpose**: Defines which LLM/vendor powers each node. Specification only; no implementation. Use for speckit.analyse and TDD before implementation.

**Constraint:** All models use **local Ollama** (no API keys required). Current implementation uses **Ollama (qwen2.5:7b)** for all nodes; fast and efficient local inference.

---

## 1. Stack Overview

| Responsibility | Node(s) | Model / Service | Provider | Notes |
|----------------|---------|-----------------|----------|-------|
| Forensic / Repo Investigator | RepoInvestigator | **Ollama (qwen2.5:7b)** | Local | Optional LLM (can be disabled with AUDITOR_FAST_REPO) |
| Judicial Bench | Prosecutor, Defense, TechLead | **Ollama (qwen2.5:7b)** | Local | Default: local, no API key required |
| Document + Vision | DocAnalyst, VisionInspector | **Ollama (qwen2.5:7b)** | Local | All nodes use same model |
| Observability | All nodes | LangSmith | LangChain | Optional (Developer tier) |

**Current Implementation:** All nodes use **Ollama (qwen2.5:7b)** running locally. No API keys required. LangSmith optional for observability.

---

## 2. Per-Node Requirements (Specification)

### 2.1 RepoInvestigator (Forensic / Code)

- **Primary:** Tool-only behavior (sandboxed clone, git log, AST analysis) as defined in technical-spec and phase2. No LLM required for basic evidence.
- **Optional LLM:** When an LLM is used (e.g. to summarize git history), it uses **Ollama (qwen2.5:7b)**. Can be disabled by setting `AUDITOR_FAST_REPO=true`.
- **Env:** `OLLAMA_MODEL` (default: qwen2.5:7b), `OLLAMA_BASE_URL` (default: http://localhost:11434). No API key required. If `AUDITOR_FAST_REPO` is set, LLM is skipped and tool-only evidence is produced.
- **Acceptance (TDD):** RepoInvestigator uses Ollama (qwen2.5:7b) when LLM is enabled. When `AUDITOR_FAST_REPO` is set, evidence is produced without LLM.

### 2.2 DocAnalyst (Document / PDF)

- **LLM:** Uses **Ollama (qwen2.5:7b)** for RAG-lite querying, theoretical-depth search, and cross-reference reasoning over ingested PDF chunks.
- **Env:** `OLLAMA_MODEL` (default: qwen2.5:7b), `OLLAMA_BASE_URL` (default: http://localhost:11434). No API key required.
- **Acceptance (TDD):** DocAnalyst LLM calls use Ollama (qwen2.5:7b). If Ollama is unavailable, node may return evidence with limited LLM rationale but still produces evidence from PDF ingestion/chunking.

### 2.3 VisionInspector (Diagram / Images)

- **LLM:** Uses **Ollama (qwen2.5:7b)** for image analysis. Input: images extracted from PDF via `extract_images_from_pdf`. Prompt asks for classification (e.g. StateGraph diagram vs generic flowchart) and flow description.
- **Env:** `OLLAMA_MODEL` (default: qwen2.5:7b), `OLLAMA_BASE_URL` (default: http://localhost:11434). No API key required.
- **Acceptance (TDD):** VisionInspector uses Ollama (qwen2.5:7b) with image parts (base64 or API-accepted format). Vision execution is required for final deliverable (not optional).

### 2.4 Prosecutor, Defense, TechLead (Judges)

- **LLM:** Uses **Ollama (qwen2.5:7b)** with model `OLLAMA_MODEL` (implementation default `qwen2.5:7b`), base URL `OLLAMA_BASE_URL` (default `http://localhost:11434`). No API key required.
- **Structured output:** MUST use `.with_structured_output(JudicialOpinion)` or equivalent; on parse failure, retry with JSON-only invocation. Retry on free text; no free-text-only output.
- **Env:** `OLLAMA_MODEL` (default: qwen2.5:7b), `OLLAMA_BASE_URL` (default: http://localhost:11434). If Ollama is unavailable, implementation MAY return placeholder opinions so graph can complete.
- **Acceptance (TDD):** Judge nodes use Ollama (qwen2.5:7b). All three personas use the same model per run. Structured output with JSON fallback.

### 2.5 Chief Justice

- **No LLM.** Hardcoded deterministic logic only (security override, fact supremacy, functionality weight, dissent when variance > 2). No model assignment.

### 2.6 Observability

- **Service:** LangSmith. Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY`.
- **Acceptance:** When env is set, traces MUST appear in LangSmith for full graph (detectives → aggregator → judges → chief_justice). No other observability vendor required.

---

## 3. Environment Variables (Specification)

The following MUST be documented in `.env.example` and in README. No secrets in repo.

| Variable | Purpose | Required for |
|----------|---------|--------------|
| `OLLAMA_MODEL` | Ollama model name; default qwen2.5:7b | All LLM nodes (Judges, RepoInvestigator, DocAnalyst, VisionInspector) |
| `OLLAMA_BASE_URL` | Ollama server URL; default http://localhost:11434 | All LLM nodes |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing; set to 'true' | Observability (optional) |
| `LANGCHAIN_API_KEY` | LangSmith API key | Observability (optional, required if LANGCHAIN_TRACING_V2=true) |
| `AUDITOR_DETECTIVE_WORKERS` | Parallel workers for detectives; default 3 | Performance tuning (optional) |
| `AUDITOR_JUDGE_WORKERS` | Parallel workers for judges; default 3 | Performance tuning (optional) |
| `AUDITOR_MAX_CONCURRENT_RUNS` | Max concurrent graph runs; default 2 | Performance tuning (optional) |
| `AUDITOR_FAST_REPO` | Skip LLM for RepoInvestigator; set to any value | Performance tuning (optional) |

**Note:** All nodes use local Ollama. No API keys required. LangSmith is optional for observability.

---

## 4. Dependencies (Specification)

- **Ollama:** A LangChain-compatible Ollama chat client (`langchain-ollama` `ChatOllama`) is used for all LLM nodes. Model default `qwen2.5:7b`; run `ollama pull qwen2.5:7b` locally before use.
- **LangSmith:** Optional dependency for observability; set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` to enable tracing.

---

## 5. Test-Driven / Acceptance Criteria Summary

| # | Criterion | Pass condition |
|---|-----------|----------------|
| M1 | RepoInvestigator LLM | LLM is Ollama (qwen2.5:7b). If `AUDITOR_FAST_REPO` is set, tool-only evidence (no LLM). |
| M2 | DocAnalyst LLM | LLM is Ollama (qwen2.5:7b) for RAG-lite and theoretical depth queries. |
| M3 | VisionInspector LLM | LLM is Ollama (qwen2.5:7b) with image input. Vision execution required for final deliverable. |
| M4 | Judge LLM | Prosecutor, Defense, TechLead use **Ollama (qwen2.5:7b)**. Structured output JudicialOpinion with JSON fallback on parse failure. |
| M5 | Chief Justice | No LLM; deterministic rules only. |
| M6 | Env and docs | `.env.example` lists OLLAMA_*, LANGCHAIN_*, AUDITOR_*; README states all nodes use Ollama (local, no API keys). |

---

## 6. References

- [technical-spec.md](technical-spec.md) — Tool contracts, graph topology, state schema.
- [functional-spec.md](functional-spec.md) — Detective protocols, judicial personas, synthesis rules.
- [phase2-detective-layer/spec.md](phase2-detective-layer/spec.md) — Detective layer scope.
- [phase3-judicial-layer/spec.md](phase3-judicial-layer/spec.md) — Judicial layer scope.
- TRP1 Challenge Week 2 — The Automaton Auditor.md; reports/interim_report.pdf.
