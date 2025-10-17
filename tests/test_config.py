"""
Tests for configuration loading and models
"""

import pytest
import yaml
import tempfile
from pathlib import Path
from gal.config import (
    Config,
    Service,
    Upstream,
    Route,
    GlobalConfig,
    Transformation,
    ComputedField,
    Validation,
    Plugin,
    RateLimitConfig,
    AuthenticationConfig,
    BasicAuthConfig,
    ApiKeyConfig,
    JwtConfig,
    HeaderManipulation
)


class TestGlobalConfig:
    """Test GlobalConfig class"""

    def test_default_values(self):
        """Test default configuration values"""
        config = GlobalConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 10000
        assert config.admin_port == 9901
        assert config.timeout == "30s"

    def test_custom_values(self):
        """Test custom configuration values"""
        config = GlobalConfig(
            host="127.0.0.1",
            port=8080,
            admin_port=9000,
            timeout="60s"
        )
        assert config.host == "127.0.0.1"
        assert config.port == 8080
        assert config.admin_port == 9000
        assert config.timeout == "60s"


class TestUpstream:
    """Test Upstream class"""

    def test_upstream_creation(self):
        """Test creating an upstream"""
        upstream = Upstream(host="service.local", port=8080)
        assert upstream.host == "service.local"
        assert upstream.port == 8080


class TestRoute:
    """Test Route class"""

    def test_route_with_path_only(self):
        """Test route with only path prefix"""
        route = Route(path_prefix="/api/v1")
        assert route.path_prefix == "/api/v1"
        assert route.methods is None
        assert route.rate_limit is None

    def test_route_with_methods(self):
        """Test route with HTTP methods"""
        route = Route(path_prefix="/api/v1", methods=["GET", "POST"])
        assert route.path_prefix == "/api/v1"
        assert route.methods == ["GET", "POST"]

    def test_route_with_rate_limit(self):
        """Test route with rate limiting"""
        rate_limit = RateLimitConfig(
            enabled=True,
            requests_per_second=100,
            burst=200
        )
        route = Route(
            path_prefix="/api/v1",
            methods=["GET", "POST"],
            rate_limit=rate_limit
        )
        assert route.path_prefix == "/api/v1"
        assert route.rate_limit is not None
        assert route.rate_limit.requests_per_second == 100
        assert route.rate_limit.burst == 200


class TestRateLimitConfig:
    """Test RateLimitConfig class"""

    def test_rate_limit_defaults(self):
        """Test rate limit configuration with default values"""
        rate_limit = RateLimitConfig()
        assert rate_limit.enabled is True
        assert rate_limit.requests_per_second == 100
        assert rate_limit.burst == 200  # Auto-calculated as 2x rate
        assert rate_limit.key_type == "ip_address"
        assert rate_limit.key_header is None
        assert rate_limit.key_claim is None
        assert rate_limit.response_status == 429
        assert rate_limit.response_message == "Rate limit exceeded"

    def test_rate_limit_custom_values(self):
        """Test rate limit configuration with custom values"""
        rate_limit = RateLimitConfig(
            enabled=True,
            requests_per_second=50,
            burst=150,
            key_type="header",
            key_header="X-API-Key",
            response_status=503,
            response_message="Too many requests"
        )
        assert rate_limit.enabled is True
        assert rate_limit.requests_per_second == 50
        assert rate_limit.burst == 150
        assert rate_limit.key_type == "header"
        assert rate_limit.key_header == "X-API-Key"
        assert rate_limit.response_status == 503
        assert rate_limit.response_message == "Too many requests"

    def test_rate_limit_burst_auto_calculation(self):
        """Test automatic burst calculation (2x rate)"""
        rate_limit = RateLimitConfig(requests_per_second=200)
        assert rate_limit.burst == 400  # Should be 2x

    def test_rate_limit_jwt_claim(self):
        """Test rate limit with JWT claim key"""
        rate_limit = RateLimitConfig(
            key_type="jwt_claim",
            key_claim="sub"
        )
        assert rate_limit.key_type == "jwt_claim"
        assert rate_limit.key_claim == "sub"

    def test_rate_limit_disabled(self):
        """Test rate limit configuration when disabled"""
        rate_limit = RateLimitConfig(enabled=False)
        assert rate_limit.enabled is False


