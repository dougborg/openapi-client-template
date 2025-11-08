# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial template structure with Copier support
- Basic project skeleton (pyproject.toml, src/, tests/)
- Shared library placeholder for openapi-client-core
- Template sync script for updating existing projects
- CI workflow for template repository
- LICENSE (MIT), CODE_OF_CONDUCT.md, and CONTRIBUTING.md
- This CHANGELOG

## [0.0.1] - 2025-11-08

### Added
- Initial release of openapi-client-template
- Copier-based template for Python OpenAPI clients
- Basic template files: README, pyproject.toml, __init__.py, smoke test
- Template variables: project_name, project_slug, package_name, api_service, include_mcp, author_name, license, python_version
- Scripts for template synchronization
- GitHub Actions CI workflow

[Unreleased]: https://github.com/dougborg/openapi-client-template/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/dougborg/openapi-client-template/releases/tag/v0.0.1
