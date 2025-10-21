#!/usr/bin/env bash
set -euo pipefail

# Integration test runner for OTLP payload (clean copy)
ROOT_DIR=$(cd "$(dirname "$0")/../../" && pwd)
TMPDIR=$(mktemp -d)
PY_SERVER="$TMPDIR/server.py"
PAYLOAD_FILE="$TMPDIR/payload.json"
DONE_FILE="$TMPDIR/done"

PORT=$(python3 - <<'PY'
import socket
s=socket.socket()
s.bind(('127.0.0.1',0))
port=s.getsockname()[1]
s.close()
print(port)
PY
)

cat > "$PY_SERVER" <<'PY'
import http.server
import socketserver
import sys
from pathlib import Path

PORT = int(sys.argv[1])
PAYLOAD_FILE = sys.argv[2]
DONE_FILE = sys.argv[3]

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length)
        Path(PAYLOAD_FILE).write_bytes(body)
        Path(DONE_FILE).write_text('1')
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return

with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    httpd.serve_forever()
PY

python3 "$PY_SERVER" "$PORT" "$PAYLOAD_FILE" "$DONE_FILE" &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

export HOMELAB_VECTOR_ENDPOINT="http://127.0.0.1:$PORT"

source "$ROOT_DIR/lib/logging.sh"
export HOMELAB_LOG_TARGET=vector

log_info "integration test" "integration=true"

SECS=0
while [ ! -f "$DONE_FILE" ] && [ $SECS -lt 6 ]; do
  sleep 1
  SECS=$((SECS+1))
done

if [ ! -f "$PAYLOAD_FILE" ]; then
  echo "FAIL: Server did not receive a payload"
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

python3 "$PY_VALIDATOR" "$PAYLOAD_FILE"
