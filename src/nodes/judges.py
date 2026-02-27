"""Judge nodes: Prosecutor, Defense, TechLead. Uses src.llm for LLM (Groq/Gemini)."""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_judge_llm, get_judge_llm_google, get_judge_llm_groq
from src.rubric_loader import get_synthesis_rules
from src.state import Evidence, JudicialOpinion


JUDGE_RETRY_ATTEMPTS = 2
EVIDENCE_SUMMARY_MAX_CHARS = 1200


def _load_synthesis_rules() -> dict[str, str]:
    return get_synthesis_rules()


def _evidence_summary(evidences: dict[str, list[Evidence]], dimension_id: str) -> str:
    elist = evidences.get(dimension_id) or []
    if not elist:
        return "No evidence collected for this criterion."
    parts = []
    total = 0
    for e in elist[:5]:
        if total >= EVIDENCE_SUMMARY_MAX_CHARS:
            break
        line = f"- found={e.found}, location={e.location}"
        if e.rationale:
            line += f", rationale={e.rationale[:200]}"
        if e.content:
            content_snippet = (e.content[:400] + "...") if len(e.content) > 400 else e.content
            line += f"\n  content: {content_snippet}"
        if total + len(line) > EVIDENCE_SUMMARY_MAX_CHARS:
            line = line[: EVIDENCE_SUMMARY_MAX_CHARS - total - 3] + "..."
        parts.append(line)
        total += len(line)
    return "\n".join(parts) if parts else "No evidence."


def _parse_json_fallback(text: str) -> dict[str, Any] | None:
    if not text or not text.strip():
        return None
    text = text.strip()
    stripped = re.sub(r"^```(?:json)?\s*", "", text)
    stripped = re.sub(r"\s*```\s*$", "", stripped).strip()
    for candidate in (text, stripped):
        if not candidate.startswith("{"):
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        start = candidate.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(candidate)):
                if candidate[i] == "{":
                    depth += 1
                elif candidate[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(candidate[start : i + 1])
                        except json.JSONDecodeError:
                            break
                        break
    return None


def _opinion_for_dimension(
    judge_name: Literal["Prosecutor", "Defense", "TechLead"],
    dimension: dict[str, Any],
    evidence_text: str,
    system_prompt: str,
) -> JudicialOpinion:
    llm = get_judge_llm()
    if llm is None:
        return JudicialOpinion(judge=judge_name, criterion_id=dimension.get("id", "unknown"), score=3, argument="No judge LLM (set GROQ_API_KEY or GOOGLE_API_KEY); placeholder opinion", cited_evidence=[])
    dim_id = dimension.get("id", "unknown")
    dim_name = dimension.get("name", "")
    instruction = dimension.get("forensic_instruction", "")
    success = dimension.get("success_pattern", "")
    failure = dimension.get("failure_pattern", "")

    role_reminder = {"Prosecutor": "Respond ONLY as the Prosecutor. Be critical; cite gaps and weaknesses.", "Defense": "Respond ONLY as the Defense. Be charitable; cite evidence that supports the team.", "TechLead": "Respond ONLY as the Tech Lead. Be pragmatic; cite architectural and implementation evidence."}.get(judge_name, "")
    user_base = f"""Role: {role_reminder}

Criterion: {dim_name} (id={dim_id})
Forensic instruction: {instruction}
Success pattern: {success}
Failure pattern: {failure}

Evidence collected:
{evidence_text}

Provide your opinion: score (1-5 integer), argument (string), and cited_evidence (list of short strings)."""

    user_json = user_base + """

You must respond with ONLY a valid JSON object, no other text. Use this exact shape:
{"score": <1-5>, "argument": "<your reasoning>", "cited_evidence": ["<quote1>", "<quote2>"]}"""

    json_system = system_prompt + "\n\nYou must respond with ONLY a valid JSON object: {\"score\": <1-5>, \"argument\": \"...\", \"cited_evidence\": [...]}. No markdown, no explanation outside the JSON."

    def try_llm(use_structured: bool):
        nonlocal llm
        if use_structured:
            try:
                structured_llm = llm.with_structured_output(JudicialOpinion)
                out = structured_llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_base),
                ])
                if isinstance(out, JudicialOpinion):
                    return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=out.score, argument=out.argument or "", cited_evidence=out.cited_evidence or [])
            except Exception:
                pass
        raw = llm.invoke([
            SystemMessage(content=json_system),
            HumanMessage(content=user_json),
        ])
        content = getattr(raw, "content", None) or str(raw)
        parsed = _parse_json_fallback(content)
        if parsed:
            score = int(parsed.get("score", 3))
            score = max(1, min(5, score))
            argument = str(parsed.get("argument", "")) or "Parsed from JSON"
            cited = parsed.get("cited_evidence")
            cited = [str(x) for x in (cited[:10] if isinstance(cited, list) else ([str(c) for c in cited] if cited else []))]
            return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=score, argument=argument[:2000], cited_evidence=cited)
        return None

    last_error: str | None = None
    for attempt in range(JUDGE_RETRY_ATTEMPTS):
        use_structured = attempt == 0
        try:
            result = try_llm(use_structured)
            if result is not None:
                return result
        except Exception as e:
            err = str(e).strip() or e.__class__.__name__
            last_error = err[:120] + "..." if len(err) > 120 else err
            is_429 = "429" in err or "rate limit" in err.lower()
            is_400 = "400" in err or "failed to call" in err.lower()
            if is_400:
                try:
                    result = try_llm(False)
                    if result is not None:
                        return result
                except Exception:
                    pass
            if (is_429 or is_400) and get_judge_llm_groq() is llm:
                fallback = get_judge_llm_google()
                if fallback:
                    llm = fallback
                    try:
                        result = try_llm(False)
                        if result is not None:
                            return result
                    except Exception:
                        pass
        if attempt == JUDGE_RETRY_ATTEMPTS - 1 and last_error:
            return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=3, argument=f"Parse/LLM error after retries: {last_error}", cited_evidence=[])

    return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=3, argument="Judge error", cited_evidence=[])


