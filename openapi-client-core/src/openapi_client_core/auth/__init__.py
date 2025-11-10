"""Authentication components for OpenAPI clients.

This module provides authentication patterns including:
- Multi-source credential resolution (param → env → .env → netrc)
- Custom header authentication for APIs with non-standard auth
- Bearer token helpers

Modules:
    credential_resolver: Multi-source credential resolution
    header_auth: Custom header authentication transport
    netrc: Netrc file credential resolution

Example:
    ```python
    from openapi_client_core.auth import CredentialResolver

    resolver = CredentialResolver()
    api_key = resolver.resolve(
        param_value=None,
        env_var_name="API_KEY",
        netrc_host="api.example.com",
    )
    ```
"""

__all__ = []
