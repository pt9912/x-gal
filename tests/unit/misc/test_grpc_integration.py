"""
Integration tests for gRPC transformations.

Tests complete end-to-end flow: Config → ProtoManager → Provider → Output validation.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

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
from gal.providers.nginx import NginxProvider


@pytest.fixture
def sample_proto_content():
    """Valid proto3 content for testing."""
    return """
syntax = "proto3";
package user.v1;

message User {
    string id = 1;
    string name = 2;
    string email = 3;
    string password = 4;
}

service UserService {
    rpc CreateUser (CreateUserRequest) returns (CreateUserResponse);
    rpc GetUser (GetUserRequest) returns (GetUserResponse);
}

message CreateUserRequest {
    string user_id = 1;
    string name = 2;
    string email = 3;
    string password = 4;
}

message CreateUserResponse {
    User user = 1;
    string secret = 2;
}

message GetUserRequest {
    string user_id = 1;
}

message GetUserResponse {
    User user = 1;
}
"""


class TestGrpcIntegrationEndToEnd:
    """End-to-end integration tests for gRPC transformations."""

    def test_full_transformation_flow_envoy(self, sample_proto_content):
        """Test complete flow: Config → ProtoManager → Envoy → Validated output."""
        # Create proto descriptor (inline)
        proto_desc = ProtoDescriptor(
            name="user_service", source="inline", content=sample_proto_content
        )

        # Create gRPC transformation
        grpc_transform = GrpcTransformation(
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
            response_transform=ResponseBodyTransformation(filter_fields=["secret"]),
        )

        # Create route with transformation
        route = Route(
            path_prefix="/user.v1.UserService/CreateUser", grpc_transformation=grpc_transform
        )

        # Create gRPC service
        service = Service(
            name="user_api",
            type="grpc",
            protocol="http2",
            upstream=Upstream(host="grpc-backend", port=50051),
            routes=[route],
        )

        # Create complete config
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(),
            services=[service],
            proto_descriptors=[proto_desc],
        )

        # Generate output with mocked ProtoManager
        provider = EnvoyProvider()

        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:
            # Mock descriptor with path
            mock_desc = ProtoDescriptor(name="user_service", source="file", path="/tmp/user.desc")
            mock_manager = type(
                "obj",
                (object,),
                {
                    "register_descriptor": lambda self, desc: None,
                    "get_descriptor": lambda self, name: mock_desc,
                },
            )()
            mock_pm_class.return_value = mock_manager

            result = provider.generate(config)

        # Validate output contains all transformation components
        assert "envoy.filters.http.lua" in result
        assert "user.v1" in result
        assert "CreateUserRequest" in result
        assert "CreateUserResponse" in result
        assert "trace_id" in result
        assert "password" in result  # Removal logic
        assert "secret" in result  # Filter logic
        assert "user_id" in result  # Rename logic

    def test_multiple_proto_descriptors(self, sample_proto_content):
        """Test configuration with multiple proto descriptors."""
        # Create two proto descriptors
        user_proto = ProtoDescriptor(
            name="user_service", source="inline", content=sample_proto_content
        )

        order_proto_content = """
syntax = "proto3";
package order.v1;

message Order {
    string order_id = 1;
    string user_id = 2;
}

service OrderService {
    rpc CreateOrder (CreateOrderRequest) returns (CreateOrderResponse);
}

message CreateOrderRequest {
    string user_id = 1;
}

