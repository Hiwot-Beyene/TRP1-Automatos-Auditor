"""Unit tests for state models (Evidence, AuditReport, reducer semantics)."""

import pytest
from pydantic import ValidationError

from src.state import Evidence, JudicialOpinion, AuditReport


def test_evidence_requires_goal_found_location_rationale():
    Evidence(goal="g", found=True, location="x", rationale="r", confidence=0.0)
    Evidence(goal="g", found=False, location="", rationale="", content=None, confidence=0.0)


def test_evidence_confidence_bounds():
    Evidence(goal="g", found=True, location="x", rationale="r", confidence=0.0)
    Evidence(goal="g", found=True, location="x", rationale="r", confidence=1.0)
    with pytest.raises(ValidationError):
        Evidence(goal="g", found=True, location="x", rationale="r", confidence=-0.1)
    with pytest.raises(ValidationError):
        Evidence(goal="g", found=True, location="x", rationale="r", confidence=1.1)


def test_evidence_model_dump_roundtrip():
    e = Evidence(goal="dim1", found=True, content="c", location="loc", rationale="r", confidence=0.8)
    d = e.model_dump()
    assert d["goal"] == "dim1" and d["found"] is True and d["confidence"] == 0.8
    e2 = Evidence.model_validate(d)
    assert e2.goal == e.goal and e2.confidence == e.confidence


def test_judicial_opinion_judge_literal():
    JudicialOpinion(judge="Prosecutor", criterion_id="c1", score=1, argument="a", cited_evidence=[])
    JudicialOpinion(judge="Defense", criterion_id="c1", score=5, argument="a")
    JudicialOpinion(judge="TechLead", criterion_id="c1", score=3, argument="a")
    with pytest.raises(ValidationError):
        JudicialOpinion(judge="Other", criterion_id="c1", score=1, argument="a")


def test_audit_report_defaults():
    r = AuditReport()
    assert r.repo_url == "" and r.overall_score == 0.0 and r.criteria == []
