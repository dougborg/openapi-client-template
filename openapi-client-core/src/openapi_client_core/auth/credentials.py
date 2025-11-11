"""Multi-source credential resolution for OpenAPI clients.

This module provides flexible credential resolution that can load API credentials
from multiple sources with priority ordering and fallbacks.

Resolution order (highest to lowest priority):
1. Explicitly provided value
2. Environment variable
3. .env file (python-dotenv)
4. Default value

Example:
    ```python
    from openapi_client_core.auth import CredentialResolver

    # Initialize resolver (loads .env file by default)
    resolver = CredentialResolver()

    # Resolve API key from environment or .env file
    api_key = resolver.resolve(
        env_var_name="MY_API_KEY",
        default=None,
        required=True,
    )

    # Resolve with explicit value (highest priority)
    api_key = resolver.resolve(
        value="explicit-key-123",
        env_var_name="MY_API_KEY",  # Ignored when value is provided
    )

    # Resolve from file
    api_key = resolver.resolve_from_file(
        file_path="~/.config/myapp/api_key",
        env_var_name="MY_API_KEY_FILE",  # Path can come from env var
    )
    ```

Security Considerations:
    - Credentials are never logged in full (masked with ***)
    - Only source information is logged (env var name, file path, etc.)
    - File-based credentials have whitespace stripped
    - Thread-safe dotenv loading with lock
"""

import logging
import os
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv

from openapi_client_core.auth.exceptions import CredentialFileError, CredentialNotFoundError

logger = logging.getLogger(__name__)


