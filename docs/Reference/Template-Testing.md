# Template Testing Guide

This document explains how to run template generation tests locally and in CI, in order to validate guard rails and conditional features.

## Install dev dependencies

Use a Python virtualenv or `pipx` for the Copier CLI and install the dev/test dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pipx install copier
```

## Run tests locally (fast)

1. Unit tests (validators, pre_copy, etc.):

```bash
pytest tests/python -q
```

2. Full template validation (generate project -> run guard tests -> run tests in generated project):

```bash
copier copy --vcs-ref=HEAD . /tmp/test-homelab \
  -d project_name=test-homelab -d admin_email=test@example.com \
  -d enable_pulumi=true -d enable_ansible=true -d enable_nx_distributed=true \
  --defaults --UNSAFE

cd /tmp/test-homelab
bash tests/04_just_safety_guards.sh
bash tests/08_infra_guards.sh
pytest tests/python -q
```

**Note:** Generated projects include a `pytest.ini` file that configures `pythonpath = .` to enable importing from `hooks/` and `extensions/` packages. This ensures Python tests can import project modules correctly.

## Just tasks

- `just copier-test` installs dev deps and runs `pytest` locally.
- `just copier-validate` installs dev deps and generates a test project and runs guard tests and pytest in the generated project.

## How to Verify Locally (Devbox)

Devbox provides a reproducible Python environment with all required dependencies. This is the recommended approach for local testing and matches the CI environment configuration.

### Prerequisites

1. **Install Devbox** (if not already installed):
   ```bash
   curl -fsSL https://get.jetify.com/devbox | bash
   ```

2. **Allow direnv** to auto-detect the homelab environment:
   ```bash
   direnv allow
   ```

### Running Tests in Devbox

1. **Enter Devbox shell** (activates Python 3.13.9, pytest, and all dev dependencies):
   ```bash
   devbox shell
   ```

2. **Run unit tests** (validators, pre_copy hooks, etc.):
   ```bash
   pytest tests/python -q
   ```
   Expected output: All tests pass with green dots (17 tests as of 2025-11-16).

3. **Run full validation suite** (bash tests + Python tests):
   ```bash
   just ci-validate
   ```
   This runs all 10 bash guard tests plus Python tests.

4. **Test template generation** with full features:
   ```bash
   copier copy --vcs-ref=HEAD . /tmp/test-homelab \
     -d project_name=test-homelab \
     -d admin_email=test@example.com \
     -d npm_scope=@test \
     -d node_version=22.17.0 \
     -d enable_pulumi=true \
     -d enable_ansible=true \
     -d enable_nx_distributed=true \
     --defaults --UNSAFE

   # Validate generated project
   cd /tmp/test-homelab
   bash tests/04_just_safety_guards.sh
   bash tests/08_infra_guards.sh
   pytest tests/python -q
   ```

### Exit Devbox Shell

```bash
exit  # or Ctrl+D
```

### Troubleshooting Devbox Testing

**Issue**: `pytest: command not found` inside Devbox shell

**Solution**: Ensure you entered the shell with `devbox shell` (not just `devbox run`). Verify with:
```bash
which pytest  # Should show Devbox nix store path
pytest --version  # Should show pytest 9.0.1+
```

**Issue**: Import errors (`ModuleNotFoundError: No module named 'hooks'`)

**Solution**: Ensure `pytest.ini` exists in the project root with `pythonpath = .` setting. This is automatically created by the template.

**Issue**: Tests pass in Devbox but fail in CI

**Solution**: Check for environment-specific behavior:
- CRLF line endings (use `tr -d '\r'` in shell tests)
- Missing system commands (add skip pattern with `exit 2`)
- Hardcoded paths (use relative paths or `$HOME` variables)

**Issue**: Generated project tests fail with pip unavailable

**Solution**: The `test_template_generation.py` integration test automatically skips pip-dependent steps if pip is unavailable. This is expected in minimal environments.

### Best Practices

1. **Always test in Devbox before committing** to ensure reproducibility
2. **Run `just ci-validate` before pushing** to catch issues CI will catch
3. **Use `--defaults --UNSAFE` for copier testing** to avoid interactive prompts
4. **Clean up test artifacts** in `/tmp/test-homelab` between test runs
5. **Exit Devbox shell when done** to avoid confusion with host Python environment

## Python Testing in Generated Projects

Generated projects include a `pytest.ini` configuration file that:
- Sets `pythonpath = .` to add the project root to Python's import path
- Configures standard test discovery patterns
- Enables strict markers and test summary reporting

This allows tests in `tests/python/` to import from:
- `extensions.validators` — Jinja2 filter validators
- `hooks.pre_copy` — Pre-generation validation logic

Both `extensions/` and `hooks/` include `__init__.py` files to make them proper Python packages.

## CI integration

On the `template` branch we run `copier copy --vcs-ref=HEAD` for multiple feature combinations (all features enabled and minimal/no features), then run the guard shell tests `tests/04_just_safety_guards.sh`, `tests/08_infra_guards.sh`, and run Python tests with `pytest`.

Security guidance:
- Do not run `copier` on untrusted remote templates. For CI always use `--vcs-ref=HEAD` and `copier` from the local code in the `template` branch.
- Avoid passing secrets to Copier in CI. Keep `tailscale_authkey` and other secrets out of the template `answers`. Use the post-copy script to guide users to generate secrets locally.
- To test secret-dependent workflows temporarily, use `HOMELAB=1` in a local environment with real credentials and test interactively — CI should skip those tests.
