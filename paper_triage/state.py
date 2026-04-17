from typing import TypedDict, Optional, Literal, Annotated
from pydantic import BaseModel, Field
from datetime import datetime
import operator


class PlanStep(BaseModel):
    step_id: int
    action: str
    tool: Literal["arxiv_search", "semantic_scholar_search", "semantic_scholar_citations"]
    args: dict
    rationale: str


class Plan(BaseModel):
    steps: list[PlanStep]
    summary: str


class ToolCall(BaseModel):
    step_id: int
    tool: str
    args: dict
    result_summary: str
    raw_result: dict
    timestamp: str
    error: Optional[str] = None


class Paper(BaseModel):
    paper_id: str
    title: str
    abstract: Optional[str]
    year: Optional[int]
    citation_count: Optional[int] = None
    influential_citation_count: Optional[int] = None
    source: Literal["arxiv", "semantic_scholar"]


class AgentState(TypedDict):
    question: str
    plan: Optional[Plan]
    plan_approved: bool
    user_feedback: Optional[str]
    trace: Annotated[list[ToolCall], operator.add]
    retrieved: Annotated[list[Paper], operator.add]
    answer: Optional[str]
