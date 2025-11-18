# Release Checklist for openapi-client-core v0.1.0

## Pre-Release Checks

- [ ] All tests pass: `uv run pytest`
- [ ] Code coverage ≥ 80%: `uv run pytest --cov=openapi_client_core --cov-report=term-missing`
- [ ] Linting passes: `uv run ruff check .`
- [ ] Formatting is correct: `uv run ruff format --check .`
- [ ] Package builds successfully: `uv build`
- [ ] All imports work: Test all public API imports
- [ ] README is up to date
- [ ] CHANGELOG.md is updated with release date
- [ ] Version numbers are consistent:
  - [ ] `pyproject.toml`: `version = "0.1.0"`
  - [ ] `src/openapi_client_core/__init__.py`: `__version__ = "0.1.0"`

## Publishing Steps

### Step 1: TestPyPI (Recommended First)

1. [ ] Build package: `uv build`
2. [ ] Publish to TestPyPI: `uv publish --publish-url https://test.pypi.org/legacy/ dist/*`
   - You'll need a TestPyPI API token
3. [ ] Test installation from TestPyPI:
   ```bash
   uv pip install --index-url https://test.pypi.org/simple/ openapi-client-core
   ```
4. [ ] Verify package works:
   ```python
   import openapi_client_core
   from openapi_client_core.auth import CredentialResolver
   from openapi_client_core.transport.retry import IdempotentOnlyRetry
   print(f"Version: {openapi_client_core.__version__}")
   ```

### Step 2: PyPI (After TestPyPI Verification)

1. [ ] Publish to PyPI: `uv publish dist/*`
   - You'll need a PyPI API token
2. [ ] Verify on PyPI: https://pypi.org/project/openapi-client-core/
3. [ ] Test installation from PyPI:
   ```bash
   uv pip install openapi-client-core
   ```
4. [ ] Create GitHub release tag: `v0.1.0`

## Post-Release

- [ ] Update issue #2 with completion status
- [ ] Announce release (if applicable)
- [ ] Update any downstream projects to use the published package

## Troubleshooting

- **"Package already exists"**: Version already published, increment version
- **"Authentication failed"**: Check API token is correct
- **"Build failed"**: Run `uv run poe check` to find issues

