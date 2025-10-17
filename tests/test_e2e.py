"""
End-to-End tests for complete workflows
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from gal.manager import Manager
from gal.providers.envoy import EnvoyProvider
from gal.providers.kong import KongProvider
from gal.providers.apisix import APISIXProvider
from gal.providers.traefik import TraefikProvider
from gal.config import Config


class TestE2EBasicWorkflow:
    """Test basic end-to-end workflow: load → validate → generate"""

    @pytest.fixture
    def config_file(self, tmp_path):
        """Create test configuration file"""
        config = tmp_path / "gateway-config.yaml"
        config.write_text("""
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901
  timeout: 30

services:
  - name: user_service
    type: rest
    protocol: http
    upstream:
      host: user-backend
      port: 8080
    routes:
      - path_prefix: /api/users
        methods: [GET, POST, PUT, DELETE]
    transformation:
      enabled: true
      defaults:
        status: active
      computed_fields:
        - field: user_id
          generator: uuid
          prefix: usr_
      validation:
        required_fields:
          - email
""")
        return str(config)

    def test_complete_workflow_envoy(self, config_file, tmp_path):
        """Test complete workflow: load → validate → generate → verify"""
        # Setup
        manager = Manager()
        manager.register_provider(EnvoyProvider())

        # Step 1: Load configuration
        config = manager.load_config(config_file)
        assert config is not None
        assert config.provider == "envoy"
        assert len(config.services) == 1

        # Step 2: Validate configuration
        is_valid = manager.validate(config)
        assert is_valid is True

        # Step 3: Generate configuration
        result = manager.generate(config)
        assert result is not None
        assert "static_resources:" in result
        assert "user_service_cluster" in result

        # Step 4: Verify generated content
        assert "envoy.filters.http.lua" in result  # Transformation filter
        assert "user_service transformations" in result

        # Step 5: Write to file
        output_file = tmp_path / "envoy.yaml"
        with open(output_file, 'w') as f:
            f.write(result)

        # Step 6: Verify file exists and is readable
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_complete_workflow_all_providers(self, config_file, tmp_path):
        """Test workflow for all providers"""
        manager = Manager()
        manager.register_provider(EnvoyProvider())
        manager.register_provider(KongProvider())
        manager.register_provider(APISIXProvider())
        manager.register_provider(TraefikProvider())

        # Load config
        base_config = manager.load_config(config_file)

        providers = {
            'envoy': 'yaml',
            'kong': 'yaml',
            'apisix': 'json',
            'traefik': 'yaml'
        }

        for provider_name, extension in providers.items():
            # Switch provider
            config = Config(
                version=base_config.version,
                provider=provider_name,
                global_config=base_config.global_config,
                services=base_config.services,
                plugins=base_config.plugins
            )

            # Validate
            assert manager.validate(config) is True

            # Generate
            result = manager.generate(config)
            assert result is not None
            assert len(result) > 0

            # Write to file
            output_file = tmp_path / f"{provider_name}.{extension}"
            with open(output_file, 'w') as f:
                f.write(result)

            # Verify
            assert output_file.exists()
            assert output_file.stat().st_size > 0


class TestE2EWithDeployment:
    """Test end-to-end workflow including deployment"""

    @pytest.fixture
    def config_file(self, tmp_path):
        """Create test configuration"""
        config = tmp_path / "deploy-config.yaml"
        config.write_text("""
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
      port: 3000
    routes:
      - path_prefix: /api/v1
