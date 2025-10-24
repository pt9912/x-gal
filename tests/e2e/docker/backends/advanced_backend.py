#!/usr/bin/env python3
"""
Advanced backend service that identifies itself based on environment variables.
Used for testing advanced routing capabilities.
"""

import json
import os
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# Get backend configuration from environment
BACKEND_NAME = os.getenv("BACKEND_NAME", "default")
BACKEND_VERSION = os.getenv("BACKEND_VERSION", "v1")
BACKEND_TYPE = os.getenv("BACKEND_TYPE", "standard")
BACKEND_REGION = os.getenv("BACKEND_REGION", "us")


class AdvancedBackendHandler(BaseHTTPRequestHandler):
    request_count = 0

    def do_GET(self):
        """Handle GET requests."""
        AdvancedBackendHandler.request_count += 1
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Backend-Name", BACKEND_NAME)
        self.send_header("X-Backend-Version", BACKEND_VERSION)
        self.send_header("X-Backend-Type", BACKEND_TYPE)
        self.send_header("X-Backend-Region", BACKEND_REGION)
        self.send_header("X-Request-Count", str(AdvancedBackendHandler.request_count))
        self.end_headers()

        # Extract request headers and query params
        headers = {key: value for key, value in self.headers.items()}

        # Parse query parameters
        query_params = {}
        if "?" in self.path:
            query_string = self.path.split("?", 1)[1]
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    query_params[key] = value
                else:
                    query_params[param] = ""

        response = {
            "backend": {
                "name": BACKEND_NAME,
                "version": BACKEND_VERSION,
                "type": BACKEND_TYPE,
                "region": BACKEND_REGION,
            },
            "request": {
                "method": "GET",
                "path": self.path.split("?")[0],
                "query_params": query_params,
                "headers": headers,
                "request_count": AdvancedBackendHandler.request_count,
            },
            "timestamp": time.time(),
            "message": f"Response from {BACKEND_NAME} backend ({BACKEND_VERSION})",
        }

        self.wfile.write(json.dumps(response, indent=2).encode())

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else ""

        AdvancedBackendHandler.request_count += 1
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Backend-Name", BACKEND_NAME)
        self.send_header("X-Backend-Version", BACKEND_VERSION)
        self.send_header("X-Backend-Type", BACKEND_TYPE)
        self.send_header("X-Backend-Region", BACKEND_REGION)
        self.send_header("X-Request-Count", str(AdvancedBackendHandler.request_count))
        self.end_headers()

        # Extract headers
        headers = {key: value for key, value in self.headers.items()}

        response = {
            "backend": {
                "name": BACKEND_NAME,
                "version": BACKEND_VERSION,
                "type": BACKEND_TYPE,
                "region": BACKEND_REGION,
            },
            "request": {
                "method": "POST",
                "path": self.path,
                "body": body,
                "headers": headers,
                "request_count": AdvancedBackendHandler.request_count,
            },
            "timestamp": time.time(),
            "message": f"POST received by {BACKEND_NAME} backend ({BACKEND_VERSION})",
        }

        self.wfile.write(json.dumps(response, indent=2).encode())

    def do_PUT(self):
        """Handle PUT requests."""
        self.do_POST()  # Same handling as POST

    def do_DELETE(self):
        """Handle DELETE requests."""
        AdvancedBackendHandler.request_count += 1
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Backend-Name", BACKEND_NAME)
        self.send_header("X-Backend-Version", BACKEND_VERSION)
        self.end_headers()

        response = {
            "backend": {
                "name": BACKEND_NAME,
                "version": BACKEND_VERSION,
            },
            "request": {
                "method": "DELETE",
                "path": self.path,
            },
            "message": f"DELETE handled by {BACKEND_NAME} backend",
        }

        self.wfile.write(json.dumps(response, indent=2).encode())

    def log_message(self, format, *args):
        """Custom log format with structured logging."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = {
            "timestamp": timestamp,
            "backend": BACKEND_NAME,
            "version": BACKEND_VERSION,
            "type": BACKEND_TYPE,
            "region": BACKEND_REGION,
            "message": format % args,
        }

        # Structured JSON log for analysis
        print(json.dumps(log_entry))

        # Also print human-readable format
        print(f"[{timestamp}] [{BACKEND_NAME}:{BACKEND_VERSION}] {format % args}", file=sys.stderr)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), AdvancedBackendHandler)
    print(f"Starting {BACKEND_NAME} backend server")
    print(f"  Version: {BACKEND_VERSION}")
    print(f"  Type: {BACKEND_TYPE}")
    print(f"  Region: {BACKEND_REGION}")
    print(f"  Port: {port}")
    print(f"  Ready to handle requests...")
    server.serve_forever()
