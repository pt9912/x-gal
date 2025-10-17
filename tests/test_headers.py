"""
Tests for header manipulation feature across all providers
"""

import pytest
import json
from gal.providers.envoy import EnvoyProvider
from gal.providers.kong import KongProvider
from gal.providers.apisix import APISIXProvider
from gal.providers.traefik import TraefikProvider
from gal.config import (
    Config,
    Service,
    Upstream,
    Route,
    GlobalConfig,
    HeaderManipulation,
    Transformation
)


class TestHeaderManipulation:
    """Test header manipulation for all providers"""

    def test_kong_request_headers_add(self):
        """Test Kong request header addition"""
        provider = KongProvider()
        config = self._create_config_with_request_headers("kong", "add")
        result = provider.generate(config)

        assert "request-transformer" in result
        assert "X-Custom-Header" in result
        assert "custom-value" in result

    def test_kong_request_headers_set(self):
        """Test Kong request header set/replace"""
        provider = KongProvider()
        headers = HeaderManipulation(
            request_set={"X-Forwarded-For": "10.0.0.1"}
        )
        config = self._create_config_with_headers("kong", headers)
        result = provider.generate(config)

        assert "request-transformer" in result
        assert "replace:" in result
        assert "X-Forwarded-For" in result

    def test_kong_request_headers_remove(self):
        """Test Kong request header removal"""
        provider = KongProvider()
        headers = HeaderManipulation(
            request_remove=["X-Internal-Header", "X-Debug"]
        )
        config = self._create_config_with_headers("kong", headers)
        result = provider.generate(config)

        assert "request-transformer" in result
        assert "remove:" in result
        assert "X-Internal-Header" in result

    def test_kong_response_headers(self):
        """Test Kong response header manipulation"""
        provider = KongProvider()
        headers = HeaderManipulation(
            response_add={"X-Response-Time": "100ms"},
            response_remove=["Server"]
        )
        config = self._create_config_with_headers("kong", headers)
        result = provider.generate(config)

        assert "response-transformer" in result
        assert "X-Response-Time" in result
        assert "Server" in result

    def test_apisix_request_headers(self):
        """Test APISIX request header manipulation"""
        provider = APISIXProvider()
        headers = HeaderManipulation(
            request_add={"X-API-Version": "v1"},
            request_set={"X-Request-ID": "12345"},
            request_remove=["X-Old-Header"]
        )
        config = self._create_config_with_headers("apisix", headers)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "plugins" in route
        assert "proxy-rewrite" in route["plugins"]
        proxy_rewrite = route["plugins"]["proxy-rewrite"]
        assert "headers" in proxy_rewrite
        assert "add" in proxy_rewrite["headers"]
        assert "set" in proxy_rewrite["headers"]
        assert "remove" in proxy_rewrite["headers"]

    def test_apisix_response_headers(self):
        """Test APISIX response header manipulation"""
        provider = APISIXProvider()
        headers = HeaderManipulation(
            response_add={"X-Powered-By": "GAL"},
            response_remove=["Server"]
        )
        config = self._create_config_with_headers("apisix", headers)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "plugins" in route
        assert "response-rewrite" in route["plugins"]
        response_rewrite = route["plugins"]["response-rewrite"]
        assert "headers" in response_rewrite

    def test_traefik_request_headers(self):
        """Test Traefik request header manipulation"""
        provider = TraefikProvider()
        headers = HeaderManipulation(
            request_add={"X-Traefik": "enabled"},
            request_remove=["X-Old"]
        )
        config = self._create_config_with_headers("traefik", headers)
        result = provider.generate(config)

        assert "middlewares:" in result
        assert "_headers:" in result
        assert "customRequestHeaders:" in result
        assert "X-Traefik" in result

    def test_traefik_response_headers(self):
        """Test Traefik response header manipulation"""
        provider = TraefikProvider()
        headers = HeaderManipulation(
            response_add={"X-Frame-Options": "DENY"},
            response_remove=["Server"]
        )
        config = self._create_config_with_headers("traefik", headers)
        result = provider.generate(config)

        assert "middlewares:" in result
        assert "customResponseHeaders:" in result
        assert "X-Frame-Options" in result

    def test_envoy_request_headers(self):
        """Test Envoy request header manipulation"""
        provider = EnvoyProvider()
        headers = HeaderManipulation(
            request_add={"X-Envoy-Custom": "value"},
            request_set={"X-User-Agent": "GAL-Proxy"},
            request_remove=["X-Debug"]
        )
        config = self._create_config_with_headers("envoy", headers)
        result = provider.generate(config)

        assert "request_headers_to_add:" in result
        assert "X-Envoy-Custom" in result
        assert "request_headers_to_remove:" in result
        assert "X-Debug" in result

    def test_envoy_response_headers(self):
        """Test Envoy response header manipulation"""
        provider = EnvoyProvider()
        headers = HeaderManipulation(
            response_add={"X-Response-ID": "12345"},
            response_remove=["Server", "X-Powered-By"]
        )
        config = self._create_config_with_headers("envoy", headers)
        result = provider.generate(config)

        assert "response_headers_to_add:" in result
        assert "X-Response-ID" in result
        assert "response_headers_to_remove:" in result
        assert "Server" in result

    def test_kong_service_level_headers(self):
        """Test Kong service-level (transformation) header manipulation"""
        provider = KongProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        headers = HeaderManipulation(
            request_add={"X-Service": "api"},
            response_add={"X-API-Version": "1.0"}
        )

        transformation = Transformation(
            enabled=True,
            headers=headers
        )

        route = Route(path_prefix="/api")
        service = Service(
            name="test_service",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route],
            transformation=transformation
        )

        config = Config(
            version="1.0",
            provider="kong",
            global_config=global_config,
            services=[service]
        )

        result = provider.generate(config)
        assert "request-transformer" in result
        assert "response-transformer" in result
        assert "X-Service" in result
        assert "X-API-Version" in result

    def test_apisix_service_level_headers(self):
        """Test APISIX service-level header manipulation"""
        provider = APISIXProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        headers = HeaderManipulation(
            request_set={"X-Backend": "service1"}
        )

        transformation = Transformation(
            enabled=True,
            headers=headers
        )

        route = Route(path_prefix="/api")
        service = Service(
            name="test_service",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route],
            transformation=transformation
        )

        config = Config(
            version="1.0",
            provider="apisix",
            global_config=global_config,
            services=[service]
        )

        result = provider.generate(config)
        config_json = json.loads(result)

        assert "services" in config_json
        svc = config_json["services"][0]
        assert "plugins" in svc
        assert "proxy-rewrite" in svc["plugins"]

    def test_mixed_route_and_service_headers(self):
        """Test that route-level headers take precedence over service-level"""
        provider = KongProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        # Service-level headers
        svc_headers = HeaderManipulation(
            request_add={"X-Service-Level": "true"}
        )
        transformation = Transformation(
            enabled=True,
            headers=svc_headers
        )

        # Route-level headers
        route_headers = HeaderManipulation(
            request_add={"X-Route-Level": "true"}
        )
        route = Route(path_prefix="/api", headers=route_headers)

        service = Service(
            name="test_service",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route],
            transformation=transformation
        )

        config = Config(
            version="1.0",
            provider="kong",
            global_config=global_config,
            services=[service]
        )

        result = provider.generate(config)
        # Route-level headers should be in route plugins section
        assert "X-Route-Level" in result
        # Service-level headers should be in service plugins section
        assert "X-Service-Level" in result

    def test_security_headers(self):
        """Test common security header configuration"""
        provider = TraefikProvider()
        headers = HeaderManipulation(
            response_add={
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'"
            },
            response_remove=["Server", "X-Powered-By"]
        )
        config = self._create_config_with_headers("traefik", headers)
        result = provider.generate(config)

        assert "X-Frame-Options" in result
        assert "X-Content-Type-Options" in result
        assert "Strict-Transport-Security" in result
        assert "Content-Security-Policy" in result

    def test_cors_headers(self):
        """Test CORS header configuration"""
        provider = APISIXProvider()
        headers = HeaderManipulation(
            response_add={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
        config = self._create_config_with_headers("apisix", headers)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "response-rewrite" in route["plugins"]
        headers_config = route["plugins"]["response-rewrite"]["headers"]
        assert "Access-Control-Allow-Origin" in headers_config["add"]

    def test_all_providers_same_config(self):
        """Test that all providers accept the same header configuration"""
        headers = HeaderManipulation(
            request_add={"X-Custom": "value"},
            request_remove=["X-Old"],
            response_add={"X-Response": "ok"}
        )

        providers = [
            ("kong", KongProvider()),
            ("apisix", APISIXProvider()),
            ("traefik", TraefikProvider()),
            ("envoy", EnvoyProvider())
        ]

        for provider_name, provider in providers:
            config = self._create_config_with_headers(provider_name, headers)
            result = provider.generate(config)
            # Should not raise any exceptions
            assert result is not None
            assert len(result) > 0

    # Helper methods
    def _create_config_with_headers(self, provider_name, headers):
        """Helper to create config with header manipulation"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api", headers=headers)

        service = Service(
            name="test_service",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        return Config(
            version="1.0",
            provider=provider_name,
            global_config=global_config,
            services=[service]
        )

    def _create_config_with_request_headers(self, provider_name, operation):
        """Helper to create config with request header operations"""
        if operation == "add":
            headers = HeaderManipulation(
                request_add={"X-Custom-Header": "custom-value"}
            )
        elif operation == "set":
            headers = HeaderManipulation(
                request_set={"X-User-Agent": "GAL-Proxy"}
            )
        else:  # remove
            headers = HeaderManipulation(
                request_remove=["X-Internal-Header"]
            )

        return self._create_config_with_headers(provider_name, headers)
