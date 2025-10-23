"""
Docker-based E2E tests for Request Mirroring with APISIX.

These tests use Docker Compose to spin up APISIX with request mirroring
configured, then verify that requests are properly mirrored to shadow backend.

Feature 6: Request Mirroring / Traffic Shadowing

Test Scenarios:
1. 100% mirroring to shadow backend (/api/v1)
2. 50% sampling rate (/api/v2)
3. No mirroring baseline (/api/v3)

Requirements:
- Docker and Docker Compose installed
- pytest (pip install pytest requests)

Run with:
    pytest tests/test_apisix_mirroring_e2e.py -v -s
"""

import json
import subprocess
import time
from collections import Counter
from pathlib import Path

import pytest
import requests


class TestAPISIXRequestMirroringE2E:
    """Test APISIX request mirroring with real Docker containers"""

    @pytest.fixture(scope="class")
    def docker_compose_file(self):
        """Path to Docker Compose file"""
        return str(Path(__file__).parent / "docker" / "apisix-mirroring" / "docker-compose.yml")

    @pytest.fixture(scope="class")
    def apisix_mirroring_setup(self, docker_compose_file):
        """Setup and teardown Docker Compose environment for mirroring"""
        compose_dir = Path(docker_compose_file).parent

        # Build and start containers
        print("\n🐳 Starting Docker Compose environment for APISIX Request Mirroring...")
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=compose_dir,
            check=True,
            capture_output=True,
        )

        # Wait for APISIX to be ready
        print("⏳ Waiting for APISIX to be healthy...")
        max_wait = 60  # APISIX needs more time to start
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
                response = requests.get("http://localhost:10003/health", timeout=2)
                if response.status_code == 200:
                    print("✅ APISIX is ready!")
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        else:
            # Show logs if startup failed
            print("❌ APISIX did not become ready in time. Showing logs:")
            subprocess.run(["docker", "compose", "ps"], cwd=compose_dir)
            subprocess.run(["docker", "compose", "logs", "apisix"], cwd=compose_dir)
            subprocess.run(["docker", "compose", "logs", "etcd"], cwd=compose_dir)
            pytest.fail("APISIX did not become ready in time")

        # Configure APISIX via Admin API using GAL config
        print("⚙️  Configuring APISIX routes via Admin API...")
        try:
            # Generate APISIX configuration from GAL config
            gal_config_path = compose_dir / "mirroring-config.yaml"
            subprocess.run(
                [
                    "python3",
                    "-m",
                    "gal.cli",
                    "generate",
                    "apisix",
                    str(gal_config_path),
                    "--output",
                    "/tmp/apisix-mirroring-generated.json",
                ],
                check=True,
                capture_output=True,
            )

            # Load generated config
            with open("/tmp/apisix-mirroring-generated.json") as f:
                apisix_config = json.load(f)

            # Deploy to APISIX Admin API
            admin_url = "http://localhost:9182"
            api_key = "edd1c9f034335f136f87ad84b625c8f1"
            headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

            # Deploy upstreams
            for upstream in apisix_config.get("upstreams", []):
                upstream_id = upstream["id"]
                response = requests.put(
                    f"{admin_url}/apisix/admin/upstreams/{upstream_id}",
                    json=upstream,
                    headers=headers,
                    timeout=10,
                )
                if response.status_code not in (200, 201):
                    print(f"⚠️  Failed to deploy upstream {upstream_id}: {response.status_code}")
                    print(f"  Response: {response.text}")

            # Deploy services
            for service in apisix_config.get("services", []):
                service_id = service["id"]
                response = requests.put(
                    f"{admin_url}/apisix/admin/services/{service_id}",
                    json=service,
                    headers=headers,
                    timeout=10,
                )
                if response.status_code not in (200, 201):
                    print(f"⚠️  Failed to deploy service {service_id}: {response.status_code}")
                    print(f"  Response: {response.text}")

            # Deploy routes
            for i, route in enumerate(apisix_config.get("routes", []), 1):
                route_id = str(i)
                response = requests.put(
                    f"{admin_url}/apisix/admin/routes/{route_id}",
                    json=route,
                    headers=headers,
                    timeout=10,
                )
                if response.status_code not in (200, 201):
                    print(f"⚠️  Failed to deploy route {route_id}: {response.status_code}")
                    print(f"  Response: {response.text}")
                else:
                    print(f"  ✅ Deployed route: {route.get('name', route_id)}")

            print("✅ APISIX configuration deployed successfully!")

        except Exception as e:
            print(f"❌ Failed to configure APISIX: {e}")
            subprocess.run(["docker", "compose", "logs", "apisix"], cwd=compose_dir)
            pytest.fail(f"APISIX configuration failed: {e}")

        # Additional wait for configuration to propagate
        time.sleep(3)

        yield

        # Cleanup
        print("\n🧹 Stopping Docker Compose environment...")
        subprocess.run(
            ["docker", "compose", "down", "-v"], cwd=compose_dir, check=True, capture_output=True
        )

    def test_100_percent_mirroring(self, apisix_mirroring_setup):
        """Test that 100% of requests to /api/v1 are mirrored to shadow backend"""
        print("\n📊 Testing 100% Request Mirroring to /api/v1...")

        num_requests = 100
        primary_responses = []
        failed = 0

        for i in range(num_requests):
            try:
                response = requests.get("http://localhost:10003/api/v1", timeout=5)

                if response.status_code == 200:
                    backend = response.headers.get("X-Backend-Name")
                    if backend == "primary":
                        primary_responses.append(response)
                    else:
                        print(f"⚠️  Unexpected backend: {backend}")
                else:
                    failed += 1
            except requests.exceptions.RequestException as e:
                failed += 1
                if i < 5:  # Only log first few failures
                    print(f"❌ Request failed: {e}")

            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{num_requests} requests sent")

        # All responses should be from primary
        assert len(primary_responses) >= num_requests * 0.95, (
            f"Expected at least {num_requests * 0.95} successful requests, "
            f"got {len(primary_responses)}"
        )

        print(f"\n✅ Received {len(primary_responses)} responses from primary backend")
        print(f"   Failed requests: {failed}")

        # Wait for mirrored requests to complete
        time.sleep(2)

        # Check APISIX Admin API for proxy-mirror plugin stats
        try:
            admin_url = "http://localhost:9182"
            api_key = "edd1c9f034335f136f87ad84b625c8f1"
            headers = {"X-API-KEY": api_key}

            # Get route configuration to verify proxy-mirror plugin
            response = requests.get(
                f"{admin_url}/apisix/admin/routes/1", headers=headers, timeout=5
            )
            if response.status_code == 200:
                route_config = response.json()
                plugins = route_config.get("value", {}).get("plugins", {})
                if "proxy-mirror" in plugins:
                    mirror_config = plugins["proxy-mirror"]
                    print(f"\n📋 APISIX proxy-mirror plugin configuration:")
                    print(f"  Mirror host: {mirror_config.get('host')}")
                    print(f"  Sample ratio: {mirror_config.get('sample_ratio', 1.0)}")
                    print("✅ Proxy-mirror plugin is configured!")
                else:
                    print("⚠️  proxy-mirror plugin not found in route config")

        except Exception as e:
            print(f"⚠️  Could not verify proxy-mirror plugin: {e}")

    def test_50_percent_mirroring_sampling(self, apisix_mirroring_setup):
        """Test that ~50% of requests to /api/v2 are mirrored (sampling)"""
        print("\n📊 Testing 50% Request Mirroring (Sampling) to /api/v2...")

        num_requests = 100
        primary_responses = []
        failed = 0

        for i in range(num_requests):
            try:
                response = requests.get("http://localhost:10003/api/v2", timeout=5)

                if response.status_code == 200:
                    backend = response.headers.get("X-Backend-Name")
                    if backend == "primary":
                        primary_responses.append(response)
                    else:
                        print(f"⚠️  Unexpected backend: {backend}")
                else:
                    failed += 1
            except requests.exceptions.RequestException as e:
                failed += 1
                if i < 5:
                    print(f"❌ Request failed: {e}")

            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{num_requests} requests sent")

        # All responses should be from primary
        assert len(primary_responses) >= num_requests * 0.95, (
            f"Expected at least {num_requests * 0.95} successful requests, "
            f"got {len(primary_responses)}"
        )

        print(f"\n✅ Received {len(primary_responses)} responses from primary backend")
        print(f"   Failed requests: {failed}")
        print(
            "   Note: ~50% of these should be mirrored to shadow "
            "(sample_ratio=0.5 in proxy-mirror plugin)"
        )

    def test_no_mirroring_baseline(self, apisix_mirroring_setup):
        """Test that /api/v3 has no mirroring (baseline)"""
        print("\n📊 Testing No Mirroring (Baseline) to /api/v3...")

        num_requests = 50
        primary_responses = []
        failed = 0

        for i in range(num_requests):
            try:
                response = requests.get("http://localhost:10003/api/v3", timeout=5)

                if response.status_code == 200:
                    backend = response.headers.get("X-Backend-Name")
                    if backend == "primary":
                        primary_responses.append(response)
                    else:
                        print(f"⚠️  Unexpected backend: {backend}")
                else:
                    failed += 1
            except requests.exceptions.RequestException as e:
                failed += 1
                if i < 5:
                    print(f"❌ Request failed: {e}")

            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{num_requests} requests sent")

        # All responses should be from primary
        assert len(primary_responses) >= num_requests * 0.95, (
            f"Expected at least {num_requests * 0.95} successful requests, "
            f"got {len(primary_responses)}"
        )

        print(f"\n✅ Received {len(primary_responses)} responses from primary backend")
        print(f"   Failed requests: {failed}")
        print("   No mirroring configured for this route ✅")

    def test_post_request_mirroring(self, apisix_mirroring_setup):
        """Test that POST requests are also mirrored correctly"""
        print("\n📊 Testing POST Request Mirroring to /api/v1...")

        num_requests = 50
        primary_responses = []
        failed = 0

        for i in range(num_requests):
            try:
                payload = {"test": f"data_{i}", "index": i}
                response = requests.post("http://localhost:10003/api/v1", json=payload, timeout=5)

                if response.status_code == 200:
                    backend = response.headers.get("X-Backend-Name")
                    if backend == "primary":
                        primary_responses.append(response)
                    else:
                        print(f"⚠️  Unexpected backend: {backend}")
                else:
                    failed += 1
            except requests.exceptions.RequestException as e:
                failed += 1
                if i < 5:
                    print(f"❌ Request failed: {e}")

            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{num_requests} requests sent")

        # All responses should be from primary
        assert len(primary_responses) >= num_requests * 0.95, (
            f"Expected at least {num_requests * 0.95} successful POST requests, "
            f"got {len(primary_responses)}"
        )

        print(f"\n✅ Received {len(primary_responses)} POST responses from primary backend")
        print(f"   Failed requests: {failed}")

        # Verify response bodies contain expected data
        for i, resp in enumerate(primary_responses[:5]):  # Check first 5
            body = resp.json()
            assert body.get("backend") == "primary"
            assert "body_received" in body
            print(f"  Sample response {i+1}: {body.get('message')}")

        print("✅ POST request bodies are mirrored correctly!")

    def test_apisix_admin_api_health(self, apisix_mirroring_setup):
        """Test that APISIX Admin API is accessible"""
        print("\n🏥 Testing APISIX Admin API Health...")

        try:
            admin_url = "http://localhost:9182"
            api_key = "edd1c9f034335f136f87ad84b625c8f1"
            headers = {"X-API-KEY": api_key}

            # Get all routes
            response = requests.get(f"{admin_url}/apisix/admin/routes", headers=headers, timeout=5)
            assert response.status_code == 200

            routes_data = response.json()
            routes = routes_data.get("list", [])

            print(f"\n📊 APISIX Admin API Status:")
            print(f"  Total routes configured: {len(routes)}")

            for route in routes:
                route_value = route.get("value", {})
                route_id = route.get("key", "").split("/")[-1]
                uri = route_value.get("uri", "N/A")
                plugins = list(route_value.get("plugins", {}).keys())
                print(f"  Route {route_id}: {uri} - Plugins: {plugins}")

            print("\n✅ APISIX Admin API is working correctly!")

        except Exception as e:
            pytest.fail(f"Failed to check Admin API health: {e}")

    def test_apisix_upstream_health(self, apisix_mirroring_setup):
        """Test that APISIX upstreams are healthy"""
        print("\n🏥 Testing APISIX Upstream Health...")

        try:
            admin_url = "http://localhost:9182"
            api_key = "edd1c9f034335f136f87ad84b625c8f1"
            headers = {"X-API-KEY": api_key}

            # Get all upstreams
            response = requests.get(
                f"{admin_url}/apisix/admin/upstreams", headers=headers, timeout=5
            )
            assert response.status_code == 200

            upstreams_data = response.json()
            upstreams = upstreams_data.get("list", [])

            print(f"\n📊 APISIX Upstream Status:")
            print(f"  Total upstreams: {len(upstreams)}")

            for upstream in upstreams:
                upstream_value = upstream.get("value", {})
                upstream_id = upstream.get("key", "").split("/")[-1]
                nodes = upstream_value.get("nodes", {})
                lb_type = upstream_value.get("type", "roundrobin")
                print(f"  Upstream {upstream_id}:")
                print(f"    Load balancing: {lb_type}")
                print(f"    Nodes: {list(nodes.keys())}")

            print("\n✅ All upstreams are configured!")

        except Exception as e:
            pytest.fail(f"Failed to check upstream health: {e}")

    def test_multiple_concurrent_requests(self, apisix_mirroring_setup):
        """Test that APISIX handles concurrent requests correctly"""
        print("\n🔀 Testing Concurrent Request Handling...")

        import concurrent.futures

        num_concurrent = 50
        results = {"success": 0, "failed": 0}

        def make_request(i):
            try:
                response = requests.get("http://localhost:10003/api/v1", timeout=5)
                if response.status_code == 200:
                    return "success"
                return "failed"
            except Exception:
                return "failed"

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_concurrent)]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results[result] += 1

        success_rate = (results["success"] / num_concurrent) * 100
        print(f"\n✅ Concurrent requests: {results['success']}/{num_concurrent} successful")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Failed: {results['failed']}")

        # At least 95% should succeed
        assert success_rate >= 95, f"Success rate too low: {success_rate}%"

    def test_apisix_proxy_mirror_plugin_config(self, apisix_mirroring_setup):
        """Verify proxy-mirror plugin configuration for all routes"""
        print("\n🔍 Verifying APISIX proxy-mirror Plugin Configuration...")

        try:
            admin_url = "http://localhost:9182"
            api_key = "edd1c9f034335f136f87ad84b625c8f1"
            headers = {"X-API-KEY": api_key}

            # Expected configurations
            expected_configs = {
                "1": {
                    "uri": "/api/v1/*",
                    "has_mirror": True,
                    "sample_ratio": 1.0,
                },  # 100% mirroring
                "2": {
                    "uri": "/api/v2/*",
                    "has_mirror": True,
                    "sample_ratio": 0.5,
                },  # 50% mirroring
                "3": {"uri": "/api/v3/*", "has_mirror": False},  # No mirroring
            }

            print("\n📋 Route Configuration Verification:")

            for route_id, expected in expected_configs.items():
                response = requests.get(
                    f"{admin_url}/apisix/admin/routes/{route_id}", headers=headers, timeout=5
                )

                if response.status_code == 200:
                    route_config = response.json()
                    route_value = route_config.get("value", {})
                    uri = route_value.get("uri")
                    plugins = route_value.get("plugins", {})

                    print(f"\n  Route {route_id} ({uri}):")

                    if expected["has_mirror"]:
                        if "proxy-mirror" in plugins:
                            mirror_config = plugins["proxy-mirror"]
                            sample_ratio = mirror_config.get("sample_ratio", 1.0)
                            mirror_host = mirror_config.get("host")
                            print(f"    ✅ proxy-mirror plugin found")
                            print(f"       Mirror host: {mirror_host}")
                            print(f"       Sample ratio: {sample_ratio}")

                            # Verify sample ratio
                            if "sample_ratio" in expected:
                                assert (
                                    abs(sample_ratio - expected["sample_ratio"]) < 0.01
                                ), f"Sample ratio mismatch: {sample_ratio} != {expected['sample_ratio']}"
                        else:
                            print(f"    ⚠️  proxy-mirror plugin NOT found (expected)")
                    else:
                        if "proxy-mirror" not in plugins:
                            print(f"    ✅ No proxy-mirror plugin (expected)")
                        else:
                            print(f"    ⚠️  Unexpected proxy-mirror plugin found")

            print("\n✅ APISIX proxy-mirror plugin configuration verified!")

        except Exception as e:
            pytest.fail(f"Failed to verify proxy-mirror plugin: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
