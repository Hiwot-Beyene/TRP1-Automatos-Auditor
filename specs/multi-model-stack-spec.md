# Multi-Model Stack Specification

**Feature**: Automaton Auditor | **Source**: TRP1 Challenge Week 2, interim report, free-tier research  
**Purpose**: Defines which LLM/vendor powers each node. Specification only; no implementation. Use for speckit.analyse and TDD before implementation.

**Constraint:** All models MAY be free-tier (Groq/Gemini) or **local** (Ollama). Default judge stack uses **Ollama (Llama 3.2)** running locally; no API key required for judges when using Ollama.

---

## 1. Stack Overview

| Responsibility | Node(s) | Model / Service | Provider | Notes |
|----------------|---------|-----------------|----------|-------|
| Forensic / Repo Investigator | RepoInvestigator | Ollama (when JUDGE_PROVIDER=ollama) or Groq Llama 3.1 8B (optional summary) | Local / Groq | Optional LLM |
| Judicial Bench | Prosecutor, Defense, TechLead | **Ollama — Llama 3.2** (default, local) or Groq / Gemini when JUDGE_PROVIDER=groq or google | Ollama (local) / Groq / Google | Default: local, no API key |
| Document + Vision | DocAnalyst, VisionInspector | Google Gemini 1.5 / 2.0 Flash | Google AI Studio | Yes |
| Observability | All nodes | LangSmith | LangChain | Yes (Developer tier) |

No OpenAI required. Default stack: **Ollama (llama3.2)** for Judges and optional RepoInvestigator; Gemini for Doc/Vision; LangSmith for tracing.

---

## 2. Per-Node Requirements (Specification)

### 2.1 RepoInvestigator (Forensic / Code)

- **Primary:** Tool-only behavior (sandboxed clone, git log, AST analysis) as defined in technical-spec and phase2. No LLM required for basic evidence.
- **Optional LLM:** When an LLM is used (e.g. to summarize git history), it MUST use **Ollama** when `JUDGE_PROVIDER=ollama` (same model as judges, e.g. llama3.2), or **Groq** when JUDGE_PROVIDER=groq and `GROQ_API_KEY` is set.
- **Env:** When JUDGE_PROVIDER=ollama: no API key; use `OLLAMA_MODEL`, `OLLAMA_BASE_URL`. Otherwise `GROQ_API_KEY` for Groq. If unset, node MUST still produce Evidence using tools only; MUST NOT fail.
- **Acceptance (TDD):** When JUDGE_PROVIDER=ollama and Ollama is used for RepoInvestigator, client is Ollama. When JUDGE_PROVIDER=groq and GROQ_API_KEY set, client is Groq. When unset, evidence produced without LLM.

### 2.2 DocAnalyst (Document / PDF)

- **LLM:** MUST use **Google Gemini 1.5 Flash** (or 2.0 Flash if available on free tier) for RAG-lite querying, theoretical-depth search, and cross-reference reasoning over ingested PDF chunks.
- **Env:** `GOOGLE_API_KEY` (or provider-specific env documented by LangChain for Google Gemini). If unset, node MAY return evidence with `found=False` and rationale indicating missing API key, or skip LLM and use only local PDF ingestion/chunking.
- **Acceptance (TDD):** When `GOOGLE_API_KEY` is set, DocAnalyst LLM calls MUST use Gemini 1.5 Flash (or specified Flash variant). No OpenAI or other vendor for this node unless overridden by explicit config.

### 2.3 VisionInspector (Diagram / Images)

- **LLM:** MUST use **Google Gemini 1.5 Flash** (vision/multimodal) for image analysis. Input: images extracted from PDF via `extract_images_from_pdf`. Prompt must ask for classification (e.g. StateGraph diagram vs generic flowchart) and flow description.
- **Env:** Same as DocAnalyst — `GOOGLE_API_KEY`. If unset, node MAY return evidence with `found=False` or placeholder rationale; MUST NOT call a paid vision API as default.
- **Acceptance (TDD):** When `GOOGLE_API_KEY` is set, VisionInspector MUST call Gemini with image parts (base64 or API-accepted format). Vision execution is required for final deliverable (not optional).

### 2.4 Prosecutor, Defense, TechLead (Judges)

