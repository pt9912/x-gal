"""
Tests for AWS API Gateway provider

Tests cover:
- OpenAPI 3.0 generation with x-amazon-apigateway extensions
- HTTP_PROXY, AWS_PROXY, and MOCK integrations
- Lambda Authorizers and Cognito User Pools
- API Keys and CORS configuration
- Validation logic
"""

import json

import pytest

from gal.config import (
    ApiKeyConfig,
    AuthenticationConfig,
    AWSAPIGatewayConfig,
    Config,
    GlobalConfig,
    JwtConfig,
    Route,
    Service,
    Upstream,
)
from gal.providers.aws_apigateway import AWSAPIGatewayProvider


class TestAWSAPIGatewayProvider:
    """Test AWS API Gateway provider basic functionality"""

    def test_provider_name(self):
        """Test provider name"""
        provider = AWSAPIGatewayProvider()
        assert provider.name() == "aws_apigateway"

    def test_parse_implemented(self):
        """Test parse method is now implemented"""
        provider = AWSAPIGatewayProvider()
        # Parse method is now implemented, should accept valid OpenAPI
        openapi_spec = json.dumps(
            {"openapi": "3.0.1", "info": {"title": "Test", "version": "1.0"}, "paths": {}}
        )
        config = provider.parse(openapi_spec)
        assert config is not None
        assert config.version == "1.0"


