"""Tests for database layer, models, session, and DB CRUD."""

import unittest
from datetime import UTC
from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import Base
from backend.app.db.models import ReviewRecord
from backend.app.services.review_store import delete_review_result
from backend.app.services.review_store import get_review_result
from backend.app.services.review_store import list_review_results
from backend.app.services.review_store import save_review_result
from backend.app.training.data_loader import load_review_results_from_db


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        # In-memory SQLite engine for tests
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_create_and_get_review(self):
        review_id = str(uuid4())
        review_data = {
            "review_id": review_id,
            "repo_url": "https://github.com/example/repo",
            "analyzed_files": ["app.py"],
            "repository_metadata": {"name": "repo"},
            "metrics": {
                "quality_score": 90.0,
                "total_findings": 2,
                "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 1},
                "category_counts": {"bug_risk": 0, "maintainability": 1, "style": 1, "security": 0},
            },
            "findings": [{"file": "app.py", "line": 10, "message": "Test issue"}],
            "fix_suggestions": [],
            "issues": "Sample log",
            "ai_review": "Looking good",
            "scorecard": {"weighted_total": 85.5, "categories": {}},
            "created_at": datetime.now(UTC).isoformat(),
        }

        saved = save_review_result(review_data, db=self.db)
        self.assertEqual(saved["review_id"], review_id)

        # Retrieve
        fetched = get_review_result(review_id, db=self.db)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["repo_url"], "https://github.com/example/repo")
        self.assertEqual(fetched["metrics"]["quality_score"], 90.0)
        self.assertEqual(fetched["scorecard"]["weighted_total"], 85.5)

    def test_list_and_search_reviews(self):
        # Insert 3 reviews
        for i, name in enumerate(["alpha_project", "beta_service", "gamma_alpha"]):
            review_data = {
                "review_id": f"rev-{i}",
                "repo_url": f"https://github.com/org/{name}",
                "repository_metadata": {"name": name},
                "metrics": {"quality_score": 70.0 + (i * 10), "total_findings": i},
                "scorecard": {"weighted_total": 70.0 + (i * 10)},
                "created_at": datetime.now(UTC).isoformat(),
            }
            save_review_result(review_data, db=self.db)

        # List all
        res = list_review_results(db=self.db, skip=0, limit=10)
        self.assertEqual(res["total"], 3)
        self.assertEqual(len(res["items"]), 3)

        # Search for 'alpha'
        search_res = list_review_results(db=self.db, search="alpha")
        self.assertEqual(search_res["total"], 2)

    def test_delete_review(self):
        review_id = "to-delete-123"
        review_data = {
            "review_id": review_id,
            "repo_url": "https://github.com/org/temp",
            "created_at": datetime.now(UTC).isoformat(),
        }
        save_review_result(review_data, db=self.db)

        deleted = delete_review_result(review_id, db=self.db)
        self.assertTrue(deleted)

        fetched = get_review_result(review_id, db=self.db)
        self.assertIsNone(fetched)

    def test_load_dataset_from_db(self):
        review_data = {
            "review_id": "rev-ml-1",
            "repo_url": "https://github.com/org/ml-repo",
            "metrics": {
                "quality_score": 88.0,
                "total_findings": 3,
                "severity_counts": {"critical": 0, "high": 0, "medium": 1, "low": 2},
                "category_counts": {"bug_risk": 0, "maintainability": 1, "style": 2, "security": 0},
            },
            "created_at": datetime.now(UTC).isoformat(),
        }
        save_review_result(review_data, db=self.db)

        df = load_review_results_from_db(db=self.db)
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["label"], "excellent")
