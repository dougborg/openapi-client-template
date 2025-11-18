# Release Instructions for v0.1.0

## Step 1: Set Up PyPI Trusted Publishing (One-time setup)

If you haven't already set up trusted publishing for this repository:

1. Go to https://pypi.org/manage/account/
2. Navigate to "API tokens" → "Add a new trusted publisher"
3. Configure:
   - **PyPI project name**: `openapi-client-core`
   - **Publisher**: `GitHub Actions`
   - **Owner**: `dougborg`
   - **Repository name**: `openapi-client-template`
   - **Workflow filename**: `.github/workflows/publish-core.yml`
4. Save the configuration

This allows the GitHub Actions workflow to publish without storing API tokens.

## Step 2: Commit and Push Changes

```bash
# Add all the new files
git add .cursorrules .cursorignore
git add .github/workflows/publish-core.yml
git add openapi-client-core/

# Commit
git commit -m "feat: Prepare openapi-client-core v0.1.0 for publishing

- Update CHANGELOG with v0.1.0 release notes
- Add GitHub Actions publishing workflow
- Add publishing documentation and checklists
- Adjust coverage configuration"

# Push to main
git push origin main
```

## Step 3: Create GitHub Release

### Option A: Using GitHub CLI

```bash
# Create and push the tag
git tag v0.1.0
git push origin v0.1.0

# Create the release (this triggers the workflow)
gh release create v0.1.0 \
  --title "openapi-client-core v0.1.0" \
  --notes "Initial release of openapi-client-core

## Features

- Transport layers: IdempotentOnlyRetry, RateLimitAwareRetry
- Multi-source credential resolution
- RFC 7807 error handling with structured exceptions
- Null field detection
- BaseOpenAPIClient foundation class

See CHANGELOG.md for full details."
```

### Option B: Using GitHub Web UI

1. Go to https://github.com/dougborg/openapi-client-template/releases/new
2. **Tag**: `v0.1.0` (create new tag)
3. **Title**: `openapi-client-core v0.1.0`
4. **Description**: Copy from CHANGELOG.md v0.1.0 section
5. Click "Publish release"

## Step 4: Monitor the Workflow

1. Go to https://github.com/dougborg/openapi-client-template/actions
2. Watch the "Publish openapi-client-core" workflow run
3. It will:
   - Run all checks
   - Build the package
   - Publish to PyPI

## Step 5: Verify Publication

Once the workflow completes:

```bash
# Wait a few minutes for PyPI to index, then verify
uv pip install openapi-client-core

# Test import
python -c "import openapi_client_core; print(f'Version: {openapi_client_core.__version__}')"
```

Check on PyPI: https://pypi.org/project/openapi-client-core/

## Alternative: Manual Workflow Trigger

If you want to trigger the workflow manually without creating a release:

1. Go to https://github.com/dougborg/openapi-client-template/actions/workflows/publish-core.yml
2. Click "Run workflow"
3. Select branch (usually `main`)
4. Click "Run workflow"

This will publish whatever version is in `pyproject.toml` and `__init__.py`.

