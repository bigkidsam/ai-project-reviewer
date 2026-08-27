"""Authentication router providing registration, login, demo login, and profile check."""

from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import create_access_token, decode_access_token, hash_password, verify_password
from ..db.models import UserRecord
from ..db.session import get_db
from ..schemas.auth import TokenResponse, UserLoginRequest, UserProfileResponse, UserRegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> UserRecord:
    """Dependency to retrieve currently authenticated user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token",
        )

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    user = db.scalar(select(UserRecord).where(UserRecord.id == payload["sub"]))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists",
        )

    return user


@router.post("/register", response_model=TokenResponse)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user account."""
    # Check if username or email already taken
    existing = db.scalar(
        select(UserRecord).where(
            (UserRecord.username == payload.username) | (UserRecord.email == payload.email)
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered.",
        )

    user = UserRecord(
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "username": user.username})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate user with username or email + password."""
    identifier = payload.username_or_email.strip()
    user = db.scalar(
        select(UserRecord).where(
            (UserRecord.username == identifier) | (UserRecord.email == identifier.lower())
        )
    )

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
        )

    token = create_access_token({"sub": user.id, "username": user.username})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        email=user.email,
    )


@router.post("/demo", response_model=TokenResponse)
def demo_login(db: Session = Depends(get_db)) -> TokenResponse:
    """One-click demo login for fast, instant guest evaluation."""
    demo_email = "demo@reviewer.ai"
    user = db.scalar(select(UserRecord).where(UserRecord.email == demo_email))
    
    if not user:
        user = UserRecord(
            username="demo_user",
            email=demo_email,
            hashed_password=hash_password("demopassword123"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.id, "username": user.username})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        email=user.email,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: UserRecord = Depends(get_current_user)) -> UserProfileResponse:
    """Return profile of the currently logged-in user."""
    return UserProfileResponse(**current_user.to_dict())
