#!/usr/bin/env python3
"""
Simple SPOE (Stream Processing Offload Engine) agent for request mirroring.

This is a simplified Python implementation of spoa-mirror that:
1. Listens for SPOE messages from HAProxy
2. Extracts request data (method, URI, headers, body)
3. Mirrors requests to shadow backend (fire-and-forget)

Based on HAProxy SPOE protocol specification.
"""

import argparse
import asyncio
import struct
import sys
import urllib.error
import urllib.request
from typing import Any, Dict


class SPOEAgent:
    """Simple SPOE agent for request mirroring"""

    def __init__(self, mirror_url: str, port: int = 12345):
        self.mirror_url = mirror_url
        self.port = port
        self.connections = 0

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle SPOE client connection from HAProxy"""
        self.connections += 1
        client_id = self.connections
        addr = writer.get_extra_info("peername")
        print(f"[{client_id}] Connection from {addr}")

        try:
            while True:
                # Read frame header (4 bytes)
                header = await reader.readexactly(4)
                if not header:
                    break

                # Parse frame length
                frame_length = struct.unpack(">I", header)[0]
                if frame_length == 0:
                    break

                # Read frame data
                frame_data = await reader.readexactly(frame_length)

                # Process SPOE message
                await self.process_spoe_message(frame_data, client_id)

                # Send ACK (simple empty frame for now)
                # In production, parse message and send proper ACK
                ack = struct.pack(">I", 0)
                writer.write(ack)
                await writer.drain()

        except asyncio.IncompleteReadError:
            print(f"[{client_id}] Client disconnected")
        except Exception as e:
            print(f"[{client_id}] Error: {e}", file=sys.stderr)
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"[{client_id}] Connection closed")

    async def process_spoe_message(self, data: bytes, client_id: int):
        """Process SPOE message and mirror request"""
        # This is a SIMPLIFIED parser - real SPOE is more complex
        # We just extract basic request info from the message

        try:
            # Extract request data (simplified - assumes message contains method and URI)
            message_str = data.decode("utf-8", errors="ignore")

            # Look for method and URI in message
            # Real SPOE uses binary format with typed arguments
            method = "GET"  # Default
            uri = "/"  # Default

            if b"method" in data:
                # Try to extract method
                idx = data.find(b"method")
                if idx != -1:
                    # Next few bytes might contain the method
                    snippet = data[idx : idx + 20].decode("utf-8", errors="ignore")
                    if "GET" in snippet:
                        method = "GET"
                    elif "POST" in snippet:
                        method = "POST"
                    elif "PUT" in snippet:
                        method = "PUT"
                    elif "DELETE" in snippet:
                        method = "DELETE"

            if b"uri" in data or b"path" in data:
                # Try to extract URI
                idx = max(data.find(b"uri"), data.find(b"path"))
                if idx != -1:
                    snippet = data[idx : idx + 100].decode("utf-8", errors="ignore")
                    # Look for /api/ patterns
                    if "/api/" in snippet:
                        start = snippet.find("/api/")
                        end = snippet.find(" ", start)
                        if end == -1:
                            end = snippet.find("\x00", start)
                        if end != -1:
                            uri = snippet[start:end]
                        else:
                            uri = snippet[start : start + 20]

            # Mirror the request to shadow backend
            mirror_url = f"{self.mirror_url}{uri}"
            print(f"[{client_id}] Mirroring: {method} {uri} → {mirror_url}")

            # Fire-and-forget mirror (don't wait for response)
            asyncio.create_task(self.mirror_request(method, mirror_url, client_id))

        except Exception as e:
            print(f"[{client_id}] Failed to parse SPOE message: {e}", file=sys.stderr)

    async def mirror_request(self, method: str, url: str, client_id: int):
        """Mirror request to shadow backend (async, fire-and-forget)"""
        try:
            # Use asyncio to not block
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._make_http_request, method, url)
            print(f"[{client_id}] ✓ Mirrored: {method} {url}")
        except Exception as e:
            print(f"[{client_id}] ✗ Mirror failed: {e}", file=sys.stderr)

    def _make_http_request(self, method: str, url: str):
        """Make HTTP request (blocking, run in executor)"""
        try:
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=5) as response:
                response.read()  # Consume response
        except urllib.error.HTTPError as e:
            # Even errors are OK for mirroring (shadow backend might not exist)
            pass
        except Exception as e:
            raise

    async def run(self):
        """Start SPOE agent server"""
        server = await asyncio.start_server(self.handle_client, "0.0.0.0", self.port)

        addr = server.sockets[0].getsockname()
        print(f"SPOE Mirror Agent listening on {addr[0]}:{addr[1]}")
        print(f"Mirror target: {self.mirror_url}")
        print("Ready to receive SPOE messages from HAProxy...")

        async with server:
            await server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="SPOE Mirror Agent")
    parser.add_argument(
        "-p", "--port", type=int, default=12345, help="Port to listen on (default: 12345)"
    )
    parser.add_argument(
        "-u", "--url", required=True, help="Mirror target URL (e.g., http://shadow-backend:8080)"
    )
    args = parser.parse_args()

    agent = SPOEAgent(mirror_url=args.url, port=args.port)

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
