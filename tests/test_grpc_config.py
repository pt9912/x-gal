"""
Tests for gRPC configuration model (ProtoDescriptor and GrpcTransformation).

Tests config validation, edge cases, and error handling for gRPC-specific
configuration classes introduced in v1.4.0.
"""

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


class TestProtoDescriptor:
    """Tests for ProtoDescriptor dataclass."""

    def test_proto_descriptor_file_source(self):
        """Test ProtoDescriptor with source='file'."""
        desc = ProtoDescriptor(
            name="user_service",
            source="file",
            path="/protos/user.proto"
        )

        assert desc.name == "user_service"
        assert desc.source == "file"
        assert desc.path == "/protos/user.proto"
        assert desc.content == ""
        assert desc.url == ""

    def test_proto_descriptor_inline_source(self):
        """Test ProtoDescriptor with source='inline'."""
        proto_content = '''
        syntax = "proto3";
        package user.v1;
        message User { string id = 1; }
        '''

        desc = ProtoDescriptor(
            name="user_service",
            source="inline",
            content=proto_content
        )

        assert desc.name == "user_service"
        assert desc.source == "inline"
        assert desc.content == proto_content
        assert desc.path == ""
        assert desc.url == ""

    def test_proto_descriptor_url_source(self):
        """Test ProtoDescriptor with source='url'."""
        desc = ProtoDescriptor(
            name="user_service",
            source="url",
            url="https://api.example.com/protos/user.proto"
        )

        assert desc.name == "user_service"
        assert desc.source == "url"
        assert desc.url == "https://api.example.com/protos/user.proto"
        assert desc.path == ""
        assert desc.content == ""

    def test_proto_descriptor_empty_name(self):
        """Test ProtoDescriptor with empty name raises ValueError."""
        with pytest.raises(ValueError, match="ProtoDescriptor.name is required"):
            ProtoDescriptor(name="", source="file", path="/protos/user.proto")

    def test_proto_descriptor_invalid_source(self):
        """Test ProtoDescriptor with invalid source raises ValueError."""
        with pytest.raises(ValueError, match="Invalid source"):
            ProtoDescriptor(name="user_service", source="s3", path="/protos/user.proto")

    def test_proto_descriptor_file_without_path(self):
        """Test ProtoDescriptor with source='file' but no path raises ValueError."""
        with pytest.raises(ValueError, match="ProtoDescriptor.path is required when source='file'"):
            ProtoDescriptor(name="user_service", source="file")

    def test_proto_descriptor_inline_without_content(self):
        """Test ProtoDescriptor with source='inline' but no content raises ValueError."""
        with pytest.raises(ValueError, match="ProtoDescriptor.content is required when source='inline'"):
            ProtoDescriptor(name="user_service", source="inline")

    def test_proto_descriptor_url_without_url(self):
        """Test ProtoDescriptor with source='url' but no url raises ValueError."""
        with pytest.raises(ValueError, match="ProtoDescriptor.url is required when source='url'"):
            ProtoDescriptor(name="user_service", source="url")


