"""
Tests for configuration loading and models
"""

import pytest
import yaml
import tempfile
from pathlib import Path
from gal.config import (
    Config,
    Service,
    Upstream,
    Route,
    GlobalConfig,
    Transformation,
    ComputedField,
    Validation,
    Plugin
)


class TestGlobalConfig:
    """Test GlobalConfig class"""

    def test_default_values(self):
        """Test default configuration values"""
        config = GlobalConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 10000
        assert config.admin_port == 9901
        assert config.timeout == "30s"

    def test_custom_values(self):
        """Test custom configuration values"""
        config = GlobalConfig(
            host="127.0.0.1",
            port=8080,
            admin_port=9000,
            timeout="60s"
        )
        assert config.host == "127.0.0.1"
        assert config.port == 8080
        assert config.admin_port == 9000
        assert config.timeout == "60s"


class TestUpstream:
    """Test Upstream class"""

    def test_upstream_creation(self):
        """Test creating an upstream"""
        upstream = Upstream(host="service.local", port=8080)
        assert upstream.host == "service.local"
        assert upstream.port == 8080


class TestRoute:
    """Test Route class"""

    def test_route_with_path_only(self):
        """Test route with only path prefix"""
        route = Route(path_prefix="/api/v1")
        assert route.path_prefix == "/api/v1"
        assert route.methods is None

    def test_route_with_methods(self):
        """Test route with HTTP methods"""
        route = Route(path_prefix="/api/v1", methods=["GET", "POST"])
        assert route.path_prefix == "/api/v1"
        assert route.methods == ["GET", "POST"]


class TestComputedField:
    """Test ComputedField class"""

    def test_computed_field_basic(self):
        """Test basic computed field"""
        field = ComputedField(field="user_id", generator="uuid")
        assert field.field == "user_id"
        assert field.generator == "uuid"
        assert field.prefix == ""
        assert field.suffix == ""

    def test_computed_field_with_prefix_suffix(self):
        """Test computed field with prefix and suffix"""
        field = ComputedField(
            field="order_id",
            generator="uuid",
            prefix="order_",
            suffix="_v1"
        )
        assert field.field == "order_id"
        assert field.generator == "uuid"
        assert field.prefix == "order_"
        assert field.suffix == "_v1"


class TestValidation:
    """Test Validation class"""

    def test_validation_empty(self):
        """Test validation with no required fields"""
        validation = Validation()
        assert validation.required_fields == []

    def test_validation_with_fields(self):
        """Test validation with required fields"""
        validation = Validation(required_fields=["id", "name", "email"])
        assert len(validation.required_fields) == 3
        assert "id" in validation.required_fields


class TestTransformation:
    """Test Transformation class"""

    def test_transformation_defaults(self):
        """Test transformation with default values"""
        trans = Transformation()
        assert trans.enabled is True
        assert trans.defaults == {}
        assert trans.computed_fields == []
        assert trans.metadata == {}

    def test_transformation_full(self):
        """Test transformation with all fields"""
        computed = ComputedField(field="id", generator="uuid")
        validation = Validation(required_fields=["name"])

        trans = Transformation(
            enabled=True,
            defaults={"status": "active"},
            computed_fields=[computed],
            metadata={"version": "1.0"},
            validation=validation
        )

        assert trans.enabled is True
        assert trans.defaults["status"] == "active"
        assert len(trans.computed_fields) == 1
        assert trans.metadata["version"] == "1.0"
        assert trans.validation is not None


class TestService:
    """Test Service class"""

    def test_grpc_service(self):
        """Test gRPC service creation"""
        upstream = Upstream(host="grpc.local", port=9090)
        route = Route(path_prefix="/myapp.Service")

        service = Service(
            name="test_service",
            type="grpc",
            protocol="http2",
            upstream=upstream,
            routes=[route]
        )

        assert service.name == "test_service"
        assert service.type == "grpc"
        assert service.protocol == "http2"
        assert service.upstream.host == "grpc.local"
        assert len(service.routes) == 1

    def test_rest_service_with_transformation(self):
        """Test REST service with transformation"""
        upstream = Upstream(host="api.local", port=8080)
        route = Route(path_prefix="/api/users", methods=["GET", "POST"])
        trans = Transformation(
            enabled=True,
            defaults={"role": "user"}
        )

        service = Service(
            name="user_api",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route],
            transformation=trans
        )

        assert service.name == "user_api"
        assert service.type == "rest"
        assert service.transformation is not None
        assert service.transformation.defaults["role"] == "user"