message CreateOrderResponse {
    Order order = 1;
}
"""

        order_proto = ProtoDescriptor(
            name="order_service", source="inline", content=order_proto_content
        )

        # Create two services with different transformations
        user_route = Route(
            path_prefix="/user.v1.UserService/CreateUser",
            grpc_transformation=GrpcTransformation(
                enabled=True,
                proto_descriptor="user_service",
                package="user.v1",
                service="UserService",
                request_type="CreateUserRequest",
                response_type="CreateUserResponse",
            ),
        )

        order_route = Route(
            path_prefix="/order.v1.OrderService/CreateOrder",
            grpc_transformation=GrpcTransformation(
                enabled=True,
                proto_descriptor="order_service",
                package="order.v1",
                service="OrderService",
                request_type="CreateOrderRequest",
                response_type="CreateOrderResponse",
            ),
        )

        user_service = Service(
            name="user_api",
            type="grpc",
            protocol="http2",
            upstream=Upstream(host="user-backend", port=50051),
            routes=[user_route],
        )

        order_service = Service(
            name="order_api",
            type="grpc",
            protocol="http2",
            upstream=Upstream(host="order-backend", port=50052),
            routes=[order_route],
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(),
            services=[user_service, order_service],
            proto_descriptors=[user_proto, order_proto],
        )

        provider = EnvoyProvider()

        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:

            def mock_get_descriptor(self, name):
                if name == "user_service":
                    return ProtoDescriptor(
                        name="user_service", source="file", path="/tmp/user.desc"
                    )
                elif name == "order_service":
                    return ProtoDescriptor(
                        name="order_service", source="file", path="/tmp/order.desc"
                    )
                return None

            mock_manager = type(
                "obj",
                (object,),
                {
                    "register_descriptor": lambda self, desc: None,
                    "get_descriptor": mock_get_descriptor,
                },
            )()
            mock_pm_class.return_value = mock_manager

            result = provider.generate(config)

        # Validate both services are present
        assert "user.v1" in result
        assert "order.v1" in result
        assert "/tmp/user.desc" in result
        assert "/tmp/order.desc" in result

    def test_nginx_integration_with_transformation(self, sample_proto_content):
        """Test Nginx provider integration with gRPC transformation."""
        proto_desc = ProtoDescriptor(
            name="user_service", source="inline", content=sample_proto_content
        )

        grpc_transform = GrpcTransformation(
            enabled=True,
            proto_descriptor="user_service",
            package="user.v1",
            service="UserService",
            request_type="CreateUserRequest",
            response_type="CreateUserResponse",
            request_transform=RequestBodyTransformation(add_fields={"trace_id": "{{uuid}}"}),
        )

        route = Route(
            path_prefix="/user.v1.UserService/CreateUser", grpc_transformation=grpc_transform
        )

        service = Service(
            name="user_api",
            type="grpc",
            protocol="http2",
            upstream=Upstream(host="grpc-backend", port=50051),
            routes=[route],
        )

        config = Config(
            version="1.0",
            provider="nginx",
            global_config=GlobalConfig(),
            services=[service],
            proto_descriptors=[proto_desc],
        )

        provider = NginxProvider()

        with patch("gal.providers.nginx.ProtoManager") as mock_pm_class:
            mock_desc = ProtoDescriptor(name="user_service", source="file", path="/tmp/user.desc")
            mock_manager = type(
                "obj",
                (object,),
                {
                    "register_descriptor": lambda self, desc: None,
                    "get_descriptor": lambda self, name: mock_desc,
                },
            )()
            mock_pm_class.return_value = mock_manager

            result = provider.generate(config)

        # Validate Nginx-specific output
        assert "access_by_lua_block" in result
        assert "ngx.req.read_body" in result
        assert "pb.decode" in result
        assert "user.v1.CreateUserRequest" in result
        assert "trace_id" in result

    def test_apisix_integration_with_transformation(self, sample_proto_content):
        """Test APISIX provider integration with gRPC transformation."""
        proto_desc = ProtoDescriptor(
            name="user_service", source="inline", content=sample_proto_content
        )

        grpc_transform = GrpcTransformation(
            enabled=True,
            proto_descriptor="user_service",
            package="user.v1",
            service="UserService",
            request_type="CreateUserRequest",
            response_type="CreateUserResponse",
            request_transform=RequestBodyTransformation(add_fields={"trace_id": "{{uuid}}"}),
        )

        route = Route(
            path_prefix="/user.v1.UserService/CreateUser", grpc_transformation=grpc_transform
        )

        service = Service(
            name="user_api",
            type="grpc",
            protocol="http2",
            upstream=Upstream(host="grpc-backend", port=50051),
            routes=[route],
        )

        config = Config(
            version="1.0",
            provider="apisix",
            global_config=GlobalConfig(),
            services=[service],
            proto_descriptors=[proto_desc],
        )

        provider = APISIXProvider()

        with patch("gal.providers.apisix.ProtoManager") as mock_pm_class:
            mock_desc = ProtoDescriptor(name="user_service", source="file", path="/tmp/user.desc")
            mock_manager = type(
                "obj",
                (object,),
                {
                    "register_descriptor": lambda self, desc: None,
                    "get_descriptor": lambda self, name: mock_desc,
                },
            )()
            mock_pm_class.return_value = mock_manager

            result = provider.generate(config)

        # Validate APISIX-specific output (JSON format)
        assert '"serverless-pre-function"' in result or "serverless-pre-function" in result
        assert "apisix.core" in result
        assert "user.v1.CreateUserRequest" in result
        assert "trace_id" in result

    def test_complex_transformation_scenario(self, sample_proto_content):
        """Test complex transformation with multiple operations."""
        proto_desc = ProtoDescriptor(
            name="user_service", source="inline", content=sample_proto_content
        )

        # Complex transformation with all operation types
        grpc_transform = GrpcTransformation(
            enabled=True,
            proto_descriptor="user_service",
            package="user.v1",
            service="UserService",
            request_type="CreateUserRequest",
            response_type="CreateUserResponse",
            request_transform=RequestBodyTransformation(
                add_fields={
                    "trace_id": "{{uuid}}",
                    "timestamp": "{{timestamp}}",
                    "server": "gateway",
                },
                remove_fields=["password", "email"],
                rename_fields={"user_id": "id", "name": "username"},
            ),
            response_transform=ResponseBodyTransformation(
                filter_fields=["secret", "password"], add_fields={"processed_by": "gateway"}
            ),
        )

        route = Route(
            path_prefix="/user.v1.UserService/CreateUser", grpc_transformation=grpc_transform
        )

        service = Service(
            name="user_api",
            type="grpc",
            protocol="http2",
            upstream=Upstream(host="grpc-backend", port=50051),
            routes=[route],
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(),
            services=[service],
            proto_descriptors=[proto_desc],
        )

        provider = EnvoyProvider()

        with patch("gal.providers.envoy.ProtoManager") as mock_pm_class:
            mock_desc = ProtoDescriptor(name="user_service", source="file", path="/tmp/user.desc")
            mock_manager = type(
                "obj",
                (object,),
                {
                    "register_descriptor": lambda self, desc: None,
                    "get_descriptor": lambda self, name: mock_desc,
                },
            )()
            mock_pm_class.return_value = mock_manager

            result = provider.generate(config)

        # Validate all transformation types are present
        assert "trace_id" in result
        assert "timestamp" in result
        assert "server" in result
        assert "password" in result  # Removal
        assert "email" in result  # Removal
        assert "user_id" in result  # Rename from
        assert "id" in result  # Rename to
        assert "name" in result  # Rename from
        assert "username" in result  # Rename to
        assert "secret" in result  # Filter
        assert "processed_by" in result  # Response add
