"""
Tests for APISIX Config Import (v1.3.0 Feature 3)
"""

import pytest

from gal.providers.apisix import APISIXProvider


class TestAPISIXImportBasic:
    """Test basic APISIX config import."""

    def test_import_simple_service(self):
        """Test importing a simple APISIX service."""
        provider = APISIXProvider()

        apisix_config = """
routes:
  - id: 1
    uri: /api
    service_id: api_service

services:
  - id: api_service
    name: api_service
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api.internal:8080": 1
"""

        config = provider.parse(apisix_config)

        assert len(config.services) == 1
        assert config.services[0].name == "api_service"
        assert len(config.services[0].upstream.targets) == 1
        assert config.services[0].upstream.targets[0].host == "api.internal"
        assert config.services[0].upstream.targets[0].port == 8080

    def test_import_service_with_route(self):
        """Test importing service with route."""
        provider = APISIXProvider()

        apisix_config = """
routes:
  - id: 1
    uri: /api/v1
    methods:
      - GET
      - POST
    service_id: api_service

services:
  - id: api_service
    name: api_service
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api:8080": 1
"""

        config = provider.parse(apisix_config)

        assert len(config.services) == 1
        assert len(config.services[0].routes) == 1
        route = config.services[0].routes[0]
        assert route.path_prefix == "/api/v1"
        assert route.methods == ["GET", "POST"]

    def test_import_json_format(self):
        """Test importing APISIX JSON config."""
        provider = APISIXProvider()

        apisix_config = """
{
    "services": [
        {
            "id": "json_service",
            "name": "json_service",
            "upstream_id": "json_upstream"
        }
    ],
    "upstreams": [
        {
            "id": "json_upstream",
            "nodes": {
                "backend:9000": 1
            }
        }
    ],
    "routes": []
}
"""

        config = provider.parse(apisix_config)

        assert len(config.services) == 1
        assert config.services[0].name == "json_service"


class TestAPISIXImportUpstream:
    """Test upstream and targets import."""

    def test_import_upstream_with_targets(self):
        """Test upstream and targets import."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: lb_service
    name: lb_service
    upstream_id: lb_upstream

upstreams:
  - id: lb_upstream
    type: roundrobin
    nodes:
      "server1:8080": 2
      "server2:8080": 1

routes: []
"""

        config = provider.parse(apisix_config)

        assert config.services[0].upstream.load_balancer.algorithm == "round_robin"
        assert len(config.services[0].upstream.targets) == 2
        assert config.services[0].upstream.targets[0].weight == 2
        assert config.services[0].upstream.targets[1].weight == 1

    def test_import_load_balancing_algorithms(self):
        """Test different load balancing algorithms."""
        test_cases = [
            ("roundrobin", "round_robin"),
            ("chash", "ip_hash"),
            ("ewma", "least_conn"),
            ("least_conn", "least_conn"),
        ]

        for apisix_alg, gal_alg in test_cases:
            provider = APISIXProvider()

            apisix_config = f"""
services:
  - id: test
    name: test
    upstream_id: upstream

upstreams:
  - id: upstream
    type: {apisix_alg}
    nodes:
      "server:8080": 1

routes: []
"""

            config = provider.parse(apisix_config)
            assert config.services[0].upstream.load_balancer.algorithm == gal_alg


class TestAPISIXImportHealthChecks:
    """Test health check import."""

    def test_import_active_health_check(self):
        """Test active health check import."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: hc_service
    name: hc_service
    upstream_id: hc_upstream

upstreams:
  - id: hc_upstream
    nodes:
      "server:8080": 1
    checks:
      active:
        http_path: /health
        timeout: 5
        interval: 10
        healthy:
          successes: 2
          http_statuses: [200]
        unhealthy:
          http_failures: 3

routes: []
"""

        config = provider.parse(apisix_config)

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
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: passive_service
    name: passive_service
    upstream_id: passive_upstream

upstreams:
  - id: passive_upstream
    nodes:
      "server:8080": 1
    checks:
      passive:
        healthy:
          successes: 2
        unhealthy:
          http_failures: 5

routes: []
"""

        config = provider.parse(apisix_config)

        hc = config.services[0].upstream.health_check
        assert hc is not None
        assert hc.passive.enabled is True
        assert hc.passive.max_failures == 5

    def test_import_combined_health_checks(self):
        """Test combined active + passive health checks."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: combined_service
    name: combined_service
    upstream_id: combined_upstream

