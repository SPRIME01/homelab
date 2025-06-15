

**Development Stack & Tooling:**
- Python with strict typing (mypy), Loguru for logging, uv for package management
- Ruff for linting/formatting, Typer for CLI interfaces, Pydantic for data validation
- TDD approach with pytest (Python/Pulumi), Molecule (Ansible), and appropriate testing frameworks
- Pre-commit hooks, Makefiles, automated documentation with MkDocs
- GitHub Actions for CI/CD automation

**Development Environment:**
- VSCode with GitHub Copilot Pro optimization for maximum AI-assisted development
- Configuration for 'vibe coding' workflow optimization
- Containerized development environments where applicable

**Architecture & Implementation:**
- Detailed system architecture with component interactions, API specifications, data models
- Security implementation details, deployment strategies, monitoring implementation
- Error handling and resilience patterns, code organization, testing strategies

Focus on pragmatic implementation details and developer experience optimization while addressing technical debt and implementing industry best practices.

---

# Software Design Specification (SDS): Smart Home K3s Lab Infrastructure

## #### 1. System Architecture Overview

### Core Architecture Pattern
The system follows a **microservices architecture** with **event-driven design**, implementing the **Hexagonal Architecture (Ports and Adapters)** pattern for clean separation of concerns.

```
┌─────────────────────────────────────────────────────────────┐
│                     Control Plane Layer                     │
├─────────────────────────────────────────────────────────────┤
│  ArgoCD  │  Vault   │  Traefik  │  Prometheus │  Grafana   │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                         │
├─────────────────────────────────────────────────────────────┤
│ LocalAI  │ Guacamole │ Home Assistant │ Custom Services     │
├─────────────────────────────────────────────────────────────┤
│                    Data Fabric Layer                       │
├─────────────────────────────────────────────────────────────┤
│  RabbitMQ │ PostgreSQL │ Redis │ InfluxDB │ VectorDB       │
├─────────────────────────────────────────────────────────────┤
│                 Infrastructure Layer                        │
├─────────────────────────────────────────────────────────────┤
│     K3s Cluster (Control: 192.168.0.50, Agent: .66)       │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack Architecture

| Layer | Technology | Purpose | Implementation |
|-------|------------|---------|----------------|
| **CLI Interface** | Typer + Rich | Command-line tools | Type-safe CLI with auto-completion |
| **Validation** | Pydantic V2 | Data validation | Strict typing with serialization |
| **Logging** | Loguru | Structured logging | JSON formatting with rotation |
| **Package Management** | uv | Dependency management | Fast resolver with lock files |
| **Code Quality** | Ruff + MyPy | Linting/Type checking | Pre-commit integration |
| **Testing** | pytest + Molecule | Unit/Integration testing | TDD with fixtures |
| **Documentation** | MkDocs + mkdocs-material | Auto-generated docs | API docs from docstrings |

## #### 2. Development Environment Setup

### Project Structure
```
smart-home-k3s-lab/
├── .devcontainer/           # VSCode dev container config
├── .github/
│   ├── workflows/           # GitHub Actions CI/CD
│   └── CODEOWNERS          # Code review assignments
├── .vscode/                # VSCode settings optimized for Copilot
├── ansible/                # Ansible playbooks and roles
├── docs/                   # MkDocs documentation
├── infrastructure/         # Pulumi infrastructure code
├── scripts/               # Python automation scripts
├── src/
│   ├── homelab/           # Main Python package
│   ├── cli/               # Typer CLI applications
│   └── services/          # Microservice implementations
├── tests/                 # Test suites
├── pyproject.toml         # Python project configuration
├── Makefile              # Development automation
└── docker-compose.dev.yml # Development environment
```

### VSCode Configuration for GitHub Copilot Pro

**.vscode/settings.json**
```json
{
  "github.copilot.enable": {
    "*": true,
    "yaml": true,
    "markdown": true,
    "python": true
  },
  "github.copilot.inlineSuggest.enable": true,
  "github.copilot.editor.enableCodeActions": true,
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "ruff",
  "python.testing.pytestEnabled": true,
  "ruff.organizeImports": true,
  "mypy-type-checker.preferDaemon": true
}
```

**.vscode/extensions.json**
```json
{
  "recommendations": [
    "GitHub.copilot",
    "GitHub.copilot-chat",
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "ms-python.python",
    "ms-vscode.vscode-typescript-next"
  ]
}
```

### pyproject.toml Configuration
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "smart-home-k3s-lab"
version = "0.1.0"
description = "Smart Home K3s Laboratory Infrastructure"
dependencies = [
    "typer[all]>=0.9.0",
    "pydantic>=2.5.0",
    "loguru>=0.7.0",
    "rich>=13.0.0",
    "pulumi>=3.95.0",
    "pulumi-kubernetes>=4.0.0",
    "ansible>=8.0.0",
    "paho-mqtt>=1.6.0",
    "asyncio-mqtt>=0.16.0",
    "httpx>=0.25.0",
    "pydantic-settings>=2.1.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "molecule[docker]>=6.0.0",
    "mypy>=1.7.0",
    "ruff>=0.1.8",
    "pre-commit>=3.6.0",
    "mkdocs-material>=9.4.0",
    "mkdocs-gen-files>=0.5.0"
]

[tool.ruff]
target-version = "py311"
line-length = 88
select = ["E", "F", "I", "N", "UP", "YTT", "S", "BLE", "FBT", "B", "A", "COM", "C4", "T20", "SIM", "ARG", "ERA", "PL", "RUF"]
ignore = ["S101", "PLR0913"]

[tool.ruff.per-file-ignores]
"tests/*" = ["S101", "PLR2004"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = "-v --cov=src --cov-report=html --cov-report=term-missing"
asyncio_mode = "auto"
```

