"""Auto-training orchestration: triggers model retraining after new reviews."""

import logging
from pathlib import Path
from threading import Lock, Thread

from ..core.config import settings
from ..training.trainer import train_quality_classifier

logger = logging.getLogger(__name__)

MODELS_DIR = settings.models_dir
REVIEW_RESULTS_DIR = settings.review_results_dir
MODEL_PATH = MODELS_DIR / "quality_model.joblib"

_TRAINING_LOCK = Lock()


def _retrain_model() -> None:
    """Retrain the model in background. Silently handles errors."""
    if not _TRAINING_LOCK.acquire(blocking=False):
        logger.info("Auto-training skipped: another training task is currently in progress.")
        return

    try:
        logger.info("Auto-training started...")
        result = train_quality_classifier(
            results_dir=settings.review_results_dir,
            model_path=settings.models_dir / "quality_model.joblib",
            test_size=0.2,
            random_state=42,
        )
        logger.info(f"Model retrained successfully: {result['model_path']}")
    except Exception as exc:
        logger.error(f"Auto-training failed: {exc}")
    finally:
        _TRAINING_LOCK.release()


def trigger_auto_training() -> None:
    """Trigger model retraining in a background thread (non-blocking)."""
    thread = Thread(target=_retrain_model, daemon=True)
    thread.start()
