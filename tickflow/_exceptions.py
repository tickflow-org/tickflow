"""Custom exceptions for the TickFlow SDK."""

from __future__ import annotations

from typing import Any, Optional


class TickFlowError(Exception):
    """Base exception for all TickFlow SDK errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class APIError(TickFlowError):
    """Error returned by the TickFlow API.

    Attributes
    ----------
    message : str
        Human-readable error message.
    code : str
        Error code returned by the API (e.g., "INVALID_PERIOD", "SYMBOL_NOT_FOUND").
    status_code : int
        HTTP status code.
    details : Any, optional
        Additional error details for debugging.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.details = details

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"status_code={self.status_code})"
        )


class AuthenticationError(APIError):
    """Authentication failed (401)."""

    pass


class PermissionError(APIError):
    """Permission denied (403)."""

    pass


class NotFoundError(APIError):
    """Resource not found (404)."""

    pass


class BadRequestError(APIError):
    """Invalid request parameters (400)."""

    pass


class RateLimitError(APIError):
    """Rate limit exceeded (429)."""

    pass


class InternalServerError(APIError):
    """Server error (5xx)."""

    pass


class ConnectionError(TickFlowError):
    """Network connection error."""

    pass


class TimeoutError(TickFlowError):
    """Request timeout."""

    pass


def raise_for_status(status_code: int, response_body: dict[str, Any]) -> None:
    """Raise an appropriate exception based on status code and response body.

    Parameters
    ----------
    status_code : int
        HTTP status code.
    response_body : dict
        Parsed JSON response body.

    Raises
    ------
    APIError
        Appropriate subclass based on the status code.
    """
    if status_code < 400:
        return

    message = response_body.get("message", "Unknown error")
    code = response_body.get("code", "UNKNOWN")
    details = response_body.get("details")

    error_cls: type[APIError]

    if status_code == 400:
        error_cls = BadRequestError
    elif status_code == 401:
        error_cls = AuthenticationError
    elif status_code == 403:
        error_cls = PermissionError
    elif status_code == 404:
        error_cls = NotFoundError
    elif status_code == 429:
        error_cls = RateLimitError
    elif status_code >= 500:
        error_cls = InternalServerError
    else:
        error_cls = APIError

    raise error_cls(message, code=code, status_code=status_code, details=details)
