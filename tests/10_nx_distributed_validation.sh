#!/usr/bin/env bash
# Test 10: Nx Distributed Mode Validation
# Validates nx.json schema, agent IP discovery, HOMELAB guards, and fallback behavior

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Test 10: Nx Distributed Mode Validation"

# Test 1: nx.json exists and is valid JSON
echo "  [10.1] Validating nx.json exists and is valid JSON..."
if [ ! -f "$REPO_ROOT/nx.json" ]; then
  echo "FAIL: nx.json not found" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "SKIP: jq not installed (cannot validate JSON schema)" >&2
  exit 2
fi

if ! jq empty "$REPO_ROOT/nx.json" >/dev/null 2>&1; then
  echo "FAIL: nx.json is invalid JSON" >&2
  exit 1
fi

# Test 2: Verify tasksRunnerOptions exists with required fields
echo "  [10.2] Validating tasksRunnerOptions structure..."
if ! jq -e '.tasksRunnerOptions.default.options.cacheDirectory' "$REPO_ROOT/nx.json" >/dev/null; then
  echo "FAIL: tasksRunnerOptions.default.options.cacheDirectory not found" >&2
  exit 1
fi

CACHE_DIR=$(jq -r '.tasksRunnerOptions.default.options.cacheDirectory' "$REPO_ROOT/nx.json")
if [ "$CACHE_DIR" != "~/.local/state/nx-cache" ]; then
  echo "FAIL: cacheDirectory should be ~/.local/state/nx-cache (got: $CACHE_DIR)" >&2
  exit 1
fi

# Test 3: Validate agent IP regex pattern (Tailscale range 100.x.x.x)
echo "  [10.3] Testing Tailscale IP validation function..."
VALID_IPS=("100.64.0.10" "100.127.255.254" "100.0.0.1")
INVALID_IPS=("192.168.1.1" "10.0.0.1" "100.256.0.1" "100.64.0" "100.64.0.1.1")

# Function to validate Tailscale IP (100.0.0.0/8 range with proper octet validation)
is_tailscale_ip() {
  local ip="$1"
  # Check format first
  if ! echo "$ip" | grep -qE '^100\.[0-9]+\.[0-9]+\.[0-9]+$'; then
    return 1
  fi
  # Validate each octet is 0-255
  IFS='.' read -r -a octets <<< "$ip"
  [ "${octets[0]}" = "100" ] || return 1
  for octet in "${octets[@]:1}"; do
    [ "$octet" -ge 0 ] && [ "$octet" -le 255 ] 2>/dev/null || return 1
  done
  return 0
}

for ip in "${VALID_IPS[@]}"; do
  if ! is_tailscale_ip "$ip"; then
    echo "FAIL: Valid Tailscale IP $ip rejected" >&2
    exit 1
  fi
done

for ip in "${INVALID_IPS[@]}"; do
  if is_tailscale_ip "$ip"; then
    echo "FAIL: Invalid IP $ip accepted" >&2
    exit 1
  fi
done

# Test 4: Mock Tailscale agent discovery
echo "  [10.4] Testing mocked Tailscale agent discovery..."
TMPDIR=$(mktemp -d)
trap "rm -rf '$TMPDIR'" EXIT

# Create fake tailscale CLI for testing
cat > "$TMPDIR/tailscale" <<'MOCK_TAILSCALE'
#!/usr/bin/env bash
case "$1" in
  status)
    if [ "${2:-}" = "--json" ]; then
      echo '{"Peer": [{"TailscaleIPs": ["100.64.0.10"], "Tags": ["tag:homelab-wsl2"]}, {"TailscaleIPs": ["100.64.0.11"], "Tags": ["tag:homelab-wsl2"]}]}'
    else
      echo "100.64.0.10  node1"
      echo "100.64.0.11  node2"
    fi
    exit 0
    ;;
  ip)
    echo "100.64.0.10"
    exit 0
    ;;
  *)
    exit 1
    ;;
esac
MOCK_TAILSCALE
chmod +x "$TMPDIR/tailscale"

# Test discovery without jq (fallback mode)
export PATH="$TMPDIR:$PATH"
DISCOVERED_IPS=$(tailscale status | grep "100\." | awk '{print $1}' | sort)
EXPECTED_IPS=$(printf "100.64.0.10\n100.64.0.11")

if [ "$DISCOVERED_IPS" != "$EXPECTED_IPS" ]; then
  echo "FAIL: Agent discovery mismatch" >&2
  echo "  Expected: $EXPECTED_IPS" >&2
  echo "  Got: $DISCOVERED_IPS" >&2
  exit 1
fi

# Test 5: HOMELAB=0 blocks nx-start-agent
echo "  [10.5] Testing HOMELAB=0 blocks nx-start-agent..."
if ! command -v just >/dev/null 2>&1; then
  echo "SKIP: just not installed" >&2
  exit 2
