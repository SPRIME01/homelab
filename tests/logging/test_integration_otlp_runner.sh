#!/usr/bin/env bash
set -euo pipefail

# Integration test runner for OTLP payload
ROOT_DIR=$(cd "$(dirname "$0")/../../" && pwd)
TMPDIR=$(mktemp -d)

# Use fixed ports that match our mock receiver
PORTS=(43215 51417)
PAYLOAD_FILES=()
DONE_FILES=()

# Create payload and done files for each port
for port in "${PORTS[@]}"; do
  PAYLOAD_FILES+=("$TMPDIR/payload_${port}.json")
  DONE_FILES+=("$TMPDIR/done_${port}")
done

# Ensure the mock receiver payload directory exists
PAYLOAD_DIR="/tmp/otlp-test"
mkdir -p "$PAYLOAD_DIR"

cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

# Test with the first port
PORT=${PORTS[0]}
export HOMELAB_VECTOR_ENDPOINT="http://127.0.0.1:$PORT/v1/logs"

source "$ROOT_DIR/lib/logging.sh"
export HOMELAB_LOG_TARGET=vector

log_info "integration test" "integration=true"

# Wait for payload to be received by the mock receiver
SECS=0
RECEIVED=false
for port in "${PORTS[@]}"; do
  PAYLOAD_FILE="${PAYLOAD_DIR}/payload_${port}.json"
  DONE_FILE="${PAYLOAD_DIR}/done_${port}"

  while [ ! -f "$DONE_FILE" ] && [ $SECS -lt 6 ]; do
    sleep 1
    SECS=$((SECS+1))
  done

  if [ -f "$PAYLOAD_FILE" ]; then
    RECEIVED=true
    break
  fi
done

if [ "$RECEIVED" = false ]; then
  echo "FAIL: Server did not receive a payload on any of the ports"
  exit 2
fi

PY_VALIDATOR="$TMPDIR/validate_payload.py"
cat > "$PY_VALIDATOR" <<'PY'
import json,sys
payload_path = sys.argv[1]
try:
    b = open(payload_path,'rb').read()
    data = json.loads(b.decode('utf-8'))
except Exception as e:
    print('FAIL: payload is not valid JSON:', e)
    sys.exit(2)

if 'resourceLogs' not in data:
    print('FAIL: resourceLogs not found in payload')
    sys.exit(2)

try:
    rl = data['resourceLogs'][0]
    sl = rl['scopeLogs'][0]
    lr = sl['logRecords'][0]
    if 'body' not in lr or 'stringValue' not in lr['body']:
        print('FAIL: body.stringValue missing')
        sys.exit(2)
except Exception as e:
    print('FAIL: unexpected payload structure', e)
    sys.exit(2)

print('PASS: integration OTLP payload received and valid')
PY

# Find which port received the payload and validate it
for port in "${PORTS[@]}"; do
  PAYLOAD_FILE="${PAYLOAD_DIR}/payload_${port}.json"
  if [ -f "$PAYLOAD_FILE" ]; then
    python3 "$PY_VALIDATOR" "$PAYLOAD_FILE"
    exit 0
  fi
done

echo "FAIL: No valid payload found"
exit 2
