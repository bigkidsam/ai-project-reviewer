"""Review storage service: manages database operations with JSON backup."""

import json
import logging
from datetime import UTC
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import ReviewRecord
from ..db.session import SessionLocal
from .auto_trainer import trigger_auto_training

logger = logging.getLogger(__name__)
RESULTS_DIR = settings.review_results_dir


def _parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            pass
    return datetime.now(UTC)


def save_review_result(
    review: dict[str, Any],
    db: Session | None = None,
) -> dict[str, Any]:
    """Persist a review result into the database and write a JSON backup."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    review_id = str(review.get("review_id") or uuid4())
    created_at_dt = _parse_datetime(review.get("created_at"))
    created_at_str = created_at_dt.isoformat()

    stored_review = {
        **review,
        "review_id": review_id,
        "created_at": created_at_str,
    }

    # 1. Write to database
    should_close = False
    session = db
    if session is None:
        session = SessionLocal()
        should_close = True

    try:
        metrics = stored_review.get("metrics") or {}
        scorecard = stored_review.get("scorecard") or {}
        repo_metadata = stored_review.get("repository_metadata") or {}

        record = session.scalar(select(ReviewRecord).where(ReviewRecord.id == review_id))
        if record is None:
            record = ReviewRecord(
                id=review_id,
                repo_url=str(stored_review.get("repo_url", "")),
                repo_name=str(repo_metadata.get("name", "")),
                quality_score=metrics.get("quality_score"),
                weighted_total=scorecard.get("weighted_total"),
                total_findings=int(metrics.get("total_findings", 0)),
                created_at=created_at_dt,
                analyzed_files=stored_review.get("analyzed_files") or [],
                repository_metadata=repo_metadata,
                metrics=metrics,
                findings=stored_review.get("findings") or [],
                fix_suggestions=stored_review.get("fix_suggestions") or [],
                issues=str(stored_review.get("issues", "")),
                ai_review=str(stored_review.get("ai_review", "")),
                scorecard=scorecard,
            )
            session.add(record)
        else:
            record.repo_url = str(stored_review.get("repo_url", ""))
            record.repo_name = str(repo_metadata.get("name", ""))
            record.quality_score = metrics.get("quality_score")
            record.weighted_total = scorecard.get("weighted_total")
            record.total_findings = int(metrics.get("total_findings", 0))
            record.analyzed_files = stored_review.get("analyzed_files") or []
            record.repository_metadata = repo_metadata
            record.metrics = metrics
            record.findings = stored_review.get("findings") or []
            record.fix_suggestions = stored_review.get("fix_suggestions") or []
            record.issues = str(stored_review.get("issues", ""))
            record.ai_review = str(stored_review.get("ai_review", ""))
            record.scorecard = scorecard

        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("Failed to save review to database: %s", exc)
    finally:
        if should_close:
            session.close()

    # 2. Write JSON file backup
    result_path = RESULTS_DIR / f"{review_id}.json"
    try:
        result_path.write_text(
            json.dumps(stored_review, indent=2, default=str),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Could not write JSON backup for %s: %s", review_id, exc)

    # 3. Trigger auto-training if enabled
    if settings.auto_train_enabled:
        trigger_auto_training()

    return stored_review


def get_review_result(
    review_id: str,
    db: Session | None = None,
) -> dict[str, Any] | None:
    """Retrieve a review by ID from the database with JSON fallback."""
    should_close = False
    session = db
    if session is None:
        session = SessionLocal()
        should_close = True

    try:
        record = session.scalar(select(ReviewRecord).where(ReviewRecord.id == review_id))
        if record is not None:
            return record.to_dict()
    except Exception as exc:
        logger.warning("Database query failed for %s, falling back to JSON: %s", review_id, exc)
    finally:
        if should_close:
            session.close()

    # Fallback to JSON file
    result_path = RESULTS_DIR / f"{review_id}.json"
    if result_path.exists():
        try:
            return json.loads(result_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    return None


def list_review_results(
    db: Session | None = None,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    sort_by: str = "date_desc",
) -> dict[str, Any]:
    """Return paginated review records directly from the database."""
    should_close = False
    session = db
    if session is None:
        session = SessionLocal()
        should_close = True

    try:
        query = select(ReviewRecord)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    ReviewRecord.repo_name.ilike(search_pattern),
                    ReviewRecord.repo_url.ilike(search_pattern),
                    ReviewRecord.id.ilike(search_pattern),
                )
            )

        # Apply sorting
        if sort_by == "date_asc":
            query = query.order_by(ReviewRecord.created_at.asc())
        elif sort_by == "score_desc":
            query = query.order_by(ReviewRecord.weighted_total.desc().nullslast())
        elif sort_by == "score_asc":
            query = query.order_by(ReviewRecord.weighted_total.asc().nullslast())
        elif sort_by == "findings_desc":
            query = query.order_by(ReviewRecord.total_findings.desc())
        else:
            query = query.order_by(ReviewRecord.created_at.desc())

        # Count total matching rows
        count_query = select(func.count()).select_from(query.subquery())
        total = session.scalar(count_query) or 0

        # Fetch page items
        items = session.scalars(query.offset(skip).limit(limit)).all()
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [item.to_dict() for item in items],
        }
    except Exception as exc:
        logger.error("Failed to list reviews from database: %s", exc)
        return {"total": 0, "skip": skip, "limit": limit, "items": []}
    finally:
        if should_close:
            session.close()


def delete_review_result(
    review_id: str,
    db: Session | None = None,
) -> bool:
    """Delete a review from the database and remove the JSON backup file."""
    deleted = False
    should_close = False
    session = db
    if session is None:
        session = SessionLocal()
        should_close = True

    try:
        result = session.execute(delete(ReviewRecord).where(ReviewRecord.id == review_id))
        session.commit()
        deleted = (result.rowcount or 0) > 0
    except Exception as exc:
        session.rollback()
        logger.error("Failed to delete review %s from database: %s", review_id, exc)
    finally:
        if should_close:
            session.close()

    # Also clean up JSON file
    result_path = RESULTS_DIR / f"{review_id}.json"
    if result_path.exists():
        try:
            result_path.unlink()
            deleted = True
        except Exception:
            pass

    return deleted