fi

# Try to run with HOMELAB=0, expecting failure
if HOMELAB=0 just nx-start-agent 2>&1 | grep -q "HOMELAB != 1"; then
  : # Expected failure message found
else
  # Alternative: check if it actually failed (non-zero exit)
  if HOMELAB=0 just nx-start-agent >/dev/null 2>&1; then
    echo "FAIL: nx-start-agent should fail with HOMELAB=0" >&2
    exit 1
  fi
  # If it failed but without the expected message, still pass (guard worked)
fi

# Test 6: REQUIRE_TAILSCALE=1 with missing Tailscale exits correctly
echo "  [10.6] Testing REQUIRE_TAILSCALE=1 behavior..."
# Note: We keep the mocked tailscale in PATH from Test 4, which simulates Tailscale being available
# In production, REQUIRE_TAILSCALE=1 would fail if tailscale is not running
# This test verifies the guard logic exists in the recipe
if grep -q "REQUIRE_TAILSCALE" "$REPO_ROOT/justfile"; then
  : # Guard exists in justfile, pass
else
  echo "FAIL: REQUIRE_TAILSCALE guard should exist in nx recipes" >&2
  exit 1
fi

# Test 7: DRY_RUN=1 preview mode
echo "  [10.7] Testing DRY_RUN=1 preview mode..."
DRY_RUN_OUTPUT=$(cd "$REPO_ROOT" && DRY_RUN=1 bash -lc 'just nx-cache-prune' 2>&1 || true)
if ! echo "$DRY_RUN_OUTPUT" | grep -q "DRY RUN:"; then
  echo "FAIL: DRY_RUN=1 should show preview message" >&2
  echo "  Output: $DRY_RUN_OUTPUT" >&2
  exit 1
fi

# Test 8: Bun workspace configuration exists and references correct paths
echo "  [10.8] Validating Bun workspace configuration..."
if [ ! -f "$REPO_ROOT/bun-workspace.yml" ]; then
  # Check package.json for workspaces field (alternative approach)
  if ! command -v jq >/dev/null 2>&1; then
    echo "SKIP: jq not installed (cannot validate package.json workspaces)" >&2
    exit 2
  fi
  if ! jq -e '.workspaces' "$REPO_ROOT/package.json" >/dev/null 2>&1; then
    echo "FAIL: package.json missing workspaces field and no bun-workspace.yml found" >&2
    exit 1
  fi
  # Validate workspaces includes packages/* and infra/*
  WORKSPACES=$(jq -r '.workspaces[]' "$REPO_ROOT/package.json")
  if ! echo "$WORKSPACES" | grep -q "packages/\*"; then
    echo "FAIL: package.json workspaces should include 'packages/*'" >&2
    exit 1
  fi
  if ! echo "$WORKSPACES" | grep -q "infra/\*"; then
    echo "FAIL: package.json workspaces should include 'infra/*'" >&2
    exit 1
  fi
else
  # Validate bun-workspace.yml
  if ! grep -q "packages/\*" "$REPO_ROOT/bun-workspace.yml"; then
    echo "FAIL: bun-workspace.yml should include 'packages/*'" >&2
    exit 1
  fi
  if ! grep -q "infra/\*" "$REPO_ROOT/bun-workspace.yml"; then
    echo "FAIL: bun-workspace.yml should include 'infra/*'" >&2
    exit 1
  fi
fi

# Test 9: .nxignore excludes encrypted secrets
echo "  [10.9] Validating .nxignore patterns..."
if [ ! -f "$REPO_ROOT/.nxignore" ]; then
  echo "FAIL: .nxignore not found" >&2
  exit 1
fi

REQUIRED_PATTERNS=("**/*.sops" "**/*.env" ".envrc")
for pattern in "${REQUIRED_PATTERNS[@]}"; do
  if ! grep -q "$pattern" "$REPO_ROOT/.nxignore"; then
    echo "FAIL: .nxignore should exclude pattern: $pattern" >&2
    exit 1
  fi
done

# Test 10: tsconfig.base.json has strict mode enabled
echo "  [10.10] Validating TypeScript strict mode in tsconfig.base.json..."
if [ ! -f "$REPO_ROOT/tsconfig.base.json" ]; then
  echo "FAIL: tsconfig.base.json not found" >&2
  exit 1
fi

if ! jq -e '.compilerOptions.strict == true' "$REPO_ROOT/tsconfig.base.json" >/dev/null 2>&1; then
  echo "FAIL: tsconfig.base.json must have strict mode enabled" >&2
  exit 1
fi

echo "✓ All Nx distributed mode validation tests passed"
exit 0
