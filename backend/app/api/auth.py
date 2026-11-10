"""Sign-in, self-registration, and the forgot/reset password flow.

Self-registration always creates a 'fisherman' account -- 'officer' and 'admin' are
provisioned separately (not self-service), consistent with Chapter 5's actor
definitions (an Officer is a regulatory authority, not a public signup).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.models import PasswordResetToken, User
from app.schemas.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

MIN_USERNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 8
GENERIC_FORGOT_PASSWORD_DETAIL = (
    "If an account exists for that username, a password reset link has been generated."
)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter_by(username=payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    token = create_access_token(subject=user.username, role=user.role)
    return LoginResponse(access_token=token, role=user.role, username=user.username)


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> LoginResponse:
    username = payload.username.strip()
    if len(username) < MIN_USERNAME_LENGTH:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Username must be at least {MIN_USERNAME_LENGTH} characters."
        )
    if len(payload.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if db.query(User).filter_by(username=username).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken.")

    user = User(username=username, password_hash=hash_password(payload.password), role="fisherman")
    db.add(user)
    db.commit()

    # Sign the new account in immediately, same as a successful login -- no reason to
    # make them submit the same credentials twice.
    token = create_access_token(subject=user.username, role=user.role)
    return LoginResponse(access_token=token, role=user.role, username=user.username)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    user = db.query(User).filter_by(username=payload.username.strip()).first()
    if user is None:
        # Deliberately generic -- don't reveal whether the username exists.
        return ForgotPasswordResponse(detail=GENERIC_FORGOT_PASSWORD_DETAIL)

    raw_token = generate_reset_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.password_reset_token_expire_minutes),
        )
    )
    db.commit()

    # No email provider is configured yet (see docs/USER_MANUAL.md) -- the reset link
    # is returned directly in the response instead of being emailed. Swapping in real
    # email delivery later only touches this one spot; nothing else in the flow
    # (token generation, hashing, expiry, single-use enforcement) needs to change.
    reset_url = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
    return ForgotPasswordResponse(detail=GENERIC_FORGOT_PASSWORD_DETAIL, reset_token=raw_token, reset_url=reset_url)


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> ResetPasswordResponse:
    if len(payload.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    record = db.query(PasswordResetToken).filter_by(token_hash=hash_token(payload.token)).first()
    now = datetime.now(timezone.utc)
    if record is None or record.used_at is not None or record.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")

    user = db.query(User).filter_by(id=record.user_id).first()
    user.password_hash = hash_password(payload.new_password)
    record.used_at = now
    db.commit()
    return ResetPasswordResponse(detail="Your password has been updated. You can now sign in.")
