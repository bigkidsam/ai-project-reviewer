SEVERITY_WEIGHTS = {
    "critical": 10,
    "high": 7,
    "medium": 3,
    "low": 1,
}


def _has_issue(result: dict) -> bool:
    if result.get("findings"):
        return True

    issues = result.get("issues")
    return bool(
        issues
        and issues not in {
            "No issues found",
            "No issues found.",
            "No syntax issues found. Install pylint for deeper analysis.",
        }
    )


def calculate_metrics(results: list[dict]) -> dict[str, int | float | dict[str, int]]:
    total_files = len(results)
    files_with_errors = sum(1 for result in results if result.get("error"))
    files_with_issues = sum(1 for result in results if _has_issue(result))
    findings = [
        finding
        for result in results
        for finding in result.get("findings", [])
    ]

    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    category_counts = {
        "bug_risk": 0,
        "maintainability": 0,
        "style": 0,
        "security": 0,
    }

    for finding in findings:
        severity = str(finding.get("severity", "low"))
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

        symbol = str(finding.get("symbol", ""))
        code = str(finding.get("code", ""))

        if code.startswith("E") or symbol in {"missing-timeout", "raise-missing-from"}:
            category_counts["bug_risk"] += 1
        elif symbol in {"unused-import", "unused-argument", "unnecessary-pass"}:
            category_counts["maintainability"] += 1
        elif symbol in {"redefined-builtin", "redundant-u-string-prefix"}:
            category_counts["style"] += 1
        elif "security" in symbol:
            category_counts["security"] += 1
        else:
            category_counts["maintainability"] += 1

    penalty = sum(
        count * SEVERITY_WEIGHTS.get(severity, 1)
        for severity, count in severity_counts.items()
    )
    quality_score = max(0, 100 - penalty)
    issue_density = round(len(findings) / total_files, 2) if total_files else 0

    return {
        "total_files_analyzed": total_files,
        "files_with_issues": files_with_issues,
        "files_with_errors": files_with_errors,
        "total_findings": len(findings),
        "severity_counts": severity_counts,
        "category_counts": category_counts,
        "quality_score": quality_score,
        "issue_density_per_file": issue_density,
    }
