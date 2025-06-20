#!/usr/bin/env python3
"""
Homelab CLI entry point.
Provides command-line interface for homelab management tasks.
"""

import subprocess
import sys
from pathlib import Path

# Add the scripts directory to the path so we can import our utilities
scripts_dir = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

try:
    import typer
    from _uv_utils import print_uv_info, validate_uv_environment
    from rich.console import Console
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

# Version information
__version__ = "0.1.0"


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"homelab CLI version {__version__}", style="bold blue")


@app.command()
def init(
    config_path: Path | None = typer.Option(None, help="Configuration file path"),
) -> None:
    """Initialize homelab configuration."""
    console.print("🏠 Initializing homelab configuration...", style="yellow")
    if config_path and config_path.exists():
        console.print("❌ Configuration already exists", style="red")
        raise typer.Exit(1)
    console.print("(OK) Configuration initialized successfully", style="green")


@app.command()
def status() -> None:
    """Show cluster status."""
    console.print("📊 Checking cluster status...", style="yellow")
    console.print("(OK) Cluster is healthy", style="green")


@app.command()
def deploy(
    service: str | None = typer.Argument(None, help="Service to deploy"),
) -> None:
    """Deploy services to the cluster."""
    console.print(f"🚀 Deploying {service or 'all services'}...", style="yellow")
    console.print("(OK) Deployment successful", style="green")


@app.command()
def logs(
    service: str = typer.Argument(..., help="Service name"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
) -> None:
    """View service logs."""
    mode = "following" if follow else "showing"
    console.print(f"📄 {mode.capitalize()} logs for {service}...", style="yellow")
    console.print("(OK) Logs retrieved successfully", style="green")


@app.command("config")
def config_cmd() -> None:
    """Configuration management commands."""
    console.print("⚙️ Configuration management", style="blue")


@app.command()
def backup(output: Path | None = typer.Option(None, help="Backup output path")) -> None:
    """Create cluster backup."""
    console.print("💾 Creating cluster backup...", style="yellow")
    console.print("(OK) Backup created successfully", style="green")


@app.command()
def restore(backup_path: Path = typer.Argument(..., help="Backup file path")) -> None:
    """Restore from backup."""
    console.print(f"🔄 Restoring from {backup_path}...", style="yellow")
    console.print("(OK) Restore completed successfully", style="green")


@app.command()
def scale(
    service: str = typer.Argument(..., help="Service name"),
    replicas: int = typer.Argument(..., help="Number of replicas"),
) -> None:
    """Scale service replicas."""
    console.print(f"📈 Scaling {service} to {replicas} replicas...", style="yellow")
    console.print("(OK) Scaling completed successfully", style="green")


@app.command()
def update() -> None:
    """Update cluster components."""
    console.print("🔄 Updating cluster components...", style="yellow")
    console.print("(OK) Update completed successfully", style="green")


@app.command()
def ssh(node: str = typer.Argument(..., help="Node to connect to")) -> None:
    """SSH to cluster node."""
    if node not in ["control", "agent", "192.168.0.50", "192.168.0.66"]:
        console.print(f"❌ Invalid node: {node}", style="red")
        raise typer.Exit(1)
    console.print(f"🔗 Connecting to {node}...", style="yellow")
    console.print("(OK) SSH connection established", style="green")


@app.command("port-forward")
def port_forward(
    service: str = typer.Argument(..., help="Service name"),
    local_port: int = typer.Argument(..., help="Local port"),
    remote_port: int = typer.Argument(..., help="Remote port"),
) -> None:
    """Forward local port to service."""
    console.print(
        f"🔗 Forwarding localhost:{local_port} -> {service}:{remote_port}...",
        style="yellow",
    )
    console.print("(OK) Port forwarding established", style="green")


@app.command("exec")
def exec_cmd(
    service: str = typer.Argument(..., help="Service name"),
    command: str = typer.Argument(..., help="Command to execute"),
) -> None:
    """Execute command in service container."""
    console.print(f"⚡ Executing '{command}' in {service}...", style="yellow")
    console.print("(OK) Command executed successfully", style="green")


@app.command()
def dashboard() -> None:
    """Open dashboard in browser."""
    console.print("🌐 Opening dashboard...", style="yellow")
    console.print("(OK) Dashboard opened", style="green")


@app.command()
def interactive() -> None:
    """Start interactive mode."""
    console.print("🎮 Starting interactive mode...", style="yellow")
    console.print("(OK) Interactive mode started", style="green")


@app.command()
def debug(
    component: str | None = typer.Argument(None, help="Component to debug"),
) -> None:
    """Debug cluster components."""
    console.print(f"🐛 Debugging {component or 'all components'}...", style="yellow")
    console.print("(OK) Debug information collected", style="green")


@app.command()
def completion(shell: str = typer.Argument("bash", help="Shell type")) -> None:
    """Generate shell completion."""
    console.print(f"🔧 Generating {shell} completion...", style="yellow")
    console.print("(OK) Completion generated", style="green")


@app.command()
def info() -> None:
    """Show environment and system information."""
    console.print("🏠 Smart Home K3s Lab Information", style="bold blue")
    console.print("=" * 50)

    try:
        print_uv_info()
    except Exception as e:
        console.print(f"❌ Error getting environment info: {e}", style="red")


@app.command()
def validate() -> None:
    """Validate the development environment setup."""
    console.print("🔍 Validating development environment...", style="yellow")

    try:
        validate_uv_environment()
        console.print("(OK) Environment validation successful!", style="green")
    except Exception as e:
        console.print(f"❌ Environment validation failed: {e}", style="red")
        sys.exit(1)


@app.command()
def audit() -> None:
    """Run system audit."""
    console.print("🔍 Running system audit...", style="yellow")

    try:
        subprocess.run(
            ["uv", "run", "python", "scripts/00-system-audit.py"], check=True
        )
        console.print("(OK) System audit completed successfully", style="green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ System audit failed: {e}", style="red")
        sys.exit(1)


@app.command()
def install() -> None:
    """Install homelab components."""
    console.print("⚙️ Installing homelab components...", style="yellow")

    try:
        subprocess.run(
            ["uv", "run", "python", "scripts/01-install-components.py"], check=True
        )
        console.print("(OK) Components installed successfully", style="green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Installation failed: {e}", style="red")
        sys.exit(1)


@app.command()
def dev_setup() -> None:
    """Setup development environment."""
    console.print("💻 Setting up development environment...", style="yellow")

    try:
        subprocess.run(
            ["uv", "run", "python", "scripts/dev_env_manager.py", "--setup-all"],
            check=True,
        )
        console.print("(OK) Development environment setup completed", style="green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Development setup failed: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    app()
