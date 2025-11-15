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

# Nx distributed task execution recipes
nx-init:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing nx-init: HOMELAB != 1" >&2; exit 1; fi; echo "Installing pnpm dependencies..."; pnpm install; echo "Validating nx.json schema..."; if ! command -v jq >/dev/null 2>&1; then echo "WARN: jq not installed, skipping JSON validation" >&2; else jq empty nx.json || { echo "ERROR: nx.json is invalid JSON" >&2; exit 1; }; fi; echo "Nx workspace initialized successfully"'

nx-encrypt-config:
	bash -lc 'set -euo pipefail; if [ -z "${AGE_RECIPIENT:-}" ]; then echo "Specify AGE_RECIPIENT env var (age public key like age1...)" >&2; exit 2; fi; if [ ! -f "infra/nx-agents.env" ]; then echo "ERROR: infra/nx-agents.env not found. Create it from docs/Reference/example.nx-agents.env" >&2; exit 2; fi; sops --encrypt --input-type dotenv --output-type dotenv --age "${AGE_RECIPIENT}" infra/nx-agents.env > infra/nx-agents.env.sops; shred -u infra/nx-agents.env; echo "Created infra/nx-agents.env.sops (encrypted)"'

nx-start-agent:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing nx-start-agent: HOMELAB != 1" >&2; exit 1; fi; if [ "${REQUIRE_TAILSCALE:-1}" = "1" ]; then if ! command -v tailscale >/dev/null 2>&1 || ! tailscale status >/dev/null 2>&1; then echo "REQUIRE_TAILSCALE=1 but Tailscale not active" >&2; exit 1; fi; fi; if [ ! -f "$HOME/.config/sops/age/keys.txt" ]; then echo "ERROR: SOPS age key not found at $HOME/.config/sops/age/keys.txt" >&2; exit 2; fi; echo "Decrypting nx-agents.env.sops..."; eval "$(sops -d --input-type dotenv --output-type dotenv infra/nx-agents.env.sops)"; if [ -z "${NX_SHARED_SECRET:-}" ]; then echo "ERROR: NX_SHARED_SECRET not set in decrypted config" >&2; exit 1; fi; MACHINE_ID="$(tailscale ip -4 2>/dev/null || echo "local-dev")"; echo "Starting Nx agent with machine ID: $MACHINE_ID"; echo "NOTE: Manual DTE mode - agents wait for orchestrator to assign tasks"; echo "Run this command on each agent machine, then run just nx-distributed-build on orchestrator"; NX_CLOUD_AUTH_TOKEN="$NX_SHARED_SECRET" pnpm exec nx-cloud start-agent'

nx-distributed-build:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing nx-distributed-build: HOMELAB != 1" >&2; exit 1; fi; if [ "${DEPLOY_CONFIRM:-}" != "yes" ]; then if [ -t 0 ]; then echo "DEPLOY_CONFIRM not set. To confirm distributed build, type '\''build'\'' and press Enter:"; read -r _confirm; if [ "$_confirm" != "build" ]; then echo "Aborting distributed build (confirmation not provided)" >&2; exit 1; fi; else echo "Refusing to run: set DEPLOY_CONFIRM=yes to proceed (non-interactive)" >&2; exit 1; fi; fi; if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN: would execute nx run-many --target=build --all --parallel=3 --configuration=production"; echo "DRY RUN: would distribute tasks to agents listed in infra/nx-agents.env.sops"; exit 0; fi; echo "Running distributed build across Nx agents..."; pnpm exec nx run-many --target=build --all --parallel=3 --configuration=production'

nx-test:
	bash -lc 'set -euo pipefail; if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN: would run nx run-many --target=test --all"; exit 0; fi; pnpm exec nx run-many --target=test --all'

nx-affected-build:
	bash -lc 'set -euo pipefail; if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN: would run nx affected --target=build --base=main --parallel=3"; exit 0; fi; pnpm exec nx affected --target=build --base=main --parallel=3'

