"""Judge nodes: Prosecutor, Defense, TechLead. Groq with configurable model (default 8b for higher rate limits)."""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.state import Evidence, JudicialOpinion


JUDGE_RETRY_ATTEMPTS = 2
GROQ_JUDGE_MODEL = os.environ.get("GROQ_JUDGE_MODEL", "llama-3.1-8b-instant")
RUBRIC_PATH = Path(__file__).resolve().parent.parent.parent / "rubric.json"


def _load_synthesis_rules() -> dict[str, str]:
    for p in (RUBRIC_PATH, Path.cwd() / "rubric.json"):
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return data.get("synthesis_rules") or {}
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def _get_llm():
    if not os.environ.get("GROQ_API_KEY"):
        return None
    model = os.environ.get("GROQ_JUDGE_MODEL", GROQ_JUDGE_MODEL) or GROQ_JUDGE_MODEL
    return ChatGroq(model=model, temperature=0.6)


def _evidence_summary(evidences: dict[str, list[Evidence]], dimension_id: str) -> str:
    elist = evidences.get(dimension_id) or []
    if not elist:
        return "No evidence collected for this criterion."
    parts = []
    for e in elist[:5]:
        line = f"- found={e.found}, location={e.location}"
        if e.rationale:
            line += f", rationale={e.rationale[:200]}"
        if e.content:
            line += f"\n  content: {(e.content[:400] + '...') if len(e.content) > 400 else e.content}"
        parts.append(line)
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
    llm = _get_llm()
    if llm is None:
        return JudicialOpinion(judge=judge_name, criterion_id=dimension.get("id", "unknown"), score=3, argument="GROQ_API_KEY not set; placeholder opinion", cited_evidence=[])
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

    for attempt in range(JUDGE_RETRY_ATTEMPTS):
        last_error: str | None = None
        try:
            structured_llm = llm.with_structured_output(JudicialOpinion)
            out = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_base),
            ])
            if isinstance(out, JudicialOpinion):
                return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=out.score, argument=out.argument or "", cited_evidence=out.cited_evidence or [])
        except Exception as e:
            last_error = str(e).strip() or e.__class__.__name__
            if len(last_error) > 120:
                last_error = last_error[:117] + "..."

        try:
            raw = llm.invoke([
                SystemMessage(content=system_prompt + "\n\nYou must respond with ONLY a valid JSON object: {\"score\": <1-5>, \"argument\": \"...\", \"cited_evidence\": [...]}. No markdown, no explanation outside the JSON."),
                HumanMessage(content=user_json),
            ])
            content = getattr(raw, "content", None) or str(raw)
            parsed = _parse_json_fallback(content)
            if parsed:
                score = int(parsed.get("score", 3))
                if score < 1:
                    score = 1
                if score > 5:
                    score = 5
                argument = str(parsed.get("argument", "")) or "Parsed from JSON fallback"
                cited = parsed.get("cited_evidence")
                if not isinstance(cited, list):
                    cited = [str(c) for c in cited] if cited else []
                else:
                    cited = [str(x) for x in cited[:10]]
                return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=score, argument=argument[:2000], cited_evidence=cited)
        except Exception as e:
            last_error = str(e).strip() or e.__class__.__name__
            if len(last_error) > 120:
                last_error = last_error[:117] + "..."

        if attempt == JUDGE_RETRY_ATTEMPTS - 1:
            msg = f"Parse/LLM error after retries: {last_error}" if last_error else "Judge failed to return structured output"
            return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=3, argument=msg, cited_evidence=[])

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
