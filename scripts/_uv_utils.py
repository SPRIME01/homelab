#!/usr/bin/env python3
"""
UV package manager utilities for homelab scripts.
Provides common UV validation and environment setup functions.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def validate_uv_environment(project_root: Path | None = None) -> None:
    """
    Validate that UV is available and the environment is properly set up.

    Args:
        project_root: Path to project root. If None, uses current working directory.

    Raises:
        RuntimeError: If UV is not available or environment is not properly configured.
    """
    if project_root is None:
        project_root = Path.cwd()

    # Check if UV is installed
    if not shutil.which("uv"):
        raise RuntimeError(
            "UV package manager not found. Please install it with: pip install uv"
        )

    # Check if project is initialized
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise RuntimeError(
            f"Project not initialized. No pyproject.toml found at {pyproject_path}. "
            "Please run 'uv init' first."
        )

    # Check if virtual environment exists
    venv_path = project_root / ".venv"
    if not venv_path.exists():
        print("Virtual environment not found. Creating it...")
        try:
            subprocess.run(
                ["uv", "venv", ".venv"],
                cwd=project_root,
                check=True,
                capture_output=True,
                text=True,
            )
            print("✅ Virtual environment created successfully.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create virtual environment: {e}")

    # Verify we can access the virtual environment
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"

    if not python_exe.exists():
        raise RuntimeError(
            f"Virtual environment appears corrupted. Python executable not found at {python_exe}"
        )


def ensure_dependencies_synced(project_root: Path | None = None) -> None:
    """
    Ensure project dependencies are synced using UV.

    Args:
        project_root: Path to project root. If None, uses current working directory.
    """
    if project_root is None:
        project_root = Path.cwd()

    validate_uv_environment(project_root)

    try:
        subprocess.run(
            ["uv", "sync", "--all-extras"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
        print("✅ Dependencies synced successfully.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to sync dependencies: {e}\nstdout: {e.stdout}\nstderr: {e.stderr}"
        )


def run_with_uv(
    command: list[str], project_root: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """
    Run a command using UV's virtual environment.

    Args:
        command: Command to run as a list of strings
        project_root: Path to project root. If None, uses current working directory.

    Returns:
        subprocess.CompletedProcess: Result of the command execution
    """
    if project_root is None:
        project_root = Path.cwd()

    validate_uv_environment(project_root)

    uv_command = ["uv", "run"] + command
    return subprocess.run(uv_command, cwd=project_root, check=True, text=True)


def get_virtual_env_path(project_root: Path | None = None) -> Path:
    """
    Get the path to the virtual environment.

    Args:
        project_root: Path to project root. If None, uses current working directory.

    Returns:
        Path: Path to the virtual environment directory
    """
    if project_root is None:
        project_root = Path.cwd()

    return project_root / ".venv"


def is_running_in_venv() -> bool:
    """
    Check if currently running inside a virtual environment.

    Returns:
        bool: True if running in a virtual environment, False otherwise
    """
    return hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )


def print_uv_info() -> None:
    """Print information about the current UV environment."""
    try:
        # Get UV version
        result = subprocess.run(
            ["uv", "--version"], capture_output=True, text=True, check=True
        )
        uv_version = result.stdout.strip()

        print(f"UV Version: {uv_version}")
        print(f"Python: {sys.executable}")
        print(f"Virtual Environment: {'Yes' if is_running_in_venv() else 'No'}")

        project_root = Path.cwd()
        venv_path = get_virtual_env_path(project_root)
        print(f"Virtual Environment Path: {venv_path}")
        print(f"Virtual Environment Exists: {venv_path.exists()}")

    except Exception as e:
        print(f"Error getting UV info: {e}")


if __name__ == "__main__":
    """Run UV environment validation and info when called directly."""
    try:
        print("Validating UV environment...")
        validate_uv_environment()
        print("UV environment validation successful!")
        print()
        print_uv_info()
    except RuntimeError as e:
        print(f"UV environment validation failed: {e}")
        sys.exit(1)
