#!/usr/bin/env python3
"""
Comprehensive test suite for Envoy Advanced Routing.
Tests all routing scenarios: Header, Query, JWT, GeoIP, and Fallback.
"""

import requests
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class RoutingType(Enum):
    """Types of routing rules"""
    HEADER = "header"
    QUERY = "query"
    JWT = "jwt"
    GEOIP = "geoip"
    FALLBACK = "fallback"
    COMBINED = "combined"


@dataclass
class TestCase:
    """Test case definition"""
    name: str
    routing_type: RoutingType
    url: str
    expected_backend: str
    headers: Optional[Dict[str, str]] = None
    description: str = ""

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


@dataclass
class TestResult:
    """Test result"""
    test_case: TestCase
    passed: bool
    actual_backend: str
    routing_rule: Optional[str] = None
    response_time_ms: float = 0.0
    error: Optional[str] = None


class EnvoyRoutingTester:
    """Test runner for Envoy routing scenarios"""

    def __init__(self, envoy_url: str = "http://localhost:8080", admin_url: str = "http://localhost:9901"):
        self.envoy_url = envoy_url
        self.admin_url = admin_url
        self.results: List[TestResult] = []

    def check_envoy_ready(self) -> bool:
        """Check if Envoy is ready"""
        try:
            response = requests.get(f"{self.admin_url}/ready", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Envoy not ready: {e}")
            return False

    def run_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        try:
            start_time = time.time()
            response = requests.get(
                test_case.url,
                headers=test_case.headers,
                timeout=10
            )
            response_time_ms = (time.time() - start_time) * 1000

            # Extract backend name from response
            try:
                response_json = response.json()
                # Handle nested backend object
                if isinstance(response_json.get("backend"), dict):
                    actual_backend = response_json["backend"].get("name", "unknown")
                else:
                    actual_backend = response_json.get("backend_name", response_json.get("backend", "unknown"))
            except json.JSONDecodeError:
                actual_backend = "unknown"

            # Extract routing rule from response headers
            routing_rule = response.headers.get("X-Routing-Rule", "none")

            # Check if test passed
            passed = actual_backend == test_case.expected_backend

            return TestResult(
                test_case=test_case,
                passed=passed,
                actual_backend=actual_backend,
                routing_rule=routing_rule,
                response_time_ms=response_time_ms
            )

        except Exception as e:
            return TestResult(
                test_case=test_case,
                passed=False,
                actual_backend="error",
                error=str(e)
            )

    def run_all_tests(self) -> Tuple[int, int]:
        """Run all test cases and return (passed, failed) counts"""
        test_cases = self._get_test_cases()

        print("\n" + "=" * 80)
        print("🚀 Envoy Advanced Routing Test Suite")
        print("=" * 80 + "\n")

        # Check Envoy readiness
        print("🔍 Checking Envoy availability...")
        if not self.check_envoy_ready():
            print("❌ ERROR: Envoy is not running!")
            print("   Please start with: docker compose -f docker-compose-improved.yml up -d")
            return 0, 0

        print("✅ Envoy is ready\n")

        # Group test cases by routing type
        test_groups = {}
        for tc in test_cases:
            if tc.routing_type not in test_groups:
                test_groups[tc.routing_type] = []
            test_groups[tc.routing_type].append(tc)

        # Run tests by group
        passed_count = 0
        failed_count = 0

        for routing_type, tests in test_groups.items():
            print("=" * 80)
            print(f"📋 {routing_type.value.upper()} ROUTING TESTS")
            print("=" * 80 + "\n")

            for test_case in tests:
                print(f"🧪 {test_case.name}")
                if test_case.description:
                    print(f"   📝 {test_case.description}")

                result = self.run_test(test_case)
                self.results.append(result)

                if result.passed:
                    print(f"   ✅ PASS")
                    print(f"      Expected: {test_case.expected_backend}")
                    print(f"      Got: {result.actual_backend}")
                    if result.routing_rule and result.routing_rule != "none":
                        print(f"      Routing Rule: {result.routing_rule}")
                    print(f"      Response Time: {result.response_time_ms:.2f}ms")
                    passed_count += 1
                else:
                    print(f"   ❌ FAIL")
                    print(f"      Expected: {test_case.expected_backend}")
                    print(f"      Got: {result.actual_backend}")
                    if result.error:
                        print(f"      Error: {result.error}")
                    failed_count += 1

                print()

        return passed_count, failed_count

    def _get_test_cases(self) -> List[TestCase]:
        """Get all test cases"""
        return [
            # Header-based Routing
            TestCase(
                name="Header: X-API-Version=v2",
                routing_type=RoutingType.HEADER,
                url=f"{self.envoy_url}/api/test",
                expected_backend="backend-v2",
                headers={"X-API-Version": "v2"},
                description="Route to v2 backend based on API version header"
            ),
            TestCase(
                name="Header: User-Agent contains Mobile",
                routing_type=RoutingType.HEADER,
                url=f"{self.envoy_url}/api/test",
                expected_backend="backend-mobile",
                headers={"User-Agent": "Mozilla/5.0 (Mobile; Android)"},
                description="Route to mobile backend for mobile user agents"
            ),
            TestCase(
                name="Header: X-Beta-Features=enabled",
                routing_type=RoutingType.HEADER,
                url=f"{self.envoy_url}/api/test",
                expected_backend="backend-beta",
                headers={"X-Beta-Features": "enabled"},
                description="Route to beta backend when beta features are enabled"
            ),

            # Query Parameter Routing
            TestCase(
                name="Query: version=2",
                routing_type=RoutingType.QUERY,
                url=f"{self.envoy_url}/api/test?version=2",
                expected_backend="backend-v2",
                description="Route to v2 backend via query parameter"
            ),
            TestCase(
                name="Query: beta=true",
                routing_type=RoutingType.QUERY,
                url=f"{self.envoy_url}/api/test?beta=true",
                expected_backend="backend-beta",
                description="Route to beta backend via query parameter"
            ),
            TestCase(
                name="Query: admin present",
                routing_type=RoutingType.QUERY,
                url=f"{self.envoy_url}/api/test?admin",
                expected_backend="backend-admin",
                description="Route to admin backend when admin param is present"
            ),

            # JWT-based Routing (requires valid JWT token)
            # Token generated by: tests/e2e/docker/tools/keygen/generate_local.py
            TestCase(
                name="JWT: role=admin claim",
                routing_type=RoutingType.JWT,
                url=f"{self.envoy_url}/api/admin/test",
                expected_backend="backend-admin",
                headers={
                    "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InRlc3Qta2V5In0.eyJzdWIiOiJ0ZXN0LWFkbWluLXVzZXIiLCJuYW1lIjoiQWRtaW4gVXNlciIsInJvbGUiOiJhZG1pbiIsImF1ZCI6IngtZ2FsLXRlc3QiLCJpc3MiOiJodHRwczovL2p3a3Mtc2VydmljZSIsImlhdCI6MTc2MTMwNjgyOCwiZXhwIjoxNzYxMzQyODI4fQ.UDww6Ma71OOLLeQdq4I3hfdlG5g1fsXfEAA_nl_qAWI-_Jt6uPe2_TNy_7tYOQLhW5sNj4LXlCAgKtfgImqRHv2hM6R_iKOCQ9bErjbIDOMoo_hs-LUKwOQwwVvR2aFIwp6a4BJbfZCBXPqpQ_RAalQ8i3lyQE1OdhVcQaWRtHIfx3JlRC0YK79oT_hxZ43uy-p2ZAWgTePhWE7RR4CO-suxjh9NJHryjIvjchHVdOLcMaPQcohfYBg92blfJmnnM306V6PP7HOWMebU-6fCY3Grh8W-Jpr92OpUS0J7O3TGZa2A8Pr_i6wDfj5E3n1tcS3Fm1hl6QmUwagowZi-gg"
                },
                description="Route to admin backend based on JWT role claim"
            ),

            # GeoIP-based Routing
            TestCase(
                name="GeoIP: country=DE (German IP)",
                routing_type=RoutingType.GEOIP,
                url=f"{self.envoy_url}/api/eu/test",
                expected_backend="backend-eu",
                headers={"X-Forwarded-For": "192.168.1.1"},
                description="Route to EU backend for German IP addresses"
            ),

            # Fallback Routing
            TestCase(
                name="Fallback: no rules match",
                routing_type=RoutingType.FALLBACK,
                url=f"{self.envoy_url}/api/test",
                expected_backend="backend-v1",
                description="Route to default v1 backend when no rules match"
            ),

            # Combined Routing (first match wins)
            TestCase(
                name="Combined: X-API-Version=v2 + X-Beta-Features=enabled",
                routing_type=RoutingType.COMBINED,
                url=f"{self.envoy_url}/api/test",
                expected_backend="backend-v2",
                headers={
                    "X-API-Version": "v2",
                    "X-Beta-Features": "enabled"
                },
                description="First matching rule (X-API-Version) should win"
            ),
            TestCase(
                name="Combined: Header + Query (header first)",
                routing_type=RoutingType.COMBINED,
                url=f"{self.envoy_url}/api/test?beta=true",
                expected_backend="backend-v2",
                headers={"X-API-Version": "v2"},
                description="Header-based routing should take precedence over query"
            ),
        ]

    def print_summary(self, passed: int, failed: int):
        """Print test summary"""
        total = passed + failed
        pass_rate = (passed / total * 100) if total > 0 else 0

        print("=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed} ({pass_rate:.1f}%)")
        print(f"❌ Failed: {failed}")
        print("=" * 80)

        # Statistics by routing type
        print("\n📈 Statistics by Routing Type:")
        stats = {}
        for result in self.results:
            rt = result.test_case.routing_type.value
            if rt not in stats:
                stats[rt] = {"passed": 0, "failed": 0, "total_time": 0.0}
            if result.passed:
                stats[rt]["passed"] += 1
            else:
                stats[rt]["failed"] += 1
            stats[rt]["total_time"] += result.response_time_ms

        for rt, s in stats.items():
            total_tests = s["passed"] + s["failed"]
            avg_time = s["total_time"] / total_tests if total_tests > 0 else 0
            print(f"   {rt.upper()}: {s['passed']}/{total_tests} passed (avg: {avg_time:.2f}ms)")

        print()

    def run_performance_test(self, num_requests: int = 100):
        """Run performance test"""
        print("=" * 80)
        print(f"⚡ PERFORMANCE TEST ({num_requests} requests)")
        print("=" * 80 + "\n")

        url = f"{self.envoy_url}/api/test"
        response_times = []

        print(f"Sending {num_requests} requests...")
        start_time = time.time()

        for i in range(num_requests):
            try:
                req_start = time.time()
                response = requests.get(url, timeout=10)
                req_time = (time.time() - req_start) * 1000
                response_times.append(req_time)

                if (i + 1) % 10 == 0:
                    print(f"   Progress: {i + 1}/{num_requests}", end="\r")
            except Exception as e:
                print(f"   Error on request {i + 1}: {e}")

        total_time = (time.time() - start_time) * 1000

        # Calculate statistics
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            sorted_times = sorted(response_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]

            print(f"\n\n✅ Completed {len(response_times)} requests in {total_time:.2f}ms")
            print(f"   Throughput: {len(response_times) / (total_time / 1000):.2f} req/s")
            print(f"   Avg Response Time: {avg_time:.2f}ms")
            print(f"   Min: {min_time:.2f}ms")
            print(f"   Max: {max_time:.2f}ms")
            print(f"   P50: {p50:.2f}ms")
            print(f"   P95: {p95:.2f}ms")
            print(f"   P99: {p99:.2f}ms")
            print()

    def check_admin_api(self):
        """Check Envoy admin API"""
        print("=" * 80)
        print("🔧 ENVOY ADMIN API")
        print("=" * 80 + "\n")

        # Check stats
        try:
            response = requests.get(f"{self.admin_url}/stats", timeout=5)
            if response.status_code == 200:
                # Filter for cluster health stats
                stats = [line for line in response.text.split("\n") if "cluster" in line and "health" in line]
                print("Cluster Health Stats:")
                for stat in stats[:10]:  # First 10 lines
                    print(f"   {stat}")
                print()
        except Exception as e:
            print(f"   ❌ Error getting stats: {e}\n")

        # Check clusters
        try:
            response = requests.get(f"{self.admin_url}/clusters", timeout=5)
            if response.status_code == 200:
                clusters = [line for line in response.text.split("\n") if "::" in line]
                print("Active Clusters:")
                for cluster in clusters[:10]:  # First 10 lines
                    print(f"   {cluster}")
                print()
        except Exception as e:
            print(f"   ❌ Error getting clusters: {e}\n")


def main():
    """Main test runner"""
    tester = EnvoyRoutingTester()

    # Run all routing tests
    passed, failed = tester.run_all_tests()

    # Print summary
    tester.print_summary(passed, failed)

    # Run performance test
    tester.run_performance_test(num_requests=100)

    # Check admin API
    tester.check_admin_api()

    # Exit code
    exit_code = 0 if failed == 0 else 1
    if exit_code == 0:
        print("🎉 All tests passed!")
    else:
        print(f"❌ {failed} test(s) failed")

    return exit_code


if __name__ == "__main__":
    exit(main())
