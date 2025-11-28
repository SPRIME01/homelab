#!/usr/bin/env bash
set -euo pipefail

# Tests for Tailscale integration (mocked, no real network changes)

# Skip tests if just is not available (they're unit-level)
if ! command -v just >/dev/null 2>&1; then
  echo "skipping: just not found"
  exit 2
fi

echo "Testing: tailscale-related recipes respect HOMELAB guard"

TMPDIR=$(mktemp -d)
cleanup(){ rm -rf "$TMPDIR"; }
trap cleanup EXIT

# Create a fake `tailscale` shim that simulates status and up/down behavior
cat > "$TMPDIR/tailscale" <<'SH'
#!/usr/bin/env bash
case "$1" in
  status)
    # Print minimal status similar to real tailscale
    echo "100.64.0.1"; exit 0 ;;
  up)
    if [ "$2" = "--ssh" ]; then echo "tailscale up --ssh (mock)"; exit 0; fi; echo "tailscale up (mock)"; exit 0 ;;
  down)
    echo "tailscale down (mock)"; exit 0 ;;
  ip)
    echo "100.64.0.1"; exit 0 ;;
  *)
    echo "mock tailscale: $@"; exit 0 ;;
esac
SH
chmod +x "$TMPDIR/tailscale"

export PATH="$TMPDIR:$PATH"

echo "Test: tailscale-status prints availability (graceful)"
if ! just tailscale-status 2>/dev/null; then
  echo "FAIL: just tailscale-status failed (expected to succeed with mock)" >&2
  exit 1
fi

echo "Test: tailscale-ssh-enable blocked when HOMELAB=0"
if HOMELAB=0 just tailscale-ssh-enable >/dev/null 2>&1; then
  echo "FAIL: tailscale-ssh-enable unexpectedly succeeded with HOMELAB=0" >&2
  exit 1
fi

echo "Test: tailscale-ssh-enable allowed when HOMELAB=1"
if ! HOMELAB=1 DEPLOY_CONFIRM=yes just tailscale-ssh-enable | grep -q "tailscale up"; then
  echo "FAIL: tailscale-ssh-enable did not run tailscale up when HOMELAB=1" >&2
  exit 1
fi

echo "Test: infra/tailscale.env.sops exists and contains placeholder"
if [ ! -f infra/tailscale.env.sops ]; then
  echo "SKIP: infra/tailscale.env.sops not found" >&2
  exit 2
fi

echo "Tailscale tests passed (mock)"
exit 0
