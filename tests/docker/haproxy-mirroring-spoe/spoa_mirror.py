#!/usr/bin/env python3
"""
SPOE (Stream Processing Offload Engine) agent for request mirroring.

Implements HAProxy SPOE protocol with proper HELLO/DISCONNECT handshake.
Based on HAProxy SPOE specification: https://www.haproxy.org/download/2.9/doc/SPOE.txt
"""

import argparse
import asyncio
import struct
import sys
import urllib.error
import urllib.request
from typing import Tuple

# SPOE Frame Types
SPOE_FRM_T_HAPROXY_HELLO = 1
SPOE_FRM_T_HAPROXY_DISCONNECT = 2
SPOE_FRM_T_HAPROXY_NOTIFY = 3
SPOE_FRM_T_AGENT_HELLO = 101
SPOE_FRM_T_AGENT_DISCONNECT = 102
SPOE_FRM_T_AGENT_ACK = 103

# SPOE Data Types
SPOE_DATA_T_NULL = 0
SPOE_DATA_T_BOOL = 1
SPOE_DATA_T_INT32 = 2
SPOE_DATA_T_UINT32 = 3
SPOE_DATA_T_INT64 = 4
SPOE_DATA_T_UINT64 = 5
SPOE_DATA_T_IPV4 = 6
SPOE_DATA_T_IPV6 = 7
SPOE_DATA_T_STR = 8
SPOE_DATA_T_BIN = 9

from http.server import BaseHTTPRequestHandler, HTTPServer

import threading

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"healthy")
        else:
            self.send_response(404)

