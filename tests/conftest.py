#!/usr/bin/env python3
"""
Comprehensive test configuration and fixtures for homelab project.
Provides fixtures, utilities, and setup for all test categories.
"""

import asyncio
import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from typing import TypeVar, Type, Optional

import pytest
from loguru import logger
from dotenv import load_dotenv

# Add project directories to path for testing
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "infrastructure"))

# Load .env file
logger.info("Attempting to load .env file...")
if load_dotenv():
    logger.info(".env file loaded successfully.")
else:
    logger.warning(".env file not found. Proceeding with environment variables or defaults.")


# ============================================================================
# Logging Configuration
# ============================================================================


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Configure Loguru for test execution with structured logging."""
    # Remove default handlers
    logger.remove()

    # Add stderr handler for test output
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        level="DEBUG",
        colorize=True,
    )

    # Add file handler for detailed test logs
    log_dir = Path("tests/logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "test_run_{time:YYYY-MM-DD_HH-mm-ss}.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        serialize=False,
        enqueue=True,
    )

    # Add JSON handler for structured logs
    logger.add(
        log_dir / "test_structured_{time:YYYY-MM-DD_HH-mm-ss}.json",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        level="INFO",
        serialize=True,
        rotation="10 MB",
        retention="7 days",
    )

    logger.info("🧪 Test logging configuration complete")


@pytest.fixture
def test_logger():
    """Provide logger instance for tests."""
    return logger


# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ============================================================================
# File System and Path Fixtures
# ============================================================================


@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def project_root():
    """Provide project root path."""
    return PROJECT_ROOT


@pytest.fixture
def test_data_dir():
    """Provide test data directory."""
    data_dir = Path(__file__).parent / "fixtures"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture
def mock_kubeconfig(temp_dir):
    """Create mock kubeconfig file for testing."""
    kubeconfig_content = """
apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://192.168.0.50:6443
    certificate-authority-data: LS0tLS1CRUdJTi...
  name: homelab-cluster
contexts:
- context:
    cluster: homelab-cluster
    user: homelab-admin
  name: homelab-context
current-context: homelab-context
users:
- name: homelab-admin
  user:
    client-certificate-data: LS0tLS1CRUdJTi...
    client-key-data: LS0tLS1CRUdJTi...
