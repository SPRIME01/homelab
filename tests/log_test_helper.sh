#!/usr/bin/env bash
set -euo pipefail

# Helper to run a single-request HTTP server for tests.
# Usage: start_test_server <port> <output-file>
# Prints the PID of the background server on stdout.

start_test_server() {
  local port="$1"
  local out="$2"
  local tmpdir
  tmpdir=$(mktemp -d)
  cat >"$tmpdir/server.py" <<'PY'
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
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format, *args):
        return

if __name__ == '__main__':
    port = int(sys.argv[1])
    server = HTTPServer(('127.0.0.1', port), Handler)
    server.serve_forever()
PY

  python3 "$tmpdir/server.py" "$port" "$out" &
  echo $!
}

stop_test_server() {
  local pid="$1"
  kill "$pid" 2>/dev/null || true
}

# Export functions for callers that source this file
export -f start_test_server
export -f stop_test_server
