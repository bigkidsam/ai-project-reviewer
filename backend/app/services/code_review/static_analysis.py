import ast
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

PYLINT_PATTERN = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+): "
    r"(?P<code>[A-Z]\d+): (?P<message>.+?) \((?P<symbol>[\w-]+)\)$"
)

SEVERITY_BY_PREFIX = {
    "E": "high",
    "W": "medium",
    "C": "low",
    "R": "low",
    "F": "critical",
}


def _find_project_root(file_path: str) -> Path:
    path = Path(file_path).resolve()

    for parent in [path.parent, *path.parents]:
        if any((parent / marker).exists() for marker in (".git", "pyproject.toml", "setup.py")):
            return parent

    return path.parent


def _run_subprocess(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )
    except FileNotFoundError:
        return None


def _severity_for_code(code: str) -> str:
    return SEVERITY_BY_PREFIX.get(code[:1], "low")


def _parse_pylint_output(output: str, fallback_file: str) -> list[dict[str, object]]:
    findings = []

    for line in output.splitlines():
        match = PYLINT_PATTERN.match(line.strip())

        if not match:
            continue

        data = match.groupdict()
        findings.append(
            {
                "file": data["path"] or fallback_file,
                "line": int(data["line"]),
                "column": int(data["column"]),
                "code": data["code"],
                "symbol": data["symbol"],
                "message": data["message"],
                "severity": _severity_for_code(data["code"]),
                "tool": "pylint",
            }
        )

    return findings


def _has_pylint_messages(output: str) -> bool:
    for line in output.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("*") or stripped.startswith("-"):
            continue

        if stripped.startswith("Your code has been rated at"):
            continue

        return True

    return False


@lru_cache(maxsize=1)
def _pylint_available() -> bool:
    result = _run_subprocess(["python", "-m", "pylint", "--version"])
    return bool(result and result.returncode == 0)


def _run_pylint(target_path: str, cwd: str | None = None) -> dict[str, object]:
    if not _pylint_available():
        return {
            "issues": "No issues found. Install pylint for deeper analysis.",
            "findings": [],
            "tool": "pylint",
            "error": None,
        }

    result = _run_subprocess(
        ["python", "-m", "pylint", "--exit-zero", target_path],
        cwd=cwd,
    )

    output = (result.stdout or result.stderr or "").strip() if result else ""
    
    if not _has_pylint_messages(output):
        output = "No issues found. Install pylint for deeper analysis."
    
    findings = _parse_pylint_output(output, target_path)

    return {
        "issues": output or "No issues found",
        "findings": findings,
        "tool": "pylint",
        "error": None,
    }


@lru_cache(maxsize=1)
def _bandit_available() -> bool:
    result = _run_subprocess(["python", "-m", "bandit", "--version"])
    return bool(result and result.returncode == 0)


@lru_cache(maxsize=1)
def _radon_available() -> bool:
    result = _run_subprocess(["python", "-m", "radon", "--version"])
    return bool(result and result.returncode == 0)


@lru_cache(maxsize=1)
def _eslint_available() -> bool:
    result = _run_subprocess(["npx", "--version"])
    if result and result.returncode == 0:
        return True

    result = _run_subprocess(["eslint", "--version"])
    return bool(result and result.returncode == 0)


@lru_cache(maxsize=1)
def _semgrep_available() -> bool:
    result = _run_subprocess(["python", "-m", "semgrep", "--version"])
    return bool(result and result.returncode == 0)


def _parse_bandit_output(output: str, fallback_file: str) -> list[dict[str, object]]:
    findings = []

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return findings

    for issue in data.get("results", []):
        findings.append(
            {
                "file": issue.get("filename", fallback_file),
                "line": int(issue.get("line_number", 0)),
                "column": int(issue.get("column_number", 0)),
                "code": issue.get("test_id", "B000"),
                "symbol": issue.get("test_name", "bandit_issue"),
                "message": issue.get("issue_text", "Security issue detected."),
                "severity": issue.get("issue_severity", "medium"),
                "tool": "bandit",
            }
        )

    return findings


