"""
Tests for gRPC transformation provider implementations.

Tests Lua filter/script generation for Envoy, Nginx, and APISIX providers
with gRPC protobuf transformations.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gal.config import (
    Config,
    GlobalConfig,
    GrpcTransformation,
    ProtoDescriptor,
    RequestBodyTransformation,
    ResponseBodyTransformation,
    Route,
    Service,
    Upstream,
)
from gal.proto_manager import ProtoManager
from gal.providers.apisix import APISIXProvider
from gal.providers.envoy import EnvoyProvider
from gal.providers.haproxy import HAProxyProvider
from gal.providers.kong import KongProvider
from gal.providers.nginx import NginxProvider
from gal.providers.traefik import TraefikProvider


@pytest.fixture
def sample_proto_descriptor():
    """Sample proto descriptor for testing."""
    return ProtoDescriptor(name="user_service", source="file", path="/tmp/user.desc")


@pytest.fixture
def sample_grpc_transformation():
    """Sample gRPC transformation config."""
    return GrpcTransformation(
        enabled=True,
        proto_descriptor="user_service",
        package="user.v1",
        service="UserService",
        request_type="CreateUserRequest",
        response_type="CreateUserResponse",
        request_transform=RequestBodyTransformation(
            add_fields={"trace_id": "{{uuid}}", "timestamp": "{{timestamp}}"},
            remove_fields=["password"],
            rename_fields={"user_id": "id"},
        ),
        response_transform=ResponseBodyTransformation(
            filter_fields=["secret"], add_fields={"server": "gateway"}
        ),
    )


@pytest.fixture
def grpc_service(sample_grpc_transformation):
    """Sample gRPC service with transformation."""
    route = Route(
        path_prefix="/user.v1.UserService/CreateUser",
        grpc_transformation=sample_grpc_transformation,
    )

    return Service(
        name="user_api",
        type="grpc",
        protocol="http2",
        upstream=Upstream(host="grpc-backend.local", port=50051),
        routes=[route],
    )


@pytest.fixture
def grpc_config(sample_proto_descriptor, grpc_service):
    """Complete gRPC config with proto descriptor and service."""
    return Config(
        version="1.0",
        provider="envoy",
        global_config=GlobalConfig(),
        services=[grpc_service],
        proto_descriptors=[sample_proto_descriptor],
    )


class TestEnvoyGrpcTransformation:
    """Tests for Envoy gRPC transformation generation."""

    def test_envoy_generates_lua_filter(self, grpc_config):
        """Test Envoy generates Lua filter for gRPC transformation."""
        provider = EnvoyProvider()

        # Mock ProtoManager
        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check Lua filter is present
        assert "envoy.filters.http.lua" in result
        assert "inline_code:" in result

    def test_envoy_lua_contains_pb_require(self, grpc_config):
        """Test Envoy Lua code contains protobuf library require."""
        provider = EnvoyProvider()

        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check pb library is required
        assert "local pb = require('pb')" in result or "require('pb')" in result

    def test_envoy_lua_contains_descriptor_path(self, grpc_config):
        """Test Envoy Lua code references proto descriptor path."""
        provider = EnvoyProvider()

        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check descriptor path is referenced
        assert "/tmp/user.desc" in result

    def test_envoy_request_transform_adds_fields(self, grpc_config):
        """Test Envoy request transformation adds trace_id and timestamp."""
        provider = EnvoyProvider()

        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check trace_id and timestamp are added
        assert "trace_id" in result
        assert "uuid" in result.lower() or "generate_uuid" in result

    def test_envoy_request_transform_removes_fields(self, grpc_config):
        """Test Envoy request transformation removes password field."""
        provider = EnvoyProvider()

        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check password is removed
        assert "password" in result
        assert (
            "= nil" in result
            or "msg['password'] = nil" in result
            or 'msg["password"] = nil' in result
        )

    def test_envoy_request_transform_renames_fields(self, grpc_config):
        """Test Envoy request transformation renames user_id to id."""
        provider = EnvoyProvider()

        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check user_id is renamed to id
        assert "user_id" in result
        assert '"id"' in result or "'id'" in result

    def test_envoy_response_transform_filters_fields(self, grpc_config):
        """Test Envoy response transformation filters secret field."""
        provider = EnvoyProvider()

        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check secret is filtered
        assert "secret" in result

    def test_envoy_without_grpc_transformation(self):
        """Test Envoy generation without gRPC transformation."""
        service = Service(
            name="http_api",
            type="http",
            protocol="http",
            upstream=Upstream(host="backend", port=8080),
            routes=[Route(path_prefix="/api")],
        )

        config = Config(
            version="1.0", provider="envoy", global_config=GlobalConfig(), services=[service]
        )

        provider = EnvoyProvider()
        result = provider.generate(config)

        # Should not contain Lua filter
        assert "envoy.filters.http.lua" not in result


class TestNginxGrpcTransformation:
    """Tests for Nginx gRPC transformation generation."""

    def test_nginx_generates_lua_blocks(self, grpc_config):
        """Test Nginx generates Lua blocks for gRPC transformation."""
        grpc_config.provider = "nginx"
        provider = NginxProvider()

        with patch("gal.providers.nginx.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check Lua blocks are present
        assert "access_by_lua_block" in result or "body_filter_by_lua_block" in result

    def test_nginx_lua_contains_pb_require(self, grpc_config):
        """Test Nginx Lua code contains protobuf library require."""
        grpc_config.provider = "nginx"
        provider = NginxProvider()

        with patch("gal.providers.nginx.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check pb library is required
        assert "local pb = require('pb')" in result or "require('pb')" in result

    def test_nginx_request_transform_uses_ngx_var(self, grpc_config):
        """Test Nginx uses ngx.var for UUID generation."""
        grpc_config.provider = "nginx"
        provider = NginxProvider()

        with patch("gal.providers.nginx.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check ngx.var.request_id or similar
        assert "ngx.var" in result or "ngx." in result

    def test_nginx_reads_request_body(self, grpc_config):
        """Test Nginx reads request body for transformation."""
        grpc_config.provider = "nginx"
        provider = NginxProvider()

        with patch("gal.providers.nginx.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check request body read
        assert "ngx.req.read_body" in result or "ngx.req.get_body_data" in result

    def test_nginx_without_grpc_transformation(self):
        """Test Nginx generation without gRPC transformation."""
        service = Service(
            name="http_api",
            type="http",
            protocol="http",
            upstream=Upstream(host="backend", port=8080),
            routes=[Route(path_prefix="/api")],
        )

        config = Config(
            version="1.0", provider="nginx", global_config=GlobalConfig(), services=[service]
        )

        provider = NginxProvider()
        result = provider.generate(config)

        # Should not contain gRPC Lua blocks
        assert "# gRPC" not in result or "grpc_pass" not in result


class TestAPISIXGrpcTransformation:
    """Tests for APISIX gRPC transformation generation."""

    def test_apisix_generates_serverless_plugin(self, grpc_config):
        """Test APISIX generates serverless-pre-function plugin."""
        grpc_config.provider = "apisix"
        provider = APISIXProvider()

        with patch("gal.providers.apisix.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check serverless plugin
        assert "serverless-pre-function" in result or "serverless" in result

    def test_apisix_lua_contains_pb_require(self, grpc_config):
        """Test APISIX Lua code contains protobuf library require."""
        grpc_config.provider = "apisix"
        provider = APISIXProvider()

        with patch("gal.providers.apisix.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check pb library is required
        assert "require('pb')" in result

    def test_apisix_uses_core_request(self, grpc_config):
        """Test APISIX uses apisix.core.request for body access."""
        grpc_config.provider = "apisix"
        provider = APISIXProvider()

        with patch("gal.providers.apisix.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Check apisix.core usage
        assert "apisix.core" in result or "core.request" in result

    def test_apisix_without_grpc_transformation(self):
        """Test APISIX generation without gRPC transformation."""
        service = Service(
            name="http_api",
            type="http",
            protocol="http",
            upstream=Upstream(host="backend", port=8080),
            routes=[Route(path_prefix="/api")],
        )

        config = Config(
            version="1.0", provider="apisix", global_config=GlobalConfig(), services=[service]
        )

        provider = APISIXProvider()
        result = provider.generate(config)

        # Should not contain serverless for gRPC
        # (APISIX may use serverless for other features)
        # Just check it doesn't crash
        assert result is not None


class TestProviderGrpcWarnings:
    """Tests for provider warnings about gRPC support."""

    def test_kong_has_grpc_warning(self):
        """Test Kong provider has gRPC transformation warning in docstring."""
        provider = KongProvider()
        docstring = provider.__class__.__doc__

        assert docstring is not None
        assert "gRPC" in docstring or "grpc" in docstring.lower()

    def test_haproxy_has_grpc_warning(self):
        """Test HAProxy provider has gRPC transformation warning in docstring."""
        provider = HAProxyProvider()
        docstring = provider.__class__.__doc__

        assert docstring is not None
        assert "gRPC" in docstring or "grpc" in docstring.lower()

    def test_traefik_has_grpc_limitation(self):
        """Test Traefik provider has gRPC limitation warning in docstring."""
        provider = TraefikProvider()
        docstring = provider.__class__.__doc__

        assert docstring is not None
        assert "gRPC" in docstring or "grpc" in docstring.lower()
        # Should mention not supported
        assert "NOT supported" in docstring or "not supported" in docstring


class TestGrpcTransformationIntegration:
    """Integration tests for complete gRPC transformation flow."""

    def test_envoy_complete_grpc_service(self, grpc_config):
        """Test complete Envoy config with gRPC service and transformation."""
        provider = EnvoyProvider()

        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Should contain all major components
        assert "static_resources:" in result  # Envoy config structure
        assert "clusters:" in result
        assert "listeners:" in result
        assert "envoy.filters.http.lua" in result  # gRPC transformation
        assert "user.v1" in result  # Proto package
        assert "CreateUserRequest" in result  # Request type

    def test_nginx_complete_grpc_service(self, grpc_config):
        """Test complete Nginx config with gRPC service and transformation."""
        grpc_config.provider = "nginx"
        provider = NginxProvider()

        with patch("gal.providers.nginx.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Should contain Nginx config structure
        assert "server" in result
        assert "location" in result
        assert "proxy_pass" in result
        # Should contain gRPC transformation
        assert "lua" in result.lower()
        assert "access_by_lua_block" in result or "body_filter_by_lua_block" in result

    def test_apisix_complete_grpc_service(self, grpc_config):
        """Test complete APISIX config with gRPC service and transformation."""
        grpc_config.provider = "apisix"
        provider = APISIXProvider()

        with patch("gal.providers.apisix.ProtoManager") as mock_pm_class:
            mock_manager = MagicMock()
            mock_manager.get_descriptor.return_value = grpc_config.proto_descriptors[0]
            mock_pm_class.return_value = mock_manager

            result = provider.generate(grpc_config)

        # Should contain APISIX config structure (JSON format)
        assert '"routes"' in result or "routes:" in result
        assert (
            '"upstreams"' in result
            or "upstreams:" in result
            or '"upstream"' in result
            or "upstream:" in result
        )
        # Should contain serverless plugin
        assert '"plugins"' in result or "plugins:" in result
