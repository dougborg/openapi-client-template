# Publishing openapi-client-core

This guide explains how to publish `openapi-client-core` to PyPI.

## Prerequisites

1. **PyPI Account**: Create accounts on [TestPyPI](https://test.pypi.org/) and [PyPI](https://pypi.org/)
2. **Trusted Publishing**: Set up trusted publishing for automated releases (recommended)
   - Go to PyPI project settings → API tokens → Add trusted publisher
   - Add GitHub Actions workflow: `dougborg/openapi-client-template/.github/workflows/publish-core.yml`
   - Do the same for TestPyPI

## Publishing Process

### Option 1: Automated Publishing (Recommended)

#### Via GitHub Release

1. Update version in `pyproject.toml` and `src/openapi_client_core/__init__.py`
2. Update `CHANGELOG.md` with release date
3. Commit and push changes
4. Create a GitHub release:
   ```bash
   gh release create v0.1.0 --title "v0.1.0" --notes "Initial release"
   ```
5. The workflow will automatically publish to PyPI

#### Via Workflow Dispatch

1. Go to Actions → Publish openapi-client-core → Run workflow
2. Enter version (e.g., `0.1.0`)
3. Choose publish target: `testpypi`, `pypi`, or `both`
4. Run the workflow

### Option 2: Manual Publishing

#### Test TestPyPI First

```bash
cd openapi-client-core

# Build the package
uv build

# Publish to TestPyPI (requires API token)
uv publish --publish-url https://test.pypi.org/legacy/ dist/*

# Test installation from TestPyPI
uv pip install --index-url https://test.pypi.org/simple/ openapi-client-core
```

#### Publish to PyPI

Once verified on TestPyPI:

```bash
# Publish to PyPI
uv publish dist/*

# Or using twine (if installed)
twine upload dist/*
```

## Version Management

- Follow [Semantic Versioning](https://semver.org/)
- Update version in:
  - `pyproject.toml` (`version = "0.1.0"`)
  - `src/openapi_client_core/__init__.py` (`__version__ = "0.1.0"`)
  - `CHANGELOG.md` (add new version section)

## Verification

After publishing, verify the package:

```bash
# Install from PyPI
uv pip install openapi-client-core

# Test import
python -c "import openapi_client_core; print(openapi_client_core.__version__)"

# Run a quick test
python -c "from openapi_client_core.auth import CredentialResolver; print('OK')"
```

## Troubleshooting

- **Authentication errors**: Ensure PyPI API tokens are set up correctly
- **Version conflicts**: Check if version already exists on PyPI
- **Build errors**: Run `uv run poe check` to verify all tests pass first
- **Trusted publishing**: Verify workflow has `id-token: write` permission

