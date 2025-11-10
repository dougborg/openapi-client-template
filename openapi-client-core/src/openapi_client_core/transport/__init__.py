"""Transport layer components for composable HTTP middleware.

This module provides transport layers that can be composed to build resilient
HTTP clients. Transport layers wrap httpx's AsyncHTTPTransport to add features
like retry logic, pagination, error logging, and authentication.

Modules:
    base: Base transport class
    error_logging: Error logging with null field detection
    retry: Retry logic with multiple strategies
    pagination: Automatic pagination for GET requests
    auth: Authentication transport layers
    factory: Factory function for creating common transport stacks

Example:
    ```python
    from openapi_client_core.transport import create_transport_stack

    transport = create_transport_stack(
        base_url="https://api.example.com",
        retry_strategy="rate_limited",
        enable_pagination=True,
        enable_error_logging=True,
    )
    ```
"""

__all__ = []
