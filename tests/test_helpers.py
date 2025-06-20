#!/usr/bin/env python3
"""
Test utilities and helpers for the homelab test suite.
Provides common test patterns, assertions, and mock helpers.
"""

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from loguru import logger


class TestHelpers:
    """Collection of helper methods for testing."""

    @staticmethod
    def create_mock_subprocess_result(
        returncode: int = 0, stdout: str = "", stderr: str = ""
    ) -> Mock:
        """Create a mock subprocess.CompletedProcess result.

        Args:
            returncode: Process return code (0 for success)
            stdout: Standard output text
            stderr: Standard error text

        Returns:
            Mock object configured as subprocess result
        """
        # Arrange: Create mock with proper attributes
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = returncode
        mock_result.stdout = stdout
        mock_result.stderr = stderr
        mock_result.check_returncode = Mock()

        if returncode != 0:
            mock_result.check_returncode.side_effect = subprocess.CalledProcessError(
                returncode, ["test-command"], stdout, stderr
            )

        return mock_result

    @staticmethod
    def create_kubectl_mock_responses() -> dict[str, Mock]:
        """Create comprehensive kubectl command mock responses.

        Returns:
            Dictionary mapping kubectl commands to mock responses
        """
        # Arrange: Define common kubectl outputs
        kubectl_responses = {
            "get_pods_running": TestHelpers.create_mock_subprocess_result(
                stdout=json.dumps(
                    {
                        "items": [
                            {
                                "metadata": {"name": "supabase-postgres-0"},
                                "status": {
                                    "phase": "Running",
                                    "containerStatuses": [
                                        {"ready": True, "restartCount": 0}
                                    ],
                                },
                            }
                        ]
                    }
                )
            ),
            "get_pods_empty": TestHelpers.create_mock_subprocess_result(
                stdout=json.dumps({"items": []})
            ),
            "get_namespace_exists": TestHelpers.create_mock_subprocess_result(
                stdout="supabase   Active   5m"
            ),
            "get_namespace_not_found": TestHelpers.create_mock_subprocess_result(
                returncode=1, stderr="namespaces 'supabase' not found"
            ),
            "apply_success": TestHelpers.create_mock_subprocess_result(
                stdout="deployment.apps/test-deployment created"
            ),
            "delete_success": TestHelpers.create_mock_subprocess_result(
                stdout="deployment.apps 'test-deployment' deleted"
            ),
        }

        return kubectl_responses

    @staticmethod
    def create_test_kubeconfig(temp_dir: Path) -> Path:
        """Create a realistic test kubeconfig file.

        Args:
            temp_dir: Directory to create kubeconfig in

        Returns:
            Path to created kubeconfig file
        """
        kubeconfig_content = {
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [
                {
                    "cluster": {
                        "certificate-authority-data": "LS0tLS1CRUdJTi...",
                        "server": "https://192.168.0.50:6443",
                    },
                    "name": "homelab-cluster",
                }
            ],
            "contexts": [
                {
                    "context": {"cluster": "homelab-cluster", "user": "homelab-admin"},
                    "name": "homelab-context",
                }
            ],
            "current-context": "homelab-context",
            "users": [
                {
                    "name": "homelab-admin",
                    "user": {
                        "client-certificate-data": "LS0tLS1CRUdJTi...",
                        "client-key-data": "LS0tLS1CRUdJTi...",
                    },
                }
            ],
        }

        kubeconfig_path = temp_dir / "kubeconfig"
        kubeconfig_path.write_text(json.dumps(kubeconfig_content, indent=2))
        return kubeconfig_path

    @staticmethod
    def assert_command_called_with_args(
        mock_subprocess: Mock, expected_args: list[str]
    ) -> None:
        """Assert that subprocess was called with specific arguments.

        Args:
            mock_subprocess: Mocked subprocess.run
            expected_args: Expected command arguments
        """
        # Assert: Verify subprocess was called
        assert mock_subprocess.called, "subprocess.run was not called"

        # Get the actual call arguments
        actual_call = mock_subprocess.call_args
        actual_args = actual_call[0][0]  # First positional argument

        # Assert: Command arguments match
        assert (
            actual_args == expected_args
        ), f"Expected command: {expected_args}\nActual command: {actual_args}"

    @staticmethod
    def create_sample_device_data() -> list[dict[str, Any]]:
        """Create sample device discovery data for testing.

        Returns:
            List of device dictionaries for testing
        """
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
            {
                "ip": "192.168.0.100",
                "hostname": "smart-switch",
                "mac_address": "99:88:77:66:55:44",
                "device_type": "network_switch",
                "services": ["snmp", "http"],
                "manufacturer": "TP-Link",
            },
        ]

    @staticmethod
    def create_test_backup_structure(temp_dir: Path) -> Path:
        """Create a test backup directory structure.

        Args:
            temp_dir: Base temporary directory

        Returns:
            Path to backup directory
        """
        backup_dir = temp_dir / "test_backup_20241215_120000"
        backup_dir.mkdir(parents=True)

        # Create subdirectories
        (backup_dir / "k3s").mkdir()
        (backup_dir / "supabase").mkdir()
        (backup_dir / "home_assistant").mkdir()
        (backup_dir / "configurations").mkdir()

        # Create sample files
        (backup_dir / "k3s" / "etcd-snapshot.db").write_text("mock etcd data")
        (backup_dir / "supabase" / "postgres_dump.sql").write_text("mock sql dump")
        (backup_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "timestamp": "2024-12-15T12:00:00Z",
                    "components": ["k3s", "supabase", "home_assistant"],
                    "status": "completed",
                }
            )
        )

        return backup_dir

    @staticmethod
    def create_performance_test_data() -> dict[str, Any]:
        """Create sample performance monitoring data.

        Returns:
            Dictionary with performance metrics
        """
        return {
            "cpu_usage": 25.5,
            "memory_usage": 65.2,
            "disk_usage": 78.1,
            "network_rx_bytes": 1024000,
            "network_tx_bytes": 512000,
            "pod_count": 15,
            "node_count": 2,
            "service_count": 8,
        }


