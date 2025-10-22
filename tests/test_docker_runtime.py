"""
Docker-based runtime tests for traffic splitting.

These tests use Docker Compose to spin up actual gateways and backends,
then verify traffic distribution works as expected.

Requirements:
- Docker and Docker Compose installed
- pytest (pip install pytest requests)

Run with:
    pytest tests/test_docker_runtime.py -v -s
"""

import subprocess
import time
from collections import Counter
from pathlib import Path

import pytest
import requests


class TestEnvoyTrafficSplitRuntime:
    """Test Envoy traffic splitting with real Docker containers"""

    @pytest.fixture(scope="class")
    def docker_compose_file(self):
        """Path to Docker Compose file"""
        return str(Path(__file__).parent / "docker" / "envoy" / "docker-compose.yml")

    @pytest.fixture(scope="class")
    def envoy_setup(self, docker_compose_file):
        """Setup and teardown Docker Compose environment"""
        compose_dir = Path(docker_compose_file).parent

        # Build and start containers
        print("\n🐳 Starting Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=compose_dir,
            check=True,
            capture_output=True,
        )

        # Wait for Envoy to be ready
        print("⏳ Waiting for Envoy to be healthy...")
        max_wait = 30
        for i in range(max_wait):
            # Check container status
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=compose_dir,
                capture_output=True,
                text=True,
            )
            if i % 10 == 0:  # Log every 10 seconds
                print(f"  Waiting... ({i}s) - Container status check")

            try:
                response = requests.get("http://localhost:9901/ready", timeout=2)
                if response.status_code == 200:
                    print("✅ Envoy is ready!")
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        else:
            # Show logs if startup failed
            print("❌ Envoy did not become ready in time. Showing logs:")
            subprocess.run(["docker", "compose", "ps"], cwd=compose_dir)
            subprocess.run(["docker", "compose", "logs", "envoy"], cwd=compose_dir)
            pytest.fail("Envoy did not become ready in time")

        # Additional wait for backends
        time.sleep(2)

        yield

        # Cleanup
        print("\n🧹 Stopping Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "down", "-v"], cwd=compose_dir, check=True, capture_output=True
        )

    def test_traffic_distribution_90_10(self, envoy_setup):
        """Test that traffic is distributed 90% stable, 10% canary"""
        # Send 1000 requests
        results = Counter()
        failed = 0

        print("\n📊 Sending 1000 requests to test traffic distribution...")

        for i in range(1000):
            try:
                response = requests.get("http://localhost:10000/api/v1", timeout=5)

                if response.status_code == 200:
                    backend = response.headers.get("X-Backend-Name")
                    if backend:
                        results[backend] += 1
                    else:
                        # Try JSON body
                        data = response.json()
                        backend = data.get("backend")
                        if backend:
                            results[backend] += 1
                        else:
                            failed += 1
                else:
                    failed += 1

            except Exception as e:
                print(f"Request {i} failed: {e}")
                failed += 1

            # Progress indicator
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/1000 requests")

        # Print results
        print(f"\n📈 Traffic Distribution Results:")
        print(f"  Stable: {results['stable']} requests ({results['stable']/10:.1f}%)")
        print(f"  Canary: {results['canary']} requests ({results['canary']/10:.1f}%)")
        print(f"  Failed: {failed} requests")

        # Verify distribution (90/10 ± 5% tolerance)
        # Expected: 900 ± 50 for stable, 100 ± 50 for canary
        assert (
            results["stable"] >= 850
        ), f"Stable backend received too few requests: {results['stable']} < 850"
        assert (
            results["stable"] <= 950
        ), f"Stable backend received too many requests: {results['stable']} > 950"
        assert (
            results["canary"] >= 50
        ), f"Canary backend received too few requests: {results['canary']} < 50"
        assert (
            results["canary"] <= 150
        ), f"Canary backend received too many requests: {results['canary']} > 150"
        assert failed < 50, f"Too many failed requests: {failed}"

        print("\n✅ Traffic distribution test PASSED!")

    def test_backend_responses(self, envoy_setup):
        """Test that both backends respond correctly"""
        # Test a few requests to ensure backends work
        for i in range(10):
            response = requests.get("http://localhost:10000/api/v1", timeout=5)
            assert response.status_code == 200

            # Verify response format
            data = response.json()
            assert "backend" in data
            assert data["backend"] in ["stable", "canary"]
            assert "message" in data
            assert "path" in data
            assert data["path"] == "/api/v1"

        print("\n✅ Backend response test PASSED!")

    def test_envoy_admin_stats(self, envoy_setup):
        """Test Envoy admin interface shows traffic split stats"""
        # Get cluster stats
        response = requests.get("http://localhost:9901/stats", timeout=5)
        assert response.status_code == 200

        stats = response.text

        # Verify both clusters exist
        assert "canary_deployment_api_stable_cluster" in stats
        assert "canary_deployment_api_canary_cluster" in stats

        print("\n✅ Envoy admin stats test PASSED!")


