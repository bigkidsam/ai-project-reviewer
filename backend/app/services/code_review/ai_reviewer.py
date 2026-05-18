import os


def _quality_label(score: int | float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 65:
        return "good"
    if score >= 40:
        return "moderate"
    return "poor"


def _top_findings(findings: list[dict], limit: int = 5) -> str:
    if not findings:
        return "No structured findings were detected."

    lines = []

    for finding in findings[:limit]:
        file_name = finding.get("file", "unknown")
        line = finding.get("line", "?")
        severity = str(finding.get("severity", "low")).upper()
        message = finding.get("message", "No message")
        symbol = finding.get("symbol", "unknown")
        lines.append(f"- {severity}: {file_name}:{line} [{symbol}] {message}")

    return "\n".join(lines)


def _generate_rule_based_review(
    metrics: dict,
    issues_text: str,
    findings: list[dict],
    repository_metadata: dict,
) -> str:
    total_files = metrics.get("total_files_analyzed", 0)
    files_with_issues = metrics.get("files_with_issues", 0)
    quality_score = metrics.get("quality_score", 0)
    quality = _quality_label(float(quality_score))
    repo_name = repository_metadata.get("name", "repository")

    if quality in {"excellent", "good"}:
        suggestion = (
            "The scanned files look healthy. Keep adding automated tests and run "
            "the reviewer in CI so regressions are caught early."
        )
    elif quality == "moderate":
        suggestion = (
            "The repository is usable, but the findings should be triaged before "
            "the codebase grows further."
        )
    else:
        suggestion = (
            "The repository needs focused cleanup. Start with high-severity "
            "findings, then improve tests and maintainability."
        )

    return f"""AI REVIEW SUMMARY

Repository: {repo_name}
Repository Quality: {quality.upper()}
Quality score: {quality_score}

Files analyzed: {total_files}
Files with issues: {files_with_issues}
Total findings: {metrics.get("total_findings", 0)}

Suggestion:
{suggestion}

Top Detected Findings:
{_top_findings(findings)}

Analyzer Output Preview:
{issues_text[:1500] or "No analyzer output."}
"""


def generate_ai_review(
    metrics: dict,
    issues_text: str,
    findings: list[dict] | None = None,
    repository_metadata: dict | None = None,
) -> str:
    """Generate a review summary.

    This function is intentionally deterministic by default so the pipeline
    works without external API credentials. A hosted LLM can be added here later
    without changing API or CLI callers.
    """
    findings = findings or []
    repository_metadata = repository_metadata or {}

    if not os.getenv("GEMINI_API_KEY"):
        return _generate_rule_based_review(
            metrics=metrics,
            issues_text=issues_text,
            findings=findings,
            repository_metadata=repository_metadata,
        )

    return _generate_rule_based_review(
        metrics=metrics,
        issues_text=issues_text,
        findings=findings,
        repository_metadata=repository_metadata,
    )
