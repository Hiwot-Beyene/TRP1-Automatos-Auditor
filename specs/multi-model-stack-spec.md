# Multi-Model Stack Specification

**Feature**: Automaton Auditor | **Source**: TRP1 Challenge Week 2, interim report, free-tier research  
**Purpose**: Defines which LLM/vendor powers each node. Specification only; no implementation. Use for speckit.analyse and TDD before implementation.

**Constraint:** All models MUST be usable on **free tiers** (no paid API required). Best-fit per responsibility.

---

## 1. Stack Overview

| Responsibility | Node(s) | Model / Service | Provider | Free tier |
|----------------|---------|-----------------|----------|-----------|
| Forensic / Repo Investigator | RepoInvestigator | Groq — Llama 3.1 8B (optional summary) | Groq | Yes |
| Judicial Bench | Prosecutor, Defense, TechLead | Groq (default model configurable; default llama-3.3-70b-versatile) or Gemini when JUDGE_PROVIDER=google or on 429/400 fallback | Groq / Google | Yes |
| Document + Vision | DocAnalyst, VisionInspector | Google Gemini 1.5 / 2.0 Flash | Google AI Studio | Yes |
| Observability | All nodes | LangSmith | LangChain | Yes (Developer tier) |

No OpenAI (e.g. GPT-4o-mini) is required for the default stack.

---

## 2. Per-Node Requirements (Specification)

### 2.1 RepoInvestigator (Forensic / Code)

- **Primary:** Tool-only behavior (sandboxed clone, git log, AST analysis) as defined in technical-spec and phase2. No LLM required for basic evidence.
- **Optional LLM:** When an LLM is used (e.g. to summarize git history, interpret AST results, or generate rationale text), it MUST use **Groq** (model id configurable; implementation default e.g. Llama 3.1 8B for higher rate limits).
- **Env:** `GROQ_API_KEY`. If unset, node MUST still produce Evidence using tools only; MUST NOT fail. If set and LLM is invoked, MUST use Groq.
- **Acceptance (TDD):** When `GROQ_API_KEY` is set and implementation uses an LLM for RepoInvestigator, the client MUST be Groq. When unset, evidence MUST be produced without calling any LLM.

### 2.2 DocAnalyst (Document / PDF)

- **LLM:** MUST use **Google Gemini 1.5 Flash** (or 2.0 Flash if available on free tier) for RAG-lite querying, theoretical-depth search, and cross-reference reasoning over ingested PDF chunks.
- **Env:** `GOOGLE_API_KEY` (or provider-specific env documented by LangChain for Google Gemini). If unset, node MAY return evidence with `found=False` and rationale indicating missing API key, or skip LLM and use only local PDF ingestion/chunking.
- **Acceptance (TDD):** When `GOOGLE_API_KEY` is set, DocAnalyst LLM calls MUST use Gemini 1.5 Flash (or specified Flash variant). No OpenAI or other vendor for this node unless overridden by explicit config.

### 2.3 VisionInspector (Diagram / Images)

- **LLM:** MUST use **Google Gemini 1.5 Flash** (vision/multimodal) for image analysis. Input: images extracted from PDF via `extract_images_from_pdf`. Prompt must ask for classification (e.g. StateGraph diagram vs generic flowchart) and flow description.
- **Env:** Same as DocAnalyst — `GOOGLE_API_KEY`. If unset, node MAY return evidence with `found=False` or placeholder rationale; MUST NOT call a paid vision API as default.
- **Acceptance (TDD):** When `GOOGLE_API_KEY` is set, VisionInspector MUST call Gemini with image parts (base64 or API-accepted format). Vision execution is required for final deliverable (not optional).

### 2.4 Prosecutor, Defense, TechLead (Judges)