class TestNginxTrafficSplitRuntime:
    """Test Nginx traffic splitting with real Docker containers"""

    @pytest.fixture(scope="class")
    def docker_compose_file(self):
        """Path to Docker Compose file"""
        return str(Path(__file__).parent / "docker" / "nginx" / "docker-compose.yml")

    @pytest.fixture(scope="class")
    def nginx_setup(self, docker_compose_file):
        """Setup and teardown Docker Compose environment"""
        compose_dir = Path(docker_compose_file).parent

        # Build and start containers
        print("\n🐳 Starting Nginx Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=compose_dir,
            check=True,
            capture_output=True,
        )

        # Wait for Nginx to be ready
        print("⏳ Waiting for Nginx to be healthy...")
        max_wait = 30
        for i in range(max_wait):
            # Check container status
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=compose_dir,
                capture_output=True,
                text=True,
            )
            if i % 10 == 0:  # Log every 10 seconds
                print(f"  Waiting... ({i}s) - Container status check")

            try:
                response = requests.get("http://localhost:8080/api/v1", timeout=2)
                if response.status_code == 200:
                    print("✅ Nginx is ready!")
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        else:
            # Show logs if startup failed
            print("❌ Nginx did not become ready in time. Showing logs:")
            subprocess.run(["docker", "compose", "ps"], cwd=compose_dir)
            subprocess.run(["docker", "compose", "logs", "nginx"], cwd=compose_dir)
            pytest.fail("Nginx did not become ready in time")

        # Additional wait for backends
        time.sleep(2)

        yield

        # Cleanup
        print("\n🧹 Stopping Nginx Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "down", "-v"], cwd=compose_dir, check=True, capture_output=True
        )

    def test_traffic_distribution_90_10(self, nginx_setup):
        """Test that traffic is distributed 90% stable, 10% canary"""
        results = Counter()
        failed = 0

        print("\n📊 Sending 1000 requests to test Nginx traffic distribution...")

        for i in range(1000):
            try:
                response = requests.get("http://localhost:8080/api/v1", timeout=5)

                if response.status_code == 200:
                    backend = response.headers.get("X-Backend-Name")
                    if backend:
                        results[backend] += 1
                    else:
                        data = response.json()
                        backend = data.get("backend")
                        if backend:
                            results[backend] += 1
                        else:
                            failed += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1

            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/1000 requests")

        # Print results
        print(f"\n📈 Nginx Traffic Distribution Results:")
        print(f"  Stable: {results['stable']} requests ({results['stable']/10:.1f}%)")
        print(f"  Canary: {results['canary']} requests ({results['canary']/10:.1f}%)")
        print(f"  Failed: {failed} requests")

        # Verify distribution (90/10 ± 5% tolerance)
        assert (
            results["stable"] >= 850
        ), f"Stable backend received too few requests: {results['stable']} < 850"
        assert (
            results["stable"] <= 950
        ), f"Stable backend received too many requests: {results['stable']} > 950"
        assert (
            results["canary"] >= 50
        ), f"Canary backend received too few requests: {results['canary']} < 50"
        assert (
            results["canary"] <= 150
        ), f"Canary backend received too many requests: {results['canary']} > 150"
        assert failed < 50, f"Too many failed requests: {failed}"

        print("\n✅ Nginx traffic distribution test PASSED!")


