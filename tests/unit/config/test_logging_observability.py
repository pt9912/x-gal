"""Tests for Logging & Observability feature (v1.2.0 Feature 6)."""

import json

import pytest
import yaml

from gal.config import (
    Config,
    GlobalConfig,
    LoggingConfig,
    MetricsConfig,
    Route,
    Service,
    Upstream,
    UpstreamTarget,
)
from gal.providers.apisix import APISIXProvider
from gal.providers.envoy import EnvoyProvider
from gal.providers.haproxy import HAProxyProvider
from gal.providers.kong import KongProvider
from gal.providers.nginx import NginxProvider
from gal.providers.traefik import TraefikProvider


class TestLoggingObservabilityConfigModel:
    """Test LoggingConfig and MetricsConfig dataclasses."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig with default values."""
        logging = LoggingConfig()

        assert logging.enabled is True
        assert logging.format == "json"
        assert logging.level == "info"
        assert logging.access_log_path == "/var/log/gateway/access.log"
        assert logging.error_log_path == "/var/log/gateway/error.log"
        assert logging.sample_rate == 1.0
        assert logging.include_request_body is False
        assert logging.include_response_body is False
        assert logging.include_headers == ["X-Request-ID", "User-Agent"]
        assert logging.exclude_paths == ["/health", "/metrics"]
        assert logging.custom_fields == {}

    def test_logging_config_custom(self):
        """Test LoggingConfig with custom values."""
        logging = LoggingConfig(
            enabled=True,
            format="text",
            level="debug",
            access_log_path="/custom/access.log",
            error_log_path="/custom/error.log",
            sample_rate=0.5,
            include_request_body=True,
            include_response_body=True,
            include_headers=["X-Custom-Header"],
            exclude_paths=["/ping"],
            custom_fields={"environment": "production"},
        )

        assert logging.enabled is True
        assert logging.format == "text"
        assert logging.level == "debug"
        assert logging.access_log_path == "/custom/access.log"
        assert logging.error_log_path == "/custom/error.log"
        assert logging.sample_rate == 0.5
        assert logging.include_request_body is True
        assert logging.include_response_body is True
        assert logging.include_headers == ["X-Custom-Header"]
        assert logging.exclude_paths == ["/ping"]
        assert logging.custom_fields == {"environment": "production"}

    def test_metrics_config_defaults(self):
        """Test MetricsConfig with default values."""
        metrics = MetricsConfig()

        assert metrics.enabled is True
        assert metrics.exporter == "prometheus"
        assert metrics.prometheus_port == 9090
        assert metrics.prometheus_path == "/metrics"
        assert metrics.opentelemetry_endpoint == ""
        assert metrics.include_histograms is True
        assert metrics.include_counters is True
        assert metrics.custom_labels == {}

    def test_metrics_config_custom(self):
        """Test MetricsConfig with custom values."""
        metrics = MetricsConfig(
            enabled=True,
            exporter="both",
            prometheus_port=9091,
            prometheus_path="/custom/metrics",
            opentelemetry_endpoint="http://otel-collector:4317",
            include_histograms=False,
            include_counters=True,
            custom_labels={"cluster": "prod", "region": "eu-west-1"},
        )

        assert metrics.enabled is True
        assert metrics.exporter == "both"
        assert metrics.prometheus_port == 9091
        assert metrics.prometheus_path == "/custom/metrics"
        assert metrics.opentelemetry_endpoint == "http://otel-collector:4317"
        assert metrics.include_histograms is False
        assert metrics.include_counters is True
        assert metrics.custom_labels == {"cluster": "prod", "region": "eu-west-1"}


class TestEnvoyLoggingObservability:
    """Test Envoy provider logging & observability."""

    def test_envoy_logging_json(self):
        """Test Envoy JSON access logging."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=10000,
                admin_port=9901,
                logging=LoggingConfig(
                    enabled=True,
                    format="json",
                    level="info",
                    access_log_path="/var/log/envoy/access.log",
                    include_headers=["X-Request-ID", "User-Agent"],
                    custom_fields={"service": "api-gateway"},
                ),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = EnvoyProvider()
        output = provider.generate(config)

        assert "access_log:" in output
        assert "envoy.access_loggers.file" in output
        assert "/var/log/envoy/access.log" in output
        assert "json_format:" in output
        assert "request_id" in output
        assert "method" in output
        assert "response_code" in output
        assert 'service: "api-gateway"' in output

    def test_envoy_logging_sampling(self):
        """Test Envoy log sampling."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=10000,
                admin_port=9901,
                logging=LoggingConfig(enabled=True, sample_rate=0.1),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = EnvoyProvider()
        output = provider.generate(config)

        assert "runtime_filter:" in output
        assert "access_log_sampling" in output
        assert "numerator: 10" in output
        assert "denominator: HUNDRED" in output

    def test_envoy_metrics_prometheus(self):
        """Test Envoy Prometheus metrics."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=10000,
                admin_port=9901,
                metrics=MetricsConfig(enabled=True, exporter="prometheus", prometheus_port=9090),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = EnvoyProvider()
        output = provider.generate(config)

        assert "Prometheus metrics available at admin interface" in output
        assert "/stats/prometheus" in output

    def test_envoy_metrics_opentelemetry(self):
        """Test Envoy OpenTelemetry metrics."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=10000,
                admin_port=9901,
                metrics=MetricsConfig(
                    enabled=True,
                    exporter="opentelemetry",
                    opentelemetry_endpoint="http://otel-collector:4317",
                ),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = EnvoyProvider()
        output = provider.generate(config)

        assert "stats_sinks:" in output
        assert "envoy.stat_sinks.open_telemetry" in output
        assert "opentelemetry_collector" in output


