"""
Tests for authentication feature across all providers
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
    AuthenticationConfig,
    BasicAuthConfig,
    ApiKeyConfig,
    JwtConfig
)


class TestAuthentication:
    """Test authentication for all providers"""

    def test_kong_basic_auth(self):
        """Test Kong basic authentication generation"""
        provider = KongProvider()
        config = self._create_config_with_basic_auth("kong")

        result = provider.generate(config)

        assert "plugins:" in result
        assert "basic-auth" in result
        assert "hide_credentials: true" in result

    def test_kong_api_key_auth(self):
        """Test Kong API key authentication generation"""
        provider = KongProvider()
        config = self._create_config_with_api_key_auth("kong")

        result = provider.generate(config)

        assert "plugins:" in result
        assert "key-auth" in result
        assert "X-API-Key" in result
        assert "key_in_header: true" in result

    def test_kong_jwt_auth(self):
        """Test Kong JWT authentication generation"""
        provider = KongProvider()
        config = self._create_config_with_jwt_auth("kong")

        result = provider.generate(config)

        assert "plugins:" in result
        assert "- name: jwt" in result

    def test_apisix_basic_auth(self):
        """Test APISIX basic authentication generation"""
        provider = APISIXProvider()
        config = self._create_config_with_basic_auth("apisix")

        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "plugins" in route
        assert "basic-auth" in route["plugins"]

    def test_apisix_api_key_auth(self):
        """Test APISIX API key authentication generation"""
        provider = APISIXProvider()
        config = self._create_config_with_api_key_auth("apisix")

        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "plugins" in route
        assert "key-auth" in route["plugins"]
        assert "header" in route["plugins"]["key-auth"]

    def test_apisix_jwt_auth(self):
        """Test APISIX JWT authentication generation"""
        provider = APISIXProvider()
        config = self._create_config_with_jwt_auth("apisix")

        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "plugins" in route
        assert "jwt-auth" in route["plugins"]

    def test_traefik_basic_auth(self):
        """Test Traefik basic authentication generation"""
        provider = TraefikProvider()
        config = self._create_config_with_basic_auth("traefik")

        result = provider.generate(config)

        assert "middlewares:" in result
        assert "_auth:" in result
        assert "basicAuth:" in result
        assert "users:" in result

    def test_traefik_api_key_auth(self):
        """Test Traefik API key authentication (via forwardAuth)"""
        provider = TraefikProvider()
        config = self._create_config_with_api_key_auth("traefik")

        result = provider.generate(config)

        assert "middlewares:" in result
        assert "_auth:" in result
        assert "forwardAuth:" in result
        assert "X-API-Key" in result

    def test_traefik_jwt_auth(self):
        """Test Traefik JWT authentication (via forwardAuth)"""
        provider = TraefikProvider()
        config = self._create_config_with_jwt_auth("traefik")

        result = provider.generate(config)

        assert "middlewares:" in result
        assert "_auth:" in result
        assert "forwardAuth:" in result
        assert "Authorization" in result

    def test_envoy_basic_auth(self):
        """Test Envoy basic authentication (via Lua filter)"""
        provider = EnvoyProvider()
        config = self._create_config_with_basic_auth("envoy")

        result = provider.generate(config)

        assert "envoy.filters.http.lua" in result
        assert "Basic Authentication" in result
        assert "authorization" in result

    def test_envoy_api_key_auth(self):
        """Test Envoy API key authentication (via Lua filter)"""
        provider = EnvoyProvider()
        config = self._create_config_with_api_key_auth("envoy")

        result = provider.generate(config)

        assert "envoy.filters.http.lua" in result
        assert "API Key Authentication" in result
        assert "x-api-key" in result

    def test_envoy_jwt_auth(self):
        """Test Envoy JWT authentication generation"""
        provider = EnvoyProvider()
        config = self._create_config_with_jwt_auth("envoy")

        result = provider.generate(config)

        assert "envoy.filters.http.jwt_authn" in result
        assert "jwt_provider" in result
        assert "https://auth.example.com" in result
        assert "api.example.com" in result
        assert "jwks_cluster" in result

    def test_kong_multiple_auth_types(self):
        """Test Kong with different auth types on multiple routes"""
        provider = KongProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        route1 = Route(
            path_prefix="/api/public",
            authentication=AuthenticationConfig(
                type="api_key",
                api_key=ApiKeyConfig(keys=["key123"])
            )
        )
        route2 = Route(
            path_prefix="/api/admin",
            authentication=AuthenticationConfig(
                type="basic",
                basic_auth=BasicAuthConfig(users={"admin": "secret"})
            )
        )

        service = Service(
            name="test_service",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route1, route2]
        )

        config = Config(
            version="1.0",
            provider="kong",
            global_config=global_config,
            services=[service]
        )

        result = provider.generate(config)

        # Should have both authentication types
        assert result.count("key-auth") == 1
        assert result.count("basic-auth") == 1

    def test_authentication_disabled(self):
        """Test that disabled authentication is not generated"""
        provider = KongProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        auth = AuthenticationConfig(
            enabled=False,
            type="api_key",
            api_key=ApiKeyConfig(keys=["key123"])
        )
        route = Route(path_prefix="/api", authentication=auth)

        service = Service(
            name="test_service",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="kong",
            global_config=global_config,
            services=[service]
        )

        result = provider.generate(config)

        # Should NOT have authentication since it's disabled
        assert "key-auth" not in result
        assert "basic-auth" not in result

    def test_envoy_no_authentication(self):
        """Test Envoy without authentication"""
        provider = EnvoyProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")  # No authentication

        service = Service(
            name="test_service",
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

        result = provider.generate(config)

        # Should NOT have authentication filters
        assert "envoy.filters.http.jwt_authn" not in result
        # Note: Lua filter might exist for transformations, so don't check for it

    def test_apisix_jwt_with_custom_algorithm(self):
        """Test APISIX JWT authentication with custom algorithm"""
        provider = APISIXProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        jwt_config = JwtConfig(
            issuer="https://auth.example.com",
            audience="api.example.com",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            algorithms=["ES256"]
        )

        auth = AuthenticationConfig(
            type="jwt",
            jwt=jwt_config
        )
        route = Route(path_prefix="/api", authentication=auth)

        service = Service(
            name="test_service",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="apisix",
            global_config=global_config,
            services=[service]
        )

        result = provider.generate(config)
        config_json = json.loads(result)

        route_config = config_json["routes"][0]
        assert route_config["plugins"]["jwt-auth"]["algorithm"] == "ES256"
        assert route_config["plugins"]["jwt-auth"]["iss"] == "https://auth.example.com"
        assert route_config["plugins"]["jwt-auth"]["aud"] == "api.example.com"

    def test_traefik_basic_auth_with_realm(self):
        """Test Traefik basic authentication with custom realm"""
        provider = TraefikProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        basic_auth = BasicAuthConfig(
            users={"admin": "secret123"},
            realm="Admin Area"
        )

        auth = AuthenticationConfig(
            type="basic",
            basic_auth=basic_auth
        )
        route = Route(path_prefix="/api", authentication=auth)

        service = Service(
            name="test_service",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="traefik",
            global_config=global_config,
            services=[service]
        )

        result = provider.generate(config)

        assert "realm: 'Admin Area'" in result
        assert "admin:secret123" in result

    def test_api_key_in_query_parameter(self):
        """Test API key authentication via query parameter"""
        provider = KongProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        api_key = ApiKeyConfig(
            keys=["key123"],
            key_name="api_key",
            in_location="query"
        )

        auth = AuthenticationConfig(
            type="api_key",
            api_key=api_key
        )
        route = Route(path_prefix="/api", authentication=auth)

        service = Service(
            name="test_service",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="kong",
            global_config=global_config,
            services=[service]
        )

        result = provider.generate(config)

        assert "key-auth" in result
        assert "key_in_query: true" in result
        assert "api_key" in result

    def _create_config_with_basic_auth(self, provider_name):
        """Helper to create config with basic authentication"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        basic_auth = BasicAuthConfig(
            users={"admin": "secret123", "user": "password456"},
            realm="API Gateway"
        )

        auth = AuthenticationConfig(
            enabled=True,
            type="basic",
            basic_auth=basic_auth
        )

        route = Route(path_prefix="/api", authentication=auth)

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

    def _create_config_with_api_key_auth(self, provider_name):
        """Helper to create config with API key authentication"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        api_key = ApiKeyConfig(
            keys=["key123", "key456", "key789"],
            key_name="X-API-Key",
            in_location="header"
        )

        auth = AuthenticationConfig(
            enabled=True,
            type="api_key",
            api_key=api_key
        )

        route = Route(path_prefix="/api", authentication=auth)

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

    def _create_config_with_jwt_auth(self, provider_name):
        """Helper to create config with JWT authentication"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        jwt = JwtConfig(
            issuer="https://auth.example.com",
            audience="api.example.com",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            algorithms=["RS256", "ES256"],
            required_claims=["sub", "email"]
        )

        auth = AuthenticationConfig(
            enabled=True,
            type="jwt",
            jwt=jwt
        )

        route = Route(path_prefix="/api", authentication=auth)

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
