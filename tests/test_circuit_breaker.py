"""
Tests for Circuit Breaker pattern implementation.

Tests circuit breaker functionality across all providers:
- APISIX: api-breaker plugin with state-based detection
- Traefik: CircuitBreaker middleware with expression syntax
- Envoy: Outlier Detection with consecutive errors
- Kong: Warning only (no native support)
"""

import json
import pytest
from gal.config import Config, Service, Route, Upstream, GlobalConfig, CircuitBreakerConfig
from gal.providers.kong import KongProvider
from gal.providers.apisix import APISIXProvider
from gal.providers.traefik import TraefikProvider
from gal.providers.envoy import EnvoyProvider


class TestCircuitBreaker:
    """Test Circuit Breaker pattern for all providers"""

    def _create_config_with_circuit_breaker(self, provider_name: str, circuit_breaker: CircuitBreakerConfig):
        """Helper to create test config with circuit breaker"""
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
                            methods=["GET", "POST"],
                            circuit_breaker=circuit_breaker
                        )
                    ]
                )
            ]
        )

    # APISIX Tests
    def test_apisix_circuit_breaker_basic(self):
        """Test APISIX api-breaker plugin with basic configuration"""
        provider = APISIXProvider()
        cb = CircuitBreakerConfig(
            enabled=True,
            max_failures=5,
            timeout="30s",
            half_open_requests=3
        )
        config = self._create_config_with_circuit_breaker("apisix", cb)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert "api-breaker" in route["plugins"]
        assert route["plugins"]["api-breaker"]["max_breaker_sec"] == 30
        assert route["plugins"]["api-breaker"]["unhealthy"]["failures"] == 5
        assert route["plugins"]["api-breaker"]["healthy"]["successes"] == 3

    def test_apisix_circuit_breaker_unhealthy_codes(self):
        """Test APISIX circuit breaker with custom unhealthy status codes"""
        provider = APISIXProvider()
        cb = CircuitBreakerConfig(
            enabled=True,
            unhealthy_status_codes=[500, 502, 503, 504]
        )
        config = self._create_config_with_circuit_breaker("apisix", cb)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert route["plugins"]["api-breaker"]["unhealthy"]["http_statuses"] == [500, 502, 503, 504]

    def test_apisix_circuit_breaker_healthy_codes(self):
        """Test APISIX circuit breaker with custom healthy status codes"""
        provider = APISIXProvider()
        cb = CircuitBreakerConfig(
            enabled=True,
            healthy_status_codes=[200, 201, 204]
        )
        config = self._create_config_with_circuit_breaker("apisix", cb)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert route["plugins"]["api-breaker"]["healthy"]["http_statuses"] == [200, 201, 204]

    def test_apisix_circuit_breaker_response_code(self):
        """Test APISIX circuit breaker with custom failure response code"""
        provider = APISIXProvider()
        cb = CircuitBreakerConfig(
            enabled=True,
            failure_response_code=503
        )
        config = self._create_config_with_circuit_breaker("apisix", cb)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        assert route["plugins"]["api-breaker"]["break_response_code"] == 503

    # Traefik Tests
    def test_traefik_circuit_breaker_basic(self):
        """Test Traefik CircuitBreaker middleware with expression"""
        provider = TraefikProvider()
        cb = CircuitBreakerConfig(
            enabled=True,
            max_failures=5,
            unhealthy_status_codes=[500, 502, 503, 504]
        )
        config = self._create_config_with_circuit_breaker("traefik", cb)
        result = provider.generate(config)

        assert "api_service_router_0_circuitbreaker:" in result
        assert "circuitBreaker:" in result
        assert "expression:" in result
        assert "ResponseCodeRatio" in result

    def test_traefik_circuit_breaker_expression_format(self):
        """Test Traefik circuit breaker expression format"""
        provider = TraefikProvider()
        cb = CircuitBreakerConfig(
            enabled=True,
            max_failures=5,
            unhealthy_status_codes=[500, 505]
        )
        config = self._create_config_with_circuit_breaker("traefik", cb)
        result = provider.generate(config)

        # Should generate expression with min=500, max=506 (505+1)
        assert "ResponseCodeRatio(500, 506" in result
        # Should calculate ratio from max_failures (5/10 = 0.5)
        assert "0.50" in result

    def test_traefik_circuit_breaker_network_error_fallback(self):
        """Test Traefik circuit breaker NetworkErrorRatio fallback"""
        provider = TraefikProvider()
        cb = CircuitBreakerConfig(
            enabled=True,
            max_failures=3,
            unhealthy_status_codes=[]  # Empty list triggers fallback
        )
        config = self._create_config_with_circuit_breaker("traefik", cb)
        result = provider.generate(config)

        assert "NetworkErrorRatio" in result
        assert "0.30" in result  # 3/10 = 0.3

    def test_traefik_circuit_breaker_middleware_reference(self):
        """Test Traefik circuit breaker middleware is referenced in router"""
        provider = TraefikProvider()
        cb = CircuitBreakerConfig(enabled=True)
        config = self._create_config_with_circuit_breaker("traefik", cb)
        result = provider.generate(config)

        # Check that router references the middleware
        assert "api_service_router_0:" in result
        assert "middlewares:" in result
        assert "- api_service_router_0_circuitbreaker" in result

    # Envoy Tests
    def test_envoy_circuit_breaker_basic(self):
        """Test Envoy outlier detection for circuit breaker"""
        provider = EnvoyProvider()
        cb = CircuitBreakerConfig(
            enabled=True,
            max_failures=5,
            timeout="30s",
            half_open_requests=3
        )
        config = self._create_config_with_circuit_breaker("envoy", cb)
        result = provider.generate(config)

        assert "outlier_detection:" in result
        assert "consecutive_5xx: 5" in result
        assert "base_ejection_time: 30s" in result
        assert "success_rate_minimum_hosts: 3" in result

    def test_envoy_circuit_breaker_consecutive_errors(self):
        """Test Envoy consecutive_5xx configuration"""
        provider = EnvoyProvider()
        cb = CircuitBreakerConfig(
            enabled=True,
            max_failures=10
        )
        config = self._create_config_with_circuit_breaker("envoy", cb)
        result = provider.generate(config)

        assert "consecutive_5xx: 10" in result

    def test_envoy_circuit_breaker_ejection_time(self):
        """Test Envoy base ejection time configuration"""
        provider = EnvoyProvider()
        cb = CircuitBreakerConfig(
            enabled=True,
            timeout="60s"
        )
        config = self._create_config_with_circuit_breaker("envoy", cb)
        result = provider.generate(config)

        assert "base_ejection_time: 60s" in result

    def test_envoy_circuit_breaker_enforcement(self):
        """Test Envoy enforcement configuration"""
        provider = EnvoyProvider()
        cb = CircuitBreakerConfig(enabled=True)
        config = self._create_config_with_circuit_breaker("envoy", cb)
        result = provider.generate(config)

        assert "enforcing_consecutive_5xx: 100" in result
        assert "enforcing_success_rate: 100" in result
        assert "max_ejection_percent: 50" in result

    def test_envoy_circuit_breaker_interval(self):
        """Test Envoy outlier detection interval"""
        provider = EnvoyProvider()
        cb = CircuitBreakerConfig(enabled=True)
        config = self._create_config_with_circuit_breaker("envoy", cb)
        result = provider.generate(config)

        assert "interval: 10s" in result

    # Kong Tests
    def test_kong_circuit_breaker_warning(self, caplog):
        """Test Kong logs warning when circuit breaker is configured"""
        import logging
        caplog.set_level(logging.WARNING)

        provider = KongProvider()
        cb = CircuitBreakerConfig(enabled=True)
        config = self._create_config_with_circuit_breaker("kong", cb)
        result = provider.generate(config)

        # Should log warning about lack of native support
        assert any("circuit breaker" in record.message.lower() for record in caplog.records)
        assert any("native" in record.message.lower() for record in caplog.records)

    def test_kong_circuit_breaker_no_plugin(self):
        """Test Kong does not add circuit breaker plugin"""
        provider = KongProvider()
        cb = CircuitBreakerConfig(enabled=True)
        config = self._create_config_with_circuit_breaker("kong", cb)
        result = provider.generate(config)

        # Should not have circuit-breaker plugin in output
        assert "circuit-breaker" not in result.lower()
        # Should not have any outlier detection or similar
        assert "outlier" not in result.lower()

    # Disabled Circuit Breaker Tests
    def test_circuit_breaker_disabled_apisix(self):
        """Test that disabled circuit breaker is not generated for APISIX"""
        provider = APISIXProvider()
        cb = CircuitBreakerConfig(enabled=False)
        config = self._create_config_with_circuit_breaker("apisix", cb)
        result = provider.generate(config)
        config_json = json.loads(result)

        route = config_json["routes"][0]
        # Circuit breaker plugin should not be present when disabled
        assert "api-breaker" not in route.get("plugins", {})

    def test_circuit_breaker_disabled_traefik(self):
        """Test that disabled circuit breaker is not generated for Traefik"""
        provider = TraefikProvider()
        cb = CircuitBreakerConfig(enabled=False)
        config = self._create_config_with_circuit_breaker("traefik", cb)
        result = provider.generate(config)

        # Circuit breaker middleware should not be present
        assert "api_service_router_0_circuitbreaker:" not in result
        # Should not have circuitBreaker config
        lines = result.split('\n')
        assert not any("circuitBreaker:" in line for line in lines)

    def test_circuit_breaker_disabled_envoy(self):
        """Test that disabled circuit breaker is not generated for Envoy"""
        provider = EnvoyProvider()
        cb = CircuitBreakerConfig(enabled=False)
        config = self._create_config_with_circuit_breaker("envoy", cb)
        result = provider.generate(config)

        # Outlier detection should not be present
        assert "outlier_detection:" not in result

    def test_circuit_breaker_disabled_kong(self, caplog):
        """Test Kong does not log warning when circuit breaker is disabled"""
        import logging
        caplog.set_level(logging.WARNING)

        provider = KongProvider()
        cb = CircuitBreakerConfig(enabled=False)
        config = self._create_config_with_circuit_breaker("kong", cb)
        result = provider.generate(config)

        # Should not log warning when disabled
        circuit_breaker_warnings = [
            record for record in caplog.records
            if "circuit breaker" in record.message.lower()
        ]
        assert len(circuit_breaker_warnings) == 0

    # Multiple Services Test
    def test_circuit_breaker_multiple_services(self):
        """Test circuit breaker with multiple services"""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="service1",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="svc1.local", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api/v1",
                            circuit_breaker=CircuitBreakerConfig(
                                enabled=True,
                                max_failures=3
                            )
                        )
                    ]
                ),
                Service(
                    name="service2",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="svc2.local", port=8081),
                    routes=[
                        Route(
                            path_prefix="/api/v2",
                            circuit_breaker=CircuitBreakerConfig(
                                enabled=True,
                                max_failures=7
                            )
                        )
                    ]
                )
            ]
        )

        provider = EnvoyProvider()
        result = provider.generate(config)

        # Both services should have outlier detection
        assert result.count("outlier_detection:") == 2
        # With different configurations
        assert "consecutive_5xx: 3" in result
        assert "consecutive_5xx: 7" in result
