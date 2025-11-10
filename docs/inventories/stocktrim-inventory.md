# StockTrim OpenAPI Client - Comprehensive Inventory

**Repository**: stocktrim-openapi-client  
**Current Version**: 0.9.2 (Client), 0.10.0 (MCP Server)  
**Created**: 2024  
**License**: MIT  
**Python Support**: 3.11-3.13

## Executive Summary

The stocktrim-openapi-client is a production-ready Python client library with integrated MCP (Model Context Protocol) server support for the StockTrim Inventory Management API. This inventory documents **1,674 lines of helper code**, comprehensive CI/CD infrastructure, and patterns suitable for extraction into a shared openapi-client-core library.

### Key Statistics

- **Helper Methods**: 10+ domain helpers (Products, Customers, Suppliers, Orders, Inventory, etc.)
- **Transport Layers**: 4-layer composable architecture (retry, logging, auth, HTTP)
- **Test Coverage**: 26 tests across conftest fixtures, client tests, and integration tests
- **CI/CD Jobs**: 5 workflows (CI, Security, Docs, Release) with matrix testing (3.11, 3.12, 3.13)
- **Documentation**: 20+ markdown docs with MkDocs material theme
- **Monorepo Structure**: Dual-package workspace (client + MCP server)

### Unique Innovations vs Katana

1. **Custom Header Authentication**: Uses api-auth-id + api-auth-signature headers instead of Bearer tokens
2. **Idempotent-Only Retry Logic**: Only retries GET/HEAD/OPTIONS on 5xx (no 429 rate limiting)
3. **Error Logging Transport**: Sophisticated logging with null-field detection and fix suggestions
4. **Nullable Field Handling**: Comprehensive post-generation fixes for date/enum fields
5. **Upsert Pattern**: POST endpoints that return 200 on update, 201 on create
6. **Bulk Operation Helpers**: V1/V2 helper patterns with pagination and filtering
7. **MCP Server Integration**: FastMCP-based foundation and workflow tools

---

## 1. OpenAPI Client Logic (CRITICAL - Extract to Core)

### 1.1 Transport Layer Architecture

**Files**: 
- `/Users/dougborg/Projects/stocktrim-openapi-client/stocktrim_public_api_client/stocktrim_client.py:519-616` (transport factory)
- `/Users/dougborg/Projects/stocktrim-openapi-client/stocktrim_public_api_client/stocktrim_client.py:128-481` (error logging)
- `/Users/dougborg/Projects/stocktrim-openapi-client/stocktrim_public_api_client/stocktrim_client.py:483-517` (auth header)

**Pattern**: 4-layer composable transport stack with middleware-like pattern

```python
# create_resilient_transport factory (lines 519-616)
# Building block pattern:
1. Base AsyncHTTPTransport (core HTTP)
2. AuthHeaderTransport (wraps base, adds api-auth-signature)
3. ErrorLoggingTransport (wraps auth, logs detailed errors)
4. RetryTransport (outermost, handles retries with exponential backoff)
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL
- Can be extracted with minimal changes
- Pattern applicable to ANY API with custom auth headers
- Logging transport is API-agnostic, only needs auth header names
- Retry logic (IdempotentOnlyRetry) is StockTrim-specific but easily templated

**Migration Strategy**:
1. Extract to `openapi-client-core.transport.composable`
2. Create `BaseAuthTransport` abstract class for custom auth patterns
3. Provide `ErrorLoggingTransport` as standard middleware
4. Document retry customization points

---

### 1.2 Retry Logic - Idempotent-Only Pattern

**Files**: 
- `/Users/dougborg/Projects/stocktrim-openapi-client/stocktrim_public_api_client/stocktrim_client.py:75-126` (IdempotentOnlyRetry class)

**Pattern**: Custom Retry subclass that only retries idempotent HTTP methods on server errors

```python
class IdempotentOnlyRetry(Retry):
    """Only retries GET, HEAD, OPTIONS, TRACE on 5xx errors.
    
    Key features:
    - Implements is_retryable_method() and is_retryable_status_code()
    - Tracks request method across retry attempts
    - Exponential backoff: 1, 2, 4, 8, 16 seconds
    - No 429 rate limiting (StockTrim doesn't rate limit)
    - Status forcelist: [502, 503, 504] only
    """
    
    IDEMPOTENT_METHODS = frozenset(["HEAD", "GET", "OPTIONS", "TRACE"])
    
    def is_retryable_method(self, method: str) -> bool:
        self._current_method = method.upper()
        return self._current_method in self.allowed_methods
    
    def is_retryable_status_code(self, status_code: int) -> bool:
        # Only 5xx errors on idempotent methods
        if self._current_method in self.IDEMPOTENT_METHODS:
            return status_code in self.status_forcelist
        return False
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- Directly reusable for any API without rate limiting
- Pattern works for APIs with custom retry requirements
- httpx-retries dependency already in template

**Key Difference from Katana**: 
- Katana likely has 429 rate limiting (requires backoff + tracking)
- StockTrim only needs 5xx handling on idempotent methods

**Migration Strategy**:
1. Extract to `openapi-client-core.retry.IdempotentOnlyRetry`
2. Create variants: `RateLimitedRetry` (with 429), `AllMethodsRetry` (POST/PUT/PATCH)
3. Add to template as configurable option

---

### 1.3 Error Logging Transport - Sophisticated Debugging

**Files**: 
- `/Users/dougborg/Projects/stocktrim-openapi-client/stocktrim_public_api_client/stocktrim_client.py:128-481`

**Pattern**: Custom AsyncHTTPTransport that logs detailed debugging information

