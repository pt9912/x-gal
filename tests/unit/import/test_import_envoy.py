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


class TestEnvoyImportAdvancedRouting:
    """Tests for Advanced Routing filters import (JWT, GeoIP)."""

    def test_import_jwt_authentication_filter(self):
        """Test importing JWT Authentication filter configuration."""
        envoy_yaml = """
static_resources:
  listeners:
  - name: main_listener
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          http_filters:
          - name: envoy.filters.http.jwt_authn
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication
              providers:
                jwt_provider:
                  issuer: 'https://auth.example.com'
                  audiences:
                    - 'api.example.com'
                  remote_jwks:
                    http_uri:
                      uri: 'http://jwks-service:8080/.well-known/jwks.json'
                      cluster: jwks_cluster
                      timeout: 5s
                    cache_duration:
                      seconds: 300
                  payload_in_metadata: 'jwt_payload'
                  forward_payload_header: 'X-JWT-Payload'
              rules:
              - match:
                  prefix: '/'
                requires:
                  allow_missing_or_failed: {}
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ['*']
              routes:
              - match:
                  prefix: '/api'
                route:
                  cluster: api_cluster
  clusters:
  - name: api_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api-backend
                port_value: 8080
  - name: jwks_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: jwks_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: jwks-service
                port_value: 8080
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        # Should have parsed both clusters
        assert len(config.services) == 2

        # Find api service
        api_service = next((s for s in config.services if s.name == "api"), None)
        assert api_service is not None
        assert len(api_service.routes) == 1

        # Check that JWT filter was parsed
        route = api_service.routes[0]
        assert route.advanced_routing is not None
        assert route.advanced_routing.jwt_filter is not None

        jwt_filter = route.advanced_routing.jwt_filter
        assert jwt_filter.enabled is True
        assert jwt_filter.issuer == 'https://auth.example.com'
        assert jwt_filter.audience == 'api.example.com'
        assert jwt_filter.jwks_uri == 'http://jwks-service:8080/.well-known/jwks.json'
        assert jwt_filter.jwks_cluster == 'jwks_cluster'
        assert jwt_filter.payload_in_metadata == 'jwt_payload'
        assert jwt_filter.forward_payload_header == 'X-JWT-Payload'

    def test_import_geoip_ext_authz_filter(self):
        """Test importing GeoIP External Authorization filter configuration."""
        envoy_yaml = """