## #### 3. Core System Components

### CLI Interface Design with Typer

**src/cli/main.py**
```python
from typing import Annotated, Optional
import typer
from rich.console import Console
from loguru import logger
from pathlib import Path

app = typer.Typer(
    name="homelab",
    help="Smart Home K3s Lab Management CLI",
    rich_markup_mode="rich"
)
console = Console()

@app.command()
def deploy(
    environment: Annotated[str, typer.Argument(help="Target environment")] = "dev",
    dry_run: Annotated[bool, typer.Option("--dry-run", "-d")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False
) -> None:
    """Deploy infrastructure to the specified environment."""
    if verbose:
        logger.configure(handlers=[{"sink": "sys.stdout", "level": "DEBUG"}])

    console.print(f"[bold green]Deploying to {environment}[/bold green]")
    # Implementation here
```

### Data Models with Pydantic V2

**src/homelab/models/infrastructure.py**
```python
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, IPvAnyAddress, validator
from enum import Enum

class NodeType(str, Enum):
    CONTROL = "control"
    AGENT = "agent"

class KubernetesNode(BaseModel):
    """Kubernetes node configuration model."""

    name: str = Field(..., description="Node name")
    ip_address: IPvAnyAddress = Field(..., description="Node IP address")
    node_type: NodeType = Field(..., description="Node type")
    ssh_user: str = Field(default="ubuntu", description="SSH username")
    ssh_key_path: Optional[Path] = Field(None, description="SSH private key path")
    labels: Dict[str, str] = Field(default_factory=dict)
    taints: List[Dict[str, str]] = Field(default_factory=list)

    model_config = {
        "json_encoders": {
            IPvAnyAddress: str,
            Path: str
        }
    }

class ClusterConfig(BaseModel):
    """K3s cluster configuration."""

    cluster_name: str = Field(..., description="Cluster name")
    nodes: List[KubernetesNode] = Field(..., description="Cluster nodes")
    kubeconfig_path: Path = Field(..., description="Kubeconfig file path")

    @validator('nodes')
    def validate_control_node(cls, v):
        control_nodes = [n for n in v if n.node_type == NodeType.CONTROL]
        if len(control_nodes) != 1:
            raise ValueError("Exactly one control node required")
        return v
```

### Logging Configuration with Loguru

