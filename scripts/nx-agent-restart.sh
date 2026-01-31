#!/usr/bin/env bash
# Idempotent restart script for Nx agent (runs on agent machines)

set -euo pipefail

if [ "${HOMELAB:-0}" != "1" ]; then
  echo "Refusing to restart: HOMELAB != 1" >&2
  exit 1
fi

# Stop any existing agent
PIDFILE="$HOME/.local/state/nx-agent.pid"
if [ -f "$PIDFILE" ]; then
  pid=$(cat "$PIDFILE")
  if kill -0 "$pid" 2>/dev/null; then
    echo "Stopping Nx agent PID $pid"
    kill "$pid" || true
    sleep 1
  fi
  rm -f "$PIDFILE"
fi

# Load encrypted config if present
if [ -f "infra/nx-agents.env.sops" ]; then
  if ! command -v sops >/dev/null 2>&1; then
    echo "ERROR: sops not installed" >&2
    exit 2
  fi
  eval "$(sops -d --input-type dotenv --output-type dotenv infra/nx-agents.env.sops)"
fi

# Ensure tailscale if required
if [ "${REQUIRE_TAILSCALE:-1}" = "1" ]; then
  if ! command -v tailscale >/dev/null 2>&1 || ! tailscale status >/dev/null 2>&1; then
    echo "REQUIRE_TAILSCALE=1 but tailscale not active" >&2
    exit 2
  fi
fi

# Start agent
MACHINE_ID=$(tailscale ip -4 2>/dev/null || echo "local-dev")
LOG_DIR="$HOME/.local/state"
mkdir -p "$LOG_DIR"
nohup bunx nx-cloud start-agent --machineId "$MACHINE_ID" > "$LOG_DIR/nx-agent.log" 2>&1 &
agent_pid=$!
echo "$agent_pid" > "$LOG_DIR/nx-agent.pid"

echo "Started Nx agent (PID $agent_pid)"
exit 0