class TestKongTrafficSplitRuntime:
    """Test Kong traffic splitting with real Docker containers"""

    @pytest.fixture(scope="class")
    def docker_compose_file(self):
        """Path to Docker Compose file"""
        return str(Path(__file__).parent / "docker" / "kong" / "docker-compose.yml")

    @pytest.fixture(scope="class")
    def kong_setup(self, docker_compose_file):
        """Setup and teardown Docker Compose environment"""
        compose_dir = Path(docker_compose_file).parent

        # Build and start containers
        print("\n🐳 Starting Kong Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=compose_dir,
            check=True,
            capture_output=True,
        )

        # Wait for Kong to be ready
        print("⏳ Waiting for Kong to be healthy...")
        max_wait = 30
        for i in range(max_wait):
            # Check container status
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=compose_dir,
                capture_output=True,
                text=True,
            )
            if i % 10 == 0:  # Log every 10 seconds
                print(f"  Waiting... ({i}s) - Container status check")

            try:
                response = requests.get("http://localhost:8001/status", timeout=2)
                if response.status_code == 200:
                    print("✅ Kong is ready!")
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        else:
            # Show logs if startup failed
            print("❌ Kong did not become ready in time. Showing logs:")
            subprocess.run(["docker", "compose", "ps"], cwd=compose_dir)
            subprocess.run(["docker", "compose", "logs", "kong"], cwd=compose_dir)
            pytest.fail("Kong did not become ready in time")

        # Additional wait for backends
        time.sleep(2)

        yield

        # Cleanup
        print("\n🧹 Stopping Kong Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "down", "-v"], cwd=compose_dir, check=True, capture_output=True
        )

    def test_traffic_distribution_90_10(self, kong_setup):
        """Test that traffic is distributed 90% stable, 10% canary"""
        results = Counter()
        failed = 0

        print("\n📊 Sending 1000 requests to test Kong traffic distribution...")

        for i in range(1000):
            try:
                response = requests.get("http://localhost:8000/api/v1", timeout=5)

                if response.status_code == 200:
                    backend = response.headers.get("X-Backend-Name")
                    if backend:
                        results[backend] += 1
                    else:
                        data = response.json()
                        backend = data.get("backend")
                        if backend:
                            results[backend] += 1
                        else:
                            failed += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1

            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/1000 requests")

        # Print results
        print(f"\n📈 Kong Traffic Distribution Results:")
        print(f"  Stable: {results['stable']} requests ({results['stable']/10:.1f}%)")
        print(f"  Canary: {results['canary']} requests ({results['canary']/10:.1f}%)")
        print(f"  Failed: {failed} requests")

        # Verify distribution (90/10 ± 5% tolerance)
        assert (
            results["stable"] >= 850
        ), f"Stable backend received too few requests: {results['stable']} < 850"
        assert (
            results["stable"] <= 950
        ), f"Stable backend received too many requests: {results['stable']} > 950"
        assert (
            results["canary"] >= 50
        ), f"Canary backend received too few requests: {results['canary']} < 50"
        assert (
            results["canary"] <= 150
        ), f"Canary backend received too many requests: {results['canary']} > 150"
        assert failed < 50, f"Too many failed requests: {failed}"

        print("\n✅ Kong traffic distribution test PASSED!")


