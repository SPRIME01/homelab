# HOMELAB flag: set `HOMELAB=1` in the environment on trusted homelab machines.
# The recipes reference the environment variable with a shell default of 0.

# Use bash with strict flags so recipes run with `-e -u -o pipefail`.
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# Safe diagnostic targets
check:
	bash -lc 'mise doctor || true; devbox doctor || true'

env:
	bash -lc 'printenv | sort'

# Guarded deployment target — blocked unless HOMELAB=1
# This recipe supports interactive confirmation (type "deploy")
# or non-interactive confirmation via DEPLOY_CONFIRM=yes and DRY_RUN support.
deploy:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing to deploy: HOMELAB != 1" >&2; exit 1; fi; if [ "${DEPLOY_CONFIRM:-}" != "yes" ]; then if [ -t 0 ]; then echo "DEPLOY_CONFIRM not set. To confirm, type \"deploy\" and press Enter:"; read -r _deploy_confirm; if [ "$_deploy_confirm" != "deploy" ]; then echo "Aborting deploy (confirmation not provided)" >&2; exit 1; fi; else echo "Refusing to deploy: set DEPLOY_CONFIRM=yes to proceed (non-interactive)" >&2; exit 1; fi; fi; if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN: would perform infra deployment (no actions taken)"; exit 0; fi; echo "Infra deploy allowed"'

# Print detected homelab status and instructions
detect-homelab:
	bash -lc 'if [ -f "$HOME/.config/sops/age/keys.txt" ]; then echo "HOMELAB detected: SOPS/age key present at $HOME/.config/sops/age/keys.txt"; echo "To enable guarded actions for this shell: export HOMELAB=1"; else echo "No homelab SOPS/age key detected; HOMELAB defaults to 0"; echo "To force-enable guarded actions (use with caution): export HOMELAB=1"; fi'

# CI validation target: syntax + tests
ci-validate:
	bash -lc 'just --dump >/dev/null; bash tests/run-tests.sh'
