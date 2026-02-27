# Multi-Model Stack Specification

**Feature**: Automaton Auditor | **Source**: TRP1 Challenge Week 2, interim report, free-tier research  
**Purpose**: Defines which LLM/vendor powers each node. Specification only; no implementation. Use for speckit.analyse and TDD before implementation.

**Constraint:** All models MUST be usable on **free tiers** (no paid API required). Best-fit per responsibility.

---

## 1. Stack Overview

| Responsibility | Node(s) | Model / Service | Provider | Free tier |
|----------------|---------|-----------------|----------|-----------|
| Forensic / Repo Investigator | RepoInvestigator | Groq — Llama 3.1 70B | Groq | Yes (14,400 RPD, 30 RPM, 6K TPM) |
| Judicial Bench | Prosecutor, Defense, TechLead | Groq — Llama 3.1 70B | Groq | Same as above |
| Document + Vision | DocAnalyst, VisionInspector | Google Gemini 1.5 Flash | Google AI Studio | Yes (~250 RPD, 10 RPM; vision + long context) |
| Observability | All nodes | LangSmith | LangChain | Yes (unlimited runs on Developer tier) |

No OpenAI (e.g. GPT-4o-mini) is required for the default stack.

---

## 2. Per-Node Requirements (Specification)

### 2.1 RepoInvestigator (Forensic / Code)

- **Primary:** Tool-only behavior (sandboxed clone, git log, AST analysis) as defined in technical-spec and phase2. No LLM required for basic evidence.
- **Optional LLM:** When an LLM is used (e.g. to summarize git history, interpret AST results, or generate rationale text), it MUST use **Groq — Llama 3.1 70B** (model id per Groq docs, e.g. `llama-3.1-70b-versatile`).
- **Env:** `GROQ_API_KEY`. If unset, node MUST still produce Evidence using tools only; MUST NOT fail. If set and LLM is invoked, MUST use Groq.
- **Acceptance (TDD):** When `GROQ_API_KEY` is set and implementation uses an LLM for RepoInvestigator, the client MUST be Groq with Llama 3.1 70B. When unset, evidence MUST be produced without calling any LLM.

### 2.2 DocAnalyst (Document / PDF)

- **LLM:** MUST use **Google Gemini 1.5 Flash** (or 2.0 Flash if available on free tier) for RAG-lite querying, theoretical-depth search, and cross-reference reasoning over ingested PDF chunks.
- **Env:** `GOOGLE_API_KEY` (or provider-specific env documented by LangChain for Google Gemini). If unset, node MAY return evidence with `found=False` and rationale indicating missing API key, or skip LLM and use only local PDF ingestion/chunking.
- **Acceptance (TDD):** When `GOOGLE_API_KEY` is set, DocAnalyst LLM calls MUST use Gemini 1.5 Flash (or specified Flash variant). No OpenAI or other vendor for this node unless overridden by explicit config.

### 2.3 VisionInspector (Diagram / Images)

- **LLM:** MUST use **Google Gemini 1.5 Flash** (vision/multimodal) for image analysis. Input: images extracted from PDF via `extract_images_from_pdf`. Prompt must ask for classification (e.g. StateGraph diagram vs generic flowchart) and flow description.
- **Env:** Same as DocAnalyst — `GOOGLE_API_KEY`. If unset, node MAY return evidence with `found=False` or placeholder rationale; MUST NOT call a paid vision API as default.
- **Acceptance (TDD):** When `GOOGLE_API_KEY` is set, VisionInspector MUST call Gemini with image parts (base64 or API-accepted format). Vision execution is required for final deliverable (not optional).

### 2.4 Prosecutor, Defense, TechLead (Judges)

- **LLM:** MUST use **Groq — Llama 3.1 70B** for all three. Same model, distinct system prompts (Prosecutor critical, Defense charitable, Tech Lead pragmatic).
- **Structured output:** MUST use `.with_structured_output(JudicialOpinion)` or equivalent bound to Pydantic `JudicialOpinion`. Retry on parse failure; no free-text-only output.
- **Env:** `GROQ_API_KEY`. If unset, implementation MAY return placeholder opinions (e.g. score=3, argument="API key not set") so graph can complete; MUST NOT require OpenAI.
- **Acceptance (TDD):** Judge nodes MUST use Groq Llama 3.1 70B when `GROQ_API_KEY` is set. All three personas MUST use the same model and provider.

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
| `GROQ_API_KEY` | Groq API (Llama 3.1 70B) | RepoInvestigator (optional LLM), Prosecutor, Defense, TechLead |
| `GOOGLE_API_KEY` | Google AI Studio (Gemini) | DocAnalyst, VisionInspector |
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
| M4 | Judge LLM | Prosecutor, Defense, TechLead all use Groq Llama 3.1 70B when `GROQ_API_KEY` set. Structured output JudicialOpinion. |
| M5 | Chief Justice | No LLM; deterministic rules only. |
| M6 | Env and docs | `.env.example` lists GROQ_API_KEY, GOOGLE_API_KEY, LANGCHAIN_*; README states default stack is free-tier (Groq + Gemini + LangSmith). |

---

## 6. References

- [technical-spec.md](technical-spec.md) — Tool contracts, graph topology, state schema.
- [functional-spec.md](functional-spec.md) — Detective protocols, judicial personas, synthesis rules.
- [phase2-detective-layer/spec.md](phase2-detective-layer/spec.md) — Detective layer scope.
- [phase3-judicial-layer/spec.md](phase3-judicial-layer/spec.md) — Judicial layer scope.
- TRP1 Challenge Week 2 — The Automaton Auditor.md; reports/interim_report.pdf.
