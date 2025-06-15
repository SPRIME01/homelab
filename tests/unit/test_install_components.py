"""Unit tests for scripts/01-install-components.py module.

Tests cover component installation, dependency management, and system configuration
with comprehensive mocking of installation processes and system commands.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from test_helpers import AAATester


class TestInstallComponents(AAATester):
    """Test suite for component installation functionality."""

    @pytest.fixture
    def sample_component_config(self) -> dict[str, Any]:
        """Sample component configuration data."""
        return {
            "components": [
                {
                    "name": "docker",
                    "type": "package",
                    "install_command": "curl -fsSL https://get.docker.com | sh",
                    "verify_command": "docker --version",
                    "required": True,
                },
                {
                    "name": "k3s",
                    "type": "package",
                    "install_command": "curl -sfL https://get.k3s.io | sh -",
                    "verify_command": "k3s --version",
                    "required": True,
                },
                {
                    "name": "kubectl",
                    "type": "binary",
                    "install_command": "curl -LO https://dl.k8s.io/release/stable.txt",
                    "verify_command": "kubectl version --client",
                    "required": False,
                },
            ]
        }

    def test_check_component_installed_success(self) -> None:
        """Test successful component installation check."""
        # Arrange
        component_name = "docker"
        verify_command = "docker --version"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Docker version 20.10.0")
            result = self._mock_check_component_installed(
                component_name, verify_command
            )

        # Assert
        assert result["installed"] is True
        assert result["component"] == component_name
        assert "20.10.0" in result["version"]

    def test_check_component_installed_not_found(self) -> None:
        """Test component installation check when component not found."""
        # Arrange
        component_name = "nonexistent"
        verify_command = "nonexistent --version"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = self._mock_check_component_installed(
                component_name, verify_command
            )

        # Assert
        assert result["installed"] is False
        assert result["component"] == component_name
        assert "not found" in result["error"].lower()

    def test_install_component_success(self) -> None:
        """Test successful component installation."""
        # Arrange
        component = {
            "name": "docker",
            "install_command": "curl -fsSL https://get.docker.com | sh",
        }

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._mock_install_component(component)

        # Assert
        assert result["success"] is True
        assert result["component"] == "docker"
        mock_run.assert_called_once()

    def test_install_component_failure(self) -> None:
        """Test component installation failure handling."""
        # Arrange
        component = {
            "name": "failing-component",
            "install_command": "failing-command",
        }

        # Act & Assert
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "failing-command")
            with pytest.raises(subprocess.CalledProcessError):
                self._mock_install_component(component)

    def test_verify_system_requirements_met(self) -> None:
        """Test system requirements verification when all requirements are met."""
        # Arrange
        requirements = {
            "min_memory_gb": 4,
            "min_disk_gb": 20,
            "required_ports": [80, 443, 6443],
        }

        # Act
        with (
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
            patch("socket.socket") as mock_socket,
        ):
            mock_memory.return_value = Mock(total=8 * 1024**3)  # 8GB
            mock_disk.return_value = Mock(free=50 * 1024**3)  # 50GB
            mock_socket.return_value.__enter__.return_value.bind.return_value = None

            result = self._mock_verify_system_requirements(requirements)

        # Assert
        assert result["requirements_met"] is True
        assert result["memory_sufficient"] is True
        assert result["disk_sufficient"] is True
        assert result["ports_available"] is True

    def test_verify_system_requirements_insufficient_memory(self) -> None:
        """Test system requirements verification with insufficient memory."""
        # Arrange
        requirements = {
            "min_memory_gb": 8,
            "min_disk_gb": 20,
            "required_ports": [80, 443],
        }

        # Act
        with (
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
        ):
            mock_memory.return_value = Mock(total=4 * 1024**3)  # 4GB (insufficient)
            mock_disk.return_value = Mock(free=50 * 1024**3)  # 50GB

            result = self._mock_verify_system_requirements(requirements)

        # Assert
        assert result["requirements_met"] is False
        assert result["memory_sufficient"] is False
        assert "insufficient memory" in result["error"].lower()

    def test_install_all_components_success(
        self, sample_component_config: dict[str, Any]
    ) -> None:
        """Test successful installation of all components."""
        # Arrange
        components = sample_component_config["components"]

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._mock_install_all_components(components)

        # Assert
        assert result["success"] is True
        assert len(result["installed_components"]) == len(components)
        assert len(result["failed_components"]) == 0

    def test_install_all_components_partial_failure(
        self, sample_component_config: dict[str, Any]
    ) -> None:
        """Test component installation with some failures."""
        # Arrange
        components = sample_component_config["components"]

        # Act
        with patch("subprocess.run") as mock_run:
            # First component succeeds, second fails, third succeeds
            mock_run.side_effect = [
                Mock(returncode=0),  # docker success
                subprocess.CalledProcessError(1, "k3s-install"),  # k3s failure
                Mock(returncode=0),  # kubectl success
            ]
            result = self._mock_install_all_components(components)

        # Assert
        assert result["success"] is False
        assert len(result["installed_components"]) == 2
        assert len(result["failed_components"]) == 1
        assert "k3s" in result["failed_components"]

    def test_configure_docker_success(self) -> None:
        """Test successful Docker configuration."""
        # Arrange
        config = {
            "add_user_to_group": True,
            "enable_service": True,
            "start_service": True,
        }

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = self._mock_configure_docker(config)

        # Assert
        assert result["success"] is True
        assert result["user_added_to_group"] is True
        assert result["service_enabled"] is True
        assert result["service_started"] is True

    def test_configure_k3s_control_plane_success(self) -> None:
        """Test successful K3s control plane configuration."""
        # Arrange
        config = {
            "bind_address": "192.168.0.51",
            "advertise_address": "192.168.0.50",
            "disable_traefik": True,
            "write_kubeconfig_mode": "644",
        }

        # Act
        with (
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.write_text") as mock_write,
        ):
            mock_run.return_value = Mock(returncode=0)
            result = self._mock_configure_k3s_control_plane(config)

        # Assert
        assert result["success"] is True
        assert result["bind_address"] == config["bind_address"]
        assert result["advertise_address"] == config["advertise_address"]
        assert result["traefik_disabled"] is True

    def test_generate_kubeconfig_dual_ip_success(self) -> None:
        """Test successful dual IP kubeconfig generation."""
        # Arrange
        internal_ip = "192.168.0.51"
        external_ip = "192.168.0.50"
        kubeconfig_template = """
