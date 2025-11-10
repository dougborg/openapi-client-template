"""Retry transport implementations for resilient HTTP clients.

This module provides retry logic with multiple strategies:
- IdempotentOnlyRetry: Safest, only retries truly idempotent methods (GET, HEAD, OPTIONS, TRACE)
- RateLimitAwareRetry: Retries all methods on 429, standard idempotent methods on 5xx

## When to Use Each Strategy

| Strategy | 429 (Rate Limit) | 5xx Errors | Best For |
|----------|------------------|------------|----------|
| `IdempotentOnlyRetry` | ❌ No retry | GET, HEAD, OPTIONS, TRACE | APIs without rate limiting, maximum safety |
| `RateLimitAwareRetry` | ✅ All methods | GET, HEAD, PUT, DELETE, OPTIONS, TRACE | Modern APIs with 429 rate limiting |

## IdempotentOnlyRetry Example

```python
from openapi_client_core.transport.retry import IdempotentOnlyRetry
import httpx

retry_transport = IdempotentOnlyRetry(
    wrapped_transport=httpx.AsyncHTTPTransport(),
    max_retries=5,
)

async with httpx.AsyncClient(transport=retry_transport) as client:
    response = await client.get("https://api.example.com")
```

## RateLimitAwareRetry Example

```python
from openapi_client_core.transport.retry import RateLimitAwareRetry
import httpx

# Recommended for APIs that use 429 for rate limiting
retry_transport = RateLimitAwareRetry(
    wrapped_transport=httpx.AsyncHTTPTransport(),
    max_retries=5,
    max_backoff=60,  # Cap backoff at 60 seconds
)

async with httpx.AsyncClient(transport=retry_transport) as client:
    # Retries on 429 with Retry-After header support
    response = await client.post("https://api.example.com/data", json={...})
```
"""

import asyncio
import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

logger = logging.getLogger(__name__)


class IdempotentOnlyRetry(httpx.AsyncHTTPTransport):
    """Retry transport that only retries truly idempotent methods on 5xx errors.

    This is the safest retry strategy - it will never retry operations that could
    cause duplicates. Only retries GET, HEAD, OPTIONS, and TRACE on server errors.

    Use this when:
    - Your API does NOT provide idempotency keys
    - Duplicate operations (POST, PUT, DELETE) would be dangerous
    - You want the safest possible retry behavior

    Args:
        wrapped_transport: The underlying transport to wrap
        max_retries: Maximum number of retry attempts (default: 5)
        backoff_factor: Multiplier for exponential backoff (default: 1.0)
        retry_status_codes: Set of status codes that trigger retries (default: 502, 503, 504)

    Example:
        ```python
        transport = IdempotentOnlyRetry(
            wrapped_transport=httpx.AsyncHTTPTransport(),
            max_retries=3,
        )
        ```
    """

    # Truly idempotent HTTP methods (per RFC 7231)
    IDEMPOTENT_METHODS: frozenset[str] = frozenset(["HEAD", "GET", "OPTIONS", "TRACE"])

    # Server errors that warrant retry
    DEFAULT_RETRY_STATUS_CODES: frozenset[int] = frozenset([502, 503, 504])

    def __init__(
        self,
        *,
        wrapped_transport: httpx.AsyncHTTPTransport,
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        retry_status_codes: frozenset[int] | None = None,
    ) -> None:
        self._wrapped_transport = wrapped_transport
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_status_codes = retry_status_codes or self.DEFAULT_RETRY_STATUS_CODES

    async def __aenter__(self):
        """Enter async context, delegating to wrapped transport."""
        await self._wrapped_transport.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context, delegating to wrapped transport."""
        return await self._wrapped_transport.__aexit__(exc_type, exc_val, exc_tb)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Handle request with retry logic for idempotent methods on server errors.

        Args:
            request: The HTTP request to send

        Returns:
            HTTP response (after retries if needed)
        """
        retries = 0
        last_response = None

        while retries <= self.max_retries:
            try:
                response = await self._wrapped_transport.handle_async_request(request)

                # Check if we should retry
                if self._should_retry(request, response, retries):
                    last_response = response
                    retries += 1

                    # Calculate backoff delay
                    delay = self._calculate_backoff_delay(retries)

                    logger.warning(
                        f"Request {request.method} {request.url} failed with {response.status_code}, "
                        f"retrying in {delay}s (attempt {retries}/{self.max_retries})"
                    )

                    await asyncio.sleep(delay)
                    continue

                # Success or non-retryable error
                return response

            except Exception as e:
                # Network errors, timeouts, etc.
                if retries >= self.max_retries:
                    raise

                retries += 1
                delay = self._calculate_backoff_delay(retries)

                logger.warning(
                    f"Request {request.method} {request.url} failed with {e}, "
                    f"retrying in {delay}s (attempt {retries}/{self.max_retries})"
                )

                await asyncio.sleep(delay)

        # Max retries exceeded
        if last_response is not None:
            return last_response

        # Should not reach here, but just in case
        return await self._wrapped_transport.handle_async_request(request)

    def _should_retry(self, request: httpx.Request, response: httpx.Response, current_retries: int) -> bool:
        """Determine if request should be retried.

        Args:
            request: The HTTP request
            response: The HTTP response received
            current_retries: Number of retries attempted so far

        Returns:
            True if should retry, False otherwise
        """
        # Don't retry if max retries reached
        if current_retries >= self.max_retries:
            return False

        # Only retry idempotent methods
        if request.method not in self.IDEMPOTENT_METHODS:
            return False

        # Only retry configured status codes
        return response.status_code in self.retry_status_codes

    def _calculate_backoff_delay(self, retry_number: int) -> float:
        """Calculate exponential backoff delay.

        Uses formula: backoff_factor * (2 ** (retry_number - 1))
        Default backoff sequence: 1, 2, 4, 8, 16 seconds

        Args:
            retry_number: Current retry attempt (1-indexed)

        Returns:
            Delay in seconds
        """
        return self.backoff_factor * (2 ** (retry_number - 1))


