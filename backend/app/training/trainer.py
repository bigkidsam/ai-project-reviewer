from pathlib import Path
from typing import Any

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from .data_loader import load_review_results_dir

FEATURES = [
    "severity_critical",
    "severity_high",
    "severity_medium",
    "severity_low",
    "category_bug_risk",
    "category_maintainability",
    "category_style",
    "category_security",
    "total_files_analyzed",
    "total_findings",
    "files_with_issues",
    "files_with_errors",
    "issue_density_per_file",
    "findings_count",
    "issues_text_len",
]


def train_quality_classifier(
    results_dir: str | Path,
    model_path: str | Path,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    df = load_review_results_dir(results_dir)

    if df.empty:
        raise ValueError(f"No review result data found in database or directory: {results_dir}")

    features = [feature for feature in FEATURES if feature in df.columns]
    X = df[features]
    y = df["label"]

    if len(df) < 2:
        # Fit on single sample for initial model bootstrapping without split
        X_train, y_train = X, y
        X_test, y_test = X, y
    else:
        # Stratify only when there are multiple samples per class
        can_stratify = len(y.unique()) > 1 and min(y.value_counts()) >= 2
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=test_size if len(df) >= 4 else 0.5,
            random_state=random_state,
            stratify=y if can_stratify else None,
        )

    model = RandomForestClassifier(random_state=random_state, n_estimators=100)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    return {
        "model_path": str(model_path),
        "feature_names": features,
        "classification_report": report,
        "sample_count": len(df),
    }