class TestKongLoggingObservability:
    """Test Kong provider logging & observability."""

    def test_kong_logging_plugin(self):
        """Test Kong file-log plugin."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=8000,
                logging=LoggingConfig(
                    enabled=True,
                    format="json",
                    access_log_path="/var/log/kong/access.log",
                    custom_fields={"environment": "production"},
                ),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = KongProvider()
        output = provider.generate(config)

        assert "plugins:" in output
        assert "file-log" in output
        assert "/var/log/kong/access.log" in output
        assert "format: json" in output

    def test_kong_metrics_prometheus(self):
        """Test Kong Prometheus plugin."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=8000,
                metrics=MetricsConfig(enabled=True, exporter="prometheus"),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = KongProvider()
        output = provider.generate(config)

        assert "plugins:" in output
        assert "prometheus" in output


class TestAPISIXLoggingObservability:
    """Test APISIX provider logging & observability."""

    def test_apisix_logging_plugin(self):
        """Test APISIX file-logger plugin."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=9080,
                logging=LoggingConfig(
                    enabled=True,
                    access_log_path="/var/log/apisix/access.log",
                    include_request_body=True,
                    include_response_body=True,
                ),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = APISIXProvider()
        output = provider.generate(config)
        data = json.loads(output)

        assert "global_plugins" in data
        assert "file-logger" in data["global_plugins"]
        assert data["global_plugins"]["file-logger"]["path"] == "/var/log/apisix/access.log"
        assert data["global_plugins"]["file-logger"]["include_req_body"] is True
        assert data["global_plugins"]["file-logger"]["include_resp_body"] is True

    def test_apisix_metrics_prometheus(self):
        """Test APISIX prometheus plugin."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=9080,
                metrics=MetricsConfig(enabled=True, exporter="prometheus"),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = APISIXProvider()
        output = provider.generate(config)
        data = json.loads(output)

        assert "global_plugins" in data
        assert "prometheus" in data["global_plugins"]


class TestTraefikLoggingObservability:
    """Test Traefik provider logging & observability."""

    def test_traefik_access_log(self):
        """Test Traefik accessLog configuration."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=80,
                logging=LoggingConfig(
                    enabled=True,
                    format="json",
                    access_log_path="/var/log/traefik/access.log",
                    custom_fields={"cluster": "prod"},
                ),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = TraefikProvider()
        output = provider.generate(config)

        assert "accessLog:" in output
        assert "filePath: /var/log/traefik/access.log" in output
        assert "format: json" in output

    def test_traefik_metrics_prometheus(self):
        """Test Traefik Prometheus metrics."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=80,
                metrics=MetricsConfig(enabled=True, exporter="prometheus", prometheus_port=9090),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = TraefikProvider()
        output = provider.generate(config)

        assert "metrics:" in output
        assert "prometheus:" in output
        assert "entryPoint: metrics" in output


class TestNginxLoggingObservability:
    """Test Nginx provider logging & observability."""

    def test_nginx_logging_json(self):
        """Test Nginx JSON logging."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=80,
                logging=LoggingConfig(
                    enabled=True,
                    format="json",
                    level="info",
                    access_log_path="/var/log/nginx/access.log",
                    error_log_path="/var/log/nginx/error.log",
                    custom_fields={"app": "gateway"},
                ),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = NginxProvider()
        output = provider.generate(config)

        assert "log_format json_combined" in output
        assert "time_local" in output
        assert "remote_addr" in output
        assert "request_method" in output
        assert "status" in output
        assert "access_log /var/log/nginx/access.log json_combined" in output
        assert "error_log /var/log/nginx/error.log info" in output
        assert 'app":"gateway"' in output

    def test_nginx_logging_text(self):
        """Test Nginx text logging."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=80,
                logging=LoggingConfig(
                    enabled=True,
                    format="text",
                    level="warning",
                    access_log_path="/var/log/nginx/access.log",
                    error_log_path="/var/log/nginx/error.log",
                ),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = NginxProvider()
        output = provider.generate(config)

        assert "access_log /var/log/nginx/access.log;" in output
        assert "error_log /var/log/nginx/error.log warn;" in output


class TestHAProxyLoggingObservability:
    """Test HAProxy provider logging & observability."""

    def test_haproxy_logging_config(self):
        """Test HAProxy logging configuration."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=80,
                logging=LoggingConfig(enabled=True, format="text", level="info"),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = HAProxyProvider()
        output = provider.generate(config)

        assert "log         127.0.0.1 local0 info" in output

    def test_haproxy_logging_json_note(self):
        """Test HAProxy JSON logging note."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=80,
                logging=LoggingConfig(enabled=True, format="json", level="debug"),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = HAProxyProvider()
        output = provider.generate(config)

        assert "log         127.0.0.1 local0 info" in output
        assert "JSON format requires log-format directive" in output

    def test_haproxy_metrics_note(self):
        """Test HAProxy metrics note."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=80,
                metrics=MetricsConfig(enabled=True, exporter="prometheus", prometheus_port=9090),
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        provider = HAProxyProvider()
        output = provider.generate(config)

        assert "Prometheus metrics endpoint" in output
        assert "prometheus-exporter on port 9090" in output
        assert "stats endpoint" in output
