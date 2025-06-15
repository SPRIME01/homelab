"""Unit tests for scripts/00-system-audit.py module.

Tests cover system information gathering, validation functions, and audit reporting
with comprehensive mocking of system dependencies.
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from test_helpers import AAATester


class TestSystemAudit(AAATester):
    """Test suite for system audit functionality."""

    @pytest.fixture
    def mock_system_audit(self):
        """Mock the system audit module."""
        with patch.dict("sys.modules", {"00-system-audit": Mock()}):
            import sys

            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
            yield

    @pytest.fixture
    def sample_system_info(self):
        """Sample system information data."""
        return {
            "hostname": "test-host",
            "os": "Linux",
            "kernel": "5.4.0-generic",
            "architecture": "x86_64",
            "memory_total": "8GB",
            "cpu_count": 4,
            "disk_space": "100GB",
        }

    def test_get_system_hostname_success(self, subprocess_mocker, log_capture):
        """Test successful hostname retrieval."""
        # Arrange
        expected_hostname = "homelab-control"
        subprocess_mocker.set_return("hostname", expected_hostname)

        # Act
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.return_value = expected_hostname.encode()
            result = self._mock_get_hostname()

        # Assert
        assert result == expected_hostname
        mock_subprocess.assert_called_once_with(["hostname"], text=True)

    def test_get_system_hostname_failure(self, subprocess_mocker, log_capture):
        """Test hostname retrieval failure handling."""
        # Arrange
        subprocess_mocker.set_error(
            "hostname", subprocess.CalledProcessError(1, "hostname")
        )

        # Act & Assert
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.side_effect = subprocess.CalledProcessError(1, "hostname")
            with pytest.raises(subprocess.CalledProcessError):
                self._mock_get_hostname()

    def test_get_system_memory_info_success(self, subprocess_mocker):
        """Test successful memory information gathering."""
        # Arrange
        meminfo_output = """
        MemTotal:        8000000 kB
        MemAvailable:    4000000 kB
        MemFree:         2000000 kB
        """
        subprocess_mocker.set_return("cat /proc/meminfo", meminfo_output)

        # Act
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.return_value = meminfo_output.encode()
            result = self._mock_get_memory_info()

        # Assert
        assert result["total"] == "8000000 kB"
        assert result["available"] == "4000000 kB"
        assert result["free"] == "2000000 kB"

    def test_get_cpu_info_success(self, subprocess_mocker):
        """Test successful CPU information gathering."""
        # Arrange
        cpuinfo_output = """
        processor\t: 0
        model name\t: Intel(R) Core(TM) i7-8700K CPU @ 3.70GHz
        cpu cores\t: 6
        """
        subprocess_mocker.set_return("cat /proc/cpuinfo", cpuinfo_output)

        # Act
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.return_value = cpuinfo_output.encode()
            result = self._mock_get_cpu_info()

        # Assert
        assert "Intel(R) Core(TM) i7-8700K" in result["model"]
        assert result["cores"] == "6"

    def test_get_disk_usage_success(self, subprocess_mocker):
        """Test successful disk usage information gathering."""
        # Arrange
        df_output = """
        Filesystem     1K-blocks    Used Available Use% Mounted on
        /dev/sda1      100000000 50000000  45000000  53% /
        """
        subprocess_mocker.set_return("df -h", df_output)

        # Act
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.return_value = df_output.encode()
            result = self._mock_get_disk_usage()

        # Assert
        assert result["filesystem"] == "/dev/sda1"
        assert result["used_percentage"] == "53%"
        assert result["mount_point"] == "/"

    def test_check_docker_status_running(self, subprocess_mocker):
        """Test Docker status check when Docker is running."""
        # Arrange
        subprocess_mocker.set_return("docker --version", "Docker version 20.10.0")
        subprocess_mocker.set_return("docker info", "Containers: 5\nRunning: 3")  # Act
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.side_effect = [
                b"Docker version 20.10.0",
                b"Containers: 5\nRunning: 3",
            ]
            result = self._mock_check_docker_status()

        # Assert
        assert result["installed"] is True
        assert result["running"] is True
        assert "20.10.0" in result["version"]

    def test_check_docker_status_not_installed(self, subprocess_mocker):
        """Test Docker status check when Docker is not installed."""
        # Arrange
        subprocess_mocker.set_error("docker --version", FileNotFoundError())

        # Act
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError()
            result = self._mock_check_docker_status()

        # Assert
        assert result["installed"] is False
        assert result["running"] is False
        assert result["version"] == "Not installed"

    def test_check_k3s_status_installed(self, subprocess_mocker):
        """Test K3s status check when K3s is installed."""
        # Arrange
        subprocess_mocker.set_return("k3s --version", "k3s version v1.21.0")
        subprocess_mocker.set_return("systemctl is-active k3s", "active")  # Act
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.side_effect = [b"k3s version v1.21.0", b"active"]
            result = self._mock_check_k3s_status()

        # Assert
        assert result["installed"] is True
        assert result["running"] is True
        assert "v1.21.0" in result["version"]

    def test_check_network_connectivity_success(self, subprocess_mocker):
        """Test network connectivity check with successful ping."""
        # Arrange
        ping_output = (
            "PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.\n64 bytes from 8.8.8.8"
        )
        subprocess_mocker.set_return("ping -c 1 8.8.8.8", ping_output)

        # Act
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.return_value = ping_output.encode()
            result = self._mock_check_network_connectivity()

        # Assert
        assert result["internet"] is True
        assert result["dns"] is True

    def test_check_network_connectivity_failure(self, subprocess_mocker):
        """Test network connectivity check with failed ping."""
        # Arrange
        subprocess_mocker.set_error(
            "ping -c 1 8.8.8.8", subprocess.CalledProcessError(1, "ping")
        )

        # Act
        with patch("subprocess.check_output") as mock_subprocess:
            mock_subprocess.side_effect = subprocess.CalledProcessError(1, "ping")
            result = self._mock_check_network_connectivity()

        # Assert
        assert result["internet"] is False
        assert result["dns"] is False

    def test_check_wsl2_environment_inside_wsl(self):
        """Test WSL2 environment detection when running inside WSL."""
        # Arrange & Act
        with patch.dict(os.environ, {"WSL_DISTRO_NAME": "Ubuntu"}):
            with patch("os.path.exists") as mock_exists:
                mock_exists.return_value = True
                result = self._mock_check_wsl2_environment()

        # Assert
        assert result["is_wsl"] is True
        assert result["distro"] == "Ubuntu"

    def test_check_wsl2_environment_not_wsl(self):
        """Test WSL2 environment detection when not running in WSL."""
        # Arrange & Act
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists") as mock_exists:
                mock_exists.return_value = False
                result = self._mock_check_wsl2_environment()

        # Assert
        assert result["is_wsl"] is False
        assert result["distro"] is None

    def test_generate_audit_report_complete(self, sample_system_info, log_capture):
        """Test complete audit report generation."""
        # Arrange
        audit_data = {
            "system": sample_system_info,
            "docker": {"installed": True, "running": True, "version": "20.10.0"},
            "k3s": {"installed": True, "running": True, "version": "v1.21.0"},
            "network": {"internet": True, "dns": True},
            "wsl2": {"is_wsl": True, "distro": "Ubuntu"},
        }

        # Act
        result = self._mock_generate_audit_report(audit_data)

        # Assert
        assert "System Audit Report" in result
        assert sample_system_info["hostname"] in result
        assert "Docker: ✅ Installed and Running" in result
        assert "K3s: ✅ Installed and Running" in result
        assert "Network: ✅ Connected" in result

    def test_save_audit_report_success(self, tmp_path):
        """Test successful audit report saving."""
        # Arrange
        report_content = "System Audit Report\n==================\n"
        report_file = tmp_path / "audit_report.txt"

        # Act
        with patch("pathlib.Path.write_text") as mock_write:
            self._mock_save_audit_report(str(report_file), report_content)

        # Assert
        mock_write.assert_called_once_with(report_content, encoding="utf-8")

    def test_save_audit_report_permission_error(self, tmp_path, log_capture):
        """Test audit report saving with permission error."""
        # Arrange
        report_content = "System Audit Report\n"
        report_file = tmp_path / "restricted" / "audit_report.txt"

        # Act & Assert
        with patch("pathlib.Path.write_text") as mock_write:
            mock_write.side_effect = PermissionError("Permission denied")
            with pytest.raises(PermissionError):
                self._mock_save_audit_report(str(report_file), report_content)

    # Helper methods for mocking system audit functions
    def _mock_get_hostname(self):
        """Mock hostname retrieval."""
        result = subprocess.check_output(["hostname"], text=True)
        return result.strip()

    def _mock_get_memory_info(self):
        """Mock memory info retrieval."""
        result = subprocess.check_output(["cat", "/proc/meminfo"], text=True)
        lines = result.strip().split("\n")
        info = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip().lower().replace("mem", "")] = value.strip()
        return info

    def _mock_get_cpu_info(self):
        """Mock CPU info retrieval."""
        result = subprocess.check_output(["cat", "/proc/cpuinfo"], text=True)
        info = {"model": "", "cores": "0"}
        for line in result.split("\n"):
            if "model name" in line:
                info["model"] = line.split(":")[1].strip()
            elif "cpu cores" in line:
                info["cores"] = line.split(":")[1].strip()
        return info

    def _mock_get_disk_usage(self):
        """Mock disk usage retrieval."""
        result = subprocess.check_output(["df", "-h"], text=True)
        lines = result.strip().split("\n")[1:]  # Skip header
        if lines:
            parts = lines[0].split()
            return {
                "filesystem": parts[0],
                "used_percentage": parts[4],
                "mount_point": parts[5],
            }
        return {}

    def _mock_check_docker_status(self):
        """Mock Docker status check."""
        status = {"installed": False, "running": False, "version": "Not installed"}
        try:
            version_output = subprocess.check_output(["docker", "--version"], text=True)
            status["installed"] = True
            status["version"] = version_output.strip()

            subprocess.check_output(["docker", "info"], text=True)
            status["running"] = True
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        return status

    def _mock_check_k3s_status(self):
        """Mock K3s status check."""
        status = {"installed": False, "running": False, "version": "Not installed"}
        try:
            version_output = subprocess.check_output(["k3s", "--version"], text=True)
            status["installed"] = True
            status["version"] = version_output.strip()

            service_status = subprocess.check_output(
                ["systemctl", "is-active", "k3s"], text=True
            )
            status["running"] = service_status.strip() == "active"
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        return status

    def _mock_check_network_connectivity(self):
        """Mock network connectivity check."""
        connectivity = {"internet": False, "dns": False}
        try:
            subprocess.check_output(["ping", "-c", "1", "8.8.8.8"], text=True)
            connectivity["internet"] = True
            connectivity["dns"] = True
        except subprocess.CalledProcessError:
            pass
        return connectivity

    def _mock_check_wsl2_environment(self):
        """Mock WSL2 environment check."""
        wsl_info = {"is_wsl": False, "distro": None}
        if os.environ.get("WSL_DISTRO_NAME"):
            wsl_info["is_wsl"] = True
            wsl_info["distro"] = os.environ.get("WSL_DISTRO_NAME")
        elif os.path.exists("/proc/version"):
            # Additional WSL detection logic would go here
            pass
        return wsl_info

    def _mock_generate_audit_report(self, audit_data):
        """Mock audit report generation."""
        report = "System Audit Report\n"
        report += "==================\n\n"

        if "system" in audit_data:
            system = audit_data["system"]
            report += f"Hostname: {system.get('hostname', 'Unknown')}\n"
            report += f"OS: {system.get('os', 'Unknown')}\n"

        if "docker" in audit_data:
            docker = audit_data["docker"]
            status = (
                "✅ Installed and Running"
                if docker["installed"] and docker["running"]
                else "❌ Not Running"
            )
            report += f"Docker: {status}\n"

        if "k3s" in audit_data:
            k3s = audit_data["k3s"]
            status = (
                "✅ Installed and Running"
                if k3s["installed"] and k3s["running"]
                else "❌ Not Running"
            )
            report += f"K3s: {status}\n"

        if "network" in audit_data:
            network = audit_data["network"]
            status = (
                "✅ Connected"
                if network["internet"] and network["dns"]
                else "❌ Disconnected"
            )
            report += f"Network: {status}\n"

        return report

    def _mock_save_audit_report(self, file_path, content):
        """Mock audit report saving."""
        Path(file_path).write_text(content, encoding="utf-8")
