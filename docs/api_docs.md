# API Docs

## Health Check

`GET /`

Response:

```json
{
  "status": "ok",
  "service": "ai-project-reviewer"
}
```

## Review Repository

`POST /review`

Request:

```json
{
  "repo_url": "https://github.com/psf/requests",
  "max_files": 10
}
```

Response:

```json
{
  "repo_url": "https://github.com/psf/requests",
  "analyzed_files": ["..."],
  "repository_metadata": {
    "name": "requests",
    "has_readme": true,
    "has_pyproject": true,
    "has_requirements": true,
    "has_tests": true
  },
  "metrics": {
    "total_files_analyzed": 10,
    "files_with_issues": 8,
    "files_with_errors": 0,
    "total_findings": 42,
    "severity_counts": {
      "critical": 0,
      "high": 3,
      "medium": 28,
      "low": 11
    },
    "quality_score": 0,
    "issue_density_per_file": 4.2
  },
  "findings": [
    {
      "file": "src/example.py",
      "line": 10,
      "column": 4,
      "code": "W0611",
      "symbol": "unused-import",
      "message": "Unused import os",
      "severity": "medium",
      "tool": "pylint"
    }
  ],
  "issues": "...",
  "ai_review": "..."
}
```
