"""Tests for RFC 7807 Problem Details models."""

import pytest
from httpx import Response

from openapi_client_core.errors.models import ProblemDetail


@pytest.mark.unit
def test_parse_rfc7807_response():
    """Test parsing RFC 7807 formatted response."""
    response = Response(
        status_code=400,
        headers={"content-type": "application/problem+json"},
        json={
            "type": "https://api.example.com/problems/validation-error",
            "title": "Request validation failed",
            "status": 400,
            "detail": "The request body contains invalid data",
            "instance": "/users/123",
        },
    )

    problem = ProblemDetail.from_response(response)

    assert problem is not None
    assert problem.type == "https://api.example.com/problems/validation-error"
    assert problem.title == "Request validation failed"
    assert problem.status == 400
    assert problem.detail == "The request body contains invalid data"
    assert problem.instance == "/users/123"
    assert problem.extensions is None


@pytest.mark.unit
def test_parse_rfc7807_with_extensions():
    """Test parsing RFC 7807 response with extension members."""
    response = Response(
        status_code=422,
        headers={"content-type": "application/problem+json"},
        json={
            "type": "https://api.example.com/problems/validation",
            "title": "Validation Failed",
            "status": 422,
            "errors": [{"field": "email", "message": "Invalid email format"}],
            "request_id": "abc-123",
        },
    )

    problem = ProblemDetail.from_response(response)

    assert problem is not None
    assert problem.type == "https://api.example.com/problems/validation"
    assert problem.title == "Validation Failed"
    assert problem.status == 422
    assert problem.extensions is not None
    assert "errors" in problem.extensions
    assert problem.extensions["errors"] == [{"field": "email", "message": "Invalid email format"}]
    assert problem.extensions["request_id"] == "abc-123"


@pytest.mark.unit
def test_handle_non_rfc7807_response():
    """Test handling non-RFC 7807 response returns None."""
    response = Response(
        status_code=500,
        headers={"content-type": "text/plain"},
        text="Internal Server Error",
    )

    problem = ProblemDetail.from_response(response)

    assert problem is None


@pytest.mark.unit
def test_handle_json_without_rfc7807_fields():
    """Test handling JSON response without RFC 7807 fields returns None."""
    response = Response(
        status_code=400,
        headers={"content-type": "application/json"},
        json={"error": "Something went wrong", "code": "ERR001"},
    )

    problem = ProblemDetail.from_response(response)

    assert problem is None


@pytest.mark.unit
def test_parse_json_with_rfc7807_fields_without_content_type():
    """Test parsing JSON with RFC 7807 fields even without proper content-type."""
    response = Response(
        status_code=404,
        headers={"content-type": "application/json"},
        json={
            "type": "https://api.example.com/problems/not-found",
            "title": "Resource Not Found",
            "status": 404,
        },
    )

    problem = ProblemDetail.from_response(response)

    assert problem is not None
    assert problem.type == "https://api.example.com/problems/not-found"
    assert problem.title == "Resource Not Found"
    assert problem.status == 404


@pytest.mark.unit
def test_to_exception_message_with_all_fields():
    """Test converting problem details to exception message with all fields."""
    problem = ProblemDetail(
        type="https://api.example.com/problems/validation",
        title="Validation Failed",
        status=422,
        detail="The email field is invalid",
        instance="/users/create",
        extensions={"errors": [{"field": "email", "message": "Invalid format"}]},
    )

    message = problem.to_exception_message()

    assert "Validation Failed" in message
    assert "The email field is invalid" in message
    assert "https://api.example.com/problems/validation" in message
    assert "/users/create" in message
    assert "errors" in message


@pytest.mark.unit
def test_to_exception_message_minimal():
    """Test converting minimal problem details to exception message."""
    problem = ProblemDetail(title="Error")

    message = problem.to_exception_message()

    assert message == "Error"


@pytest.mark.unit
def test_to_exception_message_detail_only():
    """Test converting problem details with only detail field."""
    problem = ProblemDetail(detail="Something went wrong")

    message = problem.to_exception_message()

    assert message == "Something went wrong"


@pytest.mark.unit
def test_to_exception_message_empty():
    """Test converting empty problem details returns fallback message."""
    problem = ProblemDetail()

    message = problem.to_exception_message()

    assert message == "Unknown API error"