class RateLimitAwareRetry(httpx.AsyncHTTPTransport):
    """Retry transport that handles rate limiting and server errors intelligently.

    This transport is designed for modern APIs that use 429 responses for rate limiting.
    It respects Retry-After headers and uses exponential backoff when they're absent.

    Use this when:
    - Your API returns 429 responses for rate limiting
    - You want to respect Retry-After headers
    - You need automatic backoff for rate limits
    - Your API supports idempotent operations (PUT, DELETE)

    Args:
        wrapped_transport: The underlying transport to wrap
        max_retries: Maximum number of retry attempts (default: 5)
        backoff_factor: Multiplier for exponential backoff (default: 1.0)
        max_backoff: Maximum backoff time in seconds (default: 60)
        retry_5xx_status_codes: Set of 5xx codes to retry (default: 502, 503, 504)

    Example:
        ```python
        transport = RateLimitAwareRetry(
            wrapped_transport=httpx.AsyncHTTPTransport(),
            max_retries=5,
            max_backoff=60,
        )
        ```
    """

    # Idempotent HTTP methods (per RFC 7231) - safe to retry on 5xx
    IDEMPOTENT_METHODS: frozenset[str] = frozenset(["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"])

    # Server errors that warrant retry
    DEFAULT_RETRY_5XX_STATUS_CODES: frozenset[int] = frozenset([502, 503, 504])

    def __init__(
        self,
        *,
        wrapped_transport: httpx.AsyncHTTPTransport,
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        max_backoff: float = 60.0,
        retry_5xx_status_codes: frozenset[int] | None = None,
    ) -> None:
        self._wrapped_transport = wrapped_transport
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.retry_5xx_status_codes = retry_5xx_status_codes or self.DEFAULT_RETRY_5XX_STATUS_CODES

    async def __aenter__(self):
        """Enter async context, delegating to wrapped transport."""
        await self._wrapped_transport.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context, delegating to wrapped transport."""
        return await self._wrapped_transport.__aexit__(exc_type, exc_val, exc_tb)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Handle request with retry logic for rate limiting and server errors.

        Args:
            request: The HTTP request to send

        Returns:
            HTTP response (after retries if needed)
        """
        retries = 0
        last_response = None

        while retries <= self.max_retries:
            try:
                response = await self._wrapped_transport.handle_async_request(request)

                # Check if we should retry
                should_retry, delay = self._should_retry_with_delay(request, response, retries)
                if should_retry:
                    last_response = response
                    retries += 1

                    logger.warning(
                        f"Request {request.method} {request.url} failed with {response.status_code}, "
                        f"retrying in {delay}s (attempt {retries}/{self.max_retries})"
                    )

                    await asyncio.sleep(delay)
                    continue

                # Success or non-retryable error
                return response

            except Exception as e:
                # Network errors, timeouts, etc. - only retry idempotent methods
                if retries >= self.max_retries or request.method not in self.IDEMPOTENT_METHODS:
                    raise

                retries += 1
                delay = self._calculate_backoff_delay(retries)

                logger.warning(
                    f"Request {request.method} {request.url} failed with {e}, "
                    f"retrying in {delay}s (attempt {retries}/{self.max_retries})"
                )

                await asyncio.sleep(delay)

        # Max retries exceeded
        if last_response is not None:
            return last_response

        # Should not reach here, but just in case
        return await self._wrapped_transport.handle_async_request(request)

    def _should_retry_with_delay(
        self, request: httpx.Request, response: httpx.Response, current_retries: int
    ) -> tuple[bool, float]:
        """Determine if request should be retried and calculate delay.

        Args:
            request: The HTTP request
            response: The HTTP response received
            current_retries: Number of retries attempted so far

        Returns:
            Tuple of (should_retry, delay_in_seconds)
        """
        # Don't retry if max retries reached
        if current_retries >= self.max_retries:
            return False, 0.0

        # Handle 429 (Rate Limit) - retry ALL methods
        if response.status_code == 429:
            delay = self._parse_retry_after(response)
            if delay is None:
                # No Retry-After header, use exponential backoff
                delay = self._calculate_backoff_delay(current_retries + 1)
            return True, delay

        # Handle 5xx errors - only retry idempotent methods
        if response.status_code in self.retry_5xx_status_codes and request.method in self.IDEMPOTENT_METHODS:
            delay = self._calculate_backoff_delay(current_retries + 1)
            return True, delay

        return False, 0.0

    def _parse_retry_after(self, response: httpx.Response) -> float | None:
        """Parse Retry-After header from response.

        Supports both formats:
        - Delay-seconds: "120" (integer seconds)
        - HTTP-date: "Wed, 21 Oct 2015 07:28:00 GMT"

        Args:
            response: HTTP response with optional Retry-After header

        Returns:
            Delay in seconds, or None if header is missing or invalid
        """
        retry_after = response.headers.get("Retry-After")
        if not retry_after:
            return None

        # Try parsing as integer (delay-seconds format)
        try:
            delay = int(retry_after)
            # Protect against negative values
            if delay < 0:
                return None
            return float(min(delay, self.max_backoff))
        except ValueError:
            pass

        # Try parsing as HTTP-date format
        try:
            retry_date = parsedate_to_datetime(retry_after)
            now = datetime.now(UTC)
            delay = (retry_date - now).total_seconds()

            # Protect against negative delays (clock skew)
            if delay < 0:
                return None

            return float(min(delay, self.max_backoff))
        except (ValueError, TypeError):
            pass

        # Invalid format, return None
        return None

    def _calculate_backoff_delay(self, retry_number: int) -> float:
        """Calculate exponential backoff delay with max_backoff cap.

        Uses formula: min(backoff_factor * (2 ** (retry_number - 1)), max_backoff)
        Default backoff sequence: 1, 2, 4, 8, 16 seconds (capped at max_backoff)

        Args:
            retry_number: Current retry attempt (1-indexed)

        Returns:
            Delay in seconds (capped at max_backoff)
        """
        delay = self.backoff_factor * (2 ** (retry_number - 1))
        return min(delay, self.max_backoff)