class TestHAProxyTrafficSplitRuntime:
    """Test HAProxy traffic splitting with real Docker containers"""

    @pytest.fixture(scope="class")
    def docker_compose_file(self):
        """Path to Docker Compose file"""
        return str(Path(__file__).parent / "docker" / "haproxy" / "docker-compose.yml")

    @pytest.fixture(scope="class")
    def haproxy_setup(self, docker_compose_file):
        """Setup and teardown Docker Compose environment"""
        compose_dir = Path(docker_compose_file).parent

        print("\n🐳 Starting HAProxy Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=compose_dir,
            check=True,
            capture_output=True,
        )

        print("⏳ Waiting for HAProxy to be healthy...")
        max_wait = 30
        for i in range(max_wait):
            # Check container status
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=compose_dir,
                capture_output=True,
                text=True,
            )
            if i % 10 == 0:  # Log every 10 seconds
                print(f"  Waiting... ({i}s) - Container status check")

            try:
                response = requests.get("http://localhost:8080/api/v1", timeout=2)
                if response.status_code == 200:
                    print("✅ HAProxy is ready!")
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        else:
            print("❌ HAProxy did not become ready in time. Showing logs:")
            subprocess.run(["docker", "compose", "ps"], cwd=compose_dir)
            subprocess.run(["docker", "compose", "logs", "haproxy"], cwd=compose_dir)
            pytest.fail("HAProxy did not become ready in time")

        time.sleep(2)
        yield

        print("\n🧹 Stopping HAProxy Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "down", "-v"], cwd=compose_dir, check=True, capture_output=True
        )

    def test_traffic_distribution_90_10(self, haproxy_setup):
        """Test that traffic is distributed 90% stable, 10% canary"""
        results = Counter()
        failed = 0

        print("\n📊 Sending 1000 requests to test HAProxy traffic distribution...")

        for i in range(1000):
            try:
                response = requests.get("http://localhost:8080/api/v1", timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    backend = data.get("backend")
                    if backend:
                        results[backend] += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/1000 requests")

        print(f"\n📈 HAProxy Traffic Distribution Results:")
        print(f"  Stable: {results['stable']} requests ({results['stable']/10:.1f}%)")
        print(f"  Canary: {results['canary']} requests ({results['canary']/10:.1f}%)")
        print(f"  Failed: {failed} requests")

        assert results["stable"] >= 850, f"Stable: {results['stable']} < 850"
        assert results["stable"] <= 950, f"Stable: {results['stable']} > 950"
        assert results["canary"] >= 50, f"Canary: {results['canary']} < 50"
        assert results["canary"] <= 150, f"Canary: {results['canary']} > 150"
        assert failed < 50, f"Too many failed: {failed}"

        print("\n✅ HAProxy traffic distribution test PASSED!")


class TestTraefikTrafficSplitRuntime:
    """Test Traefik traffic splitting with real Docker containers"""

    @pytest.fixture(scope="class")
    def docker_compose_file(self):
        """Path to Docker Compose file"""
        return str(Path(__file__).parent / "docker" / "traefik" / "docker-compose.yml")

    @pytest.fixture(scope="class")
    def traefik_setup(self, docker_compose_file):
        """Setup and teardown Docker Compose environment"""
        compose_dir = Path(docker_compose_file).parent

        print("\n🐳 Starting Traefik Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=compose_dir,
            check=True,
            capture_output=True,
        )

        print("⏳ Waiting for Traefik to be healthy...")
        max_wait = 60  # Traefik needs more time to start in CI
        for i in range(max_wait):
            # Check container status
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=compose_dir,
                capture_output=True,
                text=True,
            )
            if i % 10 == 0:  # Log every 10 seconds
                print(f"  Waiting... ({i}s) - Container status check")

            try:
                response = requests.get("http://localhost:8080/api/v1", timeout=2)
                if response.status_code == 200:
                    print("✅ Traefik is ready!")
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        else:
            print("❌ Traefik did not become ready in time. Showing logs:")
            subprocess.run(["docker", "compose", "ps"], cwd=compose_dir)
            subprocess.run(["docker", "compose", "logs", "traefik"], cwd=compose_dir)
            pytest.fail("Traefik did not become ready in time")

        time.sleep(2)
        yield

        print("\n🧹 Stopping Traefik Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "down", "-v"], cwd=compose_dir, check=True, capture_output=True
        )

    def test_traffic_distribution_90_10(self, traefik_setup):
        """Test that traffic is distributed 90% stable, 10% canary"""
        results = Counter()
        failed = 0

        print("\n📊 Sending 1000 requests to test Traefik traffic distribution...")

        for i in range(1000):
            try:
                response = requests.get("http://localhost:8080/api/v1", timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    backend = data.get("backend")
                    if backend:
                        results[backend] += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/1000 requests")

        print(f"\n📈 Traefik Traffic Distribution Results:")
        print(f"  Stable: {results['stable']} requests ({results['stable']/10:.1f}%)")
        print(f"  Canary: {results['canary']} requests ({results['canary']/10:.1f}%)")
        print(f"  Failed: {failed} requests")

        assert results["stable"] >= 850, f"Stable: {results['stable']} < 850"
        assert results["stable"] <= 950, f"Stable: {results['stable']} > 950"
        assert results["canary"] >= 50, f"Canary: {results['canary']} < 50"
        assert results["canary"] <= 150, f"Canary: {results['canary']} > 150"
        assert failed < 50, f"Too many failed: {failed}"

        print("\n✅ Traefik traffic distribution test PASSED!")


class TestAPISIXTrafficSplitRuntime:
    """Test APISIX traffic splitting with real Docker containers"""

    @pytest.fixture(scope="class")
    def docker_compose_file(self):
        """Path to Docker Compose file"""
        return str(Path(__file__).parent / "docker" / "apisix" / "docker-compose.yml")

    @pytest.fixture(scope="class")
    def apisix_setup(self, docker_compose_file):
        """Setup and teardown Docker Compose environment"""
        compose_dir = Path(docker_compose_file).parent

        print("\n🐳 Starting APISIX Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=compose_dir,
            check=True,
            capture_output=True,
        )

        print("⏳ Waiting for APISIX to be healthy...")
        max_wait = 60  # APISIX needs more time to start in CI
        for i in range(max_wait):
            # Check container status
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=compose_dir,
                capture_output=True,
                text=True,
            )
            if i % 10 == 0:  # Log every 10 seconds
                print(f"  Waiting... ({i}s) - Container status check")

            try:
                response = requests.get("http://localhost:9080/api/v1", timeout=2)
                if response.status_code == 200:
                    print("✅ APISIX is ready!")
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        else:
            print("❌ APISIX did not become ready in time. Showing logs:")
            subprocess.run(["docker", "compose", "ps"], cwd=compose_dir)
            subprocess.run(["docker", "compose", "logs", "apisix"], cwd=compose_dir)
            pytest.fail("APISIX did not become ready in time")

        time.sleep(2)
        yield

        print("\n🧹 Stopping APISIX Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "down", "-v"], cwd=compose_dir, check=True, capture_output=True
        )

    def test_traffic_distribution_90_10(self, apisix_setup):
        """Test that traffic is distributed 90% stable, 10% canary"""
        results = Counter()
        failed = 0

        print("\n📊 Sending 1000 requests to test APISIX traffic distribution...")

        for i in range(1000):
            try:
                response = requests.get("http://localhost:9080/api/v1", timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    backend = data.get("backend")
                    if backend:
                        results[backend] += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/1000 requests")

        print(f"\n📈 APISIX Traffic Distribution Results:")
        print(f"  Stable: {results['stable']} requests ({results['stable']/10:.1f}%)")
        print(f"  Canary: {results['canary']} requests ({results['canary']/10:.1f}%)")
        print(f"  Failed: {failed} requests")

        assert results["stable"] >= 850, f"Stable: {results['stable']} < 850"
        assert results["stable"] <= 950, f"Stable: {results['stable']} > 950"
        assert results["canary"] >= 50, f"Canary: {results['canary']} < 50"
        assert results["canary"] <= 150, f"Canary: {results['canary']} > 150"
        assert failed < 50, f"Too many failed: {failed}"

        print("\n✅ APISIX traffic distribution test PASSED!")


@pytest.mark.skip(
    reason="Docker Compose test - run manually with: pytest tests/test_docker_runtime.py -v -m docker"
)
@pytest.mark.docker
class TestDockerRuntimeSkipped:
    """Marker class for skipped Docker tests"""

    pass