nx-cache-prune:
	bash -lc 'set -euo pipefail; CACHE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/nx-cache"; if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY RUN: would delete cache files in $CACHE_DIR older than 7 days"; if [ -d "$CACHE_DIR" ]; then find "$CACHE_DIR" -type f -mtime +7 2>/dev/null | head -n 10 || true; fi; exit 0; fi; if [ ! -d "$CACHE_DIR" ]; then echo "Cache directory $CACHE_DIR does not exist"; exit 0; fi; echo "Pruning Nx cache files older than 7 days from $CACHE_DIR..."; DELETED=$(find "$CACHE_DIR" -type f -mtime +7 -delete -print 2>/dev/null | wc -l); echo "Deleted $DELETED cache files"'

nx-cache-server-start:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing nx-cache-server-start: HOMELAB != 1" >&2; exit 1; fi; if ! command -v tailscale >/dev/null 2>&1; then echo "ERROR: Tailscale CLI not found" >&2; exit 2; fi; TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "127.0.0.1"); CACHE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/nx-cache"; mkdir -p "$CACHE_DIR"; echo "Starting Nx cache HTTP server on $TAILSCALE_IP:3333..."; echo "Cache directory: $CACHE_DIR"; if command -v npx >/dev/null 2>&1; then nohup npx http-server "$CACHE_DIR" --port 3333 --cors --host "$TAILSCALE_IP" > "$HOME/.local/state/nx-cache-server.log" 2>&1 & echo $! > "$HOME/.local/state/nx-cache-server.pid"; echo "Cache server started (PID $(cat "$HOME/.local/state/nx-cache-server.pid"))"; echo "Logs: $HOME/.local/state/nx-cache-server.log"; else echo "ERROR: npx not found (required for http-server)" >&2; exit 2; fi'

nx-cache-server-stop:
	bash -lc 'set -euo pipefail; PID_FILE="$HOME/.local/state/nx-cache-server.pid"; if [ -f "$PID_FILE" ]; then PID=$(cat "$PID_FILE"); if kill -0 "$PID" 2>/dev/null; then kill "$PID"; echo "Stopped cache server (PID $PID)"; else echo "Cache server process $PID not running"; fi; rm -f "$PID_FILE"; else echo "No cache server PID file found"; pkill -f "http-server.*nx-cache" && echo "Killed stray cache server processes" || echo "No cache server processes found"; fi'

nx-cache-health:
	bash -lc 'set -euo pipefail; if ! command -v tailscale >/dev/null 2>&1; then echo "Tailscale CLI not found, skipping health check"; exit 0; fi; TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "127.0.0.1"); CACHE_URL="http://$TAILSCALE_IP:3333"; echo "Checking Nx cache server health at $CACHE_URL..."; if command -v curl >/dev/null 2>&1; then if curl -sf "$CACHE_URL" >/dev/null 2>&1; then echo "✓ Cache server is healthy"; exit 0; else echo "✗ Cache server is unreachable"; exit 1; fi; else echo "WARN: curl not installed, cannot check health"; exit 0; fi'

nx-discover-agents:
	bash -lc 'set -euo pipefail; if [ "${HOMELAB:-0}" != "1" ]; then echo "Refusing nx-discover-agents: HOMELAB != 1 (interactive experimentation only)" >&2; exit 1; fi; echo "Discovering Nx agent candidates via Tailscale (tag:homelab-wsl2)..."; if ! command -v tailscale >/dev/null 2>&1; then echo "ERROR: Tailscale CLI not found" >&2; exit 2; fi; if command -v jq >/dev/null 2>&1; then tailscale status --json | jq -r ".Peer[] | select(.Tags[] | contains(\"tag:homelab-wsl2\")) | .TailscaleIPs[0]" | sort; else tailscale status | grep "100\." | awk "{print \$1}" | sort; fi; echo ""; echo "Copy IPs to infra/nx-agents.env as: NX_AGENT_IPS=ip1,ip2,ip3"; echo "Then encrypt with: just nx-encrypt-config"'
