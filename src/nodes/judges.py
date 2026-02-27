"""Judge nodes: Prosecutor, Defense, TechLead. Each uses .with_structured_output(JudicialOpinion)."""

import os
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from src.state import Evidence, JudicialOpinion


JUDGE_RETRY_ATTEMPTS = 2
GROQ_MODEL = "llama-3.1-70b-versatile"


def _get_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return ChatGroq(
        model=GROQ_MODEL,
        temperature=0.3,
        api_key=api_key,
    )


def _evidence_summary(evidences: dict[str, list[Evidence]], dimension_id: str) -> str:
    elist = evidences.get(dimension_id) or []
    if not elist:
        return "No evidence collected for this criterion."
    parts = []
    for e in elist[:5]:
        parts.append(f"- found={e.found}, location={e.location}, rationale={e.rationale[:200] if e.rationale else ''}")
    return "\n".join(parts) if parts else "No evidence."


def _opinion_for_dimension(
    judge_name: Literal["Prosecutor", "Defense", "TechLead"],
    dimension: dict[str, Any],
    evidence_text: str,
    system_prompt: str,
) -> JudicialOpinion:
    llm = _get_llm()
    if llm is None:
        return JudicialOpinion(judge=judge_name, criterion_id=dimension.get("id", "unknown"), score=3, argument="GROQ_API_KEY not set; placeholder opinion", cited_evidence=[])
    structured_llm = llm.with_structured_output(JudicialOpinion)
    dim_id = dimension.get("id", "unknown")
    dim_name = dimension.get("name", "")
    instruction = dimension.get("forensic_instruction", "")
    success = dimension.get("success_pattern", "")
    failure = dimension.get("failure_pattern", "")

    user = f"""Criterion: {dim_name} (id={dim_id})
Forensic instruction: {instruction}
Success pattern: {success}
Failure pattern: {failure}

Evidence collected:
{evidence_text}

Provide your opinion: score (1-5), argument, and cited_evidence (list of short strings from the evidence)."""

    for attempt in range(JUDGE_RETRY_ATTEMPTS):
        try:
            out = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user),
            ])
            if isinstance(out, JudicialOpinion):
                return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=out.score, argument=out.argument, cited_evidence=out.cited_evidence or [])
            return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=3, argument="Parse fallback", cited_evidence=[])
        except Exception:
            if attempt == JUDGE_RETRY_ATTEMPTS - 1:
                return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=3, argument="Judge failed to return structured output", cited_evidence=[])
    return JudicialOpinion(judge=judge_name, criterion_id=dim_id, score=3, argument="Judge error", cited_evidence=[])


def _run_judge(judge_name: Literal["Prosecutor", "Defense", "TechLead"], state: dict[str, Any], system_prompt: str) -> dict[str, Any]:
    evidences = state.get("evidences") or {}
    dimensions = state.get("rubric_dimensions") or []
    if not dimensions:
        return {"opinions": []}
    opinions = []
    for dim in dimensions:
        dim_id = dim.get("id", "unknown")
        evidence_text = _evidence_summary(evidences, dim_id)
        op = _opinion_for_dimension(judge_name, dim, evidence_text, system_prompt)
        opinions.append(op)
    return {"opinions": opinions}


PROSECUTOR_SYSTEM = """You are the Prosecutor. Be adversarial and critical. Look for gaps, security flaws, laziness, and missing evidence. Reward only when the evidence clearly meets the success pattern. Score low (1-2) when evidence is weak or the failure pattern applies. Cite specific evidence in cited_evidence."""

DEFENSE_SYSTEM = """You are the Defense. Reward effort, intent, and creative workarounds. Interpret evidence charitably. Score higher (3-5) when the team made a good-faith attempt. Cite evidence that supports the defendant's case in cited_evidence."""

TECH_LEAD_SYSTEM = """You are the Tech Lead. Focus on architectural soundness, maintainability, and practical viability. Be pragmatic: does it work? Is it modular? Score based on functionality and structure. Cite evidence that supports your technical assessment in cited_evidence."""


def ProsecutorNode(state: dict[str, Any]) -> dict[str, Any]:
    return _run_judge("Prosecutor", state, PROSECUTOR_SYSTEM)


def DefenseNode(state: dict[str, Any]) -> dict[str, Any]:
    return _run_judge("Defense", state, DEFENSE_SYSTEM)


def TechLeadNode(state: dict[str, Any]) -> dict[str, Any]:
    return _run_judge("TechLead", state, TECH_LEAD_SYSTEM)


def JudicialPanelNode(state: dict[str, Any]) -> dict[str, Any]:
    """Run Prosecutor, Defense, TechLead and merge opinions."""
    p = ProsecutorNode(state)
    d = DefenseNode(state)
    t = TechLeadNode(state)
    opinions = (p.get("opinions") or []) + (d.get("opinions") or []) + (t.get("opinions") or [])
    return {"opinions": opinions}
