from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

from .logging_config import setup_logging

from .api.review import router as review_router
from .api.upload import router as upload_router
from .api.auth import router as auth_router


from contextlib import asynccontextmanager
from .db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema & migrate data
    init_db()
    logger.info("Database initialized.")
    yield


app = FastAPI(
    title="AI Project Reviewer",
    description="Analyze GitHub repositories and generate an AI-assisted code review.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure structured logging early
setup_logging()
logger = logging.getLogger(__name__)
logger.info("Application startup: configured structured logging")


# CORS — allow Vite dev server and local clients during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
SERVE_DIR = FRONTEND_DIST if FRONTEND_DIST.exists() else FRONTEND_DIR
FRONTEND_INDEX = (FRONTEND_DIST / "index.html") if (FRONTEND_DIST / "index.html").exists() else (FRONTEND_DIR / "index.html")
FRONTEND_LOGIN = (FRONTEND_DIST / "login.html") if (FRONTEND_DIST / "login.html").exists() else (FRONTEND_DIR / "login.html")

# Mount static frontend directories
if FRONTEND_DIR.exists():
    if (FRONTEND_DIR / "css").exists():
        app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    if (FRONTEND_DIR / "js").exists():
        app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/")
@app.get("/index.html")
def app_home() -> FileResponse:
    return FileResponse(FRONTEND_INDEX)


@app.get("/login")
@app.get("/login.html")
def app_login() -> FileResponse:
    return FileResponse(FRONTEND_LOGIN if FRONTEND_LOGIN.exists() else FRONTEND_INDEX)


@app.get("/{page_name}.html")
def app_html_pages(page_name: str) -> FileResponse:
    file_path = SERVE_DIR / f"{page_name}.html"
    if file_path.exists():
        return FileResponse(file_path)
    return FileResponse(FRONTEND_INDEX)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(review_router)
app.include_router(upload_router)
