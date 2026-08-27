from pathlib import Path

import joblib

from ..core.config import settings
from .trainer import FEATURES

MODEL_FILENAME = "quality_model.joblib"
MODEL_PATH = settings.models_dir / MODEL_FILENAME


def load_quality_model():
    if not MODEL_PATH.exists():
        return None

    return joblib.load(MODEL_PATH)


def _build_feature_vector(metrics: dict) -> list[float]:
    severity = metrics.get("severity_counts", {}) or {}
    category = metrics.get("category_counts", {}) or {}

    row = [
        float(severity.get("critical", 0)),
        float(severity.get("high", 0)),
        float(severity.get("medium", 0)),
        float(severity.get("low", 0)),
        float(category.get("bug_risk", 0)),
        float(category.get("maintainability", 0)),
        float(category.get("style", 0)),
        float(category.get("security", 0)),
        float(metrics.get("total_files_analyzed", 0)),
        float(metrics.get("total_findings", 0)),
        float(metrics.get("files_with_issues", 0)),
        float(metrics.get("files_with_errors", 0)),
        float(metrics.get("issue_density_per_file", 0)),
        float(metrics.get("findings_count", metrics.get("total_findings", 0))),
        float(metrics.get("issues_text_len", 0)),
    ]

    return row



def predict_quality_label(metrics: dict) -> str | None:
    model = load_quality_model()
    if model is None:
        return None

    vector = _build_feature_vector(metrics)
    # If the trained model recorded feature names, provide a DataFrame
    # so sklearn receives the same feature names it was fitted with
    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is not None:
        try:
            import pandas as pd

            X = pd.DataFrame([vector], columns=list(feature_names))
            return str(model.predict(X)[0])
        except Exception:
            # fallback to raw list input if DataFrame construction fails
            return str(model.predict([vector])[0])

    return str(model.predict([vector])[0])