**src/homelab/utils/logging.py**
```python
import sys
from typing import Dict, Any
from loguru import logger
from pathlib import Path

def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    structured: bool = True
) -> None:
    """Configure Loguru logging with structured output."""

    # Remove default handler
    logger.remove()

    # Console handler with rich formatting
    if structured:
        format_string = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    else:
        format_string = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}:{function}:{line}</cyan> | {message}"

    logger.add(
        sys.stdout,
        level=level,
        format=format_string,
        colorize=not structured,
        serialize=structured
    )

    # File handler with rotation
    if log_file:
        logger.add(
            log_file,
            level=level,
            format=format_string,
            rotation="10 MB",
            retention="1 month",
            serialize=True
        )

# Usage context manager
@contextmanager
def log_operation(operation: str, **kwargs: Any):
    """Context manager for logging operations with structured data."""
    logger.info(f"Starting {operation}", **kwargs)
    start_time = time.time()
    try:
        yield
        duration = time.time() - start_time
        logger.info(f"Completed {operation}", duration=duration, **kwargs)
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed {operation}", error=str(e), duration=duration, **kwargs)
        raise
```

## #### 4. Infrastructure as Code Implementation

### Pulumi Infrastructure Components

**infrastructure/cluster.py**
```python
from typing import Dict, Any, List
import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.apps.v1 import Deployment, DeploymentSpecArgs
from homelab.models.infrastructure import ClusterConfig
from homelab.utils.logging import logger, log_operation

class K3sCluster:
    """K3s cluster management with Pulumi."""

    def __init__(self, config: ClusterConfig) -> None:
        self.config = config
        self.provider = k8s.Provider(
            "k3s-provider",
            kubeconfig=str(config.kubeconfig_path)
        )

    def deploy_application(
        self,
        name: str,
        image: str,
        replicas: int = 1,
        port: int = 80,
        environment: Dict[str, str] = None
    ) -> Deployment:
        """Deploy application to K3s cluster."""

        with log_operation("deploy_application", name=name, image=image):
            return Deployment(
                name,
                spec=DeploymentSpecArgs(
                    replicas=replicas,
                    selector={"matchLabels": {"app": name}},
                    template={
                        "metadata": {"labels": {"app": name}},
                        "spec": {
                            "containers": [{
                                "name": name,
                                "image": image,
                                "ports": [{"containerPort": port}],
                                "env": [
                                    {"name": k, "value": v}
                                    for k, v in (environment or {}).items()
                                ]
                            }]
                        }
                    }
                ),
                opts=pulumi.ResourceOptions(provider=self.provider)
            )
```

### Ansible Integration with Molecule Testing

**ansible/roles/k3s/tasks/main.yml**
```yaml
---
- name: Install K3s on control node
  shell: |
    curl -sfL https://get.k3s.io | sh -s - server \
      --cluster-init \
      --node-name {{ inventory_hostname }} \
      --bind-address {{ ansible_default_ipv4.address }}
  when: node_type == "control"
  register: k3s_install

- name: Get node token
  slurp:
    src: /var/lib/rancher/k3s/server/node-token
  register: node_token
  when: node_type == "control"

- name: Install K3s on agent node
  shell: |
    curl -sfL https://get.k3s.io | K3S_URL=https://{{ hostvars[groups['control'][0]]['ansible_default_ipv4']['address'] }}:6443 \
    K3S_TOKEN={{ hostvars[groups['control'][0]]['node_token']['content'] | b64decode | trim }} \
    sh -s - agent --node-name {{ inventory_hostname }}
  when: node_type == "agent"
```

**molecule/default/molecule.yml**
```yaml
dependency:
  name: galaxy
driver:
  name: docker
platforms:
  - name: control-node
    image: ubuntu:22.04
    groups:
      - control
  - name: agent-node
    image: ubuntu:22.04
    groups:
      - agents
provisioner:
  name: ansible
  inventory:
    group_vars:
      control:
        node_type: control
      agents:
        node_type: agent
verifier:
  name: ansible
```

## #### 5. Testing Strategy Implementation

