"""Pytest configuration and shared fixtures for openapi-client-core tests."""

import pytest


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """Auto-cleanup: Clear test-related environment variables before each test.

    This prevents test pollution when testing credential resolution.
    """
    import os

    # Store keys that look like test-related env vars
    test_prefixes = ("TEST_", "API_", "CLIENT_", "OPENAPI_")

    for key in list(os.environ.keys()):
        if any(key.startswith(prefix) for prefix in test_prefixes):
            monkeypatch.delenv(key, raising=False)

    yield
