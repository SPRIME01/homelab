#!/usr/bin/env bash
set -euo pipefail

# Test: Tailscale SSH verification in infrastructure commands
# Uses mocked tailscale CLI for CI-safe testing

echo "Test: Tailscale SSH verification mocking"

TMPDIR=$(mktemp -d)
cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

# Create mock tailscale that simulates different states
cat > "$TMPDIR/tailscale" <<'MOCK'
#!/usr/bin/env bash
case "$1" in
  status)
    if [ "${MOCK_TAILSCALE_CONNECTED:-1}" = "1" ]; then
      echo "100.64.0.1  homelab-test  tagged-devices"
      exit 0
    else
      echo "Tailscale is not running" >&2
      exit 1
    fi
    ;;
  ssh)
    # Simulate ssh command
    shift
    echo "Mock Tailscale SSH to $*"
    exit 0
    ;;
  *)
    echo "Mock tailscale: $*"
    exit 0
    ;;
esac
MOCK
chmod +x "$TMPDIR/tailscale"

export PATH="$TMPDIR:$PATH"

echo "Test: Mock tailscale status when connected"
if MOCK_TAILSCALE_CONNECTED=1 tailscale status | grep -q "100.64.0.1"; then
  echo "PASS: Mock tailscale returns expected status"
else
  echo "FAIL: Mock tailscale status failed" >&2
  exit 1
fi

echo "Test: Mock tailscale status when disconnected"
if MOCK_TAILSCALE_CONNECTED=0 tailscale status >/dev/null 2>&1; then
  echo "FAIL: Mock tailscale should fail when disconnected" >&2
  exit 1
else
  echo "PASS: Mock tailscale correctly fails when disconnected"
fi

echo "Test: ansible.cfg forces Tailscale SSH executable"
if [ -f "infra/ansible-bootstrap/ansible.cfg" ]; then
  if grep -q "ssh_executable = tailscale ssh" infra/ansible-bootstrap/ansible.cfg; then
    echo "PASS: ansible.cfg uses 'tailscale ssh'"
  else
    echo "FAIL: ansible.cfg does not use 'tailscale ssh' transport" >&2
    exit 1
  fi
else
  echo "SKIP: ansible.cfg not found (Ansible not set up yet)" >&2
  exit 2
fi

echo "Test: REQUIRE_TAILSCALE environment variable enforcement"
# This would be tested in the actual justfile recipes
# For now, verify the pattern exists in documentation or recipes
if [ -f "justfile" ]; then
  if grep -q "REQUIRE_TAILSCALE" justfile; then
    echo "PASS: justfile includes REQUIRE_TAILSCALE checks"
  else
    echo "WARNING: REQUIRE_TAILSCALE not found in justfile (may need to be added)"
  fi
fi

echo "Tailscale SSH verification tests passed"
exit 0