class TestAuthenticationConfig:
    """Test AuthenticationConfig class"""

    def test_auth_defaults(self):
        """Test authentication configuration with default values"""
        auth = AuthenticationConfig()
        assert auth.enabled is True
        assert auth.type == "api_key"
        assert auth.basic_auth is None
        assert auth.api_key is None
        assert auth.jwt is None
        assert auth.fail_status == 401
        assert auth.fail_message == "Unauthorized"

    def test_basic_auth_config(self):
        """Test basic authentication configuration"""
        basic = BasicAuthConfig(
            users={"admin": "secret123", "user": "pass456"},
            realm="Admin Area"
        )
        assert len(basic.users) == 2
        assert basic.users["admin"] == "secret123"
        assert basic.realm == "Admin Area"

    def test_api_key_config(self):
        """Test API key configuration"""
        api_key = ApiKeyConfig(
            keys=["key1", "key2", "key3"],
            key_name="X-Custom-Key",
            in_location="header"
        )
        assert len(api_key.keys) == 3
        assert api_key.key_name == "X-Custom-Key"
        assert api_key.in_location == "header"

    def test_api_key_config_query(self):
        """Test API key configuration via query parameter"""
        api_key = ApiKeyConfig(
            keys=["key123"],
            key_name="api_key",
            in_location="query"
        )
        assert api_key.key_name == "api_key"
        assert api_key.in_location == "query"

    def test_jwt_config(self):
        """Test JWT configuration"""
        jwt = JwtConfig(
            issuer="https://auth.example.com",
            audience="api.example.com",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            algorithms=["RS256", "ES256"],
            required_claims=["sub", "email"]
        )
        assert jwt.issuer == "https://auth.example.com"
        assert jwt.audience == "api.example.com"
        assert jwt.jwks_uri == "https://auth.example.com/.well-known/jwks.json"
        assert len(jwt.algorithms) == 2
        assert len(jwt.required_claims) == 2

    def test_jwt_config_defaults(self):
        """Test JWT configuration with default algorithm"""
        jwt = JwtConfig()
        assert jwt.algorithms == ["RS256"]
        assert jwt.required_claims == []

    def test_route_with_basic_auth(self):
        """Test route with basic authentication"""
        basic = BasicAuthConfig(users={"admin": "secret"})
        auth = AuthenticationConfig(type="basic", basic_auth=basic)
        route = Route(path_prefix="/api", authentication=auth)

        assert route.authentication is not None
        assert route.authentication.type == "basic"
        assert route.authentication.basic_auth is not None
        assert "admin" in route.authentication.basic_auth.users

    def test_route_with_api_key_auth(self):
        """Test route with API key authentication"""
        api_key = ApiKeyConfig(keys=["key123"])
        auth = AuthenticationConfig(type="api_key", api_key=api_key)
        route = Route(path_prefix="/api", authentication=auth)

        assert route.authentication is not None
        assert route.authentication.type == "api_key"
        assert route.authentication.api_key is not None
        assert len(route.authentication.api_key.keys) == 1

    def test_route_with_jwt_auth(self):
        """Test route with JWT authentication"""
        jwt = JwtConfig(issuer="https://auth.example.com")
        auth = AuthenticationConfig(type="jwt", jwt=jwt)
        route = Route(path_prefix="/api", authentication=auth)

        assert route.authentication is not None
        assert route.authentication.type == "jwt"
        assert route.authentication.jwt is not None
        assert route.authentication.jwt.issuer == "https://auth.example.com"

    def test_auth_disabled(self):
        """Test disabled authentication configuration"""
        api_key = ApiKeyConfig(keys=["key123"])
        auth = AuthenticationConfig(enabled=False, type="api_key", api_key=api_key)

        assert auth.enabled is False
        assert auth.type == "api_key"


class TestComputedField:
    """Test ComputedField class"""

    def test_computed_field_basic(self):
        """Test basic computed field"""
        field = ComputedField(field="user_id", generator="uuid")
        assert field.field == "user_id"
        assert field.generator == "uuid"
        assert field.prefix == ""
        assert field.suffix == ""

    def test_computed_field_with_prefix_suffix(self):
        """Test computed field with prefix and suffix"""
        field = ComputedField(
            field="order_id",
            generator="uuid",
            prefix="order_",
            suffix="_v1"
        )
        assert field.field == "order_id"
        assert field.generator == "uuid"
        assert field.prefix == "order_"
        assert field.suffix == "_v1"


class TestValidation:
    """Test Validation class"""

    def test_validation_empty(self):
        """Test validation with no required fields"""
        validation = Validation()
        assert validation.required_fields == []

    def test_validation_with_fields(self):
        """Test validation with required fields"""
        validation = Validation(required_fields=["id", "name", "email"])
        assert len(validation.required_fields) == 3
        assert "id" in validation.required_fields


