# Repository Inventories

This directory contains comprehensive inventories of existing OpenAPI client repositories. These inventories document all reusable patterns, infrastructure, and features that should be considered for extraction into the `openapi-client-core` library and/or inclusion in the template.

## Purpose

The inventories serve multiple purposes:

1. **Foundation for Core Extraction**: Identify which features should be extracted into the shared `openapi-client-core` runtime library
2. **Template Enhancement**: Identify patterns and infrastructure that should be included in the template for all generated clients
3. **Documentation**: Preserve knowledge about implementation patterns and design decisions
4. **Migration Planning**: Provide detailed migration strategies for transitioning existing clients

## Available Inventories

### [Katana Inventory](katana-inventory.md)

Comprehensive inventory of the `katana-openapi-client` repository.

**Key Findings:**
- ⭐⭐⭐⭐⭐ OpenAPI client logic (retry, pagination, auth, error handling)
- ⭐⭐⭐⭐⭐ Testing infrastructure (fixtures, patterns, coverage)
- ⭐⭐⭐⭐⭐ CI/CD infrastructure (4 workflows, automation)
- ⭐⭐⭐⭐ Agent configurations (7 specialized agents)
- ⭐⭐⭐⭐ Documentation generation (MkDocs Material)
- ⭐⭐⭐⭐ Build & packaging (semantic versioning)

**Status**: ✅ Complete (Issue #10)

### [StockTrim Inventory](stocktrim-inventory.md)

Comprehensive inventory of the `stocktrim-api-client` repository.

**Key Findings:**
- ⭐⭐⭐⭐⭐ OpenAPI client logic (null detection, idempotent retry, custom auth)
- ⭐⭐⭐⭐⭐ Code generation (1066-line regeneration script with nullable fixes)
- ⭐⭐⭐⭐⭐ CI/CD infrastructure (5 workflows, monorepo release coordination)
- ⭐⭐⭐⭐⭐ Project automation (poethepoet task runner, UV workspace)
- ⭐⭐⭐⭐⭐ Testing infrastructure (26 tests, comprehensive fixtures)
- ⭐⭐⭐⭐ Helper pattern (10+ domain helpers, 50+ convenience methods)
- ⭐⭐⭐⭐ Documentation (MkDocs Material, 20+ markdown files)
- ⭐⭐⭐ Agent configurations (MCP server, observability patterns)

**Unique Innovations:**
- Transport-level null field detection
- Idempotent-only retry strategy
- Post-generation spec fixing
- Dual-package monorepo with coordinated releases

**Status**: ✅ Complete (Issue #8)

## How to Use These Inventories

### For Core Library Extraction

When extracting `openapi-client-core`:

1. Review the **OpenAPI Client Logic** sections in each inventory
2. Compare implementations across repositories to identify common patterns
3. Design abstractions that work for all clients
4. Use the **Migration Strategies** to plan the extraction
5. Reference the **Code Snippets** for implementation details

Priority extraction candidates:
- Transport layer architecture (retry, pagination, error handling)
- Rate limiting implementations
- Authentication patterns
- Error translation mechanisms

### For Template Enhancement

When improving the template:

1. Review **CI/CD Infrastructure**, **Project Automation**, and **Documentation** sections
2. Identify patterns that should be standardized across all clients
3. Add these patterns to the `template/` directory
4. Update copier questions if new configuration is needed

Priority template additions:
- Agent configurations and guides
- Enhanced testing infrastructure
- Semantic versioning automation
- Documentation generation setup

### For Client Migration

When migrating an existing client to use the template:

1. Review the inventory for that specific repository
2. Follow the migration strategies provided
3. Ensure all existing features are preserved
4. Use the inventory as a checklist during migration

## Inventory Structure

Each inventory document follows this structure:

1. **Executive Summary**: Overview, statistics, key findings
2. **Category Sections**: Detailed analysis of each major category
   - File locations with line numbers
   - Code snippets and examples
   - Reusability assessment (⭐ ratings)
   - Migration strategies
   - Implementation notes
3. **Appendices**: Additional technical details

## Reusability Ratings

Inventories use a 5-star rating system:

- ⭐⭐⭐⭐⭐ **Critical** - Must extract to core or include in template
- ⭐⭐⭐⭐ **High** - Should extract/include, high value
- ⭐⭐⭐ **Medium** - Consider for extraction/inclusion
- ⭐⭐ **Low** - Keep as reference, may not extract
- ⭐ **Reference Only** - Document for knowledge, unlikely to extract

## Related Issues

- [#2 - Extract and publish openapi-client-core](https://github.com/dougborg/openapi-client-template/issues/2)
- [#8 - Inventory stocktrim repository](https://github.com/dougborg/openapi-client-template/issues/8) ✅
- [#9 - Analyze inventories and create extraction plan](https://github.com/dougborg/openapi-client-template/issues/9)
- [#10 - Inventory katana repository](https://github.com/dougborg/openapi-client-template/issues/10) ✅

## Next Steps

1. ✅ Complete katana inventory (Issue #10)
2. ✅ Complete stocktrim inventory (Issue #8)
3. 🔄 Analyze both inventories and compare patterns (Issue #9)
4. 🚀 Extract openapi-client-core library (Issue #2)
5. 🔄 Implement template sync workflow (Issue #3)
6. 🎯 Migrate existing clients to template (Issue #4)

## Contributing

When creating new inventories:

1. Use the katana inventory as a template for structure
2. Include file locations with line numbers (e.g., `src/client.py:42-56`)
3. Provide code snippets for important patterns
4. Assess reusability with ⭐ ratings
5. Include migration strategies
6. Update this README with the new inventory

## Questions?

If you have questions about the inventories or need clarification on any patterns, please open an issue with the `documentation` label.
