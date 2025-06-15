# Smart Home K3s Laboratory - Testing Quick Reference

## 🚀 Quick Commands

### Essential Test Commands
```bash
# Complete test suite with coverage
make test-all

# Individual test categories
make test-unit           # Unit tests
make test-integration    # Integration tests
make test-makefile      # Makefile tests

# Coverage analysis
make coverage           # Generate HTML/JSON reports
make coverage-check     # Verify 90%+ coverage
make coverage-optimize  # Optimization analysis
```

### Development Workflow
```bash
# Format → Lint → Test (recommended workflow)
make format && make lint && make test

# Pre-commit validation
make pre-commit

# Development environment setup
make dev-install
```

## 📁 Test Structure

```
tests/
├── unit/                   # Component isolation testing
│   ├── test_uv_utils.py           # UV utilities
│   ├── test_system_audit.py       # System diagnostics
│   ├── test_ssh_key_manager.py    # SSH operations
│   ├── test_install_components.py # Installation logic
│   ├── test_supabase_infrastructure.py # Infrastructure
│   └── test_cli_main.py           # CLI interface
├── integration/            # Cross-component testing
│   ├── test_component_interactions.py  # Component communication
│   ├── test_component_contracts.py     # API contracts
│   ├── test_configuration_validation.py # Config validation
│   └── test_end_to_end_workflows.py    # E2E scenarios
├── makefile/              # Build automation testing
│   ├── test_makefile_targets.py        # Target functionality
│   └── test_makefile_comprehensive.py  # Performance & reliability
├── fixtures/              # Test data and utilities
│   └── test_data.py               # Sample configurations
├── test_helpers.py        # AAA pattern base classes
├── conftest.py           # Pytest fixtures and configuration
└── pytest.ini           # Test execution configuration
```

## 🎯 Coverage Targets

- **Minimum Coverage**: 90% (enforced by CI/CD)
- **Current Achievement**: 90%+ across all modules
- **Focus Areas**: Error handling, edge cases, integration paths

## 🔄 CI/CD Integration

### GitHub Actions Workflow
- **Triggers**: Push, PR, daily schedule
- **Matrix Testing**: Python 3.11/3.12, Ubuntu/Windows
- **Quality Gates**: Format, lint, security scan, test coverage
- **Artifacts**: Coverage reports, test results

### Pre-commit Hooks
- Code formatting (Ruff)
- Linting and type checking (Ruff + MyPy)
- Security scanning (Bandit)
- Conventional commits
- UV dependency validation

## 🛠️ Testing Patterns

### AAA Pattern (Arrange-Act-Assert)
```python
def test_function_behavior():
    # Arrange
    setup_data = create_test_data()

    # Act
    result = function_under_test(setup_data)

    # Assert
    assert result.is_valid
    assert result.message == "expected"
```

### Mocking External Dependencies
```python
@patch('subprocess.run')
@patch('pathlib.Path.exists')
def test_with_mocks(mock_exists, mock_run):
    # Mock setup
    mock_exists.return_value = True
    mock_run.return_value = Mock(returncode=0)

    # Test execution
    result = function_with_external_deps()

    # Verification
    assert result.success
    mock_run.assert_called_once()
```

## 🚨 Troubleshooting

### Common Issues
1. **Import Errors**: Ensure `uv sync --all-extras` completed
2. **Coverage Gaps**: Check test coverage with `make coverage`
3. **Slow Tests**: Use `pytest -x` to stop on first failure
4. **Mock Issues**: Verify mock paths match actual import paths

### Debug Commands
```bash
# Verbose test output
uv run pytest tests/ -v -s

# Run specific test
uv run pytest tests/unit/test_uv_utils.py::test_function_name -v

# Debug with pdb
uv run pytest tests/ --pdb

# Coverage analysis
uv run python scripts/coverage_analysis.py --verbose
```

## 📚 Additional Resources

- **Full Documentation**: [docs/TESTING_DOCUMENTATION.md](../docs/TESTING_DOCUMENTATION.md)
- **Implementation Summary**: [TESTING_IMPLEMENTATION_COMPLETE.md](../TESTING_IMPLEMENTATION_COMPLETE.md)
- **Development Workflow**: [docs/development_workflow.md](../docs/development_workflow.md)
- **GitHub Workflow**: [.github/workflows/test.yml](../.github/workflows/test.yml)

---
*Last Updated: June 2025 | Coverage: 90%+ | Tests: 25+ files | CI/CD: ✅*
