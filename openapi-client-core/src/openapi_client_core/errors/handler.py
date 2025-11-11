"""Error handling utilities for HTTP responses."""

from typing import Any

import httpx

from openapi_client_core.errors.exceptions import (
    APIError,
    BadRequestError,
    ClientError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnauthorizedError,
    ValidationError,
)
from openapi_client_core.errors.models import ProblemDetail


def raise_for_status(response: httpx.Response) -> None:
    """Raise appropriate exception for HTTP error responses.

    Parses RFC 7807 problem details if present, otherwise uses standard
    HTTP status code to exception mapping.

    Args:
        response: HTTP response object

    Raises:
        APIError subclass based on status code
    """
    if response.is_success:
        return

    # Try to parse RFC 7807 problem details
    problem_detail = ProblemDetail.from_response(response)

    # Map status codes to exceptions
    status_code = response.status_code

    exception_map = {
        400: BadRequestError,
        401: UnauthorizedError,
        403: ForbiddenError,
        404: NotFoundError,
        409: ConflictError,
        422: ValidationError,
        429: RateLimitError,
    }

    # Determine exception class
    if status_code in exception_map:
        exc_class = exception_map[status_code]
    elif 400 <= status_code < 500:
        exc_class = ClientError
    elif 500 <= status_code < 600:
        exc_class = ServerError
    else:
        exc_class = APIError

    # Build error message
    if problem_detail:
        message = problem_detail.to_exception_message()
    else:
        # Fallback to simple message with response text
        response_text = response.text[:200]
        message = f"HTTP {status_code}: {response_text}" if response_text else f"HTTP {status_code}"

    # Handle special case for RateLimitError
    if exc_class == RateLimitError:
        retry_after = None
        if "retry-after" in response.headers:
            # Try to parse retry-after header as integer
            try:
                retry_after = int(response.headers["retry-after"])
            except (ValueError, TypeError):
                # If parsing fails, leave as None
                retry_after = None
        raise exc_class(
            message=message,
            retry_after=retry_after,
            status_code=status_code,
            response=response,
            problem_detail=problem_detail,
        )

    # Handle special case for ValidationError
    if exc_class == ValidationError:
        validation_errors = None
        if problem_detail and problem_detail.extensions:
            # Try to extract validation errors from extensions
            # Use explicit key checking to handle empty collections properly
            if "errors" in problem_detail.extensions:
                validation_errors = problem_detail.extensions.get("errors")
            else:
                validation_errors = problem_detail.extensions.get("validation_errors")
        raise exc_class(
            message=message,
            validation_errors=validation_errors,
            status_code=status_code,
            response=response,
            problem_detail=problem_detail,
        )

    # Create and raise exception
    raise exc_class(
        message=message,
        status_code=status_code,
        response=response,
        problem_detail=problem_detail,
    )


def detect_null_fields(data: dict[str, Any] | list, path: str = "") -> list[str]:
    """Detect null fields in API response data.

    Recursively scans response data for null values and returns paths.

    Args:
        data: Response data (dict or list)
        path: Current path (for recursion)

    Returns:
        List of field paths that contain null values
    """
    null_paths = []

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            if value is None:
                null_paths.append(current_path)
            elif isinstance(value, (dict, list)):
                null_paths.extend(detect_null_fields(value, current_path))

    elif isinstance(data, list):
        for index, item in enumerate(data):
            current_path = f"{path}[{index}]"

            if item is None:
                null_paths.append(current_path)
            elif isinstance(item, (dict, list)):
                null_paths.extend(detect_null_fields(item, current_path))

    return null_paths
