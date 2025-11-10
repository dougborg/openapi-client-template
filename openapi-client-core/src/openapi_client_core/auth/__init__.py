"""Authentication components for OpenAPI clients.

This module provides authentication patterns including:
- Multi-source credential resolution (value → env → .env → default)
- Custom header authentication for APIs with non-standard auth
- Bearer token helpers

Example:
    ```python
    from openapi_client_core.auth import CredentialResolver

    resolver = CredentialResolver()
    api_key = resolver.resolve(
        env_var_name="API_KEY",
        required=True,
    )
    ```
"""

from openapi_client_core.auth.credentials import CredentialResolver
from openapi_client_core.auth.exceptions import (
    CredentialError,
    CredentialFileError,
    CredentialNotFoundError,
)

__all__ = [
    "CredentialError",
    "CredentialFileError",
    "CredentialNotFoundError",
    "CredentialResolver",
]
