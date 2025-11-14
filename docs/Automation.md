````markdown
# Automation and Safety Guards

This document describes the `just` automation in this repository and the guard rails added to prevent accidental infra actions on non-homelab machines. It documents how `HOMELAB` is detected and used, how to run `deploy` safely (interactive and non-interactive), local test commands, and the CI validation workflow.

**Key concepts and files**
- `justfile` — repository root: contains `check`, `env`, `deploy`, `detect-homelab`, and `ci-validate` targets.
- `.envrc` — auto-detects homelab by checking for the SOPS age key and sets `HOMELAB` if not already set.
- `devbox.json` — lists `just` in `packages` so it is available inside `devbox shell`.
- `tests/04_just_safety_guards.sh` and `tests/run-tests.sh` — unit tests validating the Justfile and guard behavior.
- GitHub Actions workflow: `.github/workflows/ci-validate.yml` — runs `just ci-validate` on pushes and PRs to `main`.

Environment variables and detection
- `HOMELAB` (flag):
  - When `HOMELAB=1`, guarded targets are allowed to run (subject to additional confirmation).
  - When unset or `0`, guarded targets will refuse to run.
  - This repo's `.envrc` will auto-set `HOMELAB=1` when the SOPS/age key file exists at `$HOME/.config/sops/age/keys.txt`. Direnv must be allowed locally to enable this: run `direnv allow` after pulling changes.

- `DEPLOY_CONFIRM` (confirmation gate):
  - Non-interactive runs (CI or scripts) must set `DEPLOY_CONFIRM=yes` to allow `just deploy` to proceed.
  - If `DEPLOY_CONFIRM` is not set and `just deploy` is run interactively, the recipe prompts the user to type the word `deploy` to confirm.

- `DRY_RUN` (safety/verification):
  - Setting `DRY_RUN=1` causes `just deploy` to print the actions it would take and exit without performing them.

Why this pattern?
- Two-level guards reduce risk: `HOMELAB` limits which machines can run infra operations; `DEPLOY_CONFIRM` prevents accidental automated runs; `DRY_RUN` lets you verify actions before committing them.

Detailed usage

- Quick detection check (local):

```bash
just detect-homelab
# Example output: "HOMELAB detected: SOPS/age key present at $HOME/.config/sops/age/keys.txt"
```

- Interactive local deploy (recommended for manual runs):

```bash
# If .envrc sets HOMELAB automatically you don't need to export it, otherwise:
export HOMELAB=1
just deploy
# When prompted, type: deploy
```

- Non-interactive/CI deploy (explicit):

```bash
export HOMELAB=1
export DEPLOY_CONFIRM=yes
# Optional verification step
export DRY_RUN=1
just deploy
```

Notes about the `deploy` recipe
- The `deploy` recipe intentionally contains a placeholder `echo "Infra deploy allowed"` where your real deployment commands should go (Pulumi/Terraform/Ansible, etc.).
- When you replace the placeholder with real commands, prefer an approach that respects `DRY_RUN` (e.g., wrap commands in an `if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN"; else <real-command>; fi`), or use a variable-driven `--dry-run` flag supported by your tooling.
- The `justfile` sets the recipe shell to `bash -eu -o pipefail` to enforce strict behavior inside recipes.

Testing and CI
- Local test run (runs all repository tests and new Just tests):

```bash
bash tests/run-tests.sh
```

- `tests/run-tests.sh` treats test exit code `2` as "skipped" (used by tests that require the absence or presence of local homelab age keys). The Just guard tests (`tests/04_just_safety_guards.sh`) validate:
  - `just --dump` (syntax)
  - `just deploy` fails when `HOMELAB=0`
  - `just deploy` succeeds when `HOMELAB=1` and `DEPLOY_CONFIRM=yes` (or when run interactively and the typed confirmation is provided)

- CI: The included workflow `.github/workflows/ci-validate.yml` checks out the repo, installs `just` (via apt in the example), and runs `just ci-validate` which performs `just --dump` and `bash tests/run-tests.sh`.
  - You can adapt the workflow to install `just` via a different mechanism (prebuilt binary, cargo install, etc.) depending on your CI constraints.

Devbox and environment
- `devbox.json` was updated to include `just` in `packages`, so when you `devbox shell` the `just` binary will be available in that environment. If you rely on devbox for reproducible developer environments, run:

```bash
devbox shell
# inside the shell, run:
just --version
```

- `.envrc` auto-detection requires you to accept the change with direnv:

```bash
direnv allow
```

Security notes and recommendations
- Avoid exposing `DEPLOY_CONFIRM` or other guard variables in public CI logs or untrusted environments.
- Do not programmatically set `DEPLOY_CONFIRM=yes` in arbitrary scripts unless those scripts run in a tightly controlled environment.
- When you replace the deploy placeholder, prefer idempotent infrastructure commands and consider adding additional safeguards (e.g., require a short-lived token or specific branch name for production deploys).

Where to find things
- `justfile` — repository root
- `docs/Automation.md` — this document (you are here)
- `tests/04_just_safety_guards.sh` — guard behavior tests
- `.github/workflows/ci-validate.yml` — example CI job

If you want me to replace the `deploy` placeholder with concrete Pulumi/Terraform/Ansible commands, tell me which tool and preferred flags; I'll wire them into `just deploy` with DRY_RUN-aware execution and tests.

````