```python
class ErrorLoggingTransport(AsyncHTTPTransport):
    """Intercepts responses and logs with sophisticated error context.
    
    Features:
    - DEBUG: Request details (sanitized auth headers)
    - INFO: Success responses with timing
    - WARNING: Null responses (potential TypeErrors)
    - ERROR: 4xx/5xx with detailed context
    
    Null Field Detection (NEW):
    - Recursively finds null fields in responses
    - Suggests fixes: nullable fields, OpenAPI spec updates, defensive coding
    """
    
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await self._log_request(request)  # DEBUG with sanitized headers
        response = await self._wrapped_transport.handle_async_request(request)
        
        # Log based on status code with increasing detail
        if 200 <= response.status_code < 300:
            await self._log_success_response(response, request, duration_ms)
        elif 400 <= response.status_code < 500:
            await self._log_client_error(response, request, duration_ms)
        elif 500 <= response.status_code < 600:
            await self._log_server_error(response, request, duration_ms)
        
        return response
    
    def log_parsing_error(self, error: Exception, response: httpx.Response, request: httpx.Request):
        """Special handling for response parsing errors.
        
        For TypeErrors: Calls _find_null_fields() to detect and suggest fixes
        Suggests 3 approaches:
        1. Add fields to NULLABLE_FIELDS in regenerate_client.py
        2. Update OpenAPI spec with nullable: true
        3. Handle null values defensively in helpers
        """
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL
- Works for ANY API
- Logging patterns are generic
- Null field detection is unique innovation
- ProblemDetails parsing is RFC 7807 standard

**Unique Features**:
- Detects null fields at transport level (before parsing errors)
- Provides actionable fix suggestions
- Sanitizes auth headers in logs (security)
- Respects log level (debug vs info)

**Code Example - Null Field Detection** (lines 46-72):
```python
def _find_null_fields(data: Any, path: str = "") -> list[str]:
    """Recursively find all null fields in JSON response."""
    # Handles dict, list, and primitives
    # Returns paths like: ["orderDate", "supplier.supplierName", "items[0].id"]
```

**Migration Strategy**:
1. Extract to `openapi-client-core.logging.ErrorLoggingTransport`
2. Make ProblemDetails handling optional (inject model if available)
3. Add to all generated clients by default
4. Document logging patterns in template

---

### 1.4 Custom Header Authentication

**Files**: 
- `/Users/dougborg/Projects/stocktrim-openapi-client/stocktrim_public_api_client/stocktrim_client.py:483-517`

**Pattern**: Transport middleware that adds custom headers

```python
class AuthHeaderTransport(AsyncHTTPTransport):
    """Adds StockTrim api-auth-signature header to requests.
    
    Note: api-auth-id is handled by parent AuthenticatedClient's native
    auth_header_name customization. This transport only adds api-auth-signature.
    
    Design: Separates concerns:
    - AuthenticatedClient: Handles one header (api-auth-id)
    - AuthHeaderTransport: Handles additional headers (api-auth-signature)
    """
    
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        request.headers["api-auth-signature"] = self.api_auth_signature
        return await self._wrapped_transport.handle_async_request(request)
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- Generic pattern for any multi-header authentication
- Works with or without Bearer token
- Composable with other transports

**Unique Aspect**: Separates single-header auth (handled by client) from multi-header auth (transport layer)

---

### 1.5 Error Translation and Handling

**Files**:
- `/Users/dougborg/Projects/stocktrim-openapi-client/stocktrim_public_api_client/utils.py:18-182` (exception classes and unwrap function)

**Pattern**: RFC 7807 ProblemDetails-based error handling

```python
class APIError(Exception):
    """Base exception with status code and ProblemDetails model."""
    
    def __init__(self, message: str, status_code: int, 
                 problem_details: "ProblemDetails | None" = None):
        self.status_code = status_code
        self.problem_details = problem_details

# Specific subclasses:
class AuthenticationError(APIError): pass  # 401
class PermissionError(APIError): pass      # 403
class NotFoundError(APIError): pass        # 404
class ValidationError(APIError): pass      # 400, 422
class ServerError(APIError): pass          # 5xx

def unwrap(response: Response[T], raise_on_error: bool = True) -> T | None:
    """Main utility for handling API responses.
    
    - Overload support for return type inference
    - Extracts ProblemDetails if available
    - Raises specific exceptions based on status code
    - Provides detailed messages from error model
    """
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL
- RFC 7807 standard (applicable to most modern APIs)
- Exception hierarchy is simple but effective
- Overload support provides great DX

**Key Innovation**: Stores ProblemDetails object for inspection (not just message string)

---

### 1.6 Client Types and Response Handling

**Files**:
- `/Users/dougborg/Projects/stocktrim-openapi-client/stocktrim_public_api_client/client_types.py` (Unset, Response, File)
- `/Users/dougborg/Projects/stocktrim-openapi-client/stocktrim_public_api_client/generated/client.py` (base Client)

**Pattern**: Standard openapi-python-client types

```python
class Unset:
    """Marker for unset optional parameters (better than None)."""
    def __bool__(self) -> Literal[False]:
        return False

@define
class Response(Generic[T]):
    """Generic response wrapper."""
    status_code: HTTPStatus
    content: bytes
    headers: MutableMapping[str, str]
    parsed: T | None
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- Direct from openapi-python-client
- Can be reused as-is in any generated client

---

## 2. CI/CD Infrastructure

### 2.1 GitHub Actions Workflows

**Files**:
- `.github/workflows/ci.yml` - Main test workflow
- `.github/workflows/release.yml` - Semantic versioning & PyPI publishing
- `.github/workflows/security.yml` - Trivy + Semgrep scanning
- `.github/workflows/docs.yml` - MkDocs GitHub Pages deployment

### 2.1.1 CI Workflow

**File**: `.github/workflows/ci.yml` (lines 1-78)

```yaml
# Matrix testing: Python 3.11, 3.12, 3.13
# Steps:
# 1. Install UV (package manager)
# 2. Format check (ruff format --check)
# 3. Linting (ruff check + ty type check + yamllint)
# 4. Test with coverage (pytest --cov)
# 5. Upload to Codecov

Jobs:
- test: Matrix testing on ubuntu-latest
- quality: OpenAPI validation + docs build
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL
- Exact pattern for any Python project using ruff + pytest
- UV package manager setup is modern best practice
- Matrix strategy for multiple Python versions
- Codecov integration is standard

---

### 2.1.2 Release Workflow (Semantic Release)

**File**: `.github/workflows/release.yml` (274 lines)

**Pattern**: Sophisticated multi-stage release with conditional semantics

```yaml
Jobs:
1. test (prerequisite)
   - Runs full CI pipeline before releasing

