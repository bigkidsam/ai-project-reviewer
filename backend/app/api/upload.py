from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile
import tarfile
import shutil

def _is_within_directory(directory: Path, target: Path) -> bool:
    try:
        directory = directory.resolve()
        target = target.resolve()
        return str(target).startswith(str(directory))
    except Exception:
        return False


def _safe_extract_zip(z: zipfile.ZipFile, path: Path) -> None:
    for member in z.infolist():
        member_path = path / member.filename
        if not _is_within_directory(path, member_path):
            raise ValueError("Archive contains files outside extraction dir")
        if member.is_dir():
            member_path.mkdir(parents=True, exist_ok=True)
            continue
        member_path.parent.mkdir(parents=True, exist_ok=True)
        with z.open(member) as src, open(member_path, "wb") as dst:
            shutil.copyfileobj(src, dst)


def _safe_extract_tar(t: tarfile.TarFile, path: Path) -> None:
    for member in t.getmembers():
        member_path = path / member.name
        if not _is_within_directory(path, member_path):
            raise ValueError("Archive contains files outside extraction dir")
        if member.isdir():
            member_path.mkdir(parents=True, exist_ok=True)
            continue
        # Skip other special members (symlinks, devices)
        if member.isreg():
            member_path.parent.mkdir(parents=True, exist_ok=True)
            f = t.extractfile(member)
            if f is None:
                continue
            with f, open(member_path, "wb") as dst:
                shutil.copyfileobj(f, dst)

from fastapi import Depends
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..services.code_review.github_fetcher import fetch_local_bundle
from ..services.code_review.reviewer import run_bundle_review
from ..models.review import ReviewResponse
from ..services.review_store import save_review_result

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=ReviewResponse)
def upload_repo(
    file: UploadFile = File(...),
    max_files: int = 10,
    db: Session = Depends(get_db),
) -> ReviewResponse:
    try:
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            upload_path = tmpdir_path / (file.filename or "upload.bin")
            upload_path.write_bytes(file.file.read())

            extract_dir = tmpdir_path / "repo"
            extract_dir.mkdir()

            # Try ZIP
            if zipfile.is_zipfile(upload_path):
                with zipfile.ZipFile(upload_path) as z:
                    _safe_extract_zip(z, extract_dir)
            # Try tar
            elif tarfile.is_tarfile(upload_path):
                with tarfile.open(upload_path) as t:
                    _safe_extract_tar(t, extract_dir)
            else:
                # Not an archive: treat as single-file repo
                (extract_dir / upload_path.name).write_bytes(upload_path.read_bytes())

            bundle = fetch_local_bundle(str(extract_dir))
            review = run_bundle_review(bundle, max_files=max_files)
            stored = save_review_result(review, db=db)
            return ReviewResponse(**stored)

    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

