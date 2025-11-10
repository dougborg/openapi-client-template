"""Testing utilities for OpenAPI clients.

This module provides pytest fixtures, mock factories, and test helpers
to make testing OpenAPI clients easier.

Modules:
    fixtures: Pre-built pytest fixtures
    factories: Mock response and handler factories

Example:
    ```python
    from openapi_client_core.testing import (
        mock_api_credentials,
        create_mock_response,
        create_error_response,
    )


    def test_client_handles_404(mock_api_credentials):
        client = MyClient(**mock_api_credentials)
        response = create_error_response("404")
        # Test error handling...
    ```
"""

__all__ = []
