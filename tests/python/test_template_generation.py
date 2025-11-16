import subprocess
import tempfile
from pathlib import Path
from copier import run_copy


def run_cmd(cmd, cwd=None):
    print("running:", cmd)
    subprocess.check_call(cmd.split(), cwd=cwd)


def test_generate_all_features(tmp_path: Path):
    dst = tmp_path / "test-all"
    dst.mkdir()

    answers = {
        "project_name": "test-homelab",
        "admin_email": "test@example.com",
        "enable_pulumi": True,
        "enable_ansible": True,
        "enable_nx_distributed": True,
    }

    # Use the local repo as the template source
    # Trust local template so pre/post tasks and jinja extensions can run in tests
    # Provide defaults True to avoid interactive prompts during CI
    run_copy(".", str(dst), data=answers, vcs_ref="HEAD", unsafe=True, defaults=True)

    # Sanity checks
    assert (dst / "README.md").exists(), "README.md missing in generated project"

    # Run core guard shell tests (copied into generated project tests/)
    run_cmd("bash tests/04_just_safety_guards.sh", cwd=str(dst))
    run_cmd("bash tests/08_infra_guards.sh", cwd=str(dst))

    # Run Python tests inside generated project
    # Some python installations in CI may not have pip available.
    # Try to upgrade pip and install pytest, but skip inner test if pip missing.
    try:
        run_cmd("python -m pip --version", cwd=str(dst))
    except Exception:
        print("SKIP: pip not available in generated project python; skipping inner pytest")
        return

    run_cmd("python -m pip install --upgrade pip", cwd=str(dst))
    run_cmd("python -m pip install pytest", cwd=str(dst))
    run_cmd("pytest tests/python -q", cwd=str(dst))


def test_generate_minimal_features(tmp_path: Path):
    dst = tmp_path / "test-min"
    dst.mkdir()

    answers = {
        "project_name": "minimal-lab",
        "admin_email": "test@example.com",
        "enable_pulumi": False,
        "enable_ansible": False,
        "enable_nx_distributed": False,
    }

    # Trust local template for test harness
    run_copy(".", str(dst), data=answers, vcs_ref="HEAD", unsafe=True, defaults=True)

    # pulumi package should not be present
    assert not (dst / "packages/pulumi-bootstrap").exists()

    # Run essential guard tests
    run_cmd("bash tests/04_just_safety_guards.sh", cwd=str(dst))
