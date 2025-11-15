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
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing to deploy: HOMELAB != 1" >&2; exit 1; fi; if [ "${DEPLOY_CONFIRM:-}" != "yes" ]; then if [ -t 0 ]; then echo "DEPLOY_CONFIRM not set. To confirm, type "deploy" and press Enter:"; read -r _deploy_confirm; if [ "$_deploy_confirm" != "deploy" ]; then echo "Aborting deploy (confirmation not provided)" >&2; exit 1; fi; else echo "Refusing to deploy: set DEPLOY_CONFIRM=yes to proceed (non-interactive)" >&2; exit 1; fi; fi; if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN: would perform infra deployment (no actions taken)"; exit 0; fi; if [ "${REQUIRE_TAILSCALE:-0}" = "1" ]; then if ! command -v tailscale >/dev/null 2>&1; then echo "Refusing to deploy: REQUIRE_TAILSCALE=1 but tailscale CLI not found" >&2; exit 1; fi; if ! tailscale status >/dev/null 2>&1; then echo "Refusing to deploy: REQUIRE_TAILSCALE=1 but tailscale status failed or not connected" >&2; exit 1; fi; fi; echo "Infra deploy allowed"'

# Print detected homelab status and instructions
detect-homelab:
	bash -lc 'if [ -f "$HOME/.config/sops/age/keys.txt" ]; then echo "HOMELAB detected: SOPS/age key present at $HOME/.config/sops/age/keys.txt"; echo "To enable guarded actions for this shell: export HOMELAB=1"; else echo "No homelab SOPS/age key detected; HOMELAB defaults to 0"; echo "To force-enable guarded actions (use with caution): export HOMELAB=1"; fi'

# Tailscale helpers and guarded recipes
tailscale-status:
	bash -lc 'if ! command -v tailscale >/dev/null 2>&1; then echo "Tailscale not available (install on Windows host)"; exit 0; fi; tailscale status'

tailscale-join:
	bash -lc 'set -euo pipefail; if [ -f scripts/tailscale-join.sh ]; then bash scripts/tailscale-join.sh; else echo "Missing scripts/tailscale-join.sh" >&2; exit 2; fi'

tailscale-ssh-enable:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing to enable SSH: HOMELAB != 1" >&2; exit 1; fi; if ! command -v tailscale >/dev/null 2>&1; then echo "Tailscale CLI not found; ensure Tailscale is installed on Windows host" >&2; exit 2; fi; tailscale up --ssh'

tailscale-ssh-disable:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing to disable SSH: HOMELAB != 1" >&2; exit 1; fi; if ! command -v tailscale >/dev/null 2>&1; then echo "Tailscale CLI not found; nothing to do"; exit 0; fi; tailscale down'

tailscale-rotate-key:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing to rotate keys: HOMELAB != 1" >&2; exit 1; fi; echo "Rotate your Tailscale auth key in the admin console, then update infra/tailscale.env and re-encrypt to infra/tailscale.env.sops"'

tailscale-encrypt:
	bash -lc 'set -euo pipefail; if [ -z "${AGE_RECIPIENT:-}" ]; then echo "Specify AGE_RECIPIENT env var (age public recipient like age1...)" >&2; exit 2; fi; if [ -z "${TAILSCALE_AUTHKEY:-}" ]; then echo "Specify TAILSCALE_AUTHKEY env var (do not commit)" >&2; exit 2; fi; mkdir -p infra; printf "%s\n" "TAILSCALE_AUTHKEY=${TAILSCALE_AUTHKEY}" "TAILSCALE_WINDOWS_IP=${TAILSCALE_WINDOWS_IP:-}" "TAILNET=${TAILNET:-}" > infra/tailscale.env; sops --encrypt --input-type dotenv --output-type dotenv --age "${AGE_RECIPIENT}" infra/tailscale.env > infra/tailscale.env.sops; shred -u infra/tailscale.env; echo "Created infra/tailscale.env.sops (encrypted)"'

# Infrastructure recipes (Pulumi)
pulumi-preview:
	bash -lc 'set -euo pipefail; if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN: would run pulumi preview"; exit 0; fi; cd infra/pulumi-bootstrap && npm install; PULUMI_LOCAL_STATE="${PULUMI_LOCAL_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/pulumi}"; mkdir -p "$PULUMI_LOCAL_STATE"; export PULUMI_BACKEND_URL="${PULUMI_BACKEND_URL:-file://$PULUMI_LOCAL_STATE}"; if ! command -v pulumi >/dev/null 2>&1; then echo "Pulumi not installed: please run 'mise install' or add pulumi to your PATH" >&2; exit 2; fi; if ! pulumi whoami >/dev/null 2>&1; then pulumi login "$PULUMI_BACKEND_URL"; fi; pulumi preview'

