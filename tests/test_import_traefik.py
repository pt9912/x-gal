"""
Tests for Traefik Config Import (v1.3.0 Feature 4)
"""

import pytest

from gal.providers.traefik import TraefikProvider


class TestTraefikImportBasic:
    """Test basic Traefik config import."""

    def test_import_simple_service(self):
        """Test importing a simple Traefik service."""
        provider = TraefikProvider()

        traefik_config = """
http:
  services:
    test-service:
      loadBalancer:
        servers:
          - url: http://test-backend:8080
"""

        config = provider.parse(traefik_config)

        assert len(config.services) == 1
        assert config.services[0].name == "test-service"
        assert len(config.services[0].upstream.targets) == 1
        assert config.services[0].upstream.targets[0].host == "test-backend"
        assert config.services[0].upstream.targets[0].port == 8080

    def test_import_service_with_router(self):
        """Test importing service with router."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    api-router:
      rule: PathPrefix(`/api/v1`)
      service: api-service

  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://api:8080
"""

        config = provider.parse(traefik_config)

        assert len(config.services) == 1
        assert len(config.services[0].routes) == 1
        route = config.services[0].routes[0]
        assert route.path_prefix == "/api/v1"

    def test_import_multiple_servers(self):
        """Test importing service with multiple backend servers."""
        provider = TraefikProvider()

        traefik_config = """
http:
  services:
    lb-service:
      loadBalancer:
        servers:
          - url: http://server1:8080
          - url: http://server2:8080
          - url: http://server3:9000
"""

        config = provider.parse(traefik_config)

        assert len(config.services[0].upstream.targets) == 3
        assert config.services[0].upstream.targets[0].host == "server1"
        assert config.services[0].upstream.targets[1].host == "server2"
        assert config.services[0].upstream.targets[2].port == 9000


class TestTraefikImportRouters:
    """Test router import."""

    def test_import_path_prefix_rule(self):
        """Test PathPrefix rule parsing."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    test-router:
      rule: PathPrefix(`/api`)
      service: test-service

  services:
    test-service:
      loadBalancer:
        servers:
          - url: http://backend:8080
"""

        config = provider.parse(traefik_config)

        assert config.services[0].routes[0].path_prefix == "/api"

    def test_import_exact_path_rule(self):
        """Test exact Path rule parsing."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    test-router:
      rule: Path(`/api/v1/users`)
      service: test-service

  services:
    test-service:
      loadBalancer:
        servers:
          - url: http://backend:8080
"""

        config = provider.parse(traefik_config)

        assert config.services[0].routes[0].path_prefix == "/api/v1/users"

    def test_import_complex_rule(self):
        """Test complex rule with Host and PathPrefix."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    test-router:
      rule: Host(`example.com`) && PathPrefix(`/api/v2`)
      service: test-service

  services:
    test-service:
      loadBalancer:
        servers:
          - url: http://backend:8080
"""

        config = provider.parse(traefik_config)

        assert config.services[0].routes[0].path_prefix == "/api/v2"


class TestTraefikImportHealthChecks:
    """Test health check import."""

    def test_import_health_check(self):
        """Test health check import."""
        provider = TraefikProvider()

        traefik_config = """
http:
  services:
    hc-service:
      loadBalancer:
        servers:
          - url: http://backend:8080
        healthCheck:
          path: /health
          interval: 10s
          timeout: 5s
"""

        config = provider.parse(traefik_config)

        hc = config.services[0].upstream.health_check
        assert hc is not None
        assert hc.passive.enabled is True

        # Check warnings
        warnings = provider.get_import_warnings()
        assert any("passive health checks" in w for w in warnings)


class TestTraefikImportStickySession:
    """Test sticky session import."""

    def test_import_sticky_session_with_cookie(self):
        """Test sticky session with cookie."""
        provider = TraefikProvider()

        traefik_config = """
http:
  services:
    sticky-service:
      loadBalancer:
        servers:
          - url: http://backend:8080
        sticky:
          cookie:
            name: my_sticky_cookie
"""

        config = provider.parse(traefik_config)

        lb = config.services[0].upstream.load_balancer
        assert lb.sticky_sessions is True
        assert lb.cookie_name == "my_sticky_cookie"

    def test_import_sticky_session_default_cookie(self):
        """Test sticky session with default cookie name."""
        provider = TraefikProvider()

        traefik_config = """
http:
  services:
    sticky-service:
      loadBalancer:
        servers:
          - url: http://backend:8080
        sticky:
          cookie: {}
"""

        config = provider.parse(traefik_config)

        lb = config.services[0].upstream.load_balancer
        assert lb.sticky_sessions is True
        assert lb.cookie_name == "lb"


