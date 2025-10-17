"""
Tests for rate limiting feature across all providers
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
    Transformation,
    RateLimitConfig
)


class TestRateLimiting:
    """Test rate limiting for all providers"""

    def test_kong_rate_limiting(self):
        """Test Kong rate limiting generation"""
        provider = KongProvider()
        config = self._create_config_with_rate_limit("kong")

        result = provider.generate(config)

        assert "plugins:" in result
        assert "rate-limiting" in result
        assert "second: 100" in result
        assert "policy: local" in result

    def test_apisix_rate_limiting(self):
        """Test APISIX rate limiting generation"""
        provider = APISIXProvider()
        config = self._create_config_with_rate_limit("apisix")

        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "plugins" in route
        assert "limit-count" in route["plugins"]
        assert route["plugins"]["limit-count"]["count"] == 100
        assert route["plugins"]["limit-count"]["time_window"] == 1
        assert route["plugins"]["limit-count"]["rejected_code"] == 429
        assert route["plugins"]["limit-count"]["key"] == "remote_addr"

    def test_traefik_rate_limiting(self):
        """Test Traefik rate limiting generation"""
        provider = TraefikProvider()
        config = self._create_config_with_rate_limit("traefik")

        result = provider.generate(config)

        assert "middlewares:" in result
        assert "_ratelimit:" in result
        assert "rateLimit:" in result
        assert "average: 100" in result
        assert "burst: 200" in result

    def test_envoy_rate_limiting(self):
        """Test Envoy rate limiting generation"""
        provider = EnvoyProvider()
        config = self._create_config_with_rate_limit("envoy")

        result = provider.generate(config)

        assert "envoy.filters.http.local_ratelimit" in result
        assert "token_bucket:" in result
        assert "max_tokens: 200" in result
        assert "tokens_per_fill: 100" in result
        assert "fill_interval: 1s" in result
        assert "status_code: 429" in result

    def test_kong_multiple_routes_rate_limiting(self):
        """Test Kong with different rate limits on multiple routes"""
        provider = KongProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        route1 = Route(
            path_prefix="/api/public",
            rate_limit=RateLimitConfig(requests_per_second=100, burst=200)
        )
        route2 = Route(
            path_prefix="/api/private",
            rate_limit=RateLimitConfig(requests_per_second=50, burst=100)
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

        # Should have rate limiting for both routes
        assert result.count("rate-limiting") == 2
        assert result.count("second: 100") == 1
        assert result.count("second: 50") == 1

    def test_traefik_with_transformation_and_rate_limit(self):
        """Test Traefik with both transformation and rate limiting middleware"""
        provider = TraefikProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        rate_limit = RateLimitConfig(requests_per_second=100, burst=200)
        route = Route(path_prefix="/api", rate_limit=rate_limit)

        transformation = Transformation(
            enabled=True,
            defaults={"status": "active"}
        )

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
            provider="traefik",
            global_config=global_config,
            services=[service]
        )

        result = provider.generate(config)

        # Should have both middlewares
        assert "- test_service_transform" in result
        assert "- test_service_router_0_ratelimit" in result
        assert "test_service_transform:" in result
        assert "test_service_router_0_ratelimit:" in result

    def test_rate_limit_disabled(self):
        """Test that disabled rate limiting is not generated"""
        provider = KongProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        rate_limit = RateLimitConfig(enabled=False, requests_per_second=100)
        route = Route(path_prefix="/api", rate_limit=rate_limit)

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

        # Should NOT have rate limiting since it's disabled
        assert "rate-limiting" not in result

    def test_apisix_rate_limit_custom_status(self):
        """Test APISIX rate limiting with custom status code and message"""
        provider = APISIXProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        rate_limit = RateLimitConfig(
            enabled=True,
            requests_per_second=50,
            burst=100,
            response_status=503,
            response_message="Service temporarily unavailable"
        )
        route = Route(path_prefix="/api", rate_limit=rate_limit)

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
        assert route_config["plugins"]["limit-count"]["rejected_code"] == 503
        assert route_config["plugins"]["limit-count"]["rejected_msg"] == "Service temporarily unavailable"

    def test_envoy_no_rate_limit(self):
        """Test Envoy without rate limiting"""
        provider = EnvoyProvider()
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")  # No rate limit

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

        # Should NOT have rate limiting filter
        assert "envoy.filters.http.local_ratelimit" not in result

    def _create_config_with_rate_limit(self, provider_name):
        """Helper to create config with rate limiting"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)

        rate_limit = RateLimitConfig(
            enabled=True,
            requests_per_second=100,
            burst=200,
            response_status=429,
            response_message="Rate limit exceeded"
        )

        route = Route(path_prefix="/api", rate_limit=rate_limit)

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