"""
    kubeconfig_path = temp_dir / "kubeconfig"
    kubeconfig_path.write_text(kubeconfig_content.strip())
    return kubeconfig_path


# ============================================================================
# Environment and Configuration Fixtures
# ============================================================================

T = TypeVar('T')

def get_env_var(name: str, default: Optional[T] = None, cast: Optional[Type[T]] = None) -> Optional[T]:
    """
    Retrieves an environment variable with optional casting and default value.
    Logs warnings if casting fails or variable is not found and no default is provided.
    If cast is not provided but default is, infers cast from type(default).
    Handles ValueError and TypeError during casting.
    """
    value = os.getenv(name)
    if value is None:
        if default is None:
            logger.warning(f"Environment variable {name} not found and no default value provided.")
        return default

    cast_to = cast
    if cast_to is None and default is not None:
        cast_to = type(default)

    if cast_to:
        try:
            return cast_to(value)  # type: ignore[call-arg]
        except (ValueError, TypeError):
            logger.warning(f"Could not cast environment variable {name}='{value}' to {cast_to}. Returning default.")
            return default
    return value if cast_to is None else default


@pytest.fixture
def mock_environment():
    """Provide mock environment variables for testing."""
    env_vars = {
        "KUBECONFIG": "/tmp/test-kubeconfig",
        "SUPABASE_POSTGRES_PASSWORD": "test-password",
        "SUPABASE_JWT_SECRET": "test-jwt-secret-32-characters-long",
        "HOME": "/tmp/test-home",
        "USER": "test-user",
        "WSL_DISTRO_NAME": "Ubuntu",
        "WSL2_HOST_IP": "192.168.0.50",
        "WSL2_IP": "192.168.0.51",
    }

    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def homelab_config():
    """Provide test homelab configuration."""
    return {
        "cluster": {
            "name": "homelab-test",
            "control_node_ip": "192.168.0.50",
            "agent_node_ip": "192.168.0.66",
            "kubeconfig_path": "/tmp/test-kubeconfig",
        },
        "supabase": {
            "namespace": "supabase",
            "postgres_password": "test-password",
            "jwt_secret": "test-jwt-secret-32-characters-long",
        },
        "networking": {
            "home_assistant_url": "http://192.168.0.41:8123",
            "mqtt_broker": "192.168.0.41:1883",
        },
    }


# ============================================================================
# Mock External Dependencies
# ============================================================================

from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs # Added for waiting

@pytest.fixture(scope="session")
def postgres_container(test_logger) -> Generator[DockerContainer, None, None]: # Renamed logger to test_logger to match existing fixture
    test_logger.info("Starting PostgreSQL container for testing...")
    container = DockerContainer("postgres:13")
    container.with_env("POSTGRES_PASSWORD", "test")
    container.with_exposed_ports(5432)
    try:
        container.start()
        wait_for_logs(container, "database system is ready to accept connections", timeout=30)
        test_logger.info(f"PostgreSQL container started on port {container.get_exposed_port(5432)}")
        yield container
    finally:
        test_logger.info("Stopping PostgreSQL container...")
        container.stop()
        test_logger.info("PostgreSQL container stopped.")

@pytest.fixture(scope="session")
def mqtt_container(test_logger) -> Generator[DockerContainer, None, None]:
    test_logger.info("Starting MQTT container (eclipse-mosquitto)...")
    container = DockerContainer("eclipse-mosquitto:latest")
    container.with_exposed_ports(1883)
    try:
        container.start()
        # Mosquitto version 1.x log: "mosquitto version x.x.x (build date ...) starting"
        # Mosquitto version 2.x log: "mosquitto version x.x.x running"
        wait_for_logs(container, r"mosquitto version .* (starting|running)", timeout=20)
        test_logger.info(f"MQTT container started on port {container.get_exposed_port(1883)}")
        yield container
    finally:
        test_logger.info("Stopping MQTT container...")
        container.stop()
        test_logger.info("MQTT container stopped.")

@pytest.fixture(scope="session")
def rabbitmq_container(test_logger) -> Generator[DockerContainer, None, None]:
    test_logger.info("Starting RabbitMQ container...")
    container = DockerContainer("rabbitmq:3-management-alpine")
    container.with_exposed_ports(5672, 15672) # 5672 for AMQP, 15672 for management
    try:
        container.start()
        # Default RabbitMQ log line: " completed with 0 plugins." or "Starting RabbitMQ"
        # More specific: "Server startup complete"
        wait_for_logs(container, "Server startup complete", timeout=30)
        test_logger.info(f"RabbitMQ container started on AMQP port {container.get_exposed_port(5672)}")
        yield container
    finally:
        test_logger.info("Stopping RabbitMQ container...")
        container.stop()
        test_logger.info("RabbitMQ container stopped.")

@pytest.fixture(scope="session")
def echo_websocket_server_container(test_logger) -> Generator[DockerContainer, None, None]:
    test_logger.info("Starting echo WebSocket server container (jmalloc/echo-server)...")
    # This server echoes back whatever it receives. Listens on port 8080.
    container = DockerContainer("jmalloc/echo-server:latest")
    container.with_exposed_ports(8080)
    try:
        container.start()
        # jmalloc/echo-server logs "Listening on port 8080"
        wait_for_logs(container, "Listening on port 8080", timeout=20)
        test_logger.info(f"Echo WebSocket server container started on port {container.get_exposed_port(8080)}")
        yield container
    finally:
        test_logger.info("Stopping echo WebSocket server container...")
        container.stop()
        test_logger.info("Echo WebSocket server container stopped.")

@pytest.fixture(scope="session")
def httpbin_container(test_logger) -> Generator[DockerContainer, None, None]:
    test_logger.info("Starting httpbin container (kennethreitz/httpbin)...")
    container = DockerContainer("kennethreitz/httpbin:latest")
    container.with_exposed_ports(80) # Default httpbin port
    try:
        container.start()
        # Httpbin doesn't have a very specific "ready" log line quickly,
        # but it starts fast. Check for a common gunicorn log.
        wait_for_logs(container, "Listening at: http://0.0.0.0:80", timeout=20)
        test_logger.info(f"httpbin container started on port {container.get_exposed_port(80)}")
        yield container
    finally:
        test_logger.info("Stopping httpbin container...")
        container.stop()
        test_logger.info("httpbin container stopped.")

# ============================================================================
# Higher-Level Test Configuration Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def postgres_test_config(postgres_container: DockerContainer) -> dict:
    return {
        "host": postgres_container.get_container_host_ip(),
        "port": int(postgres_container.get_exposed_port(5432)),
        "database": "postgres",  # Default database
        "user": "postgres",      # Default user
        "password": "test"       # Password set in postgres_container fixture
    }

@pytest.fixture(scope="session")
def mqtt_test_config(mqtt_container: DockerContainer) -> dict:
    return {
        "broker": mqtt_container.get_container_host_ip(),
        "port": int(mqtt_container.get_exposed_port(1883)),
    }

@pytest.fixture(scope="session")
def rabbitmq_test_config(rabbitmq_container: DockerContainer) -> dict:
    return {
        "host": rabbitmq_container.get_container_host_ip(),
        "port": int(rabbitmq_container.get_exposed_port(5672)),
    }

@pytest.fixture(scope="session")
def echo_websocket_test_endpoint(echo_websocket_server_container: DockerContainer) -> str:
    host = echo_websocket_server_container.get_container_host_ip()
    port = echo_websocket_server_container.get_exposed_port(8080)
    return f"ws://{host}:{port}"

@pytest.fixture(scope="session")
def httpbin_test_base_url(httpbin_container: DockerContainer) -> str:
    host = httpbin_container.get_container_host_ip()
    port = httpbin_container.get_exposed_port(80)
    return f"http://{host}:{port}"


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0, stdout="success", stderr="", check=True
        )
        yield mock_run


@pytest.fixture
def mock_async_subprocess():
    """Mock async subprocess calls."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"success", b""))
        mock_process.wait = AsyncMock(return_value=0)
        mock_exec.return_value = mock_process
        yield mock_exec


