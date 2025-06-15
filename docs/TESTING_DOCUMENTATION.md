# Smart Home K3s Laboratory - Testing Documentation

## Overview

This document provides comprehensive guidance for the Smart Home K3s Laboratory testing suite, which achieves 90%+ code coverage through strategic unit, integration, and Makefile testing.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Architecture](#test-architecture)
- [Running Tests](#running-tests)
- [Coverage Analysis](#coverage-analysis)
- [Writing New Tests](#writing-new-tests)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

## Quick Start

### Prerequisites

- Python 3.11+ with UV package manager
- Git with pre-commit hooks
- Make (for Makefile automation)

### Initial Setup

```bash
# Clone and setup project
git clone <repository-url>
cd homelab

# Install dependencies
make install

# Setup development environment
make dev-install

# Run all tests
make test

# Generate coverage report
make coverage
```

## Test Architecture

### Directory Structure

```
tests/
├── conftest.py                 # Global fixtures and configuration
├── pytest.ini                 # Pytest configuration
├── test_helpers.py            # Testing utilities and patterns
├── unit/                      # Unit tests for individual modules
│   ├── test_uv_utils.py      # UV utility functions
│   ├── test_system_audit.py  # System audit functionality
│   ├── test_ssh_key_manager.py # SSH key management
│   ├── test_install_components.py # Component installation
│   ├── test_supabase_infrastructure.py # Infrastructure tests
│   └── test_cli_main.py       # CLI interface tests
├── integration/               # Integration and end-to-end tests
│   ├── test_component_interactions.py # Cross-component communication
│   ├── test_component_contracts.py # API/interface validation
│   ├── test_configuration_validation.py # Config loading tests
│   └── test_end_to_end_workflows.py # Complete workflow tests
├── makefile/                  # Makefile target testing
│   ├── test_makefile_targets.py # Basic target functionality
│   └── test_makefile_comprehensive.py # Advanced Makefile testing
├── fixtures/                  # Test data and mock objects
│   └── test_data.py          # Sample configurations and data
└── logs/                      # Test execution logs
```

### Testing Patterns

#### AAA Pattern

All tests follow the **Arrange-Act-Assert** pattern:

```python
class TestExample(AAATester):
    def test_function_success(self):
        # Arrange
        input_data = {"key": "value"}
        expected_result = "success"

        # Act
        result = function_under_test(input_data)

        # Assert
        assert result == expected_result
        self.assert_success_result(result)
```

#### Comprehensive Mocking

External dependencies are systematically mocked:

```python
@patch('subprocess.run')
@patch('pathlib.Path.exists')
def test_with_mocking(self, mock_exists, mock_subprocess):
    # Arrange
    mock_exists.return_value = True
    mock_subprocess.return_value = Mock(returncode=0, stdout="success")

    # Act & Assert
    result = function_with_dependencies()
    assert result.success is True
```

## Running Tests

### Test Categories

#### Unit Tests


Test individual functions and classes in isolation:

```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run specific test file
uv run pytest tests/unit/test_uv_utils.py -v

# Run specific test method
uv run pytest tests/unit/test_uv_utils.py::TestUVUtils::test_check_uv_installation_success -v
```


#### Integration Tests

Test component interactions and workflows:

```bash
# Run all integration tests
uv run pytest tests/integration/ -v

# Run end-to-end workflow tests
uv run pytest tests/integration/test_end_to_end_workflows.py -v

# Run with integration marker
uv run pytest -m integration -v
```


#### Makefile Tests

Test build and automation processes:

```bash
# Run Makefile tests
uv run pytest tests/makefile/ -v

# Test specific Makefile targets
uv run pytest tests/makefile/test_makefile_targets.py::TestMakefileTargets::test_help_target -v
```

### Test Markers

Tests are categorized using pytest markers:

```bash
# Run only unit tests
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"

# Run Makefile tests
uv run pytest -m makefile

# Run smoke tests only
uv run pytest -m smoke
```

### Parallel Execution

For faster test execution:

```bash
# Install pytest-xdist
uv add pytest-xdist

# Run tests in parallel
uv run pytest -n auto tests/

# Run with specific worker count
uv run pytest -n 4 tests/
```

## Coverage Analysis


### Generating Coverage Reports

#### Terminal Coverage

```bash
# Basic coverage report
uv run pytest --cov=src --cov=scripts --cov=infrastructure --cov-report=term

# Coverage with missing lines

uv run pytest --cov=src --cov=scripts --cov=infrastructure --cov-report=term-missing
```

#### HTML Coverage Report

```bash
# Generate interactive HTML report
uv run pytest --cov=src --cov=scripts --cov=infrastructure --cov-report=html

# Open in browser

open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html # Windows
```

#### JSON Coverage Data

```bash
# Generate machine-readable coverage data
uv run pytest --cov=src --cov=scripts --cov=infrastructure --cov-report=json:coverage.json
```

### Coverage Optimization

Use the automated coverage optimizer:

```bash
# Run coverage optimization analysis
uv run python scripts/coverage_optimizer.py

# View optimization recommendations
cat COVERAGE_OPTIMIZATION.md
```

### Coverage Thresholds

The project maintains strict coverage standards:

- **Target Coverage**: 90%+
- **Minimum Acceptable**: 85%
- **Critical Files**: 95%+ (core infrastructure)

Coverage thresholds are enforced in CI/CD:

```ini
# pytest.ini
[tool:pytest]
addopts = --cov=src --cov=scripts --cov=infrastructure --cov-fail-under=90
```

## Writing New Tests

### Test File Structure

Create new test files following the naming convention:

```python
#!/usr/bin/env python3
"""
Unit tests for [module_name] functionality.
Tests cover [brief description of what's tested].
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from test_helpers import AAATester


class TestModuleName(AAATester):
    """Test suite for [module] functionality."""

    @pytest.fixture
    def sample_data(self):
        """Sample test data."""
        return {"key": "value"}

    def test_function_success(self, sample_data):
        """Test successful function execution.

        Arrange: Setup test data and mocks
        Act: Execute function under test
        Assert: Verify expected behavior
        """
        # Arrange
        expected = "success"

        # Act
        result = function_under_test(sample_data)

        # Assert
        assert result == expected
        self.assert_success_result(result)

    def test_function_error_handling(self):
        """Test function error handling.

        Arrange: Setup error conditions
        Act: Execute function with invalid input
        Assert: Verify graceful error handling
        """
        # Arrange
        invalid_input = None

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid input"):

            function_under_test(invalid_input)
```

### Fixtures and Mocking

#### Common Fixtures

Available in `conftest.py`:

```python
# Temporary directory
def test_function(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

# Kubernetes API mock
def test_k8s_function(mock_k8s_client):
    mock_k8s_client.list_pods.return_value = []

# MQTT client mock
def test_mqtt_function(mock_mqtt_client):
    mock_mqtt_client.publish.return_value = Mock(rc=0)
```

#### Custom Mocking Patterns

```python
# Mock external processes
@patch('subprocess.run')
def test_subprocess_call(mock_run):
    mock_run.return_value = Mock(returncode=0, stdout="output")

# Mock file system operations
@patch('pathlib.Path.exists')
@patch('pathlib.Path.read_text')
def test_file_operations(mock_read, mock_exists):
    mock_exists.return_value = True
    mock_read.return_value = "file content"

# Mock network operations
@patch('requests.get')
def test_http_request(mock_get):
    mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "ok"})
```

### Error Testing

Test error conditions comprehensively:

```python
def test_error_scenarios(self):
    """Test various error conditions."""

    # Test invalid input
    with pytest.raises(ValueError):
        function_under_test(invalid_input)

    # Test file not found
    with pytest.raises(FileNotFoundError):
        function_under_test("/nonexistent/path")

    # Test network errors
    with patch('requests.get', side_effect=ConnectionError):
        result = function_under_test()
        self.assert_failure_result(result, "connection")
```

## CI/CD Integration

### GitHub Actions Workflow

The project includes automated CI/CD with comprehensive testing:

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]

    steps:
    - uses: actions/checkout@v4

    - name: Install UV
      uses: astral-sh/setup-uv@v1

    - name: Set up Python ${{ matrix.python-version }}
      run: uv python install ${{ matrix.python-version }}

    - name: Install dependencies
      run: uv sync --all-extras

    - name: Run linting
      run: |
        uv run ruff check src/ tests/ scripts/ infrastructure/
        uv run mypy --strict src/ scripts/

    - name: Run tests with coverage
      run: |
        uv run pytest tests/ --cov=src --cov=scripts --cov=infrastructure \
          --cov-report=xml --cov-report=term-missing

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

    - name: Run Makefile tests
      run: uv run pytest tests/makefile/ -v

    - name: Test Makefile targets
      run: |
        make help
        make lint
        make format
```

### Pre-commit Hooks

Automated quality checks before commits:

```yaml
# .pre-commit-config.yaml
repos:
-   repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
    -   id: ruff
        args: [--fix, --exit-non-zero-on-fix]
    -   id: ruff-format

-   repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
    -   id: mypy
        args: [--strict]
        additional_dependencies: [types-all]

-   repo: local
    hooks:
    -   id: pytest
        name: pytest
        entry: uv run pytest
        language: system

        types: [python]
        args: [tests/, --cov=src, --cov-fail-under=90]
```

### Continuous Integration Features

#### Automated Testing


- ✅ Unit tests on multiple Python versions
- ✅ Integration tests with mocked dependencies
- ✅ Makefile target validation
- ✅ Coverage reporting and enforcement
- ✅ Code quality checks (Ruff, MyPy)


#### Coverage Monitoring

- ✅ Codecov integration for coverage tracking
- ✅ Coverage trend analysis
- ✅ PR coverage comparison
- ✅ Coverage threshold enforcement

#### Quality Gates

- ✅ Minimum 90% coverage requirement
- ✅ All tests must pass
- ✅ Code quality checks must pass
- ✅ Type checking must pass
- ✅ No linting errors allowed

### Makefile Integration

 he Makefile provides convenient CI/CD commands:

```makefile
# Development workflow
 PHONY: test lint format coverage pre-commit

test: check-uv  ## Run comprehensive test suite
 uv run pytest tests/ -v --cov=src --cov=scripts --cov=infrastructure

 int: check-uv  ## Run code quality checks
 uv run ruff check src/ tests/ scripts/ infrastructure/
 uv run mypy --strict src/ scripts/

format: check-uv  ## Format code with ruff
 uv run ruff format src/ tests/ scripts/ infrastructure/

coverage: check-uv  ## Generate coverage reports
 uv run pytest tests/ --cov=src --cov=scripts --cov=infrastructure \
  --cov-report=html --cov-report=term-missing
 @echo "Coverage report: htmlcov/index.html"


pre-commit: lint test  ## Run pre-commit validation
 @echo "✅ All checks passed - ready for commit"
```

## Troubleshooting

### Common Issues

#### Import Errors


```bash
# Issue: Module not found
# Solution: Ensure proper PYTHONPATH
export PYTHONPATH="$PWD/src:$PWD/scripts:$PWD/infrastructure"

# Or use UV's path resolution
uv run pytest tests/
```

#### Test Collection Failures


```bash
# Issue: Tests not collected
# Solution: Check file naming and structure
pytest --collect-only tests/

# Ensure proper test file naming: test_*.py or *_test.py
# Ensure test classes start with Test*
# Ensure test methods start with test_*
```

#### Coverage Issues


```bash
# Issue: Low coverage numbers
# Solution: Run coverage analysis
uv run python scripts/coverage_optimizer.py

# Check for uncovered files
uv run pytest --cov=src --cov-report=term-missing

# Add missing tests based on recommendations
```


#### Mock/Fixture Issues

```bash
# Issue: Mock not working
# Solution: Check import paths and patching targets
@patch('module.function')  # Patch where it's used, not where it's defined

# Issue: Fixture not found
# Solution: Check conftest.py location and fixture scope
```

### Debugging Tests


#### Verbose Output

```bash
# Run with maximum verbosity
uv run pytest -vvv tests/

# Show local variables in tracebacks
uv run pytest --tb=long tests/


# Drop into debugger on failure
uv run pytest --pdb tests/
```

#### Log Capture

```bash
# Show captured logs
uv run pytest --log-cli-level=INFO tests/


# Capture logs to file
uv run pytest --log-file=test.log tests/
```

#### Isolated Test Runs

```bash
# Run single test with output
uv run pytest -v -s tests/unit/test_example.py::test_specific_function

# Run with coverage for single module
uv run pytest --cov=specific_module --cov-report=term tests/unit/test_example.py

```

### Performance Issues

#### Slow Tests

```bash
# Identify slow tests
uv run pytest --durations=10 tests/

# Skip slow tests during development
uv run pytest -m "not slow" tests/

# Run tests in parallel
uv run pytest -n auto tests/
```

#### Memory Issues

```bash
# Monitor memory usage
uv run pytest --memcheck tests/

# Run tests in smaller batches
uv run pytest tests/unit/
uv run pytest tests/integration/
```


## Advanced Topics

### Custom Test Markers

Define custom markers in `pytest.ini`:

```ini
[tool:pytest]
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
    smoke: Smoke tests for quick validation
    makefile: Makefile target tests
    requires_k8s: Tests requiring Kubernetes
    requires_network: Tests requiring network access
```

Usage:

```python
@pytest.mark.slow
@pytest.mark.requires_network
def test_network_operation():
    """Test that requires network access and runs slowly."""
    pass
```

### Parametrized Tests

Test multiple scenarios efficiently:

```python
@pytest.mark.parametrize("input,expected", [
    ("valid_input", "success"),
    ("invalid_input", "error"),
    ("edge_case", "handled"),
])
def test_multiple_scenarios(input, expected):
    result = function_under_test(input)
    assert result.status == expected
```


### Property-Based Testing

Use Hypothesis for property-based testing:

```python
from hypothesis import given, strategies as st

@given(st.text(), st.integers())
def test_function_properties(text_input, int_input):
    """Test function properties with generated inputs."""
    result = function_under_test(text_input, int_input)

    # Test invariants
    assert isinstance(result, dict)
    assert "status" in result
```

### Test Data Management

#### External Test Data


```python
# tests/fixtures/test_data.py
TEST_CONFIGS = {
    "valid_config": {
        "database": {"host": "localhost", "port": 5432},
        "cache": {"enabled": True, "ttl": 300}
    },
    "invalid_config": {
        "database": {"host": "", "port": "invalid"}
    }
}

# Usage in tests
def test_config_loading():
    config = TEST_CONFIGS["valid_config"]

    result = load_configuration(config)
    assert result.success is True
```

#### Dynamic Test Data

```python
@pytest.fixture
def database_config(tmp_path):
    """Generate temporary database configuration."""
    config_file = tmp_path / "db_config.yaml"
    config_file.write_text(yaml.dump({
        "host": "test_host",
        "port": 5432,
        "database": "test_db"

    }))
    return config_file
```

### Performance Testing

#### Benchmark Tests

```python
import time

def test_function_performance():
    """Test function performance requirements."""
    start_time = time.time()

    result = expensive_function()

    execution_time = time.time() - start_time
    assert execution_time < 1.0, f"Function too slow: {execution_time:.2f}s"
    assert result.success is True
```

#### Memory Usage Tests

```python
import psutil
import os

def test_memory_usage():
    """Test function memory usage."""
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss

    result = memory_intensive_function()

    memory_after = process.memory_info().rss
    memory_used = memory_after - memory_before

    # Assert reasonable memory usage (e.g., < 100MB)
    assert memory_used < 100 * 1024 * 1024
    assert result.success is True
```

## Contributing to Tests

### Test Contribution Guidelines

1. **Follow AAA Pattern**: All tests must use Arrange-Act-Assert structure
2. **Comprehensive Documentation**: Include docstrings explaining test purpose
3. **Proper Mocking**: Mock external dependencies appropriately
4. **Error Testing**: Include tests for error conditions and edge cases
5. **Performance Awareness**: Avoid unnecessarily slow tests
6. **Marker Usage**: Apply appropriate pytest markers

### Code Review Checklist

- [ ] Tests follow AAA pattern
- [ ] All external dependencies are mocked
- [ ] Error conditions are tested
- [ ] Test documentation is clear
- [ ] Coverage requirements are met
- [ ] Performance is acceptable
- [ ] Markers are applied correctly

### Test Quality Standards

- **Coverage**: Maintain 90%+ coverage
- **Documentation**: Every test must have a clear docstring
- **Isolation**: Tests must not depend on external services
- **Determinism**: Tests must be deterministic and repeatable
- **Performance**: Tests should complete in reasonable time

---

## Conclusion

The Smart Home K3s Laboratory testing suite provides comprehensive validation of all system components through strategic unit, integration, and Makefile testing. With 90%+ code coverage, automated CI/CD integration, and extensive documentation, the testing framework ensures robust and reliable homelab infrastructure.

For additional support or questions, refer to the troubleshooting section or contact the development team.
