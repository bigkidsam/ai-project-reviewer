from pathlib import Path


def _read_file_lines(file_path: str) -> list[str]:
    try:
        return Path(file_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def _build_suggestion(
    finding: dict,
    suggested_code: str,
    explanation: str,
    confidence: str,
    tier: str,
) -> dict[str, object]:
    return {
        "file": finding.get("file", ""),
        "line": int(finding.get("line", 0)),
        "column": int(finding.get("column", 0)),
        "symbol": str(finding.get("symbol", "")),
        "problem": str(finding.get("message", "")),
        "suggested_code": suggested_code,
        "explanation": explanation,
        "confidence": confidence,
        "tier": tier,
    }


def _rule_based_fix(finding: dict) -> dict[str, object] | None:
    symbol = str(finding.get("symbol", ""))
    lines = _read_file_lines(str(finding.get("file", "")))
    line_idx = int(finding.get("line", 1)) - 1
    current_line = lines[line_idx] if 0 <= line_idx < len(lines) else ""

    if symbol == "unused-import" and current_line.strip().startswith(("import ", "from ")):
        return _build_suggestion(
            finding=finding,
            suggested_code="# remove this unused import",
            explanation="Pylint marked this import as unused. Remove it or use it.",
            confidence="high",
            tier="rule_based",
        )

    if symbol == "missing-timeout" and "timeout=" not in current_line:
        patched = f"{current_line.rstrip(')')}, timeout=10)" if ")" in current_line else current_line
        return _build_suggestion(
            finding=finding,
            suggested_code=patched,
            explanation="Network calls should define timeout to avoid hanging requests.",
            confidence="high",
            tier="rule_based",
        )

    return None


def _llm_style_placeholder(finding: dict) -> dict[str, object]:
    return _build_suggestion(
        finding=finding,
        suggested_code="",
        explanation=(
            "Complex issue detected. Generate patch with LLM and validate by re-running "
            "lint/tests before applying."
        ),
        confidence="medium",
        tier="model_guided",
    )


def generate_fix_suggestions(findings: list[dict]) -> list[dict[str, object]]:
    suggestions: list[dict[str, object]] = []

    for finding in findings:
        suggestion = _rule_based_fix(finding)
        if suggestion is not None:
            suggestions.append(suggestion)
            continue

        suggestions.append(_llm_style_placeholder(finding))

    return suggestions