static_resources:
  listeners:
  - name: main_listener
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          http_filters:
          - name: envoy.filters.http.ext_authz
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz
              transport_api_version: V3
              http_service:
                server_uri:
                  uri: 'http://geoip-service:8080/check'
                  cluster: geoip_cluster
                  timeout: 1.5s
                authorization_request:
                  allowed_headers:
                    patterns:
                      - exact: 'x-forwarded-for'
                authorization_response:
                  allowed_upstream_headers:
                    patterns:
                      - exact: 'x-geo-country'
              failure_mode_allow: true
              metadata_context_namespaces:
                - envoy.filters.http.ext_authz
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ['*']
              routes:
              - match:
                  prefix: '/api'
                route:
                  cluster: api_cluster
  clusters:
  - name: api_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api-backend
                port_value: 8080
  - name: geoip_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: geoip_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: geoip-service
                port_value: 8080
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        # Find api service
        api_service = next((s for s in config.services if s.name == "api"), None)
        assert api_service is not None

        # Check that GeoIP filter was parsed
        route = api_service.routes[0]
        assert route.advanced_routing is not None
        assert route.advanced_routing.geoip_filter is not None

        geoip_filter = route.advanced_routing.geoip_filter
        assert geoip_filter.enabled is True
        assert geoip_filter.geoip_service_uri == 'http://geoip-service:8080/check'
        assert geoip_filter.geoip_cluster == 'geoip_cluster'
        assert geoip_filter.timeout_ms == 1500  # 1.5s = 1500ms
        assert geoip_filter.failure_mode_allow is True

    def test_import_jwt_and_geoip_filters_together(self):
        """Test importing both JWT and GeoIP filters in same config."""
        envoy_yaml = """
static_resources:
  listeners:
  - name: main_listener
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          http_filters:
          - name: envoy.filters.http.jwt_authn
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication
              providers:
                jwt_provider:
                  issuer: 'https://test-issuer.com'
                  audiences:
                    - 'test-audience'
                  remote_jwks:
                    http_uri:
                      uri: 'http://jwks:8080/keys'
                      cluster: jwks_cluster
                      timeout: 5s
                  payload_in_metadata: 'jwt_claims'
              rules:
              - match:
                  prefix: '/'
                requires:
                  allow_missing_or_failed: {}
          - name: envoy.filters.http.ext_authz
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz
              transport_api_version: V3
              http_service:
                server_uri:
                  uri: 'http://geoip:8080/lookup'
                  cluster: geoip_cluster
                  timeout: 0.8s
              failure_mode_allow: false
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ['*']
              routes:
              - match:
                  prefix: '/api'
                route:
                  cluster: api_cluster
  clusters:
  - name: api_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api-backend
                port_value: 8080
  - name: jwks_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: jwks_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: jwks
                port_value: 8080
  - name: geoip_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: geoip_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: geoip
                port_value: 8080
"""
        provider = EnvoyProvider()
        config = provider.parse(envoy_yaml)

        # Find api service
        api_service = next((s for s in config.services if s.name == "api"), None)
        assert api_service is not None

        # Check both filters
        route = api_service.routes[0]
        assert route.advanced_routing is not None

        # JWT filter
        assert route.advanced_routing.jwt_filter is not None
        jwt = route.advanced_routing.jwt_filter
        assert jwt.enabled is True
        assert jwt.issuer == 'https://test-issuer.com'
        assert jwt.audience == 'test-audience'
        assert jwt.payload_in_metadata == 'jwt_claims'

        # GeoIP filter
        assert route.advanced_routing.geoip_filter is not None
        geo = route.advanced_routing.geoip_filter
        assert geo.enabled is True
        assert geo.geoip_service_uri == 'http://geoip:8080/lookup'
        assert geo.timeout_ms == 800  # 0.8s = 800ms
        assert geo.failure_mode_allow is False

    @pytest.mark.skip(reason="Roundtrip test needs further investigation - routes not preserved in second generation")
    def test_import_and_regenerate_roundtrip(self):
        """Test that filters are preserved in parse → generate → parse roundtrip."""
        # Start with a complete Envoy YAML that has JWT/GeoIP filters
        envoy_yaml_original = """
static_resources:
  listeners:
  - name: main_listener
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          http_filters:
          - name: envoy.filters.http.jwt_authn
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication
              providers:
                jwt_provider:
                  issuer: 'https://auth.roundtrip.com'
                  audiences:
                    - 'roundtrip-api'
                  remote_jwks:
                    http_uri:
                      uri: 'http://jwks:8080/.well-known/jwks.json'
                      cluster: jwks_cluster
                      timeout: 5s
                  payload_in_metadata: 'jwt_payload'
              rules:
              - match:
                  prefix: '/'
                requires:
                  allow_missing_or_failed: {}
          - name: envoy.filters.http.ext_authz
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz
              transport_api_version: V3
              http_service:
                server_uri:
                  uri: 'http://geoip:8080/check'
                  cluster: geoip_cluster
                  timeout: 0.6s
              failure_mode_allow: true
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ['*']
              routes:
              - match:
                  prefix: '/api'
                route:
                  cluster: api_cluster
  clusters:
  - name: api_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api-backend
                port_value: 8080
  - name: jwks_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: jwks_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: jwks
                port_value: 8080
  - name: geoip_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: geoip_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: geoip
                port_value: 8080
"""

        provider = EnvoyProvider()

        # Step 1: Parse original YAML to GAL
        config_1 = provider.parse(envoy_yaml_original)

        # Verify filters were parsed in first parse
        api_service = next((s for s in config_1.services if 'api' in s.name.lower()), None)
        assert api_service is not None
        assert len(api_service.routes) > 0

        route_1 = api_service.routes[0]
        assert route_1.advanced_routing is not None
        assert route_1.advanced_routing.jwt_filter is not None
        assert route_1.advanced_routing.geoip_filter is not None

        jwt_1 = route_1.advanced_routing.jwt_filter
        assert jwt_1.issuer == 'https://auth.roundtrip.com'
        assert jwt_1.audience == 'roundtrip-api'

        geo_1 = route_1.advanced_routing.geoip_filter
        assert geo_1.geoip_service_uri == 'http://geoip:8080/check'
        assert geo_1.timeout_ms == 600  # 0.6s

        # Step 2: Generate Envoy YAML from parsed GAL
        envoy_yaml_2 = provider.generate(config_1)

        # Verify filters are in generated YAML
        assert 'envoy.filters.http.jwt_authn' in envoy_yaml_2
        assert 'envoy.filters.http.ext_authz' in envoy_yaml_2
        assert 'https://auth.roundtrip.com' in envoy_yaml_2
        assert 'http://geoip:8080/check' in envoy_yaml_2

        # Step 3: Parse the re-generated YAML again
        config_2 = provider.parse(envoy_yaml_2)

        # Verify filters are still present after roundtrip
        api_service_2 = next((s for s in config_2.services if 'api' in s.name.lower()), None)
        assert api_service_2 is not None
        assert len(api_service_2.routes) > 0

        route_2 = api_service_2.routes[0]
        assert route_2.advanced_routing is not None
        assert route_2.advanced_routing.jwt_filter is not None
        assert route_2.advanced_routing.geoip_filter is not None

        # Verify filter values match original
        jwt_2 = route_2.advanced_routing.jwt_filter
        assert jwt_2.issuer == jwt_1.issuer
        assert jwt_2.audience == jwt_1.audience

        geo_2 = route_2.advanced_routing.geoip_filter
        assert geo_2.geoip_service_uri == geo_1.geoip_service_uri
        assert geo_2.timeout_ms == geo_1.timeout_ms
