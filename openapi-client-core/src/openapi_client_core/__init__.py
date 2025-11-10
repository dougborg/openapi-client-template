"""OpenAPI Client Core - Shared runtime library for Python OpenAPI clients.

This library provides battle-tested patterns for building robust OpenAPI clients:
- Composable transport layers (retry, pagination, error logging, auth)
- Multi-source credential resolution
- RFC 7807 error handling with null field detection
- Testing utilities and fixtures

Example:
    ```python
    from openapi_client_core.transport import create_transport_stack
    from openapi_client_core.auth import CredentialResolver

    # Resolve credentials
    resolver = CredentialResolver()
    api_key = resolver.resolve(env_var_name="MY_API_KEY")

    # Create resilient transport
    transport = create_transport_stack(
        base_url="https://api.example.com",
        retry_strategy="rate_limited",
        enable_pagination=True,
    )

    # Use with your generated client
    client = MyClient(
        base_url="https://api.example.com", token=api_key, transport=transport
    )
    ```
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
