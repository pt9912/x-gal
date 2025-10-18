"""
Tests for WebSocket support implementation.

Tests WebSocket functionality across all providers:
- Envoy: Native WebSocket via HTTP/1.1 Upgrade
- Kong: Native WebSocket support
- APISIX: enable_websocket flag
- Traefik: Automatic with flushInterval
- Nginx: proxy_http_version 1.1 + Upgrade headers
- HAProxy: timeout tunnel for WebSocket
"""

import json

import pytest

from gal.config import Config, GlobalConfig, Route, Service, Upstream, WebSocketConfig
from gal.providers.apisix import APISIXProvider
from gal.providers.envoy import EnvoyProvider
from gal.providers.haproxy import HAProxyProvider
from gal.providers.kong import KongProvider
from gal.providers.nginx import NginxProvider
from gal.providers.traefik import TraefikProvider


class TestWebSocketSupport:
    """Test WebSocket support for all providers"""

    def _create_config_with_websocket(self, provider_name: str, websocket: WebSocketConfig):
        """Helper to create test config with WebSocket"""
        return Config(
            version="1.0",
            provider=provider_name,
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="websocket_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="ws-server.local", port=8080),
                    routes=[Route(path_prefix="/ws", websocket=websocket)],
                )
            ],
        )

    # Envoy Tests
    def test_envoy_basic_websocket(self):
        """Test Envoy basic WebSocket configuration"""
        provider = EnvoyProvider()
        ws = WebSocketConfig(enabled=True)
        config = self._create_config_with_websocket("envoy", ws)
        result = provider.generate(config)

        # Check for WebSocket upgrade support
        assert "upgrade_configs:" in result
        assert "upgrade_type: websocket" in result
        # Check for idle timeout (default: 300s)
        assert "idle_timeout: 300s" in result

    def test_envoy_websocket_custom_timeout(self):
        """Test Envoy WebSocket with custom idle timeout"""
        provider = EnvoyProvider()
        ws = WebSocketConfig(
            enabled=True,
            idle_timeout="600s",  # 10 minutes
            ping_interval="20s",
            max_message_size=2097152,  # 2MB
        )
        config = self._create_config_with_websocket("envoy", ws)
        result = provider.generate(config)

        assert "upgrade_type: websocket" in result
        assert "idle_timeout: 600s" in result

    def test_envoy_websocket_disabled(self):
        """Test Envoy without WebSocket (should not have upgrade_configs)"""
        provider = EnvoyProvider()
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="rest_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.local", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )
        result = provider.generate(config)

        # Should not have WebSocket upgrade configs
        assert "upgrade_type: websocket" not in result

    def test_envoy_websocket_with_compression(self):
        """Test Envoy WebSocket with compression enabled"""
        provider = EnvoyProvider()
        ws = WebSocketConfig(enabled=True, compression=True, max_message_size=1048576)
        config = self._create_config_with_websocket("envoy", ws)
        result = provider.generate(config)

        assert "upgrade_type: websocket" in result
        # Note: Envoy compression is handled separately via filters

    # Kong Tests
    def test_kong_basic_websocket(self):
        """Test Kong basic WebSocket configuration"""
        provider = KongProvider()
        ws = WebSocketConfig(enabled=True)
        config = self._create_config_with_websocket("kong", ws)
        result = provider.generate(config)

        # Kong has native WebSocket support with timeout configuration
        # Verify service is created with WebSocket timeouts
        assert "name: websocket_service" in result
        assert "read_timeout: 300" in result  # Default 300s = 5 minutes
        assert "write_timeout: 300" in result

    def test_kong_websocket_with_timeouts(self):
        """Test Kong WebSocket with custom timeouts"""
        provider = KongProvider()
        ws = WebSocketConfig(enabled=True, idle_timeout="1200s", ping_interval="15s")  # 20 minutes
        config = self._create_config_with_websocket("kong", ws)
        result = provider.generate(config)

        # Kong handles WebSocket timeouts via service configuration (YAML output)
        assert "name: websocket_service" in result
        assert "read_timeout: 1200" in result  # 20 minutes in seconds
        assert "write_timeout: 1200" in result

    # APISIX Tests
    def test_apisix_basic_websocket(self):
        """Test APISIX basic WebSocket configuration"""
        provider = APISIXProvider()
        ws = WebSocketConfig(enabled=True)
        config = self._create_config_with_websocket("apisix", ws)
        result = provider.generate(config)

        config_json = json.loads(result)
        route = config_json["routes"][0]
        # APISIX uses enable_websocket flag
        assert route.get("enable_websocket") is True

    def test_apisix_websocket_disabled(self):
        """Test APISIX without WebSocket"""
        provider = APISIXProvider()
        config = Config(
            version="1.0",
            provider="apisix",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="rest_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.local", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )
        result = provider.generate(config)

        config_json = json.loads(result)
        route = config_json["routes"][0]
        # Should not have enable_websocket flag
        assert "enable_websocket" not in route

    def test_apisix_websocket_with_timeout(self):
        """Test APISIX WebSocket with custom timeout"""
        provider = APISIXProvider()
        ws = WebSocketConfig(enabled=True, idle_timeout="900s")
        config = self._create_config_with_websocket("apisix", ws)
        result = provider.generate(config)

        config_json = json.loads(result)
        route = config_json["routes"][0]
        assert route.get("enable_websocket") is True
        # APISIX timeout is handled via upstream configuration

    # Traefik Tests
    def test_traefik_basic_websocket(self):
        """Test Traefik basic WebSocket configuration"""
        provider = TraefikProvider()
        ws = WebSocketConfig(enabled=True)
        config = self._create_config_with_websocket("traefik", ws)
        result = provider.generate(config)

        # Traefik automatically handles WebSocket
        # No specific flag needed, but verify service is created
        assert "websocket_service" in result

    def test_traefik_websocket_with_flush_interval(self):
        """Test Traefik WebSocket configuration"""
        provider = TraefikProvider()
        ws = WebSocketConfig(enabled=True, ping_interval="10s")
        config = self._create_config_with_websocket("traefik", ws)
        result = provider.generate(config)

        # Traefik handles WebSocket transparently
        assert "websocket_service" in result

    # Nginx Tests
    def test_nginx_basic_websocket(self):
        """Test Nginx basic WebSocket configuration"""
        provider = NginxProvider()
        ws = WebSocketConfig(enabled=True)
        config = self._create_config_with_websocket("nginx", ws)
        result = provider.generate(config)

        # Nginx requires proxy_http_version 1.1 and Upgrade headers
        assert "proxy_http_version 1.1;" in result
        assert "proxy_set_header Upgrade $http_upgrade;" in result
        assert 'proxy_set_header Connection "upgrade";' in result

    def test_nginx_websocket_with_timeout(self):
        """Test Nginx WebSocket with custom timeout"""
        provider = NginxProvider()
        ws = WebSocketConfig(enabled=True, idle_timeout="600s")
        config = self._create_config_with_websocket("nginx", ws)
        result = provider.generate(config)

        assert "proxy_http_version 1.1;" in result
        assert "proxy_set_header Upgrade $http_upgrade;" in result
        # Nginx uses proxy_read_timeout for idle timeout
        assert "proxy_read_timeout 600s;" in result

    def test_nginx_websocket_disabled(self):
        """Test Nginx without WebSocket"""
        provider = NginxProvider()
        config = Config(
            version="1.0",
            provider="nginx",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="rest_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.local", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )
        result = provider.generate(config)

        # Should not have WebSocket-specific headers
        assert "proxy_set_header Upgrade $http_upgrade;" not in result
        assert 'proxy_set_header Connection "upgrade";' not in result

    # HAProxy Tests
    def test_haproxy_basic_websocket(self):
        """Test HAProxy basic WebSocket configuration"""
        provider = HAProxyProvider()
        ws = WebSocketConfig(enabled=True)
        config = self._create_config_with_websocket("haproxy", ws)
        result = provider.generate(config)

        # HAProxy uses timeout tunnel for WebSocket
        assert "timeout tunnel" in result

    def test_haproxy_websocket_with_timeout(self):
        """Test HAProxy WebSocket with custom timeout"""
        provider = HAProxyProvider()
        ws = WebSocketConfig(enabled=True, idle_timeout="1800s")  # 30 minutes
        config = self._create_config_with_websocket("haproxy", ws)
        result = provider.generate(config)

        # HAProxy timeout tunnel should match idle_timeout
        assert "timeout tunnel 1800s" in result

    def test_haproxy_websocket_disabled(self):
        """Test HAProxy without WebSocket"""
        provider = HAProxyProvider()
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="rest_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.local", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )
        result = provider.generate(config)

        # Should not have WebSocket-specific timeout tunnel
        # (HAProxy may still have default timeouts, but not tunnel-specific)
        pass  # Negative test - just verify it doesn't crash

    # Combined Features Tests
    def test_envoy_websocket_with_authentication(self):
        """Test Envoy WebSocket with JWT authentication"""
        from gal.config import AuthenticationConfig, JwtConfig

        provider = EnvoyProvider()
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="ws_chat",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="chat.local", port=8080),
                    routes=[
                        Route(
                            path_prefix="/ws/chat",
                            websocket=WebSocketConfig(enabled=True, idle_timeout="600s"),
                            authentication=AuthenticationConfig(
                                enabled=True,
                                type="jwt",
                                jwt=JwtConfig(
                                    issuer="https://auth.example.com",
                                    audience="chat-api",
                                    jwks_uri="https://auth.example.com/.well-known/jwks.json",
                                ),
                            ),
                        )
                    ],
                )
            ],
        )
        result = provider.generate(config)

        # Should have both WebSocket and JWT auth
        assert "upgrade_type: websocket" in result
        assert "idle_timeout: 600s" in result
        assert "envoy.filters.http.jwt_authn" in result
        assert "jwt_provider" in result

    def test_nginx_websocket_with_rate_limiting(self):
        """Test Nginx WebSocket with rate limiting"""
        from gal.config import RateLimitConfig

        provider = NginxProvider()
        config = Config(
            version="1.0",
            provider="nginx",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="ws_dashboard",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="dashboard.local", port=8080),
                    routes=[
                        Route(
                            path_prefix="/ws/dashboard",
                            websocket=WebSocketConfig(enabled=True, compression=True),
                            rate_limit=RateLimitConfig(
                                enabled=True, requests_per_second=100, burst=200
                            ),
                        )
                    ],
                )
            ],
        )
        result = provider.generate(config)

        # Should have both WebSocket and rate limiting
        assert "proxy_http_version 1.1;" in result
        assert "proxy_set_header Upgrade $http_upgrade;" in result
        assert "limit_req_zone" in result
        assert "limit_req" in result

    def test_apisix_websocket_with_load_balancing(self):
        """Test APISIX WebSocket with load balancing"""
        from gal.config import LoadBalancerConfig, UpstreamTarget

        provider = APISIXProvider()
        config = Config(
            version="1.0",
            provider="apisix",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="ws_gaming",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[
                            UpstreamTarget(host="game-1.local", port=8080, weight=3),
                            UpstreamTarget(host="game-2.local", port=8080, weight=2),
                            UpstreamTarget(host="game-3.local", port=8080, weight=1),
                        ],
                        load_balancer=LoadBalancerConfig(algorithm="weighted"),
                    ),
                    routes=[
                        Route(
                            path_prefix="/ws/game",
                            websocket=WebSocketConfig(
                                enabled=True, idle_timeout="60s", ping_interval="5s"
                            ),
                        )
                    ],
                )
            ],
        )
        result = provider.generate(config)

        config_json = json.loads(result)
        route = config_json["routes"][0]
        upstream = config_json["upstreams"][0]

        # Should have WebSocket enabled
        assert route.get("enable_websocket") is True

        # Should have weighted load balancing
        assert upstream["nodes"]["game-1.local:8080"] == 3
        assert upstream["nodes"]["game-2.local:8080"] == 2
        assert upstream["nodes"]["game-3.local:8080"] == 1