2. release-client
   - Checks for (client) scoped commits since last release
   - Runs python-semantic-release v9.15.2
   - Builds wheel + source dist
   - Uploads artifacts

3. release-mcp
   - Depends on test + release-client
   - Runs if: (1) (mcp) scoped commits OR (2) client was released
   - Updates client dependency version in stocktrim_mcp_server/pyproject.toml
   - Builds + publishes MCP server

4. publish-client & publish-mcp
   - Uses trusted publishing (OIDC token)
   - Uploads to PyPI with attestations
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL - Monorepo Pattern
- Excellent example of monorepo release coordination
- Conditional release logic (commit scoping)
- Dependency version management (client → MCP)
- Semantic Release integration with scoped commits

**Unique Pattern**: 
```bash
# Release triggers only on scoped commits:
feat(client): new feature        # Triggers client release
fix(mcp): bug fix               # Triggers MCP release
feat: no scope                  # Triggers client release (default)
chore(mcp): dependency update   # No release (default_bump_level=0)
```

**Key Configuration** (pyproject.toml lines 252-299):
```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
tag_format = "client-v{version}"

[tool.semantic_release.commit_parser_options]
allowed_tags = ["build", "chore", "ci", "docs", "feat", "fix", "perf", "style", "refactor", "test"]
minor_tags = ["feat"]
patch_tags = ["fix", "perf"]
default_bump_level = 0  # Only feat/fix/perf tags bump version
```

**Comparison with Katana**: 
- Katana likely doesn't have monorepo complexity
- This shows advanced semantic release patterns

---

### 2.1.3 Security Workflow

**File**: `.github/workflows/security.yml` (lines 1-52)

```yaml
Triggers: push to main, PRs, weekly schedule

Jobs:
1. security-scan
   - Trivy filesystem scan → SARIF
   - Semgrep (config=auto) → SARIF
   - Both uploaded to GitHub Security tab

2. dependency-review (PR only)
   - GitHub's built-in dependency review action
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- Modern scanning best practices
- SARIF format for GitHub integration
- Scheduled weekly scans

---

### 2.1.4 Documentation Deployment

**File**: `.github/workflows/docs.yml` (lines 1-55)

```yaml
Triggers: push to main, releases, manual dispatch

Jobs:
1. build
   - Install deps with UV
   - Run: poe docs-clean && poe docs-build
   - Upload site/ artifact

2. deploy
   - Deploy artifact to GitHub Pages
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- Standard MkDocs + GitHub Pages pattern
- Leverages poe tasks for consistency

---

### 2.2 Pre-commit Configuration

**File**: `.pre-commit-config.yaml` (48 lines)

```yaml
Hooks:
1. ruff (format + lint)
2. pre-commit standard hooks (trailing-whitespace, case-conflicts, etc.)
3. mdformat (markdown formatting)
4. yamllint (YAML validation)
5. Local hooks (lint, pytest)
   - Uses: bash -c 'uv run poe lint'
   - Uses: bash -c 'uv run poe test'
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL
- Excellent example of comprehensive pre-commit setup
- Integration with poe tasks (single source of truth)
- Modern Python linting (ruff)

---

## 3. Project Automation & Tooling

### 3.1 Task Runner (poethepoet)

**File**: `pyproject.toml` lines 305-437 (task definitions)

**Pattern**: Centralized task definitions with clear organization

```toml
[tool.poe.tasks]

# Code Formatting
format-python = "ruff format ."
format-markdown = "mdformat README.md docs/*.md --wrap 88"
format = ["format-python", "format-markdown"]
format-check = ["format-python-check", "format-markdown-check"]

# Linting
lint-ty = "ty check"           # Fast type checker by Astral
lint-ruff = "ruff check ."
lint = ["lint-ruff", "lint-ty", "lint-yaml"]

# Testing
test = "pytest -m 'not docs'"
test-coverage = "pytest --cov=stocktrim_public_api_client --cov-report=term-missing"
test-docs = { shell = "CI_DOCS_BUILD=true pytest -m docs -v --timeout=600" }

# OpenAPI
regenerate-client = "python scripts/regenerate_client.py"
validate-openapi = "openapi-spec-validator stocktrim-openapi.yaml"

# Documentation
docs-build = "mkdocs build"
docs-serve = "mkdocs serve"

# Pre-commit
pre-commit-run = "pre-commit run --all-files"

# Combined workflows
check = ["format-check", "lint", "test"]
ci = ["format-check", "lint", "test-coverage", "docs-build"]
prepare = ["format", "lint", "test", "validate-openapi"]
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL
- Single source of truth for all development commands
- CI uses: `uv run poe ci`, pre-commit uses: `uv run poe lint`
- Reduces shell command duplication
- Easy to document in README

**Key Innovation**: Task composition (`check = ["format-check", "lint", "test"]`)

---

### 3.2 Dependency Management (UV)

**File**: `pyproject.toml` lines 1-127 (dependencies, workspace config)

**Pattern**: Modern Python packaging with UV workspace

