#!/usr/bin/env python3
"""
Development environment management for homelab.
Manages Python environments, VSCode settings, GitHub Copilot optimization.
"""

import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List

# Import UV utilities
try:
    from _uv_utils import validate_uv_environment, ensure_dependencies_synced
except ImportError:
    # Fallback if not available
    def validate_uv_environment():
        pass
    def ensure_dependencies_synced():
        pass

class DevEnvironmentManager:
    """Manage development environment for optimal GitHub Copilot usage."""

    def __init__(self):
        self.project_root = Path.cwd()
        self.vscode_settings = self.project_root / ".vscode"
        self._validate_uv_environment()

    def _validate_uv_environment(self) -> None:
        """Validate that UV is available and environment is properly set up."""
        # Check if UV is installed
        if not shutil.which("uv"):
            raise RuntimeError(
                "UV package manager not found. Please install it with: pip install uv"
            )

        # Check if project is initialized
        if not (self.project_root / "pyproject.toml").exists():
            raise RuntimeError(
                "Project not initialized. Please run 'uv init' first."
            )

        # Check if virtual environment exists
        venv_path = self.project_root / ".venv"
        if not venv_path.exists():
            print("Virtual environment not found. Creating it...")
            subprocess.run(["uv", "venv", ".venv"], cwd=self.project_root, check=True)
            print("Virtual environment created. Please activate it before continuing.")

    def _update_vscode_settings(self, settings: Dict) -> None:
        """Update VSCode settings file."""
        self.vscode_settings.mkdir(exist_ok=True)
        settings_file = self.vscode_settings / "settings.json"

        # Merge with existing settings if file exists
        existing_settings = {}
        if settings_file.exists():
            with open(settings_file, "r") as f:
                existing_settings = json.load(f)

        existing_settings.update(settings)

        with open(settings_file, "w") as f:
            json.dump(existing_settings, f, indent=2)

    def setup_optimal_copilot_environment(self) -> None:
        """Configure environment for maximum GitHub Copilot effectiveness."""

        # VSCode settings for optimal Copilot experience
        copilot_settings = {
            "github.copilot.enable": {
                "*": True,
                "yaml": True,
                "markdown": True,
                "python": True,
                "dockerfile": True,
                "json": True
            },
            "github.copilot.inlineSuggest.enable": True,
            "github.copilot.editor.enableCodeActions": True,
            "github.copilot.chat.localeOverride": "en",
            "editor.inlineSuggest.enabled": True,
            "editor.tabCompletion": "on",
            "editor.quickSuggestions": {
                "other": True,
                "comments": True,
                "strings": True
            },
            "python.analysis.autoImportCompletions": True,
            "python.analysis.completeFunctionParens": True,
            "files.associations": {
                "*.yaml": "yaml",
                "*.yml": "yaml",
                "Dockerfile*": "dockerfile",
                "*.tf": "terraform"
            }
        }

        self._update_vscode_settings(copilot_settings)

        # Create context files for better Copilot suggestions
        self._create_context_files()

        # Setup development containers
        self._setup_devcontainer()

    def _create_context_files(self) -> None:
        """Create context files to help Copilot understand the project."""

        context_content = """
# Smart Home K3s Lab Context

## Project Overview
This is a comprehensive smart home laboratory environment using:
- Kubernetes (K3s) cluster with control node (WSL2) and agent node (Jetson AGX Orin)
- Home Assistant Yellow for IoT integration via MQTT
- Infrastructure as Code using Pulumi and Ansible
- GitOps with ArgoCD
- Comprehensive monitoring and observability

## Architecture
- Control Node: 192.168.0.50 (Windows host) / 192.168.0.51 (WSL2)
- Agent Node: 192.168.0.66 (Jetson AGX Orin)
- Home Assistant: 192.168.0.41 (MQTT broker)
- Network: OpenWRT router with Tailscale VPN

## Key Technologies
- Python 3.11+ with strict typing
- Typer for CLI interfaces
- Pydantic for data validation
- Loguru for structured logging
- pytest for testing
- Ruff for linting/formatting
- MyPy for type checking

## Development Patterns
- Test-driven development (TDD)
- Hexagonal architecture
- Event-driven design with RabbitMQ
- Microservices architecture
- GitOps deployment workflows
"""

        with open(self.project_root / "PROJECT_CONTEXT.md", "w") as f:
            f.write(context_content)

    def _setup_devcontainer(self) -> None:
        """Setup development container for consistent environment."""

        devcontainer_config = {
            "name": "Smart Home K3s Lab",
            "image": "mcr.microsoft.com/devcontainers/python:3.11",
            "features": {
                "ghcr.io/devcontainers/features/docker-in-docker:2": {},
                "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {}
            },
            "postCreateCommand": "uv sync --all-extras && uv run pre-commit install",
            "customizations": {
                "vscode": {
                    "extensions": [
                        "GitHub.copilot",
                        "GitHub.copilot-chat",
                        "ms-python.python",
                        "charliermarsh.ruff",
                        "ms-python.mypy-type-checker",
                        "ms-kubernetes-tools.vscode-kubernetes-tools",
                        "HashiCorp.terraform"
                    ]
                }
            },
            "forwardPorts": [6443, 8080, 3000],
            "mounts": [
                "source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind"
            ]
        }

        devcontainer_dir = self.project_root / ".devcontainer"
        devcontainer_dir.mkdir(exist_ok=True)

        with open(devcontainer_dir / "devcontainer.json", "w") as f:
            json.dump(devcontainer_config, f, indent=2)

    def create_development_shortcuts(self) -> None:
        """Create useful development shortcuts and aliases."""

        shortcuts_script = """#!/bin/bash
# Smart Home K3s Lab Development Shortcuts

# Aliases for common operations
alias kc='kubectl'
alias kgp='kubectl get pods'
alias kgs='kubectl get services'
alias kgn='kubectl get nodes'
alias logs-k3s='sudo journalctl -u k3s -f'
alias health-check='python3 scripts/cluster-health-monitor.py'
alias discover-devices='python3 scripts/homelab-discovery.py --scan'

# Quick cluster status
cluster-status() {
    echo "=== K3s Cluster Status ==="
    kubectl get nodes -o wide
    echo ""
    echo "=== Pod Status ==="
    kubectl get pods --all-namespaces
    echo ""
    echo "=== Services ==="
    kubectl get services --all-namespaces
}

# Quick deployment
quick-deploy() {
    if [ -z "$1" ]; then
        echo "Usage: quick-deploy <app-name>"
        return 1
    fi

    echo "Deploying $1..."
    ansible-playbook ansible/playbooks/deploy-$1.yml
}

# Development environment reset
dev-reset() {
    echo "Resetting development environment..."

    # Check if UV is available
    if ! command -v uv &> /dev/null; then
        echo "ERROR: UV package manager not found. Please install with: pip install uv"
        return 1
    fi

    # Check if we're in a UV project
    if [ ! -f "pyproject.toml" ]; then
        echo "ERROR: No pyproject.toml found. Please run 'uv init' first."
        return 1
    fi

    # Clean and reset environment
    make clean 2>/dev/null || echo "No Makefile clean target found"

    # Sync dependencies with UV
    echo "Syncing dependencies with UV..."
    uv sync --all-extras

    # Install pre-commit hooks if available
    if uv run which pre-commit &> /dev/null; then
        uv run pre-commit install
        echo "Pre-commit hooks installed"
    fi

    echo "Development environment reset complete"
}

# Add to .bashrc if not already there
if ! grep -q "Smart Home K3s Lab shortcuts" ~/.bashrc; then
    echo "# Smart Home K3s Lab shortcuts" >> ~/.bashrc
    echo "source $(pwd)/scripts/dev-shortcuts.sh" >> ~/.bashrc
    echo "Development shortcuts added to .bashrc"
fi
"""

        with open(self.project_root / "scripts" / "dev-shortcuts.sh", "w") as f:
            f.write(shortcuts_script)

        # Make executable
        subprocess.run(["chmod", "+x", "scripts/dev-shortcuts.sh"])

# Usage: python3 scripts/dev-env-manager.py --setup-all
