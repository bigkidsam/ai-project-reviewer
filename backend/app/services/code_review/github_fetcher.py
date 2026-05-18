import os
from pathlib import Path

from git import GitCommandError
from git import Repo

TEMP_DIR = Path(__file__).resolve().parents[3] / "temp_repos"
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


def clone_repo(repo_url: str) -> str:
    TEMP_DIR.mkdir(exist_ok=True)

    repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    repo_path = TEMP_DIR / repo_name

    if repo_path.exists():
        try:
            repo = Repo(str(repo_path))
            repo.remotes.origin.fetch(depth=1)
        except GitCommandError:
            pass

        return str(repo_path)

    try:
        Repo.clone_from(repo_url, str(repo_path), depth=1)
    except GitCommandError as exc:
        raise RuntimeError(
            f"Could not clone repository '{repo_url}'. Check your internet connection "
            "and make sure the repository URL is correct."
        ) from exc

    return str(repo_path)


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


def get_repository_metadata(repo_path: str) -> dict[str, object]:
    root = Path(repo_path)
    files = list(root.iterdir())
    readme = next((file.name for file in files if file.name.lower().startswith("readme")), None)

    return {
        "name": root.name,
        "path": str(root),
        "has_readme": readme is not None,
        "readme_file": readme,
        "has_pyproject": (root / "pyproject.toml").exists(),
        "has_requirements": (root / "requirements.txt").exists(),
        "has_tests": any((root / dirname).exists() for dirname in ("tests", "test")),
    }


def fetch_repository(repo_url: str) -> list[dict[str, str]]:
    repo_path = clone_repo(repo_url)
    return get_code_files(repo_path)


def fetch_repository_bundle(repo_url: str) -> dict[str, object]:
    repo_path = clone_repo(repo_url)
    return {
        "metadata": get_repository_metadata(repo_path),
        "files": get_code_files(repo_path),
    }


if __name__ == "__main__":
    repo = "https://github.com/octocat/Hello-World"
    files = fetch_repository(repo)

    print(f"\nTotal files fetched: {len(files)}")

    for f in files[:3]:
        print(f"\nFile: {f['file']}")
        print(f"Content preview: {f['content'][:100]}")
