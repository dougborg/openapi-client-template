"""Custom exceptions for credential resolution and authentication.

This module defines exceptions used throughout the authentication system,
particularly for credential resolution errors.

Example:
    ```python
    from openapi_client_core.auth.exceptions import CredentialNotFoundError

    if not api_key:
        raise CredentialNotFoundError("API key not found", env_var_name="MY_API_KEY")
    ```
"""


class CredentialError(Exception):
    """Base exception for credential-related errors.

    All credential-specific exceptions inherit from this class,
    making it easy to catch any credential-related error.
    """

    pass


class CredentialNotFoundError(CredentialError):
    """Raised when a required credential cannot be resolved.

    This exception is raised when a credential is marked as required
    but cannot be found in any of the configured sources.

    Attributes:
        env_var_name: The environment variable name that was checked (if any).

    Example:
        ```python
        try:
            api_key = resolver.resolve(env_var_name="MY_API_KEY", required=True)
        except CredentialNotFoundError as e:
            print(f"Missing credential: {e.env_var_name}")
        ```
    """

    def __init__(self, message: str, env_var_name: str | None = None):
        """Initialize CredentialNotFoundError.

        Args:
            message: Error message describing what credential is missing.
            env_var_name: Optional environment variable name for reference.
        """
        super().__init__(message)
        self.env_var_name = env_var_name


class CredentialFileError(CredentialError):
    """Raised when credential file cannot be read.

    This exception is raised when there are issues reading a credential
    from a file, such as file not found, permission denied, or read errors.

    Example:
        ```python
        try:
            api_key = resolver.resolve_from_file(file_path="~/.config/myapp/api_key", required=True)
        except CredentialFileError as e:
            print(f"Cannot read credential file: {e}")
        ```
    """

    pass
