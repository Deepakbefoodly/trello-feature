from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.errors import ApiError
from app.models import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class MeResponse(BaseModel):
    user: UserOut


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, session: DbSession) -> AuthResponse:
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        # Insert first and let the unique index decide, rather than SELECT-then-
        # INSERT: the check-then-act version has a race where two concurrent
        # registrations both see no row and one then fails with a 500.
        raise ApiError.conflict("Email already registered") from exc

    return AuthResponse(
        user=UserOut.model_validate(user),
        access_token=create_access_token(user.id),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, session: DbSession) -> AuthResponse:
    user = session.scalar(select(User).where(User.email == payload.email))

    # One message for "no such account" and "wrong password" so the endpoint
    # cannot be used to discover which addresses are registered.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise ApiError.unauthenticated("Invalid email or password")

    return AuthResponse(
        user=UserOut.model_validate(user),
        access_token=create_access_token(user.id),
    )


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser) -> MeResponse:
    return MeResponse(user=UserOut.model_validate(user))
