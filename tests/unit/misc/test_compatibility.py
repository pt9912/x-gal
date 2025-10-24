"""Tests for compatibility checking functionality."""

import pytest

from gal.compatibility import (
    CompatibilityChecker,
    CompatibilityReport,
    FeatureCheck,
    FeatureSupport,
)
from gal.config import (
    ActiveHealthCheck,
    ApiKeyConfig,
    AuthenticationConfig,
    BasicAuthConfig,
    CircuitBreakerConfig,
    Config,
    CORSPolicy,
    GlobalConfig,
    HealthCheckConfig,
    JwtConfig,
    LoadBalancerConfig,
    PassiveHealthCheck,
    RateLimitConfig,
    Route,
    Service,
    Upstream,
)


class TestFeatureSupport:
    """Tests for FeatureSupport enum."""

    def test_feature_support_values(self):
        """Test FeatureSupport enum values."""
        assert FeatureSupport.FULL.value == "full"
        assert FeatureSupport.PARTIAL.value == "partial"
        assert FeatureSupport.UNSUPPORTED.value == "unsupported"


class TestFeatureCheck:
    """Tests for FeatureCheck dataclass."""

    def test_feature_check_creation(self):
        """Test creating a FeatureCheck."""
        check = FeatureCheck(
            feature_name="rate_limiting",
            support=FeatureSupport.FULL,
            message="✅ Rate Limiting fully supported",
            recommendation="",
        )
        assert check.feature_name == "rate_limiting"
        assert check.support == FeatureSupport.FULL
        assert check.message == "✅ Rate Limiting fully supported"
        assert check.recommendation == ""

    def test_feature_check_defaults(self):
        """Test FeatureCheck with default values."""
        check = FeatureCheck(feature_name="test_feature", support=FeatureSupport.UNSUPPORTED)
        assert check.message == ""
        assert check.recommendation == ""


class TestCompatibilityReport:
    """Tests for CompatibilityReport dataclass."""

    def test_compatibility_report_creation(self):
        """Test creating a CompatibilityReport."""
        report = CompatibilityReport(
            provider="envoy",
            compatible=True,
            compatibility_score=1.0,
            features_checked=5,
            features_supported=[
                FeatureCheck("feature1", FeatureSupport.FULL),
                FeatureCheck("feature2", FeatureSupport.FULL),
            ],
            features_partial=[],
            features_unsupported=[],
            warnings=[],
            recommendations=[],
        )
        assert report.provider == "envoy"
        assert report.compatible is True
        assert report.compatibility_score == 1.0
        assert report.features_checked == 5
        assert len(report.features_supported) == 2
        assert len(report.features_partial) == 0
        assert len(report.features_unsupported) == 0


