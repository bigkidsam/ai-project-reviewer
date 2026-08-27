from typing import Any
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.review import ReviewRequest
from ..models.review import ReviewResponse
from ..services.code_review.reviewer import run_repository_review
from ..services.review_store import delete_review_result
from ..services.review_store import get_review_result
from ..services.review_store import list_review_results
from ..services.review_store import save_review_result

router = APIRouter(prefix="", tags=["review"])


@router.post("/review", response_model=ReviewResponse)
def review_repository(
    payload: ReviewRequest,
    db: Session = Depends(get_db),
) -> ReviewResponse:
    try:
        review = run_repository_review(
            repo_url=str(payload.repo_url),
            max_files=payload.max_files,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored_review = save_review_result(review, db=db)
    return ReviewResponse(**stored_review)


@router.get("/reviews")
@router.get("/review/list")
def list_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    sort_by: str = Query("date_desc"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return list_review_results(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        sort_by=sort_by,
    )


@router.get("/review/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: str,
    db: Session = Depends(get_db),
) -> ReviewResponse:
    review = get_review_result(review_id, db=db)

    if review is None:
        raise HTTPException(status_code=404, detail="Review result not found")

    return ReviewResponse(**review)


@router.delete("/review/{review_id}")
def delete_review(
    review_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    deleted = delete_review_result(review_id, db=db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Review not found or could not be deleted")
    return {"status": "success", "message": f"Review {review_id} deleted successfully"}
