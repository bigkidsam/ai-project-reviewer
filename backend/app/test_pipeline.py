import argparse
import os

try:
    from services.code_review.reviewer import run_repository_review
except ModuleNotFoundError:
    from app.services.code_review.reviewer import run_repository_review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an AI project review.")
    parser.add_argument(
        "--repo-url",
        default=os.getenv("REVIEW_REPO_URL", "https://github.com/psf/requests"),
        help="Git repository URL to review.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=int(os.getenv("REVIEW_MAX_FILES", "10")),
        help="Maximum number of Python files to analyze.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        review = run_repository_review(args.repo_url, max_files=args.max_files)
    except RuntimeError as exc:
        print(f"Repository fetch failed: {exc}")
        return 1

    print(f"\nRepository metadata: {review['repository_metadata']}")
    print(f"Analyzed files: {len(review['analyzed_files'])}")

    print("\nFinal Metrics:")
    print(review["metrics"])
    print(f"\nStructured findings: {len(review['findings'])}")

    print("\nAI REVIEW:\n")
    print(review["ai_review"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