def _run_bandit(target_path: str, cwd: str | None = None) -> dict[str, object]:
    if not _bandit_available():
        return {
            "issues": "No security analysis available. Install bandit for Python security checks.",
            "findings": [],
            "tool": "bandit",
            "error": None,
        }

    result = _run_subprocess(
        ["python", "-m", "bandit", "-f", "json", "-q", target_path],
        cwd=cwd,
    )

    output = (result.stdout or result.stderr or "").strip() if result else ""
    findings = _parse_bandit_output(output, target_path)

    if not findings and not output:
        output = "No security issues found"

    return {
        "issues": output or "No security issues found",
        "findings": findings,
        "tool": "bandit",
        "error": None,
    }


def _parse_radon_output(output: str, fallback_file: str) -> list[dict[str, object]]:
    findings = []

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return findings

    for path, blocks in data.items():
        for block in blocks:
            rank = block.get("rank", "A")
            severity = "low"
            if rank in {"D"}:
                severity = "medium"
            elif rank in {"E", "F"}:
                severity = "high"

            findings.append(
                {
                    "file": path or fallback_file,
                    "line": int(block.get("lineno", 0)),
                    "column": 0,
                    "code": str(block.get("name", "unknown")),
                    "symbol": f"radon_{rank}",
                    "message": (
                        f"Cyclomatic complexity {block.get('complexity', 0)} "
                        f"for {block.get('name', 'code block')} at rank {rank}."
                    ),
                    "severity": severity,
                    "tool": "radon",
                }
            )

    return findings


def _run_radon(target_path: str, cwd: str | None = None) -> dict[str, object]:
    if not _radon_available():
        return {
            "issues": "No complexity analysis available. Install radon for Python complexity metrics.",
            "findings": [],
            "tool": "radon",
            "error": None,
        }

    result = _run_subprocess(
        ["python", "-m", "radon", "cc", "-s", "-j", target_path],
        cwd=cwd,
    )

    output = (result.stdout or result.stderr or "").strip() if result else ""
    findings = _parse_radon_output(output, target_path)

    if not findings and not output:
        output = "No complexity issues found"

    return {
        "issues": output or "No complexity issues found",
        "findings": findings,
        "tool": "radon",
        "error": None,
    }


def _parse_eslint_output(output: str, fallback_file: str) -> list[dict[str, object]]:
    findings = []

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return findings

    for document in data:
        for message in document.get("messages", []):
            severity = "medium"
            if message.get("severity") == 2:
                severity = "high"
            elif message.get("severity") == 1:
                severity = "low"

            findings.append(
                {
                    "file": document.get("filePath", fallback_file),
                    "line": int(message.get("line", 0)),
                    "column": int(message.get("column", 0)),
                    "code": str(message.get("ruleId", "eslint_issue")),
                    "symbol": str(message.get("ruleId", "eslint_issue")),
                    "message": str(message.get("message", "ESLint issue detected.")),
                    "severity": severity,
                    "tool": "eslint",
                }
            )

    return findings


def _run_eslint(target_path: str, cwd: str | None = None) -> dict[str, object]:
    if not _eslint_available():
        return {
            "issues": "No JavaScript lint analysis available. Install ESLint for deeper JS checks.",
            "findings": [],
            "tool": "eslint",
            "error": None,
        }

    eslint_cmd = ["npx", "eslint", "--format", "json", target_path]
    if not _run_subprocess(["npx", "--version"]):
        eslint_cmd = ["eslint", "--format", "json", target_path]

    result = _run_subprocess(eslint_cmd, cwd=cwd)
    output = (result.stdout or result.stderr or "").strip() if result else ""
    findings = _parse_eslint_output(output, target_path)

    if not findings and not output:
        output = "No ESLint issues found"

    return {
        "issues": output or "No ESLint issues found",
        "findings": findings,
        "tool": "eslint",
        "error": None,
    }


def _parse_semgrep_output(output: str, fallback_file: str) -> list[dict[str, object]]:
    findings = []

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return findings

    for item in data.get("results", []):
        findings.append(
            {
                "file": item.get("path", fallback_file),
                "line": int(item.get("start", {}).get("line", 0)),
                "column": int(item.get("start", {}).get("col", 0)),
                "code": str(item.get("check_id", "SEM000")),
                "symbol": str(item.get("extra", {}).get("metadata", {}).get("ruleset", "semgrep_rule")),
                "message": str(item.get("extra", {}).get("message", "Semgrep issue detected.")),
                "severity": str(item.get("extra", {}).get("metadata", {}).get("severity", "medium")),
                "tool": "semgrep",
            }
        )

    return findings