class TestCompatibilityChecker:
    """Tests for CompatibilityChecker class."""

    @pytest.fixture
    def checker(self):
        """Create a CompatibilityChecker instance."""
        return CompatibilityChecker()

    @pytest.fixture
    def simple_config(self):
        """Create a simple GAL config for testing."""
        return Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        host="backend.internal",
                        port=8080,
                    ),
                    routes=[
                        Route(
                            path_prefix="/api/test",
                            methods=["GET", "POST"],
                        )
                    ],
                )
            ],
        )

    @pytest.fixture
    def complex_config(self):
        """Create a complex GAL config with many features."""
        return Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        host="api.internal",
                        port=8080,
                        load_balancer=LoadBalancerConfig(
                            algorithm="round_robin",
                            sticky_sessions=True,
                        ),
                        health_check=HealthCheckConfig(
                            active=ActiveHealthCheck(
                                enabled=True,
                                http_path="/health",
                                interval=10,
                                timeout=5,
                                healthy_threshold=2,
                                unhealthy_threshold=3,
                            ),
                            passive=PassiveHealthCheck(
                                enabled=True,
                                max_failures=5,
                            ),
                        ),
                    ),
                    routes=[
                        Route(
                            path_prefix="/api/v1",
                            methods=["GET", "POST"],
                            rate_limit=RateLimitConfig(
                                enabled=True,
                                requests_per_second=100,
                                burst=200,
                            ),
                            authentication=AuthenticationConfig(
                                enabled=True,
                                type="jwt",
                                jwt=JwtConfig(
                                    issuer="https://auth.example.com",
                                    audience="api.example.com",
                                ),
                            ),
                            cors=CORSPolicy(
                                enabled=True,
                                allowed_origins=["*"],
                            ),
                            circuit_breaker=CircuitBreakerConfig(
                                enabled=True,
                                max_failures=5,
                            ),
                        )
                    ],
                )
            ],
        )

    def test_extract_features_simple(self, checker, simple_config):
        """Test feature extraction from simple config."""
        features = checker._extract_features_from_config(simple_config)
        assert "routing_path_prefix" in features
        assert "http_methods" in features
        assert len(features) == 2

    def test_extract_features_complex(self, checker, complex_config):
        """Test feature extraction from complex config."""
        features = checker._extract_features_from_config(complex_config)
        assert "routing_path_prefix" in features
        assert "http_methods" in features
        assert "rate_limiting" in features
        assert "authentication_jwt" in features
        assert "cors" in features
        assert "circuit_breaker" in features
        assert "load_balancing_round_robin" in features
        assert "sticky_sessions" in features
        assert "health_check_active" in features
        assert "health_check_passive" in features

    def test_get_feature_support_envoy(self, checker):
        """Test getting feature support for Envoy."""
        support = checker._get_feature_support("routing_path_prefix", "envoy")
        assert support == FeatureSupport.FULL

        # Envoy OSS rate limiting is partial (global only)
        support = checker._get_feature_support("rate_limiting", "envoy")
        assert support == FeatureSupport.PARTIAL

    def test_get_feature_support_traefik(self, checker):
        """Test getting feature support for Traefik."""
        # Traefik doesn't support active health checks
        support = checker._get_feature_support("health_check_active", "traefik")
        assert support == FeatureSupport.UNSUPPORTED

        # Traefik partially supports IP hash
        support = checker._get_feature_support("load_balancing_ip_hash", "traefik")
        assert support == FeatureSupport.PARTIAL

    def test_get_feature_support_nginx(self, checker):
        """Test getting feature support for Nginx."""
        # Nginx doesn't support active health checks (OSS)
        support = checker._get_feature_support("health_check_active", "nginx")
        assert support == FeatureSupport.UNSUPPORTED

        # Nginx supports rate limiting
        support = checker._get_feature_support("rate_limiting", "nginx")
        assert support == FeatureSupport.FULL

    def test_get_feature_support_unknown(self, checker):
        """Test getting support for unknown feature."""
        support = checker._get_feature_support("unknown_feature", "envoy")
        assert support == FeatureSupport.UNSUPPORTED

    def test_check_provider_simple_envoy(self, checker, simple_config):
        """Test checking simple config with Envoy."""
        report = checker.check_provider(simple_config, "envoy")
        assert report.provider == "envoy"
        assert report.compatible is True
        assert report.compatibility_score == 1.0
        assert report.features_checked == 2
        assert len(report.features_supported) == 2
        assert len(report.features_unsupported) == 0

    def test_check_provider_complex_envoy(self, checker, complex_config):
        """Test checking complex config with Envoy."""
        report = checker.check_provider(complex_config, "envoy")
        assert report.provider == "envoy"
        assert report.compatible is True
        # Envoy has partial rate limiting support, so score < 1.0
        assert report.compatibility_score >= 0.9
        assert len(report.features_supported) > 0
        assert len(report.features_unsupported) == 0
        assert len(report.features_partial) > 0  # rate_limiting is partial

    def test_check_provider_complex_traefik(self, checker, complex_config):
        """Test checking complex config with Traefik."""
        report = checker.check_provider(complex_config, "traefik")
        assert report.provider == "traefik"
        # Traefik doesn't support active health checks
        assert len(report.features_unsupported) > 0
        assert report.compatibility_score < 1.0

    def test_check_provider_complex_nginx(self, checker, complex_config):
        """Test checking complex config with Nginx."""
        report = checker.check_provider(complex_config, "nginx")
        assert report.provider == "nginx"
        # Nginx OSS doesn't support active health checks
        assert len(report.features_unsupported) > 0
        assert report.compatibility_score < 1.0

    def test_check_provider_invalid_provider(self, checker, simple_config):
        """Test checking with invalid provider."""
        report = checker.check_provider(simple_config, "invalid_provider")
        assert report.provider == "invalid_provider"
        assert report.compatible is False
        assert report.compatibility_score == 0.0
        assert report.features_checked == 0
        assert len(report.warnings) > 0

    def test_compare_providers_simple(self, checker, simple_config):
        """Test comparing providers with simple config."""
        providers = ["envoy", "kong", "traefik"]
        reports = checker.compare_providers(simple_config, providers)
        assert len(reports) == 3
        assert all(r.compatible for r in reports)
        assert all(r.compatibility_score == 1.0 for r in reports)

    def test_compare_providers_complex(self, checker, complex_config):
        """Test comparing providers with complex config."""
        providers = ["envoy", "kong", "apisix", "traefik", "nginx", "haproxy"]
        reports = checker.compare_providers(complex_config, providers)
        assert len(reports) == 6

        # Envoy should have high compatibility (with partial rate limiting)
        envoy_report = next(r for r in reports if r.provider == "envoy")
        assert envoy_report.compatibility_score >= 0.9

        # Traefik should have some unsupported features (active health checks)
        traefik_report = next(r for r in reports if r.provider == "traefik")
        assert traefik_report.compatibility_score < 1.0
        assert len(traefik_report.features_unsupported) > 0

    def test_feature_display_names(self, checker):
        """Test getting human-readable feature names."""
        name = checker._get_feature_display_name("routing_path_prefix")
        assert name == "Path-based Routing"

        name = checker._get_feature_display_name("health_check_active")
        assert name == "Active Health Checks"

        name = checker._get_feature_display_name("authentication_jwt")
        assert name == "JWT Authentication"

        name = checker._get_feature_display_name("unknown_feature")
        assert name == "unknown_feature"  # Returns feature name as-is if not in mapping

    def test_feature_recommendations_traefik_active_health(self, checker):
        """Test recommendations for Traefik active health checks."""
        rec = checker._get_feature_recommendation("health_check_active", "traefik")
        assert "Traefik Enterprise" in rec or "passive" in rec.lower()

    def test_feature_recommendations_nginx_jwt(self, checker):
        """Test recommendations for Nginx JWT authentication."""
        rec = checker._get_feature_recommendation("authentication_jwt", "nginx")
        assert "OpenResty" in rec or "lua" in rec.lower()

    def test_feature_recommendations_haproxy_circuit_breaker(self, checker):
        """Test recommendations for HAProxy circuit breaker."""
        rec = checker._get_feature_recommendation("circuit_breaker", "haproxy")
        assert "observe layer7" in rec or "Envoy" in rec or "APISIX" in rec

    def test_compatibility_score_calculation(self, checker):
        """Test compatibility score calculation."""
        # Create a config with 4 features
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        host="backend.internal",
                        port=8080,
                        load_balancer=LoadBalancerConfig(
                            algorithm="round_robin",
                        ),
                        health_check=HealthCheckConfig(
                            active=ActiveHealthCheck(
                                enabled=True,
                                http_path="/health",
                            ),
                        ),
                    ),
                    routes=[
                        Route(
                            path_prefix="/api",
                            methods=["GET"],
                        )
                    ],
                )
            ],
        )

        # Check with Traefik (doesn't support active health checks)
        report = checker.check_provider(config, "traefik")

        # Score should be less than 1.0 because of unsupported feature
        assert report.compatibility_score < 1.0
        assert len(report.features_unsupported) > 0


