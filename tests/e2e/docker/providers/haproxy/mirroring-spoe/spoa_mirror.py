#!/usr/bin/env python3
"""
SPOE (Stream Processing Offload Engine) agent for request mirroring.
Uses haproxyspoa for robust SPOP handling.
"""

import argparse
import asyncio
import datetime
import signal
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    from haproxyspoa.payloads.ack import AckPayload
    from haproxyspoa.spoa_server import SpoaServer
except ImportError:
    print(
        "ERROR: haproxyspoa library not found. Install with: pip install haproxyspoa",
        file=sys.stderr,
    )
    sys.exit(1)


def _ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"healthy")
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"not found")

    def log_message(self, fmt, *args):
        return


class SPOEAgent:
    """SPOE agent for request mirroring with HAProxy using haproxyspoa"""

    def __init__(self, mirror_url: str, port: int = 12345, health_port: int = 12346):
        self.mirror_url = mirror_url.rstrip("/")
        self.port = port
        self.health_port = health_port
        self.message_count = 0
        self.spoa = SpoaServer()

        @self.spoa.handler("mirror-request")
        async def _handle(**kwargs):
            return await self.handle_messages(**kwargs)

    def log(self, msg: str, *, to_stderr: bool = False, flush: bool = False):
        stream = sys.stderr if to_stderr else sys.stdout
        print(f"[SpoaMirror-{_ts()}] {msg}", file=stream, flush=flush)

    async def handle_messages(self, **kwargs) -> AckPayload:
        self.message_count += 1
        msg_id = self.message_count

        method = str(kwargs.get("method", "")).upper()
        uri = kwargs.get("path", "") or kwargs.get("uri", "") or ""

        headers = {}
        for k, v in kwargs.items():
            if isinstance(k, str) and k.lower().startswith("x-"):
                if v is None or v == "":
                    continue
                headers[k] = str(v)

        # Normalize x-test-name into canonical X-Test-Name casing.
        xtn = kwargs.get("x-test-name")
        if xtn not in (None, ""):
            headers["X-Test-Name"] = str(xtn)

        if not (method and uri):
            self.log(f"[msg#{msg_id}] No valid method/URI in message", flush=True)
            return AckPayload()

        mirror_url = f"{self.mirror_url}{uri}"
        self.log(f"[msg#{msg_id}] Mirroring: {method} {uri} -> {mirror_url}", flush=True)
        asyncio.create_task(self.mirror_request(method, mirror_url, headers, msg_id))
        return AckPayload()

    async def mirror_request(self, method: str, url: str, headers: dict, msg_id: int):
        """Fire-and-forget HTTP request to the shadow backend."""
        try:
            req = urllib.request.Request(url, method=method, headers=headers)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=5))
            self.log(f"[msg#{msg_id}] Mirrored OK: {method} {url}", flush=True)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            self.log(f"[msg#{msg_id}] Mirror got HTTP error (ignored): {e}")
        except Exception as e:
            self.log(f"[msg#{msg_id}] Mirror failed: {e}", to_stderr=True, flush=True)

    def start_health_server(self):
        server = HTTPServer(("0.0.0.0", self.health_port), HealthCheckHandler)
        self.log(f"Healthcheck server listening on 0.0.0.0:{self.health_port}", flush=True)
        server.serve_forever()

    def run(self):
        """Start SPOE agent with haproxyspoa (blocking call)."""
        health_thread = threading.Thread(target=self.start_health_server, daemon=True)
        health_thread.start()

        self.log(f"SPOE Mirror Agent listening on 0.0.0.0:{self.port}", flush=True)
        self.log(f"Mirror target: {self.mirror_url}", flush=True)
        self.log(f"Health check: http://0.0.0.0:{self.health_port}/health", flush=True)
        self.log("Ready to receive SPOE messages from HAProxy...", flush=True)

        # haproxyspoa exposes a synchronous .run(...) (starts event loop internally).
        self.spoa.run(host="0.0.0.0", port=self.port)


def main():
    parser = argparse.ArgumentParser(description="SPOE Mirror Agent (haproxyspoa)")
    parser.add_argument(
        "-p", "--port", type=int, default=12345, help="Port to listen on (default: 12345)"
    )
    parser.add_argument(
        "-u", "--url", required=True, help="Mirror target URL (e.g., http://shadow-backend:8080)"
    )
    parser.add_argument(
        "-e",
        "--health-port",
        type=int,
        default=12346,
        help="Health port to listen on (default: 12346)",
    )

    args = parser.parse_args()
    agent = SPOEAgent(mirror_url=args.url, port=args.port, health_port=args.health_port)

    def handle_shutdown(signum, frame):
        try:
            sig_name = signal.Signals(signum).name
        except Exception:
            sig_name = str(signum)
        print(f"\n[SpoaMirror-{_ts()}] Received {sig_name}. Shutting down...", flush=True)
        for attr in ("stop", "close", "shutdown"):
            handler = getattr(agent.spoa, attr, None)
            if handler is None:
                continue
            try:
                handler()
                break
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    try:
        agent.run()
    except KeyboardInterrupt:
        handle_shutdown(signal.SIGINT, None)


if __name__ == "__main__":
    main()
