# openapi-client-core

**Shared runtime library for Python OpenAPI clients**

[![CI](https://github.com/dougborg/openapi-client-core/actions/workflows/ci.yml/badge.svg)](https://github.com/dougborg/openapi-client-core/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/openapi-client-core.svg)](https://badge.fury.io/py/openapi-client-core)
[![Python versions](https://img.shields.io/pypi/pyversions/openapi-client-core.svg)](https://pypi.org/project/openapi-client-core/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Vision

`openapi-client-core` provides battle-tested patterns for building Python OpenAPI clients. Instead of duplicating retry
logic, error handling, and testing utilities across every client, share a common foundation.

**Features**:

- 🔄 **Composable transport layers** (retry, pagination, error logging, auth)
- 🔁 **3 retry strategies** (idempotent-only, rate-limit-aware, all-methods)
- 🛡️ **Error handling** with RFC 7807 ProblemDetails and null field detection
- 🔐 **Multi-source authentication** (param → env → .env → netrc)
- 🧪 **Testing utilities** (fixtures, mocks, factories)
- ⚡ **Async-first** with httpx

## Installation

```bash
pip install openapi-client-core
```

Or with UV:

```bash
uv add openapi-client-core
```

## Quick Start

### Creating a Resilient Client

```python
from openapi_client_core.transport import create_transport_stack
from openapi_client_core.auth import CredentialResolver
from your_generated_client import Client

# Resolve credentials from multiple sources
resolver = CredentialResolver()
api_key = resolver.resolve(
    param_value=None,  # Will check env vars and .env file
    env_var_name="MY_API_KEY",
    netrc_host="api.example.com",
)

# Create transport stack with retry, error logging, pagination
transport = create_transport_stack(
    base_url="https://api.example.com",
    retry_strategy="rate_limited",  # or "idempotent_only" or "all_methods"
    enable_pagination=True,
    enable_error_logging=True,
    enable_null_field_detection=True,
)

# Initialize your generated client with enhanced transport
client = Client(
    base_url="https://api.example.com",
    token=api_key,
    transport=transport,
)
```

### Using the unwrap() Helper

```python
from openapi_client_core.utils import unwrap
from openapi_client_core.exceptions import NotFoundError, ValidationError

# Raises specific exceptions on error
try:
    data = unwrap(client.get_resource(id=123))
    print(f"Got resource: {data}")
except NotFoundError:
    print("Resource not found")
except ValidationError as e:
    print(f"Validation failed: {e.problem_details}")

# Or return None on error
data = unwrap(client.get_resource(id=123), raise_on_error=False)
if data is None:
    print("Request failed")
```

### Testing Your Client

```python
import pytest
from openapi_client_core.testing import (
    mock_api_credentials,
    create_mock_response,
    create_error_response,
)

def test_client_handles_404(mock_api_credentials):
    """Test client gracefully handles 404 errors."""
    # Fixtures provided by openapi-client-core
    client = MyClient(**mock_api_credentials)

    # Mock a 404 response
    response = create_error_response("404")

    # Test your error handling
    with pytest.raises(NotFoundError):
        unwrap(response)
```

## Why openapi-client-core?

### Before

Every OpenAPI client duplicates the same patterns:

```python
# In client A
class RateLimitAwareRetry(Retry):
    # 60 lines of retry logic...

# In client B
class RateLimitAwareRetry(Retry):
    # Same 60 lines duplicated...

# In client C
class RateLimitAwareRetry(Retry):
    # Same 60 lines again...
```

**Problems**:

- ❌ Code duplication (hundreds of lines per client)
- ❌ Bug fixes require updating every client
- ❌ New clients don't benefit from lessons learned
- ❌ Testing utilities re-implemented everywhere

### After

Share the battle-tested core:

```python
from openapi_client_core.transport import create_transport_stack

transport = create_transport_stack(
    base_url=base_url,
    retry_strategy="rate_limited",
    enable_pagination=True,
)
```

**Benefits**:

- ✅ **35-40% less code** in each client
- ✅ **Shared maintenance**: Fix once, benefit everywhere
- ✅ **Battle-tested patterns**: Learned from real-world usage
- ✅ **Fast development**: New clients in \<5 minutes

## Core Components

### Transport Layers

Composable async HTTP transport middleware:

```python
from openapi_client_core.transport import (
    ErrorLoggingTransport,
    RetryTransport,
    PaginationTransport,
    CustomHeaderAuthTransport,
)

# Stack them in any order
transport = CustomHeaderAuthTransport(
    headers_dict={"api-key": "..."},
    wrapped_transport=RetryTransport(
        retry_strategy="idempotent_only",
        wrapped_transport=ErrorLoggingTransport(
            enable_null_field_detection=True,
            wrapped_transport=httpx.AsyncHTTPTransport(),
        ),
    ),
)

# Or use the factory for common patterns
from openapi_client_core.transport import create_transport_stack

transport = create_transport_stack(
    base_url="https://api.example.com",
    retry_strategy="rate_limited",
    custom_auth_headers={"api-key": "..."},
)
```

### Retry Strategies

Three retry strategies for different API behaviors:

1. **IdempotentOnlyRetry** (safest)

   - Retries only GET, HEAD, OPTIONS on 5xx errors
   - Use when duplicates are dangerous

1. **RateLimitAwareRetry** (recommended)

   - Retries all methods on 429 (rate limit)
   - Retries GET, HEAD, PUT, DELETE on 5xx
   - Best for modern REST APIs

1. **AllMethodsRetry** (use with caution)

   - Retries everything
   - Only use with idempotency keys

### Authentication

Multi-source credential resolution:

```python
from openapi_client_core.auth import CredentialResolver

resolver = CredentialResolver()

# Checks in order: param → env var → .env file → ~/.netrc
api_key = resolver.resolve(
    param_value=None,
    env_var_name="API_KEY",
    netrc_host="api.example.com",
)
```

Custom header authentication:

```python
from openapi_client_core.transport import CustomHeaderAuthTransport

transport = CustomHeaderAuthTransport(
    headers_dict={
        "api-auth-id": tenant_id,
        "api-auth-signature": tenant_name,
    },
    wrapped_transport=base_transport,
)
```

### Error Handling

Structured exceptions with RFC 7807 ProblemDetails:

```python
from openapi_client_core.errors import (
    APIError,
    UnauthorizedError,   # 401
    ForbiddenError,      # 403
    NotFoundError,       # 404
    ValidationError,     # 422
    BadRequestError,     # 400
    ConflictError,       # 409
    RateLimitError,      # 429
    ServerError,         # 5xx
    raise_for_status,
    detect_null_fields,
)
import httpx

# Automatic RFC 7807 parsing
response = httpx.get("https://api.example.com/users/123")
try:
    raise_for_status(response)
except NotFoundError as e:
    # Access structured error details
    print(e.status_code)  # 404
    print(e.problem_detail.title)  # "Resource Not Found"
    print(e.problem_detail.detail)  # "User with id 123 does not exist"
    print(e.problem_detail.type)  # "https://api.example.com/problems/not-found"

# ValidationError with structured errors
try:
    raise_for_status(response)
except ValidationError as e:
    print(e.validation_errors)  # [{"field": "email", "message": "Invalid"}]

# RateLimitError with retry timing
try:
    raise_for_status(response)
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")

# Detect null fields in response data
data = {"user": {"name": "John", "email": None}}
null_fields = detect_null_fields(data)
print(null_fields)  # ["user.email"]
```

**Null field detection**:

```python
from openapi_client_core.errors import detect_null_fields, NullFieldError

# Detect null fields in API response
data = {
    "user": {
        "name": "John",
        "email": None,
        "address": {
            "city": None,
            "street": "123 Main St"
        }
    }
}

null_paths = detect_null_fields(data)
print(null_paths)  # ["user.email", "user.address.city"]

# Raise helpful error for null fields
if null_paths:
    raise NullFieldError(
        message=f"Found {len(null_paths)} null field(s): {null_paths}",
        field_path=null_paths[0]
    )
```

### Testing Utilities

Pre-built fixtures and factories:

```python
import pytest
from openapi_client_core.testing import (
    mock_api_credentials,
    create_mock_response,
    create_error_response,
    create_paginated_mock_handler,
)

@pytest.fixture
def my_client(mock_api_credentials):
    return MyClient(**mock_api_credentials)

def test_pagination(my_client):
    handler = create_paginated_mock_handler([
        [{"id": 1}, {"id": 2}],  # Page 1
        [{"id": 3}, {"id": 4}],  # Page 2
    ])
    # Test with mock handler...
```

## Documentation

Full documentation available at: https://dougborg.github.io/openapi-client-core

- [Getting Started](https://dougborg.github.io/openapi-client-core/getting-started/)
- [Transport Layer Guide](https://dougborg.github.io/openapi-client-core/transport/)
- [Authentication Patterns](https://dougborg.github.io/openapi-client-core/auth/)
- [Error Handling](https://dougborg.github.io/openapi-client-core/errors/)
- [Testing Guide](https://dougborg.github.io/openapi-client-core/testing/)
- [API Reference](https://dougborg.github.io/openapi-client-core/reference/)

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/dougborg/openapi-client-core.git
cd openapi-client-core

# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --all-extras
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=openapi_client_core --cov-report=term-missing

# Run only unit tests
uv run pytest -m unit

# Run specific test file
uv run pytest tests/unit/test_transport/test_retry.py
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type check
uv run ty check
```

### Documentation

```bash
# Build docs locally
uv run mkdocs build

# Serve docs locally
uv run mkdocs serve
# Open http://127.0.0.1:8000
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas for Contribution

- 🐛 Bug fixes and improvements
- 📚 Documentation enhancements
- ✨ New transport middleware patterns
- 🧪 Additional testing utilities
- 🎨 Usage examples and tutorials

## Clients Using This Library

- [katana-openapi-client](https://github.com/dougborg/katana-openapi-client) - Katana MRP/ERP API client
- [stocktrim-api-client](https://github.com/dougborg/stocktrim-api-client) - StockTrim inventory management API client

## License

MIT License - see [LICENSE](LICENSE) for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Acknowledgments

This library extracts battle-tested patterns from:

- [katana-openapi-client](https://github.com/dougborg/katana-openapi-client): Pagination, rate limiting, event hooks
- [stocktrim-api-client](https://github.com/dougborg/stocktrim-api-client): Null field detection, idempotent-only retry,
  code generation patterns

Special thanks to the OpenAPI and httpx communities for providing excellent foundations.
