"""ChiefJusticeNode: hardcoded deterministic synthesis. Produces AuditReport and Markdown."""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.rubric_loader import get_rubric
from src.state import AuditReport, CriterionResult, Evidence, JudicialOpinion


def _load_rubric():
    return get_rubric()


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


def _actionable_remediation(
    dimension: dict,
    ops: list[JudicialOpinion],
    dissent_summary: str,
    score: int,
    criterion_id: str,
    evidences: dict[str, Any],
) -> str:
    if score >= 4:
        return ""
    paths: set[str] = set()
    for op in ops:
        for ref in getattr(op, "cited_evidence", None) or []:
            s = (ref if isinstance(ref, str) else str(ref)).strip()
            if "/" in s or s.endswith((".py", ".md", ".json", ".txt")):
                paths.add(s)
    ev_list = evidences.get(criterion_id) or []
    for e in ev_list:
        loc = getattr(e, "location", None) if not isinstance(e, dict) else e.get("location")
        if loc and isinstance(loc, str) and loc.strip():
            paths.add(loc.strip())
    success = (dimension.get("success_pattern") or "").strip()
    failure = (dimension.get("failure_pattern") or "").strip()
    low = [o for o in ops if o.score <= 3 and (o.argument or "").strip()]
    parts = []
    if success:
        parts.append(f"Aim for: {success[:220]}{'...' if len(success) > 220 else ''}")
    if failure:
        parts.append(f"Avoid: {failure[:180]}{'...' if len(failure) > 180 else ''}")
    if low and low[0].argument:
        arg = (low[0].argument or "").strip()[:200]
        if len(low[0].argument or "") > 200:
            arg += "..."
        parts.append(f"({low[0].judge}): {arg}")
    if dissent_summary and dissent_summary not in (success + failure):
        parts.append(dissent_summary)
    base = " ".join(parts).strip() or "Review evidence and address gaps noted by Prosecutor and Tech Lead."
    if paths:
        path_list = sorted(paths)[:10]
        file_bullets = [f"In `{p}`: {base}" for p in path_list]
        return " ".join(file_bullets) if len(file_bullets) == 1 else "\n   - ".join([file_bullets[0]] + file_bullets[1:])
    return base


def _build_executive_summary(
    state: dict[str, Any],
    criteria: list[CriterionResult],
    overall: float,
) -> str:
    repo_url = (state.get("repo_url") or "").strip()
    pdf_path = (state.get("pdf_path") or "").strip()
    audited: list[str] = []
    if repo_url:
        audited.append("repository")
    if pdf_path:
        audited.append("document")
    scope = " and ".join(audited) if audited else "submission"
    n = len(criteria)
    score_line = f"Overall score: {overall:.1f}/5 across {n} criteria."

    strong = [c for c in criteria if c.final_score >= 4]
    weak = [c for c in criteria if c.final_score <= 2]
    with_dissent = [c for c in criteria if c.dissent_summary]

    parts = [f"This report summarizes the audit of the {scope}. {score_line}"]

    if weak:
        weak_names = ", ".join(c.dimension_name for c in weak[:3])
        if len(weak) > 3:
            weak_names += f" (and {len(weak) - 3} other)"
        parts.append(f"Criteria requiring attention: {weak_names}.")
    elif strong and len(strong) == n:
        parts.append("All criteria meet or exceed the target threshold.")
    elif strong:
        parts.append(f"{len(strong)} criteria meet or exceed the target; review the breakdown for the rest.")

    if with_dissent:
        parts.append("Notable dissents or synthesis rules applied are noted in the criterion breakdown.")
    return " ".join(parts)


