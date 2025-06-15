# Smart Home K3s Laboratory - Copilot Instructions

## Project Architecture & Context

This is a comprehensive smart home laboratory built on Kubernetes (K3s) with infrastructure-as-code practices. The system integrates IoT devices, home automation, and distributed AI inference across multiple nodes.

**Network Topology:**
- Control Node: Windows 11 Pro (192.168.0.50) running WSL2 Ubuntu (192.168.0.51)
- Agent Node: NVIDIA Jetson AGX Orin (192.168.0.66)
- Home Assistant Yellow: MQTT broker and IoT gateway (192.168.0.41)
- Dual-IP networking requires special handling for K3s API server binding and external access

## Development Stack & Tooling

**Core Development Tools:**
- **Package Management**: Use `uv` for Python package management with `pyproject.toml` configuration
- **Type Checking**: MyPy in strict mode for all Python code with `--strict` flag
- **Logging**: Loguru exclusively for all logging with structured JSON output
- **Linting/Formatting**: Ruff for both linting and code formatting with 88-character line length
- **CLI Development**: Typer with Rich for all command-line interfaces and progress indicators
- **Data Validation**: Pydantic V2 models with `Field()` descriptors for all data structures

**Testing & Quality Assurance:**
- **Python Testing**: pytest with pytest-asyncio for async support and pytest-cov for coverage
- **Infrastructure Testing**: pytest for Pulumi infrastructure code with mocking
- **Ansible Testing**: Molecule for Ansible playbook testing and validation
- **Test Organization**: Tests mirror source structure in `tests/` directory with `conftest.py` fixtures
- **Coverage Requirements**: Minimum 90% test coverage for all production code

**Automation & CI/CD:**
- **Pre-commit Hooks**: Automated quality checks including Ruff, MyPy, and pytest
- **Build Automation**: Makefiles for common development tasks (test, lint, deploy, clean)
- **Documentation**: MkDocs with auto-generation from docstrings and markdown files
- **CI/CD Pipeline**: GitHub Actions for automated testing, building, and deployment
- **Container Scanning**: Automated vulnerability scanning for all container images

**Development Workflow Standards:**
- All Python packages must include `pyproject.toml` with uv dependency management
- Use `uv sync` for dependency installation and environment management
- Implement `Makefile` targets: `make test`, `make lint`, `make format`, `make docs`, `make deploy`
- GitHub Actions workflows must include: test, lint, security-scan, and deploy stages
- All commits must pass pre-commit hooks before acceptance

## Development Standards & Technologies

**Python Development (Primary Language):**
- Always use Python 3.11+ features and type hints with strict typing
- Use `from typing import` imports for type annotations, prefer built-in generics where available
- All functions must have complete type annotations including return types
- Use Pydantic V2 models for data validation with `Field()` descriptors
- Implement proper error handling with custom exception classes that inherit from built-in exceptions
- Use Loguru for all logging with structured JSON output: `logger.info("message", key=value)`
- CLI applications must use Typer with Rich for formatting and progress indicators
- Package management exclusively through `uv` with `pyproject.toml` configuration

**Code Quality & Testing:**
- Follow TDD approach - write tests first, then implementation
- Use pytest for all testing with async support via pytest-asyncio
- Create fixtures in `conftest.py` for reusable test components
- Mock external dependencies (K8s API, MQTT broker, SSH connections) in tests
- Use Ruff for linting/formatting with line length 88 characters
- All code must pass MyPy strict mode type checking (`mypy --strict`)
- Use pre-commit hooks for automated quality checks
- Ansible playbooks must be tested with Molecule framework
- Maintain minimum 90% test coverage across all modules

**Infrastructure as Code Patterns:**
- Pulumi resources should use proper typing with `pulumi_kubernetes` imports
- Ansible playbooks must be idempotent with proper error handling and rollback capabilities
- K3s configurations must account for WSL2 dual-IP networking with `bind-address` and `advertise-address` settings
- All infrastructure code should include comprehensive logging and state validation
- Use resource tags and labels consistently for organization and cleanup
- Infrastructure tests must use pytest with proper mocking of cloud APIs

## Kubernetes & Container Orchestration

**K3s Specific Requirements:**
- Control plane runs in WSL2, must bind to WSL2 IP (192.168.0.51) but advertise Windows host IP (192.168.0.50)
- Always disable Traefik in K3s installation: `--disable traefik` (using containerized Traefik instead)
- External access to K3s API requires Windows host IP configuration for agent node connectivity
- Use dual kubeconfig files: internal (WSL2 IP) and external (Windows host IP) access
- Account for WSL2 systemd limitations - provide alternative service management approaches

**Container & Service Patterns:**
- All deployments must include resource limits and requests for memory/CPU
- Use ConfigMaps and Secrets for configuration, never hardcode sensitive data
- Implement health checks (readiness/liveness probes) for all services
- Services requiring external access should use NodePort or LoadBalancer with proper network binding
- Container images should use specific tags, not 'latest', with vulnerability scanning

