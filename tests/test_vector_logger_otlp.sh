#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
BODY_OUT="$TMPDIR/request_body.json"
HEAD_OUT="$TMPDIR/request_headers.txt"

cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

cat > "$TMPDIR/server.py" <<'PY'
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

body_file = sys.argv[2]
hdr_file = sys.argv[3]

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        with open(body_file, 'w', encoding='utf-8') as f:
            f.write(body)
        with open(hdr_file, 'w', encoding='utf-8') as f:
            for k, v in self.headers.items():
                f.write(f"{k}: {v}\n")
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return

if __name__ == '__main__':
    port = int(sys.argv[1])
    server = HTTPServer(('127.0.0.1', port), Handler)
    server.serve_forever()
PY

PORT=$(python3 - <<PY
import socket
s=socket.socket()
s.bind(('127.0.0.1',0))
print(s.getsockname()[1])
s.close()
PY
)

python3 "$TMPDIR/server.py" "$PORT" "$BODY_OUT" "$HEAD_OUT" &
PID=$!

sleep 0.1

export HOMELAB_VECTOR_ENDPOINT="http://127.0.0.1:$PORT/v1/logs"
export HOMELAB_LOG_TARGET="vector"

# Source the logger
# shellcheck source=/dev/null
source "$ROOT_DIR/lib/logging.sh"

# Emit a log
log_info "otlp header test"

for i in $(seq 1 50); do
  if [ -f "$BODY_OUT" ] && [ -f "$HEAD_OUT" ]; then break; fi
  sleep 0.1
done

if [ ! -f "$BODY_OUT" ] || [ ! -f "$HEAD_OUT" ]; then
  echo "FAIL: server did not receive request" >&2
  kill "$PID" 2>/dev/null || true
  exit 2
fi

# Check Content-Type header
if ! grep -qi "content-type: application/json" "$HEAD_OUT"; then
  echo "FAIL: Content-Type header missing or not application/json" >&2
  echo "Headers:"; cat "$HEAD_OUT"
  exit 3
fi

# Validate body contains either message (string) or body with stringValue
python3 - <<PY
import json,sys
body = open('$BODY_OUT','r',encoding='utf-8').read()
try:
    outer = json.loads(body)
except Exception as e:
    print('FAIL: outer not JSON:', e)
    sys.exit(4)

if 'message' in outer:
    if not isinstance(outer['message'], str):
        print('FAIL: outer.message exists but is not a string')
        sys.exit(5)
    print('OK: found outer.message as string')
    sys.exit(0)

if 'body' in outer:
    b = outer['body']
    if isinstance(b, dict) and 'stringValue' in b:
        print('OK: found outer.body.stringValue')
        sys.exit(0)
    else:
        print('FAIL: outer.body exists but no stringValue')
        sys.exit(6)

print('FAIL: neither message nor body.stringValue found in outer')
sys.exit(7)
PY

echo "OTLP header test passed"
