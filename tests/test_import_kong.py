"""
Tests for Kong Config Import (v1.3.0 Feature 2)
"""

import pytest

from gal.providers.kong import KongProvider


class TestKongImportBasic:
    """Test basic Kong config import."""

    def test_import_simple_service(self):
        """Test importing a simple Kong service."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: test_service
    url: http://test-backend:8080
"""

        config = provider.parse(kong_config)

        assert len(config.services) == 1
        assert config.services[0].name == "test_service"
        assert len(config.services[0].upstream.targets) == 1
        assert config.services[0].upstream.targets[0].host == "test-backend"
        assert config.services[0].upstream.targets[0].port == 8080

    def test_import_service_with_route(self):
        """Test importing service with route."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: api_service
    url: http://api:8080
routes:
  - name: api_route
    service: api_service
    paths:
      - /api/v1
    methods:
      - GET
      - POST
"""

        config = provider.parse(kong_config)

        assert len(config.services) == 1
        assert len(config.services[0].routes) == 1
        route = config.services[0].routes[0]
        assert route.path_prefix == "/api/v1"
        assert route.methods == ["GET", "POST"]

    def test_import_json_format(self):
        """Test importing Kong JSON config."""
        provider = KongProvider()

        kong_config = """
{
    "_format_version": "3.0",
    "services": [
        {
            "name": "json_service",
            "url": "http://backend:9000"
        }
    ]
}
"""

        config = provider.parse(kong_config)

        assert len(config.services) == 1
        assert config.services[0].name == "json_service"


class TestKongImportUpstream:
    """Test upstream and targets import."""

    def test_import_upstream_with_targets(self):
        """Test upstream and targets import."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: lb_service
    url: http://lb_upstream
upstreams:
  - name: lb_upstream
    algorithm: least-connections
targets:
  - upstream: lb_upstream
    target: server1:8080
    weight: 2
  - upstream: lb_upstream
    target: server2:8080
    weight: 1
"""

        config = provider.parse(kong_config)

        assert config.services[0].upstream.load_balancer.algorithm == "least_conn"
        assert len(config.services[0].upstream.targets) == 2
        assert config.services[0].upstream.targets[0].weight == 2
        assert config.services[0].upstream.targets[1].weight == 1

    def test_import_load_balancing_algorithms(self):
        """Test different load balancing algorithms."""
        test_cases = [
            ("round-robin", "round_robin"),
            ("least-connections", "least_conn"),
            ("consistent-hashing", "ip_hash"),
            ("latency", "least_conn"),
        ]

        for kong_alg, gal_alg in test_cases:
            provider = KongProvider()

            kong_config = f"""
_format_version: "3.0"
services:
  - name: test
    url: http://upstream
upstreams:
  - name: upstream
    algorithm: {kong_alg}
targets:
  - upstream: upstream
    target: server:8080
"""

            config = provider.parse(kong_config)
            assert config.services[0].upstream.load_balancer.algorithm == gal_alg


class TestKongImportHealthChecks:
    """Test health check import."""

    def test_import_active_health_check(self):
        """Test active health check import."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: hc_service
    url: http://hc_upstream
upstreams:
  - name: hc_upstream
    healthchecks:
      active:
        http_path: /health
        timeout: 5
        healthy:
          interval: 10
          successes: 2
        unhealthy:
          interval: 10
          http_failures: 3
targets:
  - upstream: hc_upstream
    target: server:8080
"""

        config = provider.parse(kong_config)

        hc = config.services[0].upstream.health_check
        assert hc is not None
        assert hc.active.enabled is True
        assert hc.active.http_path == "/health"
        assert hc.active.interval == "10s"
        assert hc.active.timeout == "5s"
        assert hc.active.healthy_threshold == 2
        assert hc.active.unhealthy_threshold == 3

    def test_import_passive_health_check(self):
        """Test passive health check import."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: passive_service
    url: http://passive_upstream
upstreams:
  - name: passive_upstream
    healthchecks:
      passive:
        healthy:
          successes: 2
        unhealthy:
          http_failures: 5
targets:
  - upstream: passive_upstream
    target: server:8080
"""

        config = provider.parse(kong_config)

        hc = config.services[0].upstream.health_check
        assert hc is not None
        assert hc.passive.enabled is True
        assert hc.passive.max_failures == 5

    def test_import_combined_health_checks(self):
        """Test combined active + passive health checks."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: combined_service
    url: http://combined_upstream
upstreams:
  - name: combined_upstream
    healthchecks:
      active:
        http_path: /status
        healthy:
          interval: 5
          successes: 1
        unhealthy:
          http_failures: 2
      passive:
        healthy:
          successes: 3
        unhealthy:
          http_failures: 4
targets:
  - upstream: combined_upstream
    target: server:8080
"""

        config = provider.parse(kong_config)

        hc = config.services[0].upstream.health_check
        assert hc.active.enabled is True
        assert hc.passive.enabled is True
        assert hc.active.http_path == "/status"
        assert hc.passive.max_failures == 4


