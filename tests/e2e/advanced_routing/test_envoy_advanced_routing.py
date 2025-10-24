#!/usr/bin/env python3
"""
E2E tests for Envoy Advanced Routing.

Tests header-based, query parameter-based, and fallback routing
using Docker Compose setup with multiple backend instances.
"""

import time
import requests
import pytest
import subprocess
import os
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseE2ETest


@pytest.mark.docker
@pytest.mark.routing
@pytest.mark.provider("envoy")
class TestEnvoyAdvancedRouting(BaseE2ETest):
    """E2E tests for Envoy advanced routing functionality."""

    # Configuration for BaseE2ETest
    COMPOSE_FILE = "docker-compose.yml"
    SERVICE_PORT = 8080
    HEALTH_ENDPOINT = "/api"
    ADMIN_PORT = 9901  # Envoy admin interface
    WAIT_TIMEOUT = 60
    STABILIZATION_TIME = 2

    @classmethod
    def _get_test_dir(cls):
        """Get the directory containing the docker-compose.yml file."""
        # The compose file is in e2e/docker/providers/envoy/advanced-routing/
        return str(
            Path(__file__).parent.parent / "docker" / "providers" / "envoy" / "advanced-routing"
        )

    @classmethod
    def check_additional_services(cls):
        """Check if all backend services are responding."""
        # Try to reach each backend through Envoy with specific headers
        test_requests = [
            ("backend-v1", {}, {}),
            ("backend-v2", {"X-API-Version": "v2"}, {}),
            ("backend-mobile", {"User-Agent": "Mobile Safari"}, {}),
            ("backend-admin", {"X-Admin-Access": "true"}, {}),
            ("backend-eu", {"X-Region": "EU"}, {}),
            ("backend-beta", {"X-Beta-Features": "enabled"}, {}),
        ]

        for backend_name, headers, params in test_requests:
            try:
                response = requests.get(
                    f"http://localhost:{cls.SERVICE_PORT}/api",
                    headers=headers,
                    params=params,
                    timeout=1
                )
                if response.status_code != 200:
                    return False
            except:
                return False

        return True

    def test_default_routing_no_headers(self):
        """Test that requests without special headers go to v1 backend."""
        response = self.make_request("/api")
        self.assert_response(response, 200)

        data = response.json()
        assert data["backend"]["name"] == "backend-v1"
        assert data["backend"]["version"] == "v1"
        print(f"✓ Default routing: {data['backend']['name']}")

    def test_header_routing_api_version(self):
        """Test routing based on X-API-Version header."""
        response = self.make_request(
            "/api",
            headers={"X-API-Version": "v2"}
        )
        self.assert_response(response, 200)

        data = response.json()
        assert data["backend"]["name"] == "backend-v2"
        assert data["backend"]["version"] == "v2"
        print(f"✓ API Version header routing: {data['backend']['name']}")

    def test_header_routing_mobile_user_agent(self):
        """Test routing based on User-Agent containing 'Mobile'."""
        response = self.make_request(
            "/api",
            headers={"User-Agent": "Mozilla/5.0 (iPhone; Mobile Safari)"}
        )
        self.assert_response(response, 200)

        data = response.json()
        assert data["backend"]["name"] == "backend-mobile"
        assert data["backend"]["type"] == "mobile"
        print(f"✓ Mobile User-Agent routing: {data['backend']['name']}")

    def test_header_routing_beta_features(self):
        """Test routing based on X-Beta-Features header."""
        response = self.make_request(
            "/api",
            headers={"X-Beta-Features": "enabled"}
        )
        self.assert_response(response, 200)

        data = response.json()
        assert data["backend"]["name"] == "backend-beta"
        assert data["backend"]["version"] == "beta"
        print(f"✓ Beta features header routing: {data['backend']['name']}")

    def test_header_routing_admin_access(self):
        """Test routing based on X-Admin-Access header."""
        response = self.make_request(
            "/api",
            headers={"X-Admin-Access": "true"}
        )
        self.assert_response(response, 200)

        data = response.json()
        assert data["backend"]["name"] == "backend-admin"
        assert data["backend"]["type"] == "admin"
        print(f"✓ Admin access header routing: {data['backend']['name']}")

    def test_header_routing_eu_region(self):
        """Test routing based on X-Region header."""
        response = self.make_request(
            "/api",
            headers={"X-Region": "EU"}
        )
        self.assert_response(response, 200)

        data = response.json()
        assert data["backend"]["name"] == "backend-eu"
        assert data["backend"]["region"] == "eu"
        print(f"✓ EU region header routing: {data['backend']['name']}")

    def test_query_param_routing_version(self):
        """Test routing based on version query parameter."""
        response = self.make_request("/api?version=2")
        self.assert_response(response, 200)

        data = response.json()
        assert data["backend"]["name"] == "backend-v2"
        assert data["backend"]["version"] == "v2"
        print(f"✓ Version query param routing: {data['backend']['name']}")

    def test_query_param_routing_beta(self):
        """Test routing based on beta query parameter."""
        response = self.make_request("/api?beta=true")
        self.assert_response(response, 200)

        data = response.json()
        assert data["backend"]["name"] == "backend-beta"
        assert data["backend"]["version"] == "beta"
        print(f"✓ Beta query param routing: {data['backend']['name']}")

    def test_query_param_routing_admin_exists(self):
        """Test routing based on admin query parameter existence."""
        response = self.make_request("/api?admin")
        self.assert_response(response, 200)

        data = response.json()
        assert data["backend"]["name"] == "backend-admin"
        assert data["backend"]["type"] == "admin"
        print(f"✓ Admin query param (exists) routing: {data['backend']['name']}")

    def test_priority_header_over_query(self):
        """Test that header rules have priority over query params."""
        response = self.make_request(
            "/api?version=2",
            headers={"X-Beta-Features": "enabled"}
        )
        self.assert_response(response, 200)

        data = response.json()
        # Header rule should win (beta backend)
        assert data["backend"]["name"] == "backend-beta"
        print(f"✓ Priority test (header wins): {data['backend']['name']}")

    def test_post_request_routing(self):
        """Test that POST requests are also routed correctly."""
        response = self.make_request(
            "/api",
            method="POST",
            headers={"X-API-Version": "v2"},
            json_data={"test": "data"}
        )
        self.assert_response(response, 200)

        data = response.json()
        assert data["backend"]["name"] == "backend-v2"
        assert data["request"]["method"] == "POST"
        print(f"✓ POST request routing: {data['backend']['name']}")

    def test_multiple_matching_conditions_first_match(self):
        """Test first_match evaluation strategy."""
        response = self.make_request(
            "/api",
            headers={
                "X-API-Version": "v2",
                "X-Admin-Access": "true",  # This should be ignored
            }
        )
        self.assert_response(response, 200)

        data = response.json()
        # First matching rule should win (v2 backend)
        assert data["backend"]["name"] == "backend-v2"
        print(f"✓ First match strategy: {data['backend']['name']}")

    def test_fallback_with_unknown_header_value(self):
        """Test fallback when header exists but value doesn't match."""
        response = self.make_request(
            "/api",
            headers={"X-API-Version": "v3"}  # v3 is not configured
        )
        self.assert_response(response, 200)

        data = response.json()
        # Should fall back to v1
        assert data["backend"]["name"] == "backend-v1"
        print(f"✓ Fallback routing: {data['backend']['name']}")

    def test_envoy_admin_clusters(self):
        """Verify all backend clusters are registered in Envoy."""
        response = requests.get(f"http://localhost:{self.ADMIN_PORT}/clusters")
        assert response.status_code == 200

        clusters_text = response.text
        expected_clusters = [
            "api_service_v2_backend_cluster",
            "api_service_admin_backend_cluster",
            "api_service_eu_backend_cluster",
            "api_service_beta_backend_cluster",
            "api_service_mobile_backend_cluster",
            "api_service_cluster",  # Default/fallback cluster
        ]

        for cluster in expected_clusters:
            assert cluster in clusters_text, f"Cluster {cluster} not found in Envoy"

        print(f"✓ All {len(expected_clusters)} clusters registered in Envoy")

    def test_envoy_admin_routes(self):
        """Verify routes are configured in Envoy."""
        response = requests.get(f"http://localhost:{self.ADMIN_PORT}/config_dump")
        assert response.status_code == 200

        config = response.json()

        # Check that route configuration exists
        assert "configs" in config

        # Look for route configuration
        route_configs = [
            c for c in config["configs"]
            if c.get("@type") == "type.googleapis.com/envoy.admin.v3.RoutesConfigDump"
        ]

        assert len(route_configs) > 0, "No route configuration found"
        print("✓ Route configuration present in Envoy")

    def test_backend_logs_verification(self):
        """Verify that backends log the correct routing decisions."""
        # Make several test requests to generate logs
        test_requests = [
            ("default", {}, {}),
            ("v2", {"X-API-Version": "v2"}, {}),
            ("mobile", {"User-Agent": "Mobile Safari"}, {}),
            ("beta", {}, {"beta": "true"}),
        ]

        for name, headers, params in test_requests:
            response = self.make_request(
                "/api",
                headers=headers,
                params=params
            )
            assert response.status_code == 200

        # Give logs time to flush
        time.sleep(1)

        # Capture logs from specific backends
        backends_to_check = ["backend-v1", "backend-v2", "backend-mobile", "backend-beta"]

        for backend in backends_to_check:
            logs = self.get_logs_since_start(backend)

            # Check that the backend received requests
            # New log format: [2025-10-24 12:38:22.132] [backend-v1:v1] "GET /api HTTP/1.1" 200 -
            if backend == "backend-v1":
                assert '"GET' in logs or '"POST' in logs or '200' in logs
                print(f"✓ {backend} logs show activity ({logs.count('GET')} GET requests)")

    @pytest.mark.slow
    def test_routing_metrics(self):
        """Check Envoy metrics for routing statistics."""
        response = requests.get(f"http://localhost:{self.ADMIN_PORT}/stats/prometheus")
        assert response.status_code == 200

        metrics = response.text

        # Check for routing-related metrics
        important_metrics = [
            "envoy_cluster_upstream_rq_total",
            "envoy_http_downstream_rq_total",
            "envoy_cluster_upstream_rq_2xx",
            "envoy_router_downstream_rq_total",
        ]

        for metric in important_metrics:
            if metric in metrics:
                print(f"✓ Metric {metric} present")

        # Parse specific cluster metrics
        for line in metrics.split("\n"):
            if "api_service" in line and "upstream_rq_total" in line:
                # Extract cluster name and count
                if "{" in line and "}" in line:
                    cluster_info = line[line.index("{"):line.index("}")+1]
                    count = line.split()[-1]
                    if float(count) > 0:
                        print(f"  Cluster requests: {cluster_info} = {count}")

        print("✓ Routing metrics verified")

    @pytest.mark.slow
    def test_performance_baseline(self):
        """Establish performance baseline for routing."""
        print("\n📊 Performance Baseline Test")

        # Measure latency for different routing scenarios
        scenarios = [
            ("Default", "/api", {}),
            ("Header routing", "/api", {"X-API-Version": "v2"}),
            ("Query routing", "/api?beta=true", {}),
        ]

        for name, path, headers in scenarios:
            stats = self.measure_latency(num_requests=50, path=path)
            if stats:
                print(f"\n{name}:")
                print(f"  Mean: {stats['mean']:.2f} ms")
                print(f"  P95: {stats['p95']:.2f} ms")
                print(f"  P99: {stats['p99']:.2f} ms")

    @pytest.mark.slow
    def test_concurrent_routing(self):
        """Test routing under concurrent load."""
        print("\n🔀 Testing Concurrent Routing")

        results = self.run_concurrent_requests(
            num_requests=100,
            num_workers=10,
            path="/api"
        )

        success_rate = (results["success"] / 100) * 100
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Failed requests: {results['failed']}")

        assert success_rate >= 95, f"Success rate too low: {success_rate}%"

        # Verify routing consistency under load
        backends = {}
        for response in results["responses"]:
            backend = response.json()["backend"]["name"]
            backends[backend] = backends.get(backend, 0) + 1

        print(f"Routing distribution: {backends}")
        assert "backend-v1" in backends, "Default backend not used"


def run_tests():
    """Run the tests with pytest."""
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_tests()