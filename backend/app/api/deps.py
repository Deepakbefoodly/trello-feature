"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import ApiError
from app.models import User
from app.security import decode_access_token

# auto_error=False so that a missing or malformed Authorization header raises
# our own envelope instead of Starlette's default error shape. Clients then have
# exactly one error format to parse.
_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise ApiError.unauthenticated()

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise ApiError.unauthenticated("Invalid or expired token")

    # A token can outlive the user it names, so the row is still checked.
    user = session.get(User, user_id)
    if user is None:
        raise ApiError.unauthenticated("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