class LogCapture:
    """Utility for capturing and asserting log messages in tests."""

    def __init__(self):
        """Initialize log capture."""
        self.captured_logs: list[dict[str, Any]] = []
        self.handler_id = None

    def start_capture(self) -> None:
        """Start capturing log messages."""

        def capture_handler(record):
            self.captured_logs.append(
                {
                    "level": record["level"].name,
                    "message": record["message"],
                    "function": record["function"],
                    "line": record["line"],
                }
            )

        self.handler_id = logger.add(capture_handler)

    def stop_capture(self) -> None:
        """Stop capturing log messages."""
        if self.handler_id:
            logger.remove(self.handler_id)
            self.handler_id = None

    def assert_log_contains(self, level: str, message_substring: str) -> None:
        """Assert that a log message was captured.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            message_substring: Substring to search for in messages
        """
        matching_logs = [
            log
            for log in self.captured_logs
            if log["level"] == level and message_substring in log["message"]
        ]

        assert matching_logs, (
            f"No {level} log found containing '{message_substring}'\n"
            f"Captured logs: {self.captured_logs}"
        )

    def assert_no_errors(self) -> None:
        """Assert that no ERROR level logs were captured."""
        error_logs = [log for log in self.captured_logs if log["level"] == "ERROR"]
        assert not error_logs, f"Unexpected ERROR logs found: {error_logs}"

    def get_logs_by_level(self, level: str) -> list[dict[str, Any]]:
        """Get all captured logs for a specific level.

        Args:
            level: Log level to filter by

        Returns:
            List of log records for the specified level
        """
        return [log for log in self.captured_logs if log["level"] == level]


class MockFileSystem:
    """Mock file system operations for testing."""

    def __init__(self):
        """Initialize mock file system."""
        self.files: dict[str, str] = {}
        self.directories: set[str] = set()

    def add_file(self, path: str, content: str) -> None:
        """Add a file to the mock file system.

        Args:
            path: File path
            content: File content
        """
        self.files[path] = content
        # Ensure parent directories exist
        parent = str(Path(path).parent)
        self.directories.add(parent)

    def add_directory(self, path: str) -> None:
        """Add a directory to the mock file system.

        Args:
            path: Directory path
        """
        self.directories.add(path)

    def file_exists(self, path: str) -> bool:
        """Check if file exists in mock file system.

        Args:
            path: File path to check

        Returns:
            True if file exists
        """
        return path in self.files

    def directory_exists(self, path: str) -> bool:
        """Check if directory exists in mock file system.

        Args:
            path: Directory path to check

        Returns:
            True if directory exists
        """
        return path in self.directories

    def read_file(self, path: str) -> str:
        """Read file content from mock file system.

        Args:
            path: File path to read

        Returns:
            File content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]


class AAATester:
    """Base class for Arrange-Act-Assert testing pattern.

    Provides common testing utilities and enforces AAA structure
    for consistent and readable test methods.
    """

    def setup_method(self) -> None:
        """Set up test method with logging."""
        logger.info(f"Starting test: {self.__class__.__name__}")

    def teardown_method(self) -> None:
        """Clean up after test method."""
        logger.info(f"Completed test: {self.__class__.__name__}")

    def assert_success_result(
        self, result: dict[str, Any], expected_keys: list[str] = None
    ) -> None:
        """Assert a successful operation result.

        Args:
            result: Operation result dictionary
            expected_keys: Expected keys in result (optional)
        """
        assert isinstance(result, dict), "Result must be a dictionary"
        assert (
            result.get("success") is True
        ), f"Operation failed: {result.get('error', 'Unknown error')}"

        if expected_keys:
            for key in expected_keys:
                assert key in result, f"Expected key '{key}' not found in result"

    def assert_failure_result(
        self, result: dict[str, Any], expected_error: str = None
    ) -> None:
        """Assert a failed operation result.

        Args:
            result: Operation result dictionary
            expected_error: Expected error message substring (optional)
        """
        assert isinstance(result, dict), "Result must be a dictionary"
        assert result.get("success") is False, "Operation should have failed"
        assert "error" in result, "Failed result must contain error message"

        if expected_error:
            assert (
                expected_error.lower() in result["error"].lower()
            ), f"Expected error '{expected_error}' not found in '{result['error']}'"