class TestCompatibilityCheckerEdgeCases:
    """Tests for edge cases in compatibility checking."""

    @pytest.fixture
    def checker(self):
        """Create a CompatibilityChecker instance."""
        return CompatibilityChecker()

    def test_empty_config(self, checker):
        """Test checking empty config."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[],
        )
        report = checker.check_provider(config, "envoy")
        assert report.compatible is True
        assert report.features_checked == 0
        assert report.compatibility_score == 1.0

    def test_config_with_no_features(self, checker):
        """Test config with service but no special features."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="basic_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        host="backend.internal",
                        port=8080,
                    ),
                    routes=[
                        Route(
                            path_prefix="/",
                        )
                    ],
                )
            ],
        )
        report = checker.check_provider(config, "envoy")
        assert report.compatible is True
        assert report.features_checked == 1  # Only routing_path_prefix
        assert report.compatibility_score == 1.0

    def test_multiple_auth_types(self, checker):
        """Test config with multiple authentication types."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="auth_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        host="backend.internal",
                        port=8080,
                    ),
                    routes=[
                        Route(
                            path_prefix="/basic",
                            authentication=AuthenticationConfig(
                                enabled=True,
                                type="basic",
                            ),
                        ),
                        Route(
                            path_prefix="/jwt",
                            authentication=AuthenticationConfig(
                                enabled=True,
                                type="jwt",
                                jwt=JwtConfig(
                                    issuer="https://auth.example.com",
                                ),
                            ),
                        ),
                        Route(
                            path_prefix="/apikey",
                            authentication=AuthenticationConfig(
                                enabled=True,
                                type="api_key",
                                api_key=ApiKeyConfig(
                                    keys=["key123"],
                                ),
                            ),
                        ),
                    ],
                )
            ],
        )
        features = checker._extract_features_from_config(config)
        assert "authentication_basic" in features
        assert "authentication_jwt" in features
        assert "authentication_api_key" in features

    def test_multiple_load_balancing_algorithms(self, checker):
        """Test config with multiple load balancing algorithms."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="service_rr",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        host="backend1.internal",
                        port=8080,
                        load_balancer=LoadBalancerConfig(algorithm="round_robin"),
                    ),
                    routes=[Route(path_prefix="/rr")],
                ),
                Service(
                    name="service_lc",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        host="backend2.internal",
                        port=8080,
                        load_balancer=LoadBalancerConfig(algorithm="least_conn"),
                    ),
                    routes=[Route(path_prefix="/lc")],
                ),
                Service(
                    name="service_ip",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        host="backend3.internal",
                        port=8080,
                        load_balancer=LoadBalancerConfig(algorithm="ip_hash"),
                    ),
                    routes=[Route(path_prefix="/ip")],
                ),
            ],
        )
        features = checker._extract_features_from_config(config)
        assert "load_balancing_round_robin" in features
        assert "load_balancing_least_conn" in features
        assert "load_balancing_ip_hash" in features
