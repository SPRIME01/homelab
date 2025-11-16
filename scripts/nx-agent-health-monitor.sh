#!/usr/bin/env bash
# Periodic health monitor for Nx agent and cache server
# Should run as a user service or cron (every 5 minutes)

set -euo pipefail

# Guard: only run on homelab machines
if [ "${HOMELAB:-0}" != "1" ]; then
  echo "HOMELAB!=1; exiting"
  exit 0
fi

# Config
CACHE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/nx-cache"
CACHE_PID_FILE="$HOME/.local/state/nx-cache-server.pid"
CACHE_LOG="$HOME/.local/state/nx-cache-server.log"
AGENT_PID_FILE="$HOME/.local/state/nx-agent.pid"
HEALTH_LOG_DIR="$HOME/.local/state/nx-logs"
mkdir -p "$HEALTH_LOG_DIR"

log() { echo "$(date -Is) $*" >> "$HEALTH_LOG_DIR/health.log"; }

# Check tailscale connectivity if required
if [ "${REQUIRE_TAILSCALE:-1}" = "1" ]; then
  if ! command -v tailscale >/dev/null 2>&1; then
    log "Tailscale CLI missing"
  else
    if ! tailscale status >/dev/null 2>&1; then
      log "Tailscale not connected"
    fi
  fi
fi

# Check cache server is running and responsive
check_cache() {
  if [ -f "$CACHE_PID_FILE" ]; then
    pid=$(cat "$CACHE_PID_FILE" 2>/dev/null || echo "")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      # test HTTP
      host=$(tailscale ip -4 2>/dev/null || echo "127.0.0.1")
      if command -v curl >/dev/null 2>&1; then
        if curl -sf "http://$host:3333/" >/dev/null 2>&1; then
          log "Cache OK (PID $pid)"
          return 0
        else
          log "Cache HTTP unresponsive (PID $pid)"
          return 1
        fi
      else
        log "curl not available; assuming cache OK (PID $pid)"
        return 0
      fi
    else
      log "Cache PID file exists but process $pid not running"
      return 1
    fi
  else
    log "Cache PID file missing"
    return 1
  fi
}

# Check nx agent process and restart if needed
check_agent() {
  if [ -f "$AGENT_PID_FILE" ]; then
    pid=$(cat "$AGENT_PID_FILE" 2>/dev/null || echo "")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      log "Nx agent running (PID $pid)"
      return 0
    else
      log "Nx agent pid file present but process $pid not running"
      return 1
    fi
  else
    log "Nx agent pid file missing"
    return 1
  fi
}

# Restart helpers
restart_cache() {
  if command -v just >/dev/null 2>&1; then
    log "Attempting to start cache server via 'just nx-cache-server-start'"
    if just nx-cache-server-start >/dev/null 2>&1; then
      log "Cache server started"
    else
      log "Cache server failed to start"
    fi
  else
    log "just not available: cannot start cache server"
  fi
}

restart_agent() {
  if command -v just >/dev/null 2>&1; then
    log "Attempting to restart nx agent via 'just nx-start-agent'"
    if just nx-start-agent >/dev/null 2>&1; then
      log "Nx agent restarted"
    else
      log "Nx agent failed to restart"
    fi
  else
    log "just not available: cannot restart agent"
  fi
}

# Run checks with simple backoff
if ! check_cache; then
  restart_cache
fi

if ! check_agent; then
  restart_agent
fi

# Rotate logs weekly
find "$HEALTH_LOG_DIR" -type f -name "health.log" -mtime +30 -exec mv {} {}.old \; || true

exit 0
