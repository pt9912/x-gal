"""
Tests for Azure API Management provider.

Test coverage:
- ARM Template generation
- Policy XML generation
- OpenAPI export
- Validation
"""

import json
import pytest

from gal.config import (
    ActiveHealthCheck,
    AzureAPIMConfig,
    AzureAPIMGlobalConfig,
    Config,
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
from gal.providers.azure_apim import AzureAPIMProvider


class TestAzureAPIMProviderBasics:
    """Test Azure APIM provider basic functionality."""

    def test_provider_name(self):
        """Test provider name is correct."""
        provider = AzureAPIMProvider()
        assert provider.name() == "azure_apim"

    def test_provider_initialization(self):
        """Test provider initializes correctly."""
        provider = AzureAPIMProvider()
        assert provider is not None
        assert isinstance(provider, AzureAPIMProvider)


class TestAzureAPIMARMTemplateGeneration:
    """Test ARM Template generation."""

    def test_generate_empty_config(self):
        """Test ARM template generation with minimal config."""
        provider = AzureAPIMProvider()
        config = Config(
            version="1.0",
            provider="azure_apim",
            global_config=GlobalConfig(),
            services=[]
        )

        output = provider.generate(config)
        assert output is not None

        # Parse JSON
        arm_template = json.loads(output)
        assert arm_template["$schema"] == "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
        assert arm_template["contentVersion"] == "1.0.0.0"
        assert "resources" in arm_template

    def test_generate_single_service(self):
        """Test ARM template with single service."""
        provider = AzureAPIMProvider()
        config = Config(
            version="1.0",
            provider="azure_apim",
            global_config=GlobalConfig(
                azure_apim=AzureAPIMGlobalConfig(
                    resource_group="test-rg",
                    apim_service_name="test-apim",
                    location="westeurope",
                    sku="Developer"
                )
            ),
            services=[
                Service(
                    name="test_api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[
                            UpstreamTarget(host="backend.example.com", port=443)
                        ]
                    ),
                    routes=[
                        Route(path_prefix="/api/users")
                    ],
                    azure_apim=AzureAPIMConfig(
                        product_name="TestProduct",
                        api_revision="1",
                        api_version="v1"
                    )
                )
            ]
        )

        output = provider.generate(config)
        arm_template = json.loads(output)

        # Check resources exist
        assert len(arm_template["resources"]) > 0

        # Find APIM Service resource
        apim_service = next(
            (r for r in arm_template["resources"] if r["type"] == "Microsoft.ApiManagement/service"),
            None
        )
        assert apim_service is not None
        assert apim_service["location"] == "westeurope"
        assert apim_service["sku"]["name"] == "Developer"

    def test_generate_api_resource(self):
        """Test API resource generation."""
        provider = AzureAPIMProvider()
        config = Config(
            version="1.0",
            provider="azure_apim",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="user_api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="api.example.com", port=443)]
                    ),
                    routes=[
                        Route(path_prefix="/api/users")
                    ],
                    azure_apim=AzureAPIMConfig(
                        product_name="UserAPI",
                        api_revision="2",
                        api_version="v2"
                    )
                )
            ]
        )

        output = provider.generate(config)
        arm_template = json.loads(output)

        # Find API resource
        api_resource = next(
            (r for r in arm_template["resources"] if r["type"] == "Microsoft.ApiManagement/service/apis"),
            None
        )
        assert api_resource is not None
        assert api_resource["properties"]["displayName"] == "user_api"
        assert api_resource["properties"]["apiRevision"] == "2"
        assert api_resource["properties"]["apiVersion"] == "v2"


class TestAzureAPIMPolicyGeneration:
    """Test Policy XML generation."""

    def test_rate_limit_policy(self):
        """Test rate limiting policy generation."""
        provider = AzureAPIMProvider()
        service = Service(
            name="test_api",
            type="rest",
            protocol="http",
            upstream=Upstream(
                targets=[UpstreamTarget(host="backend.example.com", port=443)]
            ),
            routes=[]
        )
        route = Route(
            path_prefix="/api/test",
            rate_limit=RateLimitConfig(enabled=True, requests_per_second=100)
        )

        policy_xml = provider._build_policy_xml(service, route)

        assert "<policies>" in policy_xml
        assert "<rate-limit calls=\"6000\" renewal-period=\"60\" />" in policy_xml
        assert "</policies>" in policy_xml

    def test_header_manipulation_policy(self):
        """Test header manipulation policy."""
        provider = AzureAPIMProvider()
        service = Service(
            name="test_api",
            type="rest",
            protocol="http",
            upstream=Upstream(
                targets=[UpstreamTarget(host="backend.example.com", port=443)]
            ),
            routes=[]
        )
        route = Route(
            path_prefix="/api/test",
            headers=HeaderManipulation(
                request_add={"X-Custom-Header": "value1"},
                response_add={"X-Response-Header": "value2"}
            )
        )

        policy_xml = provider._build_policy_xml(service, route)

        # Check request headers in inbound section
        assert '<set-header name="X-Custom-Header" exists-action="override">' in policy_xml
        assert "<value>value1</value>" in policy_xml

        # Check response headers in outbound section
        assert '<set-header name="X-Response-Header" exists-action="override">' in policy_xml
        assert "<value>value2</value>" in policy_xml

    def test_backend_url_policy(self):
        """Test backend URL setting in policy."""
        provider = AzureAPIMProvider()
        service = Service(
            name="test_api",
            type="rest",
            protocol="http",
            upstream=Upstream(
                targets=[UpstreamTarget(host="backend.example.com", port=443)]
            ),
            routes=[]
        )
        route = Route(path_prefix="/api/test")

        policy_xml = provider._build_policy_xml(service, route)

        assert '<set-backend-service base-url="https://backend.example.com:443" />' in policy_xml