class TestTransformation:
    """Test Transformation class"""

    def test_transformation_defaults(self):
        """Test transformation with default values"""
        trans = Transformation()
        assert trans.enabled is True
        assert trans.defaults == {}
        assert trans.computed_fields == []
        assert trans.metadata == {}

    def test_transformation_full(self):
        """Test transformation with all fields"""
        computed = ComputedField(field="id", generator="uuid")
        validation = Validation(required_fields=["name"])

        trans = Transformation(
            enabled=True,
            defaults={"status": "active"},
            computed_fields=[computed],
            metadata={"version": "1.0"},
            validation=validation
        )

        assert trans.enabled is True
        assert trans.defaults["status"] == "active"
        assert len(trans.computed_fields) == 1
        assert trans.metadata["version"] == "1.0"
        assert trans.validation is not None


class TestService:
    """Test Service class"""

    def test_grpc_service(self):
        """Test gRPC service creation"""
        upstream = Upstream(host="grpc.local", port=9090)
        route = Route(path_prefix="/myapp.Service")

        service = Service(
            name="test_service",
            type="grpc",
            protocol="http2",
            upstream=upstream,
            routes=[route]
        )

        assert service.name == "test_service"
        assert service.type == "grpc"
        assert service.protocol == "http2"
        assert service.upstream.host == "grpc.local"
        assert len(service.routes) == 1

    def test_rest_service_with_transformation(self):
        """Test REST service with transformation"""
        upstream = Upstream(host="api.local", port=8080)
        route = Route(path_prefix="/api/users", methods=["GET", "POST"])
        trans = Transformation(
            enabled=True,
            defaults={"role": "user"}
        )

        service = Service(
            name="user_api",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route],
            transformation=trans
        )

        assert service.name == "user_api"
        assert service.type == "rest"
        assert service.transformation is not None
        assert service.transformation.defaults["role"] == "user"


class TestPlugin:
    """Test Plugin class"""

    def test_plugin_basic(self):
        """Test basic plugin"""
        plugin = Plugin(name="rate_limiting")
        assert plugin.name == "rate_limiting"
        assert plugin.enabled is True
        assert plugin.config == {}

    def test_plugin_with_config(self):
        """Test plugin with configuration"""
        plugin = Plugin(
            name="cors",
            enabled=True,
            config={"origins": ["*"], "methods": ["GET", "POST"]}
        )
        assert plugin.name == "cors"
        assert plugin.enabled is True
        assert plugin.config["origins"] == ["*"]


class TestConfig:
    """Test main Config class"""

    def test_config_creation(self):
        """Test creating a config object"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")
        service = Service(
            name="test",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=global_config,
            services=[service]
        )

        assert config.version == "1.0"
        assert config.provider == "envoy"
        assert len(config.services) == 1

    def test_get_service(self):
        """Test getting service by name"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")

        service1 = Service(
            name="service1",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )
        service2 = Service(
            name="service2",
            type="grpc",
            protocol="http2",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=global_config,
            services=[service1, service2]
        )

        found = config.get_service("service1")
        assert found is not None
        assert found.name == "service1"

        not_found = config.get_service("service3")
        assert not_found is None

    def test_get_grpc_services(self):
        """Test filtering gRPC services"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")

        rest_service = Service(
            name="rest",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )
        grpc_service = Service(
            name="grpc",
            type="grpc",
            protocol="http2",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=global_config,
            services=[rest_service, grpc_service]
        )

        grpc_services = config.get_grpc_services()
        assert len(grpc_services) == 1
        assert grpc_services[0].name == "grpc"

    def test_get_rest_services(self):
        """Test filtering REST services"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")

        rest_service = Service(
            name="rest",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )
        grpc_service = Service(
            name="grpc",
            type="grpc",
            protocol="http2",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=global_config,
            services=[rest_service, grpc_service]
        )

        rest_services = config.get_rest_services()
        assert len(rest_services) == 1
        assert rest_services[0].name == "rest"

    def test_from_yaml(self):
        """Test loading configuration from YAML file"""
        yaml_content = """
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901
  timeout: 30s

services:
  - name: test_service
    type: rest
    protocol: http
    upstream:
      host: test.local
      port: 8080
    routes:
      - path_prefix: /api/test
        methods: [GET, POST]
    transformation:
      enabled: true
      defaults:
        status: active
      computed_fields:
        - field: id
          generator: uuid
          prefix: "test_"
      metadata:
        version: "1.0"
      validation:
        required_fields: [name, email]

plugins:
  - name: rate_limiting
    enabled: true
    config:
      requests_per_second: 100
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            config = Config.from_yaml(temp_file)

            assert config.version == "1.0"
            assert config.provider == "envoy"
            assert config.global_config.host == "0.0.0.0"
            assert config.global_config.port == 10000

            assert len(config.services) == 1
            service = config.services[0]
            assert service.name == "test_service"
            assert service.type == "rest"
            assert service.upstream.host == "test.local"
            assert service.upstream.port == 8080

            assert len(service.routes) == 1
            assert service.routes[0].path_prefix == "/api/test"
            assert service.routes[0].methods == ["GET", "POST"]

            assert service.transformation is not None
            assert service.transformation.enabled is True
            assert service.transformation.defaults["status"] == "active"
            assert len(service.transformation.computed_fields) == 1
            assert service.transformation.computed_fields[0].field == "id"
            assert service.transformation.computed_fields[0].generator == "uuid"
            assert service.transformation.computed_fields[0].prefix == "test_"

            assert service.transformation.validation is not None
            assert "name" in service.transformation.validation.required_fields

            assert len(config.plugins) == 1
            assert config.plugins[0].name == "rate_limiting"
            assert config.plugins[0].config["requests_per_second"] == 100
        finally:
            Path(temp_file).unlink()

    def test_from_yaml_minimal(self):
        """Test loading minimal YAML configuration"""
        yaml_content = """
