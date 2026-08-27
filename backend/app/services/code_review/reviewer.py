from .ai_reviewer import generate_ai_review
from .fix_suggester import generate_fix_suggestions
from .github_fetcher import fetch_repository_bundle
from .metrics import calculate_metrics
from ..scoring import calculate_scorecard
from .static_analysis import analyze_code_file, analyze_python_file
from ...models.review import ReviewResponse
from ...training.model_predictor import predict_quality_label

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".html", ".css", ".json", ".yaml", ".yml",
    ".go", ".java", ".rs", ".cpp", ".c", ".h", ".md"
}


def _is_analyzable_file(file_path: str) -> bool:
    path_lower = file_path.lower()
    if any(ignore in path_lower for ignore in ["node_modules/", "dist/", "build/", "vendor/", ".git/", "package-lock.json"]):
        return False
    return any(path_lower.endswith(ext) for ext in SUPPORTED_EXTENSIONS)


def _dump_review_response(review_data: dict[str, object]) -> dict[str, object]:
    response = ReviewResponse(**review_data)
    if hasattr(response, "model_dump"):
        return response.model_dump()
    return response.dict()


def run_repository_review(repo_url: str, max_files: int = 10) -> dict[str, object]:
    repository = fetch_repository_bundle(repo_url)
    files = repository["files"]
    repository_metadata = repository["metadata"]
    results = []
    analyzed_files = []
    skipped_files = 0

    for file_data in files:
        if len(results) >= max_files:
            break

        file_name = str(file_data.get("file", ""))
        if not _is_analyzable_file(file_name):
            skipped_files += 1
            continue

        result = analyze_code_file(
            file_content=str(file_data.get("content", "")),
            file_path=file_name,
        )
        results.append(result)
        analyzed_files.append(str(file_data.get("relative_path") or file_name))

    metrics = calculate_metrics(results)
    metrics["total_code_files_fetched"] = len(files)
    metrics["skipped_files_before_limit"] = skipped_files

    issues = "\n".join(str(result.get("issues", "")) for result in results)
    findings = [
        finding
        for result in results
        for finding in result.get("findings", [])
    ]

    metrics["findings_count"] = len(findings)
    metrics["issues_text_len"] = len(issues)

    # Generate ML Quality Model Prediction
    predicted_label = predict_quality_label(metrics)
    if predicted_label:
        metrics["predicted_quality_label"] = predicted_label

    ai_review = generate_ai_review(
        metrics=metrics,
        issues_text=issues,
        findings=findings,
        repository_metadata=repository_metadata,
    )
    
    fix_suggestions = generate_fix_suggestions(findings)
    scorecard = calculate_scorecard(metrics, repository_metadata, findings)

    if predicted_label:
        scorecard["predicted_quality_label"] = predicted_label

    review_data = {
        "repo_url": repo_url,
        "analyzed_files": analyzed_files,
        "repository_metadata": repository_metadata,
        "metrics": metrics,
        "findings": findings,
        "fix_suggestions": fix_suggestions,
        "issues": issues,
        "ai_review": ai_review,
        "scorecard": scorecard,
    }

    return _dump_review_response(review_data)


def run_bundle_review(bundle: dict[str, object], max_files: int = 10) -> dict[str, object]:
    """Run review pipeline on a pre-built bundle.

    `bundle` should be a dict with `metadata` and `files` keys.
    Runs tools to extract metrics, then uses model to predict quality.
    """
    files = bundle.get("files", [])
    repository_metadata = bundle.get("metadata", {})
    results = []
    analyzed_files = []
    skipped_files = 0

    for file_data in files:
        if len(results) >= max_files:
            break

        file_name = str(file_data.get("file", ""))
        if not _is_analyzable_file(file_name):
            skipped_files += 1
            continue

        result = analyze_code_file(
            file_content=str(file_data.get("content", "")),
            file_path=file_name,
        )
        results.append(result)
        analyzed_files.append(str(file_data.get("relative_path") or file_name))


    metrics = calculate_metrics(results)
    metrics["total_code_files_fetched"] = len(files)
    metrics["skipped_files_before_limit"] = skipped_files

    issues = "\n".join(str(result.get("issues", "")) for result in results)
    findings = [
        finding
        for result in results
        for finding in result.get("findings", [])
    ]

    metrics["findings_count"] = len(findings)
    metrics["issues_text_len"] = len(issues)

    # Generate ML Quality Model Prediction
    predicted_label = predict_quality_label(metrics)
    if predicted_label:
        metrics["predicted_quality_label"] = predicted_label

    ai_review = generate_ai_review(
        metrics=metrics,
        issues_text=issues,
        findings=findings,
        repository_metadata=repository_metadata,
    )
    
    fix_suggestions = generate_fix_suggestions(findings)
    scorecard = calculate_scorecard(metrics, repository_metadata, findings)

    if predicted_label:
        scorecard["predicted_quality_label"] = predicted_label

    review_data = {
        "repo_url": repository_metadata.get("path", "local-bundle"),
        "analyzed_files": analyzed_files,
        "repository_metadata": repository_metadata,
        "metrics": metrics,
        "findings": findings,
        "fix_suggestions": fix_suggestions,
        "issues": issues,
        "ai_review": ai_review,
        "scorecard": scorecard,
    }

    return _dump_review_response(review_data)