- **LLM:** Default: **Ollama** with model `OLLAMA_MODEL` (implementation default `llama3.2`), base URL `OLLAMA_BASE_URL` (default `http://localhost:11434`). No API key required. Alternative: **Groq** when `JUDGE_PROVIDER=groq` and `GROQ_API_KEY` set; **Gemini** when `JUDGE_PROVIDER=google` or on Groq 429/400 fallback.
- **Structured output:** MUST use `.with_structured_output(JudicialOpinion)` or equivalent; on 400 or parse failure, retry with JSON-only invocation. Retry on free text; no free-text-only output.
- **Env:** For Ollama: `OLLAMA_MODEL`, `OLLAMA_BASE_URL` (optional). For Groq: `GROQ_API_KEY`, `GROQ_JUDGE_MODEL`. For Gemini fallback: `GOOGLE_API_KEY`, `GOOGLE_GEMINI_MODEL`. `JUDGE_PROVIDER`: `ollama` (default) | `groq` | `google`. If no judge LLM available, implementation MAY return placeholder opinions so graph can complete.
- **Acceptance (TDD):** Judge nodes use Ollama (local Llama 3.2) by default; MAY use Groq or Gemini when JUDGE_PROVIDER set. All three personas use the same model per run. Structured output with JSON fallback.

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
| `JUDGE_PROVIDER` | `ollama` (default) \| `groq` \| `google` | Judges (and RepoInvestigator optional LLM when ollama) |
| `OLLAMA_MODEL` | Optional; default llama3.2 | Judges, RepoInvestigator when JUDGE_PROVIDER=ollama |
| `OLLAMA_BASE_URL` | Optional; default http://localhost:11434 | Ollama client |
| `GROQ_API_KEY` | Groq API (when JUDGE_PROVIDER=groq) | Judges, RepoInvestigator (optional) |
| `GROQ_JUDGE_MODEL` | Optional; default judge model when using Groq | Judges (Groq) |
| `GOOGLE_API_KEY` | Google AI Studio (Gemini) | DocAnalyst, VisionInspector; optional Judges fallback |
| `GOOGLE_GEMINI_MODEL` | Optional; Gemini model | DocAnalyst, VisionInspector; Judges when JUDGE_PROVIDER=google |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith | Observability |
| `LANGCHAIN_API_KEY` | LangSmith API key | Observability |

Optional / fallback: Implementation MAY support `OPENAI_API_KEY` or other keys as overrides; default stack uses Ollama (local) + Gemini (Doc/Vision).

---

## 4. Dependencies (Specification)

- **Ollama:** A LangChain-compatible Ollama chat client (e.g. `langchain-ollama` `ChatOllama`) MUST be used for Judges when `JUDGE_PROVIDER=ollama`. Model default `llama3.2`; run `ollama pull llama3.2` locally.
- **Groq:** When JUDGE_PROVIDER=groq, use `langchain-groq` for Judges and optional RepoInvestigator.
- **Gemini:** A LangChain-compatible Google Gemini client MUST be used for DocAnalyst and VisionInspector. Optional for Judges when JUDGE_PROVIDER=google or on 429/400 fallback.
- **LangSmith:** Already required by technical-spec; no new dependency beyond existing LangChain tracing.

---

## 5. Test-Driven / Acceptance Criteria Summary

| # | Criterion | Pass condition |
|---|-----------|----------------|
| M1 | RepoInvestigator LLM | When JUDGE_PROVIDER=ollama, LLM is Ollama (llama3.2). When groq and GROQ_API_KEY set, LLM is Groq. If both unset/skipped, tool-only evidence. |
| M2 | DocAnalyst LLM | If `GOOGLE_API_KEY` set, LLM is Gemini 1.5 Flash (or specified Flash). |
| M3 | VisionInspector LLM | If `GOOGLE_API_KEY` set, vision call uses Gemini with image input. Vision execution required for final deliverable. |
| M4 | Judge LLM | Prosecutor, Defense, TechLead use **Ollama (llama3.2)** by default; or Groq/Gemini when JUDGE_PROVIDER=groq or google. Structured output JudicialOpinion with JSON fallback on 400. |
| M5 | Chief Justice | No LLM; deterministic rules only. |
| M6 | Env and docs | `.env.example` lists JUDGE_PROVIDER, OLLAMA_*, GROQ_*, GOOGLE_*, LANGCHAIN_*; README states default stack is Ollama (local) + Gemini + LangSmith. |

---

## 6. References

- [technical-spec.md](technical-spec.md) — Tool contracts, graph topology, state schema.
- [functional-spec.md](functional-spec.md) — Detective protocols, judicial personas, synthesis rules.
- [phase2-detective-layer/spec.md](phase2-detective-layer/spec.md) — Detective layer scope.
- [phase3-judicial-layer/spec.md](phase3-judicial-layer/spec.md) — Judicial layer scope.
- TRP1 Challenge Week 2 — The Automaton Auditor.md; reports/interim_report.pdf.
