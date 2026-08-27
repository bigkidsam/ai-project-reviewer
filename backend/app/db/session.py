"""Database engine, session factory, dependency, and auto-initialization."""

import json
import logging
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from ..core.config import settings
from .models import Base
from .models import ReviewRecord

logger = logging.getLogger(__name__)

# Ensure DB folder exists for SQLite file databases
if "sqlite" in settings.database_url:
    connect_args = {"check_same_thread": False}
    settings.db_dir.mkdir(parents=True, exist_ok=True)
else:
    connect_args = {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for request-scoped database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables and auto-migrate existing JSON review files."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")

    # Migrate any existing JSON review files into the database
    results_dir = settings.review_results_dir
    if not results_dir.exists():
        return

    with SessionLocal() as db:
        for json_file in results_dir.glob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            review_id = data.get("review_id") or json_file.stem
            existing = db.scalar(select(ReviewRecord).where(ReviewRecord.id == review_id))
            if existing is not None:
                continue

            # Parse created_at
            created_at_raw = data.get("created_at")
            if created_at_raw:
                try:
                    created_at = datetime.fromisoformat(created_at_raw)
                except Exception:
                    created_at = datetime.now(UTC)
            else:
                created_at = datetime.now(UTC)

            metrics = data.get("metrics") or {}
            scorecard = data.get("scorecard") or {}
            repo_metadata = data.get("repository_metadata") or {}

            record = ReviewRecord(
                id=review_id,
                repo_url=str(data.get("repo_url", "")),
                repo_name=str(repo_metadata.get("name", "")),
                quality_score=metrics.get("quality_score"),
                weighted_total=scorecard.get("weighted_total"),
                total_findings=int(metrics.get("total_findings", 0)),
                created_at=created_at,
                analyzed_files=data.get("analyzed_files") or [],
                repository_metadata=repo_metadata,
                metrics=metrics,
                findings=data.get("findings") or [],
                fix_suggestions=data.get("fix_suggestions") or [],
                issues=str(data.get("issues", "")),
                ai_review=str(data.get("ai_review", "")),
                scorecard=scorecard,
            )
            db.add(record)

        try:
            db.commit()
            logger.info("Migrated existing JSON reviews to the database.")
        except Exception as exc:
            db.rollback()
            logger.warning("Failed to commit migrated reviews: %s", exc)
