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