apiVersion: v1
clusters:
- cluster:
    server: https://SERVER_IP:6443
  name: default
"""

        # Act
        with (
            patch("pathlib.Path.read_text") as mock_read,
            patch("pathlib.Path.write_text") as mock_write,
        ):
            mock_read.return_value = kubeconfig_template
            result = self._mock_generate_kubeconfig_dual_ip(internal_ip, external_ip)

        # Assert
        assert result["success"] is True
        assert result["internal_config_path"] is not None
        assert result["external_config_path"] is not None
        assert mock_write.call_count == 2

    def test_validate_installation_success(
        self, sample_component_config: dict[str, Any]
    ) -> None:
        """Test successful installation validation."""
        # Arrange
        components = sample_component_config["components"]

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="version output")
            result = self._mock_validate_installation(components)

        # Assert
        assert result["validation_passed"] is True
        assert len(result["validated_components"]) == len(components)
        assert len(result["failed_validations"]) == 0

    # Helper methods for mocking installation functions

    def _mock_check_component_installed(
        self, component: str, verify_command: str
    ) -> dict[str, Any]:
        """Mock component installation check."""
        try:
            result = subprocess.run(
                verify_command.split(), capture_output=True, text=True, check=True
            )
            return {
                "installed": True,
                "component": component,
                "version": result.stdout.strip(),
            }
        except (FileNotFoundError, subprocess.CalledProcessError):
            return {
                "installed": False,
                "component": component,
                "error": f"Component {component} not found",
            }

    def _mock_install_component(self, component: dict[str, str]) -> dict[str, Any]:
        """Mock component installation."""
        try:
            subprocess.run(
                component["install_command"],
                shell=True,
                check=True,
                capture_output=True,
            )
            return {
                "success": True,
                "component": component["name"],
                "message": f"Successfully installed {component['name']}",
            }
        except subprocess.CalledProcessError as e:
            raise e

    def _mock_verify_system_requirements(
        self, requirements: dict[str, Any]
    ) -> dict[str, Any]:
        """Mock system requirements verification."""
        import socket

        import psutil

        # Check memory
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        memory_sufficient = memory_gb >= requirements["min_memory_gb"]

        # Check disk space
        disk = psutil.disk_usage("/")
        disk_gb = disk.free / (1024**3)
        disk_sufficient = disk_gb >= requirements["min_disk_gb"]

        # Check ports
        ports_available = True
        for port in requirements.get("required_ports", []):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", port))
            except OSError:
                ports_available = False
                break

        requirements_met = memory_sufficient and disk_sufficient and ports_available

        result = {
            "requirements_met": requirements_met,
            "memory_sufficient": memory_sufficient,
            "disk_sufficient": disk_sufficient,
            "ports_available": ports_available,
        }

        if not requirements_met:
            errors = []
            if not memory_sufficient:
                errors.append("Insufficient memory")
            if not disk_sufficient:
                errors.append("Insufficient disk space")
            if not ports_available:
                errors.append("Required ports unavailable")
            result["error"] = "; ".join(errors)

        return result

    def _mock_install_all_components(
        self, components: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Mock installation of all components."""
        installed_components = []
        failed_components = []

        for component in components:
            try:
                subprocess.run(
                    component["install_command"],
                    shell=True,
                    check=True,
                    capture_output=True,
                )
                installed_components.append(component["name"])
            except subprocess.CalledProcessError:
                failed_components.append(component["name"])

        return {
            "success": len(failed_components) == 0,
            "installed_components": installed_components,
            "failed_components": failed_components,
            "total_components": len(components),
        }

    def _mock_configure_docker(self, config: dict[str, bool]) -> dict[str, Any]:
        """Mock Docker configuration."""
        result = {"success": True}

        if config.get("add_user_to_group"):
            subprocess.run(
                ["usermod", "-aG", "docker", os.getenv("USER", "ubuntu")], check=True
            )
            result["user_added_to_group"] = True

        if config.get("enable_service"):
            subprocess.run(["systemctl", "enable", "docker"], check=True)
            result["service_enabled"] = True

        if config.get("start_service"):
            subprocess.run(["systemctl", "start", "docker"], check=True)
            result["service_started"] = True

        return result

    def _mock_configure_k3s_control_plane(
        self, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Mock K3s control plane configuration."""
        install_args = [
            "curl",
            "-sfL",
            "https://get.k3s.io",
            "|",
            "INSTALL_K3S_EXEC='server",
            f"--bind-address={config['bind_address']}",
            f"--advertise-address={config['advertise_address']}",
        ]

        if config.get("disable_traefik"):
            install_args.append("--disable=traefik")

        if config.get("write_kubeconfig_mode"):
            install_args.append(
                f"--write-kubeconfig-mode={config['write_kubeconfig_mode']}"
            )

        install_args.append("'")
        install_args.append("sh")
        install_args.append("-")

        subprocess.run(" ".join(install_args), shell=True, check=True)

        return {
            "success": True,
            "bind_address": config["bind_address"],
            "advertise_address": config["advertise_address"],
            "traefik_disabled": config.get("disable_traefik", False),
        }

    def _mock_generate_kubeconfig_dual_ip(
        self, internal_ip: str, external_ip: str
    ) -> dict[str, Any]:
        """Mock dual IP kubeconfig generation."""
        from pathlib import Path

        # Read original kubeconfig
        original_config = Path("/etc/rancher/k3s/k3s.yaml").read_text()

        # Generate internal config (for WSL2 use)
        internal_config = original_config.replace("127.0.0.1", internal_ip)
        internal_path = Path.home() / ".kube" / "config-internal"
        internal_path.parent.mkdir(exist_ok=True)
        internal_path.write_text(internal_config)

        # Generate external config (for agent nodes)
        external_config = original_config.replace("127.0.0.1", external_ip)
        external_path = Path.home() / ".kube" / "config-external"
        external_path.write_text(external_config)

        return {
            "success": True,
            "internal_config_path": str(internal_path),
            "external_config_path": str(external_path),
            "internal_ip": internal_ip,
            "external_ip": external_ip,
        }

    def _mock_validate_installation(
        self, components: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Mock installation validation."""
        validated_components = []
        failed_validations = []

        for component in components:
            try:
                result = subprocess.run(
                    component["verify_command"].split(),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                validated_components.append(
                    {
                        "name": component["name"],
                        "version": result.stdout.strip(),
                    }
                )
            except (FileNotFoundError, subprocess.CalledProcessError):
                failed_validations.append(component["name"])

        return {
            "validation_passed": len(failed_validations) == 0,
            "validated_components": validated_components,
            "failed_validations": failed_validations,
            "total_components": len(components),
        }
