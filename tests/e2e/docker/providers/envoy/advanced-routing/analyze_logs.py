#!/usr/bin/env python3
"""
Log analysis utility for Advanced Routing E2E tests.

Analyzes Docker Compose logs to verify correct routing behavior
and troubleshoot issues.
"""

import re
import json
import sys
from collections import defaultdict
from datetime import datetime


class LogAnalyzer:
    """Analyze logs from Advanced Routing E2E tests."""

    def __init__(self, log_file="test_logs.txt"):
        """Initialize analyzer with log file."""
        self.log_file = log_file
        self.routing_decisions = defaultdict(list)
        self.errors = []
        self.warnings = []
        self.request_flow = []

    def parse_logs(self):
        """Parse logs and extract routing information."""
        try:
            with open(self.log_file, "r") as f:
                current_service = None
                for line in f:
                    # Identify service from Docker Compose prefix
                    service_match = re.match(r"^(\S+)\s+\|", line)
                    if service_match:
                        current_service = service_match.group(1)

                    # Extract routing decisions from Envoy
                    if current_service == "envoy":
                        self._parse_envoy_log(line)

                    # Extract backend responses
                    elif current_service and current_service.startswith("backend-"):
                        self._parse_backend_log(line, current_service)

                    # Look for errors
                    if "error" in line.lower() or "exception" in line.lower():
                        self.errors.append({
                            "service": current_service,
                            "message": line.strip()
                        })

                    # Look for warnings
                    if "warning" in line.lower() or "warn" in line.lower():
                        self.warnings.append({
                            "service": current_service,
                            "message": line.strip()
                        })

        except FileNotFoundError:
            print(f"Log file {self.log_file} not found. Run tests first.")
            return False

        return True

    def _parse_envoy_log(self, line):
        """Parse Envoy log line for routing information."""
        # Look for route selection
        if "route selected" in line.lower() or "cluster" in line.lower():
            # Extract cluster name
            cluster_match = re.search(r"cluster[:\s]+(\S+)", line, re.IGNORECASE)
            if cluster_match:
                cluster = cluster_match.group(1)
                self.routing_decisions["envoy"].append({
                    "type": "cluster_selection",
                    "cluster": cluster,
                    "line": line.strip()
                })

        # Look for header matching
        if "header" in line.lower() and "match" in line.lower():
            header_match = re.search(r"header\s+(\S+)", line, re.IGNORECASE)
            if header_match:
                self.routing_decisions["envoy"].append({
                    "type": "header_match",
                    "header": header_match.group(1),
                    "line": line.strip()
                })

        # Extract request IDs
        request_id_match = re.search(r"x-request-id[:\s]+([a-f0-9-]+)", line, re.IGNORECASE)
        if request_id_match:
            self.request_flow.append({
                "service": "envoy",
                "request_id": request_id_match.group(1),
                "line": line.strip()
            })

    def _parse_backend_log(self, line, service):
        """Parse backend log line for request handling."""
        # Look for request received
        if "received" in line.lower() and "request" in line.lower():
            # Extract method and path
            method_match = re.search(r"(GET|POST|PUT|DELETE)\s+request", line)
            if method_match:
                self.routing_decisions[service].append({
                    "type": "request_received",
                    "method": method_match.group(1),
                    "line": line.strip()
                })

        # Look for backend identification
        if "backend" in line.lower() and ("starting" in line.lower() or "version" in line.lower()):
            backend_info = re.search(r"backend[:\s]+(\S+)", line, re.IGNORECASE)
            if backend_info:
                self.routing_decisions[service].append({
                    "type": "backend_info",
                    "backend": backend_info.group(1),
                    "line": line.strip()
                })

        # Extract headers from backend logs
        if "x-api-version" in line.lower() or "user-agent" in line.lower():
            self.routing_decisions[service].append({
                "type": "header_received",
                "line": line.strip()
            })

    def generate_report(self):
        """Generate analysis report."""
        print("\n" + "=" * 80)
        print("ADVANCED ROUTING LOG ANALYSIS REPORT")
        print("=" * 80)

        # Summary
        print("\n📊 SUMMARY")
        print("-" * 40)
        print(f"Total services analyzed: {len(self.routing_decisions)}")
        print(f"Total routing decisions: {sum(len(v) for v in self.routing_decisions.values())}")
        print(f"Errors found: {len(self.errors)}")
        print(f"Warnings found: {len(self.warnings)}")

        # Routing decisions by service
        print("\n🔀 ROUTING DECISIONS BY SERVICE")
        print("-" * 40)
        for service, decisions in self.routing_decisions.items():
            print(f"\n{service}: {len(decisions)} decisions")

            # Group by type
            by_type = defaultdict(list)
            for decision in decisions:
                by_type[decision.get("type", "unknown")].append(decision)

            for decision_type, items in by_type.items():
                print(f"  - {decision_type}: {len(items)}")

                # Show first few examples
                for item in items[:2]:
                    if "cluster" in item:
                        print(f"      → Cluster: {item['cluster']}")
                    elif "backend" in item:
                        print(f"      → Backend: {item['backend']}")
                    elif "method" in item:
                        print(f"      → Method: {item['method']}")

        # Request flow analysis
        if self.request_flow:
            print("\n📋 REQUEST FLOW")
            print("-" * 40)

            # Group by request ID
            by_request_id = defaultdict(list)
            for flow in self.request_flow:
                by_request_id[flow["request_id"]].append(flow)

            for request_id, flows in list(by_request_id.items())[:5]:
                print(f"\nRequest ID: {request_id}")
                for flow in flows:
                    print(f"  - {flow['service']}")

        # Errors and warnings
        if self.errors:
            print("\n❌ ERRORS")
            print("-" * 40)
            for error in self.errors[:10]:
                print(f"[{error['service']}] {error['message'][:100]}...")

        if self.warnings:
            print("\n⚠️ WARNINGS")
            print("-" * 40)
            for warning in self.warnings[:10]:
                print(f"[{warning['service']}] {warning['message'][:100]}...")

        # Routing verification
        print("\n✅ ROUTING VERIFICATION")
        print("-" * 40)
        self._verify_routing_rules()

    def _verify_routing_rules(self):
        """Verify expected routing rules are working."""
        verifications = []

        # Check if v2 backend received v2 requests
        v2_decisions = self.routing_decisions.get("backend-v2", [])
        if any(d["type"] == "request_received" for d in v2_decisions):
            verifications.append("✓ backend-v2 received requests")

        # Check if mobile backend received mobile requests
        mobile_decisions = self.routing_decisions.get("backend-mobile", [])
        if any(d["type"] == "request_received" for d in mobile_decisions):
            verifications.append("✓ backend-mobile received requests")

        # Check if Envoy selected correct clusters
        envoy_decisions = self.routing_decisions.get("envoy", [])
        clusters_selected = set()
        for decision in envoy_decisions:
            if decision["type"] == "cluster_selection":
                clusters_selected.add(decision.get("cluster", ""))

        if "api_service_v2_backend_cluster" in clusters_selected:
            verifications.append("✓ Envoy selected v2 backend cluster")

        if "api_service_mobile_backend_cluster" in clusters_selected:
            verifications.append("✓ Envoy selected mobile backend cluster")

        # Print verifications
        for verification in verifications:
            print(verification)

        # Calculate success rate
        expected_rules = 5  # Number of routing rules we expect to work
        success_rate = (len(verifications) / expected_rules) * 100 if expected_rules > 0 else 0

        print(f"\nSuccess Rate: {success_rate:.1f}% ({len(verifications)}/{expected_rules} rules verified)")

    def analyze_performance(self):
        """Analyze performance metrics from logs."""
        print("\n📈 PERFORMANCE ANALYSIS")
        print("-" * 40)

        # Look for response times in logs
        response_times = []
        latencies = []

        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    # Look for response time patterns
                    time_match = re.search(r"response_time[:\s]+(\d+\.?\d*)\s*ms", line, re.IGNORECASE)
                    if time_match:
                        response_times.append(float(time_match.group(1)))

                    # Look for latency patterns
                    latency_match = re.search(r"latency[:\s]+(\d+\.?\d*)", line, re.IGNORECASE)
                    if latency_match:
                        latencies.append(float(latency_match.group(1)))

            if response_times:
                avg_response = sum(response_times) / len(response_times)
                max_response = max(response_times)
                min_response = min(response_times)

                print(f"Response Times:")
                print(f"  Average: {avg_response:.2f} ms")
                print(f"  Max: {max_response:.2f} ms")
                print(f"  Min: {min_response:.2f} ms")

            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                print(f"\nLatencies:")
                print(f"  Average: {avg_latency:.2f} ms")

        except Exception as e:
            print(f"Could not analyze performance: {e}")

    def export_json(self, output_file="log_analysis.json"):
        """Export analysis results to JSON."""
        results = {
            "summary": {
                "services_analyzed": len(self.routing_decisions),
                "total_routing_decisions": sum(len(v) for v in self.routing_decisions.values()),
                "errors": len(self.errors),
                "warnings": len(self.warnings)
            },
            "routing_decisions": dict(self.routing_decisions),
            "errors": self.errors,
            "warnings": self.warnings,
            "request_flow": self.request_flow
        }

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n📄 Analysis exported to {output_file}")


def main():
    """Run log analysis."""
    analyzer = LogAnalyzer()

    print("🔍 Analyzing logs from Advanced Routing E2E tests...")

    if not analyzer.parse_logs():
        sys.exit(1)

    analyzer.generate_report()
    analyzer.analyze_performance()
    analyzer.export_json()

    print("\n✨ Analysis complete!")


if __name__ == "__main__":
    main()