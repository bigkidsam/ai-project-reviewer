import logging
import os
from pathlib import Path
import shutil
import stat
import time


from git import GitCommandError
from git import Repo

from ...core.config import settings

logger = logging.getLogger(__name__)

TEMP_DIR = settings.temp_repos_dir
SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".java"}
SKIP_DIRS = {
    ".git",
    ".github",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
MAX_FILE_SIZE_BYTES = 250_000


def _force_rmtree(path: Path) -> None:

    """Robust directory remover that clears read-only attributes on Windows."""
    def on_rm_error(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass

    if path.exists():
        try:
            shutil.rmtree(str(path), onerror=on_rm_error)
        except Exception as exc:
            logger.warning("Could not cleanly remove directory %s: %s", path, exc)


def clone_repo(repo_url: str) -> str:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    repo_path = TEMP_DIR / repo_name

    if repo_path.exists():
        try:
            repo = Repo(str(repo_path))
            repo.remotes.origin.fetch(depth=1)
            return str(repo_path)
        except Exception:
            logger.warning("Existing repo %s is invalid or fetch failed; removing for fresh clone", repo_name)
            _force_rmtree(repo_path)

    # Attempt clone with clean retries and exponential backoff
    max_attempts = 3
    delay = 1
    last_exc = None

    for attempt in range(1, max_attempts + 1):
        try:
            _force_rmtree(repo_path)
            Repo.clone_from(repo_url, str(repo_path), depth=1)
            return str(repo_path)
        except GitCommandError as exc:
            last_exc = exc
            logger.warning("Clone attempt %s failed for %s: %s", attempt, repo_url, exc)
            _force_rmtree(repo_path)
            if attempt == max_attempts:
                break
            time.sleep(delay)
            delay *= 2

    raise RuntimeError(
        f"Could not clone repository '{repo_url}' after {max_attempts} attempts. "
        "Check your internet connection and make sure the repository URL is correct."
    ) from last_exc



def _should_skip_dir(dirname: str) -> bool:
    return dirname in SKIP_DIRS or dirname.startswith(".")


def _is_supported_file(path: Path) -> bool:
    return path.suffix in SUPPORTED_EXTENSIONS and path.stat().st_size <= MAX_FILE_SIZE_BYTES


def get_code_files(repo_path: str) -> list[dict[str, str]]:
    code_files = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [dirname for dirname in dirs if not _should_skip_dir(dirname)]

        for file in files:
            file_path = Path(root) / file

            try:
                if not _is_supported_file(file_path):
                    continue

                content = file_path.read_text(encoding="utf-8")
                relative_path = str(file_path.relative_to(repo_path))

                code_files.append(
                    {
                        "file": str(file_path),
                        "relative_path": relative_path,
                        "extension": file_path.suffix,
                        "size_bytes": file_path.stat().st_size,
                        "content": content,
                    }
                )

            except Exception:
                continue

    return code_files


def get_repository_metadata(repo_path: str, code_files: list[dict[str, str]] | None = None) -> dict[str, object]:
    root = Path(repo_path)
    code_files = code_files if code_files is not None else get_code_files(repo_path)
    readme = next(
        (file.name for file in root.iterdir() if file.is_file() and file.name.lower().startswith("readme")),
        None,
    )

    python_files = [file for file in code_files if Path(file["relative_path"]).suffix.lower() == ".py"]
    frontend_file_count = sum(
        1
        for file in code_files
        if Path(file["relative_path"]).suffix.lower() in {".html", ".css", ".js", ".ts"}
    )
    test_file_count = sum(
        1
        for file in code_files
        if Path(file["relative_path"]).suffix.lower() == ".py"
        and (
            "test" in Path(file["relative_path"]).parts
            or Path(file["relative_path"]).stem.startswith("test_")
            or Path(file["relative_path"]).stem.endswith("_test")
        )
    )
    metadata_content = "\n".join(str(file.get("content", "")).lower() for file in python_files)
    has_ml_code = any(keyword in metadata_content for keyword in ("sklearn", "tensorflow", "torch", "keras", "xgboost", "pandas", "numpy"))
    has_ai_code = any(keyword in metadata_content for keyword in ("openai", "gpt", "llm", "transformers", "azure.ai", "cohere", "chatgpt", "bard"))
    has_novel_structure = any(root.rglob("*.ipynb")) or (root / "notebooks").exists()
    readme_length = 0

    if readme is not None:
        try:
            readme_length = len((root / readme).read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            readme_length = 0

    return {
        "name": root.name,
        "path": str(root),
        "has_readme": readme is not None,
        "readme_file": readme,
        "readme_length": readme_length,
        "has_docs": (root / "docs").exists() or (root / "documentation").exists(),
        "has_pyproject": (root / "pyproject.toml").exists(),
        "has_requirements": (root / "requirements.txt").exists(),
        "has_tests": test_file_count > 0 or any((root / dirname).exists() for dirname in ("tests", "test")),
        "test_file_count": test_file_count,
        "has_backend": len(python_files) > 0,
        "python_file_count": len(python_files),
        "has_frontend": frontend_file_count > 0 or (root / "frontend").exists() or (root / "templates").exists(),
        "frontend_file_count": frontend_file_count,
        "has_ml_code": has_ml_code,
        "has_ai_code": has_ai_code,
        "has_novel_structure": has_novel_structure,
    }


def fetch_repository(repo_url: str) -> list[dict[str, str]]:
    repo_path = clone_repo(repo_url)
    return get_code_files(repo_path)


def fetch_repository_bundle(repo_url: str) -> dict[str, object]:
    repo_path = clone_repo(repo_url)
    code_files = get_code_files(repo_path)
    return {
        "metadata": get_repository_metadata(repo_path, code_files=code_files),
        "files": code_files,
    }


def fetch_local_bundle(repo_path: str) -> dict[str, object]:
    """Build the repository bundle structure from an existing local path.

    This mirrors the shape returned by `fetch_repository_bundle` so the
    review pipeline can consume local extracted archives.
    """
    code_files = get_code_files(repo_path)
    return {
        "metadata": get_repository_metadata(repo_path, code_files=code_files),
        "files": code_files,
    }


# Module is intended for import; keep demo/CLI usage out of library code.
