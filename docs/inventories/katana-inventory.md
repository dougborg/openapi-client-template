# Katana OpenAPI Client - Comprehensive Infrastructure Inventory

**Repository**: katana-openapi-client
**Purpose**: Document all reusable patterns for extraction into `openapi-client-core` and template improvements
**Date**: 2025-11-09
**Status**: Complete ✅

---

## Executive Summary

The katana-openapi-client repository contains a wealth of production-ready patterns and infrastructure that can be extracted into reusable components. This inventory catalogs **8 major categories** of reusable infrastructure:

### Key Findings

**Highest Value Extractions** (Priority 1 - Must Have):
1. ⭐⭐⭐⭐⭐ Transport layers (retry, pagination, error logging)
2. ⭐⭐⭐⭐⭐ Credential resolution (multi-source auth)
3. ⭐⭐⭐⭐⭐ Base client pattern
4. ⭐⭐⭐⭐⭐ Test fixtures and helpers

**Template Improvements** (Very High Priority):
1. ⭐⭐⭐⭐⭐ All 4 CI/CD workflows (ci, release, docs, security)
2. ⭐⭐⭐⭐⭐ Complete pyproject.toml structure
3. ⭐⭐⭐⭐⭐ Pre-commit hooks (both versions)
4. ⭐⭐⭐⭐⭐ README structure
5. ⭐⭐⭐⭐⭐ MkDocs setup

**Agent Configurations** (Medium-High Value):
- 7 specialized GitHub Copilot agents
- Comprehensive guides and instructions
- Custom prompts for common tasks

---

## Table of Contents

