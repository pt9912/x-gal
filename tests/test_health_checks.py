"""
Tests for Health Checks and Load Balancing implementation.

Tests health checks and load balancing functionality across all providers:
- APISIX: Native health checks with active/passive support
- Kong: Upstream health checks with targets
- Traefik: LoadBalancer healthCheck configuration
- Envoy: health_checks and outlier_detection
"""

import json
import pytest
from gal.config import (
    Config, Service, Route, Upstream, GlobalConfig,
    UpstreamTarget, ActiveHealthCheck, PassiveHealthCheck,
    HealthCheckConfig, LoadBalancerConfig
)
from gal.providers.kong import KongProvider
from gal.providers.apisix import APISIXProvider
from gal.providers.traefik import TraefikProvider
from gal.providers.envoy import EnvoyProvider


class TestHealthChecks:
    """Test Health Checks for all providers"""

    def _create_config_with_health_checks(self, provider_name: str, health_check: HealthCheckConfig):
        """Helper to create test config with health checks"""
        return Config(
            version="1.0",
            provider=provider_name,
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        host="api.local",
                        port=8080,
                        health_check=health_check
                    ),
                    routes=[
                        Route(
                            path_prefix="/api/v1",
                            methods=["GET", "POST"]
                        )
                    ]
                )
            ]
        )

    def _create_config_with_load_balancing(self, provider_name: str, targets: list, lb_config: LoadBalancerConfig):
        """Helper to create test config with load balancing"""
        return Config(
            version="1.0",
            provider=provider_name,
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=targets,
                        load_balancer=lb_config
                    ),
                    routes=[
                        Route(
                            path_prefix="/api/v1",
                            methods=["GET", "POST"]
                        )
                    ]
                )
            ]
        )

    # APISIX Tests
    def test_apisix_active_health_check(self):
        """Test APISIX active health check configuration"""
        provider = APISIXProvider()
        hc = HealthCheckConfig(
            active=ActiveHealthCheck(
                enabled=True,
                http_path="/health",
                interval="10s",
                timeout="5s",
                healthy_threshold=2,
                unhealthy_threshold=3
            )
        )
        config = self._create_config_with_health_checks("apisix", hc)
        result = provider.generate(config)
        config_json = json.loads(result)

        upstream = config_json["upstreams"][0]
        assert "checks" in upstream
        assert "active" in upstream["checks"]
        assert upstream["checks"]["active"]["http_path"] == "/health"
        assert upstream["checks"]["active"]["timeout"] == 5
        assert upstream["checks"]["active"]["healthy"]["interval"] == 10
        assert upstream["checks"]["active"]["healthy"]["successes"] == 2
        assert upstream["checks"]["active"]["unhealthy"]["http_failures"] == 3

    def test_apisix_passive_health_check(self):
        """Test APISIX passive health check configuration"""
        provider = APISIXProvider()
        hc = HealthCheckConfig(
            passive=PassiveHealthCheck(
                enabled=True,
                max_failures=5,
                unhealthy_status_codes=[500, 502, 503, 504]
            )
        )
        config = self._create_config_with_health_checks("apisix", hc)
        result = provider.generate(config)
        config_json = json.loads(result)

        upstream = config_json["upstreams"][0]
        assert "checks" in upstream
        assert "passive" in upstream["checks"]
        assert upstream["checks"]["passive"]["unhealthy"]["http_failures"] == 5
        assert upstream["checks"]["passive"]["unhealthy"]["http_statuses"] == [500, 502, 503, 504]

    def test_apisix_combined_health_checks(self):
        """Test APISIX combined active and passive health checks"""
        provider = APISIXProvider()
        hc = HealthCheckConfig(
            active=ActiveHealthCheck(enabled=True, http_path="/health"),
            passive=PassiveHealthCheck(enabled=True, max_failures=3)
        )
        config = self._create_config_with_health_checks("apisix", hc)
        result = provider.generate(config)
        config_json = json.loads(result)

        upstream = config_json["upstreams"][0]
        assert "checks" in upstream
        assert "active" in upstream["checks"]
        assert "passive" in upstream["checks"]

    def test_apisix_load_balancing_round_robin(self):
        """Test APISIX round-robin load balancing"""
        provider = APISIXProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=1),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="round_robin")
        config = self._create_config_with_load_balancing("apisix", targets, lb_config)
        result = provider.generate(config)
        config_json = json.loads(result)

        upstream = config_json["upstreams"][0]
        assert upstream["type"] == "roundrobin"
        assert "api-1.local:8080" in upstream["nodes"]
        assert "api-2.local:8080" in upstream["nodes"]

    def test_apisix_load_balancing_weighted(self):
        """Test APISIX weighted load balancing"""
        provider = APISIXProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=2),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="weighted")
        config = self._create_config_with_load_balancing("apisix", targets, lb_config)
        result = provider.generate(config)
        config_json = json.loads(result)

        upstream = config_json["upstreams"][0]
        assert upstream["nodes"]["api-1.local:8080"] == 2
        assert upstream["nodes"]["api-2.local:8080"] == 1

    def test_apisix_load_balancing_least_conn(self):
        """Test APISIX least connections load balancing"""
        provider = APISIXProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=1),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="least_conn")
        config = self._create_config_with_load_balancing("apisix", targets, lb_config)
        result = provider.generate(config)
        config_json = json.loads(result)

        upstream = config_json["upstreams"][0]
        assert upstream["type"] == "least_conn"

    def test_apisix_load_balancing_ip_hash(self):
        """Test APISIX IP hash load balancing"""
        provider = APISIXProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=1),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="ip_hash")
        config = self._create_config_with_load_balancing("apisix", targets, lb_config)
        result = provider.generate(config)
        config_json = json.loads(result)

        upstream = config_json["upstreams"][0]
        assert upstream["type"] == "chash"
        assert upstream["hash_on"] == "vars"
        assert upstream["key"] == "remote_addr"

    # Kong Tests
    def test_kong_active_health_check(self):
        """Test Kong active health check configuration"""
        provider = KongProvider()
        hc = HealthCheckConfig(
            active=ActiveHealthCheck(
                enabled=True,
                http_path="/health",
                interval="10s",
                timeout="5s",
                healthy_threshold=2,
                unhealthy_threshold=3
            )
        )
        config = self._create_config_with_health_checks("kong", hc)
        result = provider.generate(config)

        assert "upstreams:" in result
        assert "healthchecks:" in result
        assert "active:" in result
        assert "http_path: /health" in result
        assert "interval: 10" in result
        assert "timeout: 5" in result
        assert "successes: 2" in result
        assert "http_failures: 3" in result

    def test_kong_passive_health_check(self):
        """Test Kong passive health check configuration"""
        provider = KongProvider()
        hc = HealthCheckConfig(
            passive=PassiveHealthCheck(
                enabled=True,
                max_failures=5,
                unhealthy_status_codes=[500, 502, 503, 504]
            )
        )
        config = self._create_config_with_health_checks("kong", hc)
        result = provider.generate(config)

        assert "passive:" in result
        assert "http_failures: 5" in result
        assert "[500, 502, 503, 504]" in result

    def test_kong_load_balancing_targets(self):
        """Test Kong load balancing with multiple targets"""
        provider = KongProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=2),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="round_robin")
        config = self._create_config_with_load_balancing("kong", targets, lb_config)
        result = provider.generate(config)

        assert "targets:" in result
        assert "target: api-1.local:8080" in result
        assert "weight: 200" in result  # Kong uses 0-1000 scale (2 * 100)
        assert "target: api-2.local:8080" in result
        assert "weight: 100" in result

    def test_kong_load_balancing_least_conn(self):
        """Test Kong least connections algorithm"""
        provider = KongProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=1),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="least_conn")
        config = self._create_config_with_load_balancing("kong", targets, lb_config)
        result = provider.generate(config)

        assert "algorithm: least-connections" in result

    def test_kong_load_balancing_ip_hash(self):
        """Test Kong consistent hashing (IP hash)"""
        provider = KongProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=1),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="ip_hash")
        config = self._create_config_with_load_balancing("kong", targets, lb_config)
        result = provider.generate(config)

        assert "algorithm: consistent-hashing" in result
        assert "hash_on: consumer" in result
        assert "hash_fallback: ip" in result

    # Traefik Tests
    def test_traefik_active_health_check(self):
        """Test Traefik health check configuration"""
        provider = TraefikProvider()
        hc = HealthCheckConfig(
            active=ActiveHealthCheck(
                enabled=True,
                http_path="/health",
                interval="10s",
                timeout="5s"
            )
        )
        config = self._create_config_with_health_checks("traefik", hc)
        result = provider.generate(config)

        assert "healthCheck:" in result
        assert "path: /health" in result
        assert "interval: 10s" in result
        assert "timeout: 5s" in result

    def test_traefik_load_balancing_servers(self):
        """Test Traefik multiple servers configuration"""
        provider = TraefikProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=1),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="round_robin")
        config = self._create_config_with_load_balancing("traefik", targets, lb_config)
        result = provider.generate(config)

        assert "servers:" in result
        assert "url: 'http://api-1.local:8080'" in result
        assert "url: 'http://api-2.local:8080'" in result

    def test_traefik_load_balancing_weighted(self):
        """Test Traefik weighted load balancing"""
        provider = TraefikProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=2),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="weighted")
        config = self._create_config_with_load_balancing("traefik", targets, lb_config)
        result = provider.generate(config)

        assert "weight: 2" in result
        assert "weight: 1" in result

    def test_traefik_sticky_sessions(self):
        """Test Traefik sticky sessions configuration"""
        provider = TraefikProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=1),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(
            algorithm="round_robin",
            sticky_sessions=True,
            cookie_name="mySessionCookie"
        )
        config = self._create_config_with_load_balancing("traefik", targets, lb_config)
        result = provider.generate(config)

        assert "sticky:" in result
        assert "cookie:" in result
        assert "name: mySessionCookie" in result
        assert "httpOnly: true" in result

    # Envoy Tests
    def test_envoy_active_health_check(self):
        """Test Envoy active health check configuration"""
        provider = EnvoyProvider()
        hc = HealthCheckConfig(
            active=ActiveHealthCheck(
                enabled=True,
                http_path="/health",
                interval="10s",
                timeout="5s",
                healthy_threshold=2,
                unhealthy_threshold=3,
                healthy_status_codes=[200, 201, 204]
            )
        )
        config = self._create_config_with_health_checks("envoy", hc)
        result = provider.generate(config)

        assert "health_checks:" in result
        assert "timeout: 5s" in result
        assert "interval: 10s" in result
        assert "unhealthy_threshold: 3" in result
        assert "healthy_threshold: 2" in result
        assert "path: /health" in result

    def test_envoy_passive_health_check(self):
        """Test Envoy passive health check (outlier detection)"""
        provider = EnvoyProvider()
        hc = HealthCheckConfig(
            passive=PassiveHealthCheck(
                enabled=True,
                max_failures=5,
                unhealthy_status_codes=[500, 502, 503, 504]
            )
        )
        config = self._create_config_with_health_checks("envoy", hc)
        result = provider.generate(config)

        assert "outlier_detection:" in result
        assert "consecutive_5xx: 5" in result

    def test_envoy_load_balancing_round_robin(self):
        """Test Envoy round-robin load balancing"""
        provider = EnvoyProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=1),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="round_robin")
        config = self._create_config_with_load_balancing("envoy", targets, lb_config)
        result = provider.generate(config)

        assert "lb_policy: ROUND_ROBIN" in result
        assert "address: api-1.local" in result
        assert "port_value: 8080" in result
        assert "address: api-2.local" in result

    def test_envoy_load_balancing_least_request(self):
        """Test Envoy least request (least connections) load balancing"""
        provider = EnvoyProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=1),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="least_conn")
        config = self._create_config_with_load_balancing("envoy", targets, lb_config)
        result = provider.generate(config)

        assert "lb_policy: LEAST_REQUEST" in result

    def test_envoy_load_balancing_ring_hash(self):
        """Test Envoy ring hash (IP hash) load balancing"""
        provider = EnvoyProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=1),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="ip_hash")
        config = self._create_config_with_load_balancing("envoy", targets, lb_config)
        result = provider.generate(config)

        assert "lb_policy: RING_HASH" in result
        assert "ring_hash_lb_config:" in result
        assert "minimum_ring_size: 1024" in result

    def test_envoy_load_balancing_weighted(self):
        """Test Envoy weighted load balancing"""
        provider = EnvoyProvider()
        targets = [
            UpstreamTarget(host="api-1.local", port=8080, weight=2),
            UpstreamTarget(host="api-2.local", port=8080, weight=1)
        ]
        lb_config = LoadBalancerConfig(algorithm="weighted")
        config = self._create_config_with_load_balancing("envoy", targets, lb_config)
        result = provider.generate(config)

        assert "load_balancing_weight:" in result
        assert "value: 2" in result
        assert "value: 1" in result


