#!/usr/bin/env python3
"""
Simple HTTP server that identifies itself as 'primary' backend.
Used for testing request mirroring - this is the main production backend.
"""

import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


class PrimaryHandler(BaseHTTPRequestHandler):
    request_count = 0

    def do_GET(self):
        PrimaryHandler.request_count += 1
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Backend-Name", "primary")
        self.send_header("X-Request-Count", str(PrimaryHandler.request_count))
        self.end_headers()

        response = {
            "backend": "primary",
            "message": "Response from primary backend",
            "path": self.path,
            "request_count": PrimaryHandler.request_count,
            "timestamp": time.time(),
        }
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else ""

        PrimaryHandler.request_count += 1
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Backend-Name", "primary")
        self.send_header("X-Request-Count", str(PrimaryHandler.request_count))
        self.end_headers()

        response = {
            "backend": "primary",
            "message": "POST received by primary backend",
            "path": self.path,
            "body_received": body,
            "request_count": PrimaryHandler.request_count,
            "timestamp": time.time(),
        }
        self.wfile.write(json.dumps(response).encode())

    def do_PUT(self):
        self.do_POST()

    def do_DELETE(self):
        self.do_GET()

    def log_message(self, format, *args):
        # Log to stdout for debugging with timestamp for uniqueness
        import datetime
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[PRIMARY-{ts}] {format % args}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), PrimaryHandler)
    print(f"Primary backend listening on port {port}")
    server.serve_forever()
