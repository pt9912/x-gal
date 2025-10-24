#!/usr/bin/env python3
"""
gRPC-based GeoIP service for Envoy ext_authz filter.
Implements the Envoy External Authorization gRPC protocol.
"""

import os
import json
import logging
from concurrent import futures
import grpc

# Hardcodierte IP-zu-Ländercode-Zuordnung für Testzwecke
GEOIP_MOCK = {
    "192.168.1.1": "DE",
    "192.168.1.2": "US",
    "10.0.0.1": "DE",
    "10.0.0.2": "FR",
    "172.17.0.1": "DE",  # Docker default gateway
    "127.0.0.1": "US",
    # Weitere IPs können hier hinzugefügt werden
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Envoy External Authorization Protocol Buffers (simplified)
# In production, you would use the official .proto files from Envoy
class CheckRequest:
    """Simplified CheckRequest for ext_authz"""
    def __init__(self, attributes):
        self.attributes = attributes


class CheckResponse:
    """Simplified CheckResponse for ext_authz"""
    def __init__(self, status_code, headers=None, metadata=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.metadata = metadata or {}


class AuthorizationServicer:
    """Envoy External Authorization gRPC Servicer"""

    def Check(self, request, context):
        """
        Check authorization and extract GeoIP information.
        This is called by Envoy for every request.
        """
        try:
            # Extract client IP from request attributes
            # Envoy sends this in the request attributes
            client_ip = "unknown"

            # Try to get IP from X-Forwarded-For header
            if hasattr(request, 'attributes') and hasattr(request.attributes, 'request'):
                headers = getattr(request.attributes.request, 'http', {}).get('headers', {})
                client_ip = headers.get('x-forwarded-for', headers.get('x-real-ip', 'unknown'))

            # Fallback to source address
            if client_ip == "unknown" and hasattr(request, 'attributes'):
                source = getattr(request.attributes, 'source', {})
                client_ip = getattr(source, 'address', {}).get('socketAddress', {}).get('address', 'unknown')

            # Lookup country code
            country = GEOIP_MOCK.get(client_ip, "UNKNOWN")

            logger.info(f"GeoIP Lookup: IP={client_ip} -> Country={country}")

            # Return OK response with country metadata
            # This metadata will be available in Envoy's dynamic metadata
            response_headers = [
                {'key': 'x-geo-country', 'value': country},
                {'key': 'x-geo-ip', 'value': client_ip}
            ]

            # Metadata for Envoy routing decisions
            metadata = {
                'filter_metadata': {
                    'envoy.filters.http.ext_authz': {
                        'country': country,
                        'ip': client_ip
                    }
                }
            }

            # Create response (always allow, just add metadata)
            # In production, you might deny based on country/IP
            return {
                'status': {'code': 0},  # 0 = OK
                'ok_response': {
                    'headers': response_headers
                },
                'dynamic_metadata': metadata
            }

        except Exception as e:
            logger.error(f"Error in GeoIP lookup: {e}", exc_info=True)
            # Return OK even on error (fail-open)
            return {
                'status': {'code': 0},
                'ok_response': {}
            }


def serve():
    """Start the gRPC server"""
    port = int(os.environ.get("PORT", 9090))

    # Note: This is a simplified implementation
    # In production, use the official Envoy ext_authz proto definitions
    # and generate proper gRPC stubs

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # In a real implementation, you would:
    # from envoy.service.auth.v3 import external_auth_pb2_grpc
    # external_auth_pb2_grpc.add_AuthorizationServicer_to_server(
    #     AuthorizationServicer(), server
    # )

    server.add_insecure_port(f'[::]:{port}')
    server.start()

    logger.info(f"GeoIP gRPC service listening on port {port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server")
        server.stop(0)


if __name__ == "__main__":
    # For testing without gRPC dependencies, fall back to HTTP
    try:
        import grpc
        serve()
    except ImportError:
        logger.warning("grpcio not installed, falling back to HTTP service")

        # HTTP fallback (same as geoip.py)
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class GeoIPHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "healthy"}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == "/check":
                    content_length = int(self.headers.get("Content-Length", 0))
                    request_body = self.rfile.read(content_length).decode()

                    try:
                        request_data = json.loads(request_body) if request_body else {}
                        headers = request_data.get("attributes", {}).get("request", {}).get("http", {}).get("headers", {})
                        client_ip = headers.get("x-forwarded-for", headers.get("x-real-ip", "unknown"))
                        country = GEOIP_MOCK.get(client_ip, "UNKNOWN")

                        logger.info(f"GeoIP HTTP Lookup: IP={client_ip} -> Country={country}")

                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("X-Geo-Country", country)
                        self.send_header("X-Geo-IP", client_ip)
                        self.end_headers()

                        response = {
                            "status": {"code": 0},
                            "ok_response": {
                                "headers": [
                                    {"key": "x-geo-country", "value": country},
                                    {"key": "x-geo-ip", "value": client_ip}
                                ]
                            },
                            "dynamic_metadata": {
                                "filter_metadata": {
                                    "envoy.filters.http.ext_authz": {
                                        "country": country,
                                        "ip": client_ip
                                    }
                                }
                            }
                        }
                        self.wfile.write(json.dumps(response).encode())
                    except json.JSONDecodeError:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                logger.info(f"{self.address_string()} - {format % args}")

        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), GeoIPHandler)
        logger.info(f"GeoIP HTTP service listening on port {port}")
        server.serve_forever()
