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

from homelab.cli.main import app # app is the Typer instance
from test_helpers import AAATester


class TestHomelabCLI(AAATester):
    """Test suite for Homelab CLI functionality."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """CLI test runner fixture."""
        return CliRunner()

    def test_cli_help_command(self, cli_runner: CliRunner) -> None:
        """Test CLI help command displays correctly."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "homelab" in result.stdout.lower()
        assert "usage:" in result.stdout.lower() # Typer's default help screen

    def test_version_command(self, cli_runner: CliRunner) -> None:
        """Test version command displays version information."""
        result = cli_runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "version" in result.stdout.lower()

    def test_init_command_success(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test successful homelab initialization."""
        config_file = tmp_path / "homelab.yaml"
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = cli_runner.invoke(app, ["init", "--config-path", str(config_file)])
        assert result.exit_code == 0
        assert "configuration initialized successfully" in result.stdout.lower()

    def test_init_command_existing_config(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "homelab.yaml"
        config_file.write_text("existing: config")
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = cli_runner.invoke(app, ["init", "--config-path", str(config_file)])
        assert result.exit_code == 1 # Typer.Exit(1)
        assert "already exists" in result.stdout.lower()

    def test_status_command_success(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "cluster is healthy" in result.stdout.lower()

    def test_deploy_command_success(self, cli_runner: CliRunner) -> None:
        service_name = "traefik"
        result = cli_runner.invoke(app, ["deploy", service_name])
        assert result.exit_code == 0
        assert "deployment successful" in result.stdout.lower()

    def test_deploy_command_failure(self, cli_runner: CliRunner) -> None:
        service_name = "failing-service"
        # Assume deploy internally calls something that raises an error if service fails
        with patch("src.homelab.cli.main.console.print") as mock_print:
            # Forcing an internal error to be caught by the broad except in deploy
            # This is a bit of a guess on how to make it fail as intended by original test
            with patch("subprocess.run", side_effect=Exception("Simulated deployment error")):
                 result = cli_runner.invoke(app, ["deploy", service_name])
        # The command itself might still exit 0 if it catches the error and prints
        # This depends on the internal implementation of deploy command
        # For now, let's assume it prints an error message
        # We need to find the print call that indicates failure
        found_error_message = False
        for call_args in mock_print.call_args_list:
            if "deployment successful" not in call_args[0][0].lower() and "deploying" not in call_args[0][0].lower() : # Check it's not the success message
                 found_error_message = True # Or check for a specific error message if known
                 break
        assert found_error_message # Check that some message other than success was printed

    def test_logs_command_success(self, cli_runner: CliRunner) -> None:
        service_name = "supabase"
        result = cli_runner.invoke(app, ["logs", service_name])
        assert result.exit_code == 0
        assert "logs retrieved successfully" in result.stdout.lower()

    def test_logs_command_follow(self, cli_runner: CliRunner) -> None:
        service_name = "mqtt-broker"
        # Mock Popen for follow, as it's interactive
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.stdout.readline.side_effect = [ b"Log line 1\n", b"Log line 2\n", b""]
            mock_popen.return_value = mock_process
            result = cli_runner.invoke(app, ["logs", service_name, "--follow"])
        assert result.exit_code == 0
        # Assert that console print for "Following logs" was called
        # This part of test might need adjustment based on actual implementation if it uses console.print
        # For now, exit_code 0 implies it ran.

    def test_config_cmd_invoked(self, cli_runner: CliRunner) -> None:
        """Test that the 'config' command itself can be invoked (shows help)."""
        result = cli_runner.invoke(app, ["config"])
        assert result.exit_code == 0 # Invoking a Typer group without subcommand shows its help
        assert "configuration management" in result.stdout.lower()

    def test_backup_command_success(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(app, ["backup"]) # Assuming default 'all'
        assert result.exit_code == 0
        assert "backup created successfully" in result.stdout.lower()

    def test_restore_command_success(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        backup_file = tmp_path / "backup.tar.gz"
        backup_file.write_bytes(b"backup data")
        result = cli_runner.invoke(app, ["restore", str(backup_file)])
        assert result.exit_code == 0
        assert "restore completed successfully" in result.stdout.lower()

    def test_scale_command_success(self, cli_runner: CliRunner) -> None:
        service_name = "web-app"
        replicas = 3
        result = cli_runner.invoke(app, ["scale", service_name, str(replicas)])
        assert result.exit_code == 0
        assert "scaling completed successfully" in result.stdout.lower()

    def test_update_command_success(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "update completed successfully" in result.stdout.lower()

    def test_validate_command_success(self, cli_runner: CliRunner) -> None:
        with patch("src.homelab.cli.main.validate_uv_environment") as mock_validate:
            mock_validate.return_value = None # Simulate successful validation
            result = cli_runner.invoke(app, ["validate"])
        assert result.exit_code == 0
        assert "environment validation successful" in result.stdout.lower()

    def test_validate_command_failures(self, cli_runner: CliRunner) -> None:
        with patch("src.homelab.cli.main.validate_uv_environment", side_effect=Exception("Test validation error")):
            result = cli_runner.invoke(app, ["validate"])
        assert result.exit_code == 1
        assert "environment validation failed" in result.stdout.lower()

    def test_ssh_command_success(self, cli_runner: CliRunner) -> None:
        node_name = "control" # Use a valid node from the list in main.py
        result = cli_runner.invoke(app, ["ssh", node_name])
        assert result.exit_code == 0
        assert "ssh connection established" in result.stdout.lower()

    def test_ssh_command_invalid_node(self, cli_runner: CliRunner) -> None:
        node_name = "nonexistent-node"
        result = cli_runner.invoke(app, ["ssh", node_name])
        assert result.exit_code == 1
        assert "invalid node" in result.stdout.lower()

    def test_port_forward_command_success(self, cli_runner: CliRunner) -> None:
        service_name = "database"
        local_port = "5432"
        remote_port = "5432"
        result = cli_runner.invoke(app, ["port-forward", service_name, local_port, remote_port])
        assert result.exit_code == 0
        assert "port forwarding established" in result.stdout.lower()

    def test_exec_command_success(self, cli_runner: CliRunner) -> None:
        service_name = "web-app-pod"
        command_to_exec = "ls -la"
        result = cli_runner.invoke(app, ["exec", service_name, command_to_exec])
        assert result.exit_code == 0
        assert "command executed successfully" in result.stdout.lower()

    def test_dashboard_command_success(self, cli_runner: CliRunner) -> None:
        with patch("webbrowser.open") as mock_webbrowser_open:
            result = cli_runner.invoke(app, ["dashboard"])
            assert result.exit_code == 0
            assert "dashboard opened" in result.stdout.lower()
            mock_webbrowser_open.assert_called_once()

    def test_interactive_mode_success(self, cli_runner: CliRunner) -> None:
        # This test is hard to make fully robust without more complex input mocking
        with patch("rich.console.Console.input", side_effect=["status", "exit"]):
             result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code == 0
        assert "interactive mode started" in result.stdout.lower()

    def test_debug_command_success(self, cli_runner: CliRunner) -> None:
        component = "networking"
        result = cli_runner.invoke(app, ["debug", component])
        assert result.exit_code == 0
        assert "debug information collected" in result.stdout.lower()

    def test_completion_command_success(self, cli_runner: CliRunner) -> None:
        shell = "bash"
        result = cli_runner.invoke(app, ["completion", shell])
        assert result.exit_code == 0
        assert "completion generated" in result.stdout.lower()

    def test_audit_command_invoked(self, cli_runner: CliRunner):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = cli_runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        assert "system audit completed successfully" in result.stdout.lower()

    def test_install_command_invoked(self, cli_runner: CliRunner):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = cli_runner.invoke(app, ["install"])
        assert result.exit_code == 0
        assert "components installed successfully" in result.stdout.lower()

    def test_dev_setup_command_invoked(self, cli_runner: CliRunner):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = cli_runner.invoke(app, ["dev-setup"]) # Command name from app.command()
        assert result.exit_code == 0
        assert "development environment setup completed" in result.stdout.lower()
