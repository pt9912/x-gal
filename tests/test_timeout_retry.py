"""
Tests for Timeout & Retry configuration and provider implementations.
"""

import json

import pytest

from gal.config import Config, RetryConfig, TimeoutConfig


class TestTimeoutRetryConfigModel:
    """Test timeout and retry configuration models."""

    def test_timeout_config_defaults(self):
        """Test TimeoutConfig with default values."""
        timeout = TimeoutConfig()

        assert timeout.connect == "5s"
        assert timeout.send == "30s"
        assert timeout.read == "60s"
        assert timeout.idle == "300s"

    def test_timeout_config_custom(self):
        """Test TimeoutConfig with custom values."""
        timeout = TimeoutConfig(connect="10s", send="60s", read="120s", idle="600s")

        assert timeout.connect == "10s"
        assert timeout.send == "60s"
        assert timeout.read == "120s"
        assert timeout.idle == "600s"

    def test_retry_config_defaults(self):
        """Test RetryConfig with default values."""
        retry = RetryConfig()

        assert retry.enabled is True
        assert retry.attempts == 3
        assert retry.backoff == "exponential"
        assert retry.base_interval == "25ms"
        assert retry.max_interval == "250ms"
        assert "connect_timeout" in retry.retry_on
        assert "http_5xx" in retry.retry_on

    def test_retry_config_custom(self):
        """Test RetryConfig with custom values."""
        retry = RetryConfig(
            enabled=True,
            attempts=5,
            backoff="linear",
            base_interval="50ms",
            max_interval="500ms",
            retry_on=["connect_timeout", "http_502", "http_503"],
        )

        assert retry.enabled is True
        assert retry.attempts == 5
        assert retry.backoff == "linear"
        assert retry.base_interval == "50ms"
        assert retry.max_interval == "500ms"
        assert len(retry.retry_on) == 3
        assert "http_502" in retry.retry_on

    def test_retry_config_disabled(self):
        """Test RetryConfig when disabled."""
        retry = RetryConfig(enabled=False)

        assert retry.enabled is False
        assert retry.attempts == 3  # Defaults still set


class TestTimeoutRetryYAMLParsing:
    """Test parsing timeout and retry configuration from YAML."""

    def test_parse_timeout_from_yaml(self, tmp_path):
        """Test parsing timeout configuration from YAML file."""
        config_file = tmp_path / "timeout-config.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "10s"
          send: "60s"
          read: "120s"
          idle: "600s"
"""
        )

        config = Config.from_yaml(str(config_file))

        assert len(config.services) == 1
        service = config.services[0]
        assert len(service.routes) == 1
        route = service.routes[0]

        assert route.timeout is not None
        assert route.timeout.connect == "10s"
        assert route.timeout.send == "60s"
        assert route.timeout.read == "120s"
        assert route.timeout.idle == "600s"

    def test_parse_retry_from_yaml(self, tmp_path):
        """Test parsing retry configuration from YAML file."""
        config_file = tmp_path / "retry-config.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        retry:
          enabled: true
          attempts: 5
          backoff: exponential
          base_interval: "50ms"
          max_interval: "500ms"
          retry_on:
            - connect_timeout
            - http_5xx
            - http_502
"""
        )

        config = Config.from_yaml(str(config_file))

        assert len(config.services) == 1
        service = config.services[0]
        assert len(service.routes) == 1
        route = service.routes[0]

        assert route.retry is not None
        assert route.retry.enabled is True
        assert route.retry.attempts == 5
        assert route.retry.backoff == "exponential"
        assert route.retry.base_interval == "50ms"
        assert route.retry.max_interval == "500ms"
        assert len(route.retry.retry_on) == 3
        assert "connect_timeout" in route.retry.retry_on
        assert "http_5xx" in route.retry.retry_on
        assert "http_502" in route.retry.retry_on

    def test_parse_timeout_and_retry_combined(self, tmp_path):
        """Test parsing both timeout and retry configuration."""
        config_file = tmp_path / "combined-config.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "5s"
          send: "30s"
          read: "60s"
        retry:
          enabled: true
          attempts: 3
          retry_on:
            - connect_timeout
            - http_5xx
