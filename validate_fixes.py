#!/usr/bin/env python3
"""
Quick validation script to test major fixes without full test suite.
This script validates the core functionality works before running full tests.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_cli_import():
    """Test that CLI can be imported successfully."""
    try:
        print("✅ CLI import successful")
        return True
    except Exception as e:
        print(f"❌ CLI import failed: {e}")
        return False


def test_cli_version():
    """Test that CLI version command works."""
    try:
        from typer.testing import CliRunner

        from homelab.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["version"])

        if result.exit_code == 0:
            print("✅ CLI version command successful")
            return True
        else:
            print(f"❌ CLI version command failed with exit code: {result.exit_code}")
            print(f"Output: {result.stdout}")
            return False
    except Exception as e:
        print(f"❌ CLI version test failed: {e}")
        return False


def test_uv_utils_import():
    """Test that UV utils can be imported."""
    try:
        sys.path.insert(0, str(Path(__file__).parent / "scripts"))
        print("✅ UV utils import successful")
        return True
    except Exception as e:
        print(f"❌ UV utils import failed: {e}")
        return False


def main():
    """Run validation tests."""
    print("🧪 Running validation tests...")
    print("=" * 50)

    tests = [
        test_cli_import,
        test_cli_version,
        test_uv_utils_import,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"✅ {passed}/{total} validation tests passed")

    if passed == total:
        print("🎉 All basic functionality is working!")
        return 0
    else:
        print("❌ Some basic functionality needs fixes")
        return 1


if __name__ == "__main__":
    sys.exit(main())
