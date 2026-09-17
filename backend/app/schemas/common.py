"""Field types shared across schemas, so a rule is written once."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, StringConstraints

from app.security import MAX_PASSWORD_BYTES


class ORMModel(BaseModel):
    """Base for responses read directly off SQLAlchemy instances."""

    model_config = ConfigDict(from_attributes=True)


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _within_bcrypt_limit(value: str) -> str:
    # Length is checked in BYTES, not characters: bcrypt's limit is a byte
    # limit, and a multibyte password can be well under 72 characters while
    # exceeding 72 bytes. Using Pydantic's max_length here would let those
    # through and turn a 400 into a 500 inside the hasher.
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
    return value


def _blank_to_none(value: str | None) -> str | None:
    """Collapse empty and whitespace-only descriptions to NULL.

    Keeps a single representation of 'no description' instead of tolerating both
    "" and null for the same state.
    """
    if value is None or not value.strip():
        return None
    return value


Email = Annotated[EmailStr, AfterValidator(_normalize_email)]
Password = Annotated[str, StringConstraints(min_length=8), AfterValidator(_within_bcrypt_limit)]

# strip_whitespace runs before the length checks, so " " fails min_length and a
# padded title is measured by its trimmed length.
BoardTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ListTitle = BoardTitle
CardTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CardDescription = Annotated[
    str | None, StringConstraints(max_length=5000), AfterValidator(_blank_to_none)
]
