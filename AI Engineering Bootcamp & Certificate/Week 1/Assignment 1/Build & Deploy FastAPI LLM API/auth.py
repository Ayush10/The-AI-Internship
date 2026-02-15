from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models import get_db, User
from schemas import UserRegisterRequest, UserResponse
from config import ADMIN_NAME, ADMIN_EMAIL, MESSAGE_LIMIT

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    summary="Register or Update User",
    description="Register a new user or update existing by fingerprint. Returns user info with message limits.",
)
def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    is_admin = (
        request.name.strip().lower() == ADMIN_NAME.strip().lower()
        and request.email.strip().lower() == ADMIN_EMAIL.strip().lower()
    )

    existing = db.query(User).filter(User.fingerprint == request.fingerprint).first()

    if existing:
        existing.name = request.name
        existing.email = request.email
        existing.is_admin = is_admin
        db.commit()
        db.refresh(existing)
        user = existing
    else:
        user = User(
            name=request.name,
            email=request.email,
            fingerprint=request.fingerprint,
            is_admin=is_admin,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return _build_response(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Look up user by browser fingerprint.",
)
def get_current_user(
    fingerprint: str = Query(description="Browser fingerprint UUID"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.fingerprint == fingerprint).first()
    if not user:
        raise HTTPException(404, "User not found. Please register first.")
    return _build_response(user)


def _build_response(user: User) -> UserResponse:
    remaining = None if user.is_admin else max(0, MESSAGE_LIMIT - user.message_count)
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        fingerprint=user.fingerprint,
        message_count=user.message_count,
        is_admin=user.is_admin,
        messages_remaining=remaining,
        created_at=user.created_at,
    )