def _run_semgrep(target_path: str, cwd: str | None = None) -> dict[str, object]:
    if not _semgrep_available():
        return {
            "issues": "No Semgrep security analysis available. Install semgrep for broader code checks.",
            "findings": [],
            "tool": "semgrep",
            "error": None,
        }

    result = _run_subprocess(
        ["python", "-m", "semgrep", "--json", "--config", "p/ci", target_path],
        cwd=cwd,
    )
    output = (result.stdout or result.stderr or "").strip() if result else ""
    findings = _parse_semgrep_output(output, target_path)

    if not findings and not output:
        output = "No Semgrep issues found"

    return {
        "issues": output or "No Semgrep issues found",
        "findings": findings,
        "tool": "semgrep",
        "error": None,
    }


def _analyze_with_ast(file_content: str, file_path: str | None = None) -> dict[str, object]:
    try:
        ast.parse(file_content)
    except SyntaxError as exc:
        finding = {
            "file": file_path or "inline-content",
            "line": exc.lineno or 0,
            "column": exc.offset or 0,
            "code": "E999",
            "symbol": "syntax-error",
            "message": exc.msg,
            "severity": "high",
            "tool": "ast",
        }

        return {
            "file": file_path or "inline-content",
            "issues": f"Syntax error on line {exc.lineno}: {exc.msg}",
            "findings": [finding],
            "tool": "ast",
            "error": None,
        }

    return {
        "file": file_path or "inline-content",
        "issues": "No syntax issues found. Install pylint for deeper analysis.",
        "findings": [],
        "tool": "ast",
        "error": None,
    }


def _merge_analysis_results(results: list[dict[str, object]], file_path: str | None = None) -> dict[str, object]:
    tools = []
    findings: list[dict[str, object]] = []
    issues: list[str] = []
    errors: list[str] = []

    for result in results:
        tools.append(result.get("tool", "unknown"))
        if result.get("issues"):
            issues.append(str(result["issues"]))
        findings.extend(result.get("findings", []))
        if result.get("error"):
            errors.append(str(result["error"]))

    return {
        "file": file_path or "unknown",
        "issues": "\n".join(issues) if issues else "No analysis issues found.",
        "findings": findings,
        "tool": "+".join(tools) if tools else "unknown",
        "error": "; ".join(errors) if errors else None,
    }


def _analyze_js_ts_rules(file_content: str, file_path: str) -> dict[str, object]:
    findings = []
    lines = file_content.splitlines()

    js_patterns = [
        (r"\beval\s*\(", "SEC-EVAL", "eval-usage", "Use of eval() is a high-risk security vulnerability.", "critical", "security"),
        (r"console\.(log|debug)\(", "STYL-LOG", "no-console", "Avoid debug console logging statements in production code.", "low", "style"),
        (r"(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]", "SEC-SECRET", "hardcoded-secret", "Possible hardcoded API key or credential detected.", "high", "security"),
        (r"var\s+[a-zA-Z_$]", "STYL-VAR", "no-var", "Use 'let' or 'const' instead of legacy 'var'.", "low", "style"),
        (r"debugger;", "STYL-DEBUGGER", "no-debugger", "Leftover 'debugger' statement detected.", "medium", "bug_risk"),
    ]

    for line_idx, line in enumerate(lines, start=1):
        for pattern, code, symbol, msg, severity, category in js_patterns:
            if re.search(pattern, line):
                findings.append({
                    "file": file_path,
                    "line": line_idx,
                    "column": 1,
                    "code": code,
                    "symbol": symbol,
                    "message": msg,
                    "severity": severity,
                    "tool": "js-analyzer",
                    "category": category,
                })

    issues = "\n".join(f"{f['file']}:{f['line']} [{f['symbol']}] {f['message']}" for f in findings) or "No JS/TS issues found."
    return {
        "file": file_path,
        "language": "javascript",
        "findings": findings,
        "issues": issues,
        "tool": "js-analyzer",
        "error": None,
    }


