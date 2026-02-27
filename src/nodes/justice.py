"""ChiefJusticeNode: hardcoded deterministic synthesis. Produces AuditReport and Markdown."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.state import AuditReport, CriterionResult, Evidence, JudicialOpinion


RUBRIC_PATH = Path(__file__).resolve().parent.parent.parent / "rubric.json"


def _load_rubric():
    for p in (RUBRIC_PATH, Path.cwd() / "rubric.json"):
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return {"dimensions": [], "synthesis_rules": {}}


def _group_opinions_by_criterion(opinions: list[Any]) -> dict[str, list[JudicialOpinion]]:
    out: dict[str, list[JudicialOpinion]] = defaultdict(list)
    for op in opinions:
        if isinstance(op, JudicialOpinion):
            out[op.criterion_id].append(op)
        elif isinstance(op, dict) and op.get("criterion_id"):
            out[op["criterion_id"]].append(JudicialOpinion(
                judge=op.get("judge", "TechLead"),
                criterion_id=op["criterion_id"],
                score=op.get("score", 3),
                argument=op.get("argument", ""),
                cited_evidence=op.get("cited_evidence") or [],
            ))
    return dict(out)


def _scores(ops: list[JudicialOpinion]) -> list[int]:
    return [o.score for o in ops if hasattr(o, "score")]


def _variance(ops: list[JudicialOpinion]) -> int:
    s = _scores(ops)
    if not s:
        return 0
    return max(s) - min(s)


def _prosecutor_flags_security(ops: list[JudicialOpinion]) -> bool:
    for o in ops:
        if o.judge == "Prosecutor" and "security" in (o.argument or "").lower():
            if o.score <= 2:
                return True
    return False


def _evidence_missing_for_criterion(evidences: dict[str, Any], criterion_id: str) -> bool:
    elist = evidences.get(criterion_id) or []
    if not elist:
        return True
    for e in elist:
        found = getattr(e, "found", None)
        if isinstance(e, dict):
            found = e.get("found", False)
        if found:
            return False
    return True


def _defense_overruled_fact_supremacy(ops: list[JudicialOpinion], evidences: dict[str, list[Evidence]], criterion_id: str) -> bool:
    if not _evidence_missing_for_criterion(evidences, criterion_id):
        return False
    for o in ops:
        if o.judge == "Defense" and o.score >= 4:
            return True
    return False


def _tech_lead_confirms_modular(ops: list[JudicialOpinion], criterion_id: str) -> bool:
    if criterion_id != "graph_orchestration":
        return False
    for o in ops:
        if o.judge == "TechLead" and "modular" in (o.argument or "").lower() and o.score >= 4:
            return True
    return False


def _resolve_final_score(
    criterion_id: str,
    dimension_name: str,
    ops: list[JudicialOpinion],
    evidences: dict[str, Any],
    synthesis_rules: dict[str, str],
) -> tuple[int, str]:
    scores = _scores(ops)
    if not scores:
        return 3, ""

    prosecutor_op = next((o for o in ops if o.judge == "Prosecutor"), None)
    defense_op = next((o for o in ops if o.judge == "Defense"), None)
    tech_op = next((o for o in ops if o.judge == "TechLead"), None)

    if _prosecutor_flags_security(ops):
        final = min(3, min(scores))
        dissent = "Rule of Security: Prosecutor identified security concern; score capped at 3."
        return final, dissent

    if _defense_overruled_fact_supremacy(ops, evidences, criterion_id):
        scores_no_defense = [o.score for o in ops if o.judge != "Defense"]
        final = sum(scores_no_defense) // len(scores_no_defense) if scores_no_defense else 3
        dissent = "Rule of Evidence: Defense overruled; evidence does not support claim."
        return final, dissent

    if _tech_lead_confirms_modular(ops, criterion_id):
        if tech_op and tech_op.score >= 4:
            final = max(scores)
            dissent = "Rule of Functionality: Tech Lead confirms modular architecture; highest weight applied."
            return final, dissent

    variance = _variance(ops)
    if variance > 2:
        re_eval = (prosecutor_op.argument or "")[:100] + " | " + (defense_op.argument or "")[:100] if (prosecutor_op and defense_op) else ""
        dissent = f"Score variance > 2; re-evaluation applied. Prosecutor: {prosecutor_op.score if prosecutor_op else '?'}; Defense: {defense_op.score if defense_op else '?'}; TechLead: {tech_op.score if tech_op else '?'}. {re_eval}"
        final = sum(scores) // len(scores)
        return final, dissent

    final = sum(scores) // len(scores)
    dissent = ""
    if variance > 0:
        dissent = f"Prosecutor {prosecutor_op.score if prosecutor_op else '-'}, Defense {defense_op.score if defense_op else '-'}, TechLead {tech_op.score if tech_op else '-'}."
    return max(1, min(5, final)), dissent


def ChiefJusticeNode(state: dict[str, Any]) -> dict[str, Any]:
    opinions: list[JudicialOpinion] = state.get("opinions") or []
    evidences = state.get("evidences") or {}
    rubric = _load_rubric()
    dimensions = {d["id"]: d for d in rubric.get("dimensions", [])}
    synthesis_rules = rubric.get("synthesis_rules") or {}

    grouped = _group_opinions_by_criterion(opinions)
    criteria: list[CriterionResult] = []
    for criterion_id, ops in grouped.items():
        dim = dimensions.get(criterion_id, {})
        dim_name = dim.get("name", criterion_id)
        final_score, dissent_summary = _resolve_final_score(
            criterion_id, dim_name, ops, evidences, synthesis_rules
        )
        criteria.append(CriterionResult(
            dimension_id=criterion_id,
            dimension_name=dim_name,
            final_score=final_score,
            judge_opinions=ops,
            dissent_summary=dissent_summary or None,
            remediation="",
        ))

    for dim in rubric.get("dimensions", []):
        if dim["id"] not in grouped:
            criteria.append(CriterionResult(
                dimension_id=dim["id"],
                dimension_name=dim.get("name", dim["id"]),
                final_score=3,
                judge_opinions=[],
                dissent_summary="No judge opinions for this criterion.",
                remediation="",
            ))

    overall = sum(c.final_score for c in criteria) / len(criteria) if criteria else 0.0
    report = AuditReport(
        repo_url=state.get("repo_url") or "",
        executive_summary=f"Audit completed. {len(criteria)} criteria evaluated. Overall score: {overall:.1f}/5.",
        overall_score=overall,
        criteria=criteria,
        remediation_plan="Review criterion breakdown and dissent summaries for remediation.",
    )

    md = _report_to_markdown(report)
    out_dir = state.get("audit_output_dir")
    if out_dir:
        out_path = Path(out_dir) / "audit_report.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
    out_path = Path.cwd() / "reports" / "audit_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")

    return {"final_report": report}


def _report_to_markdown(r: AuditReport) -> str:
    lines = [
        "# Automaton Auditor — Audit Report",
        "",
        "## Executive Summary",
        r.executive_summary,
        "",
        f"**Overall score:** {r.overall_score:.1f}/5",
        "",
        "## Criterion Breakdown",
        "",
    ]
    for c in r.criteria:
        lines.append(f"### {c.dimension_name} (`{c.dimension_id}`)")
        lines.append(f"- **Final score:** {c.final_score}/5")
        if c.dissent_summary:
            lines.append(f"- **Dissent:** {c.dissent_summary}")
        for op in c.judge_opinions:
            arg = (op.argument or "")[:150]
            if len(op.argument or "") > 150:
                arg += "..."
            lines.append(f"- **{op.judge}:** {op.score} — {arg}")
        lines.append("")
    lines.append("## Remediation Plan")
    lines.append(r.remediation_plan)
    lines.append("")
    return "\n".join(lines)