### pytest Configuration and Fixtures

**tests/conftest.py**
```python
import pytest
from typing import AsyncGenerator, Generator
from pathlib import Path
from homelab.models.infrastructure import ClusterConfig, KubernetesNode
from homelab.utils.logging import setup_logging
import asyncio

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def cluster_config() -> ClusterConfig:
    """Test cluster configuration."""
    return ClusterConfig(
        cluster_name="test-cluster",
        nodes=[
            KubernetesNode(
                name="control-node",
                ip_address="192.168.0.50",
                node_type="control"
            ),
            KubernetesNode(
                name="agent-node",
                ip_address="192.168.0.66",
                node_type="agent"
            )
        ],
        kubeconfig_path=Path("/tmp/test-kubeconfig")
    )

@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup logging for tests."""
    setup_logging(level="DEBUG", structured=True)
```

### Unit Test Examples

**tests/test_cluster.py**
```python
import pytest
from unittest.mock import Mock, patch
from homelab.models.infrastructure import ClusterConfig
from infrastructure.cluster import K3sCluster

class TestK3sCluster:
    """Test K3s cluster operations."""

    def test_cluster_initialization(self, cluster_config: ClusterConfig):
        """Test cluster initialization."""
        cluster = K3sCluster(cluster_config)
        assert cluster.config == cluster_config
        assert cluster.provider is not None

    @patch('pulumi_kubernetes.apps.v1.Deployment')
    def test_deploy_application(self, mock_deployment, cluster_config: ClusterConfig):
        """Test application deployment."""
        cluster = K3sCluster(cluster_config)

        deployment = cluster.deploy_application(
            name="test-app",
            image="nginx:latest",
            replicas=2,
            port=80,
            environment={"ENV": "test"}
        )

        mock_deployment.assert_called_once()
        call_args = mock_deployment.call_args
        assert call_args[0][0] == "test-app"  # name

    async def test_cluster_health_check(self, cluster_config: ClusterConfig):
        """Test cluster health monitoring."""
        cluster = K3sCluster(cluster_config)

        with patch.object(cluster, '_check_node_health', return_value=True):
            health = await cluster.health_check()
            assert health['status'] == 'healthy'
```

## #### 6. CI/CD Pipeline Implementation

### GitHub Actions Workflow

**.github/workflows/ci.yml**
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"

jobs:
  quality-checks:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Install uv
      uses: astral-sh/setup-uv@v2
      with:
        version: "latest"

    - name: Set up Python
      run: uv python install ${{ env.PYTHON_VERSION }}

    - name: Install dependencies
      run: uv sync --all-extras

    - name: Run ruff linting
      run: uv run ruff check .

    - name: Run ruff formatting
      run: uv run ruff format --check .

    - name: Run mypy type checking
      run: uv run mypy src/

    - name: Run pytest
      run: uv run pytest --cov --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3

  ansible-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Install Ansible and Molecule
      run: |
        pip install ansible molecule[docker]

    - name: Run Molecule tests
      run: |
        cd ansible
        molecule test

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Run Bandit security linter
      run: |
        pip install bandit[toml]
        bandit -r src/ -f json -o bandit-report.json

    - name: Run Safety check
      run: |
        pip install safety
        safety check --json --output safety-report.json

  documentation:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v4

    - name: Install uv
      uses: astral-sh/setup-uv@v2

    - name: Build documentation
      run: |
        uv sync --all-extras
        uv run mkdocs build

    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./site
```

### Pre-commit Configuration

**.pre-commit-config.yaml**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.8
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-requests]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-c, pyproject.toml]

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: uv run pytest
        language: system
        pass_filenames: false
        always_run: true
```

### Makefile for Development Automation

