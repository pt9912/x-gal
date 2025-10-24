"""
Tests for HAProxy Provider
"""

from gal.config import (
    ActiveHealthCheck,
    Config,
    CORSPolicy,
    GlobalConfig,
    HeaderManipulation,
    HealthCheckConfig,
    LoadBalancerConfig,
    RateLimitConfig,
    Route,
    Service,
    Upstream,
    UpstreamTarget,
)
from gal.providers.haproxy import HAProxyProvider


class TestHAProxyProvider:
    """Test HAProxy Provider"""

    def test_provider_name(self):
        """Test provider name is correct"""
        provider = HAProxyProvider()
        assert provider.name() == "haproxy"

    def test_basic_config(self):
        """Test basic configuration generation"""
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(host="0.0.0.0", port=80),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="test.local", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = HAProxyProvider()
        result = provider.generate(config)

        # Check global section
        assert "global" in result
        assert "maxconn" in result
        assert "daemon" in result

        # Check defaults section
        assert "defaults" in result
        assert "mode                    http" in result
        assert "timeout client" in result

        # Check frontend
        assert "frontend http_frontend" in result
        assert "bind 0.0.0.0:80" in result

        # Check backend
        assert "backend backend_test_service" in result
        assert "server server1 test.local:8080" in result

        # Check ACL routing
        assert "acl is_test_service_route0 path_beg /api" in result
        assert "use_backend backend_test_service if is_test_service_route0" in result

    def test_load_balancing_roundrobin(self):
        """Test round-robin load balancing"""
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[
                            UpstreamTarget(host="api-1.local", port=8080),
                            UpstreamTarget(host="api-2.local", port=8080),
                        ],
                        load_balancer=LoadBalancerConfig(algorithm="round_robin"),
                    ),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = HAProxyProvider()
        result = provider.generate(config)

        assert "backend backend_api" in result
        assert "balance roundrobin" in result
        assert "server server1 api-1.local:8080" in result
        assert "server server2 api-2.local:8080" in result

    def test_load_balancing_leastconn(self):
        """Test least connections load balancing"""
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[
                            UpstreamTarget(host="api-1.local", port=8080),
                            UpstreamTarget(host="api-2.local", port=8080),
                        ],
                        load_balancer=LoadBalancerConfig(algorithm="least_conn"),
                    ),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = HAProxyProvider()
        result = provider.generate(config)

        assert "backend backend_api" in result
        assert "balance leastconn" in result

    def test_load_balancing_weighted(self):
        """Test weighted load balancing"""
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[
                            UpstreamTarget(host="api-1.local", port=8080, weight=3),
                            UpstreamTarget(host="api-2.local", port=8080, weight=1),
                        ],
                        load_balancer=LoadBalancerConfig(algorithm="weighted"),
                    ),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = HAProxyProvider()
        result = provider.generate(config)

        assert "backend backend_api" in result
        assert "balance roundrobin" in result
        assert "weight 3" in result
        # weight 1 is default and not shown
        assert "server server2 api-2.local:8080" in result

    def test_active_health_checks(self):
        """Test active health checks"""
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="api-1.local", port=8080)],
                        health_check=HealthCheckConfig(
                            active=ActiveHealthCheck(
                                enabled=True,
                                http_path="/health",
                                interval="5s",
                                timeout="3s",
                                healthy_threshold=2,
                                unhealthy_threshold=3,
                                healthy_status_codes=[200, 204],
                            )
                        ),
                    ),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = HAProxyProvider()
        result = provider.generate(config)

        assert "backend backend_api" in result
        assert "option httpchk GET /health HTTP/1.1" in result
        assert "http-check expect status 200|204" in result
        assert "check inter 5s fall 3 rise 2" in result

    def test_rate_limiting_ip_based(self):
        """Test IP-based rate limiting"""
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.local", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api",
                            rate_limit=RateLimitConfig(
                                enabled=True,
                                requests_per_second=100,
                                burst=200,
                                key_type="ip_address",
                                response_status=429,
                            ),
                        )
                    ],
                )
            ],
        )

        provider = HAProxyProvider()
        result = provider.generate(config)

        assert "frontend http_frontend" in result
        assert "stick-table type ip" in result
        assert "http-request track-sc0 src if is_api_route0" in result
        assert (
            "http-request deny deny_status 429 if is_api_route0 { sc_http_req_rate(0) gt 100 }"
            in result
        )

    def test_request_headers(self):
        """Test request header manipulation"""
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.local", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api",
                            headers=HeaderManipulation(
                                request_add={"X-Request-ID": "{{uuid}}", "X-Gateway": "GAL"},
                                request_set={"User-Agent": "GAL/1.0"},
                                request_remove=["X-Internal"],
                            ),
                        )
                    ],
                )
            ],
        )

        provider = HAProxyProvider()
        result = provider.generate(config)

        assert 'http-request set-header X-Request-ID "%[uuid()]" if is_api_route0' in result
        assert 'http-request set-header X-Gateway "GAL" if is_api_route0' in result
        assert 'http-request set-header User-Agent "GAL/1.0" if is_api_route0' in result
        assert "http-request del-header X-Internal if is_api_route0" in result

    def test_cors_config(self):
        """Test CORS configuration"""
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.local", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api",
                            cors=CORSPolicy(
                                enabled=True,
                                allowed_origins=["https://app.example.com"],
                                allowed_methods=["GET", "POST", "PUT", "DELETE"],
                                allowed_headers=["Content-Type", "Authorization"],
                                allow_credentials=True,
                                max_age=86400,
                            ),
                        )
                    ],
                )
            ],
        )

        provider = HAProxyProvider()
        result = provider.generate(config)

        assert (
            'http-response set-header Access-Control-Allow-Origin "https://app.example.com" if is_api_route0'
            in result
        )
        assert (
            'http-response set-header Access-Control-Allow-Methods "GET, POST, PUT, DELETE" if is_api_route0'
            in result
        )
        assert (
            'http-response set-header Access-Control-Allow-Headers "Content-Type, Authorization" if is_api_route0'
            in result
        )
        assert (
            'http-response set-header Access-Control-Allow-Credentials "true" if is_api_route0'
            in result
        )
        assert 'http-response set-header Access-Control-Max-Age "86400" if is_api_route0' in result

    def test_sticky_sessions(self):
        """Test sticky sessions with cookie"""
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[
                            UpstreamTarget(host="api-1.local", port=8080),
                            UpstreamTarget(host="api-2.local", port=8080),
                        ],
                        load_balancer=LoadBalancerConfig(
                            algorithm="round_robin", sticky_sessions=True, cookie_name="GALID"
                        ),
                    ),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = HAProxyProvider()
        result = provider.generate(config)

        assert "backend backend_api" in result
        assert "cookie GALID insert indirect nocache" in result
        assert "cookie server1" in result
        assert "cookie server2" in result
