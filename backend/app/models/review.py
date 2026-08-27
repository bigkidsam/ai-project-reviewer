from typing import Any

from pydantic import AnyUrl
from pydantic import BaseModel
from pydantic import Field


class Finding(BaseModel):
    file: str = ""
    line: int | None = None
    column: int | None = None
    code: str | None = ""
    symbol: str | None = ""
    message: str = ""
    severity: str = "low"
    tool: str | None = ""


class FixSuggestion(BaseModel):
    file: str = ""
    line: int | None = None
    column: int | None = None
    symbol: str | None = ""
    problem: str = ""
    suggested_code: str = ""
    explanation: str | None = ""
    confidence: str | None = ""
    tier: str | None = None


class ReviewBase(BaseModel):
    repo_url: str
    analyzed_files: list[str]
    repository_metadata: dict[str, object] = Field(default_factory=dict)
    metrics: dict[str, object] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    fix_suggestions: list[FixSuggestion] = Field(default_factory=list)
    issues: str = ""
    ai_review: str = ""
    scorecard: dict[str, Any] = Field(default_factory=dict)


class ReviewRequest(BaseModel):
    repo_url: AnyUrl
    max_files: int = Field(default=10, ge=1, le=100)


class ReviewResponse(ReviewBase):
    review_id: str | None = None
    created_at: str | None = None
