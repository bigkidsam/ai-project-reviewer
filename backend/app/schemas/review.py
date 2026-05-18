from pydantic import AnyUrl
from pydantic import BaseModel
from pydantic import Field


class Finding(BaseModel):
    file: str
    line: int
    column: int
    code: str
    symbol: str
    message: str
    severity: str
    tool: str


class ReviewRequest(BaseModel):
    repo_url: AnyUrl
    max_files: int = Field(default=10, ge=1, le=100)


class FixSuggestion(BaseModel):
    file: str
    line: int
    column: int
    symbol: str
    problem: str
    suggested_code: str
    explanation: str
    confidence: str
    tier: str


class ReviewResponse(BaseModel):
    review_id: str | None = None
    created_at: str | None = None
    repo_url: str
    analyzed_files: list[str]
    repository_metadata: dict[str, object] = Field(default_factory=dict)
    metrics: dict[str, object]
    findings: list[Finding] = Field(default_factory=list)
    fix_suggestions: list[FixSuggestion] = Field(default_factory=list)
    issues: str
    ai_review: str
