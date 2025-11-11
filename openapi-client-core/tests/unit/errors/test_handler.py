"""Tests for error handling utilities."""

import pytest
from httpx import Response

from openapi_client_core.errors.exceptions import (
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
from openapi_client_core.errors.handler import detect_null_fields, raise_for_status


@pytest.mark.unit
def test_raise_for_status_success_response():
    """Test raise_for_status doesn't raise for successful responses."""
    response = Response(status_code=200)

    # Should not raise
    raise_for_status(response)


@pytest.mark.unit
def test_raise_for_status_400_bad_request():
    """Test raise_for_status raises BadRequestError for 400."""
    response = Response(
        status_code=400,
        headers={"content-type": "text/plain"},
        text="Bad request",
    )

    with pytest.raises(BadRequestError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == 400
    assert exc_info.value.response == response
    assert "400" in str(exc_info.value)


@pytest.mark.unit
def test_raise_for_status_401_unauthorized():
    """Test raise_for_status raises UnauthorizedError for 401."""
    response = Response(status_code=401, text="Unauthorized")

    with pytest.raises(UnauthorizedError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == 401


@pytest.mark.unit
def test_raise_for_status_403_forbidden():
    """Test raise_for_status raises ForbiddenError for 403."""
    response = Response(status_code=403, text="Forbidden")

    with pytest.raises(ForbiddenError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == 403


@pytest.mark.unit
def test_raise_for_status_404_not_found():
    """Test raise_for_status raises NotFoundError for 404."""
    response = Response(status_code=404, text="Not found")

    with pytest.raises(NotFoundError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == 404


@pytest.mark.unit
def test_raise_for_status_409_conflict():
    """Test raise_for_status raises ConflictError for 409."""
    response = Response(status_code=409, text="Conflict")

    with pytest.raises(ConflictError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == 409


@pytest.mark.unit
def test_raise_for_status_422_validation():
    """Test raise_for_status raises ValidationError for 422."""
    response = Response(
        status_code=422,
        headers={"content-type": "application/json"},
        json={"error": "Validation failed"},
    )

    with pytest.raises(ValidationError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == 422


@pytest.mark.unit
def test_raise_for_status_429_rate_limit():
    """Test raise_for_status raises RateLimitError for 429."""
    response = Response(
        status_code=429,
        headers={"retry-after": "60"},
        text="Too many requests",
    )

    with pytest.raises(RateLimitError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after == 60


@pytest.mark.unit
def test_raise_for_status_429_without_retry_after():
    """Test raise_for_status handles 429 without retry-after header."""
    response = Response(status_code=429, text="Too many requests")

    with pytest.raises(RateLimitError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after is None


@pytest.mark.unit
def test_raise_for_status_4xx_generic():
    """Test raise_for_status raises ClientError for unmapped 4xx."""
    response = Response(status_code=418, text="I'm a teapot")

    with pytest.raises(ClientError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == 418
    assert not isinstance(exc_info.value, BadRequestError)


@pytest.mark.unit
def test_raise_for_status_5xx_server_error():
    """Test raise_for_status raises ServerError for 5xx."""
    response = Response(status_code=500, text="Internal server error")

    with pytest.raises(ServerError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == 500


@pytest.mark.unit
def test_raise_for_status_with_rfc7807():
    """Test raise_for_status parses RFC 7807 problem details."""
    response = Response(
        status_code=400,
        headers={"content-type": "application/problem+json"},
        json={
            "type": "https://api.example.com/problems/validation",
            "title": "Validation Failed",
            "status": 400,
            "detail": "The email field is invalid",
        },
    )

    with pytest.raises(BadRequestError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.problem_detail is not None
    assert exc_info.value.problem_detail.title == "Validation Failed"
    assert "Validation Failed" in str(exc_info.value)


@pytest.mark.unit
def test_raise_for_status_validation_with_errors():
    """Test raise_for_status extracts validation errors from RFC 7807."""
    response = Response(
        status_code=422,
        headers={"content-type": "application/problem+json"},
        json={
            "type": "https://api.example.com/problems/validation",
            "title": "Validation Failed",
            "status": 422,
            "errors": [{"field": "email", "message": "Invalid"}],
        },
    )

    with pytest.raises(ValidationError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.validation_errors is not None
    assert len(exc_info.value.validation_errors) == 1
    assert exc_info.value.validation_errors[0]["field"] == "email"


@pytest.mark.unit
def test_raise_for_status_plain_text_error():
    """Test raise_for_status handles plain text errors."""
    response = Response(
        status_code=500,
        headers={"content-type": "text/plain"},
        text="Internal Server Error",
    )

    with pytest.raises(ServerError) as exc_info:
        raise_for_status(response)

    assert "500" in str(exc_info.value)
    assert "Internal Server Error" in str(exc_info.value)


@pytest.mark.unit
def test_raise_for_status_json_without_rfc7807():
    """Test raise_for_status handles JSON errors without RFC 7807."""
    response = Response(
        status_code=400,
        headers={"content-type": "application/json"},
        json={"error": "Something went wrong", "code": "ERR001"},
    )

    with pytest.raises(BadRequestError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.problem_detail is None
    assert "400" in str(exc_info.value)


@pytest.mark.unit
def test_detect_null_fields_simple():
    """Test detect_null_fields finds null values in simple dict."""
    data = {"name": "John", "email": None, "age": 30}

    null_paths = detect_null_fields(data)

    assert null_paths == ["email"]


@pytest.mark.unit
def test_detect_null_fields_nested():
    """Test detect_null_fields finds null values in nested structures."""
    data = {"user": {"name": "John", "address": {"city": None, "zip": "12345"}}}

    null_paths = detect_null_fields(data)

    assert null_paths == ["user.address.city"]


@pytest.mark.unit
def test_detect_null_fields_list():
    """Test detect_null_fields finds null values in lists."""
    data = {"items": [{"id": 1}, None, {"id": 3}]}

    null_paths = detect_null_fields(data)

    assert null_paths == ["items[1]"]


@pytest.mark.unit
def test_detect_null_fields_complex():
    """Test detect_null_fields handles complex nested structures."""
    data = {
        "user": {
            "name": None,
            "contacts": [{"type": "email", "value": "test@example.com"}, {"type": "phone", "value": None}],
        },
        "metadata": None,
    }

    null_paths = detect_null_fields(data)

    assert "user.name" in null_paths
    assert "user.contacts[1].value" in null_paths
    assert "metadata" in null_paths
    assert len(null_paths) == 3


@pytest.mark.unit
def test_detect_null_fields_no_nulls():
    """Test detect_null_fields returns empty list when no nulls."""
    data = {"name": "John", "age": 30, "active": True}

    null_paths = detect_null_fields(data)

    assert null_paths == []


@pytest.mark.unit
def test_detect_null_fields_empty_dict():
    """Test detect_null_fields handles empty dict."""
    data = {}

    null_paths = detect_null_fields(data)

    assert null_paths == []
