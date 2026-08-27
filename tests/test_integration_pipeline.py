import json
from pathlib import Path

import pytest


def make_sample_bundle(include_path: bool = True):
    metadata = {"default_branch": "main"}
    if include_path:
        metadata["path"] = "git@github.com:example/repo.git"

    return {
        "metadata": metadata,
        "files": [
            {"file": "src/module.py", "relative_path": "src/module.py", "content": "def add(a, b):\n    return a + b\n"},
            {"file": "README.md", "relative_path": "README.md", "content": "# Example"},
        ],
    }


def test_run_bundle_review_local(monkeypatch):
    from backend.app.services.code_review.reviewer import run_bundle_review

    # Replace AI reviewer to keep test deterministic
    monkeypatch.setattr(
        "backend.app.services.code_review.reviewer.generate_ai_review",
        lambda metrics, issues_text, findings, repository_metadata: "AI_SUMMARY_PLACEHOLDER",
    )

    # Use a bundle without metadata path so run_bundle_review uses the local-bundle default
    bundle = make_sample_bundle(include_path=False)
    review = run_bundle_review(bundle, max_files=5)

    assert isinstance(review, dict)
    assert review["repo_url"] == "local-bundle"
    assert "metrics" in review
    assert review["ai_review"] == "AI_SUMMARY_PLACEHOLDER"


def test_run_repository_review_with_mocked_fetch(monkeypatch):
    from backend.app.services.code_review import reviewer as reviewer_mod

    sample = make_sample_bundle()

    # Mock fetch_repository_bundle used by run_repository_review
    monkeypatch.setattr(reviewer_mod, "fetch_repository_bundle", lambda url: sample)

    # Mock ai reviewer
    monkeypatch.setattr(
        reviewer_mod,
        "generate_ai_review",
        lambda metrics, issues_text, findings, repository_metadata: "ok",
    )

    review = reviewer_mod.run_repository_review("git@github.com:fake/repo.git", max_files=3)

    assert review["repo_url"] == "git@github.com:fake/repo.git"
    assert "metrics" in review
    assert isinstance(review["ai_review"], str)