""")
        return str(config)

    def test_load_generate_deploy_workflow(self, config_file, tmp_path):
        """Test: load → generate → deploy (file-based)"""
        # Setup
        manager = Manager()
        provider = KongProvider()
        manager.register_provider(provider)

        # Load & validate
        config = manager.load_config(config_file)
        assert manager.validate(config) is True

        # Generate
        result = manager.generate(config)
        assert "_format_version:" in result

        # Deploy (file-based)
        output_file = tmp_path / "kong.yaml"
        deployment_result = provider.deploy(
            config,
            output_file=str(output_file)
        )

        assert deployment_result is True
        assert output_file.exists()

        # Verify deployed config
        deployed_content = output_file.read_text()
        assert deployed_content == result

    @patch('gal.providers.apisix.requests.put')
    def test_load_generate_deploy_with_api(self, mock_put, config_file, tmp_path):
        """Test: load → generate → deploy (via API)"""
        # Mock API responses
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_put.return_value = mock_response

        # Setup
        manager = Manager()
        provider = APISIXProvider()
        manager.register_provider(provider)

        # Change provider to apisix
        config = manager.load_config(config_file)
        config.provider = "apisix"

        # Validate & generate
        assert manager.validate(config) is True
        result = manager.generate(config)

        # Deploy via API
        output_file = tmp_path / "apisix.json"
        deployment_result = provider.deploy(
            config,
            output_file=str(output_file),
            admin_url="http://localhost:9180",
            api_key="test-key"
        )

        assert deployment_result is True
        assert output_file.exists()

        # Verify API was called
        assert mock_put.call_count == 3  # upstream, service, route


class TestE2EMultiService:
    """Test E2E with multiple services"""

    @pytest.fixture
    def multi_service_config(self, tmp_path):
        """Create config with multiple services"""
        config = tmp_path / "multi-service.yaml"
        config.write_text("""
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

services:
  - name: user_service
    type: grpc
    protocol: http2
    upstream:
      host: user-grpc
      port: 50051
    routes:
      - path_prefix: /user.UserService

  - name: order_service
    type: rest
    protocol: http
    upstream:
      host: order-api
      port: 8080
    routes:
      - path_prefix: /api/orders
        methods: [GET, POST]
    transformation:
      enabled: true
      defaults:
        status: pending
      computed_fields:
        - field: order_id
          generator: uuid
          prefix: ord_

  - name: payment_service
    type: rest
    protocol: http
    upstream:
      host: payment-api
      port: 8081
    routes:
      - path_prefix: /api/payments
        methods: [POST]
""")
        return str(config)

    def test_multi_service_workflow(self, multi_service_config, tmp_path):
        """Test workflow with multiple services"""
        manager = Manager()
        manager.register_provider(EnvoyProvider())

        # Load
        config = manager.load_config(multi_service_config)
        assert len(config.services) == 3
        assert len(config.get_grpc_services()) == 1
        assert len(config.get_rest_services()) == 2

        # Validate
        assert manager.validate(config) is True

        # Generate
        result = manager.generate(config)
        assert "user_service_cluster" in result
        assert "order_service_cluster" in result
        assert "payment_service_cluster" in result

        # Verify gRPC configuration
        assert "http2_protocol_options: {}" in result
        assert "/user.UserService" in result

        # Verify transformations only for order_service
        lines = result.split('\n')
        transformation_context = False
        order_transform_found = False

        for line in lines:
            if "order_service transformations" in line:
                order_transform_found = True

        assert order_transform_found is True


class TestE2EErrorHandling:
    """Test E2E error handling"""

    def test_invalid_yaml_syntax(self, tmp_path):
        """Test error handling for invalid YAML"""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("""
version: 1.0
provider: envoy
services:
  - name: test
    invalid_indent
      wrong: syntax
""")

        manager = Manager()
        manager.register_provider(EnvoyProvider())

        with pytest.raises(Exception):
            manager.load_config(str(config_file))

    def test_missing_required_field(self, tmp_path):
        """Test error handling for missing required fields"""
        config_file = tmp_path / "missing-field.yaml"
        config_file.write_text("""
version: "1.0"
provider: envoy

services:
  - name: test_service
    type: rest
    # Missing upstream
    routes:
      - path_prefix: /api
""")

        manager = Manager()
        manager.register_provider(EnvoyProvider())

        with pytest.raises(Exception):
            manager.load_config(str(config_file))

    def test_validation_error_port_zero(self, tmp_path):
        """Test validation error for port 0"""
        config_file = tmp_path / "port-zero.yaml"
        config_file.write_text("""
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 0

services:
  - name: test
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api
""")

        manager = Manager()
        manager.register_provider(EnvoyProvider())

        config = manager.load_config(str(config_file))

        with pytest.raises(ValueError, match="Port must be specified"):
            manager.validate(config)

    def test_unknown_provider(self, tmp_path):
        """Test error handling for unknown provider"""
        config_file = tmp_path / "unknown-provider.yaml"
        config_file.write_text("""
version: "1.0"
provider: unknown_gateway

