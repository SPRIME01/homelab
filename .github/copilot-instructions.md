# Smart Home K3s Laboratory - Copilot Instructions

## Project Architecture & Context

This is a comprehensive smart home laboratory built on Kubernetes (K3s) with infrastructure-as-code practices. The system integrates IoT devices, home automation, and distributed AI inference across multiple nodes.

**Network Topology:**
- Control Node: Windows 11 Pro (192.168.0.50) running WSL2 Ubuntu (192.168.0.51)
- Agent Node: NVIDIA Jetson AGX Orin (192.168.0.66)
- Home Assistant Yellow: MQTT broker and IoT gateway (192.168.0.41)
- Dual-IP networking requires special handling for K3s API server binding and external access

## Development Standards & Technologies

**Python Development (Primary Language):**
- Always use Python 3.11+ features and type hints with strict typing
- Use `from typing import` imports for type annotations, prefer built-in generics where available
- All functions must have complete type annotations including return types
- Use Pydantic V2 models for data validation with `Field()` descriptors
- Implement proper error handling with custom exception classes that inherit from built-in exceptions
- Use Loguru for all logging with structured JSON output: `logger.info("message", key=value)`
- CLI applications must use Typer with Rich for formatting and progress indicators

**Code Quality & Testing:**
- Follow TDD approach - write tests first, then implementation
- Use pytest for all testing with async support via pytest-asyncio
- Create fixtures in `conftest.py` for reusable test components
- Mock external dependencies (K8s API, MQTT broker, SSH connections) in tests
- Use Ruff for linting/formatting with line length 88 characters
- All code must pass MyPy strict mode type checking
- Use pre-commit hooks for automated quality checks

**Infrastructure as Code Patterns:**
- Pulumi resources should use proper typing with `pulumi_kubernetes` imports
- Ansible playbooks must be idempotent with proper error handling and rollback capabilities
- K3s configurations must account for WSL2 dual-IP networking with `bind-address` and `advertise-address` settings
- All infrastructure code should include comprehensive logging and state validation
- Use resource tags and labels consistently for organization and cleanup

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

**Error Handling & Observability:**
- Use structured logging with correlation IDs for request tracing
- Implement comprehensive error handling with proper exception chaining
- Include performance metrics collection using OpenTelemetry patterns
- All long-running operations should include progress reporting and cancellation support

**AI & Machine Learning Integration:**
- LocalAI deployments should leverage Jetson AGX Orin GPU capabilities
- Model serving should include proper resource management and scaling
- Inference requests should include proper timeout and fallback mechanisms
- Use VectorDB for embedding storage with proper indexing strategies

## Code Examples & Patterns

When generating code, prefer these patterns:

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
