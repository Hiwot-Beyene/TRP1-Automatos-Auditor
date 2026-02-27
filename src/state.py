"""Graph state and Pydantic models for the Automaton Auditor."""

import operator
from typing import Annotated, Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    goal: str
    found: bool
    content: Optional[str] = None
    location: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


class JudicialOpinion(BaseModel):
    judge: Literal["Prosecutor", "Defense", "TechLead"]
    criterion_id: str
    score: int = Field(ge=1, le=5)
    argument: str
    cited_evidence: list[str] = Field(default_factory=list)


class CriterionResult(BaseModel):
    dimension_id: str
    dimension_name: str
    final_score: int = Field(ge=1, le=5)
    judge_opinions: list[JudicialOpinion] = Field(default_factory=list)
    dissent_summary: Optional[str] = None
    remediation: str = ""


class AuditReport(BaseModel):
    repo_url: str = ""
    pdf_path: str = ""
    executive_summary: str = ""
    overall_score: float = 0.0
    criteria: list[CriterionResult] = Field(default_factory=list)
    remediation_plan: str = ""


class AgentState(TypedDict, total=False):
    repo_url: str
    pdf_path: str
    rubric_dimensions: list[dict[str, Any]]
    pdf_chunks: list[dict[str, Any]]
    pdf_images: list[dict[str, Any]]
    evidences: Annotated[dict[str, list[Evidence]], operator.ior]
    opinions: Annotated[list[JudicialOpinion], operator.add]
    final_report: AuditReport