"""
        )

        config = Config.from_yaml(str(config_file))

        service = config.services[0]
        route = service.routes[0]

        # Check timeout
        assert route.timeout is not None
        assert route.timeout.connect == "5s"
        assert route.timeout.send == "30s"
        assert route.timeout.read == "60s"

        # Check retry
        assert route.retry is not None
        assert route.retry.enabled is True
        assert route.retry.attempts == 3
        assert "connect_timeout" in route.retry.retry_on

    def test_parse_without_timeout_retry(self, tmp_path):
        """Test parsing when timeout and retry are not specified."""
        config_file = tmp_path / "no-timeout-retry.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
"""
        )

        config = Config.from_yaml(str(config_file))

        service = config.services[0]
        route = service.routes[0]

        assert route.timeout is None
        assert route.retry is None


class TestEnvoyTimeoutRetry:
    """Test Envoy provider timeout and retry implementation."""

    def test_envoy_timeout_basic(self, tmp_path):
        """Test Envoy timeout configuration."""
        from gal.providers.envoy import EnvoyProvider

        config_file = tmp_path / "envoy-timeout.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "10s"
          send: "60s"
          read: "120s"
          idle: "600s"
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = EnvoyProvider()
        result = provider.generate(config)

        assert "connect_timeout: 10s" in result
        assert "timeout: 120s" in result  # read timeout on route
        assert "idle_timeout: 600s" in result

    def test_envoy_retry_basic(self, tmp_path):
        """Test Envoy retry configuration."""
        from gal.providers.envoy import EnvoyProvider

        config_file = tmp_path / "envoy-retry.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        retry:
          enabled: true
          attempts: 5
          retry_on:
            - connect_timeout
            - http_5xx
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = EnvoyProvider()
        result = provider.generate(config)

        assert "retry_policy:" in result
        assert "num_retries: 5" in result
        assert "connect-failure" in result or "5xx" in result
        assert "per_try_timeout:" in result

    def test_envoy_timeout_and_retry_combined(self, tmp_path):
        """Test Envoy with both timeout and retry configured."""
        from gal.providers.envoy import EnvoyProvider

        config_file = tmp_path / "envoy-combined.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "5s"
          read: "60s"
        retry:
          enabled: true
          attempts: 3
          base_interval: "50ms"
          retry_on:
            - connect_timeout
            - http_502
            - http_503
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = EnvoyProvider()
        result = provider.generate(config)

        # Check timeout
        assert "connect_timeout: 5s" in result
        assert "timeout: 60s" in result

        # Check retry
        assert "retry_policy:" in result
        assert "num_retries: 3" in result
        assert "per_try_timeout: 50ms" in result
        assert "retriable_status_codes:" in result
        assert "- 502" in result
        assert "- 503" in result


class TestKongTimeoutRetry:
    """Test Kong provider timeout and retry implementation."""

    def test_kong_timeout_basic(self, tmp_path):
        """Test Kong timeout configuration."""
        from gal.providers.kong import KongProvider

        config_file = tmp_path / "kong-timeout.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: kong

global:
  host: 0.0.0.0
  port: 8000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "10s"
          send: "60s"
          read: "120s"
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = KongProvider()
        result = provider.generate(config)

        # Kong uses milliseconds
        assert "connect_timeout: 10000" in result
        assert "read_timeout: 120000" in result
        assert "write_timeout: 60000" in result

    def test_kong_retry_basic(self, tmp_path):
        """Test Kong retry configuration."""
        from gal.providers.kong import KongProvider

        config_file = tmp_path / "kong-retry.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: kong

global:
  host: 0.0.0.0
  port: 8000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        retry:
          enabled: true
          attempts: 5
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = KongProvider()
        result = provider.generate(config)

        assert "retries: 5" in result


class TestAPISIXTimeoutRetry:
    """Test APISIX provider timeout and retry implementation."""

    def test_apisix_timeout_basic(self, tmp_path):
        """Test APISIX timeout configuration."""
        from gal.providers.apisix import APISIXProvider

        config_file = tmp_path / "apisix-timeout.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: apisix

global:
  host: 0.0.0.0
  port: 9080

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "10s"
          send: "60s"
          read: "120s"
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = APISIXProvider()
        result = provider.generate(config)

        # APISIX uses seconds
        assert '"timeout"' in result
        assert '"connect": 10' in result
        assert '"send": 60' in result
        assert '"read": 120' in result

    def test_apisix_retry_basic(self, tmp_path):
        """Test APISIX retry configuration."""
        from gal.providers.apisix import APISIXProvider

        config_file = tmp_path / "apisix-retry.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: apisix

