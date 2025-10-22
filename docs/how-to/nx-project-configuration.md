# NX Project Configuration

## Overview

This document explains how NX project configuration works in this monorepo and documents fixes applied to resolve project graph errors.

## Project Structure

NX discovers projects in two ways:

1. **Inline project definitions** in `workspace.json` - projects can be defined as a string path to a directory containing `project.json`
2. **Standalone `project.json` files** - projects can have their configuration in a `project.json` file at the project root

## Common Issues and Fixes

### Issue: Top-level `targets` in workspace.json

**Problem:** The `workspace.json` file had a top-level `targets` key that was not associated with any project:

```json
{
  "version": 2,
  "projects": {
    "env-check": "apps/env-check"
  },
  "targets": {
    "logging": {
      "executor": "./tools/tasks/logging-check.js",
      "outputs": [],
      "options": {}
    }
  }
}
```

This caused NX to fail when building the project graph because:
- In workspace.json version 2, `targets` must be defined inside a project
- Top-level `targets` are not valid and cause NX to misinterpret the workspace structure

**Solution:** Create a proper project for the logging tooling:

1. Update `workspace.json` to map `logging` to the `tools` directory:

```json
{
  "version": 2,
  "projects": {
    "env-check": "apps/env-check",
    "logging": "tools"
  }
}
```

2. Create `tools/project.json` with the project configuration:

```json
{
  "$schema": "../node_modules/nx/schemas/project-schema.json",
  "name": "logging",
  "root": "tools",
  "sourceRoot": "tools",
  "projectType": "application",
  "targets": {
    "check": {
      "executor": "nx:run-commands",
      "options": {
        "command": "node tools/tasks/logging-check.js"
      },
      "outputs": []
    }
  },
  "tags": ["type:tooling"]
}
```

### Issue: Missing `.nx/package.json`

**Problem:** NX uses the `.nx` directory for internal caching and workspace data. Some NX commands (like `nx graph`) internally run npm commands in the `.nx` directory, which requires a `package.json` file. When this file was missing, commands failed with:

```
npm error enoent Could not read package.json: Error: ENOENT: no such file or directory, open '/home/prime/homelab/.nx/package.json'
```

**Solution:** Create a minimal `package.json` in the `.nx` directory:

```json
{
  "name": "homelab-nx-internal",
  "private": true,
  "version": "0.0.0"
}
```

This file should be committed to the repository as it's required for NX's internal operations.

## Verification

After applying these fixes, verify the configuration with:

```bash
# List all projects
npx nx show projects

# Generate and view the project graph
npx nx graph

# Run a project target
npx nx run logging:check
```

## Best Practices

1. **Use `project.json` for projects** - Rather than inline definitions in `workspace.json`, create standalone `project.json` files for better organization and IDE support.

2. **Keep targets inside projects** - Never define targets at the top level of `workspace.json`; they must be inside a project definition.

3. **Use `nx:run-commands` for scripts** - When running Node.js scripts or shell commands as NX targets, use the `nx:run-commands` executor.

4. **Tag projects appropriately** - Use tags like `type:utility`, `type:tooling`, `type:application` to categorize projects for better filtering and dependency rules.

## Related Documentation

- [NX Workspace Configuration](https://nx.dev/reference/project-configuration)
- [NX Project.json Schema](https://nx.dev/reference/project-configuration#projectjson)
- [Environment Setup](./setup-environment.md)
