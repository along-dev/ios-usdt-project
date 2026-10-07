#!/usr/bin/env python3
"""
DEPRECATED — static file server only.

Use the full FastAPI backend instead (tracking, dashboard, C2 APIs):

    ./start.sh
    # or
    python3 backend/c2_server.py --port 9000

serve.py does NOT support POST /api/track, /api/iptj, or SSE.
"""

import argparse
import http.server
import mimetypes
import socket
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent

warnings.warn(
    "serve.py is deprecated. Use ./start.sh or python3 backend/c2_server.py instead.",
    DeprecationWarning,
    stacklevel=1,
)

# Ensure Safari can load these types correctly.
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("application/octet-stream", ".dylib")
mimetypes.add_type("application/octet-stream", ".bin")
mimetypes.add_type("application/octet-stream", ".min.js")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("[serve] " + (fmt % args) + "\n")


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Static-only Coruna toolkit server — use c2_server.py instead",
    )
    parser.add_argument("-p", "--port", type=int, default=8080)
    parser.add_argument("-b", "--bind", default="0.0.0.0")
    args = parser.parse_args()

    ip = local_ip()
    print("=" * 60)
    print("WARNING: serve.py is DEPRECATED (static files only, no API).")
    print("Use: ./start.sh  OR  python3 backend/c2_server.py --port 9000")
    print("=" * 60)
    print("Coruna local test server")
    print("Root:", ROOT)
    print("Bind:", f"{args.bind}:{args.port}")
    print("On this Mac : http://127.0.0.1:{}/group.html".format(args.port))
    print("On test iOS : http://{}:{}/group.html".format(ip, args.port))
    print("=" * 60)
    print("Use an isolated lab network and authorized devices only.")
    print("Press Ctrl+C to stop.")
    print()

    server = http.server.ThreadingHTTPServer((args.bind, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
