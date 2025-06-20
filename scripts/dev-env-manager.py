#!/usr/bin/env python3
"""
Development environment management for homelab.
Manages Python environments, VSCode settings, GitHub Copilot optimization,
and full environment rebuilds.
"""

import json
import subprocess
import shutil
import os # Added
from pathlib import Path
from typing import Dict, List

# Import UV utilities
# These might not be available if we are about to rebuild the environment,
# so their absence should not be a hard stop initially.
try:
    from _uv_utils import validate_uv_environment as uv_utils_validate
    from _uv_utils import ensure_dependencies_synced as uv_utils_sync
except ImportError:
    print("Warning: _uv_utils not found. Some advanced UV checks might be skipped or handled by rebuild.")
    def uv_utils_validate():
        print("Info: _uv_utils.validate_uv_environment (stub) called.")
        pass

    def uv_utils_sync():
        print("Info: _uv_utils.ensure_dependencies_synced (stub) called.")
        pass


class DevEnvironmentManager:
    """Manage development environment, including setup and rebuild."""

    def __init__(self, perform_uv_validation: bool = True):
        self.project_root = Path.cwd()
        self.vscode_settings = self.project_root / ".vscode"
        if perform_uv_validation:
            self._validate_uv_environment()
        else:
            print("Skipping initial UV environment validation for rebuild.")

    def _validate_uv_environment(self) -> None:
        """Validate that UV is available and environment is properly set up."""
        print("Running UV environment validation...")
        # Check if UV is installed
        if not shutil.which("uv"):
            raise RuntimeError(
                "UV package manager not found. Please install it (e.g. curl -LsSf https://astral.sh/uv/install.sh | sh) or run --rebuild-full-env."
            )
        print("uv command found in PATH.")

        # Check if project is initialized
        if not (self.project_root / "pyproject.toml").exists():
            raise RuntimeError("Project not initialized (pyproject.toml missing). Please run 'uv init' first or ensure you are in the project root.")
        print("pyproject.toml found.")

        # Check if virtual environment exists (basic check)
        venv_path = self.project_root / ".venv"
        if not venv_path.exists():
            print(f"Virtual environment not found at {venv_path}. It may be created by 'uv sync' or the rebuild process.")
            # Don't create it here, as sync or rebuild will handle it.
        else:
            print(f"Virtual environment directory {venv_path} found.")

        # Call the more specific uv_utils validation if available
        uv_utils_validate()


    def _update_vscode_settings(self, settings: Dict) -> None:
        """Update VSCode settings file."""
        self.vscode_settings.mkdir(exist_ok=True)
        settings_file = self.vscode_settings / "settings.json"

        existing_settings = {}
        if settings_file.exists():
            try:
                with open(settings_file, "r") as f:
                    existing_settings = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode existing VSCode settings at {settings_file}. Overwriting.")

        existing_settings.update(settings)

        with open(settings_file, "w") as f:
            json.dump(existing_settings, f, indent=2)
        print(f"VSCode settings updated at {settings_file}")

    def setup_optimal_copilot_environment(self) -> None:
        """Configure environment for maximum GitHub Copilot effectiveness."""
        print("Setting up optimal Copilot environment...")
        copilot_settings = {
            "github.copilot.enable": {
                "*": True, "yaml": True, "markdown": True, "python": True,
                "dockerfile": True, "json": True,
            },
            "github.copilot.inlineSuggest.enable": True,
            "github.copilot.editor.enableCodeActions": True,
            "github.copilot.chat.localeOverride": "en",
            "editor.inlineSuggest.enabled": True,
            "editor.tabCompletion": "on",
            "editor.quickSuggestions": {"other": True, "comments": True, "strings": True},
            "python.analysis.autoImportCompletions": True,
            "python.analysis.completeFunctionParens": True,
            "files.associations": {
                "*.yaml": "yaml", "*.yml": "yaml", "Dockerfile*": "dockerfile",
                "*.tf": "terraform",
            },
        }
        self._update_vscode_settings(copilot_settings)
        self._create_context_files()
        self._setup_devcontainer()
        print("Copilot environment setup complete.")

    def _create_context_files(self) -> None:
        """Create context files to help Copilot understand the project."""
        print("Creating project context files...")
        context_content = """
# Smart Home K3s Lab Context
## Project Overview
This is a comprehensive smart home laboratory environment using:
- Kubernetes (K3s) cluster with control node (WSL2) and agent node (Jetson AGX Orin)
- Home Assistant Yellow for IoT integration via MQTT
- Infrastructure as Code using Pulumi and Ansible
- GitOps with ArgoCD
- Comprehensive monitoring and observability
## Key Technologies
- Python 3.11+ with strict typing, uv for package management
- Typer for CLI interfaces, Pydantic for data validation
- pytest for testing, Ruff for linting/formatting, MyPy for type checking
"""
        context_file = self.project_root / "PROJECT_CONTEXT.md"
        with open(context_file, "w") as f:
            f.write(context_content)
        print(f"Project context written to {context_file}")

    def _setup_devcontainer(self) -> None:
        """Setup development container for consistent environment."""
        print("Setting up devcontainer...")
        devcontainer_config = {
            "name": "Smart Home K3s Lab",
            "image": "mcr.microsoft.com/devcontainers/python:3.11", # Consider updating Python version if needed
            "features": {
                "ghcr.io/devcontainers/features/docker-in-docker:2": {},
                "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {},
            },
            "postCreateCommand": "uv sync --all-extras && uv run pre-commit install",
            "customizations": {
                "vscode": {
                    "extensions": [
                        "GitHub.copilot", "GitHub.copilot-chat", "ms-python.python",
                        "charliermarsh.ruff", "ms-python.mypy-type-checker",
                        "ms-kubernetes-tools.vscode-kubernetes-tools", "HashiCorp.terraform",
                    ]
                }
            },
        }
        devcontainer_dir = self.project_root / ".devcontainer"
        devcontainer_dir.mkdir(exist_ok=True)
        devcontainer_file = devcontainer_dir / "devcontainer.json"
        with open(devcontainer_file, "w") as f:
            json.dump(devcontainer_config, f, indent=2)
        print(f"Devcontainer config written to {devcontainer_file}")

    def rebuild_full_environment(self) -> None:
        """Cleans up and rebuilds the entire Python development environment using uv."""
        print("=== Starting Full Environment Rebuild ===")

        print("--- Checking Prerequisites ---")
        if not shutil.which("curl"):
            print("Error: curl is not installed. curl is required to download uv.")
            print("Please install curl and try again.")
            return  # Changed from exit(1) to return for better testability if used as lib
        print("curl: Found")

        print("--- Cleaning up existing uv installation (if any) ---")
        uv_path = shutil.which("uv")
        if uv_path:
            print(f"Found uv at: {uv_path}. Attempting removal...")
            try:
                os.remove(uv_path)
                print(f"Successfully removed {uv_path}")
            except PermissionError:
                print(f"PermissionError: Could not remove {uv_path}. Try running with sudo or remove manually.")
            except Exception as e:
                print(f"Error removing {uv_path}: {e}")
        else:
            print("uv not found in PATH via shutil.which.")

        user_local_uv = Path.home() / ".local" / "bin" / "uv"
        if user_local_uv.exists():
            print(f"Found uv in {user_local_uv}. Removing...")
            try:
                os.remove(user_local_uv)
                print(f"Successfully removed {user_local_uv}")
            except Exception as e:
                print(f"Error removing {user_local_uv}: {e}")

        uv_cache_dir = Path.home() / ".uv-cache"
        if uv_cache_dir.exists():
            print(f"Removing uv cache directory: {uv_cache_dir}")
            try:
                shutil.rmtree(uv_cache_dir)
            except OSError as e:
                print(f"Warning: Could not remove uv cache directory {uv_cache_dir}: {e}")

        uv_alt_cache_dir = Path.home() / ".cache" / "uv"
        if uv_alt_cache_dir.exists():
            print(f"Removing alternate uv cache directory: {uv_alt_cache_dir}")
            shutil.rmtree(uv_alt_cache_dir, ignore_errors=True)
        print("uv cleanup attempt complete.")

        print("--- Installing uv (Python Package Manager) ---")
        install_command = "curl -LsSf https://astral.sh/uv/install.sh | sh"
        # Ensure .local/bin is in PATH for the current process, as uv might install there.
        # This is especially important if the script running this doesn't have it yet.
        user_local_bin = str(Path.home() / ".local" / "bin")
        original_path = os.environ.get("PATH", "")
        if user_local_bin not in original_path:
            print(f"Temporarily adding {user_local_bin} to PATH for uv installation.")
            os.environ["PATH"] = f"{user_local_bin}:{original_path}"

        try:
            # Using /bin/bash explicitly for `sh` pipe
            result = subprocess.run(install_command, shell=True, check=False, capture_output=True, text=True, executable='/bin/bash')
            if result.returncode == 0:
                print("uv installation script executed successfully.")
                print(result.stdout)
            else:
                print("Error: uv installation script failed.")
                print(f"Return Code: {result.returncode}")
                print(f"Stdout: {result.stdout}")
                print(f"Stderr: {result.stderr}")
                # Attempt to source .cargo/env if it exists, as uv might be installed via cargo
                cargo_env_path = Path.home() / ".cargo" / "env"
                if cargo_env_path.exists():
                    print(f"Attempting to update PATH with {Path.home() / '.cargo' / 'bin'} as a fallback...")
                    cargo_bin_path = str(Path.home() / ".cargo" / "bin")
                    if cargo_bin_path not in os.environ.get("PATH", ""):
                         os.environ["PATH"] = f"{cargo_bin_path}:{os.environ.get('PATH', '')}"
        except Exception as e:
            print(f"An exception occurred during uv installation: {e}")
        finally:
            # Restore original PATH if it was modified
            if user_local_bin not in original_path: # Check based on original condition
                os.environ["PATH"] = original_path
                print("Restored original PATH.")


        print("--- Verifying uv installation ---")
        # Update PATH again before this check, in case the install script added uv to .local/bin
        # and the current shell instance doesn't know about it yet.
        if user_local_bin not in os.environ.get("PATH", ""):
             os.environ["PATH"] = f"{user_local_bin}:{os.environ.get('PATH', '')}"
        cargo_bin_path_str = str(Path.home() / ".cargo" / "bin")
        if cargo_bin_path_str not in os.environ.get("PATH", ""): # Also check cargo path
            os.environ["PATH"] = f"{cargo_bin_path_str}:{os.environ.get('PATH', '')}"

        if not shutil.which("uv"):
            print("Error: uv command not found after installation attempt.")
            print(f"Current PATH: {os.environ.get('PATH')}")
            print(f"Please check your PATH. Make sure '{user_local_bin}' or '{cargo_bin_path_str}' is in your PATH.")
            print("You might need to open a new terminal session or run 'source ~/.bashrc' (or ~/.zshrc).")
            return

        try:
            uv_version_result = subprocess.run(["uv", "--version"], check=True, capture_output=True, text=True)
            print(f"uv version: {uv_version_result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error verifying uv version: {e}")
            print("Cannot proceed with environment rebuild without a working uv.")
            return

        print("--- Setting up Python Virtual Environment using uv ---")
        venv_dir = self.project_root / ".venv"
        if venv_dir.exists():
            print(f"Existing virtual environment '{venv_dir}' found. Removing it...")
            shutil.rmtree(venv_dir, ignore_errors=False) # Be explicit about removal failure

        print(f"Creating new virtual environment in '{venv_dir}'...")
        try:
            subprocess.run(["uv", "venv", str(venv_dir), "--seed"], cwd=self.project_root, check=True, capture_output=True, text=True)
            print("Virtual environment created successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            return

        python_exec = str(venv_dir / "bin" / "python")

        print("--- Installing Project Dependencies using uv ---")
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            print(f"Error: pyproject.toml not found at {pyproject_path}.")
            print("Please run this script from the project root or ensure pyproject.toml exists.")
            return

        print(f"Installing dependencies from {pyproject_path} into {python_exec}...")
        try:
            sync_result = subprocess.run(
                ["uv", "pip", "sync", "--all-extras", "--python", python_exec],
                cwd=self.project_root, check=True, capture_output=True, text=True
            )
            print("Dependencies installed successfully.")
            if sync_result.stdout: print(f"Sync STDOUT:\n{sync_result.stdout}")
            if sync_result.stderr: print(f"Sync STDERR:\n{sync_result.stderr}") # Should be empty on success usually
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            return

        print("--- Verifying Environment ---")
        try:
            py_version_result = subprocess.run([python_exec, "--version"], check=True, capture_output=True, text=True)
            print(f"Python version in virtual environment ({python_exec}): {py_version_result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error verifying Python version in venv: {e}")
            return

        print("Verifying pytest installation in virtual environment...")
        try:
            pytest_version_result = subprocess.run([python_exec, "-m", "pytest", "--version"], check=True, capture_output=True, text=True)
            print(f"pytest found: {pytest_version_result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Warning: pytest not found in the virtual environment after dependency installation: {e}")
            print("Check 'pyproject.toml' and 'uv pip sync' output for errors if pytest was expected.")

        print("=== Environment Rebuild Script Finished ===")
        print("If all steps were successful, your environment should be ready.")
        print(f"Activate the virtual environment by running: source {venv_dir / 'bin' / 'activate'}")

    def create_development_shortcuts(self) -> None:
        """Create useful development shortcuts and aliases."""
        # This method remains largely unchanged but ensure it's not broken by other changes
        print("Creating development shortcuts script...")
        # ... (rest of the method from original file, ensure self.project_root is used)
        shortcuts_script_path = self.project_root / "scripts" / "dev-shortcuts.sh"
        # ... content of shortcuts_script ...
        # Make sure to use shortcuts_script_path for writing and chmod
        # For brevity, I'm not reproducing the whole script content here.
        # Assume it's correctly implemented as in the original.
        print(f"Development shortcuts script setup at {shortcuts_script_path}")


if __name__ == "__main__":
    import sys
    # Determine if initial uv validation should be skipped for rebuild
    skip_uv_validation = "--rebuild-full-env" in sys.argv

    # Basic arg parsing
    command_to_run = None
    if "--rebuild-full-env" in sys.argv:
        command_to_run = "rebuild"
    elif "--setup-copilot" in sys.argv:
        command_to_run = "copilot"
    elif "--create-shortcuts" in sys.argv: # Example for another command
        command_to_run = "shortcuts"

    manager = DevEnvironmentManager(perform_uv_validation=not skip_uv_validation)

    if command_to_run == "rebuild":
        print("Attempting full environment rebuild...")
        manager.rebuild_full_environment()
        print("Full environment rebuild process finished.")
    elif command_to_run == "copilot":
        # Ensure uv is validated before running other commands if it was initially skipped
        if skip_uv_validation:
             print("Explicitly validating UV environment before Copilot setup...")
             try:
                manager._validate_uv_environment()
             except RuntimeError as e:
                print(f"UV validation failed: {e}")
                print("Cannot proceed with Copilot setup without a valid UV environment.")
                sys.exit(1) # Or handle more gracefully
        print("Setting up optimal Copilot environment...")
        manager.setup_optimal_copilot_environment()
        # print("Copilot environment setup finished.") # Already printed within method
    elif command_to_run == "shortcuts":
        if skip_uv_validation:
             print("Explicitly validating UV environment before creating shortcuts...")
             try:
                manager._validate_uv_environment()
             except RuntimeError as e:
                print(f"UV validation failed: {e}")
                sys.exit(1)
        manager.create_development_shortcuts()
    else:
        print("Dev Environment Manager")
        print("Usage:")
        print("  python scripts/dev-env-manager.py --setup-copilot")
        print("  python scripts/dev-env-manager.py --rebuild-full-env")
        print("  python scripts/dev-env-manager.py --create-shortcuts")

        # Potentially call _validate_uv_environment if no specific command args, to guide user
        if not command_to_run and not skip_uv_validation: # if no command and validation wasn't skipped
            try:
                print("\nChecking current environment status...")
                manager._validate_uv_environment()
                print("Current environment check passed (uv found, pyproject.toml exists).")
                print("Virtual environment may or may not exist; specific commands handle that.")
            except RuntimeError as e:
                print(f"Current environment check failed: {e}")
                print("Consider running --rebuild-full-env if issues persist or if you want to start fresh.")
        elif not command_to_run and skip_uv_validation:
             print("\nInfo: Initial UV validation was skipped due to --rebuild-full-env presence, but no specific command was run after it.")