## Smart Home Integration

**MQTT & Home Assistant:**
- MQTT broker runs on Home Assistant Yellow (192.168.0.41:1883)
- Use `paho-mqtt` or `asyncio-mqtt` for Python MQTT clients
- All MQTT topics should follow Home Assistant discovery format: `homeassistant/{component}/{node_id}/{object_id}/config`
- Implement proper MQTT reconnection logic with exponential backoff
- IoT device state should be cached locally with periodic synchronization

**Event-Driven Architecture:**
- Use RabbitMQ for internal service communication with proper exchange/queue setup
- Implement circuit breaker patterns for external service dependencies
- All async operations should include timeout handling and retry logic
- Use dataclasses or Pydantic models for event schemas with proper serialization

## Networking & Security

**WSL2 Network Considerations:**
- Always test connectivity between WSL2 instance and Windows host
- SSH key management should leverage Windows SSH keys via `/mnt/c/Users/{user}/.ssh/`
- Port forwarding may be required for services accessed from external nodes
- Network debugging should include both WSL2 and Windows host perspectives

**Security Practices:**
- All SSH connections must use key-based authentication, never passwords in production code
- Secrets should be managed through HashiCorp Vault or Kubernetes Secrets
- Network services should implement TLS/SSL encryption for external communications
- Regular security scanning for containers and dependencies

## Development Workflow

**File Organization:**
- Python packages in `src/` directory with proper `__init__.py` files
- CLI tools in `src/cli/` using Typer with auto-completion support
- Infrastructure code in separate directories: `ansible/`, `infrastructure/` (Pulumi)
- Tests mirror source structure in `tests/` directory
- Documentation auto-generated with MkDocs from docstrings and markdown files
- Each project must include `pyproject.toml`, `Makefile`, and `.pre-commit-config.yaml`

**Project Structure Template:**
```
project/
├── pyproject.toml          # uv package configuration
├── Makefile               # Development automation
├── .pre-commit-config.yaml # Quality gate automation
├── src/
│   ├── __init__.py
│   ├── cli/               # Typer CLI applications
│   └── models/            # Pydantic data models
├── tests/
│   ├── conftest.py        # pytest fixtures
│   └── test_*.py          # Test modules
├── docs/
│   └── *.md               # MkDocs documentation
└── .github/
    └── workflows/         # GitHub Actions CI/CD
```

**Error Handling & Observability:**
- Use structured logging with correlation IDs for request tracing
- Implement comprehensive error handling with proper exception chaining
- Include performance metrics collection using OpenTelemetry patterns
- All long-running operations should include progress reporting and cancellation support
- Log all infrastructure operations with structured data for observability

**Makefile Targets (Required):**
```makefile
.PHONY: install test lint format docs clean deploy
install:
	uv sync
test:
	uv run pytest tests/ -v --cov=src
lint:
	uv run ruff check src/ tests/
	uv run mypy --strict src/
format:
	uv run ruff format src/ tests/
docs:
	uv run mkdocs build
clean:
	find . -type d -name __pycache__ -delete
	find . -name "*.pyc" -delete
deploy:
	uv run pulumi up --yes
```

## Code Examples & Patterns

When generating code, prefer these patterns:

**Project Setup with uv:**
```toml
# pyproject.toml
[project]
name = "homelab-service"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "loguru>=0.7.0",
    "typer[all]>=0.9.0",
    "pydantic>=2.0.0",
    "pulumi>=3.0.0",
    "pulumi-kubernetes>=4.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "mypy>=1.5.0",
    "ruff>=0.1.0",
    "pre-commit>=3.0.0",
]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.mypy]
strict = true
python_version = "3.11"
```

**Async Function with Proper Error Handling:**
```python
async def deploy_service(service_name: str, config: ServiceConfig) -> DeploymentResult:
    """Deploy service with proper error handling and logging."""
    with log_operation("deploy_service", service=service_name):
        try:
            result = await kubernetes_client.deploy(service_name, config)
            logger.info("Service deployed successfully", service=service_name, result=result)
            return DeploymentResult(status="success", details=result)
        except KubernetesError as e:
            logger.error("Deployment failed", service=service_name, error=str(e))
            raise DeploymentError(f"Failed to deploy {service_name}") from e
```

**Typer CLI with Rich Integration:**
```python
import typer
from rich.console import Console
from rich.progress import Progress

app = typer.Typer()
console = Console()

@app.command()
def deploy(
    service: str = typer.Argument(..., help="Service name to deploy"),
    config_file: Path = typer.Option("config.yaml", help="Configuration file"),
) -> None:
    """Deploy service to K3s cluster."""
    with Progress() as progress:
        task = progress.add_task("Deploying service...", total=100)
        # Implementation with progress updates
        progress.update(task, completed=100)

    console.print(f"✅ Service {service} deployed successfully", style="green")
```

**GitHub Actions Workflow Template:**
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
      - run: uv sync
      - run: uv run make lint
      - run: uv run make test
      - run: uv run make docs
```
