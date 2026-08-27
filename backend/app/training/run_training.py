import argparse
from pathlib import Path

from .trainer import train_quality_classifier


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a custom review quality model.")
    parser.add_argument(
        "--review-dir",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "review_results",
        help="Directory containing JSON review result files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "models" / "quality_model.joblib",
        help="Path to save the trained model.",
    )
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    report = train_quality_classifier(
        results_dir=args.review_dir,
        model_path=args.output,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    print("Trained model saved to:", report["model_path"])
    print("Classification report:")
    for label, metrics in report["classification_report"].items():
        if label in {"accuracy", "macro avg", "weighted avg"}:
            continue
        print(f"{label}: precision={metrics['precision']:.2f}, recall={metrics['recall']:.2f}, f1={metrics['f1-score']:.2f}")


if __name__ == "__main__":
    main()
