"""Tests for structured API exceptions."""

import pytest
from httpx import Response

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
from openapi_client_core.errors.models import ProblemDetail


@pytest.mark.unit
def test_api_error_instantiation():
    """Test APIError can be instantiated with all attributes."""
    response = Response(status_code=500)
    problem = ProblemDetail(title="Error", status=500)

    error = APIError(
        message="Test error",
        status_code=500,
        response=response,
        problem_detail=problem,
    )

    assert str(error) == "Test error"
    assert error.status_code == 500
    assert error.response == response
    assert error.problem_detail == problem


@pytest.mark.unit
def test_exception_inheritance():
    """Test exception inheritance chain."""
    # ClientError inherits from APIError
    assert issubclass(ClientError, APIError)

    # All 4xx errors inherit from ClientError
    assert issubclass(BadRequestError, ClientError)
    assert issubclass(UnauthorizedError, ClientError)
    assert issubclass(ForbiddenError, ClientError)
    assert issubclass(NotFoundError, ClientError)
    assert issubclass(ConflictError, ClientError)
    assert issubclass(ValidationError, ClientError)
    assert issubclass(RateLimitError, ClientError)

    # ServerError inherits from APIError
    assert issubclass(ServerError, APIError)

    # NullFieldError inherits from ValidationError
    assert issubclass(NullFieldError, ValidationError)


@pytest.mark.unit
def test_validation_error_with_errors():
    """Test ValidationError stores validation errors."""
    validation_errors = [
        {"field": "email", "message": "Invalid email"},
        {"field": "name", "message": "Required field"},
    ]

    error = ValidationError(message="Validation failed", validation_errors=validation_errors)

    assert str(error) == "Validation failed"
    assert error.validation_errors == validation_errors


@pytest.mark.unit
def test_validation_error_without_errors():
    """Test ValidationError without validation errors list."""
    error = ValidationError(message="Validation failed")

    assert str(error) == "Validation failed"
    assert error.validation_errors == []


@pytest.mark.unit
def test_rate_limit_error_with_retry_after():
    """Test RateLimitError stores retry_after value."""
    error = RateLimitError(message="Too many requests", retry_after=60)

    assert str(error) == "Too many requests"
    assert error.retry_after == 60


@pytest.mark.unit
def test_rate_limit_error_without_retry_after():
    """Test RateLimitError without retry_after value."""
    error = RateLimitError(message="Too many requests")

    assert str(error) == "Too many requests"
    assert error.retry_after is None


@pytest.mark.unit
def test_null_field_error():
    """Test NullFieldError stores field path."""
    error = NullFieldError(message="Field is null", field_path="user.address.city")

    assert str(error) == "Field is null"
    assert error.field_path == "user.address.city"
    # Should also have validation_errors from parent class
    assert error.validation_errors == []
