#!/usr/bin/env bash
set -euuo pipefail

# Small integration test for lib/logging.sh -> Vector HTTP wrapper
# Starts a short-lived HTTP server that captures one POST and writes its body to a file,
# then invokes the shell logger configured to send to that server and validates the payload.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
OUTFILE="$TMPDIR/request_body.json"

cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

cat > "$TMPDIR/server.py" <<'PY'
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

output_file = sys.argv[2]

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(body)
        self.send_response(200)
        self.end_headers()
        # Shutdown the server after handling one request
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format, *args):
        # Silence default logging
        return

if __name__ == '__main__':
    port = int(sys.argv[1])
    server = HTTPServer(('127.0.0.1', port), Handler)
    server.serve_forever()
PY

# Choose an available ephemeral port
PORT=$(python3 - <<PY
import socket
s=socket.socket()
s.bind(('127.0.0.1',0))
print(s.getsockname()[1])
s.close()
PY
)

# Start server
python3 "$TMPDIR/server.py" "$PORT" "$OUTFILE" &
SERVER_PID=$!

sleep 0.1

export HOMELAB_VECTOR_ENDPOINT="http://127.0.0.1:$PORT/v1/logs"
export HOMELAB_LOG_TARGET="vector"

# Source the logger
# shellcheck source=/dev/null
source "$ROOT_DIR/lib/logging.sh"

# Emit a log
MSG="test message from shell test"
log_info "$MSG"

# Wait for server to capture the request (timeout after 5s)
for i in $(seq 1 50); do
  if [ -f "$OUTFILE" ]; then break; fi
  sleep 0.1
done

if [ ! -f "$OUTFILE" ]; then
  echo "ERROR: server did not receive any request" >&2
  kill "$SERVER_PID" 2>/dev/null || true
  exit 2
fi

python3 - <<PY
import json,sys
body = open('$OUTFILE','r',encoding='utf-8').read()
try:
    outer = json.loads(body)
except Exception as e:
    print('FAIL: outer payload not valid JSON:', e)
    print('BODY:', body)
    sys.exit(3)

# Check for OTLP structure
if 'resourceLogs' not in outer:
    print('FAIL: outer JSON missing "resourceLogs" field')
    print(outer)
    sys.exit(4)

try:
    rl = outer['resourceLogs'][0]
    sl = rl['scopeLogs'][0]
    lr = sl['logRecords'][0]
    if 'body' not in lr or 'stringValue' not in lr['body']:
        print('FAIL: body.stringValue missing')
        sys.exit(5)
except Exception as e:
    print('FAIL: unexpected payload structure', e)
    sys.exit(6)

inner_raw = lr['body']['stringValue']
if not isinstance(inner_raw, str):
    print('FAIL: body.stringValue is not a string')
    print(type(inner_raw), inner_raw)
    sys.exit(7)

try:
    inner = json.loads(inner_raw)
except Exception as e:
    print('FAIL: inner message is not valid JSON:', e)
    print('INNER RAW:', inner_raw)
    sys.exit(8)

if inner.get('level') != 'info':
    print('FAIL: inner.level != info, got:', inner.get('level'))
    sys.exit(9)

if inner.get('message') != 'test message from shell test':
    print('FAIL: inner.message mismatch, got:', inner.get('message'))
    sys.exit(10)

print('OK: OTLP payload and inner JSON look correct')
PY

exit 0
