from fastapi import APIRouter
from fastapi import HTTPException

from ..schemas.review import ReviewRequest
from ..schemas.review import ReviewResponse
from ..services.review_store import get_review_result
from ..services.review_store import save_review_result
from ..services.code_review.reviewer import run_repository_review

router = APIRouter(prefix="/review", tags=["review"])


@router.post("", response_model=ReviewResponse)
def review_repository(payload: ReviewRequest) -> ReviewResponse:
    try:
        review = run_repository_review(
            repo_url=str(payload.repo_url),
            max_files=payload.max_files,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored_review = save_review_result(review)
    return ReviewResponse(**stored_review)


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(review_id: str) -> ReviewResponse:
    review = get_review_result(review_id)

    if review is None:
        raise HTTPException(status_code=404, detail="Review result not found")

    return ReviewResponse(**review)
