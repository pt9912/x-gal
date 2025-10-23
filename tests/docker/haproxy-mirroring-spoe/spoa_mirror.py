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


class SPOEAgent:
    """SPOE agent for request mirroring with HAProxy"""

    def __init__(self, mirror_url: str, port: int = 12345):
        self.mirror_url = mirror_url.rstrip('/')
        self.port = port
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
                    print(f"[{client_id}] Client disconnected (no header) - bytes read: {len(e.partial)}", flush=True)
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
                    print(f"[{client_id}] Frame data received ({len(frame_data)} bytes): {frame_data[:50].hex()}...", flush=True)
                except asyncio.IncompleteReadError as e:
                    print(f"[{client_id}] Incomplete frame data - expected {frame_length}, got {len(e.partial)}", flush=True)
                    break

                # Process SPOE frame
                should_continue = await self.process_spoe_frame(
                    frame_data, writer, client_id
                )
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

        frame_type_name = {
            1: "HAPROXY_HELLO",
            2: "HAPROXY_DISCONNECT",
            3: "HAPROXY_NOTIFY"
        }.get(frame_type, f"UNKNOWN({frame_type})")

        print(f"[{client_id}] >>> Processing frame: type={frame_type_name}, flags={frame_flags}, len={len(data)}", flush=True)

        if frame_type == SPOE_FRM_T_HAPROXY_HELLO:
            print(f"[{client_id}] Handling HAPROXY_HELLO...", flush=True)
            # Parse stream-id and frame-id from HELLO
            stream_id, frame_id = self.parse_hello_ids(data[2:])  # Skip type+flags
            print(f"[{client_id}] HELLO stream_id={stream_id}, frame_id={frame_id}", flush=True)
            await self.send_agent_hello(writer, client_id, frame_flags, stream_id, frame_id)
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
            print(f"[{client_id}] WARNING: Unknown frame type: {frame_type} (raw data: {data[:20].hex()})", flush=True)
            return True

    async def send_agent_hello(
        self, writer: asyncio.StreamWriter, client_id: int, flags: int,
        stream_id: int = 0, frame_id: int = 0
    ):
        """Send AGENT_HELLO response to HAProxy"""
        print(f"[{client_id}] Building AGENT_HELLO response...", flush=True)

        # Build AGENT_HELLO frame
        frame = bytearray()
        frame.append(SPOE_FRM_T_AGENT_HELLO)  # Frame type = 101
        frame.append(flags & 0x01)  # Flags: FIN bit only

        # Stream-ID and Frame-ID (must match from HELLO)
        frame.extend(self.encode_varint(stream_id))
        frame.extend(self.encode_varint(frame_id))

        # KV pairs: version, max-frame-size, capabilities
        # Version
        frame.extend(self.encode_kv_string("version", "2.0"))
        # Max frame size
        frame.extend(self.encode_kv_uint32("max-frame-size", 16384))
        # Capabilities (empty string = no capabilities)
        frame.extend(self.encode_kv_string("capabilities", ""))

        print(f"[{client_id}] AGENT_HELLO frame built: {len(frame)} bytes (hex: {bytes(frame[:50]).hex()}...)", flush=True)

        # Send frame with length prefix
        frame_length_bytes = struct.pack(">I", len(frame))
        print(f"[{client_id}] Sending frame length: {len(frame)} (hex: {frame_length_bytes.hex()})", flush=True)

        writer.write(frame_length_bytes)
        writer.write(frame)
        await writer.drain()

        print(f"[{client_id}] ✓ AGENT_HELLO sent successfully", flush=True)

    async def send_agent_disconnect(
        self, writer: asyncio.StreamWriter, client_id: int, flags: int
    ):
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
            method, uri = self.parse_notify_frame(data[2:], client_id)  # Skip type+flags

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

    async def send_agent_ack(
        self, writer: asyncio.StreamWriter, client_id: int, flags: int
    ):
        """Send AGENT_ACK response to HAProxy"""
        print(f"[{client_id}] Building AGENT_ACK response...", flush=True)

        frame = bytearray()
        frame.append(SPOE_FRM_T_AGENT_ACK)  # Frame type = 103
        frame.append(flags & 0x01)  # Flags: FIN bit only

        # Stream-ID and Frame-ID
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
        """Parse stream-id and frame-id from HELLO frame"""
        try:
            pos = 0
            stream_id, pos = self.decode_varint(data, pos)
            frame_id, pos = self.decode_varint(data, pos)
            return stream_id, frame_id
        except Exception as e:
            print(f"Error parsing HELLO IDs: {e}", file=sys.stderr, flush=True)
            return 0, 0

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
            message_name = data[pos:pos + message_name_len].decode('utf-8')
            pos += message_name_len

            print(f"[{client_id}] Message: {message_name}", flush=True)

            # Read number of arguments
            nb_args, pos = self.decode_varint(data, pos)

            # Read arguments (key-value pairs)
            for _ in range(nb_args):
                # Argument name
                arg_name_len, pos = self.decode_varint(data, pos)
                arg_name = data[pos:pos + arg_name_len].decode('utf-8')
                pos += arg_name_len

                # Argument value type
                arg_type = data[pos]
                pos += 1

                # Argument value
                if arg_type == SPOE_DATA_T_STR:
                    arg_value_len, pos = self.decode_varint(data, pos)
                    arg_value = data[pos:pos + arg_value_len].decode('utf-8', errors='ignore')
                    pos += arg_value_len

                    if arg_name == "method":
                        method = arg_value
                    elif arg_name == "path":
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
        """Encode key-value pair with string value"""
        result = bytearray()
        # Key name
        key_bytes = key.encode('utf-8')
        result.extend(self.encode_varint(len(key_bytes)))
        result.extend(key_bytes)
        # Value type
        result.append(SPOE_DATA_T_STR)
        # Value
        value_bytes = value.encode('utf-8')
        result.extend(self.encode_varint(len(value_bytes)))
        result.extend(value_bytes)
        return bytes(result)

    def encode_kv_uint32(self, key: str, value: int) -> bytes:
        """Encode key-value pair with uint32 value"""
        result = bytearray()
        # Key name
        key_bytes = key.encode('utf-8')
        result.extend(self.encode_varint(len(key_bytes)))
        result.extend(key_bytes)
        # Value type
        result.append(SPOE_DATA_T_UINT32)
        # Value (varint encoded)
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

    async def run(self):
        """Start SPOE agent server"""
        server = await asyncio.start_server(self.handle_client, "0.0.0.0", self.port)

        addr = server.sockets[0].getsockname()
        print(f"SPOE Mirror Agent listening on {addr[0]}:{addr[1]}", flush=True)
        print(f"Mirror target: {self.mirror_url}", flush=True)
        print("Ready to receive SPOE messages from HAProxy...", flush=True)

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
        print("\nShutting down...", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
