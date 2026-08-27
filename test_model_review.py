#!/usr/bin/env python
"""Test integrated tools + model approach."""

from backend.app.services.code_review.reviewer import run_bundle_review

print("Testing Integrated Tools + Model Review...")
print("=" * 60)

# Test with a simple local bundle
test_bundle = {
    "metadata": {
        "name": "test-repo",
        "path": "/test",
        "has_readme": True,
        "has_tests": True,
        "has_frontend": False,
        "test_file_count": 3,
        "python_file_count": 5,
    },
    "files": [
        {"file": "main.py", "relative_path": "main.py", "content": "def hello(): pass"},
        {"file": "utils.py", "relative_path": "utils.py", "content": "def add(a,b): return a+b"},
        {"file": "test_main.py", "relative_path": "test_main.py", "content": "def test(): pass"},
    ]
}

result = run_bundle_review(test_bundle, max_files=10)

print('\n[OK] Review completed!\n')
print(f'Quality Score (from tools): {result["metrics"]["quality_score"]}')
print(f'Total Findings: {len(result["findings"])}')
print(f'Scorecard Weighted Total: {result["scorecard"]["weighted_total"]}')
print('\nIssues Found:')
print(result["issues"][:300])
print('\n\nAI Review (with Model Prediction):')
print(result["ai_review"][:600])
print("\n" + "=" * 60)
print("[OK] System: Tools extract metrics -> Model predicts quality -> Data saved for retraining")