@pytest.fixture
def mock_kubernetes_api():
    """Mock Kubernetes API calls."""
    with patch("kubernetes.client.ApiClient") as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_file_operations():
    """Mock file system operations."""
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("pathlib.Path.write_text") as mock_write,
        patch("pathlib.Path.read_text") as mock_read,
    ):
        mock_exists.return_value = True
        mock_mkdir.return_value = None
        mock_write.return_value = None
        mock_read.return_value = "mock file content"

        yield {
            "exists": mock_exists,
            "mkdir": mock_mkdir,
            "write_text": mock_write,
            "read_text": mock_read,
        }


@pytest.fixture
def mock_network_operations():
    """Mock network operations (ping, socket, HTTP requests)."""
    with (
        patch("socket.gethostbyname") as mock_gethostbyname,
        patch("socket.gethostname") as mock_gethostname,
        patch("requests.get") as mock_requests_get,
    ):
        mock_gethostbyname.return_value = "192.168.0.51"
        mock_gethostname.return_value = "homelab-test"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_requests_get.return_value = mock_response

        yield {
            "gethostbyname": mock_gethostbyname,
            "gethostname": mock_gethostname,
            "requests_get": mock_requests_get,
        }


@pytest.fixture
def mock_psutil():
    """Mock psutil system monitoring calls."""
    with (
        patch("psutil.cpu_percent") as mock_cpu,
        patch("psutil.virtual_memory") as mock_memory,
        patch("psutil.disk_usage") as mock_disk,
    ):
        mock_cpu.return_value = 25.0

        mock_memory_obj = Mock()
        mock_memory_obj.percent = 60.0
        mock_memory_obj.total = 8 * 1024**3  # 8GB
        mock_memory_obj.available = 3 * 1024**3  # 3GB
        mock_memory.return_value = mock_memory_obj

        mock_disk_obj = Mock()
        mock_disk_obj.percent = 45.0
        mock_disk_obj.total = 500 * 1024**3  # 500GB
        mock_disk_obj.free = 275 * 1024**3  # 275GB
        mock_disk.return_value = mock_disk_obj

        yield {
            "cpu_percent": mock_cpu,
            "virtual_memory": mock_memory,
            "disk_usage": mock_disk,
        }


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_kubectl_output():
    """Provide sample kubectl command outputs."""
    return {
        "get_pods": """
NAME                    READY   STATUS    RESTARTS   AGE
supabase-postgres-0     1/1     Running   0          5m
supabase-gotrue-123     1/1     Running   0          5m
supabase-storage-456    1/1     Running   0          5m
""",
        "get_nodes": """
NAME           STATUS   ROLES                  AGE   VERSION
control-node   Ready    control-plane,master   5d    v1.28.4+k3s1
agent-node     Ready    <none>                 5d    v1.28.4+k3s1
""",
        "get_services": """
NAME                TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
supabase-postgres   ClusterIP   10.43.200.100   <none>        5432/TCP   5m
supabase-kong       NodePort    10.43.200.101   <none>        8000:30000/TCP   5m
""",
    }


