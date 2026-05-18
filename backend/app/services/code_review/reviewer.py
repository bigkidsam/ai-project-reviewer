from .ai_reviewer import generate_ai_review
from .fix_suggester import generate_fix_suggestions
from .github_fetcher import fetch_repository_bundle
from .metrics import calculate_metrics
from .static_analysis import analyze_python_file


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

        if not str(file_data["file"]).endswith(".py"):
            skipped_files += 1
            continue

        result = analyze_python_file(
            file_content=str(file_data["content"]),
            file_path=str(file_data["file"]),
        )
        results.append(result)
        analyzed_files.append(str(file_data.get("relative_path") or file_data["file"]))

    metrics = calculate_metrics(results)
    metrics["total_code_files_fetched"] = len(files)
    metrics["skipped_files_before_limit"] = skipped_files

    issues = "\n".join(str(result.get("issues", "")) for result in results)
    findings = [
        finding
        for result in results
        for finding in result.get("findings", [])
    ]
    ai_review = generate_ai_review(
        metrics=metrics,
        issues_text=issues,
        findings=findings,
        repository_metadata=repository_metadata,
    )
    fix_suggestions = generate_fix_suggestions(findings)

    return {
        "repo_url": repo_url,
        "analyzed_files": analyzed_files,
        "repository_metadata": repository_metadata,
        "metrics": metrics,
        "findings": findings,
        "fix_suggestions": fix_suggestions,
        "issues": issues,
        "ai_review": ai_review,
    }