class TestAWSAPIGatewayValidation:
    """Test AWS API Gateway configuration validation"""

    def test_validate_basic_config(self):
        """Test validation of basic valid configuration"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[Route(path_prefix="/api", methods=["GET"])],
                )
            ],
        )

        assert provider.validate(config) is True

    def test_validate_no_services(self):
        """Test validation fails when no services defined"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(),
            services=[],
        )

        with pytest.raises(ValueError, match="At least one service is required"):
            provider.validate(config)

    def test_validate_missing_upstream(self):
        """Test validation fails when upstream is missing"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=None,
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        with pytest.raises(ValueError, match="upstream configuration is required"):
            provider.validate(config)

    def test_validate_missing_upstream_host(self):
        """Test validation fails when upstream host is missing"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host=None, port=443),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        with pytest.raises(ValueError, match="upstream host is required"):
            provider.validate(config)

    def test_validate_no_routes(self):
        """Test validation fails when no routes defined"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[],
                )
            ],
        )

        with pytest.raises(ValueError, match="at least one route is required"):
            provider.validate(config)

    def test_validate_invalid_integration_type(self):
        """Test validation fails for invalid integration type"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(integration_type="INVALID")
            ),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        with pytest.raises(ValueError, match="Invalid integration_type"):
            provider.validate(config)

    def test_validate_aws_proxy_without_lambda_arn(self):
        """Test validation fails when AWS_PROXY without Lambda ARN"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(
                    integration_type="AWS_PROXY", lambda_function_arn=None
                )
            ),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        with pytest.raises(ValueError, match="lambda_function_arn is required"):
            provider.validate(config)

    def test_validate_invalid_authorizer_type(self):
        """Test validation fails for invalid authorizer type"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(authorizer_type="invalid")
            ),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        with pytest.raises(ValueError, match="Invalid authorizer_type"):
            provider.validate(config)

    def test_validate_lambda_authorizer_without_arn(self):
        """Test validation fails when lambda authorizer without ARN"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(
                    authorizer_type="lambda", lambda_authorizer_arn=None
                )
            ),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        with pytest.raises(ValueError, match="lambda_authorizer_arn is required"):
            provider.validate(config)

    def test_validate_cognito_authorizer_without_pool_arns(self):
        """Test validation fails when cognito authorizer without pool ARNs"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(
                    authorizer_type="cognito", cognito_user_pool_arns=[]
                )
            ),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        with pytest.raises(ValueError, match="cognito_user_pool_arns is required"):
            provider.validate(config)

    def test_validate_invalid_endpoint_type(self):
        """Test validation fails for invalid endpoint type"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(aws_apigateway=AWSAPIGatewayConfig(endpoint_type="INVALID")),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        with pytest.raises(ValueError, match="Invalid endpoint_type"):
            provider.validate(config)


class TestAWSAPIGatewayGeneration:
    """Test OpenAPI 3.0 generation with AWS extensions"""

    def test_generate_basic_http_proxy(self):
        """Test basic HTTP_PROXY integration generation"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(
                    api_name="Test-API",
                    api_description="Test API",
                    endpoint_type="REGIONAL",
                    stage_name="prod",
                    integration_type="HTTP_PROXY",
                )
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="backend.example.com", port=443),
                    routes=[
                        Route(path_prefix="/api/users", methods=["GET", "POST"]),
                    ],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Check OpenAPI version
        assert openapi["openapi"] == "3.0.1"

        # Check info
        assert openapi["info"]["title"] == "Test-API"
        assert openapi["info"]["description"] == "Test API"
        assert openapi["info"]["version"] == "1.0"

        # Check servers
        assert len(openapi["servers"]) == 1
        assert "{api_id}.execute-api.{region}.amazonaws.com" in openapi["servers"][0]["url"]

        # Check paths
        assert "/api/users" in openapi["paths"]
        assert "get" in openapi["paths"]["/api/users"]
        assert "post" in openapi["paths"]["/api/users"]

        # Check HTTP_PROXY integration
        get_integration = openapi["paths"]["/api/users"]["get"]["x-amazon-apigateway-integration"]
        assert get_integration["type"] == "http_proxy"
        assert get_integration["httpMethod"] == "GET"
        assert "https://backend.example.com/api/users" in get_integration["uri"]

    def test_generate_lambda_integration(self):
        """Test AWS_PROXY (Lambda) integration generation"""
        provider = AWSAPIGatewayProvider()

        lambda_arn = "arn:aws:lambda:us-east-1:123456789012:function:my-function"

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(
                    api_name="Lambda-API",
                    integration_type="AWS_PROXY",
                    lambda_function_arn=lambda_arn,
                )
            ),
            services=[
                Service(
                    name="lambda_service",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="lambda", port=443),
                    routes=[
                        Route(path_prefix="/lambda", methods=["POST"]),
                    ],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Check Lambda integration
        integration = openapi["paths"]["/lambda"]["post"]["x-amazon-apigateway-integration"]
        assert integration["type"] == "aws_proxy"
        assert integration["httpMethod"] == "POST"
        assert lambda_arn in integration["uri"]

    def test_generate_mock_integration(self):
        """Test MOCK integration generation"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(api_name="Mock-API", integration_type="MOCK")
            ),
            services=[
                Service(
                    name="mock_service",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="mock", port=443),
                    routes=[
                        Route(path_prefix="/mock", methods=["GET"]),
                    ],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Check MOCK integration
        integration = openapi["paths"]["/mock"]["get"]["x-amazon-apigateway-integration"]
        assert integration["type"] == "mock"
        assert "requestTemplates" in integration

    def test_generate_with_api_keys(self):
        """Test API Key security scheme generation"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(
                    api_name="Secured-API",
                    api_key_required=True,
                    api_key_source="HEADER",
                )
            ),
            services=[
                Service(
                    name="secured_service",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="api.example.com", port=443),
                    routes=[
                        Route(path_prefix="/secure", methods=["GET"]),
                    ],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Check API key source extension
        assert openapi["x-amazon-apigateway-api-key-source"] == "HEADER"

        # Check security scheme
        assert "api_key" in openapi["components"]["securitySchemes"]
        api_key_scheme = openapi["components"]["securitySchemes"]["api_key"]
        assert api_key_scheme["type"] == "apiKey"
        assert api_key_scheme["name"] == "x-api-key"
        assert api_key_scheme["in"] == "header"

        # Check security is applied to operation
        operation = openapi["paths"]["/secure"]["get"]
        assert "security" in operation
        assert {"api_key": []} in operation["security"]

    def test_generate_with_lambda_authorizer(self):
        """Test Lambda Authorizer security scheme generation"""
        provider = AWSAPIGatewayProvider()

        authorizer_arn = "arn:aws:lambda:us-east-1:123456789012:function:my-authorizer"

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(
                    api_name="Auth-API",
                    authorizer_type="lambda",
                    lambda_authorizer_arn=authorizer_arn,
                    lambda_authorizer_ttl=300,
                )
            ),
            services=[
                Service(
                    name="auth_service",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="api.example.com", port=443),
                    routes=[
                        Route(
                            path_prefix="/protected",
                            methods=["GET"],
                            authentication=AuthenticationConfig(
                                type="jwt",
                                jwt=JwtConfig(
                                    issuer="https://auth.example.com",
                                    audience="my-api",
                                ),
                            ),
                        ),
                    ],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Check Lambda authorizer security scheme
        assert "lambda_authorizer" in openapi["components"]["securitySchemes"]
        authorizer_scheme = openapi["components"]["securitySchemes"]["lambda_authorizer"]
        assert authorizer_scheme["type"] == "apiKey"
        assert authorizer_scheme["name"] == "Authorization"
        assert authorizer_scheme["x-amazon-apigateway-authtype"] == "custom"

        # Check authorizer configuration
        authorizer_config = authorizer_scheme["x-amazon-apigateway-authorizer"]
        assert authorizer_config["type"] == "token"
        assert authorizer_arn in authorizer_config["authorizerUri"]
        assert authorizer_config["authorizerResultTtlInSeconds"] == 300

    def test_generate_with_cognito_authorizer(self):
        """Test Cognito User Pool authorizer generation"""
        provider = AWSAPIGatewayProvider()

        user_pool_arn = "arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_AbCdEfGhI"

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(
                    api_name="Cognito-API",
                    authorizer_type="cognito",
                    cognito_user_pool_arns=[user_pool_arn],
                )
            ),
            services=[
                Service(
                    name="cognito_service",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="api.example.com", port=443),
                    routes=[
                        Route(path_prefix="/user", methods=["GET"]),
                    ],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Check Cognito authorizer security scheme
        assert "cognito_authorizer" in openapi["components"]["securitySchemes"]
        cognito_scheme = openapi["components"]["securitySchemes"]["cognito_authorizer"]
        assert cognito_scheme["type"] == "apiKey"
        assert cognito_scheme["name"] == "Authorization"
        assert cognito_scheme["x-amazon-apigateway-authtype"] == "cognito_user_pools"

        # Check Cognito configuration
        cognito_config = cognito_scheme["x-amazon-apigateway-authorizer"]
        assert cognito_config["type"] == "cognito_user_pools"
        assert user_pool_arn in cognito_config["providerARNs"]

    def test_generate_with_cors(self):
        """Test CORS configuration generation"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(
                    api_name="CORS-API",
                    cors_enabled=True,
                    cors_allow_origins=["https://app.example.com"],
                    cors_allow_methods=["GET", "POST", "PUT", "DELETE"],
                    cors_allow_headers=["Content-Type", "Authorization"],
                )
            ),
            services=[
                Service(
                    name="cors_service",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="api.example.com", port=443),
                    routes=[
                        Route(path_prefix="/api", methods=["GET", "POST"]),
                    ],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Check OPTIONS method is added
        assert "options" in openapi["paths"]["/api"]
        options_method = openapi["paths"]["/api"]["options"]

        # Check CORS headers in response
        assert "200" in options_method["responses"]
        assert "headers" in options_method["responses"]["200"]

        # Check CORS integration
        cors_integration = options_method["x-amazon-apigateway-integration"]
        assert cors_integration["type"] == "mock"
        assert "responseParameters" in cors_integration["responses"]["default"]

        # Verify CORS headers values
        response_params = cors_integration["responses"]["default"]["responseParameters"]
        assert "method.response.header.Access-Control-Allow-Origin" in response_params
        assert (
            "https://app.example.com"
            in response_params["method.response.header.Access-Control-Allow-Origin"]
        )

    def test_generate_multiple_routes(self):
        """Test generation with multiple routes and methods"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="multi_route_service",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="api.example.com", port=443),
                    routes=[
                        Route(path_prefix="/users", methods=["GET", "POST"]),
                        Route(path_prefix="/users/{id}", methods=["GET", "PUT", "DELETE"]),
                        Route(path_prefix="/products", methods=["GET"]),
                    ],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Check all paths exist
        assert "/users" in openapi["paths"]
        assert "/users/{id}" in openapi["paths"]
        assert "/products" in openapi["paths"]

        # Check methods for /users
        assert "get" in openapi["paths"]["/users"]
        assert "post" in openapi["paths"]["/users"]

        # Check methods for /users/{id}
        assert "get" in openapi["paths"]["/users/{id}"]
        assert "put" in openapi["paths"]["/users/{id}"]
        assert "delete" in openapi["paths"]["/users/{id}"]

        # Check integrations exist
        assert "x-amazon-apigateway-integration" in openapi["paths"]["/users"]["get"]
        assert "x-amazon-apigateway-integration" in openapi["paths"]["/users/{id}"]["delete"]

    def test_generate_with_custom_timeout(self):
        """Test custom integration timeout configuration"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(
                aws_apigateway=AWSAPIGatewayConfig(
                    api_name="Timeout-API", integration_timeout_ms=15000
                )
            ),
            services=[
                Service(
                    name="timeout_service",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="api.example.com", port=443),
                    routes=[
                        Route(path_prefix="/slow", methods=["GET"]),
                    ],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Check timeout is set correctly
        integration = openapi["paths"]["/slow"]["get"]["x-amazon-apigateway-integration"]
        assert integration["timeoutInMillis"] == 15000


class TestAWSAPIGatewayEdgeCases:
    """Test edge cases and error handling"""

    def test_generate_with_missing_global_config(self):
        """Test generation works with missing global_config (uses defaults)"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=None,
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[Route(path_prefix="/api")],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Should use defaults
        assert openapi["info"]["title"] == "GAL-API"
        assert openapi["info"]["description"] == "API managed by GAL"

    def test_generate_with_default_methods(self):
        """Test generation with routes without methods (should default to GET)"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[Route(path_prefix="/api", methods=None)],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Should default to GET
        assert "get" in openapi["paths"]["/api"]

    def test_generate_normalizes_path(self):
        """Test path normalization (adds leading slash)"""
        provider = AWSAPIGatewayProvider()

        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=GlobalConfig(),
            services=[
                Service(
                    name="test",
                    type="rest",
                    protocol="https",
                    upstream=Upstream(host="example.com", port=443),
                    routes=[Route(path_prefix="api/users", methods=["GET"])],
                )
            ],
        )

        result = provider.generate(config)
        openapi = json.loads(result)

        # Path should be normalized
        assert "/api/users" in openapi["paths"]
