"""Tests for retry transport logic.

Testing TDD approach - tests written before implementation.
"""

import httpx
import pytest


class TestIdempotentOnlyRetry:
    """Test IdempotentOnlyRetry - safest retry strategy.

    Only retries truly idempotent methods (GET, HEAD, OPTIONS, TRACE) on 5xx errors.
    Never retries on 429 (rate limiting).
    """

    @pytest.mark.unit
    async def test_retries_get_request_on_503(self):
        """GET request should be retried on 503 Service Unavailable."""
        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        # Track retry attempts
        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1

            # Fail first 2 times, succeed on 3rd
            if attempt_count < 3:
                return httpx.Response(503, json={"error": "Service Unavailable"})
            return httpx.Response(200, json={"success": True})

        # Create mock transport
        mock_transport = httpx.MockTransport(mock_handler)

        # Wrap with retry logic
        retry_transport = IdempotentOnlyRetry(
            wrapped_transport=mock_transport,
            max_retries=5,
        )

        # Make GET request
        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        # Should succeed after retries
        assert response.status_code == 200
        assert attempt_count == 3  # Failed twice, succeeded on 3rd

    @pytest.mark.unit
    async def test_retries_head_request_on_502(self):
        """HEAD request should be retried on 502 Bad Gateway."""
        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                return httpx.Response(502)
            return httpx.Response(200)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = IdempotentOnlyRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.head("https://api.example.com/test")

        assert response.status_code == 200
        assert attempt_count == 2

    @pytest.mark.unit
    async def test_retries_options_request_on_504(self):
        """OPTIONS request should be retried on 504 Gateway Timeout."""
        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                return httpx.Response(504)
            return httpx.Response(200)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = IdempotentOnlyRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.options("https://api.example.com/test")

        assert response.status_code == 200
        assert attempt_count == 2

    @pytest.mark.unit
    async def test_does_not_retry_post_on_503(self):
        """POST request should NOT be retried even on 5xx (not idempotent)."""
        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        # Track retry attempts
        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            # Always fail with 503
            return httpx.Response(503, json={"error": "Service Unavailable"})

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = IdempotentOnlyRetry(
            wrapped_transport=mock_transport,
            max_retries=5,
        )

        # Make POST request
        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.post(
                "https://api.example.com/test", json={"data": "test"}
            )

        # Should NOT retry - POST is not idempotent
        assert response.status_code == 503
        assert attempt_count == 1  # No retries, just the initial request

    @pytest.mark.unit
    async def test_does_not_retry_put_on_503(self):
        """PUT request should NOT be retried (not in idempotent list)."""
        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(503)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = IdempotentOnlyRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.put("https://api.example.com/test", json={})

        assert response.status_code == 503
        assert attempt_count == 1

    @pytest.mark.unit
    async def test_does_not_retry_delete_on_503(self):
        """DELETE request should NOT be retried (not in idempotent list)."""
        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(503)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = IdempotentOnlyRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.delete("https://api.example.com/test")

        assert response.status_code == 503
        assert attempt_count == 1

    @pytest.mark.unit
    async def test_does_not_retry_on_429(self):
        """GET request should NOT be retried on 429 (no rate limit handling)."""
        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            # Always return 429 Rate Limit
            return httpx.Response(429, json={"error": "Rate limit exceeded"})

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = IdempotentOnlyRetry(
            wrapped_transport=mock_transport,
            max_retries=5,
        )

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        # IdempotentOnlyRetry does NOT handle 429
        assert response.status_code == 429
        assert attempt_count == 1  # No retries on 429

    @pytest.mark.unit
    async def test_does_not_retry_on_4xx_client_errors(self):
        """Should not retry on 4xx client errors (404, 400, etc)."""
        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(404, json={"error": "Not found"})

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = IdempotentOnlyRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        # Should NOT retry on 404
        assert response.status_code == 404
        assert attempt_count == 1

    @pytest.mark.unit
    async def test_exponential_backoff_delays(self):
        """Should use exponential backoff: 1, 2, 4, 8, 16 seconds."""
        import time

        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        attempt_times = []

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            attempt_times.append(time.time())
            # Always fail so we can measure all delays
            return httpx.Response(503)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = IdempotentOnlyRetry(
            wrapped_transport=mock_transport,
            max_retries=3,  # Limit to 3 for faster test
            backoff_factor=1.0,
        )

        async with httpx.AsyncClient(transport=retry_transport) as client:
            await client.get("https://api.example.com/test")

        # Calculate actual delays between attempts
        delays = [
            attempt_times[i + 1] - attempt_times[i]
            for i in range(len(attempt_times) - 1)
        ]

        # Should have 3 delays: 1s, 2s, 4s
        # Allow 10% tolerance for timing precision
        assert len(delays) == 3
        assert 0.9 < delays[0] < 1.1  # ~1 second
        assert 1.9 < delays[1] < 2.1  # ~2 seconds
        assert 3.9 < delays[2] < 4.1  # ~4 seconds

    @pytest.mark.unit
    async def test_max_retries_limit(self):
        """Should stop after max retries (default 5)."""
        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            # Always fail
            return httpx.Response(503, json={"error": "Service Unavailable"})

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = IdempotentOnlyRetry(
            wrapped_transport=mock_transport,
            max_retries=3,  # Custom limit
        )

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        # Should try: initial + 3 retries = 4 total
        assert response.status_code == 503
        assert attempt_count == 4

    @pytest.mark.unit
    async def test_eventual_success_after_retries(self):
        """Should succeed if server recovers within retry limit."""
        from openapi_client_core.transport.retry import IdempotentOnlyRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            # Fail 4 times, succeed on 5th
            if attempt_count < 5:
                return httpx.Response(503)
            return httpx.Response(200, json={"recovered": True})

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = IdempotentOnlyRetry(
            wrapped_transport=mock_transport,
            max_retries=5,
        )

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        # Should eventually succeed
        assert response.status_code == 200
        assert attempt_count == 5


