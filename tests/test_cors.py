"""
Tests for CORS (Cross-Origin Resource Sharing) policy implementation.

Tests all CORS functionality across all providers:
- Kong cors plugin
- APISIX cors plugin
- Traefik headers middleware with CORS headers
- Envoy native CORS policy
"""

import json
import pytest
from gal.config import Config, Service, Route, Upstream, GlobalConfig, CORSPolicy
from gal.providers.kong import KongProvider
from gal.providers.apisix import APISIXProvider
from gal.providers.traefik import TraefikProvider
from gal.providers.envoy import EnvoyProvider


class TestCORSPolicy:
    """Test CORS policy for all providers"""

    def _create_config_with_cors(self, provider_name: str, cors_policy: CORSPolicy):
        """Helper to create test config with CORS"""
        return Config(
            version="1.0",
            provider=provider_name,
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.local", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api/v1",
                            methods=["GET", "POST", "OPTIONS"],
                            cors=cors_policy
                        )
                    ]
                )
            ]
        )

    # Kong Tests
    def test_kong_cors_basic(self):
        """Test Kong CORS plugin with basic configuration"""
        provider = KongProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            allowed_methods=["GET", "POST"],
            allowed_headers=["Content-Type", "Authorization"]
        )
        config = self._create_config_with_cors("kong", cors)
        result = provider.generate(config)

        assert "cors" in result
        assert "origins:" in result
        assert "https://example.com" in result
        assert "methods:" in result
        assert "headers:" in result
        assert "Content-Type" in result
        assert "Authorization" in result

    def test_kong_cors_wildcard_origin(self):
        """Test Kong CORS with wildcard origin"""
        provider = KongProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["*"],
            allowed_methods=["GET", "POST"]
        )
        config = self._create_config_with_cors("kong", cors)
        result = provider.generate(config)

        assert "cors" in result
        assert '"*"' in result or "'*'" in result

    def test_kong_cors_with_credentials(self):
        """Test Kong CORS with credentials enabled"""
        provider = KongProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://app.example.com"],
            allow_credentials=True
        )
        config = self._create_config_with_cors("kong", cors)
        result = provider.generate(config)

        assert "cors" in result
        assert "credentials: true" in result

    def test_kong_cors_with_exposed_headers(self):
        """Test Kong CORS with exposed headers"""
        provider = KongProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            expose_headers=["X-Custom-Header", "X-Request-ID"]
        )
        config = self._create_config_with_cors("kong", cors)
        result = provider.generate(config)

        assert "cors" in result
        assert "exposed_headers:" in result

    def test_kong_cors_max_age(self):
        """Test Kong CORS with custom max_age"""
        provider = KongProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            max_age=7200
        )
        config = self._create_config_with_cors("kong", cors)
        result = provider.generate(config)

        assert "cors" in result
        assert "max_age: 7200" in result

    # APISIX Tests
    def test_apisix_cors_basic(self):
        """Test APISIX CORS plugin with basic configuration"""
        provider = APISIXProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            allowed_methods=["GET", "POST"],
            allowed_headers=["Content-Type"]
        )
        config = self._create_config_with_cors("apisix", cors)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "cors" in route["plugins"]
        assert route["plugins"]["cors"]["allow_origins"] == "https://example.com"
        assert route["plugins"]["cors"]["allow_methods"] == "GET,POST"
        assert route["plugins"]["cors"]["allow_headers"] == "Content-Type"

    def test_apisix_cors_multiple_origins(self):
        """Test APISIX CORS with multiple origins"""
        provider = APISIXProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com", "https://app.example.com"]
        )
        config = self._create_config_with_cors("apisix", cors)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "cors" in route["plugins"]
        assert "https://example.com" in route["plugins"]["cors"]["allow_origins"]
        assert "https://app.example.com" in route["plugins"]["cors"]["allow_origins"]

    def test_apisix_cors_credentials(self):
        """Test APISIX CORS with credentials"""
        provider = APISIXProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            allow_credentials=True
        )
        config = self._create_config_with_cors("apisix", cors)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert route["plugins"]["cors"]["allow_credential"] is True

    def test_apisix_cors_expose_headers(self):
        """Test APISIX CORS with expose headers"""
        provider = APISIXProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            expose_headers=["X-Request-ID", "X-Response-Time"]
        )
        config = self._create_config_with_cors("apisix", cors)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "expose_headers" in route["plugins"]["cors"]
        assert "X-Request-ID" in route["plugins"]["cors"]["expose_headers"]

    # Traefik Tests
    def test_traefik_cors_basic(self):
        """Test Traefik CORS headers middleware"""
        provider = TraefikProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            allowed_methods=["GET", "POST"]
        )
        config = self._create_config_with_cors("traefik", cors)
        result = provider.generate(config)

        assert "api_service_router_0_cors:" in result
        assert "accessControlAllowMethods:" in result
        assert "GET" in result
        assert "POST" in result
        assert "accessControlAllowOriginList:" in result
        assert "https://example.com" in result

    def test_traefik_cors_with_headers(self):
        """Test Traefik CORS with allowed headers"""
        provider = TraefikProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["*"],
            allowed_headers=["Content-Type", "Authorization", "X-API-Key"]
        )
        config = self._create_config_with_cors("traefik", cors)
        result = provider.generate(config)

        assert "accessControlAllowHeaders:" in result
        assert "Content-Type" in result
        assert "Authorization" in result
        assert "X-API-Key" in result

    def test_traefik_cors_with_credentials(self):
        """Test Traefik CORS with credentials"""
        provider = TraefikProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            allow_credentials=True
        )
        config = self._create_config_with_cors("traefik", cors)
        result = provider.generate(config)

        assert "accessControlAllowCredentials: true" in result

    def test_traefik_cors_max_age(self):
        """Test Traefik CORS with max age"""
        provider = TraefikProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            max_age=3600
        )
        config = self._create_config_with_cors("traefik", cors)
        result = provider.generate(config)

        assert "accessControlMaxAge: 3600" in result

    def test_traefik_cors_expose_headers(self):
        """Test Traefik CORS with expose headers"""
        provider = TraefikProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            expose_headers=["X-Custom-Header"]
        )
        config = self._create_config_with_cors("traefik", cors)
        result = provider.generate(config)

        assert "accessControlExposeHeaders:" in result
        assert "X-Custom-Header" in result

    # Envoy Tests
    def test_envoy_cors_basic(self):
        """Test Envoy native CORS policy"""
        provider = EnvoyProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            allowed_methods=["GET", "POST"]
        )
        config = self._create_config_with_cors("envoy", cors)
        result = provider.generate(config)

        assert "cors:" in result
        assert "allow_origin_string_match:" in result
        assert "https://example.com" in result
        assert "allow_methods:" in result
        assert "GET, POST" in result

    def test_envoy_cors_wildcard(self):
        """Test Envoy CORS with wildcard origin"""
        provider = EnvoyProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["*"]
        )
        config = self._create_config_with_cors("envoy", cors)
        result = provider.generate(config)

        assert "cors:" in result
        assert "safe_regex:" in result
        assert "regex: '.*'" in result

    def test_envoy_cors_credentials(self):
        """Test Envoy CORS with credentials"""
        provider = EnvoyProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            allow_credentials=True
        )
        config = self._create_config_with_cors("envoy", cors)
        result = provider.generate(config)

        assert "allow_credentials: true" in result

    def test_envoy_cors_expose_headers(self):
        """Test Envoy CORS with expose headers"""
        provider = EnvoyProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            expose_headers=["X-Request-ID", "X-Response-Time"]
        )
        config = self._create_config_with_cors("envoy", cors)
        result = provider.generate(config)

        assert "expose_headers:" in result
        assert "X-Request-ID" in result
        assert "X-Response-Time" in result

    def test_envoy_cors_max_age(self):
        """Test Envoy CORS with max age"""
        provider = EnvoyProvider()
        cors = CORSPolicy(
            enabled=True,
            allowed_origins=["https://example.com"],
            max_age=7200
        )
        config = self._create_config_with_cors("envoy", cors)
        result = provider.generate(config)

        assert "max_age: '7200'" in result

    # Disabled CORS Tests
    def test_cors_disabled_kong(self):
        """Test that disabled CORS is not generated for Kong"""
        provider = KongProvider()
        cors = CORSPolicy(enabled=False)
        config = self._create_config_with_cors("kong", cors)
        result = provider.generate(config)

        # CORS plugin should not be present when disabled
        # Check that cors config block is not in the plugins section
        # Note: "cors:" might appear in comments, check for plugin config
        assert "name: cors" not in result

    def test_cors_disabled_apisix(self):
        """Test that disabled CORS is not generated for APISIX"""
        provider = APISIXProvider()
        cors = CORSPolicy(enabled=False)
        config = self._create_config_with_cors("apisix", cors)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        # CORS plugin should not be present when disabled
        assert "cors" not in route.get("plugins", {})

    def test_cors_disabled_traefik(self):
        """Test that disabled CORS is not generated for Traefik"""
        provider = TraefikProvider()
        cors = CORSPolicy(enabled=False)
        config = self._create_config_with_cors("traefik", cors)
        result = provider.generate(config)

        # CORS middleware should not be present
        assert "api_service_router_0_cors:" not in result
        assert "accessControlAllowOrigin" not in result

    def test_cors_disabled_envoy(self):
        """Test that disabled CORS is not generated for Envoy"""
        provider = EnvoyProvider()
        cors = CORSPolicy(enabled=False)
        config = self._create_config_with_cors("envoy", cors)
        result = provider.generate(config)

        # Count occurrences of "cors:" - should only be in comments
        cors_count = result.count("cors:")
        # There should be no CORS config block in routes
        assert "allow_origin_string_match:" not in result
