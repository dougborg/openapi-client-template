# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Pagination transport layer
- Event hooks system
- Additional testing utilities and fixtures

## [0.1.0] - 2025-11-18

### Added

- **Transport Layers**:
  - `IdempotentOnlyRetry`: Retry transport that only retries safe HTTP methods (GET, HEAD, OPTIONS) on 5xx errors
  - `RateLimitAwareRetry`: Retry transport that handles HTTP 429 (rate limiting) with Retry-After header support and exponential backoff
  - Configurable retry strategies with max retries and backoff parameters

- **Authentication**:
  - `CredentialResolver`: Multi-source credential resolution system
  - Supports resolution from: explicit values, environment variables, .env files, and file-based credentials
  - Thread-safe dotenv loading
  - Credential masking in logs for security

- **Error Handling**:
  - RFC 7807 Problem Details parsing and translation
  - Structured exception hierarchy (`APIError`, `ClientError`, `ServerError`, etc.)
  - Status code-specific exceptions (`NotFoundError`, `ValidationError`, `RateLimitError`, etc.)
  - Null field detection in API responses
  - `raise_for_status()` helper function

- **Base Client**:
  - `BaseOpenAPIClient`: Foundation class for OpenAPI client implementations

- **Testing Infrastructure**:
  - Comprehensive test suite with 64+ passing tests
  - pytest configuration with markers (unit, integration, slow)
  - Coverage tracking with 80% threshold

- **Documentation**:
  - Comprehensive README with usage examples
  - API documentation
  - Code examples for all major features

- **Project Configuration**:
  - Modern Python packaging with Hatchling
  - UV-based dependency management
  - Ruff for linting and formatting
  - CI/CD workflows for testing

[Unreleased]: https://github.com/dougborg/openapi-client-core/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dougborg/openapi-client-core/releases/tag/v0.1.0
