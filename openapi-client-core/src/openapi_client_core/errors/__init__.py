"""Error handling and RFC 7807 support for OpenAPI clients."""

from openapi_client_core.errors.exceptions import (
    APIError,
    BadRequestError,
    ClientError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    NullFieldError,
    RateLimitError,
    ServerError,
    UnauthorizedError,
    ValidationError,
)
from openapi_client_core.errors.handler import detect_null_fields, raise_for_status
from openapi_client_core.errors.models import ProblemDetail

__all__ = [
    "APIError",
    "BadRequestError",
    "ClientError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "NullFieldError",
    "ProblemDetail",
    "RateLimitError",
    "ServerError",
    "UnauthorizedError",
    "ValidationError",
    "detect_null_fields",
    "raise_for_status",
]
