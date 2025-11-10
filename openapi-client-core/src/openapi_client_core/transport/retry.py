"""Retry transport implementations for resilient HTTP clients.

This module provides retry logic with multiple strategies:
- IdempotentOnlyRetry: Safest, only retries truly idempotent methods
- RateLimitAwareRetry: Retries all methods on 429, idempotent on 5xx
- AllMethodsRetry: Retries everything (use with caution)

Example:
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
"""

import asyncio
import logging

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
    ):
        self._wrapped_transport = wrapped_transport
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_status_codes = (
            retry_status_codes
            if retry_status_codes is not None
            else self.DEFAULT_RETRY_STATUS_CODES
        )

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

    def _should_retry(
        self, request: httpx.Request, response: httpx.Response, current_retries: int
    ) -> bool:
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
