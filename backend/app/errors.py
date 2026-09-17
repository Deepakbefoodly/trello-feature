"""The single error shape every non-2xx response uses.

Clients parse exactly one envelope:

    {"error": {"code": "...", "message": "...", "details": {...}}}
"""

import logging
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# FORBIDDEN (403) is deliberately absent. Boards are single-owner, so a caller
# either owns a resource or must not learn it exists; every such case is a 404
# (see ApiError.not_found). Defining a 403 nothing can raise would be dead code.


class ApiError(Exception):
    """Raised anywhere in the app to produce a typed error response."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details

    @classmethod
    def not_found(cls, resource: str) -> "ApiError":
        """404 for both 'does not exist' and 'not yours'.

        Returning 403 for someone else's board would confirm that the id is
        real, leaking the existence of other users' data. The two cases are
        deliberately indistinguishable to the caller.
        """
        return cls(404, ErrorCode.NOT_FOUND, f"{resource} not found")

    @classmethod
    def validation(cls, message: str, field: str | None = None) -> "ApiError":
        return cls(
            400,
            ErrorCode.VALIDATION_ERROR,
            message,
            {"field": field} if field else None,
        )

    @classmethod
    def conflict(cls, message: str) -> "ApiError":
        return cls(409, ErrorCode.CONFLICT, message)

    @classmethod
    def unauthenticated(cls, message: str = "Not authenticated") -> "ApiError":
        return cls(401, ErrorCode.UNAUTHENTICATED, message)


def _envelope(
    status_code: int,
    code: ErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code.value, "message": message}
    if details:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _envelope(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Convert FastAPI's 422 into our 400 VALIDATION_ERROR envelope.

        Only `loc` and `msg` are copied out of the raw error. FastAPI also puts
        the rejected `input` value in there, which for a bad registration body
        would echo the submitted password straight back in the response. That
        would violate invariant 5, so the raw errors are never passed through.
        """
        first = exc.errors()[0]
        location = [str(part) for part in first["loc"] if part != "body"]
        field = ".".join(location) or None
        return _envelope(
            400,
            ErrorCode.VALIDATION_ERROR,
            first["msg"],
            {"field": field} if field else None,
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        """Last resort: log the detail, return none of it.

        Stack traces and driver messages can contain query parameters, so the
        response body stays generic while the server log keeps the diagnosis.
        """
        logger.exception("Unhandled error", exc_info=exc)
        return _envelope(500, ErrorCode.INTERNAL_ERROR, "Internal server error")