```toml
[project]
name = "stocktrim-openapi-client"
version = "0.9.2"
requires-python = ">=3.11,<3.14"

[project.dependencies]
# Generated client deps
httpx>=0.28.0
attrs>=22.2.0
python-dateutil>=2.8.0
# Enhanced client deps
tenacity>=9.0.0
python-dotenv>=1.0.0
# Legacy compatibility
urllib3>=2.5.0,<4.0.0
pydantic>=2,<3
httpx-retries>=0.4.3,<0.5.0

[project.optional-dependencies]
dev = [
    "pytest>=7.2.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=2.8.0",
    "ruff>=0.12.4,<0.13",
    "pre-commit>=4.2.0",
    # ... more
]
docs = [
    "mkdocs>=1.6.0",
    "mkdocs-material>=9.5.0",
    "mkdocstrings[python]>=0.25.0",
]

[tool.uv.workspace]
members = [".", "stocktrim_mcp_server"]  # Monorepo structure
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL
- Modern package management approach
- Clear separation: core deps vs dev deps vs docs deps
- Workspace support for monorepo (template should use this)

**Key Difference from older approaches**: 
- Uses UV instead of poetry/pipenv
- pyproject.toml is sole source of truth (no setup.py)

---

### 3.3 Build System (Hatchling)

**File**: `pyproject.toml` lines 112-140

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["stocktrim_public_api_client"]

[tool.hatch.build.targets.wheel.force-include]
"stocktrim-openapi.yaml" = "stocktrim_public_api_client/stocktrim-openapi.yaml"
```

**Reusability**: ⭐⭐⭐ MEDIUM
- Hatchling is modern, fast build backend
- Force-include pattern for non-Python files

---

## 4. Testing Infrastructure

### 4.1 Test Fixtures and Conftest

**File**: `tests/conftest.py` (226 lines)

**Pattern**: Comprehensive pytest fixtures covering multiple scenarios

```python
@pytest.fixture
def mock_api_credentials():
    """Provide mock API credentials."""
    return {
        "api_auth_id": "test-tenant-id",
        "api_auth_signature": "test-tenant-name",
        "base_url": "https://api.test.stocktrim.example.com",
    }

@pytest.fixture
def stocktrim_client(mock_api_credentials):
    """Create a StockTrimClient for testing."""
    return StockTrimClient(**mock_api_credentials)

@pytest.fixture(autouse=True)
def clear_env():
    """Auto-cleanup: Clear env vars before each test."""
    # Store originals, delete vars, yield, restore
    # Ensures test isolation

@pytest.fixture
def mock_transport(mock_transport_handler):
    """Create httpx.MockTransport for network-free testing."""
    return httpx.MockTransport(mock_transport_handler)

@pytest.fixture
def create_mock_response():
    """Factory fixture to create custom mock responses."""
    def _create_response(status_code=200, json_data=None, headers=None):
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.json.return_value = json_data
        return response
    return _create_response

# Error response fixtures:
@pytest.fixture
def mock_server_error_response(): ...     # 500
@pytest.fixture
def mock_authentication_error_response(): ... # 401
@pytest.fixture
def mock_validation_error_response(): ...    # 422
@pytest.fixture
def mock_not_found_response(): ...          # 404
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL
- Excellent fixture patterns for generated API clients
- Covers: credentials, clients, transports, responses, errors
- Factory pattern for custom responses
- Autouse fixture for environment cleanup

**Best Practices**:
- Clear fixture names
- Proper isolation (clear_env autouse)
- Both sync and async fixtures (async_stocktrim_client)
- MagicMock for detailed control

---

### 4.2 Pytest Configuration

**File**: `pyproject.toml` lines 157-195

```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "-ra",                          # Show summary of all test outcomes
    "--strict-markers",             # Fail on unknown markers
    "--strict-config",              # Fail on config errors
    "--timeout=30",                 # 30 second timeout per test
]
testpaths = ["tests"]
asyncio_mode = "auto"              # Pytest-asyncio auto mode
asyncio_default_fixture_loop_scope = "function"

markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
    "asyncio: marks tests as async tests",
    "docs: marks tests as documentation tests",
]

[tool.coverage.run]
source = ["stocktrim_public_api_client"]
omit = ["*/tests/*", "*/test_*", "*/conftest.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "@(abc\.)?abstractmethod",
]
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL
- Modern pytest patterns
- Strict configuration catches errors
- Clear test markers for organization
- Timeout prevents hanging tests
- Coverage configuration is standard

---

### 4.3 Test Markers and Categorization

**Pattern**: Markers for different test types

```bash
# Run different test categories:
poe test                    # All tests except docs
poe test-unit              # Unit tests only
poe test-integration       # Integration tests only
poe test-docs              # Documentation tests (slow, 10min timeout)

# Pytest marks usage:
@pytest.mark.unit
@pytest.mark.asyncio
async def test_something(): ...

@pytest.mark.integration
async def test_api_call(): ...
```

**Reusability**: ⭐⭐⭐ MEDIUM
- Good practice for test organization
- Can be applied to any project

---

## 5. Project Structure and Organization

### 5.1 Directory Layout

