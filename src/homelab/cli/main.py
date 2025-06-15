#!/usr/bin/env python3
"""
Homelab CLI entry point.
Provides command-line interface for homelab management tasks.
"""

import sys
from pathlib import Path

# Add the scripts directory to the path so we can import our utilities
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

try:
    import typer
    from rich.console import Console
    from rich.table import Table
    from _uv_utils import validate_uv_environment, print_uv_info
except ImportError as e:
    print(f"❌ Failed to import required dependencies: {e}")
    print(
        "💡 Please ensure the virtual environment is activated and dependencies are installed:"
    )
    print("   uv sync --all-extras")
    sys.exit(1)

app = typer.Typer(
    name="homelab",
    help="Smart Home K3s Lab Management CLI",
    add_completion=False,
)
console = Console()


@app.command()
def info():
    """Show environment and system information."""
    console.print("🏠 Smart Home K3s Lab Information", style="bold blue")
    console.print("=" * 50)

    try:
        print_uv_info()
    except Exception as e:
        console.print(f"❌ Error getting environment info: {e}", style="red")


@app.command()
def validate():
    """Validate the development environment setup."""
    console.print("🔍 Validating development environment...", style="yellow")

    try:
        validate_uv_environment()
        console.print("✅ Environment validation successful!", style="green")
    except Exception as e:
        console.print(f"❌ Environment validation failed: {e}", style="red")
        sys.exit(1)


@app.command()
def audit():
    """Run system audit."""
    console.print("🔍 Running system audit...", style="yellow")

    try:
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "scripts/00-system-audit.py"], check=True
        )
    except subprocess.CalledProcessError as e:
        console.print(f"❌ System audit failed: {e}", style="red")
        sys.exit(1)


@app.command()
def install():
    """Install homelab components."""
    console.print("⚙️ Installing homelab components...", style="yellow")

    try:
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "scripts/01-install-components.py"], check=True
        )
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Installation failed: {e}", style="red")
        sys.exit(1)


@app.command()
def dev_setup():
    """Setup development environment."""
    console.print("💻 Setting up development environment...", style="yellow")

    try:
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "scripts/dev-env-manager.py", "--setup-all"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Development setup failed: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    app()
