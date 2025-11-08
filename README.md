# openapi-client-template

A [Copier](https://copier.readthedocs.io/)-based template for bootstrapping consistent, production-ready Python OpenAPI client projects.

## Purpose

This template provides:
- **Reproducible project structure** for Python OpenAPI clients with modern PEP 621 packaging
- **Shared runtime libraries** (openapi-client-core) for common concerns like retries, rate limiting, and pagination
- **Easy template updates** using copier to keep multiple client repositories in sync
- **Standard CI/CD workflows** to ensure quality and consistency across all generated clients
- **Optional features** like MCP (Model Context Protocol) support and CLI interfaces

## Quick Start

### Creating a New Project

1. Install Copier:
   ```bash
   pip install copier
   ```

2. Generate a new client project:
   ```bash
   copier copy gh:dougborg/openapi-client-template my-api-client
   ```

3. Follow the interactive prompts to configure your project, or provide values directly:
   ```bash
   copier copy gh:dougborg/openapi-client-template my-api-client \
     --data project_name="My API Client" \
     --data api_service="myservice" \
     --data include_mcp=true
   ```

### Updating an Existing Project

To pull in the latest template changes to an existing project created from this template:

1. Navigate to your client project directory
2. Run:
   ```bash
   copier update --trust
   ```

Or use the provided sync script from the template repository:
```bash
python scripts/sync-template.py /path/to/your-client-project --trust
```

## Template Structure

- **template/**: The Copier template that is expanded into each new client repo
  - Generated projects include: pyproject.toml, src/, tests/, docs/, CI workflows, and configuration files
- **shared-libs/**: Shared Python packages for reusable code (e.g., openapi-client-core)
- **scripts/**: Helper scripts for template synchronization and release management
- **.github/**: CI workflows for template repository maintenance

## Versioning Philosophy

This template follows [Semantic Versioning](https://semver.org/):

- **Major versions** (e.g., 2.0.0): Breaking changes to template structure, required variable changes, or major feature removals
- **Minor versions** (e.g., 1.1.0): New features, new template files, new optional variables, or significant enhancements
- **Patch versions** (e.g., 1.0.1): Bug fixes, documentation improvements, or minor template refinements

When you update your project using `copier update`, you can choose which version to pull from. See [CHANGELOG.md](CHANGELOG.md) for version history.

## Configuration Variables

The template supports the following configuration variables (defined in `copier.json`):

- `project_name`: Human-readable project name (e.g., "My OpenAPI Client")
- `project_slug`: URL/package-friendly name (e.g., "my-openapi-client")
- `package_name`: Python package name (e.g., "my_openapi_client")
- `api_service`: Name of the API service being wrapped
- `include_mcp`: Include Model Context Protocol support (true/false)
- `author_name`: Project author/maintainer name
- `license`: License type (default: MIT)
- `python_version`: Minimum Python version (e.g., "3.11")

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Testing the template locally
- Making changes to template files
- Submitting pull requests
- Release process

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

## License

This template is released under the [MIT License](LICENSE). Projects generated from this template will include their own MIT license by default (configurable via the `license` variable).

## Roadmap

See open issues and project boards for planned enhancements and feature requests.