upstreams:
  - id: combined_upstream
    nodes:
      "server:8080": 1
    checks:
      active:
        http_path: /status
        interval: 5
        healthy:
          successes: 1
        unhealthy:
          http_failures: 2
      passive:
        healthy:
          successes: 3
        unhealthy:
          http_failures: 4

routes: []
"""

        config = provider.parse(apisix_config)

        hc = config.services[0].upstream.health_check
        assert hc.active.enabled is True
        assert hc.passive.enabled is True
        assert hc.active.http_path == "/status"
        assert hc.passive.max_failures == 4


class TestAPISIXImportRateLimiting:
    """Test rate limiting plugin import."""

    def test_import_limit_req_plugin(self):
        """Test limit-req plugin (leaky bucket)."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: api
    name: api
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api:8080": 1

routes:
  - id: api_route
    uri: /api
    service_id: api
    plugins:
      limit-req:
        rate: 100
        burst: 200
        key: remote_addr
"""

        config = provider.parse(apisix_config)

        route = config.services[0].routes[0]
        assert route.rate_limit.enabled is True
        assert route.rate_limit.requests_per_second == 100
        assert route.rate_limit.burst == 200

    def test_import_limit_count_plugin(self):
        """Test limit-count plugin (fixed window)."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: api
    name: api
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api:8080": 1

routes:
  - id: api_route
    uri: /api
    service_id: api
    plugins:
      limit-count:
        count: 600
        time_window: 60
"""

        config = provider.parse(apisix_config)

        route = config.services[0].routes[0]
        assert route.rate_limit.enabled is True
        assert route.rate_limit.requests_per_second == 10  # 600 / 60


class TestAPISIXImportAuthentication:
    """Test authentication plugin import."""

    def test_import_key_auth(self):
        """Test key-auth plugin import."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: api
    name: api
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api:8080": 1

routes:
  - id: api_route
    uri: /api
    service_id: api
    plugins:
      key-auth:
        header: X-API-Key
"""

        config = provider.parse(apisix_config)

        route = config.services[0].routes[0]
        assert route.authentication.enabled is True
        assert route.authentication.type == "api_key"
        assert route.authentication.api_key.key_name == "X-API-Key"
        # Check warnings
        warnings = provider.get_import_warnings()
        assert any("API keys" in w for w in warnings)

    def test_import_basic_auth(self):
        """Test basic-auth plugin import."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: api
    name: api
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api:8080": 1

routes:
  - id: api_route
    uri: /api
    service_id: api
    plugins:
      basic-auth: {}
"""

        config = provider.parse(apisix_config)

        route = config.services[0].routes[0]
        assert route.authentication.enabled is True
        assert route.authentication.type == "basic"
        # Check warnings
        warnings = provider.get_import_warnings()
        assert any("Basic auth users" in w for w in warnings)

    def test_import_jwt_auth(self):
        """Test JWT plugin import."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: api
    name: api
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api:8080": 1

routes:
  - id: api_route
    uri: /api
    service_id: api
    plugins:
      jwt-auth: {}
"""

        config = provider.parse(apisix_config)

        route = config.services[0].routes[0]
        assert route.authentication.enabled is True
        assert route.authentication.type == "jwt"
        assert "HS256" in route.authentication.jwt.algorithms
        # Check warnings
        warnings = provider.get_import_warnings()
        assert any("JWT secret" in w for w in warnings)


class TestAPISIXImportHeaders:
    """Test header transformation plugin import."""

    def test_import_proxy_rewrite_plugin(self):
        """Test proxy-rewrite plugin import."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: api
    name: api
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api:8080": 1

routes:
  - id: api_route
    uri: /api
    service_id: api
    plugins:
      proxy-rewrite:
        headers:
          X-Request-ID: "12345"
          X-Gateway: "APISIX"
          X-Internal-Header: ""
"""

        config = provider.parse(apisix_config)

        route = config.services[0].routes[0]
        assert route.headers is not None
        assert route.headers.request_add == {"X-Request-ID": "12345", "X-Gateway": "APISIX"}
        assert route.headers.request_remove == ["X-Internal-Header"]

    def test_import_response_rewrite_plugin(self):
        """Test response-rewrite plugin import."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: api
    name: api
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api:8080": 1

