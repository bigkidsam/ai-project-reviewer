import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from uuid import uuid4


RESULTS_DIR = Path(__file__).resolve().parents[2] / "review_results"


def save_review_result(review: dict[str, object]) -> dict[str, object]:
    RESULTS_DIR.mkdir(exist_ok=True)

    review_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()
    stored_review = {
        "review_id": review_id,
        "created_at": created_at,
        **review,
    }

    result_path = RESULTS_DIR / f"{review_id}.json"
    result_path.write_text(
        json.dumps(stored_review, indent=2, default=str),
        encoding="utf-8",
    )

    return stored_review


def get_review_result(review_id: str) -> dict[str, object] | None:
    result_path = RESULTS_DIR / f"{review_id}.json"

    if not result_path.exists():
        return None

    return json.loads(result_path.read_text(encoding="utf-8"))
