from typing import Any

CATEGORY_WEIGHTS = {
    "code_quality": 20,
    "architecture": 15,
    "documentation": 10,
    "security": 15,
    "performance": 10,
    "ui_ux": 10,
    "innovation": 10,
    "testing": 10,
}


def _clamp(score: float) -> float:
    return max(0.0, min(100.0, score))


def _score_code_quality(metrics: dict[str, Any]) -> float:
    return float(metrics.get("quality_score", 0.0))


def _score_architecture(metadata: dict[str, Any]) -> float:
    score = 0.0
    if metadata.get("has_backend") or metadata.get("python_files", 0) > 0:
        score += 40.0
    if metadata.get("has_frontend") or metadata.get("frontend_file_count", 0) > 0:
        score += 30.0
    if metadata.get("has_docs"):
        score += 15.0
    if metadata.get("test_file_count", 0) > 0:
        score += 15.0
    return _clamp(score)


def _score_documentation(metadata: dict[str, Any]) -> float:
    score = 0.0
    if metadata.get("has_readme"):
        score += 50.0
    if metadata.get("has_docs"):
        score += 30.0
    if metadata.get("readme_length", 0) >= 200:
        score += 20.0
    return _clamp(score)


def _score_security(metrics: dict[str, Any], findings: list[dict[str, Any]]) -> float:
    security_count = int(metrics.get("category_counts", {}).get("security", 0))
    if security_count == 0:
        return 100.0

    penalty = min(security_count * 15, 100)
    return _clamp(100.0 - penalty)


def _score_performance(metrics: dict[str, Any], findings: list[dict[str, Any]]) -> float:
    complexity_issues = sum(
        1
        for finding in findings
        if finding.get("tool") == "radon" or "complexity" in str(finding.get("message", "")).lower()
    )
    if complexity_issues == 0:
        return 100.0

    penalty = min(complexity_issues * 20, 100)
    return _clamp(100.0 - penalty)


def _score_ui_ux(metadata: dict[str, Any]) -> float:
    if metadata.get("has_frontend") or metadata.get("frontend_file_count", 0) > 0:
        return 100.0
    return 10.0


def _score_innovation(metadata: dict[str, Any]) -> float:
    score = 0.0
    if metadata.get("has_ml_code"):
        score += 40.0
    if metadata.get("has_ai_code"):
        score += 40.0
    if metadata.get("has_novel_structure"):
        score += 20.0
    return _clamp(score)


def _score_testing(metadata: dict[str, Any]) -> float:
    count = int(metadata.get("test_file_count", 0))
    if count >= 10:
        return 100.0
    return _clamp((count / 10.0) * 100.0)


def calculate_scorecard(
    metrics: dict[str, Any],
    metadata: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    scores = {
        "code_quality": _score_code_quality(metrics),
        "architecture": _score_architecture(metadata),
        "documentation": _score_documentation(metadata),
        "security": _score_security(metrics, findings),
        "performance": _score_performance(metrics, findings),
        "ui_ux": _score_ui_ux(metadata),
        "innovation": _score_innovation(metadata),
        "testing": _score_testing(metadata),
    }

    weighted_total = sum(
        scores[key] * CATEGORY_WEIGHTS[key] / 100.0
        for key in CATEGORY_WEIGHTS
    )

    return {
        "categories": {
            key: {
                "score": round(scores[key], 1),
                "weight": CATEGORY_WEIGHTS[key],
            }
            for key in scores
        },
        "weighted_total": round(weighted_total, 2),
    }
