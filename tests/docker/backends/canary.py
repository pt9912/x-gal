#!/usr/bin/env python3
"""
Simple HTTP server that identifies itself as 'canary' backend.
Used for testing traffic splitting.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

class CanaryHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('X-Backend-Name', 'canary')
        self.end_headers()

        response = {
            "backend": "canary",
            "message": "Response from canary backend",
            "path": self.path
        }
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        self.do_GET()

    def do_PUT(self):
        self.do_GET()

    def do_DELETE(self):
        self.do_GET()

    def log_message(self, format, *args):
        # Suppress default logging
        pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), CanaryHandler)
    print(f"Canary backend listening on port {port}")
    server.serve_forever()
