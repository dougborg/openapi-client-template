"""Test basic package functionality."""

import openapi_client_core


def test_version():
    """Test that package version is defined."""
    assert hasattr(openapi_client_core, "__version__")
    assert openapi_client_core.__version__ == "0.1.0"
