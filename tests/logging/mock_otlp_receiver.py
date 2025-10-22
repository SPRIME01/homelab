#!/usr/bin/env python3
"""
Mock OTLP HTTP receiver for integration tests.

This script starts a simple HTTP server that listens on specified ports
and accepts OTLP log payloads. It logs received payloads and creates
signal files to indicate when payloads are received.
"""

import argparse
import http.server
import json
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path


class OTLPHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for OTLP logs."""

    def do_POST(self):
        """Handle POST requests with OTLP payloads."""
        content_length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(content_length)

        # Log the received payload
        print(f"Received OTLP payload on {self.server.server_address[0]}:{self.server.server_address[1]}", file=sys.stderr)

        # Try to parse and validate the payload
        try:
            payload = json.loads(body.decode('utf-8'))
            print(f"Payload keys: {list(payload.keys())}", file=sys.stderr)

            # Create a signal file to indicate payload was received
            if hasattr(self.server, 'payload_file'):
                Path(self.server.payload_file).write_bytes(body)

            if hasattr(self.server, 'done_file'):
                Path(self.server.done_file).write_text('1')

            # Send success response
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception as e:
            print(f"Error processing payload: {e}", file=sys.stderr)
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f'Error: {e}'.encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        return


def wait_for_port(port, host='127.0.0.1', timeout=10):
    """Wait for a port to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                if result == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def start_server(port, payload_file=None, done_file=None):
    """Start an HTTP server on the specified port."""
    server_address = ('127.0.0.1', port)

    # Create a custom server class to store file paths
    class CustomServer(http.server.HTTPServer):
        def __init__(self, server_address, RequestHandlerClass):
            super().__init__(server_address, RequestHandlerClass)
            self.payload_file = payload_file
            self.done_file = done_file

    httpd = CustomServer(server_address, OTLPHandler)

    # Store file paths on the server instance
    httpd.payload_file = payload_file
    httpd.done_file = done_file

    print(f"Mock OTLP receiver listening on http://127.0.0.1:{port}", file=sys.stderr)

    # Start the server in a separate thread
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # Wait for the server to be ready
    if wait_for_port(port):
        print(f"Server on port {port} is ready", file=sys.stderr)
        return httpd, server_thread
    else:
        print(f"Failed to start server on port {port}", file=sys.stderr)
        return None, None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Mock OTLP HTTP receiver')
    parser.add_argument('--ports', nargs='+', type=int, default=[43215, 51417],
                        help='Ports to listen on (default: 43215 51417)')
    parser.add_argument('--payload-dir', type=str, default='/tmp',
                        help='Directory to store payload files (default: /tmp)')
    parser.add_argument('--pid-file', type=str,
                        help='File to write server PIDs to')

    args = parser.parse_args()

    # Create payload directory if it doesn't exist
    payload_dir = Path(args.payload_dir)
    payload_dir.mkdir(exist_ok=True, parents=True)

    servers = []
    threads = []
    pids = []

    # Cleanup function
    def cleanup(signum=None, frame=None):
        print("Cleaning up servers...", file=sys.stderr)
        for server in servers:
            if server:
                server.shutdown()
        for thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=1)
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Start servers on all specified ports
    for port in args.ports:
        payload_file = payload_dir / f"payload_{port}.json"
        done_file = payload_dir / f"done_{port}"

        server, thread = start_server(port, payload_file, done_file)
        if server and thread:
            servers.append(server)
            threads.append(thread)
            pids.append(os.getpid())
        else:
            print(f"Failed to start server on port {port}", file=sys.stderr)
            cleanup()

    # Write PIDs to file if specified
    if args.pid_file:
        Path(args.pid_file).write_text(','.join(map(str, pids)))

    print(f"All servers started. PIDs: {pids}", file=sys.stderr)

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()


if __name__ == '__main__':
    main()
