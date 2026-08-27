import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ReviewRecord
from ..db.session import SessionLocal


def _quality_label(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 65:
        return "good"
    if score >= 40:
        return "moderate"
    return "poor"


def _flatten_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    severity = metrics.get("severity_counts", {}) or {}
    category = metrics.get("category_counts", {}) or {}

    for label in ("critical", "high", "medium", "low"):
        row[f"severity_{label}"] = int(severity.get(label, 0))

    for label in ("bug_risk", "maintainability", "style", "security"):
        row[f"category_{label}"] = int(category.get(label, 0))

    row["total_files_analyzed"] = int(metrics.get("total_files_analyzed", 0))
    row["total_findings"] = int(metrics.get("total_findings", 0))
    row["files_with_issues"] = int(metrics.get("files_with_issues", 0))
    row["files_with_errors"] = int(metrics.get("files_with_errors", 0))
    row["quality_score"] = float(metrics.get("quality_score", 0))
    row["issue_density_per_file"] = float(metrics.get("issue_density_per_file", 0))
    return row


def load_review_results_from_db(db: Session | None = None) -> pd.DataFrame:
    """Load review results directly from the database table."""
    should_close = False
    session = db
    if session is None:
        session = SessionLocal()
        should_close = True

    try:
        records = session.scalars(select(ReviewRecord)).all()
        rows: list[dict[str, Any]] = []

        for record in records:
            metrics = record.metrics or {}
            row = _flatten_metrics(metrics)
            row["review_id"] = record.id
            row["repo_url"] = record.repo_url or ""
            row["label"] = _quality_label(row["quality_score"])
            row["findings_count"] = len(record.findings or [])
            row["issues_text_len"] = len(str(record.issues or ""))
            rows.append(row)

        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()
    finally:
        if should_close:
            session.close()


def load_review_results_dir(results_dir: str | Path) -> pd.DataFrame:
    """Load review results from JSON files on disk with DB integration."""
    # First try loading from DB
    df_db = load_review_results_from_db()
    if not df_db.empty:
        return df_db

    results_path = Path(results_dir)
    rows: list[dict[str, Any]] = []

    if results_path.exists():
        for result_file in results_path.glob("*.json"):
            try:
                data = json.loads(result_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue

            metrics = data.get("metrics", {}) or {}
            row = _flatten_metrics(metrics)
            row["review_id"] = data.get("review_id")
            row["repo_url"] = data.get("repo_url", "")
            row["label"] = _quality_label(row["quality_score"])
            row["findings_count"] = len(data.get("findings", []))
            row["issues_text_len"] = len(str(data.get("issues", "")))
            rows.append(row)

    return pd.DataFrame(rows)