**Makefile**
```makefile
.PHONY: help install dev-install test lint format type-check security-check clean docs serve-docs deploy

# Default target
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	uv sync --no-dev

dev-install: ## Install development dependencies
	uv sync --all-extras
	uv run pre-commit install

# Testing
test: ## Run all tests
	uv run pytest -v --cov=src --cov-report=html --cov-report=term-missing

test-watch: ## Run tests in watch mode
	uv run pytest-watch -- -v

# Code Quality
lint: ## Run linting
	uv run ruff check .

format: ## Format code
	uv run ruff format .

type-check: ## Run type checking
	uv run mypy src/

security-check: ## Run security checks
	uv run bandit -r src/
	uv run safety check

# Quality gates
quality: lint format type-check security-check test ## Run all quality checks

# Documentation
docs: ## Build documentation
	uv run mkdocs build

serve-docs: ## Serve documentation locally
	uv run mkdocs serve

# Deployment
deploy-dev: ## Deploy to development environment
	uv run homelab deploy dev --verbose

deploy-prod: ## Deploy to production environment
	uv run homelab deploy prod

# Utilities
clean: ## Clean build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov site
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Docker operations
docker-build: ## Build development container
	docker-compose -f docker-compose.dev.yml build

docker-up: ## Start development environment
	docker-compose -f docker-compose.dev.yml up -d

docker-down: ## Stop development environment
	docker-compose -f docker-compose.dev.yml down
```

## #### 7. Monitoring and Observability

### OpenTelemetry Integration

**src/homelab/observability/tracing.py**
```python
from typing import Optional, Dict, Any
from opentelemetry import trace, metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from loguru import logger

class ObservabilityManager:
    """Centralized observability management."""

    def __init__(
        self,
        service_name: str,
        service_version: str,
        otlp_endpoint: Optional[str] = None
    ) -> None:
        self.service_name = service_name
        self.service_version = service_version
        self.otlp_endpoint = otlp_endpoint

        self._setup_tracing()
        self._setup_metrics()

    def _setup_tracing(self) -> None:
        """Configure distributed tracing."""
        provider = TracerProvider(
            resource=Resource.create({
                "service.name": self.service_name,
                "service.version": self.service_version
            })
        )

        if self.otlp_endpoint:
            processor = BatchSpanProcessor(
                OTLPSpanExporter(endpoint=self.otlp_endpoint)
            )
            provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(__name__)

    def _setup_metrics(self) -> None:
        """Configure metrics collection."""
        reader = PrometheusMetricReader()
        provider = MeterProvider(metric_readers=[reader])
        metrics.set_meter_provider(provider)
        self.meter = metrics.get_meter(__name__)

        # Create common metrics
        self.request_counter = self.meter.create_counter(
            "requests_total",
            description="Total number of requests"
        )

        self.request_duration = self.meter.create_histogram(
            "request_duration_seconds",
            description="Request duration in seconds"
        )

# Usage decorator
def traced_operation(operation_name: str):
    """Decorator for automatic operation tracing."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(operation_name) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(operation_name) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
```

## #### 8. Security Implementation

### SSH Key Management System

