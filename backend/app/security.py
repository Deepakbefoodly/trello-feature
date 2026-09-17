"""Password hashing and access tokens.

Deliberately free of HTTP concerns so it can be unit-tested directly; turning a
rejected token into a 401 is the API layer's job.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.config import get_settings

_ALGORITHM = "HS256"

# bcrypt refuses any password longer than 72 *bytes* — it raises rather than
# silently truncating. Request schemas enforce this at the boundary so an
# over-long password is a 400 and never reaches these functions.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()
    issued_at = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> UUID | None:
    """Return the subject id, or None if the token is invalid in any way.

    Expiry, a bad signature and a malformed subject are all indistinguishable to
    the caller on purpose — they all mean 'not authenticated', and collapsing
    them removes a branch nobody acts on differently.
    """
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITHM])
        return UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