class TestRateLimitAwareRetry:
    """Test RateLimitAwareRetry - recommended for modern APIs.

    Retries all methods on 429 (rate limiting).
    Retries standard idempotent methods (GET, HEAD, PUT, DELETE, OPTIONS, TRACE) on 5xx.
    """

    @pytest.mark.unit
    async def test_retries_get_on_429(self):
        """GET request should be retried on 429 Rate Limit."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_retries_post_on_429(self):
        """POST request SHOULD be retried on 429 (rate limiting exception)."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_retries_put_on_503(self):
        """PUT request should be retried on 5xx (assumed idempotent)."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_retries_delete_on_503(self):
        """DELETE request should be retried on 5xx (assumed idempotent)."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_does_not_retry_post_on_503(self):
        """POST request should NOT be retried on 5xx (not idempotent)."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_does_not_retry_patch_on_503(self):
        """PATCH request should NOT be retried on 5xx (not idempotent)."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_respects_retry_after_header(self):
        """Should respect Retry-After header if present on 429."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_exponential_backoff_on_5xx(self):
        """Should use exponential backoff on 5xx errors."""
        pytest.skip("Implementation pending")


class TestAllMethodsRetry:
    """Test AllMethodsRetry - use with caution.

    Retries ALL methods on all configured status codes.
    Only use when API has idempotency keys or server handles duplicates safely.
    """

    @pytest.mark.unit
    async def test_retries_post_on_503(self):
        """POST request SHOULD be retried on 5xx (dangerous but configurable)."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_retries_patch_on_503(self):
        """PATCH request SHOULD be retried on 5xx."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_retries_all_methods_on_429(self):
        """All methods should be retried on 429."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_configurable_status_codes(self):
        """Should allow configuring which status codes trigger retries."""
        pytest.skip("Implementation pending")


class TestRetryConfiguration:
    """Test retry configuration options."""

    @pytest.mark.unit
    async def test_custom_max_retries(self):
        """Should allow configuring max retries."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_custom_backoff_factor(self):
        """Should allow configuring backoff factor."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_custom_retry_status_codes(self):
        """Should allow configuring which status codes trigger retries."""
        pytest.skip("Implementation pending")

    @pytest.mark.unit
    async def test_disable_retries(self):
        """Should allow disabling retries entirely (max_retries=0)."""
        pytest.skip("Implementation pending")
