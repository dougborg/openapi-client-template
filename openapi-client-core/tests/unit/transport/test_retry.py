"""Tests for retry transport logic.

Testing TDD approach - tests written before implementation.
"""

from datetime import UTC

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
            response = await client.post("https://api.example.com/test", json={"data": "test"})

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
        delays = [attempt_times[i + 1] - attempt_times[i] for i in range(len(attempt_times) - 1)]

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
        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            # Fail twice with 429, succeed on 3rd
            if attempt_count < 3:
                return httpx.Response(429, json={"error": "Rate limit exceeded"})
            return httpx.Response(200, json={"success": True})

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        assert response.status_code == 200
        assert attempt_count == 3

    @pytest.mark.unit
    async def test_retries_post_on_429(self):
        """POST request SHOULD be retried on 429 (rate limiting exception)."""
        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                return httpx.Response(429)
            return httpx.Response(201, json={"created": True})

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.post("https://api.example.com/test", json={"data": "test"})

        # POST should be retried on 429
        assert response.status_code == 201
        assert attempt_count == 2

    @pytest.mark.unit
    async def test_retries_put_on_503(self):
        """PUT request should be retried on 5xx (assumed idempotent)."""
        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                return httpx.Response(503)
            return httpx.Response(200)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.put("https://api.example.com/test", json={})

        assert response.status_code == 200
        assert attempt_count == 2

    @pytest.mark.unit
    async def test_retries_delete_on_503(self):
        """DELETE request should be retried on 5xx (assumed idempotent)."""
        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                return httpx.Response(503)
            return httpx.Response(204)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.delete("https://api.example.com/test")

        assert response.status_code == 204
        assert attempt_count == 2

    @pytest.mark.unit
    async def test_does_not_retry_post_on_503(self):
        """POST request should NOT be retried on 5xx (not idempotent)."""
        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(503)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.post("https://api.example.com/test", json={})

        # POST should NOT be retried on 5xx
        assert response.status_code == 503
        assert attempt_count == 1

    @pytest.mark.unit
    async def test_does_not_retry_patch_on_503(self):
        """PATCH request should NOT be retried on 5xx (not idempotent)."""
        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(503)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.patch("https://api.example.com/test", json={})

        assert response.status_code == 503
        assert attempt_count == 1

    @pytest.mark.unit
    async def test_respects_retry_after_header_delay_seconds(self):
        """Should respect Retry-After header (delay-seconds format) on 429."""
        import time

        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_times = []

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            attempt_times.append(time.time())
            if len(attempt_times) < 2:
                # Return 429 with Retry-After: 2 seconds
                return httpx.Response(429, headers={"Retry-After": "2"})
            return httpx.Response(200)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        assert response.status_code == 200
        assert len(attempt_times) == 2

        # Verify delay was ~2 seconds (from Retry-After header)
        delay = attempt_times[1] - attempt_times[0]
        assert 1.9 < delay < 2.1

    @pytest.mark.unit
    async def test_respects_retry_after_header_http_date(self):
        """Should respect Retry-After header (HTTP-date format) on 429."""
        import asyncio
        import time
        from datetime import datetime, timedelta
        from unittest.mock import patch

        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_times = []
        retry_delay_used = []

        # Create a capturing sleep mock
        original_sleep = asyncio.sleep

        async def capturing_sleep(delay):
            retry_delay_used.append(delay)
            await original_sleep(delay)

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            attempt_times.append(time.time())
            if len(attempt_times) < 2:
                # Return 429 with Retry-After: 3 seconds in the future (HTTP-date format)
                retry_time = datetime.now(UTC) + timedelta(seconds=3)
                retry_after = retry_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
                return httpx.Response(429, headers={"Retry-After": retry_after})
            return httpx.Response(200)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        # Use unittest.mock.patch for safe mocking with automatic cleanup
        with patch("asyncio.sleep", side_effect=capturing_sleep):
            async with httpx.AsyncClient(transport=retry_transport) as client:
                response = await client.get("https://api.example.com/test")

        assert response.status_code == 200
        assert len(attempt_times) == 2
        assert len(retry_delay_used) == 1

        # Verify the delay used was from Retry-After, not exponential backoff (which would be 1.0)
        # Due to time passing and second granularity, expect 2-3 seconds
        assert 2.0 < retry_delay_used[0] < 3.5

    @pytest.mark.unit
    async def test_exponential_backoff_on_429_without_retry_after(self):
        """Should use exponential backoff on 429 when Retry-After is absent."""
        import time

        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_times = []

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            attempt_times.append(time.time())
            # Always return 429 without Retry-After
            return httpx.Response(429)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(
            wrapped_transport=mock_transport,
            max_retries=2,
            backoff_factor=1.0,
        )

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        assert response.status_code == 429
        assert len(attempt_times) == 3  # Initial + 2 retries

        # Verify exponential backoff delays: 1s, 2s
        delays = [attempt_times[i + 1] - attempt_times[i] for i in range(len(attempt_times) - 1)]
        assert 0.9 < delays[0] < 1.1  # ~1 second
        assert 1.9 < delays[1] < 2.1  # ~2 seconds

    @pytest.mark.unit
    async def test_max_backoff_cap_respected(self):
        """Should cap backoff at max_backoff value."""
        import time

        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_times = []

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            attempt_times.append(time.time())
            if len(attempt_times) < 2:
                # Return 429 with large Retry-After value
                return httpx.Response(429, headers={"Retry-After": "300"})  # 5 minutes
            return httpx.Response(200)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(
            wrapped_transport=mock_transport,
            max_backoff=3.0,  # Cap at 3 seconds
        )

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        assert response.status_code == 200
        assert len(attempt_times) == 2

        # Verify delay was capped at max_backoff (3 seconds)
        delay = attempt_times[1] - attempt_times[0]
        assert 2.9 < delay < 3.1

    @pytest.mark.unit
    async def test_max_retries_respected_on_429(self):
        """Should stop retrying after max_retries on 429."""
        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            # Always return 429
            return httpx.Response(429)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(
            wrapped_transport=mock_transport,
            max_retries=3,
        )

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        assert response.status_code == 429
        assert attempt_count == 4  # Initial + 3 retries

    @pytest.mark.unit
    async def test_network_error_retry_for_idempotent_methods(self):
        """Should retry network errors for idempotent methods."""
        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise httpx.ConnectError("Connection failed")
            return httpx.Response(200)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        assert response.status_code == 200
        assert attempt_count == 2

    @pytest.mark.unit
    async def test_network_error_no_retry_for_non_idempotent_methods(self):
        """Should NOT retry network errors for non-idempotent methods."""
        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("Connection failed")

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            with pytest.raises(httpx.ConnectError):
                await client.post("https://api.example.com/test", json={})

        # Should not retry POST on network error
        assert attempt_count == 1

    @pytest.mark.unit
    async def test_successful_response_after_retry(self):
        """Should return successful response after retrying."""
        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_count = 0

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                return httpx.Response(429)
            return httpx.Response(200, json={"recovered": True})

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        assert response.status_code == 200
        assert response.json() == {"recovered": True}
        assert attempt_count == 3

    @pytest.mark.unit
    async def test_retry_after_with_negative_value_ignored(self):
        """Should ignore negative Retry-After values and use exponential backoff."""
        import time

        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_times = []

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            attempt_times.append(time.time())
            if len(attempt_times) < 2:
                # Return 429 with negative Retry-After (invalid)
                return httpx.Response(429, headers={"Retry-After": "-10"})
            return httpx.Response(200)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        assert response.status_code == 200
        # Should use exponential backoff (1 second) instead of negative value
        delay = attempt_times[1] - attempt_times[0]
        assert 0.9 < delay < 1.1

    @pytest.mark.unit
    async def test_retry_after_with_past_http_date_ignored(self):
        """Should ignore Retry-After dates in the past and use exponential backoff."""
        import time
        from datetime import datetime, timedelta

        from openapi_client_core.transport.retry import RateLimitAwareRetry

        attempt_times = []

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            attempt_times.append(time.time())
            if len(attempt_times) < 2:
                # Return 429 with Retry-After in the past
                past_time = datetime.now(UTC) - timedelta(seconds=10)
                retry_after = past_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
                return httpx.Response(429, headers={"Retry-After": retry_after})
            return httpx.Response(200)

        mock_transport = httpx.MockTransport(mock_handler)
        retry_transport = RateLimitAwareRetry(wrapped_transport=mock_transport)

        async with httpx.AsyncClient(transport=retry_transport) as client:
            response = await client.get("https://api.example.com/test")

        assert response.status_code == 200
        # Should use exponential backoff (1 second) instead of negative delay
        delay = attempt_times[1] - attempt_times[0]
        assert 0.9 < delay < 1.1


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
