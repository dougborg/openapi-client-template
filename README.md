# openapi-client-template

This repository contains a Copier-based template and supporting scripts/libraries to bootstrap consistent OpenAPI client projects.

Goals
- Provide a reproducible project skeleton for Python OpenAPI clients (pyproject, tests, docs, CI).
- Extract and reference shared runtime libraries (openapi-client-core, mcp-base).
- Make it easy to update multiple existing client repositories from a central template using `copier` and CI.

Quick start
1. Create a new project from this template:
   pip install copier
   copier copy gh:dougborg/openapi-client-template

2. Update an existing project to pick up template changes:
   copier update --trust

Contents
- template/: the Copier template that is expanded into each new client repo
- shared-libs/: example shared packages to extract reusable code
- scripts/: helper scripts (sync, release helpers)
- .github/: workflows for template maintenance

See the `ROADMAP.md` in the repo for initial planned tasks.