```
stocktrim-openapi-client/
├── stocktrim_public_api_client/          # Main client package
│   ├── __init__.py                       # Exports: StockTrimClient, utils
│   ├── stocktrim_client.py               # 900+ lines: Main client class
│   ├── client_types.py                   # Unset, Response, File types
│   ├── utils.py                          # Error handling, unwrap function
│   ├── generated/                        # OpenAPI-generated code
│   │   ├── client.py                     # Base AuthenticatedClient
│   │   ├── errors.py
│   │   ├── models/                       # 80+ model classes
│   │   └── api/                          # API operation functions
│   │       ├── products/
│   │       ├── customers/
│   │       ├── purchase_orders/
│   │       └── ... (10+ domains)
│   └── helpers/                          # Domain-specific wrappers
│       ├── __init__.py
│       ├── base.py                       # Base class for all helpers
│       ├── products.py
│       ├── customers.py
│       ├── suppliers.py
│       ├── sales_orders.py
│       ├── purchase_orders.py
│       ├── purchase_orders_v2.py
│       ├── inventory.py
│       ├── locations.py
│       ├── forecasting.py
│       ├── bill_of_materials.py
│       └── order_plan.py
│
├── stocktrim_mcp_server/                 # MCP server (separate package)
│   ├── pyproject.toml                    # Separate versioning
│   ├── src/stocktrim_mcp_server/
│   │   ├── server.py                     # FastMCP initialization
│   │   ├── context.py                    # ServerContext holder
│   │   ├── dependencies.py
│   │   ├── logging_config.py
│   │   ├── observability.py              # @observe_tool decorator
│   │   └── resources/
│   │       ├── foundation.py             # CRUD tools
│   │       └── reports.py                # Workflow tools
│   └── tests/
│
├── scripts/
│   ├── regenerate_client.py              # 1066 lines: OpenAPI gen script
│   ├── test_delete_products.py
│   └── test_delete_status.py
│
├── tests/
│   ├── conftest.py                       # Pytest fixtures
│   ├── test_stocktrim_client.py
│   ├── test_helpers.py
│   └── test_utils.py
│
├── docs/
│   ├── getting-started/
│   ├── user-guide/
│   ├── architecture/
│   ├── api/
│   ├── mcp-server/
│   ├── contributing/
│   ├── CHANGELOG.md
│   └── conf.py
│
├── .github/workflows/
│   ├── ci.yml
│   ├── release.yml
│   ├── security.yml
│   └── docs.yml
│
├── .pre-commit-config.yaml
├── .yamllint.yml
├── mkdocs.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- Clean separation: generated vs custom code
- Helpers organize by domain (Products, Customers, etc.)
- Monorepo ready (separate MCP server package)
- Standard Python package structure

---

### 5.2 Helper Base Class Pattern

**File**: `stocktrim_public_api_client/helpers/base.py` (27 lines)

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stocktrim_public_api_client.stocktrim_client import StockTrimClient

class Base:
    """Base class for all domain helper classes.
    
    Provides common functionality and access to StockTrimClient.
    """
    
    def __init__(self, client: StockTrimClient) -> None:
        self._client = client
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- Simple mixin pattern for all helpers
- TYPE_CHECKING import avoids circular imports
- All helpers inherit and use: `await get_api_xxx.asyncio_detailed(client=self._client)`

---

### 5.3 Helper Method Patterns

**Example from Products Helper** (`stocktrim_public_api_client/helpers/products.py`):

```python
class Products(Base):
    """Product catalog management."""
    
    async def get_all(self, code: str | Unset = UNSET, 
                     page_no: str | Unset = UNSET) -> list[ProductsResponseDto]:
        """Get all products, optionally filtered."""
        response = await get_api_products.asyncio_detailed(
            client=self._client,
            code=code,
            page_no=page_no,
        )
        result = unwrap(response)
        return result if isinstance(result, list) else []
    
    # Convenience methods:
    async def find_by_code(self, code: str) -> ProductsResponseDto | None:
        """Find single product by code match."""
        products = await self.get_all(code=code)
        return products[0] if products else None
    
    async def search(self, code_prefix: str) -> list[ProductsResponseDto]:
        """Search for products with code prefix."""
        return await self.get_all(code=code_prefix)
    
    async def exists(self, code: str) -> bool:
        """Check if product exists."""
        return await self.find_by_code(code) is not None
    
    async def get_all_paginated(self) -> list[ProductsResponseDto]:
        """Get ALL products by paginating through pages."""
        # Implementation handles pagination loop
```

**Pattern - Ergonomic Wrappers**:
1. **Core Methods**: get_all(), create(), delete() - direct API mapping
2. **Convenience Methods**: find_by_code(), exists(), search() - common queries
3. **Bulk Methods**: get_all_paginated() - handle pagination transparently

**Reusability**: ⭐⭐⭐⭐ HIGH
- Pattern applicable to any OpenAPI-generated client
- Natural Python naming (not API naming)
- Handles API quirks (inconsistent return types)

---

### 5.4 Handling API Inconsistencies

**Example from PurchaseOrders V1** (`purchase_orders.py:29-56`):

```python
async def get_all(self, reference_number: str | Unset = UNSET
                ) -> PurchaseOrderResponseDto | list[PurchaseOrderResponseDto]:
    """Get purchase orders, optionally filtered.
    
    Note: API returns single object when filtered by reference_number,
    but list otherwise. This inconsistency is preserved here.
    """
    response = await get_api_purchase_orders.asyncio_detailed(
        client=self._client,
        reference_number=reference_number,
    )
    return cast(
        PurchaseOrderResponseDto | list[PurchaseOrderResponseDto],
        unwrap(response),
    )

# Convenience method to normalize:
async def find_by_reference(self, reference_number: str) -> PurchaseOrderResponseDto | None:
    """Find single purchase order by reference.
    
    Handles API's inconsistent return type (single vs list).
    Always returns single object or None.
    """
    result = await self.get_all(reference_number=reference_number)
    if isinstance(result, list):
        return result[0] if result else None
    return result
```

**Pattern - API Quirk Handling**:
- Document inconsistency in docstring
- Preserve inconsistency in base method (for raw access)
- Normalize in convenience method

**Reusability**: ⭐⭐⭐ MEDIUM
- Pattern useful for any API with inconsistencies
- Shows defensive programming approach

---

## 6. OpenAPI Code Generation

### 6.1 Client Regeneration Script

**File**: `scripts/regenerate_client.py` (1066 lines)

**Pattern**: Comprehensive 9-step client generation with spec fixups

```bash
STEP 1: Download OpenAPI Specification
STEP 2: Fix Authentication (convert headers to securitySchemes)
STEP 2.5: Add Nullable to Date/Time Fields (critical fix!)
STEP 2.6: Add Nullable to Enum Fields
STEP 2.7: Add 200 OK Responses to Upsert Endpoints
STEP 2.8: Fix DELETE Responses to 204 No Content
STEP 3: Validate OpenAPI Specification
STEP 4: Generate Python Client
STEP 5: Move Client & Rename types.py → client_types.py
STEP 6: Post-Process Docstrings
STEP 7: Fix Specific Generated Issues
STEP 8: Run Ruff Auto-Fixes
STEP 9: Run Tests
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL - Excellent Pattern for Template

#### 6.1.1 Nullable Field Handling (INNOVATION)

**Lines 151-259**: Add nullable markers to fields that API returns as null

