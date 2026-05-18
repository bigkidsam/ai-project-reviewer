import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.services.code_review.ai_reviewer import generate_ai_review
from backend.app.services.code_review.metrics import calculate_metrics
from backend.app.services.code_review.reviewer import run_repository_review
from backend.app.services.code_review.static_analysis import analyze_python_file
from backend.app.services.review_store import get_review_result
from backend.app.services.review_store import save_review_result


class MetricsTests(unittest.TestCase):
    def test_calculate_metrics_counts_findings_by_severity_and_category(self):
        results = [
            {
                "findings": [
                    {
                        "code": "E1101",
                        "symbol": "no-member",
                        "severity": "high",
                    },
                    {
                        "code": "W0611",
                        "symbol": "unused-import",
                        "severity": "medium",
                    },
                ]
            }
        ]

        metrics = calculate_metrics(results)

        self.assertEqual(metrics["total_files_analyzed"], 1)
        self.assertEqual(metrics["files_with_issues"], 1)
        self.assertEqual(metrics["total_findings"], 2)
        self.assertEqual(metrics["severity_counts"]["high"], 1)
        self.assertEqual(metrics["severity_counts"]["medium"], 1)
        self.assertLess(metrics["quality_score"], 100)


class StaticAnalysisTests(unittest.TestCase):
    def test_ast_fallback_reports_syntax_error_without_pylint(self):
        with patch(
            "backend.app.services.code_review.static_analysis._pylint_available",
            return_value=False,
        ):
            result = analyze_python_file("def broken(:\n    pass\n")

        self.assertEqual(result["tool"], "ast")
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("Syntax error", result["issues"])


class AiReviewerTests(unittest.TestCase):
    def test_rule_based_review_accepts_findings_and_metadata(self):
        review = generate_ai_review(
            metrics={
                "total_files_analyzed": 1,
                "files_with_issues": 0,
                "total_findings": 0,
                "quality_score": 100,
            },
            issues_text="",
            findings=[],
            repository_metadata={"name": "sample"},
        )

        self.assertIn("Repository: sample", review)
        self.assertIn("Repository Quality: EXCELLENT", review)


class PipelineTests(unittest.TestCase):
    def test_run_repository_review_uses_shared_pipeline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            sample = repo_path / "sample.py"
            sample.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

            bundle = {
                "metadata": {"name": "sample"},
                "files": [
                    {
                        "file": str(sample),
                        "relative_path": "sample.py",
                        "content": sample.read_text(encoding="utf-8"),
                    }
                ],
            }

            with patch(
                "backend.app.services.code_review.reviewer.fetch_repository_bundle",
                return_value=bundle,
            ):
                review = run_repository_review("https://example.com/sample.git")

        self.assertEqual(review["metrics"]["total_files_analyzed"], 1)
        self.assertEqual(review["analyzed_files"], ["sample.py"])
        self.assertIn("ai_review", review)
        self.assertIn("fix_suggestions", review)


class ReviewStoreTests(unittest.TestCase):
    def test_save_and_get_review_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("backend.app.services.review_store.RESULTS_DIR", Path(temp_dir)):
                stored = save_review_result(
                    {
                        "repo_url": "https://example.com/sample.git",
                        "analyzed_files": [],
                        "repository_metadata": {},
                        "metrics": {},
                        "findings": [],
                        "issues": "",
                        "ai_review": "ok",
                    }
                )

                loaded = get_review_result(stored["review_id"])

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["review_id"], stored["review_id"])
        self.assertEqual(loaded["ai_review"], "ok")


if __name__ == "__main__":
    unittest.main()