- **LLM:** Primary: **Groq** with configurable model via `GROQ_JUDGE_MODEL` (implementation default `llama-3.3-70b-versatile`). Optional: **Google Gemini** when `JUDGE_PROVIDER=google` or when Groq returns 429 (rate limit) or 400 (e.g. "Failed to call a function"); fallback uses Gemini if `GOOGLE_API_KEY` is set.
- **Structured output:** MUST use `.with_structured_output(JudicialOpinion)` or equivalent; on 400 or parse failure, retry with JSON-only invocation (no structured schema). Retry on free text; no free-text-only output.
- **Env:** `GROQ_API_KEY` for Groq; `GOOGLE_API_KEY` for Gemini fallback. Optional: `GROQ_JUDGE_MODEL`, `JUDGE_PROVIDER` (groq | google), `GOOGLE_GEMINI_MODEL`. If no judge LLM available, implementation MAY return placeholder opinions (e.g. score=3, argument="API key not set") so graph can complete.
- **Acceptance (TDD):** Judge nodes use Groq with configurable model when `GROQ_API_KEY` set; MAY use Gemini when `JUDGE_PROVIDER=google` or on 429/400 fallback. All three personas use the same model per run. Structured output with JSON fallback.

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
| `GROQ_API_KEY` | Groq API (Judges default; RepoInvestigator optional LLM) | Prosecutor, Defense, TechLead (or use Gemini); RepoInvestigator (optional LLM) |
| `GROQ_JUDGE_MODEL` | Optional; default judge model (e.g. llama-3.3-70b-versatile) | Judges when using Groq |
| `JUDGE_PROVIDER` | Optional; `groq` (default) or `google` to use Gemini for judges | Judges |
| `GOOGLE_API_KEY` | Google AI Studio (Gemini) | DocAnalyst, VisionInspector; optional Judges fallback |
| `GOOGLE_GEMINI_MODEL` | Optional; Gemini model (e.g. gemini-2.0-flash) | DocAnalyst, VisionInspector; Judges when JUDGE_PROVIDER=google |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith | Observability |
| `LANGCHAIN_API_KEY` | LangSmith API key | Observability |

Optional / fallback: Implementation MAY support `OPENAI_API_KEY` or other keys as overrides (e.g. for local testing); default stack MUST NOT require them.

---

## 4. Dependencies (Specification)

- **Groq:** A LangChain-compatible Groq chat client (e.g. `langchain-groq` or equivalent) MUST be used for RepoInvestigator (if LLM) and Judges. Package name and version to be chosen at implementation time; spec only requires that Judge and RepoInvestigator LLM calls go to Groq Llama 3.1 70B.
- **Gemini:** A LangChain-compatible Google Gemini client (e.g. `langchain-google-genai` or equivalent) MUST be used for DocAnalyst and VisionInspector. Model MUST be Gemini 1.5 Flash (or 2.0 Flash if on free tier).
- **LangSmith:** Already required by technical-spec; no new dependency beyond existing LangChain tracing.

---

## 5. Test-Driven / Acceptance Criteria Summary

| # | Criterion | Pass condition |
|---|-----------|----------------|
| M1 | RepoInvestigator LLM | If LLM used, provider is Groq; model Llama 3.1 70B. If `GROQ_API_KEY` unset, no LLM call; tool-only evidence. |
| M2 | DocAnalyst LLM | If `GOOGLE_API_KEY` set, LLM is Gemini 1.5 Flash (or specified Flash). |
| M3 | VisionInspector LLM | If `GOOGLE_API_KEY` set, vision call uses Gemini with image input. Vision execution required for final deliverable. |
| M4 | Judge LLM | Prosecutor, Defense, TechLead use Groq (configurable model) or Gemini when JUDGE_PROVIDER=google or on 429/400 fallback. Structured output JudicialOpinion with JSON fallback on 400. |
| M5 | Chief Justice | No LLM; deterministic rules only. |
| M6 | Env and docs | `.env.example` lists GROQ_API_KEY, GOOGLE_API_KEY, LANGCHAIN_*; README states default stack is free-tier (Groq + Gemini + LangSmith). |

---

## 6. References

- [technical-spec.md](technical-spec.md) — Tool contracts, graph topology, state schema.
- [functional-spec.md](functional-spec.md) — Detective protocols, judicial personas, synthesis rules.
- [phase2-detective-layer/spec.md](phase2-detective-layer/spec.md) — Detective layer scope.
- [phase3-judicial-layer/spec.md](phase3-judicial-layer/spec.md) — Judicial layer scope.
- TRP1 Challenge Week 2 — The Automaton Auditor.md; reports/interim_report.pdf.