class TestKongImportRateLimiting:
    """Test rate limiting plugin import."""

    def test_import_rate_limiting_second(self):
        """Test rate-limiting with second config."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: api
    url: http://api:8080
routes:
  - name: api_route
    service: api
    paths:
      - /api
plugins:
  - name: rate-limiting
    route: api_route
    config:
      second: 10
"""

        config = provider.parse(kong_config)

        route = config.services[0].routes[0]
        assert route.rate_limit.enabled is True
        assert route.rate_limit.requests_per_second == 10

    def test_import_rate_limiting_minute(self):
        """Test rate-limiting with minute config."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: api
    url: http://api:8080
routes:
  - name: api_route
    service: api
    paths:
      - /api
plugins:
  - name: rate-limiting
    route: api_route
    config:
      minute: 600
      limit_by: ip
"""

        config = provider.parse(kong_config)

        route = config.services[0].routes[0]
        assert route.rate_limit.enabled is True
        assert route.rate_limit.requests_per_second == 10  # 600 / 60
        assert route.rate_limit.key_type == "ip_address"


class TestKongImportAuthentication:
    """Test authentication plugin import."""

    def test_import_key_auth(self):
        """Test key-auth plugin import."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: api
    url: http://api:8080
routes:
  - name: api_route
    service: api
    paths:
      - /api
plugins:
  - name: key-auth
    route: api_route
    config:
      key_names:
        - X-API-Key
"""

        config = provider.parse(kong_config)

        route = config.services[0].routes[0]
        assert route.authentication.enabled is True
        assert route.authentication.type == "api_key"
        assert route.authentication.api_key.key_name == "X-API-Key"

    def test_import_basic_auth(self):
        """Test basic-auth plugin import."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: api
    url: http://api:8080
routes:
  - name: api_route
    service: api
    paths:
      - /api
plugins:
  - name: basic-auth
    route: api_route
"""

        config = provider.parse(kong_config)

        route = config.services[0].routes[0]
        assert route.authentication.enabled is True
        assert route.authentication.type == "basic"
        # Check warnings
        warnings = provider.get_import_warnings()
        assert any("Basic auth users" in w for w in warnings)

    def test_import_jwt_auth(self):
        """Test JWT plugin import."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: api
    url: http://api:8080
routes:
  - name: api_route
    service: api
    paths:
      - /api
plugins:
  - name: jwt
    route: api_route
    config:
      algorithm: RS256
      header_names:
        - Authorization
"""

        config = provider.parse(kong_config)

        route = config.services[0].routes[0]
        assert route.authentication.enabled is True
        assert route.authentication.type == "jwt"
        assert "RS256" in route.authentication.jwt.algorithms
        # Check warnings
        warnings = provider.get_import_warnings()
        assert any("JWT keys/secrets" in w for w in warnings)


class TestKongImportHeaders:
    """Test header transformation plugin import."""

    def test_import_request_transformer(self):
        """Test request-transformer plugin import."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: api
    url: http://api:8080
routes:
  - name: api_route
    service: api
    paths:
      - /api
plugins:
  - name: request-transformer
    route: api_route
    config:
      add:
        headers:
          - "X-Request-ID:12345"
          - "X-Gateway:Kong"
      remove:
        headers:
          - "X-Internal-Header"
"""

        config = provider.parse(kong_config)

        route = config.services[0].routes[0]
        assert route.headers is not None
        assert route.headers.request_add == {"X-Request-ID": "12345", "X-Gateway": "Kong"}
        assert route.headers.request_remove == ["X-Internal-Header"]

    def test_import_response_transformer(self):
        """Test response-transformer plugin import."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: api
    url: http://api:8080
routes:
  - name: api_route
    service: api
    paths:
      - /api
plugins:
  - name: response-transformer
    route: api_route
    config:
      add:
        headers:
          - "X-Response-Time:100ms"
      remove:
        headers:
          - "Server"
"""

        config = provider.parse(kong_config)

        route = config.services[0].routes[0]
        assert route.headers is not None
        assert route.headers.response_add == {"X-Response-Time": "100ms"}
        assert route.headers.response_remove == ["Server"]