class TestPlugin:
    """Test Plugin class"""

    def test_plugin_basic(self):
        """Test basic plugin"""
        plugin = Plugin(name="rate_limiting")
        assert plugin.name == "rate_limiting"
        assert plugin.enabled is True
        assert plugin.config == {}

    def test_plugin_with_config(self):
        """Test plugin with configuration"""
        plugin = Plugin(
            name="cors",
            enabled=True,
            config={"origins": ["*"], "methods": ["GET", "POST"]}
        )
        assert plugin.name == "cors"
        assert plugin.enabled is True
        assert plugin.config["origins"] == ["*"]


class TestConfig:
    """Test main Config class"""

    def test_config_creation(self):
        """Test creating a config object"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")
        service = Service(
            name="test",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=global_config,
            services=[service]
        )

        assert config.version == "1.0"
        assert config.provider == "envoy"
        assert len(config.services) == 1

    def test_get_service(self):
        """Test getting service by name"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")

        service1 = Service(
            name="service1",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )
        service2 = Service(
            name="service2",
            type="grpc",
            protocol="http2",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=global_config,
            services=[service1, service2]
        )

        found = config.get_service("service1")
        assert found is not None
        assert found.name == "service1"

        not_found = config.get_service("service3")
        assert not_found is None

    def test_get_grpc_services(self):
        """Test filtering gRPC services"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")

        rest_service = Service(
            name="rest",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )
        grpc_service = Service(
            name="grpc",
            type="grpc",
            protocol="http2",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=global_config,
            services=[rest_service, grpc_service]
        )

        grpc_services = config.get_grpc_services()
        assert len(grpc_services) == 1
        assert grpc_services[0].name == "grpc"

    def test_get_rest_services(self):
        """Test filtering REST services"""
        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")

        rest_service = Service(
            name="rest",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )
        grpc_service = Service(
            name="grpc",
            type="grpc",
            protocol="http2",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=global_config,
            services=[rest_service, grpc_service]
        )

        rest_services = config.get_rest_services()
        assert len(rest_services) == 1
        assert rest_services[0].name == "rest"

    def test_from_yaml(self):
        """Test loading configuration from YAML file"""
        yaml_content = """
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901
  timeout: 30s

services:
  - name: test_service
    type: rest
    protocol: http
    upstream:
      host: test.local
      port: 8080
    routes:
      - path_prefix: /api/test
        methods: [GET, POST]
    transformation:
      enabled: true
      defaults:
        status: active
      computed_fields:
        - field: id
          generator: uuid
          prefix: "test_"
      metadata:
        version: "1.0"
      validation:
        required_fields: [name, email]

plugins:
  - name: rate_limiting
    enabled: true
    config:
      requests_per_second: 100
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            config = Config.from_yaml(temp_file)

            assert config.version == "1.0"
            assert config.provider == "envoy"
            assert config.global_config.host == "0.0.0.0"
            assert config.global_config.port == 10000

            assert len(config.services) == 1
            service = config.services[0]
            assert service.name == "test_service"
            assert service.type == "rest"
            assert service.upstream.host == "test.local"
            assert service.upstream.port == 8080

            assert len(service.routes) == 1
            assert service.routes[0].path_prefix == "/api/test"
            assert service.routes[0].methods == ["GET", "POST"]

            assert service.transformation is not None
            assert service.transformation.enabled is True
            assert service.transformation.defaults["status"] == "active"
            assert len(service.transformation.computed_fields) == 1
            assert service.transformation.computed_fields[0].field == "id"
            assert service.transformation.computed_fields[0].generator == "uuid"
            assert service.transformation.computed_fields[0].prefix == "test_"

            assert service.transformation.validation is not None
            assert "name" in service.transformation.validation.required_fields

            assert len(config.plugins) == 1
            assert config.plugins[0].name == "rate_limiting"
            assert config.plugins[0].config["requests_per_second"] == 100
        finally:
            Path(temp_file).unlink()

    def test_from_yaml_minimal(self):
        """Test loading minimal YAML configuration"""
        yaml_content = """
version: "1.0"
provider: kong

services:
  - name: simple_service
    type: rest
    protocol: http
    upstream:
      host: simple.local
      port: 8080
    routes:
      - path_prefix: /api
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            config = Config.from_yaml(temp_file)

            assert config.version == "1.0"
            assert config.provider == "kong"
            assert config.global_config.host == "0.0.0.0"  # Default value
            assert len(config.services) == 1
            assert len(config.plugins) == 0
        finally:
            Path(temp_file).unlink()
