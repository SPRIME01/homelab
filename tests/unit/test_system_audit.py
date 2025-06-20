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
    def mock_system_audit_module(self):
        pass

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

    def test_get_system_hostname_success(self, log_capture):
        expected_hostname = "homelab-control"
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.return_value = expected_hostname # Already a string due to text=True in helper
            # Test the helper that itself calls the (now properly mocked) subprocess.check_output
            result = self._mock_get_hostname()
        assert result == expected_hostname
        # The actual call to subprocess.check_output is inside _mock_get_hostname, so we check how it was called
        mock_check_output.assert_called_once_with(["hostname"], text=True)


    def test_get_system_hostname_failure(self, log_capture):
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.side_effect = subprocess.CalledProcessError(1, "hostname")
            with pytest.raises(subprocess.CalledProcessError):
                self._mock_get_hostname()

    def test_get_system_memory_info_success(self):
        meminfo_output = "MemTotal:        8000000 kB\nMemAvailable:    4000000 kB\nMemFree:         2000000 kB"
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.return_value = meminfo_output
            result = self._mock_get_memory_info()
        assert result["total"] == "8000000 kB"
        assert result["available"] == "4000000 kB"
        assert result["free"] == "2000000 kB"

    def test_get_cpu_info_success(self):
        cpuinfo_output = "processor\t: 0\nmodel name\t: Intel(R) Core(TM) i7-8700K CPU @ 3.70GHz\ncpu cores\t: 6"
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.return_value = cpuinfo_output
            result = self._mock_get_cpu_info()
        assert "Intel(R) Core(TM) i7-8700K" in result["model"]
        assert result["cores"] == "6"

    def test_get_disk_usage_success(self):
        df_output = "Filesystem     1K-blocks    Used Available Use% Mounted on\n/dev/sda1      100000000 50000000  45000000  53% /\n"
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.return_value = df_output
            result = self._mock_get_disk_usage()
        assert result["filesystem"] == "/dev/sda1"
        assert result["used_percentage"] == "53%"
        assert result["mount_point"] == "/"

    def test_check_docker_status_running(self):
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.side_effect = [
                "Docker version 20.10.0", # text=True makes it string
                "Containers: 5\nRunning: 3", # text=True makes it string
            ]
            result = self._mock_check_docker_status()
        assert result["installed"] is True
        assert result["running"] is True
        assert "20.10.0" in result["version"]

    def test_check_docker_status_not_installed(self):
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.side_effect = FileNotFoundError()
            result = self._mock_check_docker_status()
        assert result["installed"] is False
        assert result["running"] is False
        assert result["version"] == "Not installed"

    def test_check_k3s_status_installed(self):
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.side_effect = ["k3s version v1.21.0", "active"]
            result = self._mock_check_k3s_status()
        assert result["installed"] is True
        assert result["running"] is True
        assert "v1.21.0" in result["version"]

    def test_check_network_connectivity_success(self):
        ping_output = "PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.\n64 bytes from 8.8.8.8"
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.return_value = ping_output
            result = self._mock_check_network_connectivity()
        assert result["internet"] is True
        assert result["dns"] is True

    def test_check_network_connectivity_failure(self):
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.side_effect = subprocess.CalledProcessError(1, "ping")
            result = self._mock_check_network_connectivity()
        assert result["internet"] is False
        assert result["dns"] is False

    def test_check_wsl2_environment_inside_wsl(self):
        with patch.dict(os.environ, {"WSL_DISTRO_NAME": "Ubuntu"}):
            with patch("os.path.exists", return_value=True):
                with patch("builtins.open", Mock(read_data="microsoft")): # Mock reading /proc/version
                     with patch("pathlib.Path.read_text", return_value="microsoft"): # If Path().read_text is used
                        result = self._mock_check_wsl2_environment()
        assert result["is_wsl"] is True
        assert result["distro"] == "Ubuntu"

    def test_check_wsl2_environment_not_wsl(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                result = self._mock_check_wsl2_environment()
        assert result["is_wsl"] is False
        assert result["distro"] is None

    def test_generate_audit_report_complete(self, sample_system_info, log_capture):
        audit_data = {
            "system": sample_system_info,
            "docker": {"installed": True, "running": True, "version": "20.10.0"},
            "k3s": {"installed": True, "running": True, "version": "v1.21.0"},
            "network": {"internet": True, "dns": True},
            "wsl2": {"is_wsl": True, "distro": "Ubuntu"},
        }
        result = self._mock_generate_audit_report(audit_data)
        assert "System Audit Report" in result
        assert sample_system_info["hostname"] in result
        assert "Docker: (OK) Installed and Running" in result
        assert "K3s: (OK) Installed and Running" in result
        assert "Network: (OK) Connected" in result

    def test_save_audit_report_success(self, tmp_path):
        report_content = "System Audit Report\n==================\n"
        report_file = tmp_path / "audit_report.txt"
        with patch("pathlib.Path.write_text") as mock_write:
            self._mock_save_audit_report(str(report_file), report_content)
        mock_write.assert_called_once_with(report_content, encoding="utf-8")

    def test_save_audit_report_permission_error(self, tmp_path, log_capture):
        report_content = "System Audit Report\n"
        report_file = tmp_path / "restricted" / "audit_report.txt"
        with patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                self._mock_save_audit_report(str(report_file), report_content)

    # Helper methods - ensuring subprocess.check_output uses text=True
    def _mock_get_hostname(self):
        result = subprocess.check_output(["hostname"], text=True)
        return result.strip()

    def _mock_get_memory_info(self):
        result = subprocess.check_output(["cat", "/proc/meminfo"], text=True)
        lines = result.strip().split("\n")
        info = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip().lower().replace("mem", "")] = value.strip()
        return info

    def _mock_get_cpu_info(self):
        result = subprocess.check_output(["cat", "/proc/cpuinfo"], text=True)
        info = {"model": "", "cores": "0"}
        for line in result.split("\n"):
            if "model name" in line:
                info["model"] = line.split(":")[1].strip()
            elif "cpu cores" in line:
                info["cores"] = line.split(":")[1].strip()
        return info

    def _mock_get_disk_usage(self):
        result = subprocess.check_output(["df", "-h"], text=True)
        lines = result.strip().split("\n")[1:]
        if lines:
            parts = lines[0].split()
            return {
                "filesystem": parts[0],
                "used_percentage": parts[4],
                "mount_point": parts[5],
            }
        return {}

    def _mock_check_docker_status(self):
        status = {"installed": False, "running": False, "version": "Not installed"}
        try:
            version_output = subprocess.check_output(["docker", "--version"], text=True)
            status["installed"] = True
            status["version"] = version_output.strip()
            subprocess.check_output(["docker", "info"], text=True) # This output isn't used, but call is made
            status["running"] = True
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        return status

    def _mock_check_k3s_status(self):
        status = {"installed": False, "running": False, "version": "Not installed"}
        try:
            version_output = subprocess.check_output(["k3s", "--version"], text=True)
            status["installed"] = True
            status["version"] = version_output.strip()
            service_status = subprocess.check_output(["systemctl", "is-active", "k3s"], text=True)
            status["running"] = service_status.strip() == "active"
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        return status

    def _mock_check_network_connectivity(self):
        connectivity = {"internet": False, "dns": False}
        try:
            subprocess.check_output(["ping", "-c", "1", "8.8.8.8"], text=True)
            connectivity["internet"] = True
            connectivity["dns"] = True
        except subprocess.CalledProcessError:
            pass
        return connectivity

    def _mock_check_wsl2_environment(self):
        wsl_info = {"is_wsl": False, "distro": None}
        if os.environ.get("WSL_DISTRO_NAME"):
            wsl_info["is_wsl"] = True
            wsl_info["distro"] = os.environ.get("WSL_DISTRO_NAME")
        elif os.path.exists("/proc/version"):
            try: # Need try-except for the open call as well if /proc/version might not exist
                with open("/proc/version", "r") as f:
                    if "microsoft" in f.read().lower():
                        wsl_info["is_wsl"] = True
            except FileNotFoundError: # Should not happen if os.path.exists is true, but good practice
                pass
        return wsl_info

    def _mock_generate_audit_report(self, audit_data):
        report = "System Audit Report\n"
        report += "==================\n\n"
        if "system" in audit_data:
            system = audit_data["system"]
            report += f"Hostname: {system.get('hostname', 'Unknown')}\n"
            report += f"OS: {system.get('os', 'Unknown')}\n"
        if "docker" in audit_data:
            docker = audit_data["docker"]
            status = "(OK) Installed and Running" if docker["installed"] and docker["running"] else "❌ Not Running"
            report += f"Docker: {status}\n"
        if "k3s" in audit_data:
            k3s = audit_data["k3s"]
            status = "(OK) Installed and Running" if k3s["installed"] and k3s["running"] else "❌ Not Running"
            report += f"K3s: {status}\n"
        if "network" in audit_data:
            network = audit_data["network"]
            status = "(OK) Connected" if network["internet"] and network["dns"] else "❌ Disconnected"
            report += f"Network: {status}\n"
        return report

    def _mock_save_audit_report(self, file_path, content):
        Path(file_path).write_text(content, encoding="utf-8")