```python
def add_nullable_to_date_fields(spec_path: Path) -> bool:
    """Fix nullable date/time fields not marked in OpenAPI spec.
    
    StockTrim API returns null for date fields but spec doesn't mark nullable.
    This causes: obj = PurchaseOrder.from_dict(data) → TypeError on isoparse(None)
    
    NULLABLE_FIELDS mapping documents which fields need fixes:
    - PurchaseOrderResponseDto.orderDate: datetime (CRITICAL - crashes)
    - PurchaseOrderResponseDto.fullyReceivedDate: datetime (CRITICAL)
    - PurchaseOrderLineItem.receivedDate: datetime (CRITICAL)
    """
    
    # For object refs: Use allOf pattern (OpenAPI 3.0 limitation)
    # field = {"$ref": "#/components/schemas/Location"}
    # Becomes:
    # field = {"allOf": [{"$ref": "#/components/schemas/Location"}], "nullable": true}
```

**Why This Matters**: 
- Without fixes, client crashes at runtime on valid API responses
- Spec doesn't match actual API behavior
- Solution: Post-processing step in regeneration

**Code Fix Example** (lines 215-223):
```python
if "$ref" in field:
    ref_value = field["$ref"]
    field.clear()
    field["allOf"] = [{"$ref": ref_value}]
    field["nullable"] = True
    logger.info(f"  ✓ Made {schema_name}.{field_name} (object ref) nullable using allOf pattern")
```

---

#### 6.1.2 Types.py Rename Automation

**Lines 599-664**: Move generated client and rename types.py to client_types.py

```python
def move_client_to_workspace(workspace_path: Path) -> bool:
    """Move and reorganize generated code.
    
    Generated structure:
    temp_workspace/{__init__.py, types.py, models/, api/, client.py}
    
    Target structure:
    stocktrim_public_api_client/
    ├── client_types.py  (renamed from types.py at package root)
    ├── generated/
    │   ├── __init__.py
    │   ├── client.py
    │   ├── errors.py
    │   ├── models/
    │   └── api/
    """
    
    # Copy types.py to package root as client_types.py
    # Move everything else to generated/
    # Then fix all imports: types → client_types
```

**Why Types Rename**:
- types.py is too generic (name collision)
- client_types.py is explicit (Unset, Response, File types)
- All imports must be updated post-generation

---

#### 6.1.3 Import Fixing

**Lines 543-597**: Fix all relative imports after moving code

```python
def _fix_types_imports(target_client_path: Path) -> None:
    """Fix imports from 'types' to 'client_types' in all generated files.
    
    Different relative import depths:
    - API files (4 levels: endpoint/ → api/ → generated/ → package/)
      from ...types → from ....client_types
    - Model files (3 levels: models/ → generated/ → package/)
      from ..types → from ...client_types
    
    Patterns for each depth level:
    - (r"from \.\.\.types import", "from ....client_types import")
    - (r"from \.\.types import", "from ...client_types import")
    - Absolute imports
    """
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL - Template Pattern
- Exact pattern for any API client with types → client_types rename
- Handles all relative import depths
- Batch file processing with regex

---

#### 6.1.4 Union Type Modernization

**Lines 709-744**: Convert Union[A, B] to A | B syntax

```python
# Handle Union types - convert to modern | syntax
content = content.replace(
    "FileContent = Union[IO[bytes], bytes, str]",
    "FileContent = IO[bytes] | bytes | str",
)

# Generic Union replacement with regex
content = re.sub(
    r"Union\[([^\[\]]+)\]",
    lambda m: " | ".join(p.strip() for p in m.group(1).split(",")),
    content,
)
```

**Why Modernize**: 
- Python 3.10+ supports | syntax
- More readable, matches modern Python style
- Pre-commit won't auto-upgrade

---

#### 6.1.5 Upsert Pattern Support

**Lines 328-394**: Add 200 response to POST endpoints (create-or-update)

```python
def add_200_response_to_upsert_endpoints(spec_path: Path) -> bool:
    """Add 200 OK to POST endpoints that support upsert.
    
    StockTrim uses POST for both create (201) and update (200):
    POST /api/Products
      - If new code: 201 Created
      - If existing code: 200 OK (updated)
    
    Spec only documents 201, so generated code crashes on update.
    Solution: Add 200 response to spec before generation.
    """
    
    UPSERT_ENDPOINTS = [
        "/api/PurchaseOrders",  # client_reference_number is upsert key
        "/api/Products",        # product code is upsert key
    ]
    
    # Copy 201 response schema to 200 response
    responses["200"] = {
        "description": "Success (Updated)",
        "content": responses["201"]["content"],
    }
```

**Unique to StockTrim**: 
- REST purists use PATCH for updates
- StockTrim uses POST for create-or-update
- Client must handle both 200 and 201 responses

---

#### 6.1.6 Validation and Testing

**Lines 445-488**: Multi-level OpenAPI validation

```python
def validate_openapi_spec_python(spec_path: Path) -> bool:
    """Validate with openapi-spec-validator (Python)."""
    validate_spec(spec_dict)  # Strict validation

def validate_openapi_spec_redocly(spec_path: Path) -> bool:
    """Validate with Redocly CLI (optional, warnings only)."""
    result = subprocess.run(
        ["npx", "@redocly/cli@latest", "lint", str(spec_path)],
        ...
    )
    # Redocly failures are logged but not fatal
```

**Pattern**: 2-level validation
1. Python: Strict OpenAPI spec validation (required)
2. Redocly: Extended rules (optional, warnings)

---

#### 6.1.7 Post-Generation Test Run

**Lines 878-917**: Validates generated code before completion

```python
def run_tests(workspace_path: Path) -> bool:
    """Run tests to validate the generated client."""
    cmd = [sys.executable, "-m", "poethepoet", "test"]
    # Streams output in real-time
    # Returns test status
```

**Why This Matters**: 
- Catches regressions immediately
- Validates entire pipeline works
- Provides fast feedback on generation

---

## 7. Documentation

### 7.1 MkDocs Configuration

**File**: `mkdocs.yml` (136 lines)

```yaml
site_name: StockTrim OpenAPI Client
theme:
  name: material
  palette: [light mode, dark mode]
  features: [navigation.tabs, search.suggest, content.code.copy, ...]