version: "1.0"
provider: kong

services:
  - name: simple_service
    type: rest
    protocol: http
    upstream:
      host: simple.local
      port: 8080
    routes:
      - path_prefix: /api
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            config = Config.from_yaml(temp_file)

            assert config.version == "1.0"
            assert config.provider == "kong"
            assert config.global_config.host == "0.0.0.0"  # Default value
            assert len(config.services) == 1
            assert len(config.plugins) == 0
        finally:
            Path(temp_file).unlink()

    def test_from_yaml_with_rate_limiting(self):
        """Test loading YAML configuration with rate limiting"""
        yaml_content = """
version: "1.0"
provider: kong

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.local
      port: 8080
    routes:
      - path_prefix: /api/public
        methods: [GET, POST]
        rate_limit:
          enabled: true
          requests_per_second: 100
          burst: 200
          key_type: ip_address
          response_status: 429
          response_message: "Rate limit exceeded"
      - path_prefix: /api/private
        methods: [GET, POST, PUT, DELETE]
        rate_limit:
          enabled: true
          requests_per_second: 50
          burst: 100
          key_type: header
          key_header: X-API-Key
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            config = Config.from_yaml(temp_file)

            assert config.version == "1.0"
            assert config.provider == "kong"
            assert len(config.services) == 1

            service = config.services[0]
            assert service.name == "api_service"
            assert len(service.routes) == 2

            # Test first route with rate limiting
            route1 = service.routes[0]
            assert route1.path_prefix == "/api/public"
            assert route1.rate_limit is not None
            assert route1.rate_limit.enabled is True
            assert route1.rate_limit.requests_per_second == 100
            assert route1.rate_limit.burst == 200
            assert route1.rate_limit.key_type == "ip_address"
            assert route1.rate_limit.response_status == 429
            assert route1.rate_limit.response_message == "Rate limit exceeded"

            # Test second route with different rate limiting
            route2 = service.routes[1]
            assert route2.path_prefix == "/api/private"
            assert route2.rate_limit is not None
            assert route2.rate_limit.enabled is True
            assert route2.rate_limit.requests_per_second == 50
            assert route2.rate_limit.burst == 100
            assert route2.rate_limit.key_type == "header"
            assert route2.rate_limit.key_header == "X-API-Key"
        finally:
            Path(temp_file).unlink()


class TestHeaderManipulation:
    """Test HeaderManipulation class"""

    def test_header_manipulation_defaults(self):
        """Test header manipulation with default values"""
        headers = HeaderManipulation()
        assert headers.request_add == {}
        assert headers.request_set == {}
        assert headers.request_remove == []
        assert headers.response_add == {}
        assert headers.response_set == {}
        assert headers.response_remove == []

    def test_header_manipulation_request_add(self):
        """Test adding request headers"""
        headers = HeaderManipulation(
            request_add={"X-Custom": "value", "X-API-Version": "v1"}
        )
        assert len(headers.request_add) == 2
        assert headers.request_add["X-Custom"] == "value"
        assert headers.request_add["X-API-Version"] == "v1"

    def test_header_manipulation_request_set(self):
        """Test setting/replacing request headers"""
        headers = HeaderManipulation(
            request_set={"User-Agent": "GAL-Proxy"}
        )
        assert headers.request_set["User-Agent"] == "GAL-Proxy"

    def test_header_manipulation_request_remove(self):
        """Test removing request headers"""
        headers = HeaderManipulation(
            request_remove=["X-Debug", "X-Internal"]
        )
        assert len(headers.request_remove) == 2
        assert "X-Debug" in headers.request_remove

    def test_header_manipulation_response_add(self):
        """Test adding response headers"""
        headers = HeaderManipulation(
            response_add={
                "X-Response-Time": "100ms",
                "X-Cache-Status": "HIT"
            }
        )
        assert len(headers.response_add) == 2
        assert headers.response_add["X-Cache-Status"] == "HIT"

    def test_header_manipulation_response_set(self):
        """Test setting/replacing response headers"""
        headers = HeaderManipulation(
            response_set={"Server": "GAL-Gateway"}
        )
        assert headers.response_set["Server"] == "GAL-Gateway"

    def test_header_manipulation_response_remove(self):
        """Test removing response headers"""
        headers = HeaderManipulation(
            response_remove=["Server", "X-Powered-By"]
        )
        assert len(headers.response_remove) == 2
        assert "Server" in headers.response_remove

    def test_header_manipulation_mixed(self):
        """Test header manipulation with mixed operations"""
        headers = HeaderManipulation(
            request_add={"X-Request-ID": "abc123"},
            request_remove=["X-Old-Header"],
            response_add={"X-Response-ID": "xyz789"},
            response_remove=["Server"]
        )
        assert len(headers.request_add) == 1
        assert len(headers.request_remove) == 1
        assert len(headers.response_add) == 1
        assert len(headers.response_remove) == 1

    def test_route_with_headers(self):
        """Test route with header manipulation"""
        headers = HeaderManipulation(
            request_add={"X-Route": "api"}
        )
        route = Route(path_prefix="/api", headers=headers)

        assert route.headers is not None
        assert route.headers.request_add["X-Route"] == "api"

    def test_transformation_with_headers(self):
        """Test transformation with header manipulation"""
        headers = HeaderManipulation(
            request_add={"X-Service": "backend"},
            response_add={"X-Version": "1.0"}
        )
        trans = Transformation(
            enabled=True,
            headers=headers
        )

        assert trans.headers is not None
        assert trans.headers.request_add["X-Service"] == "backend"
        assert trans.headers.response_add["X-Version"] == "1.0"

    def test_security_headers_config(self):
        """Test security headers configuration"""
        headers = HeaderManipulation(
            response_add={
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000"
            },
            response_remove=["Server", "X-Powered-By"]
        )

        assert "X-Frame-Options" in headers.response_add
        assert headers.response_add["X-Frame-Options"] == "DENY"
        assert "Server" in headers.response_remove

    def test_cors_headers_config(self):
        """Test CORS headers configuration"""
        headers = HeaderManipulation(
            response_add={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Max-Age": "86400"
            }
        )

        assert len(headers.response_add) == 4
        assert "Access-Control-Allow-Origin" in headers.response_add
        assert headers.response_add["Access-Control-Allow-Origin"] == "*"

    def test_from_yaml_with_headers(self):
        """Test loading YAML configuration with header manipulation"""
        yaml_content = """