class TestConfigModels:
    """Test health check and load balancing config models"""

    def test_upstream_target_creation(self):
        """Test UpstreamTarget model creation"""
        target = UpstreamTarget(host="api.local", port=8080, weight=2)
        assert target.host == "api.local"
        assert target.port == 8080
        assert target.weight == 2

    def test_active_health_check_defaults(self):
        """Test ActiveHealthCheck default values"""
        hc = ActiveHealthCheck()
        assert hc.enabled is True
        assert hc.http_path == "/health"
        assert hc.interval == "10s"
        assert hc.timeout == "5s"
        assert hc.healthy_threshold == 2
        assert hc.unhealthy_threshold == 3
        assert hc.healthy_status_codes == [200, 201, 204]

    def test_passive_health_check_defaults(self):
        """Test PassiveHealthCheck default values"""
        hc = PassiveHealthCheck()
        assert hc.enabled is True
        assert hc.max_failures == 5
        assert hc.unhealthy_status_codes == [500, 502, 503, 504]

    def test_health_check_config_combined(self):
        """Test HealthCheckConfig with both active and passive"""
        hc = HealthCheckConfig(
            active=ActiveHealthCheck(http_path="/api/health"),
            passive=PassiveHealthCheck(max_failures=3)
        )
        assert hc.active.http_path == "/api/health"
        assert hc.passive.max_failures == 3

    def test_load_balancer_config_defaults(self):
        """Test LoadBalancerConfig default values"""
        lb = LoadBalancerConfig()
        assert lb.algorithm == "round_robin"
        assert lb.sticky_sessions is False
        assert lb.cookie_name == "galSession"

    def test_load_balancer_config_sticky_sessions(self):
        """Test LoadBalancerConfig with sticky sessions"""
        lb = LoadBalancerConfig(
            algorithm="round_robin",
            sticky_sessions=True,
            cookie_name="mySession"
        )
        assert lb.sticky_sessions is True
        assert lb.cookie_name == "mySession"

    def test_upstream_simple_mode(self):
        """Test Upstream in simple mode (single host/port)"""
        upstream = Upstream(host="api.local", port=8080)
        assert upstream.host == "api.local"
        assert upstream.port == 8080
        assert len(upstream.targets) == 0

    def test_upstream_targets_mode(self):
        """Test Upstream in targets mode (multiple servers)"""
        upstream = Upstream(
            targets=[
                UpstreamTarget(host="api-1.local", port=8080, weight=2),
                UpstreamTarget(host="api-2.local", port=8080, weight=1)
            ]
        )
        assert len(upstream.targets) == 2
        assert upstream.targets[0].weight == 2
        assert upstream.targets[1].weight == 1

    def test_upstream_with_health_checks_and_load_balancing(self):
        """Test Upstream with full health checks and load balancing config"""
        upstream = Upstream(
            targets=[
                UpstreamTarget(host="api-1.local", port=8080, weight=1),
                UpstreamTarget(host="api-2.local", port=8080, weight=1)
            ],
            health_check=HealthCheckConfig(
                active=ActiveHealthCheck(http_path="/health"),
                passive=PassiveHealthCheck(max_failures=3)
            ),
            load_balancer=LoadBalancerConfig(
                algorithm="least_conn",
                sticky_sessions=True
            )
        )
        assert len(upstream.targets) == 2
        assert upstream.health_check.active.http_path == "/health"
        assert upstream.health_check.passive.max_failures == 3
        assert upstream.load_balancer.algorithm == "least_conn"
        assert upstream.load_balancer.sticky_sessions is True