class TestKongImportCORS:
    """Test CORS plugin import."""

    def test_import_cors_basic(self):
        """Test basic CORS plugin import."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: api
    url: http://api:8080
routes:
  - name: api_route
    service: api
    paths:
      - /api
plugins:
  - name: cors
    route: api_route
    config:
      origins:
        - https://app.example.com
      methods:
        - GET
        - POST
      credentials: true
      max_age: 3600
"""

        config = provider.parse(kong_config)

        route = config.services[0].routes[0]
        assert route.cors.enabled is True
        assert route.cors.allowed_origins == ["https://app.example.com"]
        assert route.cors.allowed_methods == ["GET", "POST"]
        assert route.cors.allow_credentials is True
        assert route.cors.max_age == "3600"


class TestKongImportMultiService:
    """Test multi-service import."""

    def test_import_multiple_services(self):
        """Test importing multiple services."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: user_service
    url: http://user:8080
  - name: order_service
    url: http://order:8080
  - name: payment_service
    url: http://payment:8080
routes:
  - name: user_route
    service: user_service
    paths:
      - /users
  - name: order_route
    service: order_service
    paths:
      - /orders
  - name: payment_route
    service: payment_service
    paths:
      - /payments
"""

        config = provider.parse(kong_config)

        assert len(config.services) == 3
        assert config.services[0].name == "user_service"
        assert config.services[1].name == "order_service"
        assert config.services[2].name == "payment_service"

        assert len(config.services[0].routes) == 1
        assert len(config.services[1].routes) == 1
        assert len(config.services[2].routes) == 1


class TestKongImportErrors:
    """Test error handling."""

    def test_import_invalid_yaml(self):
        """Test importing invalid YAML."""
        provider = KongProvider()

        invalid_yaml = """
this: is
not: [valid
yaml: structure
}
"""

        with pytest.raises(ValueError, match="Invalid YAML/JSON"):
            provider.parse(invalid_yaml)

    def test_import_empty_config(self):
        """Test importing empty config."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
"""

        config = provider.parse(kong_config)
        assert len(config.services) == 0

    def test_import_service_without_name(self):
        """Test importing service without name (should be skipped)."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - url: http://backend:8080
"""

        config = provider.parse(kong_config)
        assert len(config.services) == 0


class TestKongImportCombined:
    """Test combined features."""

    def test_import_production_config(self):
        """Test importing a production-like config with all features."""
        provider = KongProvider()

        kong_config = """
_format_version: "3.0"
services:
  - name: api_service
    url: http://api_upstream
upstreams:
  - name: api_upstream
    algorithm: round-robin
    healthchecks:
      active:
        http_path: /health
        healthy:
          interval: 10
          successes: 2
        unhealthy:
          http_failures: 3
targets:
  - upstream: api_upstream
    target: api-1:8080
    weight: 100
  - upstream: api_upstream
    target: api-2:8080
    weight: 100
routes:
  - name: api_route
    service: api_service
    paths:
      - /api/v1
    methods:
      - GET
      - POST
plugins:
  - name: rate-limiting
    route: api_route
    config:
      second: 100
      limit_by: ip
  - name: key-auth
    route: api_route
    config:
      key_names:
        - apikey
  - name: cors
    route: api_route
    config:
      origins:
        - https://app.example.com
      credentials: true
"""

        config = provider.parse(kong_config)

        # Service and upstream
        assert len(config.services) == 1
        service = config.services[0]
        assert service.name == "api_service"
        assert len(service.upstream.targets) == 2
        assert service.upstream.load_balancer.algorithm == "round_robin"

        # Health checks
        assert service.upstream.health_check.active.enabled is True
        assert service.upstream.health_check.active.http_path == "/health"

        # Route
        assert len(service.routes) == 1
        route = service.routes[0]
        assert route.path_prefix == "/api/v1"

        # Rate limiting
        assert route.rate_limit.enabled is True
        assert route.rate_limit.requests_per_second == 100

        # Authentication
        assert route.authentication.enabled is True
        assert route.authentication.type == "api_key"

        # CORS
        assert route.cors.enabled is True
        assert route.cors.allowed_origins == ["https://app.example.com"]