services:
  - name: test
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api
""")

        manager = Manager()
        manager.register_provider(EnvoyProvider())

        config = manager.load_config(str(config_file))

        with pytest.raises(ValueError, match="Provider .* not registered"):
            manager.generate(config)


class TestE2ERealWorldScenario:
    """Test real-world scenarios"""

    @pytest.fixture
    def ecommerce_config(self, tmp_path):
        """E-commerce platform configuration"""
        config = tmp_path / "ecommerce.yaml"
        config.write_text("""
version: "1.0"
provider: apisix

global:
  host: 0.0.0.0
  port: 9080
  admin_port: 9180
  timeout: 60

services:
  - name: user_auth_service
    type: grpc
    protocol: http2
    upstream:
      host: auth-grpc
      port: 50051
    routes:
      - path_prefix: /auth.AuthService

  - name: product_catalog
    type: rest
    protocol: http
    upstream:
      host: catalog-api
      port: 8080
    routes:
      - path_prefix: /api/products
        methods: [GET]
      - path_prefix: /api/categories
        methods: [GET]

  - name: order_management
    type: rest
    protocol: http
    upstream:
      host: orders-api
      port: 8081
    routes:
      - path_prefix: /api/orders
        methods: [GET, POST, PUT]
    transformation:
      enabled: true
      defaults:
        status: pending
        currency: USD
      computed_fields:
        - field: order_id
          generator: uuid
          prefix: ord_
        - field: created_at
          generator: timestamp
      validation:
        required_fields:
          - customer_id
          - items
          - total_amount

  - name: payment_processing
    type: rest
    protocol: http
    upstream:
      host: payments-api
      port: 8082
    routes:
      - path_prefix: /api/payments
        methods: [POST]
    transformation:
      enabled: true
      computed_fields:
        - field: payment_id
          generator: uuid
          prefix: pay_
        - field: timestamp
          generator: timestamp
      validation:
        required_fields:
          - order_id
          - amount
          - payment_method
""")
        return str(config)

    def test_ecommerce_complete_workflow(self, ecommerce_config, tmp_path):
        """Test complete e-commerce platform setup"""
        manager = Manager()
        manager.register_provider(APISIXProvider())

        # Load configuration
        config = manager.load_config(ecommerce_config)
        assert len(config.services) == 4

        # Validate
        assert manager.validate(config) is True

        # Generate
        result = manager.generate(config)
        config_data = json.loads(result)

        # Verify structure
        assert "routes" in config_data
        assert "services" in config_data
        assert "upstreams" in config_data

        # Verify all services
        assert len(config_data["services"]) == 4
        assert len(config_data["upstreams"]) == 4

        # Verify transformations for order_management
        order_service = next(
            s for s in config_data["services"]
            if s["id"] == "order_management"
        )
        assert "plugins" in order_service
        assert "serverless-pre-function" in order_service["plugins"]

        # Write and verify deployment
        output_file = tmp_path / "ecommerce-apisix.json"
        with open(output_file, 'w') as f:
            f.write(result)

        assert output_file.exists()
        assert output_file.stat().st_size > 1000  # Substantial config

    def test_provider_migration_workflow(self, ecommerce_config, tmp_path):
        """Test migrating configuration between providers"""
        manager = Manager()
        manager.register_provider(APISIXProvider())
        manager.register_provider(EnvoyProvider())
        manager.register_provider(KongProvider())

        # Load base config
        base_config = manager.load_config(ecommerce_config)

        # Generate for all providers
        results = {}
        for provider_name in ['apisix', 'envoy', 'kong']:
            config = Config(
                version=base_config.version,
                provider=provider_name,
                global_config=base_config.global_config,
                services=base_config.services,
                plugins=base_config.plugins
            )

            result = manager.generate(config)
            results[provider_name] = result

            # Verify each provider generates valid config
            assert result is not None
            assert len(result) > 100

        # Verify each provider generated different formats
        assert '"routes"' in results['apisix']  # JSON
        assert 'static_resources:' in results['envoy']  # YAML
        assert '_format_version:' in results['kong']  # YAML

        # All should reference the same services
        for result in results.values():
            assert 'user_auth_service' in result or 'auth-grpc' in result
            assert 'product_catalog' in result or 'catalog-api' in result
            assert 'order_management' in result or 'orders-api' in result
            assert 'payment_processing' in result or 'payments-api' in result