def _build_remediation_plan(criteria: list[CriterionResult]) -> str:
    need_work = [c for c in criteria if c.final_score < 4]
    if not need_work:
        return (
            "All criteria meet or exceed the target threshold (4/5). "
            "No mandatory remediation. Consider optional improvements from the criterion breakdown and judge opinions."
        )
    lines = [
        "The following criteria scored below the target threshold. Address each to improve the overall audit outcome:",
        "",
    ]
    for i, c in enumerate(need_work, 1):
        bullet = f"{i}. **{c.dimension_name}** (score: {c.final_score}/5)"
        lines.append(bullet)
        if c.remediation:
            lines.append(f"   - {c.remediation[:500]}{'...' if len(c.remediation) > 500 else ''}")
        elif c.dissent_summary:
            lines.append(f"   - {c.dissent_summary}")
        low_opinions = [o for o in c.judge_opinions if o.score <= 3 and (o.argument or "").strip()]
        if low_opinions and not c.remediation:
            for o in low_opinions[:2]:
                arg = (o.argument or "").strip()[:200]
                if len(o.argument or "") > 200:
                    arg += "..."
                if arg:
                    lines.append(f"   - {o.judge} (score {o.score}): {arg}")
        lines.append("")
    return "\n".join(lines).strip()


def ChiefJusticeNode(state: dict[str, Any]) -> dict[str, Any]:
    opinions: list[JudicialOpinion] = state.get("opinions") or []
    evidences = state.get("evidences") or {}
    rubric = _load_rubric()
    synthesis_rules = rubric.get("synthesis_rules") or {}

    grouped = _group_opinions_by_criterion(opinions)
    in_scope_dims = state.get("rubric_dimensions")
    rubric_dims_order = (in_scope_dims if in_scope_dims is not None else rubric.get("dimensions", []))
    criteria: list[CriterionResult] = []
    for dim in rubric_dims_order:
        criterion_id = dim.get("id", "")
        dim_name = dim.get("name", criterion_id)
        ops = grouped.get(criterion_id, [])
        if ops:
            final_score, dissent_summary = _resolve_final_score(
                criterion_id, dim_name, ops, evidences, synthesis_rules
            )
            remediation = _actionable_remediation(dim, ops, dissent_summary or "", final_score, criterion_id, evidences)
            criteria.append(CriterionResult(
                dimension_id=criterion_id,
                dimension_name=dim_name,
                final_score=final_score,
                judge_opinions=ops,
                dissent_summary=dissent_summary or None,
                remediation=remediation,
            ))
        else:
            criteria.append(CriterionResult(
                dimension_id=criterion_id,
                dimension_name=dim_name,
                final_score=3,
                judge_opinions=[],
                dissent_summary="No judge opinions for this criterion.",
                remediation=_actionable_remediation(dim, [], "No judge opinions.", 3, criterion_id, evidences),
            ))

    overall = sum(c.final_score for c in criteria) / len(criteria) if criteria else 0.0
    overall_100 = round(overall * 20.0, 1)
    report = AuditReport(
        repo_url=state.get("repo_url") or "",
        pdf_path=state.get("pdf_path") or "",
        executive_summary=_build_executive_summary(state, criteria, overall),
        overall_score=overall,
        overall_score_100=overall_100,
        criteria=criteria,
        remediation_plan=_build_remediation_plan(criteria),
    )

    md = _report_to_markdown(report, report_type_label=_report_type_label(state.get("report_type")))
    audit_dir = Path.cwd() / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    subdir = _audit_subdir_for_report_type(state.get("report_type"))
    write_dir = audit_dir / subdir if subdir else audit_dir
    write_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    timestamped_path = write_dir / f"report_{timestamp}.md"
    timestamped_path.write_text(md, encoding="utf-8")
    (write_dir / "audit_report.md").write_text(md, encoding="utf-8")
    (audit_dir / "audit_report.md").write_text(md, encoding="utf-8")

    out_dir = state.get("audit_output_dir")
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / "audit_report.md").write_text(md, encoding="utf-8")

    return {"final_report": report}


def _report_type_label(report_type: str | None) -> str:
    if report_type == "self":
        return "Self-Audit Report (generated by this agent on own repository)"
    if report_type == "peer":
        return "Peer-Audit Report (generated by this agent on peer's repository)"
    if report_type == "peer_received":
        return "Peer-Audit Report (received from peer — audit of this repo by another agent)"
    return "Audit Report"


