import ast
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


def _run_pylint(target_path: str, cwd: str | None = None) -> dict[str, object]:
    if not _pylint_available():
        return {
            "issues": "No syntax issues found. Install pylint for deeper analysis.",
            "findings": [],
            "tool": "ast",
            "error": None,
        }

    result = subprocess.run(
        [
            "python",
            "-m",
            "pylint",
            target_path,
            "--disable=all",
            "--enable=E,W",
        ],
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    output = (result.stdout or result.stderr).strip()
    findings = _parse_pylint_output(output, target_path)

    if result.returncode != 0 and not findings and "No module named pylint" in output:
        return {
            "issues": "No syntax issues found. Install pylint for deeper analysis.",
            "findings": [],
            "tool": "ast",
            "error": None,
        }

    if not output or not _has_pylint_messages(output):
        output = "No issues found"

    return {
        "issues": output,
        "findings": findings,
        "tool": "pylint",
        "error": None,
    }


def _pylint_available() -> bool:
    try:
        result = subprocess.run(
            ["python", "-m", "pylint", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False

    return result.returncode == 0


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


def analyze_python_file(file_content: str | None = None, file_path: str | None = None):
    temp_file_path = None

    try:
        if file_path and os.path.exists(file_path):
            if not _pylint_available():
                return _analyze_with_ast(
                    Path(file_path).read_text(encoding="utf-8"),
                    file_path=file_path,
                )

            project_root = _find_project_root(file_path)
            relative_path = os.path.relpath(file_path, project_root)
            result = _run_pylint(relative_path, cwd=str(project_root))
            result["file"] = file_path
            return result

        if file_content is None:
            return {
                "file": file_path or "unknown",
                "issues": "Error running pylint: no file content or file path provided",
                "findings": [],
                "tool": "pylint",
                "error": "no file content or file path provided",
            }

        if not _pylint_available():
            return _analyze_with_ast(file_content, file_path=file_path)

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".py",
            mode="w",
            encoding="utf-8"
        ) as temp_file:

            temp_file.write(file_content)
            temp_file_path = temp_file.name

        result = _run_pylint(temp_file_path)
        result["file"] = temp_file_path
        return result

    except Exception as e:
        return {
            "file": file_path or temp_file_path or "unknown",
            "issues": f"Error running pylint: {str(e)}",
            "findings": [],
            "tool": "pylint",
            "error": str(e),
        }

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
