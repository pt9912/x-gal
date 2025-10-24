# E2E Test Best Practices für Docker Compose Tests

Dieses Dokument sammelt Best Practices und wiederverwendbare Patterns aus unseren E2E Tests, insbesondere aus den HAProxy SPOE und Advanced Routing Tests.

## 📋 Inhaltsverzeichnis

1. [Setup & Teardown](#setup--teardown)
2. [Health Checks & Warteprozesse](#health-checks--warteprozesse)
3. [Log-Analyse](#log-analyse)
4. [Test-Isolation](#test-isolation)
5. [Fehlerbehandlung](#fehlerbehandlung)
6. [Performance & Metriken](#performance--metriken)
7. [Dokumentation](#dokumentation)
8. [Wiederverwendbare Komponenten](#wiederverwendbare-komponenten)

## Setup & Teardown

### Docker Compose Lifecycle Management

```python
@classmethod
def setup_class(cls):
    """Start Docker Compose environment."""
    print("\n=== Starting Docker Compose Environment ===")

    # Change to test directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(test_dir)

    # Stop any existing containers
    subprocess.run(["docker-compose", "down", "-v"], capture_output=True)

    # Start containers
    result = subprocess.run(
        ["docker-compose", "up", "-d", "--build"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error starting containers: {result.stderr}")
        raise RuntimeError("Failed to start Docker Compose")

    print("Waiting for services to be ready...")
    cls.wait_for_services()
    print("Services are ready!")

@classmethod
def teardown_class(cls):
    """Stop Docker Compose environment."""
    print("\n=== Stopping Docker Compose Environment ===")

    # Capture and save logs for debugging
    logs_result = subprocess.run(
        ["docker-compose", "logs", "--no-color"],
        capture_output=True,
        text=True
    )

    # Save logs to file for analysis
    with open("test_logs.txt", "w") as f:
        f.write(logs_result.stdout)
        if logs_result.stderr:
            f.write("\n=== STDERR ===\n")
            f.write(logs_result.stderr)

    print(f"Logs saved to test_logs.txt")

    # Stop containers
    subprocess.run(["docker-compose", "down", "-v"], capture_output=True)
```

## Health Checks & Warteprozesse

### Detaillierte Health Check mit Progress Logging

```python
@classmethod
def wait_for_services(cls, timeout=60):
    """Wait for all services to be healthy with detailed logging."""
    start_time = time.time()
    test_dir = os.path.dirname(os.path.abspath(__file__))

    print("⏳ Waiting for all services to be healthy...")

    for i in range(timeout):
        elapsed = time.time() - start_time

        # Log progress every 10-15 seconds
        if i % 10 == 0 and i > 0:
            print(f"  Waiting... ({i}s elapsed)")

            # Check container status
            result = subprocess.run(
                ["docker-compose", "ps", "--format", "table"],
                cwd=test_dir,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("  Container Status:")
                for line in result.stdout.split('\n')[:8]:  # Show first few containers
                    if line.strip():
                        print(f"    {line}")

        try:
            # Check primary service health
            response = requests.get("http://localhost:8080/health", timeout=2)
            if response.status_code == 200:
                print("✅ Primary service is ready!")

                # Check if all backend services are responding
                if cls.check_all_backends():
                    print("✅ All backend services are ready!")
                    return True
                else:
                    print("  Waiting for backends to be ready...")
        except requests.exceptions.RequestException as e:
            if i == 0:
                print(f"  Services not ready yet: {e}")

        time.sleep(1)

    # If we get here, services didn't become ready in time
    print("❌ Services did not become ready in time. Showing logs:")
    subprocess.run(["docker-compose", "ps"], cwd=test_dir)
    subprocess.run(["docker-compose", "logs", "--tail=50"], cwd=test_dir)

    raise TimeoutError("Services did not become ready in time")
```

### Backend Service Verification

```python
@classmethod
def check_all_backends(cls):
    """Check if all backend services are responding."""
    # Try to reach each backend through gateway with specific headers
    test_requests = [
        ("backend-v1", {}, {}),
        ("backend-v2", {"X-API-Version": "v2"}, {}),
        ("backend-mobile", {"User-Agent": "Mobile Safari"}, {}),
        ("backend-admin", {"X-Admin-Access": "true"}, {}),
    ]

    for backend_name, headers, params in test_requests:
        try:
            response = requests.get(
                "http://localhost:8080/api",
                headers=headers,
                params=params,
                timeout=1
            )
            if response.status_code != 200:
                return False
        except:
            return False

    return True
```

## Log-Analyse

### Timestamp-based Log Isolation

```python
def get_backend_request_count(self, compose_dir, path_pattern="", since=None):
    """Helper: Count requests received by backend

    Args:
        compose_dir: Docker compose directory
        path_pattern: Path pattern to match (e.g., "/api/v1")
        since: Only count logs since this timestamp (format: "2025-10-23T14:30:00")
               If None, count all logs

    Returns:
        Number of matching requests
    """
    cmd = ["docker-compose", "logs", "backend"]
    if since:
        cmd.extend(["--since", since])

    result = subprocess.run(
        cmd,
        cwd=compose_dir,
        capture_output=True,
        text=True,
    )

    if path_pattern:
        # Count requests matching the path pattern
        count = result.stdout.count(f"Received request: GET {path_pattern}")
        count += result.stdout.count(f"Received request: POST {path_pattern}")
    else:
        # Count all requests
        count = result.stdout.count("Received request:")

    return count
```

### Test Start Time Capture

```python
def test_with_timestamp_isolation(self, setup, docker_compose_file):
    """Test with timestamp-based log isolation."""
    compose_dir = Path(docker_compose_file).parent

    # Capture timestamp before sending requests (use UTC for Docker logs)
    # Subtract 2 seconds to ensure we capture all logs
    start_time = (datetime.now(timezone.utc) - timedelta(seconds=2)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    print(f"  Test start time: {start_time}")

    # Run your test
    num_requests = 20
    for i in range(num_requests):
        requests.get("http://localhost:8080/api", timeout=5)

    # Count only logs since test start (ignores previous tests)
    request_count = self.get_backend_request_count(
        compose_dir, "/api", since=start_time
    )

    print(f"Requests counted since {start_time}: {request_count}")
```

## Test-Isolation

### Clear Logs Between Tests

```python
def clear_backend_logs(self, compose_dir, backend_name):
    """Clear logs from a backend to ensure test isolation."""
    # Method 1: Touch a marker file (backend can detect this)
    subprocess.run(
        [
            "docker-compose",
            "exec",
            "-T",
            backend_name,
            "sh",
            "-c",
            "echo '' > /tmp/clear",
        ],
        cwd=compose_dir,
        capture_output=True,
    )

    # Method 2: Restart the container (more aggressive)
    # subprocess.run(
    #     ["docker-compose", "restart", backend_name],
    #     cwd=compose_dir,
    #     capture_output=True,
    # )
```

### Request Correlation with IDs

```python
def test_log_correlation(self):
    """Correlate requests across services using unique IDs."""
    import uuid
    import time

    # Send request with unique identifier
    request_id = str(uuid.uuid4())
    response = requests.get(
        "http://localhost:8080/api",
        headers={
            "X-Request-ID": request_id
        }
    )
    assert response.status_code == 200

    # Wait for logs to be written
    time.sleep(1)

    # Check gateway logs for the request ID
    gateway_logs = subprocess.run(
        ["docker-compose", "logs", "gateway", "--tail=100"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    # Check backend logs
    backend_logs = subprocess.run(
        ["docker-compose", "logs", "backend", "--tail=50"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    # Verify the request appears in both logs
    if gateway_logs.returncode == 0 and request_id in gateway_logs.stdout:
        print(f"✓ Request {request_id} found in gateway logs")

    if backend_logs.returncode == 0 and request_id in backend_logs.stdout:
        print(f"✓ Request {request_id} found in backend logs")
```

## Fehlerbehandlung

### Robuste Test Execution

```python
def test_with_retry_logic(self):
    """Test with automatic retry for flaky operations."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get("http://localhost:8080/api", timeout=5)
            if response.status_code == 200:
                break
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt + 1} failed: {e}, retrying...")
            time.sleep(2)
```

### Detailed Error Reporting

```python
def analyze_failure(self):
    """Analyze and report failure details."""
    print("\n=== FAILURE ANALYSIS ===")

    # Show container status
    result = subprocess.run(
        ["docker-compose", "ps"],
        capture_output=True,
        text=True
    )
    print("Container Status:")
    print(result.stdout)

    # Show recent logs from each service
    services = ["gateway", "backend-v1", "backend-v2"]
    for service in services:
        print(f"\n--- {service} logs (last 20 lines) ---")
        result = subprocess.run(
            ["docker-compose", "logs", service, "--tail=20"],
            capture_output=True,
            text=True
        )
        print(result.stdout)

    # Check resource usage
    result = subprocess.run(
        ["docker", "stats", "--no-stream"],
        capture_output=True,
        text=True
    )
    print("\nDocker Resource Usage:")
    print(result.stdout)
```

## Performance & Metriken

### Prometheus Metrics Analysis

```python
def test_routing_metrics(self):
    """Check gateway metrics for routing statistics."""
    response = requests.get("http://localhost:9901/stats/prometheus")
    assert response.status_code == 200

    metrics = response.text

    # Check for routing-related metrics
    important_metrics = [
        "upstream_rq_total",
        "downstream_rq_total",
        "upstream_rq_2xx",
        "router_downstream_rq_total",
    ]

    for metric in important_metrics:
        if metric in metrics:
            print(f"✓ Metric {metric} present")

    # Parse specific cluster metrics
    for line in metrics.split("\n"):
        if "cluster" in line and "upstream_rq_total" in line:
            # Extract cluster name and count
            if "{" in line and "}" in line:
                cluster_info = line[line.index("{"):line.index("}")+1]
                count = line.split()[-1]
                if float(count) > 0:
                    print(f"  Cluster requests: {cluster_info} = {count}")
```

### Latency Measurements

```python
def measure_request_latency(self, num_requests=100):
    """Measure and analyze request latencies."""
    latencies = []

    for i in range(num_requests):
        start = time.time()
        try:
            response = requests.get("http://localhost:8080/api", timeout=5)
            if response.status_code == 200:
                latency = (time.time() - start) * 1000  # Convert to ms
                latencies.append(latency)
        except:
            pass

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        p50 = sorted(latencies)[len(latencies) // 2]
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]

        print(f"\nLatency Analysis ({len(latencies)} requests):")
        print(f"  Average: {avg_latency:.2f} ms")
        print(f"  P50: {p50:.2f} ms")
        print(f"  P95: {p95:.2f} ms")
        print(f"  P99: {p99:.2f} ms")
        print(f"  Min: {min(latencies):.2f} ms")
        print(f"  Max: {max(latencies):.2f} ms")
```

## Dokumentation

### Self-Documenting Tests

```python
def test_feature_documentation(self):
    """Document feature implementation and verify it works."""
    print("\n📝 Feature: Advanced Routing")
    print("=" * 70)
    print("✅ PRODUCTION-READY Implementation")
    print()
    print("Supported Routing Types:")
    print("  ✅ Header-based routing (exact, prefix, contains, regex)")
    print("  ✅ Query parameter routing (exact, exists, regex)")
    print("  ✅ JWT claims-based routing (role, scope, custom)")
    print("  ✅ Geo-based routing (country, region)")
    print()
    print("Configuration Files:")
    print("  - gal-config.yaml: GAL routing configuration")
    print("  - envoy.yaml: Generated Envoy configuration")
    print("  - docker-compose.yml: Full stack with backends")
    print()
    print("These E2E tests VERIFY that routing works correctly!")
    print("=" * 70)

    # Run actual verification
    response = requests.get(
        "http://localhost:8080/api",
        headers={"X-API-Version": "v2"}
    )
    assert response.status_code == 200
    assert response.json()["backend"]["name"] == "backend-v2"
    print("\n✅ Feature verification passed!")
```

### Test Report Generation

```python
def generate_test_report(self, results):
    """Generate a detailed test report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_suite": self.__class__.__name__,
        "summary": {
            "total_tests": len(results),
            "passed": sum(1 for r in results if r["status"] == "passed"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "skipped": sum(1 for r in results if r["status"] == "skipped"),
        },
        "details": results,
        "environment": {
            "docker_version": self.get_docker_version(),
            "compose_version": self.get_compose_version(),
        }
    }

    # Save JSON report
    with open("test_report.json", "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n📊 Test Report Summary:")
    print(f"  Total: {report['summary']['total_tests']}")
    print(f"  ✅ Passed: {report['summary']['passed']}")
    print(f"  ❌ Failed: {report['summary']['failed']}")
    print(f"  ⏭️ Skipped: {report['summary']['skipped']}")
    print(f"\nDetailed report saved to test_report.json")
```

## Wiederverwendbare Komponenten

### Base E2E Test Class

```python
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

    @classmethod
    def setup_class(cls):
        """Start Docker Compose environment."""
        cls.test_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(cls.test_dir)

        cls.cleanup_existing()
        cls.start_containers()
        cls.wait_for_services()
        cls.save_start_time()

    @classmethod
    def teardown_class(cls):
        """Stop Docker Compose environment and save logs."""
        cls.save_logs()
        cls.stop_containers()

    @classmethod
    def cleanup_existing(cls):
        """Stop and remove any existing containers."""
        subprocess.run(["docker-compose", "down", "-v"], capture_output=True)

    @classmethod
    def start_containers(cls):
        """Start Docker Compose containers."""
        print("\n=== Starting Docker Compose Environment ===")
        result = subprocess.run(
            ["docker-compose", "up", "-d", "--build"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Error starting containers: {result.stderr}")
            raise RuntimeError("Failed to start Docker Compose")

    @classmethod
    def stop_containers(cls):
        """Stop Docker Compose containers."""
        print("\n=== Stopping Docker Compose Environment ===")
        subprocess.run(["docker-compose", "down", "-v"], capture_output=True)

    @classmethod
    def wait_for_services(cls, timeout=60):
        """Wait for all services to be healthy."""
        print("⏳ Waiting for all services to be healthy...")

        for i in range(timeout):
            if i % 10 == 0 and i > 0:
                cls.show_progress(i)

            if cls.check_health():
                print("✅ All services are ready!")
                return

            time.sleep(1)

        cls.handle_startup_failure()

    @classmethod
    def check_health(cls):
        """Override this method to check service health."""
        raise NotImplementedError("Subclasses must implement check_health()")

    @classmethod
    def show_progress(cls, elapsed):
        """Show startup progress."""
        print(f"  Waiting... ({elapsed}s elapsed)")
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "table"],
            cwd=cls.test_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("  Container Status:")
            for line in result.stdout.split('\n')[:8]:
                if line.strip():
                    print(f"    {line}")

    @classmethod
    def handle_startup_failure(cls):
        """Handle startup failure with detailed diagnostics."""
        print("❌ Services did not become ready in time. Showing diagnostics:")
        subprocess.run(["docker-compose", "ps"], cwd=cls.test_dir)
        subprocess.run(["docker-compose", "logs", "--tail=50"], cwd=cls.test_dir)
        raise TimeoutError("Services did not become ready in time")

    @classmethod
    def save_logs(cls):
        """Save all logs for debugging."""
        logs_result = subprocess.run(
            ["docker-compose", "logs", "--no-color"],
            capture_output=True,
            text=True
        )

        with open("test_logs.txt", "w") as f:
            f.write(logs_result.stdout)
            if logs_result.stderr:
                f.write("\n=== STDERR ===\n")
                f.write(logs_result.stderr)

        print("Logs saved to test_logs.txt")

    @classmethod
    def save_start_time(cls):
        """Save test start time for log filtering."""
        cls.test_start_time = (datetime.now(timezone.utc) - timedelta(seconds=2)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

    def get_logs_since_start(self, service, grep_pattern=None):
        """Get logs from a service since test start."""
        cmd = ["docker-compose", "logs", service]
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
```

### Backend Service Template

```python
#!/usr/bin/env python3
"""
Template for backend service used in E2E tests.
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


class BackendHandler(BaseHTTPRequestHandler):
    request_count = 0

    def do_GET(self):
        """Handle GET requests."""
        BackendHandler.request_count += 1
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Backend-Name", BACKEND_NAME)
        self.send_header("X-Backend-Version", BACKEND_VERSION)
        self.end_headers()

        response = {
            "backend": {
                "name": BACKEND_NAME,
                "version": BACKEND_VERSION,
                "type": BACKEND_TYPE,
            },
            "request": {
                "method": "GET",
                "path": self.path,
                "headers": dict(self.headers),
                "request_count": BackendHandler.request_count,
            },
            "timestamp": time.time(),
        }

        self.wfile.write(json.dumps(response, indent=2).encode())

    def log_message(self, format, *args):
        """Custom log format with structured logging."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = {
            "timestamp": timestamp,
            "backend": BACKEND_NAME,
            "version": BACKEND_VERSION,
            "message": format % args
        }

        # Structured JSON log for analysis
        print(json.dumps(log_entry))

        # Also print human-readable format
        print(f"[{timestamp}] [{BACKEND_NAME}:{BACKEND_VERSION}] {format % args}",
              file=sys.stderr)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), BackendHandler)
    print(f"Starting {BACKEND_NAME} backend server on port {port}")
    server.serve_forever()
```

## Zusammenfassung

Diese Best Practices helfen dabei:

1. **Zuverlässige Tests** zu schreiben, die konsistent funktionieren
2. **Aussagekräftige Fehlerberichte** zu generieren, wenn etwas schief geht
3. **Test-Isolation** sicherzustellen, damit Tests sich nicht gegenseitig beeinflussen
4. **Performance-Probleme** frühzeitig zu erkennen
5. **Wiederverwendbaren Code** zu erstellen für zukünftige Tests

### Checkliste für neue E2E Tests

- [ ] Docker Compose Setup mit health checks
- [ ] Detailliertes Progress Logging während des Startups
- [ ] Log-Speicherung im Teardown
- [ ] Timestamp-basierte Log-Isolation
- [ ] Request Correlation mit eindeutigen IDs
- [ ] Fehleranalyse bei Test-Fehlschlägen
- [ ] Performance-Metriken sammeln
- [ ] Self-documenting Test-Methoden
- [ ] Wiederverwendung der BaseE2ETest Klasse

### Nächste Schritte

1. **Refactoring bestehender Tests**: Anwendung dieser Patterns auf bestehende E2E Tests
2. **Test-Framework**: Erstellen eines gemeinsamen Test-Frameworks basierend auf BaseE2ETest
3. **CI/CD Integration**: Anpassung für GitHub Actions mit Artefakt-Speicherung
4. **Performance Baselines**: Etablierung von Performance-Baselines für Regressionstest