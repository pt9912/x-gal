#!/usr/bin/env python3
"""
Simple HTTP server for GeoIP testing with hardcoded IP-to-country mappings.
Used for testing Envoy's geo-based routing with ext_authz filter.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# Hardcodierte IP-zu-Ländercode-Zuordnung für Testzwecke
GEOIP_MOCK = {
    "192.168.1.1": "DE",
    "192.168.1.2": "US",
    "10.0.0.1": "DE",
    "10.0.0.2": "FR",
    # Weitere IPs können hier hinzugefügt werden
}


class GeoIPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Extrahiere die IP aus dem Pfad (z. B. /country/192.168.1.1)
        path_parts = self.path.split("/")
        if len(path_parts) >= 3 and path_parts[1] == "country":
            client_ip = path_parts[2]
            country = GEOIP_MOCK.get(client_ip, "unknown")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Geo-Country", country)
            self.end_headers()

            response = {
                "country": country,
                "message": f"GeoIP lookup for {client_ip}",
                "path": self.path,
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid endpoint"}).encode())

    def do_POST(self):
        # POST /check für Envoy ext_authz
        if self.path == "/check":
            content_length = int(self.headers.get("Content-Length", 0))
            request_body = self.rfile.read(content_length).decode()
            try:
                request_data = json.loads(request_body) if request_body else {}
                client_ip = request_data.get("headers", {}).get("x-forwarded-for", "unknown")
                country = GEOIP_MOCK.get(client_ip, "unknown")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("X-Geo-Country", country)
                self.end_headers()

                response = {
                    "status": {"code": 200},
                    "headers": {"x-geo-country": country},
                    "metadata_context": {
                        "filter_metadata": {"envoy.filters.http.ext_authz": {"country": country}}
                    },
                }
                self.wfile.write(json.dumps(response).encode())
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid endpoint"}).encode())

    def do_PUT(self):
        self.send_response(405)
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Method not allowed"}).encode())

    def do_DELETE(self):
        self.send_response(405)
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Method not allowed"}).encode())

    def log_message(self, format, *args):
        # Suppress default logging
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), GeoIPHandler)
    print(f"GeoIP test service listening on port {port}")
    server.serve_forever()
