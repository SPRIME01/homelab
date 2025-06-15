# Development Workflow Documentation

## Overview

This document outlines the development workflow for the Smart Home K3s Laboratory project, emphasizing modern Python development practices with UV package management, proper testing environments, and infrastructure-as-code principles.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Environment Setup](#development-environment-setup)
- [Package Management with UV](#package-management-with-uv)
- [Testing Strategy](#testing-strategy)
- [Code Quality Standards](#code-quality-standards)
- [Available Make Targets](#available-make-targets)
- [Continuous Integration](#continuous-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

Get up and running in 60 seconds:

```bash
# 1. Set up development environment
make dev-install

# 2. Validate everything works
make pre-commit

# 3. Run tests
make test

# 4. Check code quality
make lint
```

## Development Environment Setup

### Prerequisites

- **Python 3.12+**: Required for modern type hints and performance improvements
- **UV Package Manager**: Fast Python package and project manager
- **Git**: Version control with pre-commit hooks
- **Make**: Build automation (typically available on WSL2/Linux)

### Initial Setup

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd homelab
   ```

2. **Install UV** (if not already installed):

   ```bash
   # On Windows (PowerShell)
   pip install uv

   # Or via the Makefile (will auto-install if missing)
   make check-uv
   ```

3. **Set up development environment**:

   ```bash
   # Install all dependencies and setup pre-commit hooks
   make dev-install
   ```

4. **Verify installation**:

   ```bash
   # Run comprehensive validation
   make pre-commit
   ```

## Package Management with UV

### Why UV?

UV provides significant advantages over traditional pip/virtualenv workflows:

- **Speed**: 10-100x faster than pip for dependency resolution and installation
- **Reliability**: Deterministic builds with `uv.lock` file
- **Modern**: Built-in support for PEP standards and modern Python practices
- **Simplicity**: Unified tool for dependency management, virtual environments, and project builds

### Editable Installation

The project uses **editable installation** to ensure test environment matches production:

```bash
# Install package in editable mode (recommended for development)
make install-editable

# Or as part of full development setup
make dev-install
```

### Why Editable Installation?

**Previous approach (problematic)**:

```toml
# pyproject.toml - REMOVED
[tool.pytest.ini_options]
pythonpath = ["."]  # Direct filesystem imports
```

**Current approach (recommended)**:

```bash
# Package installed in editable mode
uv sync --editable
```

**Benefits**:

- ✅ Tests import from installed package (matches production)
- ✅ CLI entry points work correctly during development
- ✅ Dependency resolution matches production environment
- ✅ Package structure validation during development

### Dependency Management

```bash
# Add a new dependency
uv add requests

# Add a development dependency
uv add --group dev pytest-xdist

# Update all dependencies
uv sync --upgrade

# Install specific groups
uv sync --group dev      # Development dependencies only
uv sync --all-extras     # All optional dependencies
```

## Testing Strategy

### Test Organization

```text
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_supabase.py         # Supabase integration tests
├── integration/             # Integration tests (slower)
├── unit/                    # Unit tests (fast)
└── smoke/                   # Quick smoke tests
```

### Running Tests

```bash
# Full test suite with coverage
make test

# Quick smoke tests (fast feedback)
make quick-test

# Run specific test file
uv run pytest tests/test_supabase.py -v

# Run tests with specific marker
uv run pytest -m integration

# Run tests in parallel (if pytest-xdist installed)
uv run pytest -n auto
```

### Test Configuration

Tests are configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = [
    "--cov=homelab",
    "--cov=scripts",
    "--cov=infrastructure",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--strict-markers",
    "--disable-warnings",
]
markers = [
    "integration: mark a test as an integration test",
    "asyncio: mark a test as asyncio-based",
]
asyncio_mode = "auto"
```

### Coverage Requirements

- **Minimum**: 90% coverage for all production code
- **Reports**: Terminal summary + HTML report in `htmlcov/`
- **Exclusions**: Test files, migration scripts, and configuration files

## Code Quality Standards

### Linting and Formatting

The project uses **Ruff** for both linting and formatting:

```bash
# Check code quality
make lint

# Auto-format code
make format

# Manual commands
uv run ruff check src/ tests/ scripts/ infrastructure/
uv run ruff format src/ tests/ scripts/ infrastructure/
```

### Type Checking

**MyPy** with strict mode for type safety:

```bash
# Type check (included in make lint)
uv run mypy --strict src/ scripts/

# Configuration in pyproject.toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
```

### Pre-commit Hooks

Automated quality gates before commits:

```bash
# Install pre-commit hooks (done automatically in dev-install)
uv run pre-commit install

# Run all pre-commit checks manually
make pre-commit

# Skip hooks for emergency commits (not recommended)
git commit --no-verify
```

## Available Make Targets

### Primary Development Workflow

| Target | Description | Use Case |
|--------|-------------|----------|
| `make dev-install` | Set up complete development environment | Initial setup, after dependency changes |
| `make test` | Run full test suite with coverage | Before commits, CI/CD |
| `make lint` | Run code quality checks (ruff + mypy) | Before commits, debugging quality issues |
| `make format` | Auto-format code with ruff | Before commits, cleaning up code style |
| `make pre-commit` | Run complete validation pipeline | Final check before pushing |

### Installation and Setup

| Target | Description | Use Case |
|--------|-------------|----------|
| `make install-editable` | Install package in editable mode only | When you only need the package installed |
| `make dev-reset` | Clean and reinstall development environment | When dependencies are corrupted |
| `make check-uv` | Ensure UV is installed | Troubleshooting, CI/CD |

### Homelab-Specific Operations

| Target | Description | Use Case |
|--------|-------------|----------|
| `make all` | Complete homelab installation process | Fresh system setup |
| `make audit` | Run system audit | System validation |
| `make health-check` | Check cluster health | Monitoring, troubleshooting |
| `make supabase-deploy` | Deploy Supabase stack | Database setup |
| `make status` | Show comprehensive system status | Quick system overview |

### Utility Targets

| Target | Description | Use Case |
|--------|-------------|----------|
| `make clean` | Remove build artifacts and caches | Cleanup, troubleshooting |
| `make docs` | Build documentation | Documentation updates |
| `make help` | Show all available targets | Discovery, reference |

## Continuous Integration

### GitHub Actions Workflow

The project includes automated CI/CD pipeline:

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync --editable
      - run: make lint
      - run: make test
      - run: make docs
```

### Quality Gates

All code must pass:

- ✅ Ruff linting and formatting
- ✅ MyPy strict type checking
- ✅ Test suite with 90%+ coverage
- ✅ Pre-commit hook validation

## Best Practices

### Development Workflow

1. **Start with tests**: Write tests before implementation (TDD)
2. **Small commits**: Make focused, atomic commits with clear messages
3. **Branch management**: Use feature branches for development
4. **Quality checks**: Run `make pre-commit` before pushing
5. **Documentation**: Update docs with new features or changes

### Code Organization

```text
src/
├── homelab/              # Main package
│   ├── __init__.py
│   ├── cli/              # Command-line interfaces
│   └── models/           # Data models and schemas
├── services/             # Service implementations
scripts/                  # Standalone scripts
infrastructure/           # Infrastructure as code (Pulumi)
tests/                   # Test suite
docs/                    # Documentation
```

### Import Conventions

```python
# Standard library imports
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports
import httpx
from loguru import logger
from pydantic import BaseModel, Field
from rich.console import Console

# Local imports
from homelab.models import ServiceConfig
from homelab.services import DeploymentService
```

### Error Handling

```python
from loguru import logger

async def deploy_service(name: str, config: ServiceConfig) -> DeploymentResult:
    """Deploy service with comprehensive error handling."""
    try:
        logger.info("Starting deployment", service=name)
        result = await deployment_client.deploy(name, config)
        logger.info("Deployment successful", service=name, result=result)
        return result
    except DeploymentError as e:
        logger.error("Deployment failed", service=name, error=str(e))
        raise DeploymentError(f"Failed to deploy {name}") from e
    except Exception as e:
        logger.exception("Unexpected error during deployment", service=name)
        raise
```

### Logging Standards

```python
from loguru import logger

# Structured logging with context
logger.info("Operation started",
           operation="deploy",
           service=service_name,
           config=config.model_dump())

# Error logging with exception chaining
logger.error("Operation failed",
            operation="deploy",
            service=service_name,
            error=str(e))
```

## Troubleshooting

### Common Issues

#### 1. Import errors in tests

```bash
# Problem: ModuleNotFoundError during tests
# Solution: Ensure editable installation
make install-editable
make test
```

#### 2. UV not found

```bash
# Problem: command not found: uv
# Solution: Install UV
pip install uv
# Or let Makefile handle it
make check-uv
```

#### 3. Type checking failures

```bash
# Problem: MyPy errors
# Solution: Fix type annotations or add type ignores
uv run mypy --strict src/ scripts/
```

#### 4. Test failures after dependency changes

```bash
# Problem: Tests fail after adding dependencies
# Solution: Reinstall development environment
make dev-reset
```

#### 5. Pre-commit hook failures

```bash
# Problem: Pre-commit hooks blocking commits
# Solution: Fix issues or update hooks
make format
make lint
uv run pre-commit run --all-files
```

### Debug Commands

```bash
# Check UV environment
uv info

# Check installed packages
uv pip list

# Validate pytest configuration
uv run pytest --collect-only

# Check pre-commit hooks
uv run pre-commit --version
uv run pre-commit run --all-files --verbose

# Check package installation
uv run python -c "import homelab; print(homelab.__file__)"
```

### Getting Help

- **Make targets**: `make help`
- **Pytest help**: `uv run pytest --help`
- **Ruff help**: `uv run ruff --help`
- **UV help**: `uv --help`

---

## Summary

This development workflow emphasizes:

- **Modern tooling**: UV for fast, reliable package management
- **Production parity**: Editable installation ensures tests match production
- **Quality automation**: Pre-commit hooks and CI/CD prevent regressions
- **Developer experience**: Simple Make targets for common tasks
- **Infrastructure focus**: Specialized tooling for K3s and smart home systems

Follow this workflow to maintain high code quality while developing infrastructure automation for your smart home laboratory.
