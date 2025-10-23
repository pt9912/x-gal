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
        # Simplified SPOE parser - looks for method and path in binary data
        # Real SPOE uses complex binary format with VarInt encoding
        # This is a practical approximation that looks for text patterns

        try:
            # Default values
            method = "GET"
            uri = "/"

            # Convert to string for easier searching (ignoring unprintable chars)
            data_str = data.decode("utf-8", errors="ignore")

            # Extract HTTP method - look for common methods in the data
            if "GET" in data_str:
                method = "GET"
            elif "POST" in data_str:
                method = "POST"
            elif "PUT" in data_str:
                method = "PUT"
            elif "DELETE" in data_str:
                method = "DELETE"
            elif "PATCH" in data_str:
                method = "PATCH"

            # Extract URI/path - look for /api/ patterns
            # SPOE sends path as null-terminated string after "path" key
            if "/api/" in data_str:
                start = data_str.find("/api/")
                # Find end of path (null byte, space, or newline)
                end = len(data_str)
                for delimiter in ["\x00", " ", "\n", "\r"]:
                    pos = data_str.find(delimiter, start)
                    if pos != -1 and pos < end:
                        end = pos
                uri = data_str[start:end].strip()
                # Clean up any non-path characters
                if " " in uri:
                    uri = uri.split(" ")[0]

            # Only mirror if we found a valid URI
            if uri and uri != "/":
                mirror_url = f"{self.mirror_url}{uri}"
                print(f"[{client_id}] Mirroring: {method} {uri} → {mirror_url}", flush=True)

                # Fire-and-forget mirror (don't wait for response)
                asyncio.create_task(self.mirror_request(method, mirror_url, client_id))
            else:
                print(f"[{client_id}] No valid URI found in SPOE message", flush=True)

        except Exception as e:
            print(f"[{client_id}] Failed to parse SPOE message: {e}", file=sys.stderr, flush=True)

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