plugins:
  - search
  - mkdocstrings (Python with Google docstring style)

markdown_extensions:
  - pymdownx.superfences (with mermaid diagrams)
  - pymdownx.tabs
  - pymdownx.highlight
  - toc (with permalink)

nav:
  - Home: index.md
  - Getting Started: [installation.md, quickstart.md, configuration.md]
  - User Guide: [client-guide.md, helper-methods.md, error-handling.md, testing.md]
  - MCP Server: [overview.md, installation.md, tools.md, claude-desktop.md]
  - API Reference: [client.md, helpers.md]
  - Architecture: [overview.md, transport.md, helpers.md]
  - Contributing: [development.md, code-of-conduct.md, api-feedback.md]
  - Changelog: CHANGELOG.md
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- Modern Material theme with excellent UX
- mkdocstrings for auto-generated API docs
- Well-organized navigation
- GitHub Pages deployment ready

---

### 7.2 Architecture Documentation

**Files**: 
- `docs/architecture/overview.md` - System design
- `docs/architecture/transport.md` - Transport layer design
- `docs/architecture/logging.md` - Logging strategy
- `docs/architecture/helpers.md` - Helper pattern

**Coverage**: 
- Transport layer diagram
- Retry strategy explanation
- Error handling flow
- Helper class design
- API quirk handling

---

### 7.3 Contributing Guide

**Files**:
- `docs/contributing/development.md` - Setup, testing, debugging
- `docs/contributing/api-feedback.md` - Known API issues and fixes
- `docs/contributing/code-of-conduct.md` - Community standards

**Highlights**:
- Detailed issue templates
- API spec issues (nullable fields, inconsistent responses)
- How to regenerate client
- Pre-commit workflow

---

## 8. MCP Server Integration

### 8.1 FastMCP Server Structure

**File**: `stocktrim_mcp_server/src/stocktrim_mcp_server/server.py` (150+ lines shown)