@pytest.fixture
def sample_device_discovery():
    """Provide sample device discovery data."""
    return [
        {
            "ip": "192.168.0.41",
            "hostname": "homeassistant",
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "device_type": "home_assistant",
            "services": ["http", "mqtt"],
            "manufacturer": "Home Assistant",
        },
        {
            "ip": "192.168.0.66",
            "hostname": "jetson-orin",
            "mac_address": "11:22:33:44:55:66",
            "device_type": "kubernetes_node",
            "services": ["ssh", "k3s"],
            "manufacturer": "NVIDIA",
        },
    ]


# ============================================================================
# Performance Optimization Fixtures
# ============================================================================


@pytest.fixture
def sample_optimization_recommendations():
    """Provide sample performance optimization recommendations."""
    return [
        {
            "category": "Memory",
            "priority": "HIGH",
            "description": "Optimize PostgreSQL memory settings",
            "command": 'kubectl patch configmap postgres-config -p \'{"data":{"shared_buffers":"256MB"}}\'',
            "expected_improvement": "20% query performance improvement",
        },
        {
            "category": "Network",
            "priority": "MEDIUM",
            "description": "Enable direct routing for CNI",
            "command": 'kubectl patch configmap flannel-cfg --patch \'{"data":{"directrouting":"true"}}\'',
            "expected_improvement": "Reduced network latency",
        },
    ]


# ============================================================================
# Test Utilities
# ============================================================================


def create_mock_process(returncode: int = 0, stdout: str = "", stderr: str = ""):
    """Create a mock subprocess result."""
    mock_result = Mock()
    mock_result.returncode = returncode
    mock_result.stdout = stdout
    mock_result.stderr = stderr
    return mock_result


def create_mock_async_process(
    returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""
):
    """Create a mock async subprocess."""
    mock_process = Mock()
    mock_process.returncode = returncode
    mock_process.communicate = AsyncMock(return_value=(stdout, stderr))
    mock_process.wait = AsyncMock(return_value=returncode)
    return mock_process


@pytest.fixture
def assert_log_contains(caplog):
    """Utility to assert log messages contain specific text."""

    def _assert_log_contains(level: str, message: str):
        """Check if log contains message at specified level."""
        for record in caplog.records:
            if record.levelname == level and message in record.message:
                return True
        return False

    return _assert_log_contains


@pytest.fixture
def makefile_framework(project_root: Path):
    """Create Makefile testing framework instance."""
    # Import here to avoid circular imports
    from tests.makefile.test_makefile_comprehensive import MakefileTestFramework

    return MakefileTestFramework(project_root)


@pytest.fixture
def log_capture():
    """Fixture to capture Loguru logs."""
    from tests.test_helpers import LogCapture as LogCaptureHelper

    capture = LogCaptureHelper()
    capture.start_capture()
    yield capture
    capture.stop_capture()
