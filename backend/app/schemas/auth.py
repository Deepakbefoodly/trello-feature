from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import Email, ORMModel, Password


class RegisterRequest(BaseModel):
    email: Email
    password: Password


class LoginRequest(BaseModel):
    email: Email
    password: Password


class UserOut(ORMModel):
    """Public view of a user.

    password_hash has no field here, so it cannot be serialised into a response
    even by accident (invariant 5).
    """

    id: UUID
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserOut
    access_token: str
