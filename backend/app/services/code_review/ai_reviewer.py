import json
import time

from ...core.config import settings
from ...training.model_predictor import predict_quality_label


MAX_ISSUES_CHARS = 6000
MAX_FINDINGS = 20


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


def _safe_json(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def _build_llm_prompt(
    metrics: dict,
    issues_text: str,
    findings: list[dict],
    repository_metadata: dict,
    model_prediction: str | None,
) -> str:
    repo_name = repository_metadata.get("name", "repository")
    prompt_payload = {
        "repository": repository_metadata,
        "metrics": metrics,
        "local_quality_model_prediction": model_prediction,
        "top_findings": findings[:MAX_FINDINGS],
        "analyzer_output_preview": issues_text[:MAX_ISSUES_CHARS],
    }

    return f"""You are a senior software engineer reviewing a Python repository.

Write a practical, concise code review for the repository named "{repo_name}".
Use the metrics and analyzer findings as evidence. Do not invent files, line
numbers, dependencies, or vulnerabilities that are not present in the input.

Return the review in this exact structure:

AI REVIEW SUMMARY

Repository Quality:

Most Important Findings:

Recommended Fix Order:

Testing Recommendations:

Final Notes:

Input data:
{_safe_json(prompt_payload)}
"""


def _generate_gemini_review(
    prompt: str,
    api_key: str,
    model: str,
) -> str | None:
    try:
        from google import genai
    except ImportError:
        return None
    # Attempt the generation with retries/backoff for transient failures
    max_attempts = 3
    delay = 1
    for attempt in range(1, max_attempts + 1):
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            text = getattr(response, "text", None)
            if text:
                return str(text).strip()
            # If no text returned, treat as transient and retry
            raise RuntimeError("Empty response from LLM")
        except Exception:
            if attempt == max_attempts:
                return None
            time.sleep(delay)
            delay *= 2


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

    This function prefers Gemini when configured, includes the local quality
    classifier's prediction as context, and falls back to a deterministic
    summary when the external LLM is unavailable.
    """
    findings = findings or []
    repository_metadata = repository_metadata or {}

    quality_label = predict_quality_label(metrics)
    fallback_summary = _generate_rule_based_review(
        metrics=metrics,
        issues_text=issues_text,
        findings=findings,
        repository_metadata=repository_metadata,
    )

    if settings.use_external_llm and settings.gemini_api_key:
        prompt = _build_llm_prompt(
            metrics=metrics,
            issues_text=issues_text,
            findings=findings,
            repository_metadata=repository_metadata,
            model_prediction=quality_label,
        )
        llm_review = _generate_gemini_review(
            prompt=prompt,
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
        if llm_review:
            if quality_label:
                return (
                    llm_review
                    + f"\n\nLOCAL MODEL PREDICTION: repository quality appears to be {quality_label.upper()}."
                )
            return llm_review

    if quality_label:
        return (
            fallback_summary
            + f"\n\nLOCAL MODEL PREDICTION: repository quality appears to be {quality_label.upper()}."
        )

    return fallback_summary