class TestTraefikImportRateLimiting:
    """Test rate limiting middleware import."""

    def test_import_rate_limit_middleware(self):
        """Test rate-limit middleware import."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    api-router:
      rule: PathPrefix(`/api`)
      service: api-service
      middlewares:
        - rate-limit

  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://api:8080

  middlewares:
    rate-limit:
      rateLimit:
        average: 100
        burst: 200
"""

        config = provider.parse(traefik_config)

        route = config.services[0].routes[0]
        assert route.rate_limit.enabled is True
        assert route.rate_limit.requests_per_second == 100
        assert route.rate_limit.burst == 200
        assert route.rate_limit.key_type == "ip_address"


class TestTraefikImportAuthentication:
    """Test authentication middleware import."""

    def test_import_basic_auth_middleware(self):
        """Test basic auth middleware import."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    api-router:
      rule: PathPrefix(`/api`)
      service: api-service
      middlewares:
        - basic-auth

  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://api:8080

  middlewares:
    basic-auth:
      basicAuth:
        users:
          - "admin:$apr1$xyz..."
"""

        config = provider.parse(traefik_config)

        route = config.services[0].routes[0]
        assert route.authentication.enabled is True
        assert route.authentication.type == "basic"

        # Check warnings
        warnings = provider.get_import_warnings()
        assert any("Basic auth users are hashed" in w for w in warnings)


class TestTraefikImportHeaders:
    """Test header middleware import."""

    def test_import_request_headers(self):
        """Test request header middleware import."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    api-router:
      rule: PathPrefix(`/api`)
      service: api-service
      middlewares:
        - headers-middleware

  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://api:8080

  middlewares:
    headers-middleware:
      headers:
        customRequestHeaders:
          X-Request-ID: "12345"
          X-Gateway: "Traefik"
"""

        config = provider.parse(traefik_config)

        route = config.services[0].routes[0]
        assert route.headers is not None
        assert route.headers.request_add == {"X-Request-ID": "12345", "X-Gateway": "Traefik"}

    def test_import_response_headers(self):
        """Test response header middleware import."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    api-router:
      rule: PathPrefix(`/api`)
      service: api-service
      middlewares:
        - headers-middleware

  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://api:8080

  middlewares:
    headers-middleware:
      headers:
        customResponseHeaders:
          X-Frame-Options: "DENY"
          Server: "GAL-Gateway"
"""

        config = provider.parse(traefik_config)

        route = config.services[0].routes[0]
        assert route.headers is not None
        assert route.headers.response_add == {"X-Frame-Options": "DENY", "Server": "GAL-Gateway"}


class TestTraefikImportCORS:
    """Test CORS import via headers."""

    def test_import_cors_from_headers(self):
        """Test CORS extraction from response headers."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    api-router:
      rule: PathPrefix(`/api`)
      service: api-service
      middlewares:
        - cors-headers

  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://api:8080

  middlewares:
    cors-headers:
      headers:
        customResponseHeaders:
          Access-Control-Allow-Origin: "https://app.example.com"
          Access-Control-Allow-Methods: "GET,POST,PUT,DELETE"
          Access-Control-Allow-Headers: "Content-Type,Authorization"
          Access-Control-Allow-Credentials: "true"
          Access-Control-Max-Age: "3600"
"""

        config = provider.parse(traefik_config)

        route = config.services[0].routes[0]
        assert route.cors is not None
        assert route.cors.enabled is True
        assert route.cors.allowed_origins == ["https://app.example.com"]
        assert route.cors.allowed_methods == ["GET", "POST", "PUT", "DELETE"]
        assert route.cors.allowed_headers == ["Content-Type", "Authorization"]
        assert route.cors.allow_credentials is True
        assert route.cors.max_age == "3600"

        # CORS headers should be removed from response_add
        assert route.headers.response_add == {}

    def test_import_cors_wildcard_origin(self):
        """Test CORS with wildcard origin."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    api-router:
      rule: PathPrefix(`/api`)
      service: api-service
      middlewares:
        - cors-headers

  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://api:8080

  middlewares:
    cors-headers:
      headers:
        customResponseHeaders:
          Access-Control-Allow-Origin: "*"
          Access-Control-Allow-Methods: "GET,POST"
"""

        config = provider.parse(traefik_config)

        route = config.services[0].routes[0]
        assert route.cors.allowed_origins == ["*"]


class TestTraefikImportMultiService:
    """Test multi-service import."""

    def test_import_multiple_services(self):
        """Test importing multiple services."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    user-router:
      rule: PathPrefix(`/users`)
      service: user-service
    order-router:
      rule: PathPrefix(`/orders`)
      service: order-service
    payment-router:
      rule: PathPrefix(`/payments`)
      service: payment-service

  services:
    user-service:
      loadBalancer:
        servers:
          - url: http://user:8080
    order-service:
      loadBalancer:
        servers:
          - url: http://order:8080
    payment-service:
      loadBalancer:
        servers:
          - url: http://payment:8080
"""

        config = provider.parse(traefik_config)

        assert len(config.services) == 3
        assert config.services[0].name == "user-service"
        assert config.services[1].name == "order-service"
        assert config.services[2].name == "payment-service"

        assert len(config.services[0].routes) == 1
        assert len(config.services[1].routes) == 1
        assert len(config.services[2].routes) == 1


