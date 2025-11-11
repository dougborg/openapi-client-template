"""Tests for credential resolution exceptions."""

import pytest

from openapi_client_core.auth.exceptions import (
    CredentialError,
    CredentialFileError,
    CredentialNotFoundError,
)


class TestCredentialError:
    """Test CredentialError base exception."""

    def test_can_be_raised(self):
        """Test that CredentialError can be raised."""
        with pytest.raises(CredentialError):
            raise CredentialError("Test error")

    def test_exception_message(self):
        """Test that exception message is preserved."""
        try:
            raise CredentialError("Custom error message")
        except CredentialError as e:
            assert str(e) == "Custom error message"


class TestCredentialNotFoundError:
    """Test CredentialNotFoundError exception."""

    def test_can_be_raised(self):
        """Test that CredentialNotFoundError can be raised."""
        with pytest.raises(CredentialNotFoundError):
            raise CredentialNotFoundError("Test error")

    def test_is_credential_error(self):
        """Test that CredentialNotFoundError is a CredentialError."""
        with pytest.raises(CredentialError):
            raise CredentialNotFoundError("Test error")

    def test_exception_message(self):
        """Test that exception message is preserved."""
        try:
            raise CredentialNotFoundError("API key not found")
        except CredentialNotFoundError as e:
            assert str(e) == "API key not found"

    def test_env_var_name_attribute(self):
        """Test that env_var_name attribute is set."""
        try:
            raise CredentialNotFoundError("Test error", env_var_name="MY_API_KEY")
        except CredentialNotFoundError as e:
            assert e.env_var_name == "MY_API_KEY"

    def test_env_var_name_optional(self):
        """Test that env_var_name is optional."""
        try:
            raise CredentialNotFoundError("Test error")
        except CredentialNotFoundError as e:
            assert e.env_var_name is None


class TestCredentialFileError:
    """Test CredentialFileError exception."""

    def test_can_be_raised(self):
        """Test that CredentialFileError can be raised."""
        with pytest.raises(CredentialFileError):
            raise CredentialFileError("Test error")

    def test_is_credential_error(self):
        """Test that CredentialFileError is a CredentialError."""
        with pytest.raises(CredentialError):
            raise CredentialFileError("Test error")

    def test_exception_message(self):
        """Test that exception message is preserved."""
        try:
            raise CredentialFileError("File not found: /path/to/file")
        except CredentialFileError as e:
            assert str(e) == "File not found: /path/to/file"
