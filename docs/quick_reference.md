# Development Quick Reference

## Essential Commands

```bash
# 🚀 Setup & Installation
make dev-install          # Complete development environment setup
make install-editable     # Install package in editable mode only

# 🧪 Testing & Quality
make test                 # Run full test suite with coverage
make lint                 # Check code quality (ruff + mypy)
make format               # Auto-format code with ruff
make pre-commit           # Run complete validation pipeline

# 🏠 Homelab Operations
make all                  # Complete homelab installation
make status               # Show system status dashboard
make health-check         # Check cluster health
make supabase-deploy      # Deploy Supabase stack

# 🛠️ Utilities
make clean                # Clean build artifacts
make help                 # Show all available targets
```

## UV Commands

```bash
# Package Management
uv add <package>          # Add new dependency
uv add --group dev <pkg>  # Add development dependency
uv sync                   # Install dependencies
uv sync --editable        # Install with editable package
uv sync --all-extras      # Install all optional dependencies

# Environment Management
uv info                   # Show environment info
uv pip list               # List installed packages
uv run <command>          # Run command in UV environment
```

## Testing Commands

```bash
# Run different test types
uv run pytest tests/                    # All tests
uv run pytest tests/unit/               # Unit tests only
uv run pytest tests/integration/        # Integration tests
uv run pytest -m "not integration"      # Skip integration tests
uv run pytest -k "test_name"            # Run specific test
uv run pytest --cov-report=html         # Generate HTML coverage report
```

## Code Quality Commands

```bash
# Ruff (linting & formatting)
uv run ruff check .                     # Check for issues
uv run ruff check --fix .               # Fix auto-fixable issues
uv run ruff format .                    # Format code

# MyPy (type checking)
uv run mypy src/ scripts/               # Type check all code
uv run mypy --strict src/               # Strict type checking
```

## Git Workflow

```bash
# Development cycle
git checkout -b feature/new-feature     # Create feature branch
make dev-install                        # Setup environment
# ... make changes ...
make pre-commit                         # Validate changes
git add .                               # Stage changes
git commit -m "feat: add new feature"   # Commit with conventional message
git push origin feature/new-feature     # Push to remote
```

## Debugging Commands

```bash
# Environment debugging
uv info                                 # UV environment info
uv run python -c "import homelab; print(homelab.__file__)"  # Check package location
uv run pytest --collect-only           # Validate test discovery
make clean && make dev-install          # Reset environment

# Service debugging
make status                             # System overview
make health-check                       # Detailed health check
kubectl get pods -A                     # K3s cluster status
curl -s http://192.168.0.41:8123/api/  # Home Assistant status
```

## File Locations

```text
📁 Project Structure
├── 📄 Makefile                        # Build automation
├── 📄 pyproject.toml                  # Project configuration
├── 📄 uv.lock                         # Dependency lock file
├── 📁 src/homelab/                    # Main package
├── 📁 scripts/                        # Standalone scripts
├── 📁 infrastructure/                 # Pulumi infrastructure
├── 📁 tests/                          # Test suite
└── 📁 docs/                           # Documentation

🔧 Configuration Files
├── .pre-commit-config.yaml            # Pre-commit hooks
├── .github/workflows/                 # CI/CD pipelines
└── docker-compose.dev.yml             # Development containers
```

## Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` in tests | `make install-editable` |
| `command not found: uv` | `pip install uv` or `make check-uv` |
| Pre-commit hooks failing | `make format && make lint` |
| Tests failing after dependency changes | `make dev-reset` |
| Type checking errors | Fix annotations or `# type: ignore` |

## Links

- 📚 [Full Development Workflow](development_workflow.md)
- 🏠 [Project README](../README.md)
- 📋 [Implementation Plan](planning/implementation_plan.md)