def _analyze_generic_rules(file_content: str, file_path: str) -> dict[str, object]:
    findings = []
    lines = file_content.splitlines()

    for line_idx, line in enumerate(lines, start=1):
        if "TODO:" in line or "FIXME:" in line:
            findings.append({
                "file": file_path,
                "line": line_idx,
                "column": 1,
                "code": "MAINT-TODO",
                "symbol": "todo-comment",
                "message": f"Unresolved maintenance note: {line.strip()[:60]}",
                "severity": "low",
                "tool": "polyglot-analyzer",
                "category": "maintainability",
            })
        if re.search(r"(?:api[_-]?key|secret|private[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]", line, re.IGNORECASE):
            findings.append({
                "file": file_path,
                "line": line_idx,
                "column": 1,
                "code": "SEC-SECRET",
                "symbol": "hardcoded-secret",
                "message": "Possible hardcoded credential or private key detected.",
                "severity": "high",
                "tool": "polyglot-analyzer",
                "category": "security",
            })

    issues = "\n".join(f"{f['file']}:{f['line']} [{f['symbol']}] {f['message']}" for f in findings) or "No issues found."
    return {
        "file": file_path,
        "language": Path(file_path).suffix.lstrip("."),
        "findings": findings,
        "issues": issues,
        "tool": "polyglot-analyzer",
        "error": None,
    }


def analyze_code_file(
    file_content: str | None = None,
    file_path: str | None = None,
    extension: str | None = None,
) -> dict[str, object]:
    temp_file_path = None
    ext = extension or (Path(file_path).suffix if file_path else None)
    ext = ext.lower() if ext else None

    try:
        if file_path and os.path.exists(file_path):
            project_root = _find_project_root(file_path)
            if ext == ".py":
                # Always check syntax first
                file_content_for_ast = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                ast_result = _analyze_with_ast(file_content_for_ast, file_path)
                # If syntax error found, return early
                if ast_result.get("findings"):
                    return ast_result
                # Otherwise continue with deeper analysis
                pylint_result = _run_pylint(os.path.relpath(file_path, project_root), cwd=str(project_root))
                pylint_result["file"] = file_path
                bandit_result = _run_bandit(file_path, cwd=str(project_root))
                radon_result = _run_radon(file_path, cwd=str(project_root))
                return _merge_analysis_results([pylint_result, bandit_result, radon_result], file_path=file_path)

            if ext in {".js", ".jsx", ".ts", ".tsx"}:
                eslint_result = _run_eslint(file_path, cwd=str(project_root))
                semgrep_result = _run_semgrep(file_path, cwd=str(project_root))
                js_content = file_content or Path(file_path).read_text(encoding="utf-8", errors="ignore")
                js_rule_result = _analyze_js_ts_rules(js_content, file_path)
                return _merge_analysis_results([eslint_result, semgrep_result, js_rule_result], file_path=file_path)

        if file_content is None:
            return {
                "file": file_path or "unknown",
                "issues": "No file content or path provided for analysis.",
                "findings": [],
                "tool": "unknown",
                "error": "no file content or file path provided",
            }

        if not ext:
            return {
                "file": file_path or "unknown",
                "issues": "Unable to determine file type for analysis.",
                "findings": [],
                "tool": "unknown",
                "error": "unknown file extension",
            }

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=ext,
            mode="w",
            encoding="utf-8",
        ) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        if ext == ".py":
            # Always check syntax first
            ast_result = _analyze_with_ast(file_content, temp_file_path)
            # If syntax error found, return early
            if ast_result.get("findings"):
                return ast_result
            # Otherwise continue with deeper analysis
            pylint_result = _run_pylint(temp_file_path)
            pylint_result["file"] = temp_file_path
            bandit_result = _run_bandit(temp_file_path)
            radon_result = _run_radon(temp_file_path)
            return _merge_analysis_results([pylint_result, bandit_result, radon_result], file_path=temp_file_path)

        if ext in {".js", ".jsx", ".ts", ".tsx"}:
            eslint_result = _run_eslint(temp_file_path)
            semgrep_result = _run_semgrep(temp_file_path)
            js_rule_result = _analyze_js_ts_rules(file_content, file_path or temp_file_path)
            return _merge_analysis_results([eslint_result, semgrep_result, js_rule_result], file_path=file_path or temp_file_path)

        # For all other source/config files (HTML, CSS, JSON, Go, Rust, C++, Java, etc.)
        generic_result = _analyze_generic_rules(file_content, file_path or temp_file_path)
        return generic_result

    except Exception as exc:
        return {
            "file": file_path or temp_file_path or "unknown",
            "issues": f"Error running analysis: {str(exc)}",
            "findings": [],
            "tool": "unknown",
            "error": str(exc),
        }

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def analyze_python_file(file_content: str | None = None, file_path: str | None = None):
    return analyze_code_file(file_content=file_content, file_path=file_path, extension=".py")


