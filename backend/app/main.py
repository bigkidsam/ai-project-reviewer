from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

from .api.review import router as review_router


app = FastAPI(
    title="AI Project Reviewer",
    description="Analyze GitHub repositories and generate an AI-assisted code review.",
    version="0.1.0",
)


FRONTEND_INDEX = Path(__file__).resolve().parents[2] / "frontend" / "index.html"


@app.get("/")
def app_home() -> FileResponse:
    return FileResponse(FRONTEND_INDEX)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(review_router)