routes:
  - id: api_route
    uri: /api
    service_id: api
    plugins:
      response-rewrite:
        headers:
          X-Response-Time: "100ms"
          Server: ""
"""

        config = provider.parse(apisix_config)

        route = config.services[0].routes[0]
        assert route.headers is not None
        assert route.headers.response_add == {"X-Response-Time": "100ms"}
        assert route.headers.response_remove == ["Server"]


class TestAPISIXImportCORS:
    """Test CORS plugin import."""

    def test_import_cors_basic(self):
        """Test basic CORS plugin import."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: api
    name: api
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api:8080": 1

routes:
  - id: api_route
    uri: /api
    service_id: api
    plugins:
      cors:
        allow_origins: https://app.example.com
        allow_methods: GET,POST,PUT,DELETE
        allow_credential: true
        max_age: 3600
"""

        config = provider.parse(apisix_config)

        route = config.services[0].routes[0]
        assert route.cors.enabled is True
        assert route.cors.allowed_origins == ["https://app.example.com"]
        assert route.cors.allowed_methods == ["GET", "POST", "PUT", "DELETE"]
        assert route.cors.allow_credentials is True
        assert route.cors.max_age == "3600"


class TestAPISIXImportMultiService:
    """Test multi-service import."""

    def test_import_multiple_services(self):
        """Test importing multiple services."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: user_service
    name: user_service
    upstream_id: user_upstream
  - id: order_service
    name: order_service
    upstream_id: order_upstream
  - id: payment_service
    name: payment_service
    upstream_id: payment_upstream

upstreams:
  - id: user_upstream
    nodes:
      "user:8080": 1
  - id: order_upstream
    nodes:
      "order:8080": 1
  - id: payment_upstream
    nodes:
      "payment:8080": 1

routes:
  - id: user_route
    uri: /users
    service_id: user_service
  - id: order_route
    uri: /orders
    service_id: order_service
  - id: payment_route
    uri: /payments
    service_id: payment_service
"""

        config = provider.parse(apisix_config)

        assert len(config.services) == 3
        assert config.services[0].name == "user_service"
        assert config.services[1].name == "order_service"
        assert config.services[2].name == "payment_service"

        assert len(config.services[0].routes) == 1
        assert len(config.services[1].routes) == 1
        assert len(config.services[2].routes) == 1


class TestAPISIXImportErrors:
    """Test error handling."""

    def test_import_invalid_yaml(self):
        """Test importing invalid YAML."""
        provider = APISIXProvider()

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
        provider = APISIXProvider()

        apisix_config = """
services: []
upstreams: []
routes: []
"""

        config = provider.parse(apisix_config)
        assert len(config.services) == 0

    def test_import_service_without_name(self):
        """Test importing service without name (should use ID)."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: service_123
    upstream_id: upstream_123

upstreams:
  - id: upstream_123
    nodes:
      "backend:8080": 1

routes: []
"""

        config = provider.parse(apisix_config)
        assert len(config.services) == 1
        assert config.services[0].name == "service_123"


class TestAPISIXImportCombined:
    """Test combined features."""

    def test_import_production_config(self):
        """Test importing a production-like config with all features."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: api_service
    name: api_service
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    type: roundrobin
    nodes:
      "api-1:8080": 100
      "api-2:8080": 100
    checks:
      active:
        http_path: /health
        interval: 10
        healthy:
          successes: 2
        unhealthy:
          http_failures: 3

routes:
  - id: api_route
    uri: /api/v1
    methods:
      - GET
      - POST
    service_id: api_service
    plugins:
      limit-req:
        rate: 100
        burst: 200
      key-auth:
        header: apikey
      cors:
        allow_origins: https://app.example.com
        allow_credential: true
"""

        config = provider.parse(apisix_config)

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


class TestAPISIXImportCircuitBreaker:
    """Test circuit breaker warning."""

    def test_circuit_breaker_warning(self):
        """Test that circuit breaker generates warning."""
        provider = APISIXProvider()

        apisix_config = """
services:
  - id: api
    name: api
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    nodes:
      "api:8080": 1

routes:
  - id: api_route
    uri: /api
    service_id: api
    plugins:
      api-breaker:
        break_response_code: 502
        max_breaker_sec: 300
"""

        config = provider.parse(apisix_config)

        # Check warnings
        warnings = provider.get_import_warnings()
        assert any("Circuit breaker" in w for w in warnings)
