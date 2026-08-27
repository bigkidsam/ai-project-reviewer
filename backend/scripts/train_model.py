import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app.training.trainer import train_quality_classifier




def main() -> int:
    p = argparse.ArgumentParser(description="Train quality classifier")
    p.add_argument("--results-dir", default="backend/review_results", help="Directory with review JSONs/CSV")
    p.add_argument("--output", default="backend/models/quality_model.joblib", help="Output model path")
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--random-state", type=int, default=42)
    args = p.parse_args()

    results_dir = Path(args.results_dir)
    model_path = Path(args.output)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    info = train_quality_classifier(
        results_dir=results_dir,
        model_path=model_path,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    print("Trained:", info.get("model_path"))
    print("Feature names:", info.get("feature_names"))
    print("Classification report summary keys:", list(info.get("classification_report", {}).keys()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
