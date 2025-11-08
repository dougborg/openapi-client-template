# Contributing to openapi-client-template

Thank you for your interest in contributing! This document provides guidelines for contributing to the template repository.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/openapi-client-template.git`
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Install dependencies: `pip install copier`

## Development Workflow

### Testing the Template

To test the template locally:

```bash
# Generate a test project from the template
copier copy . /tmp/test-project

# Or test with specific variables
copier copy . /tmp/test-project \
  --data project_name="Test Client" \
  --data project_slug="test-client" \
  --data package_name="test_client"
```

### Testing Template Updates

If you have an existing project created from the template:

```bash
# Update the project with template changes
python scripts/sync-template.py /path/to/existing-project --trust
```

## Making Changes

### Template Structure

- `template/{{project_slug}}/`: The Copier template that gets expanded into client projects
- `shared-libs/`: Shared Python packages referenced by generated clients
- `scripts/`: Helper scripts for template management
- `.github/workflows/`: CI workflows for the template repository

### Copier Variables

When adding new variables to `copier.json`, consider:
- Providing sensible defaults
- Documenting the variable in the README
- Testing with both default and custom values

### Jinja2 Templates

Template files use `.jinja` extension and can reference variables from `copier.json`:
- Use `{{ variable_name }}` for substitution
- Use `{% if condition %}...{% endif %}` for conditional sections
- Use `{% for item in list %}...{% endfor %}` for loops

## Code Style

- Follow PEP 8 for Python code
- Use consistent formatting in Jinja templates
- Keep generated projects clean and minimal

## Testing

Before submitting a PR:

1. Test template generation with default values
2. Test template generation with custom values
3. Test template updates on an existing project
4. Run any existing CI checks

## Submitting Changes

1. Commit your changes with clear, descriptive messages
2. Push to your fork
3. Open a Pull Request with:
   - Clear description of changes
   - Context on why the change is needed
   - Any testing you've performed

## Release Process

The template uses semantic versioning (v0.0.1, v1.0.0, etc.):
- **Major**: Breaking changes to template structure or required variables
- **Minor**: New features, new template files, new optional variables
- **Patch**: Bug fixes, documentation updates, minor improvements

Releases are tagged and tracked in `CHANGELOG.md`.

## Questions?

Feel free to open an issue for questions or discussions about potential contributions.