class TestAzureAPIMProductGeneration:
    """Test Product resource generation."""

    def test_product_resource(self):
        """Test product generation."""
        provider = AzureAPIMProvider()
        service = Service(
            name="test_api",
            type="rest",
            protocol="http",
            upstream=Upstream(
                targets=[UpstreamTarget(host="backend.example.com", port=443)]
            ),
            routes=[],
            azure_apim=AzureAPIMConfig(
                product_name="Premium-Product",
                product_description="Premium tier product",
                product_published=True,
                product_subscription_required=True
            )
        )

        product = provider._generate_product(service)

        assert product["type"] == "Microsoft.ApiManagement/service/products"
        assert product["properties"]["displayName"] == "Premium-Product"
        assert product["properties"]["description"] == "Premium tier product"
        assert product["properties"]["subscriptionRequired"] is True
        assert product["properties"]["state"] == "published"


class TestAzureAPIMBackendGeneration:
    """Test Backend resource generation."""

    def test_backend_resource(self):
        """Test backend generation."""
        provider = AzureAPIMProvider()
        service = Service(
            name="test_api",
            type="rest",
            protocol="http",
            upstream=Upstream(
                targets=[UpstreamTarget(host="api.backend.com", port=8080)]
            ),
            routes=[]
        )

        backend = provider._generate_backend(service)

        assert backend["type"] == "Microsoft.ApiManagement/service/backends"
        assert backend["properties"]["url"] == "http://api.backend.com:8080"
        assert backend["properties"]["protocol"] == "http"

    def test_backend_https(self):
        """Test backend with HTTPS port."""
        provider = AzureAPIMProvider()
        service = Service(
            name="test_api",
            type="rest",
            protocol="http",
            upstream=Upstream(
                targets=[UpstreamTarget(host="secure.backend.com", port=443)]
            ),
            routes=[]
        )

        backend = provider._generate_backend(service)

        assert backend["properties"]["url"] == "https://secure.backend.com:443"


class TestAzureAPIMOpenAPIExport:
    """Test OpenAPI 3.0 export functionality."""

    def test_openapi_export(self):
        """Test OpenAPI spec generation."""
        provider = AzureAPIMProvider()
        config = Config(
            version="1.0",
            provider="azure_apim",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="user_api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="api.example.com", port=443)]
                    ),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            methods=["GET", "POST"]
                        )
                    ]
                )
            ]
        )

        openapi_json = provider.generate_openapi(config)
        openapi_spec = json.loads(openapi_json)

        assert openapi_spec["openapi"] == "3.0.0"
        assert openapi_spec["info"]["title"] == "GAL API"
        assert "/api/users" in openapi_spec["paths"]
        assert "get" in openapi_spec["paths"]["/api/users"]
        assert "post" in openapi_spec["paths"]["/api/users"]


class TestAzureAPIMValidation:
    """Test configuration validation."""

    def test_validate_valid_config(self):
        """Test validation with valid config."""
        provider = AzureAPIMProvider()
        config = Config(
            version="1.0",
            provider="azure_apim",
            global_config=GlobalConfig(
                azure_apim=AzureAPIMGlobalConfig()
            ),
            services=[
                Service(
                    name="test_api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="backend.example.com", port=443)]
                    ),
                    routes=[Route(path_prefix="/api/test")],
                    azure_apim=AzureAPIMConfig(
                        product_name="TestProduct",
                        api_revision="1"
                    )
                )
            ]
        )

        result = provider.validate(config)
        assert result is True

    def test_validate_missing_product_name(self):
        """Test validation fails with missing product name."""
        provider = AzureAPIMProvider()
        config = Config(
            version="1.0",
            provider="azure_apim",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="test_api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="backend.example.com", port=443)]
                    ),
                    routes=[Route(path_prefix="/api/test")],
                    azure_apim=AzureAPIMConfig(
                        product_name="",  # Empty product name
                        api_revision="1"
                    )
                )
            ]
        )

        with pytest.raises(ValueError, match="product_name is required"):
            provider.validate(config)


class TestAzureAPIMEdgeCases:
    """Test edge cases and error handling."""

    def test_service_without_azure_apim_config(self):
        """Test service without Azure APIM specific config."""
        provider = AzureAPIMProvider()
        config = Config(
            version="1.0",
            provider="azure_apim",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="test_api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="backend.example.com", port=443)]
                    ),
                    routes=[Route(path_prefix="/api/test")]
                    # No azure_apim config
                )
            ]
        )

        # Should not fail, use defaults
        output = provider.generate(config)
        assert output is not None
        arm_template = json.loads(output)
        assert len(arm_template["resources"]) > 0

    def test_service_without_upstream(self):
        """Test service without upstream targets."""
        provider = AzureAPIMProvider()
        service = Service(
            name="test_api",
            type="rest",
            protocol="http",
            upstream=Upstream(targets=[]),  # No targets
            routes=[]
        )

        backend = provider._generate_backend(service)
        assert backend == {}  # Should return empty dict

    def test_route_without_http_methods(self):
        """Test route without explicit HTTP methods."""
        provider = AzureAPIMProvider()
        config = Config(
            version="1.0",
            provider="azure_apim",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="test_api",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="backend.example.com", port=443)]
                    ),
                    routes=[
                        Route(path_prefix="/api/test")  # No http_methods
                    ]
                )
            ]
        )

        output = provider.generate(config)
        arm_template = json.loads(output)

        # Should default to GET
        operation = next(
            (r for r in arm_template["resources"] if r["type"] == "Microsoft.ApiManagement/service/apis/operations"),
            None
        )
        assert operation is not None
        assert operation["properties"]["method"] == "GET"
