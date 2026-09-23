"""Exceptions raised by the INeedToSendAFax SDK."""

from __future__ import annotations

from typing import Optional


class IFaxError(Exception):
    """Base class for every error raised by this SDK."""


class APIError(IFaxError):
    """An error returned by the API.

    Attributes:
        message: Human readable message from the API.
        status_code: HTTP status code, if the error came from a response.
        code: Machine readable error code, e.g. ``insufficient_credits``.
        retry_after: Seconds to wait before retrying, from ``Retry-After``.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.retry_after = retry_after

    def __str__(self) -> str:
        prefix = ""
        if self.code:
            prefix = self.code
        if self.status_code:
            prefix = f"{prefix} (HTTP {self.status_code})".strip()
        return f"{prefix}: {self.message}" if prefix else self.message


class AuthenticationError(APIError):
    """The API key is missing or invalid (401)."""


class AuthorizationError(APIError):
    """The API key is disabled or not permitted (403)."""


class InsufficientCreditsError(APIError):
    """The account does not have enough credit for this fax (402)."""


class NotFoundError(APIError):
    """The requested resource does not exist (404)."""


class RateLimitError(APIError):
    """Too many requests (429). Check ``retry_after``."""


class ValidationError(APIError):
    """The request was rejected, e.g. a bad number or document (400/413)."""


class ServerError(APIError):
    """The API had a server-side failure (5xx)."""


class SignatureVerificationError(IFaxError):
    """A webhook signature was malformed, stale, or did not match."""


def error_from_response(
    status_code: int,
    code: Optional[str],
    message: str,
    retry_after: Optional[float] = None,
) -> APIError:
    """Map an API error response to the most specific exception class."""
    kwargs = dict(status_code=status_code, code=code, retry_after=retry_after)
    if status_code == 401:
        return AuthenticationError(message, **kwargs)
    if status_code == 403:
        return AuthorizationError(message, **kwargs)
    if status_code == 402:
        return InsufficientCreditsError(message, **kwargs)
    if status_code == 404:
        return NotFoundError(message, **kwargs)
    if status_code == 429:
        return RateLimitError(message, **kwargs)
    if status_code in (400, 413, 422):
        return ValidationError(message, **kwargs)
    if status_code >= 500:
        return ServerError(message, **kwargs)
    return APIError(message, **kwargs)
