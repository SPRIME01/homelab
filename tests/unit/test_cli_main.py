"""Unit tests for src/homelab/cli/main.py module.

Tests cover CLI commands, argument parsing, and user interaction
with comprehensive mocking of external dependencies and file operations.
"""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from test_helpers import AAATester

from homelab.cli.main import app


class TestHomelabCLI(AAATester):
    """Test suite for Homelab CLI functionality."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """CLI test runner fixture."""
        return CliRunner()

    @pytest.fixture
    def sample_config(self) -> dict[str, Any]:
        """Sample configuration data."""
        return {
            "cluster": {
                "name": "homelab-k3s",
                "control_plane": "192.168.0.50",
                "agent_nodes": ["192.168.0.66"],
            },
            "services": {
                "traefik": {"enabled": True, "version": "v2.10"},
                "supabase": {"enabled": True, "project": "homelab-db"},
                "mqtt": {"broker": "192.168.0.41", "port": 1883},
            },
        }

    def test_cli_help_command(self, cli_runner: CliRunner) -> None:
        """Test CLI help command displays correctly."""
        # Arrange & Act
        result = cli_runner.invoke(app, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "homelab" in result.stdout.lower()
        assert "usage" in result.stdout.lower()

    def test_version_command(self, cli_runner: CliRunner) -> None:
        """Test version command displays version information."""
        # Arrange & Act
        result = cli_runner.invoke(app, ["version"])

        # Assert
        assert result.exit_code == 0
        assert "version" in result.stdout.lower()

    def test_init_command_success(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test successful homelab initialization."""
        # Arrange
        config_file = tmp_path / "homelab.yaml"

        # Act
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = cli_runner.invoke(app, ["init", "--config", str(config_file)])

        # Assert
        assert result.exit_code == 0
        assert "initialized" in result.stdout.lower()

    def test_init_command_existing_config(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test init command with existing configuration."""
        # Arrange
        config_file = tmp_path / "homelab.yaml"
        config_file.write_text("existing: config")

        # Act
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = cli_runner.invoke(app, ["init", "--config", str(config_file)])

        # Assert
        assert result.exit_code == 1
        assert "already exists" in result.stdout.lower()

    def test_status_command_success(
        self, cli_runner: CliRunner, sample_config: dict[str, Any]
    ) -> None:
        """Test successful status command."""
        # Arrange & Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Ready")
            result = cli_runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "status" in result.stdout.lower()

    def test_deploy_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful deployment command."""
        # Arrange
        service_name = "traefik"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = cli_runner.invoke(app, ["deploy", service_name])

        # Assert
        assert result.exit_code == 0
        assert "deployed" in result.stdout.lower()

    def test_deploy_command_failure(self, cli_runner: CliRunner) -> None:
        """Test deployment command failure handling."""
        # Arrange
        service_name = "failing-service"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Deployment failed")
            result = cli_runner.invoke(app, ["deploy", service_name])

        # Assert
        assert result.exit_code == 1
        assert "failed" in result.stdout.lower()

    def test_logs_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful logs command."""
        # Arrange
        service_name = "supabase"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="2024-01-01 12:00:00 INFO Service started"
            )
            result = cli_runner.invoke(app, ["logs", service_name])

        # Assert
        assert result.exit_code == 0
        assert "info" in result.stdout.lower()

    def test_logs_command_follow(self, cli_runner: CliRunner) -> None:
        """Test logs command with follow option."""
        # Arrange
        service_name = "mqtt-broker"

        # Act
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.stdout.readline.side_effect = [
                b"Log line 1\n",
                b"Log line 2\n",
                b"",  # EOF
            ]
            mock_popen.return_value = mock_process

            result = cli_runner.invoke(app, ["logs", service_name, "--follow"])

        # Assert
        assert result.exit_code == 0

    def test_config_show_command(
        self, cli_runner: CliRunner, sample_config: dict[str, Any]
    ) -> None:
        """Test config show command."""
        # Arrange & Act
        with (
            patch("yaml.safe_load", return_value=sample_config),
            patch("pathlib.Path.read_text", return_value="config content"),
        ):
            result = cli_runner.invoke(app, ["config", "show"])

        # Assert
        assert result.exit_code == 0
        assert "cluster" in result.stdout.lower()

    def test_config_set_command(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test config set command."""
        # Arrange
        config_file = tmp_path / "homelab.yaml"
        config_file.write_text("cluster:\n  name: test")

        # Act
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = cli_runner.invoke(
                app, ["config", "set", "cluster.control_plane", "192.168.0.100"]
            )

        # Assert
        assert result.exit_code == 0
        assert "updated" in result.stdout.lower()

    def test_backup_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful backup command."""
        # Arrange
        backup_target = "all"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = cli_runner.invoke(app, ["backup", backup_target])

        # Assert
        assert result.exit_code == 0
        assert "backup" in result.stdout.lower()

    def test_restore_command_success(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test successful restore command."""
        # Arrange
        backup_file = tmp_path / "backup.tar.gz"
        backup_file.write_bytes(b"backup data")

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = cli_runner.invoke(app, ["restore", str(backup_file)])

        # Assert
        assert result.exit_code == 0
        assert "restored" in result.stdout.lower()

    def test_scale_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful scale command."""
        # Arrange
        service_name = "web-app"
        replicas = 3

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = cli_runner.invoke(app, ["scale", service_name, str(replicas)])

        # Assert
        assert result.exit_code == 0
        assert "scaled" in result.stdout.lower()

    def test_update_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful update command."""
        # Arrange & Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = cli_runner.invoke(app, ["update"])

        # Assert
        assert result.exit_code == 0
        assert "updated" in result.stdout.lower()

    def test_validate_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful validate command."""
        # Arrange & Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="All checks passed")
            result = cli_runner.invoke(app, ["validate"])

        # Assert
        assert result.exit_code == 0
        assert "passed" in result.stdout.lower()

    def test_validate_command_failures(self, cli_runner: CliRunner) -> None:
        """Test validate command with validation failures."""
        # Arrange & Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1, stdout="Validation failed: Service unreachable"
            )
            result = cli_runner.invoke(app, ["validate"])

        # Assert
        assert result.exit_code == 1
        assert "failed" in result.stdout.lower()

    def test_ssh_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful SSH command."""
        # Arrange
        node_name = "control-node"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = cli_runner.invoke(app, ["ssh", node_name])

        # Assert
        assert result.exit_code == 0

    def test_ssh_command_invalid_node(self, cli_runner: CliRunner) -> None:
        """Test SSH command with invalid node."""
        # Arrange
        node_name = "nonexistent-node"

        # Act
        result = cli_runner.invoke(app, ["ssh", node_name])

        # Assert
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_port_forward_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful port forward command."""
        # Arrange
        service_name = "database"
        local_port = 5432
        remote_port = 5432

        # Act
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_popen.return_value = mock_process

            result = cli_runner.invoke(
                app, ["port-forward", service_name, f"{local_port}:{remote_port}"]
            )

        # Assert
        assert result.exit_code == 0

    def test_exec_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful exec command."""
        # Arrange
        pod_name = "web-app-pod"
        command = "ls -la"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="total 4\ndrwxr-xr-x 2 root root 4096 Jan 1 12:00 .",
            )
            result = cli_runner.invoke(app, ["exec", pod_name, "--", command])

        # Assert
        assert result.exit_code == 0
        assert "total" in result.stdout

    def test_dashboard_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful dashboard command."""
        # Arrange & Act
        with patch("webbrowser.open") as mock_open, patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = cli_runner.invoke(app, ["dashboard"])

        # Assert
        assert result.exit_code == 0
        mock_open.assert_called_once()

    def test_interactive_mode_success(self, cli_runner: CliRunner) -> None:
        """Test interactive mode functionality."""
        # Arrange & Act
        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["status", "exit"]
            result = cli_runner.invoke(app, ["interactive"])

        # Assert
        assert result.exit_code == 0

    def test_debug_command_success(self, cli_runner: CliRunner) -> None:
        """Test successful debug command."""
        # Arrange
        component = "networking"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="Debug info: All networking components healthy"
            )
            result = cli_runner.invoke(app, ["debug", component])

        # Assert
        assert result.exit_code == 0
        assert "debug" in result.stdout.lower()

    def test_completion_command_success(self, cli_runner: CliRunner) -> None:
        """Test shell completion command."""
        # Arrange
        shell = "bash"

        # Act
        result = cli_runner.invoke(app, ["completion", shell])

        # Assert
        assert result.exit_code == 0
        assert "complete" in result.stdout