global:
  host: 0.0.0.0
  port: 9080

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        retry:
          enabled: true
          attempts: 3
          retry_on:
            - http_502
            - http_503
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = APISIXProvider()
        result = provider.generate(config)

        assert '"proxy-retry"' in result
        assert '"retries": 3' in result


class TestTraefikTimeoutRetry:
    """Test Traefik provider timeout and retry implementation."""

    def test_traefik_timeout_basic(self, tmp_path):
        """Test Traefik timeout configuration."""
        from gal.providers.traefik import TraefikProvider

        config_file = tmp_path / "traefik-timeout.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: traefik

global:
  host: 0.0.0.0
  port: 8080

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "10s"
          read: "120s"
          idle: "600s"
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = TraefikProvider()
        result = provider.generate(config)

        assert "serversTransport:" in result
        assert "forwardingTimeouts:" in result
        assert "dialTimeout: 10s" in result
        assert "responseHeaderTimeout: 120s" in result
        assert "idleConnTimeout: 600s" in result

    def test_traefik_retry_basic(self, tmp_path):
        """Test Traefik retry configuration."""
        from gal.providers.traefik import TraefikProvider

        config_file = tmp_path / "traefik-retry.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: traefik

global:
  host: 0.0.0.0
  port: 8080

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        retry:
          enabled: true
          attempts: 5
          base_interval: "50ms"
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = TraefikProvider()
        result = provider.generate(config)

        assert "retry:" in result
        assert "attempts: 5" in result
        assert "initialInterval: 50ms" in result


class TestNginxTimeoutRetry:
    """Test Nginx provider timeout and retry implementation."""

    def test_nginx_timeout_basic(self, tmp_path):
        """Test Nginx timeout configuration."""
        from gal.providers.nginx import NginxProvider

        config_file = tmp_path / "nginx-timeout.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: nginx

global:
  host: 0.0.0.0
  port: 80

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "10s"
          send: "60s"
          read: "120s"
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = NginxProvider()
        result = provider.generate(config)

        assert "proxy_connect_timeout 10s;" in result
        assert "proxy_send_timeout 60s;" in result
        assert "proxy_read_timeout 120s;" in result

    def test_nginx_retry_basic(self, tmp_path):
        """Test Nginx retry configuration."""
        from gal.providers.nginx import NginxProvider

        config_file = tmp_path / "nginx-retry.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: nginx

global:
  host: 0.0.0.0
  port: 80

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        retry:
          enabled: true
          attempts: 3
          max_interval: "500ms"
          retry_on:
            - connect_timeout
            - http_502
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = NginxProvider()
        result = provider.generate(config)

        assert "proxy_next_upstream" in result
        assert "timeout" in result or "http_502" in result
        assert "proxy_next_upstream_tries 3;" in result
        assert "proxy_next_upstream_timeout 500ms;" in result


class TestHAProxyTimeoutRetry:
    """Test HAProxy provider timeout and retry implementation."""

    def test_haproxy_timeout_basic(self, tmp_path):
        """Test HAProxy timeout configuration."""
        from gal.providers.haproxy import HAProxyProvider

        config_file = tmp_path / "haproxy-timeout.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: haproxy

global:
  host: 0.0.0.0
  port: 80

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "10s"
          read: "120s"
          idle: "600s"
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = HAProxyProvider()
        result = provider.generate(config)

        assert "timeout connect 10s" in result
        assert "timeout server 120s" in result
        assert "timeout client 600s" in result

    def test_haproxy_retry_basic(self, tmp_path):
        """Test HAProxy retry configuration."""
        from gal.providers.haproxy import HAProxyProvider

        config_file = tmp_path / "haproxy-retry.yaml"
        config_file.write_text(
            """
version: "1.0"
provider: haproxy

global:
  host: 0.0.0.0
  port: 80

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        retry:
          enabled: true
          attempts: 5
          retry_on:
            - connect_timeout
            - http_503
"""
        )

        config = Config.from_yaml(str(config_file))
        provider = HAProxyProvider()
        result = provider.generate(config)

        assert "retry-on" in result
        assert "conn-failure" in result or "503" in result
        assert "retries 5" in result
