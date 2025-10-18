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