version: "1.0"
provider: kong

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.local
      port: 8080
    routes:
      - path_prefix: /api/v1
        headers:
          request_add:
            X-API-Version: v1
            X-Request-ID: "{{uuid}}"
          request_remove:
            - X-Internal-Header
          response_add:
            X-Response-Time: 100ms
          response_remove:
            - Server
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            config = Config.from_yaml(temp_file)

            assert config.version == "1.0"
            assert len(config.services) == 1

            service = config.services[0]
            assert len(service.routes) == 1

            route = service.routes[0]
            assert route.headers is not None
            assert route.headers.request_add["X-API-Version"] == "v1"
            assert "X-Internal-Header" in route.headers.request_remove
            assert route.headers.response_add["X-Response-Time"] == "100ms"
            assert "Server" in route.headers.response_remove
        finally:
            Path(temp_file).unlink()

    def test_from_yaml_with_transformation_headers(self):
        """Test loading YAML configuration with transformation-level headers"""
        yaml_content = """
version: "1.0"
provider: apisix

services:
  - name: backend_service
    type: rest
    protocol: http
    upstream:
      host: backend.local
      port: 8080
    routes:
      - path_prefix: /api
    transformation:
      enabled: true
      defaults:
        status: active
      headers:
        request_add:
          X-Service-Name: backend_service
        response_set:
          X-API-Version: "2.0"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            config = Config.from_yaml(temp_file)

            service = config.services[0]
            assert service.transformation is not None
            assert service.transformation.headers is not None
            assert service.transformation.headers.request_add["X-Service-Name"] == "backend_service"
            assert service.transformation.headers.response_set["X-API-Version"] == "2.0"
        finally:
            Path(temp_file).unlink()


class TestCORSPolicy:
    """Test CORSPolicy class"""

    def test_cors_policy_defaults(self):
        """Test CORS policy with default values"""
        from gal.config import CORSPolicy
        
        cors = CORSPolicy()
        assert cors.enabled is True
        assert cors.allowed_origins == ["*"]
        assert "GET" in cors.allowed_methods
        assert "POST" in cors.allowed_methods
        assert "Content-Type" in cors.allowed_headers
        assert "Authorization" in cors.allowed_headers
        assert cors.expose_headers == []
        assert cors.allow_credentials is False
        assert cors.max_age == 86400

    def test_cors_policy_custom_values(self):
        """Test CORS policy with custom values"""
        from gal.config import CORSPolicy
        
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com", "https://app.example.com"],
            allowed_methods=["GET", "POST"],
            allowed_headers=["Content-Type", "X-API-Key"],
            expose_headers=["X-Request-ID", "X-Response-Time"],
            allow_credentials=True,
            max_age=7200
        )
        assert cors.enabled is True
        assert len(cors.allowed_origins) == 2
        assert "https://example.com" in cors.allowed_origins
        assert len(cors.allowed_methods) == 2
        assert cors.allow_credentials is True
        assert cors.max_age == 7200

    def test_cors_policy_wildcard_origin(self):
        """Test CORS policy with wildcard origin"""
        from gal.config import CORSPolicy
        
        cors = CORSPolicy(allowed_origins=["*"])
        assert cors.allowed_origins == ["*"]

    def test_route_with_cors(self):
        """Test route with CORS policy"""
        from gal.config import Route, CORSPolicy
        
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"]
        )
        route = Route(path_prefix="/api", cors=cors)

        assert route.cors is not None
        assert route.cors.enabled is True
        assert "https://example.com" in route.cors.allowed_origins

    def test_cors_disabled(self):
        """Test disabled CORS policy"""
        from gal.config import CORSPolicy
        
        cors = CORSPolicy(enabled=False)
        assert cors.enabled is False

    def test_from_yaml_with_cors(self):
        """Test loading YAML configuration with CORS"""
        yaml_content = """
