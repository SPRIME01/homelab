#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
OUTFILE="$TMPDIR/request_body.txt"

cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

# Test 1: endpoint down (no server listening) -> logger should fail gracefully (exit 0)
export HOMELAB_VECTOR_ENDPOINT="http://127.0.0.1:59999/v1/logs"
export HOMELAB_LOG_TARGET="vector"

# Source the logger
# shellcheck source=/dev/null
source "$ROOT_DIR/lib/logging.sh"

set +e
log_info "should not crash when endpoint down"
RC=$?
set -e

if [ $RC -ne 0 ]; then
  echo "FAIL: logger exited non-zero when endpoint down: $RC" >&2
  exit 1
fi

# Test 2: curl missing -> simulate by temporarily PATH without curl
OLD_PATH="$PATH"
export PATH="/usr/bin"  # typically still has curl, but we remove curl if present

# If curl exists in /usr/bin, try to mask it by moving it (requires sudo) — instead we'll simulate
# by setting HOMELAB_LOG_TARGET to stdout and ensuring no crash when curl isn't available.
export HOMELAB_LOG_TARGET="vector"

# Create a fake wrapper that returns non-zero for command -v curl
fake_path="$TMPDIR/fakebin"
mkdir -p "$fake_path"
cat > "$fake_path/curl" <<'SH'
#!/usr/bin/env bash
exit 127
SH
chmod +x "$fake_path/curl"

export PATH="$fake_path:$OLD_PATH"

set +e
log_info "should not crash when curl fails"
RC2=$?
set -e

if [ $RC2 -ne 0 ]; then
  echo "FAIL: logger exited non-zero when curl missing/failing: $RC2" >&2
  exit 1
fi

echo "OK: failure-mode behavior passed"
