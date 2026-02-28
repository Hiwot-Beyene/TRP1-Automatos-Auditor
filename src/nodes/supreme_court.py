"""Supreme Court: alternative Chief Justice synthesis with hardcoded deliberation rules and Markdown report."""

from typing import Any

from src.state import AgentState, AuditReport, CriterionResult, Evidence, JudicialOpinion


def chief_justice_node(state: AgentState) -> dict[str, Any]:
    """
    Synthesizes judicial opinions into a final verdict.
    Resolves conflicts using hardcoded deterministic logic.
    """
    opinions = state.get("opinions", [])
    evidences = state.get("evidences", {})
    repo_url = state.get("repo_url", "")
    rubric_dims = state.get("rubric_dimensions") or []

    grouped: dict[str, list[JudicialOpinion]] = {}
    for op in opinions:
        cid = getattr(op, "criterion_id", None) or (op.get("criterion_id") if isinstance(op, dict) else "")
        if not cid:
            continue
        if cid not in grouped:
            grouped[cid] = []
        if isinstance(op, JudicialOpinion):
            grouped[cid].append(op)
        elif isinstance(op, dict):
            grouped[cid].append(JudicialOpinion(
                judge=op.get("judge", "TechLead"),
                criterion_id=cid,
                score=op.get("score", 3),
                argument=op.get("argument", ""),
                cited_evidence=op.get("cited_evidence") or [],
            ))

    dim_name_by_id = {d.get("id", ""): d.get("name", "").strip() or d.get("id", "").replace("_", " ").title() for d in rubric_dims}

    criterion_results: list[CriterionResult] = []

    for crit_id, ops in grouped.items():
        prosecutor = next((o for o in ops if o.judge == "Prosecutor"), None)
        defense = next((o for o in ops if o.judge == "Defense"), None)
        tech_lead = next((o for o in ops if o.judge == "TechLead"), None)

        final_score = tech_lead.score if tech_lead else 3
        dissent_summary: str | None = None

        if prosecutor and prosecutor.score == 1:
            final_score = min(final_score, 3)
            dissent_summary = "Security Rule: Prosecutor identified critical flaws. Score capped."

        if crit_id == "graph_orchestration" and tech_lead:
            final_score = tech_lead.score

        graph_evidence = evidences.get("graph_orchestration") or evidences.get("state_management_rigor") or []
        has_graph = any(getattr(e, "found", False) for e in graph_evidence) if graph_evidence else False
        if defense and defense.score > 3 and not has_graph:
            final_score = min(final_score, 2)
            dissent_summary = "Evidence Rule: Defense claims of merit not supported by repository artifacts."

        scores = [o.score for o in ops]
        if scores and (max(scores) - min(scores) > 2) and not dissent_summary:
            dissent_summary = f"High Variance: Significant disagreement between judges (Range: {min(scores)}-{max(scores)})."

        dimension_name = dim_name_by_id.get(crit_id) or crit_id.replace("_", " ").title()
        criterion_results.append(CriterionResult(
            dimension_id=crit_id,
            dimension_name=dimension_name,
            final_score=max(1, min(5, final_score)),
            judge_opinions=ops,
            dissent_summary=dissent_summary,
            remediation=tech_lead.argument if tech_lead else "Improve modularity and structure.",
        ))

    overall_score = sum(r.final_score for r in criterion_results) / len(criterion_results) if criterion_results else 0.0
    overall_100 = round(overall_score * 20.0, 1)

    final_report = AuditReport(
        repo_url=repo_url,
        pdf_path=state.get("pdf_path", ""),
        executive_summary="Automaton Auditor has completed the forensic analysis and judicial deliberation.",
        overall_score=overall_score,
        overall_score_100=overall_100,
        criteria=criterion_results,
        remediation_plan="\n".join(f"- {r.dimension_name}: {r.remediation}" for r in criterion_results),
    )

    return {"final_report": final_report}


def generate_markdown_report(report: AuditReport) -> str:
    """Converts the AuditReport into a formatted Markdown string."""
    md = f"# Audit Report: {report.repo_url}\n\n"
    md += f"## Overall Score: {report.overall_score:.1f}/5.0\n\n"
    md += f"### Executive Summary\n{report.executive_summary}\n\n"
    md += "## Criterion Breakdown\n"
    for crit in report.criteria:
        md += f"### {crit.dimension_name}\n"
        md += f"- **Final Score:** {crit.final_score}/5\n"
        if crit.dissent_summary:
            md += f"- **Judicial Dissent:** {crit.dissent_summary}\n"
        md += f"- **Remediation:** {crit.remediation}\n\n"
        md += "#### Judicial Opinions\n"
        for op in crit.judge_opinions:
            md += f"- **{op.judge}:** (Score: {op.score}) {op.argument}\n"
        md += "\n"
    md += f"## Remediation Plan\n{report.remediation_plan}\n"
    return md
