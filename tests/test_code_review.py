import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.services.code_review.ai_reviewer import generate_ai_review
from backend.app.services.code_review import ai_reviewer
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

    def test_polyglot_analysis_analyzes_javascript_and_generic_files(self):
        from backend.app.services.code_review.static_analysis import analyze_code_file

        js_result = analyze_code_file("console.log('test'); eval('2+2');", file_path="app.js")
        self.assertIn("js-analyzer", js_result["tool"])
        self.assertTrue(len(js_result["findings"]) >= 2)

        generic_result = analyze_code_file("// TODO: fix later\napi_key = '123456789';", file_path="config.go")
        self.assertEqual(generic_result["tool"], "polyglot-analyzer")
        self.assertTrue(len(generic_result["findings"]) >= 2)




class AiReviewerTests(unittest.TestCase):
    def test_rule_based_review_accepts_findings_and_metadata(self):
        with patch.object(ai_reviewer.settings, "use_external_llm", False):
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

    def test_gemini_review_is_used_when_configured(self):
        with (
            patch.object(ai_reviewer.settings, "use_external_llm", True),
            patch.object(ai_reviewer.settings, "gemini_api_key", "test-key"),
            patch.object(ai_reviewer.settings, "gemini_model", "test-model"),
            patch(
                "backend.app.services.code_review.ai_reviewer._generate_gemini_review",
                return_value="AI REVIEW SUMMARY\n\nRepository Quality:\nGood",
            ) as generate_gemini_review,
            patch(
                "backend.app.services.code_review.ai_reviewer.predict_quality_label",
                return_value=None,
            ),
        ):
            review = generate_ai_review(
                metrics={
                    "total_files_analyzed": 1,
                    "files_with_issues": 0,
                    "total_findings": 0,
                    "quality_score": 95,
                },
                issues_text="",
                findings=[],
                repository_metadata={"name": "sample"},
            )

        self.assertIn("Repository Quality:\nGood", review)
        generate_gemini_review.assert_called_once()


class ScoringTests(unittest.TestCase):
    def test_calculate_scorecard_applies_weights_and_categories(self):
        metrics = {
            "total_files_analyzed": 2,
            "files_with_issues": 1,
            "total_findings": 1,
            "quality_score": 80,
            "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
            "category_counts": {"security": 1},
        }
        metadata = {
            "has_readme": True,
            "readme_length": 250,
            "has_docs": True,
            "has_frontend": True,
            "frontend_file_count": 2,
            "test_file_count": 1,
            "has_ml_code": False,
            "has_ai_code": False,
            "has_novel_structure": False,
        }
        findings = [
            {
                "tool": "bandit",
                "message": "Potential security issue detected.",
                "severity": "high",
                "symbol": "security_issue",
            }
        ]

        from backend.app.services.scoring import calculate_scorecard

        scorecard = calculate_scorecard(metrics, metadata, findings)

        self.assertIn("categories", scorecard)
        self.assertIn("weighted_total", scorecard)
        self.assertEqual(scorecard["categories"]["documentation"]["weight"], 10)
        self.assertGreaterEqual(scorecard["weighted_total"], 0)


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
        self.assertIn("scorecard", review)
        self.assertIn("weighted_total", review["scorecard"])


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

    def test_save_review_respects_auto_train_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("backend.app.services.review_store.RESULTS_DIR", Path(temp_dir)),
                patch("backend.app.services.review_store.settings.auto_train_enabled", False),
                patch("backend.app.services.review_store.trigger_auto_training") as trigger_mock,
            ):
                save_review_result(
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
                trigger_mock.assert_not_called()

            with (
                patch("backend.app.services.review_store.RESULTS_DIR", Path(temp_dir)),
                patch("backend.app.services.review_store.settings.auto_train_enabled", True),
                patch("backend.app.services.review_store.trigger_auto_training") as trigger_mock,
            ):
                save_review_result(
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
                trigger_mock.assert_called_once()


class AutoTrainerTests(unittest.TestCase):
    def test_auto_trainer_lock_skips_when_busy(self):
        from backend.app.services.auto_trainer import _TRAINING_LOCK, _retrain_model

        with (
            patch("backend.app.services.auto_trainer.train_quality_classifier") as train_mock,
            _TRAINING_LOCK,
        ):
            # When lock is already held, _retrain_model should return without calling train
            _retrain_model()
            train_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
