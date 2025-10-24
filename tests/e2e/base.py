"""
Base class for E2E tests with Docker Compose.

This module provides a reusable base class for all E2E tests that require
Docker Compose environments. It includes common setup, teardown, health checking,
and logging functionality.
"""

import subprocess
import time
import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import pytest


class BaseE2ETest:
    """Base class for E2E tests with Docker Compose."""

    # Override these in subclasses
    COMPOSE_FILE = "docker-compose.yml"
    SERVICE_PORT = 8080
    HEALTH_ENDPOINT = "/health"
    ADMIN_PORT = None  # Optional admin interface port
    WAIT_TIMEOUT = 60

    @classmethod
    def setup_class(cls):
        """Start Docker Compose environment."""
        cls.test_dir = cls._get_test_dir()
        cls.original_dir = os.getcwd()
        os.chdir(cls.test_dir)

        try:
            cls.cleanup_existing()
            cls.start_containers()
            cls.wait_for_services()
            cls.save_start_time()
            cls.post_setup()
        except Exception as e:
            cls.emergency_cleanup()
            raise

    @classmethod
    def teardown_class(cls):
        """Stop Docker Compose environment and save logs."""
        try:
            cls.save_logs()
            cls.pre_teardown()
        finally:
            cls.stop_containers()
            os.chdir(cls.original_dir)

    @classmethod
    def _get_test_dir(cls):
        """Get the directory containing the docker-compose.yml file."""
        # Default: Look for docker-compose.yml in various locations
        possible_paths = [
            Path(__file__).parent / "docker" / cls.__name__.lower().replace("test", ""),
            Path(__file__).parent.parent / "docker" / cls.__name__.lower().replace("test", ""),
            Path(__file__).parent,
        ]

        for path in possible_paths:
            compose_path = path / cls.COMPOSE_FILE
            if compose_path.exists():
                return str(path)

        # If not found, use current directory
        return os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def cleanup_existing(cls):
        """Stop and remove any existing containers."""
        print("\n🧹 Cleaning up existing containers...")
        result = subprocess.run(
            ["docker-compose", "-f", cls.COMPOSE_FILE, "down", "-v"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0 and "no configuration file provided" not in result.stderr.lower():
            print(f"  Warning during cleanup: {result.stderr}")

    @classmethod
    def start_containers(cls):
        """Start Docker Compose containers."""
        print(f"\n🚀 Starting Docker Compose Environment from {cls.COMPOSE_FILE}...")
        print(f"  Working directory: {os.getcwd()}")

        result = subprocess.run(
            ["docker-compose", "-f", cls.COMPOSE_FILE, "up", "-d", "--build"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"❌ Error starting containers:")
            print(f"  STDOUT: {result.stdout}")
            print(f"  STDERR: {result.stderr}")
            raise RuntimeError("Failed to start Docker Compose")

        print("✅ Containers started successfully")

    @classmethod
    def stop_containers(cls):
        """Stop Docker Compose containers."""
        print("\n🛑 Stopping Docker Compose Environment...")
        subprocess.run(
            ["docker-compose", "-f", cls.COMPOSE_FILE, "down", "-v"],
            capture_output=True
        )
        print("✅ Containers stopped")

    @classmethod
    def emergency_cleanup(cls):
        """Emergency cleanup if setup fails."""
        print("\n⚠️ Emergency cleanup after setup failure...")
        try:
            subprocess.run(
                ["docker-compose", "-f", cls.COMPOSE_FILE, "logs", "--tail=50"],
                cwd=cls.test_dir
            )
            subprocess.run(
                ["docker-compose", "-f", cls.COMPOSE_FILE, "down", "-v"],
                cwd=cls.test_dir,
                capture_output=True
            )
        except:
            pass

    @classmethod
    def wait_for_services(cls, timeout=None):
        """Wait for all services to be healthy."""
        timeout = timeout or cls.WAIT_TIMEOUT
        print(f"⏳ Waiting for all services to be healthy (timeout: {timeout}s)...")

        for i in range(timeout):
            if i > 0 and i % 10 == 0:
                cls.show_progress(i)

            if cls.check_health():
                print("✅ All services are ready!")

                # Additional stabilization time
                if hasattr(cls, 'STABILIZATION_TIME'):
                    print(f"  Waiting {cls.STABILIZATION_TIME}s for stabilization...")
                    time.sleep(cls.STABILIZATION_TIME)

                return True

            time.sleep(1)

        cls.handle_startup_failure()
        return False

    @classmethod
    def check_health(cls):
        """Check if all services are healthy."""
        try:
            # Check main service
            response = requests.get(
                f"http://localhost:{cls.SERVICE_PORT}{cls.HEALTH_ENDPOINT}",
                timeout=2
            )
            if response.status_code != 200:
                return False

            # Check admin interface if configured
            if cls.ADMIN_PORT:
                admin_response = requests.get(
                    f"http://localhost:{cls.ADMIN_PORT}/ready",
                    timeout=2
                )
                if admin_response.status_code != 200:
                    return False

            # Check additional services if needed
            return cls.check_additional_services()

        except requests.exceptions.RequestException:
            return False

    @classmethod
    def check_additional_services(cls):
        """Override to check additional services."""
        return True

    @classmethod
    def show_progress(cls, elapsed):
        """Show startup progress."""
        print(f"  ⏱️ Waiting... ({elapsed}s elapsed)")

        result = subprocess.run(
            ["docker-compose", "-f", cls.COMPOSE_FILE, "ps", "--format", "table"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("  📊 Container Status:")
            lines = result.stdout.split('\n')
            for line in lines[:8]:  # Show first few containers
                if line.strip():
                    # Truncate long lines
                    if len(line) > 120:
                        line = line[:117] + "..."
                    print(f"    {line}")

    @classmethod
    def handle_startup_failure(cls):
        """Handle startup failure with detailed diagnostics."""
        print("\n❌ Services did not become ready in time!")
        print("\n📋 Container Status:")
        subprocess.run(["docker-compose", "-f", cls.COMPOSE_FILE, "ps"])

        print("\n📜 Recent Logs:")
        subprocess.run(
            ["docker-compose", "-f", cls.COMPOSE_FILE, "logs", "--tail=30"]
        )

        raise TimeoutError("Services did not become ready in time")

    @classmethod
    def save_logs(cls):
        """Save all logs for debugging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"test_logs_{cls.__name__}_{timestamp}.txt"

        print(f"\n💾 Saving logs to {log_file}...")

        logs_result = subprocess.run(
            ["docker-compose", "-f", cls.COMPOSE_FILE, "logs", "--no-color"],
            capture_output=True,
            text=True
        )

        with open(log_file, "w") as f:
            f.write(f"=== Test Logs for {cls.__name__} ===\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Test Directory: {cls.test_dir}\n")
            f.write("=" * 80 + "\n\n")

            f.write(logs_result.stdout)
            if logs_result.stderr:
                f.write("\n\n=== STDERR ===\n")
                f.write(logs_result.stderr)

        print(f"✅ Logs saved to {log_file}")

    @classmethod
    def save_start_time(cls):
        """Save test start time for log filtering."""
        # Use UTC and subtract 2 seconds to ensure we capture all logs
        cls.test_start_time = (datetime.now(timezone.utc) - timedelta(seconds=2)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        print(f"🕐 Test start time: {cls.test_start_time} UTC")

    @classmethod
    def post_setup(cls):
        """Override for additional setup after containers are ready."""
        pass

    @classmethod
    def pre_teardown(cls):
        """Override for cleanup before stopping containers."""
        pass

    # Helper methods for tests

    def get_logs_since_start(self, service, grep_pattern=None):
        """Get logs from a service since test start."""
        cmd = ["docker-compose", "-f", self.COMPOSE_FILE, "logs", service]

        if hasattr(self, 'test_start_time'):
            cmd.extend(["--since", self.test_start_time])

        result = subprocess.run(
            cmd,
            cwd=self.test_dir,
            capture_output=True,
            text=True,
        )

        logs = result.stdout

        if grep_pattern:
            logs = '\n'.join(line for line in logs.split('\n') if grep_pattern in line)

        return logs

    def count_log_occurrences(self, service, pattern, since_start=True):
        """Count occurrences of a pattern in service logs."""
        if since_start:
            logs = self.get_logs_since_start(service)
        else:
            result = subprocess.run(
                ["docker-compose", "-f", self.COMPOSE_FILE, "logs", service],
                cwd=self.test_dir,
                capture_output=True,
                text=True
            )
            logs = result.stdout

        return logs.count(pattern)

    def get_container_stats(self):
        """Get Docker container statistics."""
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "json"],
            capture_output=True,
            text=True
        )

        stats = []
        for line in result.stdout.strip().split('\n'):
            if line:
                stats.append(json.loads(line))

        return stats

    def make_request(self, path="/", method="GET", headers=None, json_data=None, **kwargs):
        """Make a request to the test service."""
        url = f"http://localhost:{self.SERVICE_PORT}{path}"

        if method == "GET":
            return requests.get(url, headers=headers, **kwargs)
        elif method == "POST":
            return requests.post(url, headers=headers, json=json_data, **kwargs)
        elif method == "PUT":
            return requests.put(url, headers=headers, json=json_data, **kwargs)
        elif method == "DELETE":
            return requests.delete(url, headers=headers, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")

    def assert_response(self, response, expected_status=200, expected_json=None):
        """Assert response status and optionally JSON content."""
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code}. Response: {response.text}"

        if expected_json:
            actual = response.json()
            for key, value in expected_json.items():
                assert key in actual, f"Key '{key}' not in response"
                assert actual[key] == value, f"Expected {key}={value}, got {actual[key]}"

    def measure_latency(self, num_requests=100, path="/"):
        """Measure request latencies."""
        latencies = []

        for _ in range(num_requests):
            start = time.time()
            try:
                response = self.make_request(path, timeout=5)
                if response.status_code == 200:
                    latency = (time.time() - start) * 1000  # Convert to ms
                    latencies.append(latency)
            except:
                pass

        if not latencies:
            return None

        latencies.sort()
        return {
            "count": len(latencies),
            "mean": sum(latencies) / len(latencies),
            "min": latencies[0],
            "max": latencies[-1],
            "p50": latencies[len(latencies) // 2],
            "p95": latencies[int(len(latencies) * 0.95)],
            "p99": latencies[int(len(latencies) * 0.99)] if len(latencies) > 100 else latencies[-1]
        }

    def run_concurrent_requests(self, num_requests=100, num_workers=10, path="/"):
        """Run concurrent requests and return statistics."""
        import concurrent.futures

        results = {"success": 0, "failed": 0, "responses": []}

        def make_single_request(i):
            try:
                response = self.make_request(path, timeout=5)
                if response.status_code == 200:
                    return ("success", response)
                return ("failed", response)
            except Exception as e:
                return ("error", str(e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(make_single_request, i) for i in range(num_requests)]
            for future in concurrent.futures.as_completed(futures):
                status, response = future.result()
                results[status if status in ["success", "failed"] else "failed"] += 1
                if status == "success":
                    results["responses"].append(response)

        return results