class TestTraefikImportMultipleMiddlewares:
    """Test multiple middlewares on a route."""

    def test_import_multiple_middlewares(self):
        """Test importing route with multiple middlewares."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    api-router:
      rule: PathPrefix(`/api`)
      service: api-service
      middlewares:
        - rate-limit
        - basic-auth
        - headers-middleware

  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://api:8080

  middlewares:
    rate-limit:
      rateLimit:
        average: 100
        burst: 200
    basic-auth:
      basicAuth:
        users:
          - "admin:$apr1$..."
    headers-middleware:
      headers:
        customRequestHeaders:
          X-Gateway: "Traefik"
"""

        config = provider.parse(traefik_config)

        route = config.services[0].routes[0]
        assert route.rate_limit is not None
        assert route.rate_limit.enabled is True
        assert route.authentication is not None
        assert route.authentication.enabled is True
        assert route.headers is not None
        assert route.headers.request_add == {"X-Gateway": "Traefik"}


class TestTraefikImportErrors:
    """Test error handling."""

    def test_import_invalid_yaml(self):
        """Test importing invalid YAML."""
        provider = TraefikProvider()

        invalid_yaml = """
this: is
not: [valid
yaml: structure
}
"""

        with pytest.raises(ValueError, match="Invalid YAML"):
            provider.parse(invalid_yaml)

    def test_import_empty_config(self):
        """Test importing empty config."""
        provider = TraefikProvider()

        traefik_config = ""

        with pytest.raises(ValueError, match="Empty configuration"):
            provider.parse(traefik_config)

    def test_import_no_services(self):
        """Test importing config with no services."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers: {}
  services: {}
"""

        config = provider.parse(traefik_config)
        assert len(config.services) == 0

    def test_import_service_without_load_balancer(self):
        """Test importing service without loadBalancer (should skip)."""
        provider = TraefikProvider()

        traefik_config = """
http:
  services:
    incomplete-service:
      weighted: {}
"""

        config = provider.parse(traefik_config)
        assert len(config.services) == 0

    def test_import_router_without_rule(self):
        """Test importing router without rule (should skip)."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    incomplete-router:
      service: test-service

  services:
    test-service:
      loadBalancer:
        servers:
          - url: http://backend:8080
"""

        config = provider.parse(traefik_config)

        # Service should exist but no routes
        assert len(config.services) == 1
        assert len(config.services[0].routes) == 0


class TestTraefikImportWarnings:
    """Test import warnings."""

    def test_path_manipulation_warning(self):
        """Test warning for path manipulation middleware."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    api-router:
      rule: PathPrefix(`/api`)
      service: api-service
      middlewares:
        - strip-prefix

  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://api:8080

  middlewares:
    strip-prefix:
      stripPrefix:
        prefixes:
          - /api
"""

        config = provider.parse(traefik_config)

        warnings = provider.get_import_warnings()
        assert any("Path manipulation" in w for w in warnings)


class TestTraefikImportCombined:
    """Test combined features."""

    def test_import_production_config(self):
        """Test importing a production-like config with all features."""
        provider = TraefikProvider()

        traefik_config = """
http:
  routers:
    api-router:
      rule: PathPrefix(`/api/v1`)
      service: api-service
      middlewares:
        - rate-limit
        - cors-headers

  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://api-1:8080
          - url: http://api-2:8080
        healthCheck:
          path: /health
          interval: 10s
          timeout: 5s
        sticky:
          cookie:
            name: lb

  middlewares:
    rate-limit:
      rateLimit:
        average: 100
        burst: 200
    cors-headers:
      headers:
        customResponseHeaders:
          Access-Control-Allow-Origin: "https://app.example.com"
          Access-Control-Allow-Methods: "GET,POST,PUT,DELETE"
          Access-Control-Allow-Credentials: "true"
          Access-Control-Max-Age: "86400"
"""

        config = provider.parse(traefik_config)

        # Service and upstream
        assert len(config.services) == 1
        service = config.services[0]
        assert service.name == "api-service"
        assert len(service.upstream.targets) == 2
        assert service.upstream.load_balancer.algorithm == "round_robin"
        assert service.upstream.load_balancer.sticky_sessions is True

        # Health checks
        assert service.upstream.health_check is not None

        # Route
        assert len(service.routes) == 1
        route = service.routes[0]
        assert route.path_prefix == "/api/v1"

        # Rate limiting
        assert route.rate_limit is not None
        assert route.rate_limit.enabled is True
        assert route.rate_limit.requests_per_second == 100

        # CORS
        assert route.cors is not None
        assert route.cors.enabled is True
        assert route.cors.allowed_origins == ["https://app.example.com"]
        assert route.cors.allow_credentials is True
