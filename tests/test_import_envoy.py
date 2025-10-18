"""
Tests for Envoy config import functionality (v1.3.0 Feature 1).
"""

import pytest

from gal.config import Config
from gal.providers import EnvoyProvider


class TestEnvoyImportBasic:
    """Basic Envoy config import tests."""

    def test_import_simple_cluster(self):
        """Test importing a simple Envoy cluster configuration."""
        envoy_yaml = """
static_resources:
  clusters:
  - name: api_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api.internal
                port_value: 8080
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        assert config.version == "1.0"
        assert config.provider == "envoy"
        assert len(config.services) == 1

        service = config.services[0]
        assert service.name == "api"
        assert service.type == "rest"
        assert service.protocol == "http"
        assert len(service.upstream.targets) == 1

        target = service.upstream.targets[0]
        assert target.host == "api.internal"
        assert target.port == 8080
        assert target.weight == 1

    def test_import_multiple_targets_with_weights(self):
        """Test importing cluster with multiple weighted targets."""
        envoy_yaml = """
static_resources:
  clusters:
  - name: api_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api-1.internal
                port_value: 8080
          load_balancing_weight:
            value: 3
        - endpoint:
            address:
              socket_address:
                address: api-2.internal
                port_value: 8080
          load_balancing_weight:
            value: 1
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        assert len(config.services[0].upstream.targets) == 2

        target1 = config.services[0].upstream.targets[0]
        assert target1.host == "api-1.internal"
        assert target1.weight == 3

        target2 = config.services[0].upstream.targets[1]
        assert target2.host == "api-2.internal"
        assert target2.weight == 1

    def test_import_with_routes(self):
        """Test importing Envoy config with listeners and routes."""
        envoy_yaml = """
static_resources:
  listeners:
  - name: main_listener
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 10000
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: "/api/v1"
                route:
                  cluster: api_cluster
              - match:
                  prefix: "/api/v2"
                route:
                  cluster: api_cluster
          http_filters:
          - name: envoy.filters.http.router

  clusters:
  - name: api_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api.internal
                port_value: 8080
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        assert len(config.services) == 1
        service = config.services[0]
        assert len(service.routes) == 2

        assert service.routes[0].path_prefix == "/api/v1"
        assert service.routes[1].path_prefix == "/api/v2"


class TestEnvoyImportHealthChecks:
    """Tests for health check import."""

    def test_import_active_health_check(self):
        """Test importing active HTTP health checks."""
        envoy_yaml = """
static_resources:
  clusters:
  - name: api_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api.internal
                port_value: 8080
    health_checks:
    - timeout: 3s
      interval: 5s
      unhealthy_threshold: 2
      healthy_threshold: 3
      http_health_check:
        path: "/healthz"
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        service = config.services[0]
        hc = service.upstream.health_check

        assert hc is not None
        assert hc.active is not None
        assert hc.active.enabled is True
        assert hc.active.http_path == "/healthz"
        assert hc.active.interval == "5s"
        assert hc.active.timeout == "3s"
        assert hc.active.unhealthy_threshold == 2
        assert hc.active.healthy_threshold == 3

    def test_import_passive_health_check(self):
        """Test importing passive health checks (outlier detection)."""
        envoy_yaml = """
static_resources:
  clusters:
  - name: api_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api.internal
                port_value: 8080
    outlier_detection:
      consecutive_5xx: 7
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        service = config.services[0]
        hc = service.upstream.health_check

        assert hc is not None
        assert hc.passive is not None
        assert hc.passive.enabled is True
        assert hc.passive.max_failures == 7

    def test_import_combined_health_checks(self):
        """Test importing both active and passive health checks."""
        envoy_yaml = """
static_resources:
  clusters:
  - name: api_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api.internal
                port_value: 8080
    health_checks:
    - timeout: 5s
      interval: 10s
      unhealthy_threshold: 3
      healthy_threshold: 2
      http_health_check:
        path: "/health"
    outlier_detection:
      consecutive_5xx: 5
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        service = config.services[0]
        hc = service.upstream.health_check

        assert hc is not None
        assert hc.active is not None
        assert hc.active.http_path == "/health"
        assert hc.passive is not None
        assert hc.passive.max_failures == 5


class TestEnvoyImportLoadBalancing:
    """Tests for load balancing algorithm import."""

    @pytest.mark.parametrize(
        "lb_policy,expected_algorithm",
        [
            ("ROUND_ROBIN", "round_robin"),
            ("LEAST_REQUEST", "least_conn"),
            ("RING_HASH", "ip_hash"),
            ("RANDOM", "round_robin"),  # Fallback
            ("MAGLEV", "ip_hash"),  # Consistent hashing
        ],
    )
    def test_import_load_balancing_algorithms(self, lb_policy, expected_algorithm):
        """Test importing different load balancing algorithms."""
        envoy_yaml = f"""
static_resources:
  clusters:
  - name: api_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    lb_policy: {lb_policy}
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api.internal
                port_value: 8080
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        service = config.services[0]
        lb = service.upstream.load_balancer

        assert lb is not None
        assert lb.algorithm == expected_algorithm


class TestEnvoyImportMultiService:
    """Tests for importing multiple services."""

    def test_import_multiple_clusters(self):
        """Test importing multiple Envoy clusters as separate services."""
        envoy_yaml = """
static_resources:
  clusters:
  - name: api_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api.internal
                port_value: 8080
  - name: auth_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    load_assignment:
      cluster_name: auth_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: auth.internal
                port_value: 9000
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        assert len(config.services) == 2

        api_service = config.services[0]
        assert api_service.name == "api"
        assert api_service.upstream.targets[0].host == "api.internal"

        auth_service = config.services[1]
        assert auth_service.name == "auth"
        assert auth_service.upstream.targets[0].host == "auth.internal"


class TestEnvoyImportErrors:
    """Tests for error handling during import."""

    def test_import_invalid_yaml(self):
        """Test that invalid YAML raises ValueError."""
        invalid_yaml = """
        this: is
        not: [valid
        yaml: structure
        }
        """
        provider = EnvoyProvider()

        with pytest.raises(ValueError, match="Invalid Envoy YAML"):
            provider.parse(invalid_yaml)

    def test_import_empty_config(self):
        """Test importing empty config returns empty services list."""
        envoy_yaml = """
static_resources:
  clusters: []
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        assert len(config.services) == 0

    def test_import_cluster_without_endpoints(self):
        """Test that cluster without endpoints is skipped with warning."""
        envoy_yaml = """
static_resources:
  clusters:
  - name: api_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    load_assignment:
      cluster_name: api_cluster
      endpoints: []
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        # Cluster should be skipped due to no valid endpoints
        assert len(config.services) == 0