1. [OpenAPI Client Logic](#1-openapi-client-logic)
2. [CI/CD Infrastructure](#2-cicd-infrastructure)
3. [Project Automation & Tooling](#3-project-automation--tooling)
4. [Agent Configurations](#4-agent-configurations)
5. [Testing Infrastructure](#5-testing-infrastructure)
6. [Documentation](#6-documentation)
7. [Build & Packaging](#7-build--packaging)
8. [Project Structure](#8-project-structure)
9. [Summary & Migration Priorities](#summary--migration-priorities)

---

## 1. OpenAPI Client Logic

### 1.1 Retry Mechanisms

**Location**: `katana_public_api_client/katana_client.py` (Lines 36-95)

**Implementation**:
```python
class RateLimitAwareRetry(Retry):
    """Custom retry that allows POST/PATCH retry ONLY for 429 errors"""
    IDEMPOTENT_METHODS = frozenset(["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"])

    def is_retryable_status_code(self, status_code: int) -> bool:
        # Rate limiting (429) - retry all methods
        if status_code == HTTPStatus.TOO_MANY_REQUESTS:
            return True
        # Server errors - only retry idempotent methods
        return self._current_method in self.IDEMPOTENT_METHODS
```

**Configuration**:
- Uses `httpx-retries` library
- Backoff strategy: Exponential with factor 1.0 (1s, 2s, 4s, 8s, 16s)
- Max retries: 5 (configurable via `max_retries` parameter)
- Status codes: `[429, 502, 503, 504]`
- Respects `Retry-After` header: `True`

**Dependencies**:
- `httpx-retries>=0.4.3,<0.5.0`
- `httpx>=0.28.0`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Fully generic retry logic
- Configurable parameters
- Smart idempotency detection
- Works with any httpx-based client

**Migration Strategy**:
1. Extract `RateLimitAwareRetry` class to `openapi_client_core.transports.retry`
2. Template should import and use this class in generated client
3. Make all parameters (backoff_factor, max_retries, status codes) configurable via template variables

---

### 1.2 Pagination Patterns

**Location**: `katana_public_api_client/katana_client.py` (Lines 317-538)

**Implementation**:
```python
class PaginationTransport(AsyncHTTPTransport):
    """Automatic pagination for GET requests with page/limit params"""

    async def _handle_paginated_request(self, request):
        all_data = []
        for page_num in range(1, self.max_pages + 1):
            response = await self._wrapped_transport.handle_async_request(paginated_request)
            pagination_info = self._extract_pagination_info(response, data)
            all_data.extend(items)
            if (total_pages and current_page >= total_pages) or len(items) == 0:
                break
```

**Detection Strategy**:
- Triggers for: GET requests with `page` or `limit` parameters
- Pagination metadata sources:
  1. `X-Pagination` JSON header
  2. Individual headers (`X-Total-Pages`, `X-Current-Page`)
  3. Response body `pagination` field
  4. Response body `meta.pagination` field

**Configuration**:
- Max pages: 100 (configurable via `max_pages` parameter)
- Safety limit to prevent infinite loops
- Automatic detection - no explicit opt-in needed
- Disable by specifying explicit `page` parameter

**Dependencies**:
- Pure Python stdlib (json)
- httpx transport layer

**Reusability**: ⭐⭐⭐⭐ MEDIUM-HIGH
- Generic for any API with pagination
- Needs API-specific pagination format detection
- Works with multiple pagination formats

**Migration Strategy**:
1. Extract `PaginationTransport` to `openapi_client_core.transports.pagination`
2. Make pagination header/body extraction pluggable
3. Template should provide API-specific pagination configuration
4. Consider making pagination format configurable via OpenAPI spec extensions

---

### 1.3 Authentication Methods

**Location**: `katana_public_api_client/katana_client.py` (Lines 672-793)

**Implementation**:
```python
class KatanaClient(AuthenticatedClient):
    def __init__(self, api_key=None, ...):
        # Priority: param > env > .env > netrc
        api_key = (
            api_key
            or os.getenv("KATANA_API_KEY")
            or self._read_from_netrc(base_url)
        )
```

**Auth Sources (in priority order)**:
1. **Direct parameter**: `api_key` argument
2. **Environment variable**: `KATANA_API_KEY`
3. **`.env` file**: Loaded via `python-dotenv`
4. **`~/.netrc` file**: Standard Unix credential file

**Netrc Implementation**: Lines 672-725
```python
def _read_from_netrc(base_url: str) -> str | None:
    parsed = urlparse(base_url)
    host = parsed.hostname or base_url.split("/")[0]
    auth = netrc.netrc(Path.home() / ".netrc")
    authenticators = auth.authenticators(host)
    if authenticators:
        _login, _account, password = authenticators
        return password
```

**Dependencies**:
- `python-dotenv>=1.0.0`
- Python stdlib: `netrc`, `os`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Multi-source credential resolution
- Standard patterns (env vars, dotenv, netrc)
- Secure fallback chain

**Migration Strategy**:
1. Extract credential resolution to `openapi_client_core.auth`
2. Create `CredentialResolver` class with pluggable sources
3. Template should instantiate with API-specific env var names
4. Document credential sources in generated README

---

### 1.4 Error Handling and Translation

**Location**: `katana_public_api_client/katana_client.py` (Lines 97-315)

**Implementation**:
```python
class ErrorLoggingTransport(AsyncHTTPTransport):
    """Transport that logs detailed 4xx errors using generated models"""

    async def _log_client_error(self, response, request):
        # Try parsing as DetailedErrorResponse (422 errors)
        if status_code == 422:
            detailed_error = DetailedErrorResponse.from_dict(error_data)
            self._log_detailed_error(detailed_error, method, url, status_code)
        else:
            # Parse as ErrorResponse
            error_response = ErrorResponse.from_dict(error_data)
            self._log_error(error_response, method, url, status_code)
```

**Error Types**:
1. **ValidationError (422)**: Uses `DetailedErrorResponse` with validation details array
2. **ClientError (4xx)**: Uses `ErrorResponse` with error name/message
3. **ServerError (5xx)**: Handled by retry logic, not logged (too noisy)

**Detailed Validation Logging**: Lines 193-276
- Logs error name, message, code
- Iterates through validation details (path, code, message, info)
- Handles nested error structures in `additional_properties`

**Dependencies**:
- Generated error models: `DetailedErrorResponse`, `ErrorResponse`
- Python stdlib: `logging`, `json`

**Reusability**: ⭐⭐⭐ MEDIUM
- API-specific error models
- Generic error logging pattern
- Requires error response structure

**Migration Strategy**:
1. Extract error logging transport to `openapi_client_core.transports.error_logging`
2. Make error model mapping configurable
3. Template should provide mapping from status codes to error models
4. Consider using OpenAPI spec error responses for automatic mapping

---

### 1.5 Rate Limiting

**Location**: Integrated with retry mechanism (Section 1.1)

**Implementation**: Smart 429 handling in `RateLimitAwareRetry`
- **All HTTP methods** (including POST, PATCH) can be retried on 429
- Respects `Retry-After` header
- Exponential backoff as fallback

**Strategy**:
- Pre-emptive: No (reactive only via 429 responses)
- Token bucket: No
- Rate limiter: Built into API via 429 responses
- Client-side throttling: No (relies on server signals)

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Generic 429 handling
- Standard HTTP practice

**Migration Strategy**:
- Already part of retry mechanism (Section 1.1)
- No separate extraction needed

---

### 1.6 Request/Response Processing

**Location**: `katana_public_api_client/katana_client.py` (Lines 806-825, 956-986)

**Event Hooks**:
```python
event_hooks = {
    "response": [
        self._capture_pagination_metadata,  # Extract X-Pagination header
        self._log_response_metrics,         # Log request timing
    ]
}
```

**Response Processing**:
1. **Pagination metadata capture**: Lines 957-968
   - Extracts `X-Pagination` JSON header
   - Stores as `response.pagination_info` attribute
   - Logs via debug level

2. **Response metrics logging**: Lines 970-986
   - Logs status code, method, URL, duration
   - Debug level for observability

**Dependencies**:
- httpx event hooks
- Python stdlib: `json`, `logging`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Generic event hook pattern
- Pluggable hooks

**Migration Strategy**:
1. Extract default hooks to `openapi_client_core.hooks`
2. Make hooks configurable and extensible
3. Template should set up default hooks + allow user hooks
4. Document hook interface for customization

---

### 1.7 Base Client Classes and Patterns

**Location**: `katana_public_api_client/client.py`

**Generated Base Classes**:
1. **`Client`**: Unauthenticated base (Lines 8-131)
   - Manages httpx.Client/AsyncClient lifecycle
   - Context manager support
   - Configuration: base_url, cookies, headers, timeout, verify_ssl

2. **`AuthenticatedClient`**: Authenticated base (Lines 133-268)
   - Inherits from Client pattern
   - Adds `token`, `prefix`, `auth_header_name`
   - Automatically sets `Authorization` header

**Custom Wrapper**:
3. **`KatanaClient`**: Enhanced client (Lines 636-986)
   - Inherits from `AuthenticatedClient`
   - Adds resilient transport layer
   - Provides domain helper properties
   - Multi-source credential resolution

**Pattern**: Layered inheritance
- Generated base → Generated authenticated → Custom enhanced

**Dependencies**:
- `httpx>=0.28.0`
- `attrs>=22.2.0`
- Python stdlib: `ssl`, `typing`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- `Client` and `AuthenticatedClient` are generated
- Pattern of wrapping with resilient transport is generic

**Migration Strategy**:
1. Template generates `Client` and `AuthenticatedClient` (already done)
2. Extract enhanced client pattern to `openapi_client_core.client.EnhancedClient`
3. Template should generate a custom client class inheriting from `EnhancedClient`
4. Configure transport layers via template variables

---

## 2. CI/CD Infrastructure

### 2.1 GitHub Actions Workflows

#### Main CI Workflow

**Location**: `.github/workflows/ci.yml`

**Key Features**:
- **Smart change detection**: Skips CI for docs-only changes using `dorny/paths-filter@v3`
- **Matrix testing**: Python 3.12, 3.13, 3.14
- **Parallel jobs**: test + quality
- **Concurrency control**: Cancels in-progress runs on new commits
- **Steps**:
  1. Format check (`poe format-check`)
  2. Linting + type checking (`poe lint`)
  3. Tests with coverage (`poe test-coverage`)
  4. Coverage upload to Codecov
  5. OpenAPI validation (`poe validate-openapi`)
  6. Docs build + test

**Dependencies**:
- `astral-sh/setup-uv@v7`
- `actions/checkout@v5`
- `codecov/codecov-action@v5`
- `dorny/paths-filter@v3`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Template workflow with placeholders:
   - Python versions: `{{python_versions}}`
   - Test command: `{{test_command}}`
   - Lint command: `{{lint_command}}`
2. Include smart change detection pattern
3. Document required secrets (CODECOV_TOKEN)

---

#### Release Workflow

**Location**: `.github/workflows/release.yml`

**Key Features**:
- **Dual-package release**: Separate jobs for client and MCP server
- **Semantic versioning**: Uses `python-semantic-release@v10.4.1`
- **Commit filtering**: Only releases for commits with `(client)` or `(mcp)` scope
- **PyPI publishing**: Trusted publisher with attestations
- **Docker publishing**: Multi-platform (amd64, arm64) to GHCR
- **Manual triggers**: Workflow dispatch with force-publish options

**Semantic Release Configuration** (from `pyproject.toml`):
```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
commit_message = "chore(release): client v{version}"
tag_format = "client-v{version}"
allowed_tags = ["build", "chore", "ci", "docs", "feat", "fix", "perf", "style", "refactor", "test"]
minor_tags = ["feat"]
patch_tags = ["fix", "perf"]
```

**Dependencies**:
- `python-semantic-release@v10.4.1`
- `pypa/gh-action-pypi-publish@release/v1`
- `docker/build-push-action@v6`

**Secrets Required**:
- `SEMANTIC_RELEASE_TOKEN`: GitHub token with write permissions
- `GITHUB_TOKEN`: Auto-provided for PyPI trusted publishing

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Template workflow for single or multi-package repos
2. Make commit scope filtering configurable
3. Document semantic-release setup
4. Provide PyPI trusted publisher setup guide

---

#### Documentation Workflow

**Location**: `.github/workflows/docs.yml`

**Key Features**:
- **GitHub Pages deployment**: Uses `actions/deploy-pages@v4`
- **MkDocs build**: Full docs build with `poe docs-build`
- **Triggers**: Push to main on docs paths or manual dispatch
- **Concurrency**: Only one deployment at a time

**Configuration**: `mkdocs.yml`
- Theme: Material for MkDocs
- Plugins: search, gen-files, literate-nav, swagger-ui-tag, mkdocstrings
- Auto-generated API reference from docstrings
- OpenAPI spec viewer

**Dependencies**:
- `mkdocs>=1.6.0`
- `mkdocs-material>=9.5.0`
- `mkdocstrings[python]>=0.25.0`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Template MkDocs configuration with project-specific values
2. Include gen_ref_pages.py script for auto API docs
3. Template docs structure with customizable sections
4. Document GitHub Pages setup

---

#### Security Workflow

**Location**: `.github/workflows/security.yml`

**Key Features**:
- **Trivy scanner**: Filesystem vulnerability scanning
- **Semgrep**: Static analysis for security issues
- **SARIF upload**: Results to GitHub Security tab
- **Scheduled scans**: Weekly on Sundays
- **Dependency review**: On pull requests

**Tools**:
- Trivy: `aquasecurity/trivy-action@0.33.1`
- Semgrep: Auto-config, latest rules
- Dependency Review: `actions/dependency-review-action@v4`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Include security workflow in template as-is
2. Document permissions needed
3. Optional: Make scan schedule configurable

---

### 2.2 Testing Strategies

**Test Organization**: `tests/`

**Test Categories** (from `pyproject.toml` markers):
1. **Unit tests**: `@pytest.mark.unit`
2. **Integration tests**: `@pytest.mark.integration`
3. **Slow tests**: `@pytest.mark.slow`
4. **Doc tests**: `@pytest.mark.docs` (CI-only)
5. **Schema validation**: `@pytest.mark.schema_validation` (separate run)

**Key Test Files**:
- `conftest.py`: Fixtures for mock clients, transports, responses
- `test_katana_client.py`: Core client functionality
- `test_transport_*.py`: Transport layer tests (retry, pagination, edge cases)
- `test_rate_limit_retry.py`: Rate limiting behavior
- `test_performance.py`: Performance benchmarks
- `test_real_api.py`: Live API integration (marked `integration`)

**Test Fixtures** (from `conftest.py`):
```python
@pytest.fixture
def katana_client(mock_api_credentials):
    return KatanaClient(**mock_api_credentials)

@pytest.fixture
def mock_transport(mock_transport_handler):
    return httpx.MockTransport(mock_transport_handler)

def create_auto_paginated_mock_handler(all_items, page_size=50):
    # Helper for pagination testing
```

**Coverage Configuration**:
```toml
[tool.coverage.run]
source = ["katana_public_api_client"]
omit = ["*/tests/*", "*/test_*", "*/conftest.py"]
```

**Parallel Testing**:
- pytest-xdist with 4 workers (36% faster)
- Optimal for 4+ core systems
- Schema validation tests run separately (not parallel-safe)

**Dependencies**:
- `pytest>=7.2.0`
- `pytest-asyncio>=0.21.0`
- `pytest-cov>=2.8.0`
- `pytest-mock>=3.10.0`
- `pytest-timeout>=2.1.0`
- `pytest-xdist>=3.6.1`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Extract common fixtures to `openapi_client_core.testing`
2. Template pytest configuration with markers
3. Provide test structure guide
4. Include example tests for transport, client, helpers

---

### 2.3 Code Quality Checks

**Linting Configuration**: `pyproject.toml` (Lines 230-273)

**Tools**:
1. **Ruff**: Combined linter + formatter
   - Line length: 88
   - Target: Python 3.12+
   - Rules: E, W, F, I, B, C4, UP, SIM, RUF, PLE, PLW
   - Auto-fix enabled
   - Docstring formatting: Google style

2. **Type Checker**: ty (Astral's Rust-based)
   - Replacement for mypy
   - Faster, minimal config
   - Excludes: `tests/conftest.py`, `scripts/extract_all_katana_docs.py`

3. **YAML Linter**: yamllint
   - Configuration: `.yamllint.yml`
   - Validates workflow files

**Pre-commit Configuration**: `.pre-commit-config.yaml`
```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-format
      - id: ruff-check
      - id: mdformat
      - id: yamllint
      - id: pytest
```

**Poe Tasks** (Lines 339-425):
```bash
poe format          # Format all code
poe format-check    # Check formatting
poe lint            # Run all linters
poe typecheck       # Type checking
poe test            # Run tests
poe test-coverage   # Tests with coverage
poe check           # Full check: format + lint + test
poe ci              # Full CI pipeline
```

**Dependencies**:
- `ruff>=0.12.4,<0.13`
- `ty>=0.0.1a25` (type checker)
- `pre-commit>=4.2.0`
- `yamllint>=1.37.0`
- `mdformat>=0.7.17` (with gfm, tables, toc plugins)

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Template ruff configuration with customizable rules
2. Include pre-commit config as-is
3. Template poe tasks with project-specific commands
4. Document tool versions in template README

---

### 2.4 Coverage Reporting

**Configuration**: `pyproject.toml` (Lines 212-228)

```toml
[tool.coverage.run]
source = ["katana_public_api_client"]
omit = ["*/tests/*", "*/test_*", "*/conftest.py"]

[tool.coverage.report]
exclude_lines = [
  "pragma: no cover",
  "def __repr__",
  "if self.debug:",
  "if settings.DEBUG",
  "raise AssertionError",
  "raise NotImplementedError",
  "if 0:",
  "if __name__ == .__main__.:",
  "class .*\\bProtocol\\):",
  "@(abc\\.)?abstractmethod",
]
```

**CI Integration**: `.github/workflows/ci.yml` (Lines 81-86)
```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v5
  with:
    files: coverage.xml
    fail_ci_if_error: false
```

**Coverage Analysis Script**: `scripts/analyze_coverage.py`
- Breaks down coverage by file type (generated vs core logic)
- Current stats: 74.8% core logic coverage, 45% generated code

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Template coverage configuration
2. Include Codecov integration in CI workflow
3. Optional: Include coverage analysis script
4. Document coverage goals in CONTRIBUTING.md

---

## 3. Project Automation & Tooling

### 3.1 Pre-commit Hooks

**Location**: `.pre-commit-config.yaml`

**Strategy**: Local hooks via `uv run` (no network dependency)
- Reason: Avoid network restrictions in CI environments (GitHub Copilot agents)
- All tools installed via project dependencies

**Hooks**:
1. `ruff-format`: Format Python code
2. `ruff-check --fix`: Auto-fix linting issues
3. `mdformat`: Format markdown files (excludes CHANGELOG.md)
4. `yamllint`: Validate YAML files
5. `pytest`: Run test suite

**Configuration**:
```yaml
- id: mdformat
  exclude: '(CHANGELOG\.md|\.agent\.md$)'

- id: pytest
  pass_filenames: false  # Run all tests, not just changed files
  always_run: true
```

**Lite Version**: `.pre-commit-config-lite.yaml`
- Skips pytest for faster commits
- For quick local development

**Dependencies**:
- `pre-commit>=4.2.0`
- All hooks use project dependencies via `uv run`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Template both configs (full + lite)
2. Document when to use each
3. Include in setup instructions
4. Make test hook optional via template variable

---

### 3.2 Dependency Management

**Tool**: uv (Astral's fast Python package manager)

**Configuration**: `pyproject.toml` (Lines 40-53, 66-99)

**Core Dependencies**:
```toml
[project]
dependencies = [
  "httpx>=0.28.0",
  "attrs>=22.2.0",
  "python-dateutil>=2.8.0",
  "tenacity>=9.0.0",
  "python-dotenv>=1.0.0",
  "pydantic>=2,<3",
  "httpx-retries>=0.4.3,<0.5.0",
]
```

**Dev Dependencies** (Lines 66-99):
- Testing: pytest family
- Linting: ruff, pre-commit, yamllint
- OpenAPI: openapi-python-client, openapi-spec-validator
- Docs: mkdocs, mkdocs-material, mkdocstrings
- Release: python-semantic-release

**Workspace Configuration** (Lines 128-129):
```toml
[tool.uv.workspace]
members = [".", "katana_mcp_server"]
```

**Lock File**: `uv.lock`
- Single lock file for all workspace packages
- Reproducible builds
- Fast resolution

**Commands**:
```bash
uv sync --all-extras    # Install all dependencies
uv add package          # Add dependency
uv remove package       # Remove dependency
uv run command          # Run command in env
```

**Dependencies**:
- uv >= 0.5.x (not in requirements, installed system-wide)

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Template pyproject.toml with core dependencies
2. Document uv installation
3. Provide migration guide from Poetry/pip
4. Include ADR explaining uv choice

---

### 3.3 Build System

**Build Backend**: Hatchling

**Configuration**: `pyproject.toml` (Lines 111-136)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["katana_public_api_client"]

[tool.hatch.build.targets.wheel.force-include]
"docs/katana-openapi.yaml" = "katana_public_api_client/katana-openapi.yaml"
```

**Package Metadata** (Lines 1-60):
- Name, version, description
- Authors, maintainers, license
- Python requires: `>=3.12`
- Keywords, classifiers
- URLs: homepage, repository, docs, issues, changelog

**Build Commands**:
```bash
uv build              # Build wheel + sdist
uv build --wheel      # Build wheel only
uv build --sdist      # Build source distribution
```

**Distribution**:
- PyPI publishing via GitHub Actions
- Trusted publisher (no tokens needed)
- Build artifacts upload

**Dependencies**:
- `build>=1.0.0` (optional, for manual builds)
- hatchling (specified in build-system.requires)

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Template build-system configuration
2. Template package metadata with placeholders
3. Include distribution guide
4. Document PyPI trusted publisher setup

---

### 3.4 Type Checking Configuration

**Tool**: ty (Astral's Rust-based type checker)

**Configuration**: `pyproject.toml` (Lines 137-150)

```toml
[tool.ty]
# ty auto-discovers source files from project root
# Use --exclude flags in command line for exclusions
```

**Command** (from poe tasks):
```bash
ty check --exclude 'tests/conftest.py' --exclude 'scripts/extract_all_katana_docs.py' --exclude 'katana_mcp_server/'
```

**Legacy mypy config** (commented out, Lines 152-190):
- Kept for reference/fallback
- Strict typing rules documented

**Type Stubs**:
```toml
[project.optional-dependencies.dev]
"types-python-dateutil>=2.8.0"
"types-PyYAML>=6.0.0"
"types-urllib3>=1.26.0"
```

**Dependencies**:
- `ty>=0.0.1a25` (pre-alpha, minimal config support)

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH

**Migration Strategy**:
1. Template ty configuration (minimal, as it's pre-alpha)
2. Include fallback mypy config
3. Document both options
4. Provide type stubs for common dependencies

---

## 4. Agent Configurations

### 4.1 GitHub Copilot Configuration

**Location**: `.github/copilot-instructions.md`

**Available Agents** (7 specialized agents):
1. **code-reviewer**: Code review, best practices
2. **documentation-writer**: Docs generation, ADRs
3. **python-developer**: Python development
4. **ci-cd-specialist**: CI/CD workflows, deployment
5. **tdd-specialist**: Test-driven development
6. **project-coordinator**: Project management, planning
7. **task-planner**: Task breakdown, estimation

**Agent Structure** (example: `python-developer.agent.md`):
```markdown
# Agent Name
Role description and responsibilities

## Expertise
- Skill 1
- Skill 2

## Guidelines
- Guideline 1
- Guideline 2

## Context Files
- Relevant project files
- Architecture docs
```

**Shared Guides** (`.github/agents/guides/`):
- `ARCHITECTURE_QUICK_REF.md`: Project architecture overview
- `COMMIT_STANDARDS.md`: Commit message conventions
- `FILE_ORGANIZATION.md`: Project structure
- `VALIDATION_TIERS.md`: Testing levels

**DevOps Guides**:
- `CI_DEBUGGING.md`: CI troubleshooting
- `CLIENT_REGENERATION.md`: OpenAPI client regeneration
- `DEPENDENCY_UPDATES.md`: Dependency management
- `RELEASE_PROCESS.md`: Release workflow

**Planning Guides**:
- `EFFORT_ESTIMATION.md`: Story point estimation
- `ISSUE_TEMPLATES.md`: GitHub issue templates
- `PLANNING_PROCESS.md`: Sprint planning

**Custom Instructions** (`.github/instructions/`):
- `python.instructions.md`: Python coding standards
- `pytest.instructions.md`: Testing patterns
- `markdown.instructions.md`: Documentation style

**Custom Prompts** (`.github/prompts/`):
- `create-adr.prompt.md`: ADR generation
- `create-test.prompt.md`: Test generation
- `regenerate-client.prompt.md`: Client regeneration
- `update-docs.prompt.md`: Documentation updates

**Reusability**: ⭐⭐⭐⭐ MEDIUM-HIGH
- Agents are project-specific but patterns are generic
- Guides and instructions are highly reusable
- Custom prompts need adaptation

**Migration Strategy**:
1. Extract generic agent templates
2. Parameterize project-specific content
3. Include sample agents with placeholders
4. Document agent customization guide
5. Provide template for creating new agents

---

### 4.2 MCP (Model Context Protocol) Setup

**Location**: `katana_mcp_server/` (workspace member)

**Package Structure**:
```
katana_mcp_server/
├── pyproject.toml          # Separate package config
├── src/katana_mcp/
│   ├── server.py           # MCP server implementation
│   ├── tools/              # MCP tools
│   │   ├── foundation/     # Core API tools
│   │   └── workflows/      # Business logic tools
│   ├── prompts/            # Pre-defined prompts
│   └── resources/          # Static resources
├── tests/                  # MCP-specific tests
└── docker-compose.yml      # Docker deployment
```

**MCP Server Configuration**: `katana_mcp_server/pyproject.toml`
```toml
[project]
name = "katana-mcp-server"
dependencies = [
    "katana-openapi-client",  # Uses sibling package
    "fastmcp>=1.0.0",
    "structlog>=24.0.0",
]
```

**Tools Implementation** (example: `tools/foundation/catalog.py`):
```python
@server.tool()
async def search_products(query: str, limit: int = 10) -> list[Product]:
    """Search products in Katana catalog"""
    async with KatanaClient() as client:
        return await client.products.search(query, limit=limit)
```

**Docker Deployment**: `katana_mcp_server/docker-compose.yml`
- Multi-stage build
- Health checks
- Environment variable configuration

**Reusability**: ⭐⭐⭐ LOW-MEDIUM
- MCP server is domain-specific (Katana API)
- Pattern of creating MCP server for API client is reusable
- Tool structure is generic

**Migration Strategy**:
1. Document MCP server creation pattern
2. Provide MCP server template (optional)
3. Include ADR on when to create MCP server
4. Document fastmcp integration

---

## 5. Testing Infrastructure

### 5.1 Test Fixtures and Helpers

**Location**: `tests/conftest.py`

**Core Fixtures**:

1. **Mock Credentials**:
```python
@pytest.fixture
def mock_api_credentials():
    return {
        "api_key": "test-api-key-12345",
        "base_url": "https://api.katana.test",  # RFC 6761 reserved TLD
    }
```

2. **Client Fixtures**:
```python
@pytest.fixture
def katana_client(mock_api_credentials):
    return KatanaClient(**mock_api_credentials)

@pytest.fixture
def katana_client_limited_pages(mock_api_credentials):
    return KatanaClient(max_pages=5, **mock_api_credentials)
```

3. **Mock Transport**:
```python
@pytest.fixture
def mock_transport(mock_transport_handler):
    return httpx.MockTransport(mock_transport_handler)

@pytest.fixture
def katana_client_with_mock_transport(mock_api_credentials, mock_transport):
    client = KatanaClient(**mock_api_credentials)
    mock_httpx_client = httpx.AsyncClient(
        transport=mock_transport,
        base_url=mock_api_credentials["base_url"]
    )
    client._client._async_client = mock_httpx_client
    return client
```

4. **Helper Functions** (Lines 177-299):
```python
def create_mock_paginated_response(page=1, data=None, is_last_page=False, total_pages=1):
    """Create properly formatted mock response with X-Pagination header"""

def create_paginated_mock_handler(pages_data):
    """Mock handler that returns different responses for different pages"""

def create_auto_paginated_mock_handler(all_items, page_size=50):
    """Mock handler that automatically paginates a list of items"""
```

**Environment Setup** (Lines 138-163):
```python
@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch, request):
    """Set up test environment variables"""
    is_real_api_test = "integration" in request.node.keywords

    if is_real_api_test:
        load_dotenv(override=False)  # Real credentials
    else:
        monkeypatch.setenv("KATANA_API_KEY", "test-key")
        monkeypatch.setenv("KATANA_BASE_URL", "https://api.katana.test")
```

**Dependencies**:
- `pytest>=7.2.0`
- `pytest-asyncio>=0.21.0`
- `pytest-mock>=3.10.0`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Generic fixture patterns
- Pagination testing helpers
- Environment isolation

**Migration Strategy**:
1. Extract to `openapi_client_core.testing.fixtures`
2. Parameterize API-specific parts (credentials, base URL)
3. Include pagination helpers in template
4. Document fixture customization

---

### 5.2 Integration Test Patterns

**Location**: `tests/test_real_api.py`

**Pattern**:
```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("KATANA_API_KEY"), reason="Real API key required")
async def test_real_api_products():
    """Test against real Katana API"""
    async with KatanaClient() as client:
        # Test actual API calls
        products = await client.products.list(limit=5)
        assert len(products) > 0
```

**Key Features**:
- Marked with `@pytest.mark.integration`
- Conditional skip if no credentials
- Uses real API credentials from environment
- Limited API calls to avoid rate limits

**Environment Setup**:
- `.env` file for local testing
- CI secrets for automated testing
- Graceful degradation if credentials missing

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Standard integration test pattern
- Environment-aware

**Migration Strategy**:
1. Template integration test examples
2. Document credential setup
3. Include CI configuration for integration tests
4. Provide skip conditions

---

## 6. Documentation

### 6.1 README Structure

**Location**: `README.md`

**Structure** (comprehensive, 442 lines):

1. **Header**:
   - Project title
   - Description
   - Badges (Python version, CI, codecov, docs, security)

2. **Features** (Lines 16-27):
   - Bullet list of key features
   - Production-ready emphasis

3. **Quick Start** (Lines 29-130):
   - Installation instructions (uv + pip)
   - Configuration (4 methods)
   - Basic usage example
   - KatanaClient usage

4. **API Coverage** (Lines 132-144):
   - Table of endpoint categories
   - Total endpoint count

5. **Why KatanaClient?** (Lines 146-181):
   - Automatic resilience features
   - Pythonic design
   - Transport-layer architecture

6. **Advanced Usage** (Lines 183-257):
   - Custom configuration
   - Automatic pagination
   - Response unwrapping utilities

7. **Project Structure** (Lines 259-288):
   - Monorepo structure
   - Workspace explanation
   - ADR reference

8. **Testing** (Lines 290-302):
   - Test commands
   - Coverage commands

9. **Documentation** (Lines 304-338):
   - User guides
   - Architecture & design (ADRs)
   - Project analysis

10. **Development Workflow** (Lines 340-417):
    - Setup instructions
    - Code quality tasks
    - OpenAPI generation
    - Pre-commit hooks
    - CI/development workflows

11. **Configuration** (Lines 419-432):
    - Tool summary

12. **License, Contributing** (Lines 434-442):
    - MIT License
    - Contributing guide link

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Comprehensive template structure
- Well-organized sections

**Migration Strategy**:
1. Extract README template with placeholders
2. Parameterize:
   - Project name, description
   - Feature list
   - API coverage stats
   - Badge URLs
3. Include in template with Jinja2 variables
4. Provide README generation script

---

### 6.2 API Documentation Generation

**Tool**: MkDocs with MkDocs-Material

**Configuration**: `mkdocs.yml` (181 lines)

**Key Plugins**:
1. **search**: Full-text search
2. **gen-files**: Auto-generate API reference
3. **literate-nav**: Dynamic navigation from SUMMARY.md
4. **swagger-ui-tag**: OpenAPI spec viewer
5. **mkdocstrings[python]**: Auto-generate API docs from docstrings

**Auto-Generation Script**: `docs/gen_ref_pages.py`
```python
"""Generate the code reference pages."""
import mkdocs_gen_files

for path in sorted(Path("src").rglob("*.py")):
    # Generate markdown file for each Python module
    with mkdocs_gen_files.open(doc_path, "w") as fd:
        print("::: " + module_path, file=fd)
```

**Docstring Style**: Google format
```python
def method(arg1: str, arg2: int) -> bool:
    """Short description.

    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.

    Returns:
        Description of return value.

    Example:
        >>> method("test", 42)
        True
    """
```

**Theme Configuration**:
- Material theme with dark/light mode
- Navigation tabs + sections
- Code copy buttons
- Search suggestions

**Dependencies**:
- `mkdocs>=1.6.0`
- `mkdocs-material>=9.5.0`
- `mkdocstrings[python]>=0.25.0`
- `mkdocs-gen-files>=0.5.0`
- `mkdocs-literate-nav>=0.6.0`
- `mkdocs-swagger-ui-tag>=0.7.1`

**Build Commands**:
```bash
poe docs-build      # Build docs
poe docs-serve      # Serve locally
poe docs-autobuild  # Auto-rebuild on changes
```

**Deployment**: GitHub Pages via `.github/workflows/docs.yml`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Standard MkDocs setup
- Auto-generation script is generic

**Migration Strategy**:
1. Template mkdocs.yml with project-specific values
2. Include gen_ref_pages.py script
3. Template navigation structure
4. Document docstring standards
5. Include in CI/CD workflow template

---

### 6.3 Code Examples

**Location**: `examples/client/`

**Examples**:
1. `basic_usage.py`: Simple product listing
2. `concurrent_requests.py`: Parallel API calls
3. `error_handling.py`: Exception handling patterns
4. `inventory_sync.py`: Complete inventory sync workflow
5. `low_stock_monitoring.py`: Real-time monitoring
6. `sync_usage.py`: Synchronous client usage
7. `using_utils.py`: Response unwrapping utilities

**Example Structure**:
```python
"""Example: Basic usage of KatanaClient

This example demonstrates:
- Client initialization
- Basic API calls
- Error handling
"""
import asyncio
from katana_public_api_client import KatanaClient

async def main():
    # Example code with comments
    async with KatanaClient() as client:
        products = await client.products.list(limit=10)
        print(f"Found {len(products)} products")

if __name__ == "__main__":
    asyncio.run(main())
```

**README**: `examples/README.md`
- Prerequisites
- Running examples
- Example descriptions

**Dependencies**:
- Main package only
- No additional dependencies

**Reusability**: ⭐⭐⭐⭐ MEDIUM-HIGH
- Examples are API-specific
- Patterns are generic (initialization, error handling, etc.)

**Migration Strategy**:
1. Create example templates for common patterns
2. Parameterize API-specific parts
3. Include in template as optional extras
4. Document example structure

---

## 7. Build & Packaging

### 7.1 pyproject.toml Structure

**Location**: `pyproject.toml` (500 lines)

**Sections**:

1. **Project Metadata** (Lines 1-60):
   - name, version, description
   - authors, maintainers, license
   - readme, requires-python
   - keywords, classifiers
   - URLs (homepage, repository, docs, issues, changelog)

2. **Dependencies** (Lines 40-53):
   - Core runtime dependencies
   - Version constraints

3. **Optional Dependencies** (Lines 66-109):
   - dev: testing, linting, type checking
   - docs: MkDocs, Material, mkdocstrings

4. **Build System** (Lines 111-136):
   - Hatchling backend
   - Wheel configuration
   - Force-include files (OpenAPI spec)

5. **Type Checker** (Lines 137-190):
   - ty configuration (minimal)
   - Legacy mypy configuration (commented)

6. **Pytest** (Lines 191-210):
   - Test discovery
   - Markers
   - Asyncio configuration
   - Timeout settings

7. **Coverage** (Lines 212-228):
   - Source paths
   - Exclusions
   - Report configuration

8. **Ruff** (Lines 230-273):
   - Line length, target version
   - Format options
   - Lint rules (select/ignore)
   - Per-file ignores
   - isort configuration

9. **mdformat** (Lines 275-284):
   - Wrap settings
   - Extensions (gfm, tables, toc)

10. **Semantic Release** (Lines 286-333):
    - Version files
    - Commit parsing
    - Changelog generation
    - Tag format

11. **Poe Tasks** (Lines 339-499):
    - Format tasks
    - Lint tasks
    - Test tasks
    - Docs tasks
    - Pre-commit tasks
    - Combined workflows
    - Help task

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Standard pyproject.toml structure
- Well-organized sections
- Comprehensive configuration

**Migration Strategy**:
1. Template entire pyproject.toml with placeholders
2. Parameterize:
   - Project metadata
   - Dependencies (keep core, customize extras)
   - Tool versions
3. Include all tool configurations
4. Document customization options

---

### 7.2 Version Management

**Tool**: python-semantic-release

**Configuration**: `pyproject.toml` (Lines 286-333)

**Version Sources**:
```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
version_variables = ["katana_public_api_client/__init__.py:__version__"]
```

**Commit Conventions**:
```toml
allowed_tags = ["build", "chore", "ci", "docs", "feat", "fix", "perf", "style", "refactor", "test"]
minor_tags = ["feat"]         # feat → 0.X.0
patch_tags = ["fix", "perf"]  # fix/perf → 0.0.X
```

**Tag Format**: `client-v{version}` (for monorepo)

**Changelog**: `docs/CHANGELOG.md` (auto-generated)

**Process**:
1. Commit with conventional format: `feat(client): add feature`
2. Push to main
3. GitHub Actions runs semantic-release
4. Creates git tag, updates version, generates changelog
5. Builds and publishes to PyPI

**Dependencies**:
- `python-semantic-release>=9.0.0`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Standard semantic versioning
- Conventional commits

**Migration Strategy**:
1. Template semantic-release configuration
2. Parameterize version files
3. Include in release workflow template
4. Document commit conventions
5. Provide CHANGELOG template

---

## 8. Project Structure

### 8.1 Directory Organization

**Root Structure**:
```
katana-openapi-client/           # Repository root (uv workspace)
├── .github/                     # GitHub-specific files
│   ├── workflows/               # CI/CD workflows
│   ├── agents/                  # GitHub Copilot agents
│   ├── instructions/            # Copilot instructions
│   ├── prompts/                 # Copilot prompts
│   ├── ISSUE_TEMPLATE/          # Issue templates
│   ├── copilot-instructions.md  # Main Copilot config
│   ├── pull_request_template.md # PR template
│   └── dependabot.yml           # Dependabot config
├── .devcontainer/               # Dev container config
├── docs/                        # Documentation
│   ├── adr/                     # Architecture Decision Records
│   ├── katana-api-comprehensive/ # API analysis
│   ├── katana-openapi.yaml      # OpenAPI specification
│   ├── *.md                     # User guides
│   └── gen_ref_pages.py         # API doc generation
├── examples/                    # Example code
│   ├── client/                  # Client usage examples
│   └── mcp-server/              # MCP server examples
├── katana_public_api_client/    # Main package (CLIENT)
│   ├── api/                     # Generated API methods (76 modules)
│   ├── models/                  # Generated data models (150+ models)
│   ├── helpers/                 # Domain helper classes
│   ├── domain/                  # Domain models (Pydantic)
│   ├── docs/                    # Package-local docs
│   │   └── adr/                 # Client-specific ADRs
│   ├── client.py                # Generated base client
│   ├── client_types.py          # Generated types
│   ├── errors.py                # Generated errors
│   ├── katana_client.py         # Enhanced client (CUSTOM)
│   ├── log_setup.py             # Logging utilities (CUSTOM)
│   └── __init__.py              # Package exports
├── katana_mcp_server/           # MCP server package (WORKSPACE MEMBER)
│   ├── src/katana_mcp/          # Server implementation
│   ├── tests/                   # MCP tests
│   ├── docs/                    # MCP docs
│   ├── pyproject.toml           # Separate config
│   └── Dockerfile               # Docker image
├── scripts/                     # Development scripts
│   ├── regenerate_client.py     # OpenAPI client generation
│   └── analyze_coverage.py      # Coverage analysis
├── tests/                       # Test suite (MAIN PACKAGE)
│   ├── conftest.py              # Shared fixtures
│   └── test_*.py                # Test modules (17 files)
├── .pre-commit-config.yaml      # Pre-commit hooks
├── .pre-commit-config-lite.yaml # Lite pre-commit (no tests)
├── .yamllint.yml                # YAML linting rules
├── mkdocs.yml                   # MkDocs configuration
├── pyproject.toml               # Workspace + main package config
├── uv.lock                      # Unified lock file
├── README.md                    # Main README
└── LICENSE                      # MIT License
```

**Key Principles**:
1. **Monorepo**: Single repo, multiple packages (workspace)
2. **Flat API structure**: Generated API methods at `api/{resource}/{method}.py`
3. **Separate concerns**: Generated (api/, models/) vs custom (katana_client.py, helpers/)
4. **Module-local docs**: Each package has own docs/ folder
5. **Workspace members**: katana_mcp_server/ is sibling package

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Standard Python package structure
- Well-organized, clear separation

**Migration Strategy**:
1. Template directory structure
2. Document structure in README
3. Provide file organization guide
4. Include in ADR (ADR-013: Module-Local Documentation)

---

### 8.2 Module Layout

**Main Package** (`katana_public_api_client/`):

**Generated Modules** (do NOT modify):
- `api/`: API endpoint functions
  - Organized by resource: `api/product/`, `api/customer/`, etc.
  - Each resource has CRUD methods: `get_all_*.py`, `get_*.py`, `create_*.py`, `update_*.py`, `delete_*.py`
- `models/`: Pydantic data models
  - Request models: `create_*_request.py`, `update_*_request.py`
  - Response models: `*_response.py`
  - Domain models: `product.py`, `customer.py`, etc.
- `client.py`: Base client classes
- `client_types.py`: Type definitions (renamed from `types.py`)
- `errors.py`: Exception classes

**Custom Modules** (safe to modify):
- `katana_client.py`: Enhanced client with resilience
- `log_setup.py`: Logging configuration
- `helpers/`: Domain helper classes
  - `base.py`: Base helper class
  - `products.py`, `materials.py`, `variants.py`, `services.py`, `inventory.py`
- `domain/`: Pydantic domain models
  - `base.py`: Base domain model
  - `product.py`, `material.py`, `variant.py`, `service.py`
  - `converters.py`: Conversion functions
- `docs/`: Package-local documentation
  - `adr/`: Client-specific ADRs
  - `CHANGELOG.md`: Client changelog
  - `*.md`: Client guides
- `__init__.py`: Package exports

**Pattern**: Generated code stays in `api/` and `models/`, custom code in root or `helpers/`/`domain/`

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Clear separation of generated vs custom
- Survives regeneration

**Migration Strategy**:
1. Template module structure
2. Document safe-to-modify vs generated distinction
3. Include regeneration script that preserves custom files
4. Provide migration guide for adding custom logic

---

### 8.3 Code Organization Patterns

**Patterns Observed**:

1. **Transport Layer Composition**:
   - Base → ErrorLogging → Pagination → Retry
   - Each layer wraps the previous
   - Configurable via factory function

2. **Helper Class Pattern**:
   - Base class with `_client` reference
   - Domain-specific methods
   - Lazy initialization via properties

3. **Domain Model Conversion**:
   - Generated attrs models → Domain Pydantic models
   - Converter functions in `domain/converters.py`
   - Bidirectional conversion support

4. **Credential Resolution Chain**:
   - Try multiple sources in priority order
   - Fail fast with clear error message
   - Support for standard credential files

5. **Test Organization**:
   - `conftest.py` for shared fixtures
   - `test_{feature}.py` for feature tests
   - Integration tests marked with `@pytest.mark.integration`

6. **Documentation Structure**:
   - Root docs/ for project-level docs
   - Package-local docs/ for package-specific docs
   - ADRs organized by scope

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Well-established patterns
- Clear conventions

**Migration Strategy**:
1. Document all patterns in Architecture Guide
2. Provide code examples for each pattern
3. Include in template README
4. Create ADRs for key patterns

---

### 8.4 Separation of Concerns

**Separation Strategy**:

1. **Generated vs Custom**:
   - Generated: `api/`, `models/`, `client.py`, `client_types.py`, `errors.py`
   - Custom: `katana_client.py`, `helpers/`, `domain/`, `log_setup.py`
   - Clear boundary, documented

2. **Transport Layers**:
   - HTTP transport: Network communication
   - Error logging: Observability
   - Pagination: Response aggregation
   - Retry: Resilience
   - Each layer has single responsibility

3. **Client Responsibilities**:
   - Base Client: HTTP lifecycle, configuration
   - Authenticated Client: Authentication
   - Katana Client: Resilience, helpers, credentials

4. **Helper Classes**:
   - Products: Product CRUD + search
   - Materials: Material CRUD
   - Variants: Variant CRUD
   - Services: Service CRUD
   - Inventory: Stock operations
   - Each helper owns one domain

5. **Testing Layers**:
   - Unit: Test single components in isolation
   - Integration: Test against real API
   - Slow: Performance/comprehensive tests
   - Docs: Documentation tests (CI-only)

**Reusability**: ⭐⭐⭐⭐⭐ VERY HIGH
- Clean architecture
- SOLID principles

**Migration Strategy**:
1. Document separation boundaries
2. Provide architecture diagram
3. Include in ADR (ADR-001: Transport-Layer Resilience)
4. Create contribution guide section on boundaries

---

## Summary & Migration Priorities

### Extraction Priority for `openapi-client-core`

**Priority 1 (Must Have)** ⭐⭐⭐⭐⭐:
1. Transport layers (retry, pagination, error logging)
2. Credential resolution
3. Base client pattern
4. Test fixtures and helpers

**Priority 2 (Should Have)** ⭐⭐⭐⭐:
5. Event hooks pattern
6. Logging utilities
7. Helper class base pattern
8. pytest configuration

**Priority 3 (Nice to Have)** ⭐⭐⭐:
9. Domain model pattern (optional, API-specific)
10. MCP server pattern (optional, use case specific)

### Template Improvements

**High Priority**:
1. **CI/CD workflows**: All 4 workflows (ci.yml, release.yml, docs.yml, security.yml)
2. **Pre-commit hooks**: Both full and lite versions
3. **pyproject.toml**: Complete with all tool configurations
4. **README template**: Comprehensive structure with placeholders
5. **MkDocs setup**: Documentation generation
6. **Test structure**: conftest.py with fixtures

**Medium Priority**:
7. **Agent configurations**: GitHub Copilot agents and guides
8. **ADR templates**: Architecture Decision Record structure
9. **Issue/PR templates**: GitHub templates
10. **Example code**: Template examples for common patterns

**Low Priority**:
11. **MCP server setup**: Optional, for specific use cases
12. **Custom prompts**: GitHub Copilot prompts

---

## Appendix: Key Files Reference

### Most Valuable Files for Extraction

1. `katana_client.py` (Lines 36-986): Transport layers, enhanced client
2. `conftest.py`: Test fixtures and helpers
3. `.github/workflows/ci.yml`: Modern CI/CD with UV
4. `.github/workflows/release.yml`: Semantic release automation
5. `.github/workflows/security.yml`: Security scanning
6. `pyproject.toml`: Comprehensive tool configuration
7. `.pre-commit-config.yaml`: Pre-commit hooks
8. `mkdocs.yml`: Documentation generation
9. `README.md`: README structure
10. `.github/copilot-instructions.md`: Agent configuration

### Dependencies Summary

**Core Runtime**:
- httpx>=0.28.0
- attrs>=22.2.0
- python-dateutil>=2.8.0
- tenacity>=9.0.0
- python-dotenv>=1.0.0
- pydantic>=2,<3
- httpx-retries>=0.4.3,<0.5.0

**Development**:
- pytest family (pytest, pytest-asyncio, pytest-cov, pytest-mock, pytest-timeout, pytest-xdist)
- ruff>=0.12.4,<0.13
- ty>=0.0.1a25
- pre-commit>=4.2.0
- poethepoet>=0.37.0

**Documentation**:
- mkdocs>=1.6.0
- mkdocs-material>=9.5.0
- mkdocstrings[python]>=0.25.0
- mkdocs-gen-files, mkdocs-literate-nav, mkdocs-swagger-ui-tag

**Release**:
- python-semantic-release>=9.0.0

---

**End of Katana Inventory**

This inventory provides a complete picture of all reusable patterns and infrastructure in the katana repository. Use this as the foundation for extracting `openapi-client-core` and improving `openapi-client-template`.
