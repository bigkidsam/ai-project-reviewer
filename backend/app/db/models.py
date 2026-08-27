"""SQLAlchemy ORM models for database storage."""

from datetime import UTC
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class ReviewRecord(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    repo_name: Mapped[str] = mapped_column(String(200), nullable=True, index=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    weighted_total: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
    analyzed_files: Mapped[list[str]] = mapped_column(JSON, default=list)
    repository_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    fix_suggestions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    issues: Mapped[str] = mapped_column(Text, default="")
    ai_review: Mapped[str] = mapped_column(Text, default="")
    scorecard: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert ORM model to dictionary matching ReviewResponse."""
        created_str = (
            self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else str(self.created_at)
        )
        return {
            "review_id": self.id,
            "repo_url": self.repo_url,
            "analyzed_files": self.analyzed_files or [],
            "repository_metadata": self.repository_metadata or {},
            "metrics": self.metrics or {},
            "findings": self.findings or [],
            "fix_suggestions": self.fix_suggestions or [],
            "issues": self.issues or "",
            "ai_review": self.ai_review or "",
            "scorecard": self.scorecard or {},
            "created_at": created_str,
        }


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, datetime)
                else str(self.created_at)
            ),
        }

