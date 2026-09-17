"""Authentication, and the guarantee that credentials never come back out."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from tests.api import PASSWORD, Api


def test_register_returns_user_and_token(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register", json={"email": "new@example.com", "password": PASSWORD}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["access_token"]


def test_duplicate_email_is_conflict(client: TestClient) -> None:
    Api.register(client, "taken@example.com")

    response = client.post(
        "/api/auth/register", json={"email": "taken@example.com", "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_email_is_normalized_to_lowercase(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register", json={"email": "  MiXeD@Example.COM ", "password": PASSWORD}
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "mixed@example.com"


def test_duplicate_email_is_detected_case_insensitively(client: TestClient) -> None:
    """Normalization is what makes the plain unique index case-insensitive."""
    Api.register(client, "person@example.com")

    response = client.post(
        "/api/auth/register", json={"email": "PERSON@EXAMPLE.COM", "password": PASSWORD}
    )

    assert response.status_code == 409


def test_login_succeeds_with_correct_password(client: TestClient) -> None:
    Api.register(client, "user@example.com")

    response = client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("user@example.com", "wrong-password-entirely"),
        ("nobody@example.com", PASSWORD),
    ],
    ids=["wrong password", "unknown email"],
)
def test_bad_credentials_are_rejected_identically(
    client: TestClient, email: str, password: str
) -> None:
    """Both failures return the same status and message, so the endpoint
    cannot be used to discover which addresses are registered."""
    Api.register(client, "user@example.com")

    response = client.post("/api/auth/login", json={"email": email, "password": password})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password"


def test_me_returns_the_authenticated_user(api: Api) -> None:
    response = api.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "owner@example.com"


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-jwt"}, {"Authorization": "Basic abc"}],
    ids=["missing", "malformed token", "wrong scheme"],
)
def test_requests_without_a_valid_token_are_unauthenticated(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_expired_token_is_rejected(client: TestClient, api: Api) -> None:
    expired = jwt.encode(
        {
            "sub": api.user["id"],
            "iat": datetime.now(UTC) - timedelta(hours=48),
            "exp": datetime.now(UTC) - timedelta(hours=24),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


def test_token_signed_with_another_secret_is_rejected(client: TestClient, api: Api) -> None:
    forged = jwt.encode(
        {"sub": api.user["id"], "exp": datetime.now(UTC) + timedelta(hours=1)},
        "a-different-secret-long-enough-for-hs256",
        algorithm="HS256",
    )

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401


# --- invariant 5: credentials never leave the system -----------------------


def test_password_hash_never_appears_in_any_auth_response(client: TestClient) -> None:
    register = client.post(
        "/api/auth/register", json={"email": "secret@example.com", "password": PASSWORD}
    )
    login = client.post(
        "/api/auth/login", json={"email": "secret@example.com", "password": PASSWORD}
    )
    token = register.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    for response in (register, login, me):
        assert "password" not in response.text.lower(), response.text


def test_validation_error_does_not_echo_the_submitted_password(client: TestClient) -> None:
    """FastAPI's raw validation errors include the rejected input value.

    A too-short password must not come back in the error body.
    """
    response = client.post(
        "/api/auth/register", json={"email": "not-an-email", "password": "short"}
    )

    assert response.status_code == 400
    assert "short" not in response.text


# --- password constraints --------------------------------------------------


def test_password_below_minimum_length_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "1234567"}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_password_over_bcrypt_byte_limit_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "a" * 73}
    )

    assert response.status_code == 400


def test_multibyte_password_is_measured_in_bytes_not_characters(client: TestClient) -> None:
    """30 characters, 90 bytes in UTF-8.

    Measuring characters would let this through to bcrypt, which raises — a 500
    where the caller deserves a 400.
    """
    password = "é" * 45  # 45 chars, 90 bytes

    response = client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": password}
    )

    assert response.status_code == 400
    assert response.json()["error"]["details"]["field"] == "password"


def test_password_exactly_at_the_byte_limit_is_accepted(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "a" * 72}
    )

    assert response.status_code == 201