pulumi-up:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing pulumi up: HOMELAB != 1" >&2; exit 1; fi; if [ "${DEPLOY_CONFIRM:-}" != "yes" ]; then if [ -t 0 ]; then echo "Type '\''deploy'\'' to confirm:"; read -r _confirm; if [ "$_confirm" != "deploy" ]; then echo "Aborted" >&2; exit 1; fi; else echo "Set DEPLOY_CONFIRM=yes for non-interactive" >&2; exit 1; fi; fi; if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN: would run pulumi up"; exit 0; fi; cd infra/pulumi-bootstrap && npm install; PULUMI_LOCAL_STATE="${PULUMI_LOCAL_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/pulumi}"; mkdir -p "$PULUMI_LOCAL_STATE"; export PULUMI_BACKEND_URL="${PULUMI_BACKEND_URL:-file://$PULUMI_LOCAL_STATE}"; if ! command -v pulumi >/dev/null 2>&1; then echo "Pulumi not installed: please run 'mise install' or add pulumi to your PATH" >&2; exit 2; fi; if ! pulumi whoami >/dev/null 2>&1; then pulumi login "$PULUMI_BACKEND_URL"; fi; pulumi up'

pulumi-destroy:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing pulumi destroy: HOMELAB != 1" >&2; exit 1; fi; if [ "${DEPLOY_CONFIRM:-}" != "yes" ]; then if [ -t 0 ]; then echo "Type '\''destroy'\'' to confirm:"; read -r _confirm; if [ "$_confirm" != "destroy" ]; then echo "Aborted" >&2; exit 1; fi; else echo "Set DEPLOY_CONFIRM=yes for non-interactive" >&2; exit 1; fi; fi; if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN: would run pulumi destroy"; exit 0; fi; cd infra/pulumi-bootstrap; PULUMI_LOCAL_STATE="${PULUMI_LOCAL_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/pulumi}"; mkdir -p "$PULUMI_LOCAL_STATE"; export PULUMI_BACKEND_URL="${PULUMI_BACKEND_URL:-file://$PULUMI_LOCAL_STATE}"; if ! command -v pulumi >/dev/null 2>&1; then echo "Pulumi not installed: please run 'mise install' or add pulumi to your PATH" >&2; exit 2; fi; if ! pulumi whoami >/dev/null 2>&1; then pulumi login "$PULUMI_BACKEND_URL"; fi; pulumi destroy'

pulumi-stack-init:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing stack init: HOMELAB != 1" >&2; exit 1; fi; cd infra/pulumi-bootstrap && npm install; PULUMI_LOCAL_STATE="${PULUMI_LOCAL_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/pulumi}"; mkdir -p "$PULUMI_LOCAL_STATE"; export PULUMI_BACKEND_URL="${PULUMI_BACKEND_URL:-file://$PULUMI_LOCAL_STATE}"; if ! command -v pulumi >/dev/null 2>&1; then echo "Pulumi not installed: please run 'mise install' or add pulumi to your PATH" >&2; exit 2; fi; if ! pulumi whoami >/dev/null 2>&1; then pulumi login "$PULUMI_BACKEND_URL"; fi; pulumi stack init "${STACK_NAME:-dev}"'

# Infrastructure recipes (Ansible)
ansible-ping:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing ansible-ping: HOMELAB != 1" >&2; exit 1; fi; if [ "${REQUIRE_TAILSCALE:-0}" = "1" ]; then if ! command -v tailscale >/dev/null 2>&1 || ! tailscale status >/dev/null 2>&1; then echo "REQUIRE_TAILSCALE=1 but Tailscale not active" >&2; exit 1; fi; fi; cd infra/ansible-bootstrap && ansible all -m ping'

ansible-deploy:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing ansible-deploy: HOMELAB != 1" >&2; exit 1; fi; if [ "${DEPLOY_CONFIRM:-}" != "yes" ]; then if [ -t 0 ]; then echo "Type '\''deploy'\'' to confirm:"; read -r _confirm; if [ "$_confirm" != "deploy" ]; then echo "Aborted" >&2; exit 1; fi; else echo "Set DEPLOY_CONFIRM=yes for non-interactive" >&2; exit 1; fi; fi; if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN: would run ansible-playbook"; exit 0; fi; if [ "${REQUIRE_TAILSCALE:-0}" = "1" ]; then if ! command -v tailscale >/dev/null 2>&1 || ! tailscale status >/dev/null 2>&1; then echo "REQUIRE_TAILSCALE=1 but Tailscale not active" >&2; exit 1; fi; fi; cd infra/ansible-bootstrap && ansible-playbook playbooks/deploy.yml'

ansible-check:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing ansible-check: HOMELAB != 1" >&2; exit 1; fi; if [ "${REQUIRE_TAILSCALE:-0}" = "1" ]; then if ! command -v tailscale >/dev/null 2>&1 || ! tailscale status >/dev/null 2>&1; then echo "REQUIRE_TAILSCALE=1 but Tailscale not active" >&2; exit 1; fi; fi; cd infra/ansible-bootstrap && ansible-playbook playbooks/deploy.yml --check --diff'

ansible-molecule-test:
	bash -lc 'set -euo pipefail; cd infra/ansible-bootstrap && molecule test'

ansible-molecule-converge:
	bash -lc 'set -euo pipefail; cd infra/ansible-bootstrap && molecule converge'

ansible-molecule-verify:
	bash -lc 'set -euo pipefail; cd infra/ansible-bootstrap && molecule verify'

ansible-molecule-destroy:
	bash -lc 'set -euo pipefail; cd infra/ansible-bootstrap && molecule destroy'

# CI validation target: syntax + tests
ci-validate:
	bash -lc 'just --dump >/dev/null; bash tests/run-tests.sh'