def _run_judge(judge_name: Literal["Prosecutor", "Defense", "TechLead"], state: dict[str, Any], system_prompt: str) -> dict[str, Any]:
    evidences = state.get("evidences") or {}
    dimensions = state.get("rubric_dimensions") or []
    if not dimensions:
        return {"opinions": []}
    rules = _load_synthesis_rules()
    constitution = ""
    if rules:
        constitution = "\n\nConstitution (Chief Justice will apply): " + "; ".join(rules.values())[:600]
    full_prompt = system_prompt + constitution
    opinions = []
    for dim in dimensions:
        dim_id = dim.get("id", "unknown")
        evidence_text = _evidence_summary(evidences, dim_id)
        op = _opinion_for_dimension(judge_name, dim, evidence_text, full_prompt)
        opinions.append(op)
    return {"opinions": opinions}


PROSECUTOR_SYSTEM = """You are the Prosecutor. Be adversarial and critical. Look for gaps, security flaws, laziness, and missing evidence. Reward only when the evidence clearly meets the success pattern. Score low (1-2) when evidence is weak or the failure pattern applies; avoid scoring 4-5 unless evidence is overwhelming. Cite specific evidence that shows gaps or failures in cited_evidence. Your reasoning must be clearly distinct from a charitable or pragmatic view. Apply the Constitution: security flaws cap score at 3; evidence overrides opinion; variance > 2 triggers re-evaluation."""

DEFENSE_SYSTEM = """You are the Defense. Reward effort, intent, and creative workarounds. Interpret evidence charitably. Score higher (3-5) when the team made a good-faith attempt; avoid scoring 1-2 unless evidence clearly meets the failure pattern. Cite evidence that supports the defendant's case in cited_evidence. Your reasoning must be clearly distinct from a critical or purely technical view. The Constitution: fact supremacy (evidence overrules opinion); if evidence is missing, your high score may be overruled."""

TECH_LEAD_SYSTEM = """You are the Tech Lead. Focus on architectural soundness, maintainability, and practical viability. Be pragmatic: does it work? Is it modular? Score based on functionality and structure only; score 1-2 only when architecture is broken or missing. Cite evidence that supports your technical assessment in cited_evidence. Your reasoning must be clearly distinct from an adversarial or charitable view. The Constitution: your confirmation of modular architecture carries highest weight for Graph Orchestration; variance > 2 triggers re-evaluation."""


def ProsecutorNode(state: dict[str, Any]) -> dict[str, Any]:
    return _run_judge("Prosecutor", state, PROSECUTOR_SYSTEM)


def DefenseNode(state: dict[str, Any]) -> dict[str, Any]:
    return _run_judge("Defense", state, DEFENSE_SYSTEM)


def TechLeadNode(state: dict[str, Any]) -> dict[str, Any]:
    return _run_judge("TechLead", state, TECH_LEAD_SYSTEM)


def JudicialPanelNode(state: dict[str, Any]) -> dict[str, Any]:
    """Run Prosecutor, Defense, TechLead in parallel and merge opinions."""
    with ThreadPoolExecutor(max_workers=3) as executor:
        fut_p = executor.submit(ProsecutorNode, state)
        fut_d = executor.submit(DefenseNode, state)
        fut_t = executor.submit(TechLeadNode, state)
        p = fut_p.result().get("opinions") or []
        d = fut_d.result().get("opinions") or []
        t = fut_t.result().get("opinions") or []
    return {"opinions": p + d + t}
