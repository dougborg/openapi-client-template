# Workspace Setup Guide

This document explains how to set up and use the multi-project workspace for the OpenAPI client template ecosystem.

## Workspace Overview

The workspace typically includes the following related projects:

1. **Template** (`openapi-client-template/`) - The Copier template repository
2. **Generated client projects** (e.g., `katana-openapi-client/`, `stocktrim-openapi-client/`) - Example generated clients for specific APIs. Your workspace may include different generated clients depending on your use case.

## Opening the Workspace

### VS Code / Cursor

1. Open the workspace file from the `Projects/` directory:
   ```bash
   cd ~/Projects
   code openapi-clients-workspace.code-workspace
   ```

2. The workspace will load all three projects as separate folders in the sidebar.

### Workspace Features

The workspace configuration provides:

- **Multi-root workspace** - All three projects accessible in one window
- **Shared settings** - Consistent Python, linting, and formatting settings
- **Cross-project tasks** - Run commands across all projects simultaneously
- **Extension recommendations** - Auto-suggests useful extensions
- **Debug configurations** - Pre-configured Python debugging
- **File exclusions** - Hides build artifacts and cache files

## Workspace Settings

### File Exclusions

The workspace automatically hides:
- Python cache files (`__pycache__`, `*.pyc`)
- Build artifacts (`dist/`, `build/`, `*.egg-info`)
- Test coverage reports (`htmlcov/`, `.coverage`)
- Type checking caches (`.mypy_cache`, `.ruff_cache`)
- Documentation builds (`site/`, `docs/_build`)

### Python Settings

- **Type checking**: Strict mode enabled
- **Formatting**: Ruff with format-on-save
- **Import organization**: Auto-organize on save
- **Testing**: Pytest with auto-discovery

### Editor Settings

- **Format on save**: Enabled for Python, YAML, Markdown
- **Organize imports**: Auto-organize on save
- **Line endings**: Unix (`\n`)
- **Encoding**: UTF-8

## Workspace Tasks

Access tasks via `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux) → "Tasks: Run Task"

### Individual Project Tasks

- **Template: Check Quality** - Run `uv run poe check` in template
- **Template: Run Tests** - Run tests in template
- **Katana: Check Quality** - Run `uv run poe check` in Katana client
- **Katana: Run Tests** - Run tests in Katana client
- **StockTrim: Check Quality** - Run `uv run poe check` in StockTrim client
- **StockTrim: Run Tests** - Run tests in StockTrim client

### Cross-Project Tasks

- **All Projects: Check Quality** - Run quality checks in all projects in parallel
- **All Projects: Run Tests** - Run tests in all projects in parallel

### Template Sync Tasks

- **Template: Sync to Katana** - Sync template changes to Katana client
- **Template: Sync to StockTrim** - Sync template changes to StockTrim client

## Recommended Extensions

The workspace recommends these extensions (auto-suggested when opening):

### Essential

- **Python** (`ms-python.python`) - Python language support
- **Ruff** (`charliermarsh.ruff`) - Fast Python linter and formatter
- **MyPy Type Checker** (`ms-python.mypy-type-checker`) - Type checking
- **Pylance** (`ms-python.vscode-pylance`) - Python language server

### YAML & Templates

- **YAML** (`redhat.vscode-yaml`) - YAML language support
- **Jinja** (`wholroyd.jinja`) - Jinja2 template syntax highlighting

### Development Tools

- **GitHub Copilot** (`github.copilot`) - AI code completion
- **GitHub Copilot Chat** (`github.copilot-chat`) - AI chat assistant
- **Jupyter** (`ms-toolsai.jupyter`) - Jupyter notebook support
- **Prettier** (`esbenp.prettier-vscode`) - Markdown formatting

## Debug Configurations

Pre-configured debug configurations:

- **Python: Current File** - Debug the currently open Python file
- **Python: Pytest Current File** - Debug tests in the current file
- **Python: Pytest All Tests** - Debug all tests in the workspace

Access via Run and Debug panel (`Cmd+Shift+D` / `Ctrl+Shift+D`).

## Project Relationships

### Template → Generated Clients

The template repository is the source of truth. Changes to the template can be synced to generated clients using:

1. **Manual sync** (from template directory):
   ```bash
   python scripts/sync-template.py ../katana-openapi-client --trust
   ```
   > **Note:** The above command assumes that the template and client repositories are siblings (i.e., both are in the same parent directory). If your project layout differs, adjust the path accordingly. See [Alternative Workspace Locations](#alternative-workspace-locations) below for more details.

2. **Workspace task**: Use "Template: Sync to Katana" or "Template: Sync to StockTrim"

3. **Copier update** (from client directory):
   ```bash
   cd ../katana-openapi-client
   uvx copier update --trust
   ```

### Shared Library

The `openapi-client-core/` package in the template repository provides shared functionality used by generated clients. When developing the core library:

1. Make changes in `openapi-client-core/`
2. Test locally in the template repository
3. Publish to PyPI when ready
4. Update client projects to use the new version

## Best Practices

### Working Across Projects

1. **Use workspace tasks** for running commands across projects
2. **Check all projects** before committing template changes
3. **Sync template changes** to clients after testing in template
4. **Use relative paths** in workspace configuration for portability

### Development Workflow

1. **Template changes**: Make changes → Test → Sync to clients
2. **Client changes**: Make changes → Test → Commit
3. **Core library changes**: Make changes → Test → Publish → Update clients

### File Organization

- Keep workspace file in template repository (source of truth)
- Use relative paths for portability
- Document any workspace-specific settings

## Troubleshooting

### Projects Not Loading

If projects don't load correctly:

1. Check that all project paths exist
2. Verify relative paths are correct from workspace file location
3. Try using absolute paths if relative paths fail

### Tasks Not Working

If tasks fail:

1. Ensure `uv` is installed and in PATH
2. Check that each project has `pyproject.toml` with poe tasks
3. Verify you're in the correct directory when running tasks

### Extension Issues

If extensions don't work:

1. Install recommended extensions manually
2. Reload window after installing extensions
3. Check extension settings in workspace settings

## Workspace File Location

The workspace file is located at:

```
~/Projects/openapi-clients-workspace.code-workspace
```

This location allows the workspace to use relative paths to all three projects, assuming they're siblings in the `Projects/` directory. The workspace file is at the same level as the projects it references, making it easy to access and maintain.

## Alternative Workspace Locations

You can create workspace files in other locations if needed:

- **Client directories** - For client-specific workspaces (e.g., `stocktrim-openapi-client/api-clients-workspace.code-workspace`)
- **Template directory** - For template-only development (not recommended for multi-project work)

The parent directory workspace file (`~/Projects/openapi-clients-workspace.code-workspace`) is the recommended primary workspace for multi-project development.

