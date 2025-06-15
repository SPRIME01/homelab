#!/usr/bin/env python3
"""
Test scrip    # Test 4: Check if UV can read the project configuration
    try:
        # Use 'uv pip list' to check if UV can work with the project
        result = subprocess.run(
            ["uv", "pip", "list"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ UV can read project configuration")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ UV project check failed (this is normal if dependencies aren't synced yet): {e}")

    # Test 5: Check if dependencies are already installed
    try:
        result = subprocess.run(
            ["uv", "run", "python", "-c", "import rich; print('Dependencies are installed')"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Core dependencies are installed")
    except subprocess.CalledProcessError:
        print("⚠️ Dependencies not yet installed - run 'uv sync --all-extras' to install them")UV setup and environment.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Test UV environment setup."""
    project_root = Path(__file__).parent.parent

    print("🔍 Testing UV Environment Setup")
    print("=" * 40)

    # Test 1: Check if UV is available
    try:
        result = subprocess.run(
            ["uv", "--version"], capture_output=True, text=True, check=True
        )
        print(f"✅ UV Version: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ UV not found. Please install with: pip install uv")
        return False

    # Test 2: Check pyproject.toml exists
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        print("✅ pyproject.toml found")
    else:
        print("❌ pyproject.toml not found")
        return False

    # Test 3: Check virtual environment
    venv_path = project_root / ".venv"
    if venv_path.exists():
        print("✅ Virtual environment exists")
    else:
        print("⚠️ Virtual environment not found - this is expected on first run")

    # Test 4: Try to sync dependencies (dry run)
    try:
        result = subprocess.run(
            ["uv", "sync", "--dry-run"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        print("✅ UV sync dry-run successful")
    except subprocess.CalledProcessError as e:
        print(f"❌ UV sync dry-run failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

    print("\n🎉 UV environment setup validation complete!")
    print("\n📝 Next steps:")
    print("1. Run: uv sync --all-extras")
    print(
        "2. Activate environment: .venv\\Scripts\\activate (Windows) or source .venv/bin/activate (Linux)"
    )
    print("3. Run scripts with: uv run python scripts/<script_name>.py")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
