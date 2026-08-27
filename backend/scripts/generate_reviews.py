import logging
from app.services.code_review.reviewer import run_repository_review
from app.services.review_store import save_review_result

logging.basicConfig(level=logging.INFO)

REPOS = [
    "https://github.com/psf/requests",
    "https://github.com/django/django",
    "https://github.com/numpy/numpy",
]


def main():
    for repo in REPOS:
        logging.info("Running review for %s", repo)
        try:
            review = run_repository_review(repo, max_files=5)
            saved = save_review_result(review)
            logging.info("Saved review: %s", saved.get("review_id"))
        except Exception as exc:
            logging.exception("Failed to run review for %s: %s", repo, exc)


if __name__ == "__main__":
    main()
