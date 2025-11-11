"""Structured exceptions for API errors."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

    from openapi_client_core.errors.models import ProblemDetail


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: "httpx.Response | None" = None,
        problem_detail: "ProblemDetail | None" = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
        self.problem_detail = problem_detail


class ClientError(APIError):
    """4xx client errors."""

    pass


class BadRequestError(ClientError):
    """400 Bad Request."""

    pass


class UnauthorizedError(ClientError):
    """401 Unauthorized."""

    pass


class ForbiddenError(ClientError):
    """403 Forbidden."""

    pass


class NotFoundError(ClientError):
    """404 Not Found."""

    pass


class ConflictError(ClientError):
    """409 Conflict."""

    pass


class ValidationError(ClientError):
    """422 Unprocessable Entity (validation errors)."""

    def __init__(self, message: str, validation_errors: list[dict] | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors if validation_errors is not None else []


class RateLimitError(ClientError):
    """429 Too Many Requests."""

    def __init__(self, message: str, retry_after: int | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(APIError):
    """5xx server errors."""

    pass


class NullFieldError(ValidationError):
    """Raised when API returns null for a required field."""

    def __init__(self, message: str, field_path: str, **kwargs):
        super().__init__(message, **kwargs)
        self.field_path = field_path