class CredentialResolver:
    """Resolve credentials from multiple sources with priority ordering.

    This class provides a unified interface for resolving credentials from
    various sources including explicit values, environment variables, .env files,
    and defaults.

    The resolver uses a priority-based system where explicitly provided values
    take precedence over environment variables, which take precedence over
    .env file values, which finally take precedence over defaults.

    Attributes:
        _dotenv_loaded: Whether .env file has been loaded.
        _dotenv_lock: Thread lock for safe dotenv loading.

    Example:
        ```python
        resolver = CredentialResolver()

        # Simple resolution from environment
        api_key = resolver.resolve(env_var_name="API_KEY")

        # With fallback default
        timeout = resolver.resolve(env_var_name="REQUEST_TIMEOUT", default="30")

        # Required credential (raises if not found)
        secret = resolver.resolve(env_var_name="CLIENT_SECRET", required=True)
        ```
    """

    def __init__(self, dotenv_path: str | None = None, load_dotenv: bool = True):
        """Initialize credential resolver.

        Args:
            dotenv_path: Path to .env file. If None, searches parent directories
                for .env file (default behavior of python-dotenv).
            load_dotenv: Whether to load .env file. Set to False to skip
                .env file loading (useful for testing or when not using .env).
                Default is True.

        Example:
            ```python
            # Load .env from specific path
            resolver = CredentialResolver(dotenv_path="/app/.env")

            # Skip .env loading entirely
            resolver = CredentialResolver(load_dotenv=False)

            # Auto-discover .env (default)
            resolver = CredentialResolver()
            ```
        """
        self._dotenv_loaded = False
        self._dotenv_lock = Lock()
        self._dotenv_path = dotenv_path
        self._load_dotenv_enabled = load_dotenv

        # Load dotenv immediately if enabled
        if self._load_dotenv_enabled:
            self._ensure_dotenv_loaded()

    def _ensure_dotenv_loaded(self) -> None:
        """Ensure .env file is loaded (thread-safe).

        This method is called internally and uses a lock to ensure
        thread-safe loading of the .env file. It only loads once.
        """
        if self._dotenv_loaded:
            return

        with self._dotenv_lock:
            # Double-check pattern for thread safety
            if self._dotenv_loaded:
                return

            try:
                load_dotenv(dotenv_path=self._dotenv_path)
                self._dotenv_loaded = True
                logger.debug("Loaded .env file for credential resolution")
            except Exception as e:
                logger.warning(f"Failed to load .env file: {e}")
                # Don't fail - continue without .env
                self._dotenv_loaded = True  # Mark as attempted

    def _mask_credential(self, value: str | None) -> str:
        """Mask a credential value for safe logging.

        Args:
            value: The credential value to mask.

        Returns:
            Masked string ("***") if value exists, "None" otherwise.
        """
        if value is None:
            return "None"
        return "***"

    def resolve(
        self,
        *,
        value: str | None = None,
        env_var_name: str | None = None,
        default: str | None = None,
        required: bool = False,
        mask_in_logs: bool = True,
    ) -> str | None:
        """Resolve a credential from multiple sources.

        Resolution order (first match wins):
        1. Explicitly provided `value` parameter
        2. Environment variable (if `env_var_name` provided)
        3. .env file value (if .env loading enabled)
        4. Default value (if `default` provided)
        5. None (if not required) or raise error (if required)

        Args:
            value: Explicitly provided value (highest priority).
                If provided, all other sources are ignored.
            env_var_name: Environment variable name to check.
                Checks both os.environ and loaded .env file.
            default: Default value if not found elsewhere.
            required: If True, raises CredentialNotFoundError when
                credential cannot be resolved. Default is False.
            mask_in_logs: If True (default), masks credential values
                in log messages. Disable for non-sensitive values.

        Returns:
            Resolved credential value, or None if not found and not required.

        Raises:
            CredentialNotFoundError: If required=True and credential not found
                in any source.

        Example:
            ```python
            # Try multiple sources
            api_key = resolver.resolve(env_var_name="MY_API_KEY", default="dev-key-123", required=False)

            # Explicit value takes precedence
            api_key = resolver.resolve(
                value="override-key",
                env_var_name="MY_API_KEY",  # Ignored
                default="default-key",  # Ignored
            )

            # Required credential
            secret = resolver.resolve(
                env_var_name="CLIENT_SECRET",
                required=True,  # Raises if not found
            )
            ```
        """
        result = None
        source = None

        # Priority 1: Explicit value
        if value is not None:
            result = value
            source = "explicit parameter"

        # Priority 2: Environment variable
        elif env_var_name and env_var_name in os.environ:
            result = os.environ[env_var_name]
            source = f"environment variable '{env_var_name}'"

        # Priority 3: Default value
        elif default is not None:
            result = default
            source = "default value"

        # Log resolution result
        if mask_in_logs:
            masked_value = self._mask_credential(result)
            if result is not None:
                logger.debug(f"Resolved credential from {source}: {masked_value}")
        else:
            if result is not None:
                logger.debug(f"Resolved credential from {source}: {result}")

        # Handle required credentials
        if required and result is None:
            error_msg = "Required credential not found"
            if env_var_name:
                error_msg += f" (checked env var: {env_var_name})"
            raise CredentialNotFoundError(error_msg, env_var_name=env_var_name)

        return result

    def resolve_from_file(
        self,
        *,
        file_path: str | Path | None = None,
        env_var_name: str | None = None,
        required: bool = False,
    ) -> str | None:
        """Resolve credential from a file.

        This method reads a credential from a file, with support for:
        - User home directory expansion (~)
        - Environment variable expansion ($VAR or ${VAR})
        - Path provided directly or via environment variable

        The file contents are read, stripped of leading/trailing whitespace,
        and returned as a string.

        Args:
            file_path: Path to file containing credential.
                Supports ~ expansion and $VAR substitution.
            env_var_name: Environment variable containing the file path.
                If provided and file_path is None, reads path from this env var.
            required: If True, raises CredentialFileError when file
                cannot be read. Default is False.

        Returns:
            File contents (stripped of whitespace), or None if file not found
            and not required.

        Raises:
            CredentialFileError: If required=True and file cannot be read,
                or if permission denied, or other read errors occur.

        Example:
            ```python
            # Read from explicit path
            api_key = resolver.resolve_from_file(file_path="~/.config/myapp/api_key")

            # Read path from environment variable
            api_key = resolver.resolve_from_file(env_var_name="API_KEY_FILE")

            # Required file
            secret = resolver.resolve_from_file(file_path="$HOME/.secrets/client_secret", required=True)
            ```
        """
        # Determine the file path to use
        path_to_use = None

        if file_path is not None:
            path_to_use = str(file_path)
        elif env_var_name:
            # Try to get path from environment variable
            path_from_env = self.resolve(env_var_name=env_var_name, required=False)
            if path_from_env:
                path_to_use = path_from_env

        if path_to_use is None:
            if required:
                error_msg = "No file path provided for credential resolution"
                if env_var_name:
                    error_msg += f" (env var '{env_var_name}' not set)"
                raise CredentialFileError(error_msg)
            return None

        # Expand user home directory and environment variables
        expanded_path = os.path.expanduser(os.path.expandvars(path_to_use))
        path_obj = Path(expanded_path)

        try:
            # Read file contents
            content = path_obj.read_text().strip()
            logger.debug(f"Resolved credential from file: {path_obj} (***)")
            return content

        except FileNotFoundError:
            error_msg = f"Credential file not found: {path_obj}"
            if required:
                raise CredentialFileError(error_msg) from None
            logger.debug(error_msg)
            return None

        except PermissionError:
            error_msg = f"Permission denied reading credential file: {path_obj}"
            if required:
                raise CredentialFileError(error_msg) from None
            logger.warning(error_msg)
            return None

        except Exception as e:
            error_msg = f"Error reading credential file {path_obj}: {e}"
            if required:
                raise CredentialFileError(error_msg) from e
            logger.warning(error_msg)
            return None