class TestGrpcTransformation:
    """Tests for GrpcTransformation dataclass."""

    def test_grpc_transformation_enabled(self):
        """Test GrpcTransformation with all required fields."""
        transform = GrpcTransformation(
            enabled=True,
            proto_descriptor="user_service",
            package="user.v1",
            service="UserService",
            request_type="CreateUserRequest",
            response_type="CreateUserResponse"
        )

        assert transform.enabled is True
        assert transform.proto_descriptor == "user_service"
        assert transform.package == "user.v1"
        assert transform.service == "UserService"
        assert transform.request_type == "CreateUserRequest"
        assert transform.response_type == "CreateUserResponse"

    def test_grpc_transformation_disabled(self):
        """Test GrpcTransformation with enabled=False doesn't require fields."""
        transform = GrpcTransformation(enabled=False)

        assert transform.enabled is False
        assert transform.proto_descriptor == ""
        assert transform.package == ""
        assert transform.service == ""
        assert transform.request_type == ""
        assert transform.response_type == ""

    def test_grpc_transformation_missing_proto_descriptor(self):
        """Test GrpcTransformation with enabled=True but missing proto_descriptor."""
        with pytest.raises(ValueError, match="proto_descriptor is required when enabled=True"):
            GrpcTransformation(
                enabled=True,
                package="user.v1",
                service="UserService",
                request_type="CreateUserRequest",
                response_type="CreateUserResponse"
            )

    def test_grpc_transformation_missing_package(self):
        """Test GrpcTransformation with enabled=True but missing package."""
        with pytest.raises(ValueError, match="package is required when enabled=True"):
            GrpcTransformation(
                enabled=True,
                proto_descriptor="user_service",
                service="UserService",
                request_type="CreateUserRequest",
                response_type="CreateUserResponse"
            )

    def test_grpc_transformation_missing_service(self):
        """Test GrpcTransformation with enabled=True but missing service."""
        with pytest.raises(ValueError, match="service is required when enabled=True"):
            GrpcTransformation(
                enabled=True,
                proto_descriptor="user_service",
                package="user.v1",
                request_type="CreateUserRequest",
                response_type="CreateUserResponse"
            )

    def test_grpc_transformation_missing_request_type(self):
        """Test GrpcTransformation with enabled=True but missing request_type."""
        with pytest.raises(ValueError, match="request_type is required when enabled=True"):
            GrpcTransformation(
                enabled=True,
                proto_descriptor="user_service",
                package="user.v1",
                service="UserService",
                response_type="CreateUserResponse"
            )

    def test_grpc_transformation_missing_response_type(self):
        """Test GrpcTransformation with enabled=True but missing response_type."""
        with pytest.raises(ValueError, match="response_type is required when enabled=True"):
            GrpcTransformation(
                enabled=True,
                proto_descriptor="user_service",
                package="user.v1",
                service="UserService",
                request_type="CreateUserRequest"
            )

    def test_grpc_transformation_with_request_transform(self):
        """Test GrpcTransformation with request transformation."""
        request_transform = RequestBodyTransformation(
            add_fields={"trace_id": "{{uuid}}"},
            remove_fields=["password"],
            rename_fields={"user_id": "id"}
        )

        transform = GrpcTransformation(
            enabled=True,
            proto_descriptor="user_service",
            package="user.v1",
            service="UserService",
            request_type="CreateUserRequest",
            response_type="CreateUserResponse",
            request_transform=request_transform
        )

        assert transform.request_transform is not None
        assert transform.request_transform.add_fields == {"trace_id": "{{uuid}}"}
        assert transform.request_transform.remove_fields == ["password"]
        assert transform.request_transform.rename_fields == {"user_id": "id"}

    def test_grpc_transformation_with_response_transform(self):
        """Test GrpcTransformation with response transformation."""
        response_transform = ResponseBodyTransformation(
            filter_fields=["password", "secret"],
            add_fields={"server_timestamp": "{{timestamp}}"}
        )

        transform = GrpcTransformation(
            enabled=True,
            proto_descriptor="user_service",
            package="user.v1",
            service="UserService",
            request_type="CreateUserRequest",
            response_type="CreateUserResponse",
            response_transform=response_transform
        )

        assert transform.response_transform is not None
        assert transform.response_transform.filter_fields == ["password", "secret"]
        assert transform.response_transform.add_fields == {"server_timestamp": "{{timestamp}}"}


class TestRouteGrpcTransformation:
    """Tests for Route with grpc_transformation."""

    def test_route_with_grpc_transformation(self):
        """Test Route with grpc_transformation field."""
        grpc_t = GrpcTransformation(
            enabled=True,
            proto_descriptor="user_service",
            package="user.v1",
            service="UserService",
            request_type="CreateUserRequest",
            response_type="CreateUserResponse"
        )

        route = Route(
            path_prefix="/user.v1.UserService/CreateUser",
            grpc_transformation=grpc_t
        )

        assert route.grpc_transformation is not None
        assert route.grpc_transformation.enabled is True
        assert route.grpc_transformation.service == "UserService"

    def test_route_without_grpc_transformation(self):
        """Test Route without grpc_transformation (default None)."""
        route = Route(path_prefix="/api/users")

        assert route.grpc_transformation is None


class TestConfigProtoDescriptors:
    """Tests for Config with proto_descriptors."""

    def test_config_with_proto_descriptors(self):
        """Test Config with proto_descriptors list."""
        desc1 = ProtoDescriptor(name="user_svc", source="file", path="/protos/user.proto")
        desc2 = ProtoDescriptor(name="order_svc", source="file", path="/protos/order.proto")

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(),
            services=[],
            proto_descriptors=[desc1, desc2]
        )

        assert len(config.proto_descriptors) == 2
        assert config.proto_descriptors[0].name == "user_svc"
        assert config.proto_descriptors[1].name == "order_svc"

    def test_config_without_proto_descriptors(self):
        """Test Config without proto_descriptors (default empty list)."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(),
            services=[]
        )

        assert config.proto_descriptors == []

    def test_config_with_grpc_service(self):
        """Test complete Config with gRPC service and transformation."""
        desc = ProtoDescriptor(name="user_svc", source="file", path="/protos/user.proto")

        grpc_t = GrpcTransformation(
            enabled=True,
            proto_descriptor="user_svc",
            package="user.v1",
            service="UserService",
            request_type="CreateUserRequest",
            response_type="CreateUserResponse",
            request_transform=RequestBodyTransformation(
                add_fields={"trace_id": "{{uuid}}"}
            )
        )

        route = Route(
            path_prefix="/user.v1.UserService/CreateUser",
            grpc_transformation=grpc_t
        )

        service = Service(
            name="user_api",
            type="grpc",
            protocol="http2",
            upstream=Upstream(host="grpc-backend", port=50051),
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(),
            services=[service],
            proto_descriptors=[desc]
        )

        assert len(config.services) == 1
        assert config.services[0].type == "grpc"
        assert len(config.services[0].routes) == 1
        assert config.services[0].routes[0].grpc_transformation is not None
        assert len(config.proto_descriptors) == 1