```python
@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[ServerContext]:
    """Manage server lifespan.
    
    1. Load environment variables
    2. Validate STOCKTRIM_API_AUTH_ID and STOCKTRIM_API_AUTH_SIGNATURE
    3. Initialize StockTrimClient with resilience
    4. Provide client to tools via ServerContext
    5. Ensure cleanup on shutdown
    """
    load_dotenv()
    
    api_auth_id = os.getenv("STOCKTRIM_API_AUTH_ID")
    api_auth_signature = os.getenv("STOCKTRIM_API_AUTH_SIGNATURE")
    base_url = os.getenv("STOCKTRIM_BASE_URL", "https://api.stocktrim.com")
    
    # Validate configuration
    if not api_auth_id:
        logger.error("missing_configuration", variable="STOCKTRIM_API_AUTH_ID")
        raise ValueError("STOCKTRIM_API_AUTH_ID environment variable required")
    
    # Initialize client
    async with StockTrimClient(...) as client:
        context = ServerContext(client=client)
        logger.info("server_ready")
        yield context

# Initialize server with lifespan
mcp = FastMCP(
    name="stocktrim-inventory",
    version=__version__,
    lifespan=lifespan,
    instructions="...",  # User-facing instructions
)
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- FastMCP pattern for any API client
- Environment-based configuration
- Structured logging
- Proper resource cleanup

---

### 8.2 Observability Decorators

**File**: `stocktrim_mcp_server/src/stocktrim_mcp_server/observability.py` (138 lines)

```python
def observe_tool(func: F) -> F:
    """Decorator for MCP tool observability.
    
    Logs:
    - Tool invocation with parameters
    - Execution duration
    - Success/failure status
    - Error details if failed
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        start_time = time.perf_counter()
        params = {k: v for k, v in kwargs.items() if k != "ctx"}
        
        logger.info("tool_invoked", tool_name=tool_name, params=params)
        
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info("tool_completed", tool_name=tool_name, 
                       duration_ms=round(duration_ms, 2), success=True)
            return result
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error("tool_failed", tool_name=tool_name, 
                        duration_ms=round(duration_ms, 2), error=str(e))
            raise
    
    return wrapper
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- Generic observability pattern for any async function
- Performance timing included
- Excludes ctx parameter from logging

---

## 9. Version and Release Management

### 9.1 Version Tracking

**Files**:
- `stocktrim_public_api_client/__init__.py:8` → `__version__ = "0.9.2"`
- `pyproject.toml:3` → `version = "0.9.2"`
- `stocktrim_mcp_server/pyproject.toml:3` → `version = "0.10.0"` (separate)

**Pattern**: Single source of truth in pyproject.toml, referenced in __init__.py

```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["stocktrim_public_api_client/__init__.py:__version__"]
```

**Reusability**: ⭐⭐⭐⭐⭐ CRITICAL
- Semantic Release integration
- Dual-package versioning support (client ≠ MCP)
- Automated version bumping

---

## 10. Authentication Patterns

### 10.1 Custom Header Authentication

**Implemented in**: `stocktrim_client.py:483-517` (AuthHeaderTransport) and `stocktrim_client.py:655-770` (StockTrimClient.__init__)

**Pattern**: Two-header authentication split across layers

```python
# In StockTrimClient.__init__:
super().__init__(
    base_url=base_url,
    token=api_auth_id,              # Set api-auth-id header
    auth_header_name="api-auth-id", # Custom header name (not "Authorization")
    prefix="",                       # No "Bearer " prefix
    timeout=httpx.Timeout(timeout),
    httpx_args={
        "transport": transport,     # Our custom transport adds api-auth-signature
        "event_hooks": event_hooks,
    },
)

# In AuthHeaderTransport:
async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
    request.headers["api-auth-signature"] = self.api_auth_signature
    return await self._wrapped_transport.handle_async_request(request)
```

**Reusability**: ⭐⭐⭐⭐ HIGH
- Pattern works for ANY multi-header auth scheme
- Separates concerns (client handles one header, transport handles others)
- Environment variable based (STOCKTRIM_API_AUTH_ID, STOCKTRIM_API_AUTH_SIGNATURE)

---

## 11. Unique Innovations vs Katana

### 11.1 Null Field Detection at Transport Level

**Unique to StockTrim**: `stocktrim_client.py:46-72` + error logging

StockTrim's API returns null values for date/datetime fields that the OpenAPI spec doesn't mark as nullable. The client detects this at transport level and suggests fixes:

```python
def _find_null_fields(data: Any, path: str = "") -> list[str]:
    """Recursively find null fields in response."""
    # Returns: ["orderDate", "supplier.supplierName", "items[0].receivedDate"]

# Then in log_parsing_error():
null_fields = _find_null_fields(response_data)
logger.error(f"Found {len(null_fields)} null field(s)")
logger.error("Possible fixes:")
logger.error("  1. Add fields to NULLABLE_FIELDS in regenerate_client.py")
logger.error("  2. Update OpenAPI spec with nullable: true")
logger.error("  3. Handle null defensively in helpers")
```

**Katana Comparison**: Likely doesn't have this level of error intelligence

---

### 11.2 Post-Generation Spec Fixing

**Unique to StockTrim**: `scripts/regenerate_client.py` (1066 lines)

Multiple spec fixes before generation:
1. Add nullable markers to date/enum fields (critical for crash prevention)
2. Add 200 OK responses to POST upsert endpoints
3. Fix DELETE response codes to 204
4. Convert header params to securitySchemes

**Why Needed**: Spec doesn't match actual API behavior. Post-processing normalizes this.

---

### 11.3 Idempotent-Only Retry Strategy

**Unique to StockTrim**: Only retries GET/HEAD/OPTIONS on 5xx (no 429)

```python
class IdempotentOnlyRetry(Retry):
    IDEMPOTENT_METHODS = frozenset(["HEAD", "GET", "OPTIONS", "TRACE"])
    
    def is_retryable_status_code(self, status_code: int) -> bool:
        # Server errors (5xx) only retry idempotent methods
        if self._current_method in self.IDEMPOTENT_METHODS:
            return status_code in [502, 503, 504]
        return False
```

**Katana Difference**: If using rate limiting (429), would need backoff strategy + different status_forcelist

---

## 12. Comparison Summary: StockTrim vs Katana

| Aspect | StockTrim | Katana (Expected) |
|--------|-----------|------------------|
| **Auth Pattern** | Custom headers (api-auth-id + signature) | Bearer token or OAuth2 |
| **Rate Limiting** | No (no 429 handling) | Yes (handles 429 with backoff) |
| **Retry Logic** | Idempotent methods only on 5xx | All methods with 429 backoff |
| **Pagination** | Offset-based (V1) + cursor (V2) | Likely different |
| **API Quirks** | Upsert via POST, inconsistent returns | Likely cleaner API |
| **Error Logging** | Transport-level null field detection | Standard error logging |
| **Post-Gen Fixes** | Extensive spec fixups (nullable fields) | Likely minimal |
| **MCP Integration** | FastMCP server included | Not applicable |
| **Monorepo** | Dual package (client + MCP) | Single package |

---

## 13. Extraction Recommendations for openapi-client-core

### 13.1 High Priority (Extract First)

1. **Transport Layer**
   - `composable.py`: BaseTransport, AuthHeaderTransport pattern
   - `error_logging.py`: ErrorLoggingTransport with null field detection
   - `retry.py`: IdempotentOnlyRetry, RateLimitedRetry variants

2. **Error Handling**
   - `exceptions.py`: APIError and specific subclasses
   - `utils.py`: unwrap(), is_success(), is_error(), get_error_message()

3. **Testing Utilities**
   - fixtures: mock_api_credentials, mock_transport, error_response_fixtures
   - conftest pattern with clear_env autouse fixture

### 13.2 Medium Priority

1. **Helper Base Pattern**
   - Base class (very simple, just stores _client)
   - Recommend in template with example helpers

2. **Code Generation Script**
   - Adapt regenerate_client.py for template
   - Include nullable field fixing logic
   - Document extensibility points

3. **Observability Decorators**
   - observe_tool, observe_service for MCP/general use
   - Timing + error tracking pattern

### 13.3 Low Priority (Reference Only)

1. StockTrim-specific post-gen fixes (document as pattern, not code)
2. Domain-specific helpers (Products, Customers, etc.)
3. MCP server implementation (too StockTrim-specific)

---

## 14. Key Statistics

| Metric | Value |
|--------|-------|
| **Client Package Size** | ~1,674 lines (helpers + client) |
| **Total Tests** | 26 tests across multiple files |
| **Helper Methods** | 10+ domain helpers with 50+ convenience methods |
| **CI/CD Workflows** | 5 workflows (CI, Release, Security, Docs) |
| **Python Versions** | 3 versions tested (3.11, 3.12, 3.13) |
| **Generated Code** | 80+ model classes, 10+ API domains |
| **Documentation** | 20+ markdown files in MkDocs |
| **Code Quality** | ruff (format + lint) + ty type checking |
| **Test Coverage** | pytest with --cov reporting to Codecov |
| **Release Strategy** | Semantic Release with scoped commits |
| **MCP Server** | FastMCP with foundation + workflow tools |

---

## 15. Conclusion

The stocktrim-openapi-client repository demonstrates **production-grade patterns** that are ready for extraction into openapi-client-core:

1. **Composable Transport Architecture**: 4-layer middleware pattern is generic and reusable
2. **Sophisticated Error Handling**: Null field detection and ProblemDetails support are industry-leading
3. **Comprehensive Testing**: Fixtures and conftest patterns are excellent reference
4. **Modern Python Practices**: ruff, UV, pre-commit, semantic release, type checking (ty)
5. **Monorepo Support**: Dual-package versioning and coordination is well-executed
6. **Code Generation**: Regenerate script with post-processing fixes is comprehensive

**Next Steps for openapi-client-template**:
1. Extract transport, error handling, retry logic to core library
2. Adapt code generation script as template reusable
3. Include testing patterns in template
4. Document authentication customization points
5. Provide optional MCP server starter

