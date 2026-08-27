import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default

    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    project_root: Path = Path(__file__).resolve().parents[3]
    db_dir: Path = Path(os.getenv("DB_DIR", str(project_root / "backend" / "app" / "db")))
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{project_root / 'backend' / 'app' / 'db' / 'reviewer.db'}")

    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    env: str = os.getenv("ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    cors_origins: list[str] = _env_list(
        "CORS_ORIGINS",
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
    )
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    use_external_llm: bool = _env_bool("USE_EXTERNAL_LLM", True)
    auto_train_enabled: bool = _env_bool("AUTO_TRAIN_ENABLED", False)
    review_results_dir: Path = Path(
        os.getenv(
            "REVIEW_RESULTS_DIR",
            str(project_root / "backend" / "review_results"),
        )
    )
    models_dir: Path = Path(
        os.getenv(
            "MODELS_DIR",
            str(project_root / "backend" / "models"),
        )
    )
    temp_repos_dir: Path = Path(
        os.getenv(
            "TEMP_REPOS_DIR",
            str(project_root / "temp_repos"),
        )
    )


settings = Settings()
