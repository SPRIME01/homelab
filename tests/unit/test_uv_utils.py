#!/usr/bin/env python3
"""
Unit tests for UV utilities module.
Tests the UV package manager utility functions with comprehensive mocking.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from loguru import logger

from scripts._uv_utils import (
    ensure_dependencies_synced,
    get_virtual_env_path,
    is_running_in_venv,
    print_uv_info,
    run_with_uv,
    validate_uv_environment,
)


@pytest.mark.unit
class TestUVUtils:
    """Test suite for UV utilities functionality."""

    def test_validate_uv_environment_success(self, temp_dir, mock_subprocess):
        """Test successful UV environment validation.

        Args:
            temp_dir: Temporary directory fixture
            mock_subprocess: Mocked subprocess.run
        """
        # Arrange: Set up valid environment
        pyproject_file = temp_dir / "pyproject.toml"
        pyproject_file.write_text("[project]\nname = 'test'\nversion = '1.0.0'")

        venv_dir = temp_dir / ".venv"
        venv_dir.mkdir()

        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.touch()

        with patch("shutil.which", return_value="/usr/bin/uv"):
            # Act: Validate environment
            validate_uv_environment(temp_dir)

            # Assert: No exception should be raised
            logger.info("UV environment validation succeeded as expected")

    def test_validate_uv_environment_no_uv(self, temp_dir):
        """Test validation failure when UV is not installed.

        Args:
            temp_dir: Temporary directory fixture
        """
        # Arrange: UV not available
        with patch("shutil.which", return_value=None):
            # Act & Assert: Should raise RuntimeError
            with pytest.raises(RuntimeError, match="UV package manager not found"):
                validate_uv_environment(temp_dir)

    def test_validate_uv_environment_no_pyproject(self, temp_dir):
        """Test validation failure when pyproject.toml is missing.

        Args:
            temp_dir: Temporary directory fixture
        """
        # Arrange: UV available but no pyproject.toml
        with patch("shutil.which", return_value="/usr/bin/uv"):
            # Act & Assert: Should raise RuntimeError
            with pytest.raises(RuntimeError, match="Project not initialized"):
                validate_uv_environment(temp_dir)

    def test_validate_uv_environment_creates_venv(self, temp_dir, mock_subprocess):
        """Test that virtual environment is created when missing.

        Args:
            temp_dir: Temporary directory fixture
            mock_subprocess: Mocked subprocess.run
        """
        # Arrange: Set up project without venv
        pyproject_file = temp_dir / "pyproject.toml"
        pyproject_file.write_text("[project]\nname = 'test'\nversion = '1.0.0'")

        with patch("shutil.which", return_value="/usr/bin/uv"):
            # Mock successful venv creation
            mock_subprocess.return_value = Mock(returncode=0)

            # Mock python executable creation after venv
            def side_effect(*args, **kwargs):
                venv_dir = temp_dir / ".venv"
                venv_dir.mkdir(exist_ok=True)
                if sys.platform == "win32":
                    python_exe = venv_dir / "Scripts" / "python.exe"
                else:
                    python_exe = venv_dir / "bin" / "python"
                python_exe.parent.mkdir(parents=True, exist_ok=True)
                python_exe.touch()
                return Mock(returncode=0)

            mock_subprocess.side_effect = side_effect

            # Act: Validate environment
            validate_uv_environment(temp_dir)

            # Assert: subprocess called to create venv
            mock_subprocess.assert_called_with(
                ["uv", "venv", ".venv"],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True,
            )

    def test_ensure_dependencies_synced_success(self, temp_dir, mock_subprocess):
        """Test successful dependency synchronization.

        Args:
            temp_dir: Temporary directory fixture
            mock_subprocess: Mocked subprocess.run
        """
        # Arrange: Set up valid environment
        self._setup_valid_uv_environment(temp_dir)
        mock_subprocess.return_value = Mock(returncode=0, stdout="success")

        with patch("shutil.which", return_value="/usr/bin/uv"):
            # Act: Ensure dependencies synced
            ensure_dependencies_synced(temp_dir)

            # Assert: uv sync command was called
            sync_call = None
            for call in mock_subprocess.call_args_list:
                if call[0][0] == ["uv", "sync", "--all-extras"]:
                    sync_call = call
                    break

            assert sync_call is not None, "uv sync command was not called"

    def test_ensure_dependencies_synced_failure(self, temp_dir, mock_subprocess):
        """Test dependency synchronization failure handling.

        Args:
            temp_dir: Temporary directory fixture
            mock_subprocess: Mocked subprocess.run
        """
        # Arrange: Set up environment and mock failure
        self._setup_valid_uv_environment(temp_dir)

        with patch("shutil.which", return_value="/usr/bin/uv"):
            # Mock validate_uv_environment to succeed
            with patch("scripts._uv_utils.validate_uv_environment"):
                # Mock sync failure
                error = subprocess.CalledProcessError(
                    1, ["uv", "sync"], "stdout", "stderr"
                )
                mock_subprocess.side_effect = error

                # Act & Assert: Should raise RuntimeError
                with pytest.raises(RuntimeError, match="Failed to sync dependencies"):
                    ensure_dependencies_synced(temp_dir)

    def test_run_with_uv_success(self, temp_dir, mock_subprocess):
        """Test successful command execution with UV.

        Args:
            temp_dir: Temporary directory fixture
            mock_subprocess: Mocked subprocess.run
        """  # Arrange: Set up environment and command
        self._setup_valid_uv_environment(temp_dir)
        command = ["python", "--version"]
        expected_command = ["uv", "run"] + command

        with patch("shutil.which", return_value="/usr/bin/uv"):
            with patch("scripts._uv_utils.validate_uv_environment"):
                # Act: Run command with UV
                run_with_uv(command, temp_dir)

                # Assert: Correct command was executed
                mock_subprocess.assert_called_with(
                    expected_command, cwd=temp_dir, check=True
                )

    def test_get_virtual_env_path(self, temp_dir):
        """Test getting virtual environment path.

        Args:
            temp_dir: Temporary directory fixture
        """
        # Act: Get venv path
        venv_path = get_virtual_env_path(temp_dir)

        # Assert: Correct path returned
        expected_path = temp_dir / ".venv"
        assert venv_path == expected_path

    def test_get_virtual_env_path_default(self):
        """Test getting virtual environment path with default project root."""
        # Arrange: Use current working directory
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test/project")

            # Act: Get venv path without project_root argument
            venv_path = get_virtual_env_path()

            # Assert: Uses current directory
            assert venv_path == Path("/test/project/.venv")

    def test_is_running_in_venv_true(self):
        """Test virtual environment detection - positive case."""
        # Arrange: Mock virtual environment attributes
        with patch.object(sys, "base_prefix", "/usr"):
            with patch.object(sys, "prefix", "/usr/venv"):
                # Act: Check if in venv
                result = is_running_in_venv()

                # Assert: Should detect virtual environment
                assert result is True

    def test_is_running_in_venv_false(self):
        """Test virtual environment detection - negative case."""
        # Arrange: Mock system Python attributes        with patch.object(sys, "base_prefix", "/usr"):
            with patch.object(sys, "prefix", "/usr"):
                with patch.object(sys, "real_prefix", None, create=True):
                    # Act: Check if in venv
                    result = is_running_in_venv()

                    # Assert: Should not detect virtual environment
                    assert result is False

    def test_is_running_in_venv_real_prefix(self):
        """Test virtual environment detection with real_prefix attribute."""
        # Arrange: Mock old-style virtualenv with hasattr check
        with patch("sys.real_prefix", "/usr", create=True):
            # Act: Check if in venv
            result = is_running_in_venv()

            # Assert: Should detect virtual environment
            assert result is True

    def test_print_uv_info_success(self, mock_subprocess, capsys):
        """Test successful UV info printing.

        Args:
            mock_subprocess: Mocked subprocess.run
            capsys: Pytest stdout/stderr capture
        """
        # Arrange: Mock UV version command
        mock_subprocess.return_value = Mock(returncode=0, stdout="uv 0.1.0\n")

        with patch("scripts._uv_utils.is_running_in_venv", return_value=True):
            with patch("scripts._uv_utils.get_virtual_env_path") as mock_get_venv:
                mock_get_venv.return_value = Path("/test/.venv")
                with patch("pathlib.Path.exists", return_value=True):
                    # Act: Print UV info
                    print_uv_info()

                    # Assert: Verify output content
                    captured = capsys.readouterr()
                    assert "UV Version: uv 0.1.0" in captured.out
                    assert "Virtual Environment: Yes" in captured.out
                    assert "Virtual Environment Exists: True" in captured.out

    def test_print_uv_info_failure(self, mock_subprocess, capsys):
        """Test UV info printing when UV command fails.

        Args:
            mock_subprocess: Mocked subprocess.run
            capsys: Pytest stdout/stderr capture
        """
        # Arrange: Mock UV command failure
        mock_subprocess.side_effect = FileNotFoundError("uv not found")

        # Act: Print UV info
        print_uv_info()

        # Assert: Error message displayed
        captured = capsys.readouterr()
        assert "❌ Error getting UV info:" in captured.out

    def _setup_valid_uv_environment(self, temp_dir: Path) -> None:
        """Set up a valid UV environment for testing.

        Args:
            temp_dir: Temporary directory to set up
        """
        # Create pyproject.toml
        pyproject_file = temp_dir / "pyproject.toml"
        pyproject_file.write_text("[project]\nname = 'test'\nversion = '1.0.0'")

        # Create virtual environment structure
        venv_dir = temp_dir / ".venv"
        venv_dir.mkdir()

        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.touch()


@pytest.mark.unit
class TestUVUtilsEdgeCases:
    """Test edge cases and error conditions for UV utilities."""

    def test_validate_uv_environment_corrupted_venv(self, temp_dir):
        """Test handling of corrupted virtual environment.

        Args:
            temp_dir: Temporary directory fixture
        """
        # Arrange: Create project with corrupted venv
        pyproject_file = temp_dir / "pyproject.toml"
        pyproject_file.write_text("[project]\nname = 'test'\nversion = '1.0.0'")

        venv_dir = temp_dir / ".venv"
        venv_dir.mkdir()
        # Don't create python executable - simulates corruption

        with patch("shutil.which", return_value="/usr/bin/uv"):
            # Act & Assert: Should raise RuntimeError
            with pytest.raises(
                RuntimeError, match="Virtual environment appears corrupted"
            ):
                validate_uv_environment(temp_dir)

    def test_run_with_uv_none_project_root(self, mock_subprocess):
        """Test run_with_uv with None project_root parameter.

        Args:
            mock_subprocess: Mocked subprocess.run
        """
        # Arrange: Mock current working directory
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test/project")
            with patch("scripts._uv_utils.validate_uv_environment"):
                command = ["python", "--version"]

                # Act: Run with None project_root
                run_with_uv(command, None)

                # Assert: Uses current directory
                mock_subprocess.assert_called_with(
                    ["uv", "run"] + command, cwd=Path("/test/project"), check=True
                )

    def test_ensure_dependencies_synced_none_project_root(self, mock_subprocess):
        """Test ensure_dependencies_synced with None project_root.

        Args:
            mock_subprocess: Mocked subprocess.run
        """
        # Arrange: Mock current working directory and validation
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test/project")
            with patch("scripts._uv_utils.validate_uv_environment"):
                mock_subprocess.return_value = Mock(returncode=0)

                # Act: Sync with None project_root
                ensure_dependencies_synced(None)

                # Assert: Uses current directory
                assert any(
                    call[1]["cwd"] == Path("/test/project")
                    for call in mock_subprocess.call_args_list
                )

    def test_venv_creation_failure(self, temp_dir, mock_subprocess):
        """Test handling of virtual environment creation failure.

        Args:
            temp_dir: Temporary directory fixture
            mock_subprocess: Mocked subprocess.run
        """
        # Arrange: Project without venv, mock creation failure
        pyproject_file = temp_dir / "pyproject.toml"
        pyproject_file.write_text("[project]\nname = 'test'\nversion = '1.0.0'")

        with patch("shutil.which", return_value="/usr/bin/uv"):
            error = subprocess.CalledProcessError(1, ["uv", "venv"], "stdout", "stderr")
            mock_subprocess.side_effect = error

            # Act & Assert: Should raise RuntimeError
            with pytest.raises(
                RuntimeError, match="Failed to create virtual environment"
            ):
                validate_uv_environment(temp_dir)