class SPOEAgent:
    """SPOE agent for request mirroring with HAProxy"""

    def __init__(self, mirror_url: str, port: int = 12345, health_port: int = 12346):
        self.mirror_url = mirror_url.rstrip("/")
        self.port = port
        self.health_port = health_port
        self.connections = 0

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle SPOE client connection from HAProxy"""
        self.connections += 1
        client_id = self.connections
        addr = writer.get_extra_info("peername")
        print(f"[{client_id}] ====== New Connection from {addr} ======", flush=True)

        try:
            frame_num = 0
            while True:
                frame_num += 1
                print(f"[{client_id}] Waiting for frame #{frame_num}...", flush=True)

                # Read frame header (4 bytes: length)
                try:
                    header = await reader.readexactly(4)
                    print(f"[{client_id}] Received header: {header.hex()}", flush=True)
                except asyncio.IncompleteReadError as e:
                    print(
                        f"[{client_id}] Client disconnected (no header) - bytes read: {len(e.partial)}",
                        flush=True,
                    )
                    break

                # Parse frame length
                frame_length = struct.unpack(">I", header)[0]
                print(f"[{client_id}] Frame #{frame_num} length: {frame_length} bytes", flush=True)

                if frame_length == 0:
                    print(f"[{client_id}] Empty frame, closing connection", flush=True)
                    break

                # Read frame data
                try:
                    frame_data = await reader.readexactly(frame_length)
                    if len(frame_data) <= 200:
                        print(
                            f"[{client_id}] Frame data received ({len(frame_data)} bytes): {frame_data.hex()}",
                            flush=True,
                        )
                    else:
                        print(
                            f"[{client_id}] Frame data received ({len(frame_data)} bytes): {frame_data[:50].hex()}...",
                            flush=True,
                        )
                except asyncio.IncompleteReadError as e:
                    print(
                        f"[{client_id}] Incomplete frame data - expected {frame_length}, got {len(e.partial)}",
                        flush=True,
                    )
                    break

                # Process SPOE frame
                should_continue = await self.process_spoe_frame(frame_data, writer, client_id)
                if not should_continue:
                    print(f"[{client_id}] Process returned False, closing connection", flush=True)
                    break

                print(f"[{client_id}] Frame #{frame_num} processed successfully", flush=True)

        except Exception as e:
            print(f"[{client_id}] Error: {e}", file=sys.stderr, flush=True)
            import traceback

            traceback.print_exc()
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"[{client_id}] Connection closed", flush=True)

    async def process_spoe_frame(
        self, data: bytes, writer: asyncio.StreamWriter, client_id: int
    ) -> bool:
        """Process SPOE frame from HAProxy. Returns False to close connection."""
        if len(data) == 0:
            print(f"[{client_id}] ERROR: Empty frame data!", flush=True)
            return False

        # Frame type is first byte
        frame_type = data[0]
        frame_flags = data[1] if len(data) > 1 else 0

        frame_type_name = {1: "HAPROXY_HELLO", 2: "HAPROXY_DISCONNECT", 3: "HAPROXY_NOTIFY"}.get(
            frame_type, f"UNKNOWN({frame_type})"
        )

        print(
            f"[{client_id}] >>> Processing frame: type={frame_type_name}, flags={frame_flags}, len={len(data)}",
            flush=True,
        )

        if frame_type == SPOE_FRM_T_HAPROXY_HELLO:
            print(f"[{client_id}] Handling HAPROXY_HELLO...", flush=True)
            # Parse flags (4 bytes after type byte)
            if len(data) < 7:
                print(f"[{client_id}] ERROR: HELLO frame too short", flush=True)
                return False
            haproxy_flags = struct.unpack(">I", data[1:5])[0]  # Read 4-byte flags
            print(f"[{client_id}] HAProxy flags: 0x{haproxy_flags:08x}", flush=True)

            # Parse stream-id and frame-id from HELLO
            stream_id, frame_id = self.parse_hello_ids(data[1:])  # Skip type byte
            print(f"[{client_id}] HELLO stream_id={stream_id}, frame_id={frame_id}", flush=True)

            # Parse HELLO KV-pairs properly from the beginning
            hello_kvs = self.parse_hello_kvs(
                data[7:], client_id
            )  # Skip type(1) + flags(4) + stream(1) + frame(1) = 7
            haproxy_caps = hello_kvs.get("capabilities", "")
            haproxy_engine_id = hello_kvs.get("engine-id", "")
            haproxy_max_frame_size = hello_kvs.get("max-frame-size", 16384)
            print(f"[{client_id}] HAProxy capabilities: '{haproxy_caps}'", flush=True)
            print(f"[{client_id}] HAProxy max-frame-size: {haproxy_max_frame_size}", flush=True)
            if haproxy_engine_id:
                print(f"[{client_id}] HAProxy engine-id: '{haproxy_engine_id}'", flush=True)

            # Send AGENT_HELLO - use FIN flag (0x01) in response
            response_flags = 0x01  # SPOE_FRM_FL_FIN
            await self.send_agent_hello(
                writer,
                client_id,
                response_flags,
                stream_id,
                frame_id,
                haproxy_caps,
                haproxy_engine_id,
                haproxy_max_frame_size,
            )
            print(f"[{client_id}] HAPROXY_HELLO handled, waiting for next frame", flush=True)
            return True

        elif frame_type == SPOE_FRM_T_HAPROXY_DISCONNECT:
            print(f"[{client_id}] Handling HAPROXY_DISCONNECT...", flush=True)
            await self.send_agent_disconnect(writer, client_id, frame_flags)
            return False

        elif frame_type == SPOE_FRM_T_HAPROXY_NOTIFY:
            print(f"[{client_id}] Handling HAPROXY_NOTIFY (mirroring request)...", flush=True)
            await self.handle_notify(data, writer, client_id, frame_flags)
            print(f"[{client_id}] HAPROXY_NOTIFY handled", flush=True)
            return True

        else:
            print(
                f"[{client_id}] WARNING: Unknown frame type: {frame_type} (raw data: {data[:20].hex()})",
                flush=True,
            )
            return True

    async def send_agent_hello(
        self,
        writer: asyncio.StreamWriter,
        client_id: int,
        flags: int,
        stream_id: int = 0,
        frame_id: int = 0,
        haproxy_capabilities: str = "",
        haproxy_engine_id: str = "",
        haproxy_max_frame_size: int = 16384,
    ):
        """Send AGENT_HELLO response to HAProxy"""
        print(f"[{client_id}] Building AGENT_HELLO response...", flush=True)

        # Build AGENT_HELLO frame
        frame = bytearray()
        frame.append(SPOE_FRM_T_AGENT_HELLO)  # Frame type = 101

        # Flags: 4 bytes in network byte order (big-endian)
        # SPOE_FRM_FL_FIN = 0x01
        flags_32bit = flags & 0x01  # FIN bit only
        frame.extend(struct.pack(">I", flags_32bit))  # 4 bytes, big-endian

        # Stream-ID and Frame-ID (0 for HELLO frames)
        frame.append(0)  # stream-id = 0
        frame.append(0)  # frame-id = 0

        # KV pairs per SPOE spec (required: version, max-frame-size, capabilities)
        # Per official SPOE spec (3.2.5. Frame: AGENT-HELLO):
        # - "version" <STRING> (REQUIRED): SPOP version (format "Major.Minor")
        # - "max-frame-size" <UINT32> (REQUIRED): Must be <= HAProxy's value
        # - "capabilities" <STRING> (REQUIRED): Comma-separated list
        frame.extend(self.encode_kv_string("version", "2.0"))

        # Max frame size (REQUIRED) - Return EXACTLY what HAProxy sends
        # Per spoa-server code: "Keep the lower value", but HAProxy may be rejecting
        # if we return a value that's TOO different from what it expects
        # Try returning HAProxy's value directly
        print(
            f"[{client_id}] max-frame-size: HAProxy={haproxy_max_frame_size}, returning same",
            flush=True,
        )
        frame.extend(self.encode_kv_uint32("max-frame-size", haproxy_max_frame_size))

        # Capabilities (REQUIRED): Return EXACTLY what HAProxy sends (no additions!)
        agent_caps = haproxy_capabilities if haproxy_capabilities else ""
        print(
            f"[{client_id}] Responding with capabilities: '{agent_caps}' (exact match)", flush=True
        )
        frame.extend(self.encode_kv_string("capabilities", agent_caps))

        print(
            f"[{client_id}] AGENT_HELLO frame built: {len(frame)} bytes (hex: {bytes(frame[:50]).hex()}...)",
            flush=True,
        )

        # Send frame with length prefix
        frame_length_bytes = struct.pack(">I", len(frame))
        print(
            f"[{client_id}] Sending frame length: {len(frame)} (hex: {frame_length_bytes.hex()})",
            flush=True,
        )

        writer.write(frame_length_bytes)
        writer.write(frame)
        await writer.drain()

        print(f"[{client_id}] ✓ AGENT_HELLO sent successfully", flush=True)

    async def send_agent_disconnect(self, writer: asyncio.StreamWriter, client_id: int, flags: int):
        """Send AGENT_DISCONNECT response to HAProxy"""
        frame = bytearray()
        frame.append(SPOE_FRM_T_AGENT_DISCONNECT)  # Frame type
        frame.append(flags & 0x01)  # Flags: FIN bit only

        # Stream-ID and Frame-ID
        frame.extend(self.encode_varint(0))  # stream-id
        frame.extend(self.encode_varint(0))  # frame-id

        # Status code (0 = normal)
        frame.extend(self.encode_kv_uint32("status-code", 0))
        # Message (optional)
        frame.extend(self.encode_kv_string("message", "Goodbye"))

        # Send frame
        writer.write(struct.pack(">I", len(frame)))
        writer.write(frame)
        await writer.drain()
        print(f"[{client_id}] Sent AGENT_DISCONNECT", flush=True)

    async def handle_notify(
        self, data: bytes, writer: asyncio.StreamWriter, client_id: int, flags: int
    ):
        """Handle NOTIFY frame from HAProxy"""
        try:
            # Parse NOTIFY frame to extract method and path
            # Skip type(1 byte) + flags(4 bytes) = 5 bytes
            method, uri = self.parse_notify_frame(data[5:], client_id)

            if method and uri:
                mirror_url = f"{self.mirror_url}{uri}"
                print(f"[{client_id}] Mirroring: {method} {uri} → {mirror_url}", flush=True)

                # Fire-and-forget mirror
                asyncio.create_task(self.mirror_request(method, mirror_url, client_id))
            else:
                print(f"[{client_id}] No valid method/URI in NOTIFY", flush=True)

            # Send ACK
            await self.send_agent_ack(writer, client_id, flags)

        except Exception as e:
            print(f"[{client_id}] Error handling NOTIFY: {e}", file=sys.stderr, flush=True)
            import traceback

            traceback.print_exc()

    async def send_agent_ack(self, writer: asyncio.StreamWriter, client_id: int, flags: int):
        """Send AGENT_ACK response to HAProxy"""
        print(f"[{client_id}] Building AGENT_ACK response...", flush=True)

        frame = bytearray()
        frame.append(SPOE_FRM_T_AGENT_ACK)  # Frame type = 103

        # Flags: 4 bytes in network byte order (big-endian) - CRITICAL FIX!
        # Use FIN flag (0x01) to indicate frame completion
        flags_32bit = flags & 0x01  # FIN bit only
        frame.extend(struct.pack(">I", flags_32bit))  # 4 bytes, big-endian

        # Stream-ID and Frame-ID (varints)
        frame.extend(self.encode_varint(0))  # stream-id
        frame.extend(self.encode_varint(0))  # frame-id

        # Empty actions list (we don't set any variables back)

        print(f"[{client_id}] AGENT_ACK frame: {len(frame)} bytes", flush=True)

        # Send frame
        writer.write(struct.pack(">I", len(frame)))
        writer.write(frame)
        await writer.drain()

        print(f"[{client_id}] ✓ AGENT_ACK sent", flush=True)

    def parse_hello_ids(self, data: bytes) -> Tuple[int, int]:
        """Parse stream-id and frame-id from HELLO frame (after 4-byte flags)"""
        try:
            # HELLO frame format: [flags:4 bytes][stream-id:1 byte][frame-id:1 byte]
            # Skip flags (first 4 bytes)
            if len(data) < 6:
                return 0, 0
            # Stream-ID and Frame-ID are single bytes (0) for HELLO frames
            stream_id = data[4]  # byte after 4-byte flags
            frame_id = data[5]  # next byte
            return stream_id, frame_id
        except Exception as e:
            print(f"Error parsing HELLO IDs: {e}", file=sys.stderr, flush=True)
            return 0, 0

    def parse_hello_kvs(self, payload: bytes, client_id: int) -> dict:
        """Parse all KV-pairs from HELLO payload properly from beginning to end"""
        kvs = {}
        pos = 0

        try:
            while pos < len(payload):
                # Read key length (varint)
                key_len, pos = self.decode_varint(payload, pos)
                if pos + key_len > len(payload):
                    break

                # Read key
                key = payload[pos : pos + key_len].decode("utf-8", errors="replace")
                pos += key_len

                # Read type byte
                if pos >= len(payload):
                    break
                type_byte = payload[pos]
                pos += 1

                # Read value based on type
                if type_byte == SPOE_DATA_T_STR:  # String (0x08)
                    val_len, pos = self.decode_varint(payload, pos)
                    if pos + val_len > len(payload):
                        break
                    value = payload[pos : pos + val_len].decode("utf-8", errors="replace")
                    pos += val_len
                    kvs[key] = value
                    print(f'[{client_id}]   KV: {key} = "{value}" (string)', flush=True)
                elif type_byte == SPOE_DATA_T_UINT32:  # Uint32 (0x03)
                    value, pos = self.decode_varint(payload, pos)
                    kvs[key] = value
                    print(f"[{client_id}]   KV: {key} = {value} (uint32)", flush=True)
                else:
                    # Unknown type, try to skip
                    print(
                        f"[{client_id}]   KV: {key} - unknown type {type_byte}, skipping",
                        flush=True,
                    )
                    break

        except Exception as e:
            print(f"[{client_id}] Error parsing HELLO KVs: {e}", file=sys.stderr, flush=True)

        return kvs

    def extract_capabilities_from_hello(self, data: bytes) -> str:
        """Extract capabilities string from HAPROXY_HELLO frame"""
        try:
            # Look for "capabilities" in the frame
            caps_pos = data.find(b"capabilities")
            if caps_pos == -1:
                return ""

            # We need to parse from the KEY LENGTH, not from the key itself!
            # Go back to find the varint that encodes the key length
            # capabilities = 12 bytes, so look for varint(12) = 0x0c before "capabilities"
            if caps_pos < 1:
                return ""

            # Start from the varint before "capabilities"
            pos = caps_pos - 1
            key_len, pos = self.decode_varint(data, pos)
            if key_len != 12:  # "capabilities" is 12 bytes
                return ""

            # Skip the key itself
            pos += key_len  # Skip "capabilities"

            # Read type byte
            if pos >= len(data):
                return ""
            type_byte = data[pos]
            pos += 1

            # Decode value length (varint)
            caps_len, pos = self.decode_varint(data, pos)
            if pos + caps_len > len(data):
                return ""

            # Extract capabilities string
            caps = data[pos : pos + caps_len].decode("utf-8", errors="replace")
            return caps
        except Exception as e:
            print(f"Error extracting capabilities: {e}", file=sys.stderr, flush=True)
            return ""

    def extract_engine_id_from_hello(self, data: bytes) -> str:
        """Extract engine-id string from HAPROXY_HELLO frame"""
        try:
            # Look for "engine-id" in the frame
            engine_id_pos = data.find(b"engine-id")
            if engine_id_pos == -1:
                return ""

            # Go back to find the varint that encodes the key length
            # engine-id = 9 bytes, so look for varint(9) = 0x09 before "engine-id"
            if engine_id_pos < 1:
                return ""

            # Start from the varint before "engine-id"
            pos = engine_id_pos - 1
            key_len, pos = self.decode_varint(data, pos)
            if key_len != 9:  # "engine-id" is 9 bytes
                return ""

            # Skip the key itself
            pos += key_len  # Skip "engine-id"

            # Read type byte
            if pos >= len(data):
                return ""
            type_byte = data[pos]
            pos += 1

            # Decode value length (varint)
            engine_id_len, pos = self.decode_varint(data, pos)
            if pos + engine_id_len > len(data):
                return ""

            # Extract engine-id string
            engine_id = data[pos : pos + engine_id_len].decode("utf-8", errors="replace")
            return engine_id
        except Exception as e:
            print(f"Error extracting engine-id: {e}", file=sys.stderr, flush=True)
            return ""

    def parse_notify_frame(self, data: bytes, client_id: int) -> Tuple[str, str]:
        """Parse NOTIFY frame to extract method and path arguments"""
        method = ""
        uri = ""

        try:
            # Skip stream-id and frame-id (varint)
            pos = 0
            _, pos = self.decode_varint(data, pos)  # stream-id
            _, pos = self.decode_varint(data, pos)  # frame-id

            # Read message name (string)
            message_name_len, pos = self.decode_varint(data, pos)
            message_name = data[pos : pos + message_name_len].decode("utf-8")
            pos += message_name_len

            print(f"[{client_id}] Message: {message_name}", flush=True)

            # Read number of arguments
            nb_args, pos = self.decode_varint(data, pos)

            # Read arguments (key-value pairs)
            for _ in range(nb_args):
                # Argument name
                arg_name_len, pos = self.decode_varint(data, pos)
                arg_name = data[pos : pos + arg_name_len].decode("utf-8")
                pos += arg_name_len

                # Argument value type
                arg_type = data[pos]
                pos += 1

                # Argument value
                if arg_type == SPOE_DATA_T_STR:
                    arg_value_len, pos = self.decode_varint(data, pos)
                    arg_value = data[pos : pos + arg_value_len].decode("utf-8", errors="ignore")
                    pos += arg_value_len

                    if arg_name == "method":
                        method = arg_value
                    elif arg_name == "path" or arg_name == "uri":
                        uri = arg_value

                    print(f"[{client_id}]   {arg_name}={arg_value}", flush=True)
                else:
                    # Skip other data types for now
                    print(f"[{client_id}]   {arg_name}: type {arg_type} (skipped)", flush=True)
                    break

        except Exception as e:
            print(f"[{client_id}] Error parsing NOTIFY: {e}", file=sys.stderr, flush=True)
            import traceback

            traceback.print_exc()

        return method, uri

    def encode_varint(self, value: int) -> bytes:
        """Encode integer as varint (SPOE encoding)"""
        result = bytearray()
        while value >= 0x80:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return bytes(result)

    def decode_varint(self, data: bytes, pos: int) -> Tuple[int, int]:
        """Decode varint from data at position. Returns (value, new_pos)"""
        value = 0
        shift = 0
        while pos < len(data):
            byte = data[pos]
            pos += 1
            value |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return value, pos

    def encode_kv_string(self, key: str, value: str) -> bytes:
        """Encode key-value pair with string value (matches spoa-server format)"""
        result = bytearray()
        # Key: [length:varint][bytes]
        key_bytes = key.encode("utf-8")
        result.extend(self.encode_varint(len(key_bytes)))
        result.extend(key_bytes)
        # Type byte (not combined with flags!)
        result.append(SPOE_DATA_T_STR)  # 0x08
        # Value: [length:varint][bytes]
        value_bytes = value.encode("utf-8")
        result.extend(self.encode_varint(len(value_bytes)))
        result.extend(value_bytes)
        return bytes(result)

    def encode_kv_uint32(self, key: str, value: int) -> bytes:
        """Encode key-value pair with uint32 value (matches spoa-server format)"""
        result = bytearray()
        # Key: [length:varint][bytes]
        key_bytes = key.encode("utf-8")
        result.extend(self.encode_varint(len(key_bytes)))
        result.extend(key_bytes)
        # Type byte (not combined with flags!)
        result.append(SPOE_DATA_T_UINT32)  # 0x03
        # Value: varint
        result.extend(self.encode_varint(value))
        return bytes(result)

    async def mirror_request(self, method: str, url: str, client_id: int):
        """Mirror request to shadow backend (async, fire-and-forget)"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._make_http_request, method, url)
            print(f"[{client_id}] ✓ Mirrored: {method} {url}", flush=True)
        except Exception as e:
            print(f"[{client_id}] ✗ Mirror failed: {e}", file=sys.stderr, flush=True)

    def _make_http_request(self, method: str, url: str):
        """Make HTTP request (blocking, run in executor)"""
        try:
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=5) as response:
                response.read()  # Consume response
        except urllib.error.HTTPError:
            pass  # Ignore HTTP errors (shadow backend might return error)
        except Exception:
            pass  # Fire-and-forget, ignore all errors

    def start_health_server(self):
        # Startet den HTTP-Server in einem separaten Thread
        server = HTTPServer(("0.0.0.0", self.health_port), HealthCheckHandler)
        print("Healthcheck server listening on 0.0.0.0:12346", flush=True)
        server.serve_forever()
      
    async def run(self):
        # Startet den SPOE-Server (Port 12345)
        spoa_server = await asyncio.start_server(self.handle_client, "0.0.0.0", self.port)
        addr = spoa_server.sockets[0].getsockname()
        print(f"SPOE Mirror Agent listening on {addr[0]}:{addr[1]}", flush=True)
        print(f"Mirror target: {self.mirror_url}", flush=True)
        print("Ready to receive SPOE messages from HAProxy...", flush=True)

        # Startet den HTTP-Server in einem separaten Thread
        health_thread = threading.Thread(target=self.start_health_server, daemon=True)
        health_thread.start()

        async with spoa_server:
            await spoa_server.serve_forever()        
            
    # async def run(self):
    #     """Start SPOE agent server"""
    #     server = await asyncio.start_server(self.handle_client, "0.0.0.0", self.port)

    #     addr = server.sockets[0].getsockname()
    #     print(f"SPOE Mirror Agent listening on {addr[0]}:{addr[1]}", flush=True)
    #     print(f"Mirror target: {self.mirror_url}", flush=True)
    #     print("Ready to receive SPOE messages from HAProxy...", flush=True)

    #     async with server:
    #         await server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="SPOE Mirror Agent")
    parser.add_argument(
        "-p", "--port", type=int, default=12345, help="Port to listen on (default: 12345)"
    )
    parser.add_argument(
        "-u", "--url", required=True, help="Mirror target URL (e.g., http://shadow-backend:8080)"
    )
    parser.add_argument(
        "-e", "--health-port", type=int, default=12346, help="Health-Port to listen on (default: 12346)"
    )
    
    
    args = parser.parse_args()

    agent = SPOEAgent(mirror_url=args.url, port=args.port, health_port=args.health_port)

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
