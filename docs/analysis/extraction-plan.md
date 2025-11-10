# OpenAPI Client Core - Extraction & Implementation Plan

**Status**: Approved
**Created**: 2025-11-09
**Based on**: [Katana Inventory](../inventories/katana-inventory.md) and [StockTrim Inventory](../inventories/stocktrim-inventory.md)
**Related Issues**: [#2](https://github.com/dougborg/openapi-client-template/issues/2), [#8](https://github.com/dougborg/openapi-client-template/issues/8), [#9](https://github.com/dougborg/openapi-client-template/issues/9), [#10](https://github.com/dougborg/openapi-client-template/issues/10)

## Executive Summary

After comprehensive analysis of both katana and stocktrim OpenAPI client repositories, we've identified **35+ extractable patterns** that will form the foundation of `openapi-client-core` and enhance the template. This extraction will:

- **Reduce client code by 35-40%** (620 lines from katana, 671 from stocktrim)
- **Standardize best practices** across all generated clients
- **Eliminate code duplication** between clients
- **Enable shared maintenance** and bug fixes

### Key Findings

**Critical Overlaps** (Extract to Core ⭐⭐⭐⭐⭐):
- Transport layer architecture (both use 4-layer composable pattern)
- Retry logic (2 variants: Katana's rate-limit-aware vs StockTrim's idempotent-only)
- Error logging transport (StockTrim's null-field detection is superior)
- Authentication patterns (Bearer token vs custom headers)
- Test fixtures and helpers (both have excellent patterns)

**Template Improvements** (⭐⭐⭐⭐⭐):
- CI/CD workflows (combine Katana's 4 + StockTrim's 5 workflows)
- Project automation (StockTrim's poethepoet wins over Katana's Makefiles)
- Pre-commit hooks (combine best features from both)
- Documentation (both use MkDocs Material, combine structures)
- Code generation (StockTrim's 1066-line script is comprehensive)

**Unique Innovations**:
- **StockTrim**: Null field detection, spec fixing automation, upsert pattern support
- **Katana**: Pagination transport, rate limiting, netrc credential resolution, 7 GitHub Copilot agents

## 1. Core Library Extraction Plan

### 1.1 Transport Layer Architecture ⭐⭐⭐⭐⭐

**Priority**: CRITICAL (Phase 1)

**Pattern**: Both implement composable 4-layer transport architecture

**Katana Stack**:
```
Base HTTP → ErrorLogging → Pagination → RateLimitAwareRetry
```

**StockTrim Stack**:
```
Base HTTP → AuthHeader → ErrorLogging → IdempotentOnlyRetry
```

**Extraction Strategy**:

```python
# openapi-client-core/transport/base.py
class BaseTransport(AsyncHTTPTransport):
    """Base class for all transport middleware."""

# openapi-client-core/transport/error_logging.py
class ErrorLoggingTransport(AsyncHTTPTransport):
    """Generic error logging with null field detection (StockTrim innovation)."""

# openapi-client-core/transport/retry.py
class RetryTransport(AsyncHTTPTransport):
    """Configurable retry transport with multiple strategies."""
    # Variants: IdempotentOnly, RateLimitAware, AllMethods

# openapi-client-core/transport/pagination.py (from Katana)
class PaginationTransport(AsyncHTTPTransport):
    """Automatic pagination for GET requests."""

# openapi-client-core/transport/auth.py (from StockTrim)
class CustomHeaderAuthTransport(AsyncHTTPTransport):
    """Add custom authentication headers."""

# openapi-client-core/transport/factory.py
def create_transport_stack(
    base_url: str,
    retry_strategy: Literal["idempotent_only", "rate_limited", "all_methods"] = "rate_limited",
    enable_pagination: bool = False,
    enable_error_logging: bool = True,
    enable_null_field_detection: bool = True,
    custom_auth_headers: dict[str, str] | None = None,
    max_pages: int = 100,
) -> AsyncHTTPTransport:
    """Factory to create composable transport stack."""
```

**Files to Extract**:
- Katana: `src/katana_public_api_client/katana_client.py:139-362` (Pagination), `99-138` (Error Logging), `65-98` (Retry)
- StockTrim: `src/stocktrim_public_api_client/stocktrim_client.py:25-378` (Error Logging with null detection), `379-430` (Retry), `483-517` (Auth)

**Impact**: -460 lines from Katana, -441 lines from StockTrim

---

### 1.2 Retry Logic Variants ⭐⭐⭐⭐⭐

**Priority**: CRITICAL (Phase 1)

**Comparison**:

| Feature | Katana (RateLimitAware) | StockTrim (IdempotentOnly) |
|---------|-------------------------|---------------------------|
| Idempotent Methods | GET, HEAD, PUT, DELETE, OPTIONS, TRACE | GET, HEAD, OPTIONS, TRACE |
| Rate Limiting (429) | Retries ALL methods | No 429 handling |
| Server Errors (5xx) | Only idempotent | Only idempotent |
| Status Codes | [429, 502, 503, 504] | [502, 503, 504] |
| Backoff | Exponential (1, 2, 4, 8, 16s) | Exponential (1, 2, 4, 8, 16s) |
| Retry-After | Respects header | Not mentioned |

**Extraction Strategy**:

```python
# openapi-client-core/retry.py
class IdempotentOnlyRetry(Retry):
    """Retry only truly idempotent methods (GET, HEAD, OPTIONS) on 5xx.

    Safest option - will never retry operations that could cause duplicates.
    Use when API does NOT handle idempotency keys and duplicates are dangerous.
    """
    IDEMPOTENT_METHODS = frozenset(["HEAD", "GET", "OPTIONS", "TRACE"])
    RETRY_STATUS_CODES = frozenset([502, 503, 504])

class RateLimitAwareRetry(Retry):
    """Retry all methods on 429, standard idempotent on 5xx.

    Best for modern APIs with rate limiting.
    Assumes PUT/DELETE are idempotent (common REST pattern).
    """
    IDEMPOTENT_METHODS = frozenset(["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"])
    RETRY_STATUS_CODES = frozenset([429, 502, 503, 504])

    def is_retryable_status_code(self, status_code: int) -> bool:
        if status_code == 429:  # Always retry rate limits
            return True
        # Only retry 5xx for idempotent methods
        return (status_code in self.RETRY_STATUS_CODES and
                self._current_method in self.IDEMPOTENT_METHODS)

class AllMethodsRetry(Retry):
    """Retry all methods on all configured status codes (DANGEROUS).

    Use ONLY when:
    - API has idempotency keys for all operations
    - Duplicates are handled safely server-side
    - You understand the risks
    """
```

**Design Decision**: Provide all 3 strategies, template defaults to `RateLimitAwareRetry`

**Files to Extract**:
- Katana: `src/katana_public_api_client/katana_client.py:65-98`
- StockTrim: `src/stocktrim_public_api_client/stocktrim_client.py:379-430`

**Impact**: -60 lines from Katana, -52 lines from StockTrim

---

### 1.3 Error Handling & Translation ⭐⭐⭐⭐⭐

**Priority**: CRITICAL (Phase 1)

**Winner**: StockTrim (more comprehensive)

**Comparison**:

| Feature | Katana | StockTrim |
|---------|--------|-----------|
| Error Models | DetailedErrorResponse (422), ErrorResponse (4xx) | ProblemDetails (RFC 7807) |
| Exception Hierarchy | Not shown | APIError → 5 subclasses |
| Unwrap Function | Not shown | ✓ (with overloads) |
| Null Field Detection | No | ✓ (UNIQUE) |
| Fix Suggestions | No | ✓ (actionable) |

**Extraction Strategy**:

```python
# openapi-client-core/exceptions.py
class APIError(Exception):
    """Base API error with status code and optional ProblemDetails."""
    def __init__(
        self,
        message: str,
        status_code: int,
        problem_details: ProblemDetails | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.problem_details = problem_details

class AuthenticationError(APIError):
    """401 Unauthorized"""

class PermissionError(APIError):
    """403 Forbidden"""

class NotFoundError(APIError):
    """404 Not Found"""

class ValidationError(APIError):
    """400 Bad Request, 422 Unprocessable Entity"""

class ServerError(APIError):
    """5xx Server Errors"""

# openapi-client-core/utils.py
@overload
def unwrap(response: Response[T], raise_on_error: Literal[True] = True) -> T: ...

@overload
def unwrap(response: Response[T], raise_on_error: Literal[False]) -> T | None: ...

def unwrap(response: Response[T], raise_on_error: bool = True) -> T | None:
    """Extract data from Response, raising specific exceptions on error.

    Args:
        response: The API response object
        raise_on_error: If True, raise exception on error. If False, return None.

    Returns:
        Parsed response data or None (if raise_on_error=False and error occurred)

    Raises:
        AuthenticationError: On 401
        PermissionError: On 403
        NotFoundError: On 404
        ValidationError: On 400/422
        ServerError: On 5xx
    """
```

**Files to Extract**:
- StockTrim: `src/stocktrim_public_api_client/utils.py:1-150` (exception hierarchy + unwrap)

**Impact**: -150 lines from StockTrim

---

### 1.4 Null Field Detection ⭐⭐⭐⭐⭐

**Priority**: HIGH (Phase 2, but could move to Phase 1)

**Unique Innovation**: StockTrim's transport layer detects null fields BEFORE parsing errors occur

**Implementation**:

```python
# openapi-client-core/transport/error_logging.py
def _find_null_fields(data: Any, path: str = "") -> list[str]:
    """Recursively find null fields in JSON response.

    Critical for debugging APIs that return null for fields
    marked as required in OpenAPI spec.
    """
    null_fields = []
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if value is None:
                null_fields.append(current_path)
            else:
                null_fields.extend(_find_null_fields(value, current_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            null_fields.extend(_find_null_fields(item, f"{path}[{i}]"))
    return null_fields

class ErrorLoggingTransport(AsyncHTTPTransport):
    def __init__(self, *, enable_null_detection: bool = True, **kwargs):
        self.enable_null_detection = enable_null_detection
        super().__init__(**kwargs)

    def log_parsing_error(self, error: Exception, response: httpx.Response):
        """Log parsing errors with actionable fix suggestions."""
        logger.error(f"Failed to parse response: {error}")

        if self.enable_null_detection and isinstance(error, (TypeError, AttributeError)):
            try:
                null_fields = _find_null_fields(response.json())
                if null_fields:
                    logger.error(f"Found {len(null_fields)} null field(s): {null_fields}")
                    logger.error("Possible fixes:")
                    logger.error("  1. Add fields to nullable list in regenerate_client.py")
                    logger.error("  2. Update OpenAPI spec with 'nullable: true'")
                    logger.error("  3. Handle null values defensively in helper methods")
            except Exception:
                pass  # Failed to parse JSON, skip null detection
```

**Files to Extract**:
- StockTrim: `src/stocktrim_public_api_client/stocktrim_client.py:46-95` (null detection logic)

**Impact**: This is a unique innovation worth ~50 lines

---

### 1.5 Pagination Handling ⭐⭐⭐⭐

**Priority**: HIGH (Phase 2)

**Source**: Katana (StockTrim uses manual pagination in helpers)

**Implementation**:

```python
# openapi-client-core/transport/pagination.py
class PaginationTransport(AsyncHTTPTransport):
    """Automatic pagination for GET requests with page/limit params.

    Supports multiple pagination metadata formats:
    1. X-Pagination JSON header
    2. Individual headers (X-Total-Pages, X-Current-Page)
    3. Response body `pagination` field
    4. Response body `meta.pagination` field
    """

    def __init__(
        self,
        *,
        max_pages: int = 100,
        page_param: str = "page",
        limit_param: str = "limit",
        enable_auto_pagination: bool = True,
        **kwargs
    ):
        self.max_pages = max_pages
        self.page_param = page_param
        self.limit_param = limit_param
        self.enable_auto_pagination = enable_auto_pagination
        super().__init__(**kwargs)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Handle paginated GET requests automatically."""
        if request.method != "GET" or not self.enable_auto_pagination:
            return await self._wrapped_transport.handle_async_request(request)

        # Collect all pages
        all_data = []
        for page_num in range(1, self.max_pages + 1):
            paginated_request = self._add_pagination_params(request, page_num)
            response = await self._wrapped_transport.handle_async_request(paginated_request)

            pagination_info = self._extract_pagination_info(response)
            items = self._extract_items(response)
            all_data.extend(items)

            if self._is_last_page(pagination_info, page_num):
                break

        # Return combined response
        return self._create_combined_response(response, all_data)
```

**Files to Extract**:
- Katana: `src/katana_public_api_client/katana_client.py:139-362`

**Impact**: -220 lines from Katana

---

### 1.6 Authentication Patterns ⭐⭐⭐⭐⭐

**Priority**: CRITICAL (Phase 1)

**Comparison**:

| Feature | Katana | StockTrim |
|---------|--------|-----------|
| Auth Type | Bearer token | Custom headers (multi-header) |
| Credential Sources | param → env → .env → netrc | param → env → .env |
| Netrc Support | ✓ (UNIQUE) | No |
| Multi-Header | No | ✓ (UNIQUE) |

**Extraction Strategy**:

```python
# openapi-client-core/auth/credential_resolver.py
class CredentialResolver:
    """Multi-source credential resolution with priority order.

    Resolution order:
    1. Explicit parameter value
    2. Environment variable
    3. .env file (via python-dotenv)
    4. Netrc file (if hostname provided)
    """

    def resolve(
        self,
        param_value: str | None = None,
        env_var_name: str | None = None,
        netrc_host: str | None = None,
    ) -> str | None:
        """Resolve credential from multiple sources."""
        # 1. Explicit parameter
        if param_value:
            return param_value

        # 2. Environment variable
        if env_var_name:
            value = os.getenv(env_var_name)
            if value:
                return value

        # 3. .env file (python-dotenv loads automatically)
        # Already checked via os.getenv above

        # 4. Netrc file
        if netrc_host:
            return self._read_from_netrc(netrc_host)

        return None

    def _read_from_netrc(self, host: str) -> str | None:
        """Read password from ~/.netrc file."""
        try:
            import netrc
            from pathlib import Path

            parsed_host = urlparse(host).hostname if "://" in host else host.split("/")[0]
            auth = netrc.netrc(Path.home() / ".netrc")
            authenticators = auth.authenticators(parsed_host)

            if authenticators:
                _login, _account, password = authenticators
                return password
        except (FileNotFoundError, netrc.NetrcParseError):
            return None

# openapi-client-core/auth/header_auth.py
class CustomHeaderAuthTransport(AsyncHTTPTransport):
    """Add custom authentication headers to requests.

    Supports multi-header auth patterns (e.g., api-auth-id + signature).
    """

    def __init__(self, headers_dict: dict[str, str], **kwargs):
        self.custom_headers = headers_dict
        super().__init__(**kwargs)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Add custom headers to request."""
        for key, value in self.custom_headers.items():
            request.headers[key] = value
        return await self._wrapped_transport.handle_async_request(request)
```

**Files to Extract**:
- Katana: `src/katana_public_api_client/katana_client.py:672-725` (netrc)
- StockTrim: `src/stocktrim_public_api_client/stocktrim_client.py:483-517` (custom headers)

**Impact**: -50 lines from Katana, -35 lines from StockTrim

---

### 1.7 Test Fixtures and Helpers ⭐⭐⭐⭐⭐

**Priority**: CRITICAL (Phase 1)

**Best from Both**:
- Katana: Pagination test helpers
- StockTrim: Error response fixtures, clear_env autouse

**Extraction Strategy**:

```python
# openapi-client-core/testing/fixtures.py
import pytest
import httpx

@pytest.fixture
def mock_api_credentials():
    """Provide mock API credentials.

    Override in client projects with specific credential structure.
    """
    return {
        "api_key": "test-api-key",
        "base_url": "https://api.test.example.com",
    }

@pytest.fixture
def mock_transport(mock_transport_handler):
    """Create mock HTTP transport."""
    return httpx.MockTransport(mock_transport_handler)

@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """Auto-cleanup: Clear environment variables before each test."""
    # Store current env
    original_env = os.environ.copy()

    # Clear relevant vars
    for key in list(os.environ.keys()):
        if key.startswith(("API_", "CLIENT_", "TEST_")):
            monkeypatch.delenv(key, raising=False)

    yield

    # Env is automatically restored by monkeypatch

# openapi-client-core/testing/factories.py
def create_mock_response(
    status_code: int = 200,
    json_data: dict | list | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Factory for creating mock HTTP responses."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        headers=headers or {},
    )

def create_error_response(error_type: str) -> httpx.Response:
    """Factory for common error responses.

    Args:
        error_type: One of "401", "404", "422", "500"
    """
    error_responses = {
        "401": (401, {"detail": "Unauthorized"}),
        "404": (404, {"detail": "Not found"}),
        "422": (422, {"detail": [{"loc": ["body", "field"], "msg": "Invalid"}]}),
        "500": (500, {"detail": "Internal server error"}),
    }
    status_code, json_data = error_responses[error_type]
    return create_mock_response(status_code, json_data)

def create_paginated_mock_handler(pages_data: list[list[dict]]):
    """Create mock handler for pagination testing.

    Args:
        pages_data: List of pages, each page is a list of items

    Returns:
        Mock transport handler function
    """
    def handler(request: httpx.Request) -> httpx.Response:
        # Extract page number from query params
        url = httpx.URL(request.url)
        page = int(url.params.get("page", "1"))

        if page > len(pages_data):
            return create_mock_response(200, {"data": []})

        return create_mock_response(
            200,
            {
                "data": pages_data[page - 1],
                "pagination": {
                    "current_page": page,
                    "total_pages": len(pages_data),
                }
            }
        )
    return handler
```

**Files to Extract**:
- Katana: `tests/conftest.py` (select fixtures)
- StockTrim: `tests/conftest.py` (error fixtures, clear_env)

**Impact**: -150 lines from Katana, -120 lines from StockTrim

---

### 1.8 Client Base Pattern ⭐⭐⭐⭐⭐

**Priority**: CRITICAL (Phase 1)

**Pattern**: Both use layered inheritance with enhanced client

**Extraction Strategy**:

```python
# openapi-client-core/client.py
class EnhancedClient:
    """Mixin for enhanced client functionality.

    Provides standard patterns for:
    - Transport stack creation
    - Credential resolution
    - Configuration management
    """

    def _create_transport_stack(
        self,
        base_url: str,
        retry_strategy: str = "rate_limited",
        enable_pagination: bool = False,
        enable_error_logging: bool = True,
        **kwargs,
    ) -> AsyncHTTPTransport:
        """Create resilient transport stack with standard patterns."""
        from openapi_client_core.transport import create_transport_stack

        return create_transport_stack(
            base_url=base_url,
            retry_strategy=retry_strategy,
            enable_pagination=enable_pagination,
            enable_error_logging=enable_error_logging,
            **kwargs,
        )

    def _resolve_credentials(
        self,
        param_values: dict[str, str | None],
        env_vars: dict[str, str],
        netrc_host: str | None = None,
    ) -> dict[str, str]:
        """Resolve credentials from multiple sources."""
        from openapi_client_core.auth import CredentialResolver

        resolver = CredentialResolver()
        resolved = {}

        for key, param_value in param_values.items():
            env_var = env_vars.get(key)
            resolved[key] = resolver.resolve(
                param_value=param_value,
                env_var_name=env_var,
                netrc_host=netrc_host,
            )

        return resolved
```

**Usage in Template**:

```python
# Template generates:
from openapi_client_core.client import EnhancedClient

class {{ api_service | title }}Client(AuthenticatedClient, EnhancedClient):
    """Enhanced client with transport stack and credential resolution."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.example.com",
        enable_pagination: bool = True,
        **kwargs,
    ):
        # Resolve credentials
        credentials = self._resolve_credentials(
            param_values={"api_key": api_key},
            env_vars={"api_key": "{{ api_service | upper }}_API_KEY"},
            netrc_host=base_url,
        )

        # Create transport stack
        transport = self._create_transport_stack(
            base_url=base_url,
            enable_pagination=enable_pagination,
        )

        # Initialize parent
        super().__init__(
            base_url=base_url,
            token=credentials["api_key"],
            transport=transport,
            **kwargs,
        )
```

**Impact**: Pattern enabler, simplifies generated client code

---

## 2. Template Enhancement Plan

### 2.1 CI/CD Workflows ⭐⭐⭐⭐⭐

**Priority**: CRITICAL

**Strategy**: Combine best features from both repos

#### ci.yml (Combine Both)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

jobs:
  # From Katana: Smart change detection
  changes:
    runs-on: ubuntu-latest
    outputs:
      src: {% raw %}${{ steps.filter.outputs.src }}{% endraw %}
      tests: {% raw %}${{ steps.filter.outputs.tests }}{% endraw %}
    steps:
      - uses: actions/checkout@v5
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            src:
              - 'src/**'
            tests:
              - 'tests/**'

  # From StockTrim: Matrix testing
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["{{ min_python_version }}", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: {% raw %}${{ matrix.python-version }}{% endraw %}
      - uses: astral-sh/setup-uv@v7

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Run tests with coverage
        run: uv run pytest --cov={{ package_name }} --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v5
        if: {% raw %}${{ matrix.python-version == '{{ min_python_version }}' }}{% endraw %}
        with:
          file: ./coverage.xml

  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "{{ min_python_version }}"
      - uses: astral-sh/setup-uv@v7

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Check formatting
        run: uv run ruff format --check .

      - name: Lint
        run: uv run ruff check .

      - name: Type check
        run: uv run ty check
```

#### release.yml (Use StockTrim's Sophisticated Pattern)

```yaml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  id-token: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - uses: astral-sh/setup-uv@v7

      - name: Semantic Release
        id: release
        uses: python-semantic-release/python-semantic-release@v9
        with:
          github_token: {% raw %}${{ secrets.GITHUB_TOKEN }}{% endraw %}

      - name: Publish to PyPI
        if: steps.release.outputs.released == 'true'
        run: |
          uv build
          uv publish
```

#### security.yml (StockTrim's Comprehensive Approach)

```yaml
name: Security

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

permissions:
  contents: read
  security-events: write

jobs:
  trivy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: returntocorp/semgrep-action@v1
        with:
          config: auto

  dependency-review:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v5
      - uses: actions/dependency-review-action@v4
```

**Impact**: Best-in-class CI/CD for all generated clients

---

### 2.2 Task Runner (poethepoet) ⭐⭐⭐⭐⭐

**Priority**: CRITICAL

**Winner**: StockTrim (cross-platform, task composition)

**Template Configuration**:

```toml
[tool.poe.tasks]
# Formatting
format-python = "ruff format ."
format-markdown = "mdformat README.md docs/**/*.md --wrap 88"
format = ["format-python", "format-markdown"]

# Format checking
format-python-check = "ruff format --check ."
format-markdown-check = "mdformat --check README.md docs/**/*.md --wrap 88"
format-check = ["format-python-check", "format-markdown-check"]

# Linting
lint-ruff = "ruff check ."
lint-ty = "ty check"
lint-yaml = "yamllint ."
lint = ["lint-ruff", "lint-ty", "lint-yaml"]

# Testing
test = "pytest -m 'not docs'"
test-coverage = "pytest --cov={{ package_name }} --cov-report=term-missing --cov-report=xml"
test-docs = { shell = "CI_DOCS_BUILD=true pytest -m docs -v --timeout=600" }
test-all = ["test", "test-docs"]

# OpenAPI
regenerate-client = "python scripts/regenerate_client.py"
validate-openapi = "openapi-spec-validator {{ openapi_spec_file }}"

# Documentation
docs-build = "mkdocs build"
docs-serve = "mkdocs serve"

# Pre-commit
pre-commit-run = "pre-commit run --all-files"
pre-commit-install = "pre-commit install"

# Combined workflows
check = ["format-check", "lint", "test"]
ci = ["format-check", "lint", "test-coverage", "validate-openapi", "docs-build"]
prepare = ["format", "lint", "test", "validate-openapi"]
```

**Benefits**:
- Single command: `uv run poe ci` runs all checks
- Cross-platform (no Make dependency)
- Task composition (`check = ["format-check", "lint", "test"]`)
- Self-documenting (`uv run poe` lists all tasks)

**Impact**: Superior developer experience

---

### 2.3 Pre-commit Hooks ⭐⭐⭐⭐⭐

**Priority**: CRITICAL

**Strategy**: Combine best from both

```yaml
repos:
  # Standard hooks (StockTrim)
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: check-toml
      - id: debug-statements
      - id: check-case-conflict

  # Ruff (both use this)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.12.4
    hooks:
      - id: ruff-format
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  # Local hooks via poe tasks
  - repo: local
    hooks:
      - id: mdformat
        name: mdformat
        entry: bash -c 'uv run poe format-markdown'
        language: system
        files: \.md$
        exclude: '(CHANGELOG\.md|\.agent\.md$)'

      - id: lint
        name: lint (ruff + ty + yamllint)
        entry: bash -c 'uv run poe lint'
        language: system
        pass_filenames: false

      - id: pytest
        name: pytest
        entry: bash -c 'uv run poe test'
        language: system
        pass_filenames: false
        always_run: true
```

**Also provide .pre-commit-config-lite.yaml** (Katana pattern):
```yaml
# Faster commits without pytest
# Same as above but without the pytest hook
```

**Impact**: Consistent code quality across all commits

---

### 2.4 Testing Infrastructure ⭐⭐⭐⭐⭐

**Priority**: CRITICAL

**Strategy**: Combine best from both

```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "-ra",                          # Show summary
    "--strict-markers",             # Fail on unknown markers (StockTrim)
    "--strict-config",              # Fail on config errors (StockTrim)
    "--timeout=30",                 # 30s timeout per test (StockTrim)
    "-n=4",                         # Parallel with 4 workers (Katana)
]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

markers = [
    "unit: Unit tests (fast, no external dependencies)",
    "integration: Integration tests (may hit API)",
    "slow: Slow tests (>1s)",
    "asyncio: Async tests",
    "docs: Documentation tests (CI-only)",
    "schema_validation: Schema validation tests (run separately)",
]

[tool.coverage.run]
source = ["{{ package_name }}"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/ conftest.py",
    "*/{{ package_name }}/client_types.py",  # Generated code
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
    "if TYPE_CHECKING:",
]
fail_under = 80
```

**Impact**: Rigorous testing standards

---

### 2.5 Documentation (MkDocs) ⭐⭐⭐⭐⭐

**Priority**: CRITICAL

**Strategy**: Katana's structure + StockTrim's mermaid support

```yaml
# mkdocs.yml
site_name: {{ project_name }}
site_description: Python client for {{ api_service }} API
site_author: {{ author_name }}

theme:
  name: material
  palette:
    - scheme: default
      primary: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - search.suggest
    - search.highlight
    - content.code.copy
    - content.code.annotate

plugins:
  - search
  - gen-files  # Katana - auto-generate API reference
  - literate-nav  # Katana
  - swagger-ui-tag  # Katana - OpenAPI spec viewer
  - mkdocstrings:
      handlers:
        python:
          options:
            docstring_style: google
            show_source: true
            show_root_heading: true

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.superfences:
      custom_fences:  # StockTrim - mermaid diagrams
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - admonition
  - pymdownx.details
  - toc:
      permalink: true

nav:
  - Home: index.md
  - Getting Started:
    - Installation: getting-started/installation.md
    - Quick Start: getting-started/quickstart.md
    - Configuration: getting-started/configuration.md
  - User Guide:
    - Client Usage: user-guide/client.md
    - Helper Methods: user-guide/helpers.md
    - Error Handling: user-guide/errors.md
    - Testing: user-guide/testing.md
  - API Reference: reference/
  - Architecture:
    - Overview: architecture/overview.md
    - Transport Layer: architecture/transport.md
    - Authentication: architecture/auth.md
  - Contributing: contributing.md
  - Changelog: CHANGELOG.md
  - OpenAPI Spec: api-spec
```

**Auto-generate API reference** (Katana's gen_ref_pages.py):

```python
# docs/gen_ref_pages.py
"""Generate API reference pages from docstrings."""
import mkdocs_gen_files
from pathlib import Path

for path in sorted(Path("{{ package_name }}").rglob("*.py")):
    module_path = path.relative_to(".").with_suffix("")
    doc_path = path.relative_to("{{ package_name }}").with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1] == "__main__":
        continue

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        identifier = ".".join(parts)
        print(f"::: {identifier}", file=fd)

    mkdocs_gen_files.set_edit_path(full_doc_path, path)
```

**Impact**: Professional documentation for all clients

---

### 2.6 Code Generation Script ⭐⭐⭐⭐⭐

**Priority**: CRITICAL

**Source**: StockTrim's 1066-line regeneration script

**Template**: `scripts/regenerate_client.py`

```python
#!/usr/bin/env python3
"""Regenerate OpenAPI client from spec.

This script:
1. Downloads OpenAPI spec (or uses local file)
2. Applies API-specific fixes (nullable fields, upsert endpoints, etc.)
3. Validates the spec
4. Generates client code
5. Post-processes generated code
6. Runs tests to validate

Configuration is at the top of this file - customize for your API.
"""

import json
import subprocess
from pathlib import Path

# ============================================================================
# CONFIGURATION - Customize these for your API
# ============================================================================

OPENAPI_SPEC_URL = "{{ openapi_spec_url }}"  # Or None for local file
OPENAPI_SPEC_FILE = Path("{{ openapi_spec_file }}")

# Fields that API returns as null but spec marks as required
# Format: {"SchemaName.fieldName": "type"}
NULLABLE_FIELDS = {
    # Example: "Product.created_at": "datetime",
    # Example: "Order.status": "enum",
}

# POST endpoints that return 200 on update (upsert pattern)
UPSERT_ENDPOINTS = [
    # Example: "/api/v1/products",
]

# Custom spec fixes (applied as JSON patches)
CUSTOM_FIXES = [
    # Example: {"op": "add", "path": "/components/schemas/Product/required/-", "value": "name"},
]

# ============================================================================
# IMPLEMENTATION - Usually don't need to modify below
# ============================================================================

def step_1_download_spec():
    """Download OpenAPI spec from API."""
    if OPENAPI_SPEC_URL:
        print(f"Downloading spec from {OPENAPI_SPEC_URL}")
        # Implementation...
    else:
        print(f"Using local spec: {OPENAPI_SPEC_FILE}")

def step_2_apply_fixes():
    """Apply API-specific fixes to spec."""
    with open(OPENAPI_SPEC_FILE) as f:
        spec = json.load(f)

    # Add nullable to configured fields
    for field_path, field_type in NULLABLE_FIELDS.items():
        schema_name, field_name = field_path.split(".")
        schema = spec["components"]["schemas"][schema_name]
        if "properties" in schema and field_name in schema["properties"]:
            schema["properties"][field_name]["nullable"] = True
            print(f"  ✓ Made {field_path} nullable")

    # Add 200 OK to upsert endpoints
    for endpoint in UPSERT_ENDPOINTS:
        for method in ["post"]:
            if endpoint in spec["paths"] and method in spec["paths"][endpoint]:
                responses = spec["paths"][endpoint][method]["responses"]
                if "200" not in responses and "201" in responses:
                    responses["200"] = responses["201"]
                    print(f"  ✓ Added 200 OK to {method.upper()} {endpoint}")

    # Apply custom fixes
    # Implementation...

    with open(OPENAPI_SPEC_FILE, "w") as f:
        json.dump(spec, f, indent=2)

def step_3_validate_spec():
    """Validate OpenAPI spec."""
    print("Validating spec...")
    subprocess.run(["uv", "run", "poe", "validate-openapi"], check=True)

def step_4_generate_client():
    """Generate client code using openapi-python-client."""
    print("Generating client...")
    subprocess.run([
        "uv", "run", "openapi-python-client", "generate",
        "--path", str(OPENAPI_SPEC_FILE),
        "--config", "openapi-generator-config.yml",
    ], check=True)

def step_5_post_process():
    """Post-process generated code."""
    print("Post-processing...")

    # Rename types.py → client_types.py
    types_file = Path("{{ package_name }}/types.py")
    if types_file.exists():
        types_file.rename("{{ package_name }}/client_types.py")
        # Fix imports...

    # Union → | syntax
    # Run ruff auto-fixes
    subprocess.run(["uv", "run", "ruff", "check", "--fix", "."], check=False)
    subprocess.run(["uv", "run", "ruff", "format", "."], check=True)

def step_6_run_tests():
    """Run tests to validate generated code."""
    print("Running tests...")
    subprocess.run(["uv", "run", "poe", "test"], check=True)

if __name__ == "__main__":
    print("=" * 70)
    print("OpenAPI Client Regeneration")
    print("=" * 70)

    step_1_download_spec()
    step_2_apply_fixes()
    step_3_validate_spec()
    step_4_generate_client()
    step_5_post_process()
    step_6_run_tests()

    print("\n✓ Client regeneration complete!")
```

**Impact**: Reproducible, documented client regeneration

---

## 3. Implementation Phases

### Phase 1: Core Library Foundation (Weeks 1-4)

**Week 1: Bootstrap**
- [ ] Create `openapi-client-core` repository
- [ ] Setup CI/CD (test, lint, coverage, PyPI publish)
- [ ] Basic README and docs site structure

**Week 2: Transport & Auth**
- [ ] Extract transport layer (base, error_logging, retry, factory)
- [ ] Extract auth (credential resolver, netrc, custom headers)
- [ ] Write unit tests

**Week 3: Error Handling & Testing**
- [ ] Extract exception hierarchy
- [ ] Extract unwrap() function
- [ ] Extract testing fixtures and factories
- [ ] Integration tests

**Week 4: Documentation & Release**
- [ ] Complete API documentation
- [ ] Usage examples
- [ ] Migration guides
- [ ] **Release v0.1.0 to PyPI**

**Deliverable**: Functional core library ready for use

---

### Phase 2: Template & Advanced Features (Weeks 5-8)

**Week 5: Pagination & Hooks**
- [ ] Extract pagination transport (from Katana)
- [ ] Extract event hooks
- [ ] Tests and documentation

**Week 6: CI/CD Workflows**
- [ ] Update template with 5 workflows
- [ ] Combine best features from both repos
- [ ] Test template generation

**Week 7: Task Runner & Testing**
- [ ] Add poethepoet configuration
- [ ] Update pre-commit hooks
- [ ] Enhanced pytest configuration
- [ ] Test infrastructure

**Week 8: Documentation & Code Generation**
- [ ] MkDocs configuration
- [ ] Auto API reference generation
- [ ] Code generation script template
- [ ] **Release core v0.2.0, template v2.0.0**

**Deliverable**: Enhanced template with modern tooling

---

### Phase 3: Polish & Optional Features (Weeks 9-12)

**Week 9: Helpers & Agents**
- [ ] Document helper base pattern
- [ ] Extract Katana's 7 agent templates
- [ ] Parameterize agents

**Week 10-11: MCP Server**
- [ ] Document MCP server integration
- [ ] Optional workspace member template
- [ ] FastMCP integration guide

**Week 12: Release & Migration**
- [ ] Complete documentation
- [ ] Example projects
- [ ] Migrate katana and stocktrim
- [ ] **Release core v1.0.0, template v2.1.0**

**Deliverable**: Production-ready ecosystem

---

## 4. Comparison Tables

### Transport Layer

| Feature | Katana | StockTrim | Extract? |
|---------|--------|-----------|----------|
| Base HTTP | ✓ | ✓ | ✓ YES |
| Error Logging | ✓ (detailed 422) | ✓ (null detection) | ✓ YES (combine) |
| Retry | RateLimitAware (429+5xx) | IdempotentOnly (5xx) | ✓ YES (both) |
| Pagination | ✓ (transport) | Manual (helpers) | ✓ YES (Katana) |
| Auth Headers | Standard | Custom multi-header | ✓ YES (both) |
| Event Hooks | ✓ (pagination, metrics) | No | ✓ YES (Katana) |

### Authentication

| Feature | Katana | StockTrim | Extract? |
|---------|--------|-----------|----------|
| Bearer Token | ✓ | No | ✓ YES |
| Custom Headers | No | ✓ (2 headers) | ✓ YES |
| Env Vars | ✓ | ✓ | ✓ YES |
| .env File | ✓ | ✓ | ✓ YES |
| Netrc | ✓ (unique) | No | ✓ YES |

### CI/CD

| Workflow | Katana | StockTrim | Template Choice |
|----------|--------|-----------|-----------------|
| CI | 4-step | 2-job matrix | Combine both |
| Release | Dual package | Monorepo scoped | StockTrim |
| Security | Trivy + Semgrep | +dependency review | StockTrim |
| Docs | GitHub Pages | GitHub Pages | Equal |
| Total | 4 workflows | 5 workflows | 5 (StockTrim base) |

### Testing

| Feature | Katana | StockTrim | Template Choice |
|---------|--------|-----------|-----------------|
| Markers | 5 markers | 5 markers | Combine (6 total) |
| Parallel | ✓ (4 workers) | No | Katana |
| Strict Config | No | ✓ | StockTrim |
| Fixtures | Pagination | Error responses | Combine |

---

## 5. Design Decisions

### 5.1 Retry Strategy

**Decision**: Provide all 3 variants, template defaults to RateLimitAwareRetry

**Rationale**:
- IdempotentOnly is safest (prevents duplicates)
- RateLimitAware handles modern APIs with 429
- AllMethods for special cases (with warnings)
- Let users choose based on API behavior

### 5.2 Null Field Detection

**Decision**: Enabled by default in ErrorLoggingTransport

**Rationale**:
- Minimal performance impact
- Excellent developer experience
- Catches issues early
- Can be disabled via flag

### 5.3 Task Runner

**Decision**: poethepoet required in template

**Rationale**:
- Cross-platform (Windows support)
- Task composition
- Single source of truth
- Better DX than Makefiles

### 5.4 Pagination

**Decision**: Provide both transport-layer and helper-layer options

**Rationale**:
- Transport: Automatic, transparent
- Helpers: Explicit control
- Let users choose based on needs

### 5.5 Core Library API

**Decision**: Direct imports + factory functions

**Rationale**:
- Direct imports for advanced users
- Factory functions for simple cases
- Best of both worlds

### 5.6 Code Generation

**Decision**: Always include regenerate_client.py in template

**Rationale**:
- Regeneration is common
- Documents API quirks
- Self-service for users

### 5.7 MCP Server

**Decision**: Optional workspace member via template variable

**Rationale**:
- Not everyone needs MCP
- Monorepo pattern from StockTrim
- Single template, flexible

### 5.8 Auth Pattern Default

**Decision**: Template variable (bearer | custom | oauth2)

**Rationale**:
- Auth is too important to hardcode
- Different APIs use different patterns
- Easy to configure

---

## 6. Migration Strategies

### 6.1 Katana Migration

**Timeline**: 4 weeks after core v0.1.0 release

**Steps**:

1. Add dependency: `openapi-client-core>=0.1.0,<1.0`
2. Replace transport layer (-460 lines)
3. Replace auth/credential resolution (-50 lines)
4. Replace testing fixtures (-150 lines)
5. Run full test suite
6. Release new version

**Impact**:
- Code removed: 660 lines (35%)
- Breaking changes: None
- Benefits: Shared maintenance, new features

### 6.2 StockTrim Migration

**Timeline**: 4 weeks after core v0.1.0 release

**Steps**:

1. Add dependency: `openapi-client-core>=0.1.0,<1.0`
2. Replace transport layer (-441 lines)
3. Replace error handling (-150 lines)
4. Replace testing fixtures (-120 lines)
5. Run full test suite
6. Release new version

**Impact**:
- Code removed: 711 lines (40%)
- Breaking changes: None
- Benefits: Null detection improvements shared

---

## 7. Success Metrics

### Core Library

- ✅ 80%+ test coverage
- ✅ 5+ real-world clients using it
- ✅ 100+ GitHub stars (6 months)
- ✅ Active contributor community

### Template

- ✅ 50%+ code reduction via core library
- ✅ <5 min to generate new client
- ✅ 20+ pages of documentation
- ✅ 3+ tutorial videos

### Migrations

- ✅ Zero breaking changes
- ✅ 30-40% code reduction
- ✅ All tests passing
- ✅ Performance parity

---

## 8. Next Steps

### Immediate (This Week)

1. [x] Create this extraction plan document
2. [x] Update Issue #9
3. [ ] Create openapi-client-core repository
4. [ ] Setup CI/CD for core library
5. [ ] Begin Phase 1 extractions

### Phase 1 (Weeks 1-4)

See [Implementation Phases](#3-implementation-phases) for detailed breakdown.

### Long Term

- Onboard 3+ additional clients to validate patterns
- Community feedback and iteration
- Expand to support more OpenAPI generators
- Consider GraphQL client template

---

## Appendix A: File Extraction Reference

### From Katana

| Component | Files | Lines | Priority |
|-----------|-------|-------|----------|
| Retry | `katana_client.py:65-98` | 34 | P1 |
| Error Logging | `katana_client.py:99-138` | 40 | P1 |
| Pagination | `katana_client.py:139-362` | 224 | P2 |
| Netrc | `katana_client.py:672-725` | 54 | P1 |
| Event Hooks | `katana_client.py:806-986` | 180 | P2 |
| Test Fixtures | `tests/conftest.py` | 150 | P1 |

**Total**: ~682 lines

### From StockTrim

| Component | Files | Lines | Priority |
|-----------|-------|-------|----------|
| Retry | `stocktrim_client.py:379-430` | 52 | P1 |
| Error Logging | `stocktrim_client.py:25-378` | 354 | P1 |
| Auth Headers | `stocktrim_client.py:483-517` | 35 | P1 |
| Exception Hierarchy | `utils.py:1-150` | 150 | P1 |
| Test Fixtures | `tests/conftest.py` | 120 | P1 |

**Total**: ~711 lines

---

## Appendix B: Dependencies

### Core Library Dependencies

**Runtime**:
- httpx>=0.27.0
- httpx-retries (or custom implementation)
- python-dotenv>=1.0.0

**Development**:
- pytest>=8.4.0
- pytest-asyncio>=0.25.0
- pytest-cov>=6.0.0
- pytest-httpx>=0.33.0
- ruff>=0.14.0
- mkdocs-material>=9.5.0

### Template Dependencies

Added to all generated clients:
- openapi-client-core>=0.1.0,<1.0
- All existing dependencies remain

---

**Document End**

This extraction plan provides a comprehensive roadmap for creating openapi-client-core and enhancing the template. It prioritizes the highest-impact patterns, provides concrete implementation strategies, and ensures smooth migration paths for existing clients.