**src/homelab/security/ssh_manager.py**
```python
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import subprocess
import asyncio
from dataclasses import dataclass
from homelab.models.infrastructure import KubernetesNode
from homelab.utils.logging import logger, log_operation

@dataclass
class SSHConnection:
    """SSH connection configuration."""
    host: str
    user: str
    key_path: Optional[Path] = None
    port: int = 22

class SSHKeyManager:
    """Automated SSH key management and validation."""

    def __init__(self, default_key_path: Path = Path.home() / ".ssh" / "id_rsa"):
        self.default_key_path = default_key_path
        self.connections: Dict[str, SSHConnection] = {}

    async def validate_connection(self, connection: SSHConnection) -> bool:
        """Validate SSH connection with key-based auth."""

        with log_operation("validate_ssh_connection", host=connection.host):
            try:
                cmd = [
                    "ssh",
                    "-o", "BatchMode=yes",
                    "-o", "ConnectTimeout=10",
                    "-o", "StrictHostKeyChecking=no",
                    f"-p", str(connection.port)
                ]

                if connection.key_path:
                    cmd.extend(["-i", str(connection.key_path)])

                cmd.append(f"{connection.user}@{connection.host}")
                cmd.append("echo 'SSH connection successful'")

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    logger.info("SSH validation successful", host=connection.host)
                    return True
                else:
                    logger.warning(
                        "SSH validation failed",
                        host=connection.host,
                        error=stderr.decode()
                    )
                    return False

            except Exception as e:
                logger.error("SSH validation error", host=connection.host, error=str(e))
                return False

    async def setup_passwordless_access(
        self,
        connection: SSHConnection,
        password: str
    ) -> bool:
        """Setup passwordless SSH access."""

        with log_operation("setup_passwordless_ssh", host=connection.host):
            try:
                # Generate key pair if not exists
                if not self.default_key_path.exists():
                    await self._generate_key_pair()

                # Copy public key to remote host
                pub_key_path = self.default_key_path.with_suffix(".pub")

                cmd = [
                    "sshpass", "-p", password,
                    "ssh-copy-id",
                    "-o", "StrictHostKeyChecking=no",
                    "-i", str(pub_key_path),
                    f"{connection.user}@{connection.host}"
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    logger.info("Passwordless SSH setup successful", host=connection.host)
                    return True
                else:
                    logger.error(
                        "Failed to setup passwordless SSH",
                        host=connection.host,
                        error=stderr.decode()
                    )
                    return False

            except Exception as e:
                logger.error("SSH setup error", host=connection.host, error=str(e))
                return False

    async def _generate_key_pair(self) -> None:
        """Generate SSH key pair."""
        cmd = [
            "ssh-keygen",
            "-t", "rsa",
            "-b", "4096",
            "-f", str(self.default_key_path),
            "-N", "",  # No passphrase
            "-C", "homelab-automation"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.communicate()

        if process.returncode == 0:
            logger.info("SSH key pair generated", path=self.default_key_path)
        else:
            raise RuntimeError("Failed to generate SSH key pair")
```

## #### 9. Error Handling and Resilience

### Retry and Circuit Breaker Patterns

**src/homelab/utils/resilience.py**
```python
from typing import Callable, Any, Type, Tuple, Optional
import asyncio
import time
from functools import wraps
from enum import Enum
from dataclasses import dataclass
from loguru import logger

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    timeout_seconds: int = 60
    expected_exception: Type[Exception] = Exception

class CircuitBreaker:
    """Circuit breaker implementation for resilience."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if self._should_attempt_call():
                try:
                    result = await func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.config.expected_exception as e:
                    self._on_failure()
                    raise
            else:
                raise CircuitOpenException("Circuit breaker is open")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if self._should_attempt_call():
                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.config.expected_exception as e:
                    self._on_failure()
                    raise
            else:
                raise CircuitOpenException("Circuit breaker is open")

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    def _should_attempt_call(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._is_timeout_expired():
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        else:  # HALF_OPEN
            return True

    def _on_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker opened", failure_count=self.failure_count)

    def _is_timeout_expired(self) -> bool:
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.config.timeout_seconds
        )

# Retry decorator with exponential backoff
def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Retry decorator with exponential backoff."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(
                            "Max retry attempts exceeded",
                            function=func.__name__,
                            attempt=attempt + 1,
                            error=str(e)
                        )
                        raise

                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    logger.warning(
                        "Retrying after failure",
                        function=func.__name__,
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e)
                    )
                    await asyncio.sleep(delay)

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(
                            "Max retry attempts exceeded",
                            function=func.__name__,
                            attempt=attempt + 1,
                            error=str(e)
                        )
                        raise

                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    logger.warning(
                        "Retrying after failure",
                        function=func.__name__,
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e)
                    )
                    time.sleep(delay)

            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
```

This comprehensive SDS provides a modern, production-ready foundation for the Smart Home K3s Lab Infrastructure project. The design incorporates current Python best practices, emphasizes developer experience optimization for GitHub Copilot Pro usage, and implements robust testing, monitoring, and security patterns suitable for a smart home environment.

The architecture supports the TDD approach with comprehensive testing frameworks, automated CI/CD pipelines, and structured logging throughout. The modular design allows for easy extension and maintenance while maintaining type safety and code quality standards.