version: "1.0"
provider: kong

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.local
      port: 8080
    routes:
      - path_prefix: /api/public
        methods: [GET, POST, OPTIONS]
        cors:
          enabled: true
          allowed_origins:
            - "https://example.com"
            - "https://app.example.com"
          allowed_methods: [GET, POST]
          allowed_headers: [Content-Type, Authorization]
          expose_headers: [X-Request-ID]
          allow_credentials: true
          max_age: 3600
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            config = Config.from_yaml(temp_file)

            assert config.version == "1.0"
            assert len(config.services) == 1

            service = config.services[0]
            assert len(service.routes) == 1

            route = service.routes[0]
            assert route.cors is not None
            assert route.cors.enabled is True
            assert len(route.cors.allowed_origins) == 2
            assert "https://example.com" in route.cors.allowed_origins
            assert len(route.cors.allowed_methods) == 2
            assert "Content-Type" in route.cors.allowed_headers
            assert len(route.cors.expose_headers) == 1
            assert route.cors.allow_credentials is True
            assert route.cors.max_age == 3600
        finally:
            Path(temp_file).unlink()

    def test_from_yaml_cors_defaults(self):
        """Test loading YAML with minimal CORS configuration"""
        yaml_content = """
version: "1.0"
provider: apisix

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.local
      port: 8080
    routes:
      - path_prefix: /api
        cors:
          enabled: true
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            config = Config.from_yaml(temp_file)
            route = config.services[0].routes[0]
            
            # Check that defaults are applied
            assert route.cors is not None
            assert route.cors.enabled is True
            assert route.cors.allowed_origins == ["*"]  # Default
            assert "GET" in route.cors.allowed_methods  # Default
        finally:
            Path(temp_file).unlink()