def _audit_subdir_for_report_type(report_type: str | None) -> str:
    if report_type == "self":
        return "report_onself_generated"
    if report_type == "peer":
        return "report_onpeer_generated"
    if report_type == "peer_received":
        return "report_bypeer_received"
    return ""


def _report_to_markdown(r: AuditReport, report_type_label: str = "Audit Report") -> str:
    """Structured Markdown: Report type → Executive Summary → Criterion Breakdown (all dimensions, dissent, per-judge opinions) → Remediation Plan."""
    repo_display = (r.repo_url or "").strip() or "N/A"
    pdf_display = (r.pdf_path or "").strip() or None
    target = 4
    verdict_label = "below target" if r.overall_score < target else ("at or above target" if r.overall_score >= target else "below target")

    lines = [
        "# Audit Report",
        "",
        f"**Report type:** {report_type_label}",
        "**Repository:** " + repo_display,
    ]
    if pdf_display:
        lines.append("**Document (PDF):** " + pdf_display)
    lines.extend([
        f"**Overall Score (Verdict):** {r.overall_score:.2f}/5 ({r.overall_score_100:.1f}/100) — {verdict_label} (threshold {target}/5).",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        r.executive_summary,
        "",
        "---",
        "",
        "## Criterion Breakdown",
        "",
        "All rubric dimensions appear below. For each dimension: final score (verdict), dissent summary when applicable, and explicit per-judge opinions (Prosecutor, Defense, Tech Lead) with cited evidence.",
        "",
    ])

    judge_order = ("Prosecutor", "Defense", "TechLead")
    for c in r.criteria:
        lines.append(f"### {c.dimension_name} (`{c.dimension_id}`)")
        lines.append("")
        lines.append(f"- **Verdict (Final Score):** {c.final_score}/5")
        if c.dissent_summary:
            lines.append(f"- **Dissent summary:** " + (c.dissent_summary.strip()[:500] + ("..." if len(c.dissent_summary) > 500 else "")))
        rem_line = (c.remediation or "").strip()
        if rem_line:
            lines.append(f"- **Remediation:**")
            for rem_part in rem_line.split("\n"):
                p = rem_part.strip()
                if p:
                    lines.append(f"  - {p[:500]}{'...' if len(p) > 500 else ''}")
        lines.append("")
        lines.append("**Per-judge opinions:**")
        for judge_name in judge_order:
            op = next((o for o in c.judge_opinions if o.judge == judge_name), None)
            if op:
                arg = (op.argument or "").strip()
                if len(arg) > 400:
                    arg = arg[:397] + "..."
                lines.append(f"- **{op.judge}** (score {op.score}/5): {arg or '—'}")
                cited = getattr(op, "cited_evidence", None) or []
                if isinstance(cited, list) and cited:
                    refs = ", ".join(str(x)[:80] for x in cited[:5])
                    if len(cited) > 5:
                        refs += ", …"
                    lines.append(f"  - *Cited evidence:* " + refs)
            else:
                lines.append(f"- **{judge_name}:** — (no opinion submitted)")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Remediation Plan",
        "",
        "File-level and criterion-specific steps for criteria scoring below the target (4/5).",
        "",
    ])
    need_work = [c for c in r.criteria if c.final_score < 4]
    if not need_work:
        lines.append("All criteria meet or exceed the target threshold. No mandatory remediation.")
    else:
        for i, c in enumerate(need_work, 1):
            lines.append(f"{i}. **{c.dimension_name}** (score {c.final_score}/5)")
            rem = (c.remediation or "").strip()
            if rem:
                for part in rem.split("\n"):
                    if part.strip():
                        lines.append(f"   - {part.strip()[:500]}{'...' if len(part.strip()) > 500 else ''}")
            else:
                line = (c.dissent_summary or "Review evidence and address gaps noted by Prosecutor and Tech Lead.").strip()
                lines.append(f"   - {line[:500]}{'...' if len(line) > 500 else ''}")
            lines.append("")
    lines.append("")
    return "\n".join(lines)
