"""Tests for base client classes."""

from openapi_client_core.client import BaseOpenAPIClient


def test_base_client_instantiation():
    """Test that BaseOpenAPIClient can be instantiated."""
    client = BaseOpenAPIClient()
    assert client is not None


def test_base_client_is_subclassable():
    """Test that BaseOpenAPIClient can be subclassed."""

    class MyClient(BaseOpenAPIClient):
        pass

    client = MyClient()
    assert isinstance(client, BaseOpenAPIClient)
