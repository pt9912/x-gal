"""
AWS API Gateway Provider

Generates OpenAPI 3.0 specifications with x-amazon-apigateway extensions
for AWS API Gateway deployment.

Features:
- HTTP_PROXY, AWS_PROXY (Lambda), and MOCK integrations
- Lambda Authorizers and Cognito User Pools
- API Keys and Usage Plans
- CORS configuration
- Stage variables and deployment settings

OpenAPI 3.0 Extensions Used:
- x-amazon-apigateway-integration: Backend integration configuration
- x-amazon-apigateway-request-validator: Request validation
- x-amazon-apigateway-authorizer: Custom authorizers
- x-amazon-apigateway-api-key-source: API key source configuration

References:
- https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions.html
- https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations.html
"""

from typing import Dict, List, Any, Optional
from dataclasses import asdict
import json
import yaml

from gal.config import (
    Config,
    Service,
    Route,
    GlobalConfig,
    AWSAPIGatewayConfig,
)
from gal.provider import Provider


class AWSAPIGatewayProvider(Provider):
    """
    AWS API Gateway Provider

    Generates OpenAPI 3.0 specifications with AWS-specific extensions
    for deployment to AWS API Gateway (REST APIs).

    Supported Features:
    - HTTP_PROXY integration (proxy to backend services)
    - AWS_PROXY integration (Lambda functions)
    - Lambda Authorizers
    - Cognito User Pools Authorization
    - API Keys and Usage Plans
    - CORS configuration
    - Rate limiting via Usage Plans
    - Request/Response transformations

    Limitations (v1.4.0):
    - No VTL (Velocity Template Language) templates
    - No request/response mapping templates
    - Basic authorizer support only
    - No WAF integration
    - No private API configuration
    """

    def name(self) -> str:
        """Return the provider name."""
        return "aws_apigateway"

    def validate(self, config: Config) -> bool:
        """
        Validate AWS API Gateway configuration.

        Args:
            config: GAL configuration to validate

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Check if services exist
        if not config.services:
            raise ValueError("At least one service is required")

        # Validate each service
        for service in config.services:
            if not service.upstream:
                raise ValueError(f"Service {service.name}: upstream configuration is required")

            if not service.upstream.host:
                raise ValueError(f"Service {service.name}: upstream host is required")

            # Validate routes
            if not service.routes:
                raise ValueError(f"Service {service.name}: at least one route is required")

        # Validate AWS-specific config
        aws_config = self._get_aws_config(config.global_config)

        # Validate integration type
        valid_integration_types = ["HTTP_PROXY", "AWS_PROXY", "MOCK"]
        if aws_config.integration_type not in valid_integration_types:
            raise ValueError(
                f"Invalid integration_type: {aws_config.integration_type}. "
                f"Must be one of: {', '.join(valid_integration_types)}"
            )

        # Validate Lambda ARN if using AWS_PROXY
        if aws_config.integration_type == "AWS_PROXY" and not aws_config.lambda_function_arn:
            raise ValueError(
                "lambda_function_arn is required when integration_type is AWS_PROXY"
            )

        # Validate authorizer configuration
        if aws_config.authorizer_type:
            valid_authorizer_types = ["lambda", "cognito", "iam"]
            if aws_config.authorizer_type not in valid_authorizer_types:
                raise ValueError(
                    f"Invalid authorizer_type: {aws_config.authorizer_type}. "
                    f"Must be one of: {', '.join(valid_authorizer_types)}"
                )

            if aws_config.authorizer_type == "lambda" and not aws_config.lambda_authorizer_arn:
                raise ValueError(
                    "lambda_authorizer_arn is required when authorizer_type is lambda"
                )

            if aws_config.authorizer_type == "cognito" and not aws_config.cognito_user_pool_arns:
                raise ValueError(
                    "cognito_user_pool_arns is required when authorizer_type is cognito"
                )

        # Validate endpoint type
        valid_endpoint_types = ["REGIONAL", "EDGE", "PRIVATE"]
        if aws_config.endpoint_type not in valid_endpoint_types:
            raise ValueError(
                f"Invalid endpoint_type: {aws_config.endpoint_type}. "
                f"Must be one of: {', '.join(valid_endpoint_types)}"
            )

        return True

    def parse(self, provider_config: str) -> Config:
        """
        Parse AWS API Gateway OpenAPI 3.0 export to GAL Config.

        AWS API Gateway supports exporting APIs as OpenAPI 3.0 with
        x-amazon-apigateway extensions. This method parses those exports.

        Args:
            provider_config: OpenAPI 3.0 JSON/YAML from AWS API Gateway export

        Returns:
            GAL Config object

        Raises:
            NotImplementedError: Import functionality coming in next phase
        """
        # TODO: Implement AWS API Gateway import in next phase
        # Similar to Azure APIM, we'll parse OpenAPI 3.0 exports
        raise NotImplementedError(
            "AWS API Gateway import will be implemented in next phase. "
            "Use 'aws apigateway get-export' to export OpenAPI 3.0 spec."
        )

    def generate(self, config: Config) -> str:
        """
        Generate AWS API Gateway OpenAPI 3.0 specification.

        Produces an OpenAPI 3.0 document with x-amazon-apigateway extensions
        that can be imported into AWS API Gateway.

        Args:
            config: GAL configuration

        Returns:
            OpenAPI 3.0 JSON string with AWS extensions
        """
        # Get AWS-specific config or use defaults
        aws_config = self._get_aws_config(config.global_config)

        # Build OpenAPI 3.0 base structure
        openapi_spec = {
            "openapi": "3.0.1",
            "info": {
                "title": aws_config.api_name,
                "description": aws_config.api_description,
                "version": config.version,
            },
            "servers": self._build_servers(aws_config),
            "paths": {},
            "components": {
                "securitySchemes": {},
                "schemas": {},
            },
        }

        # Add AWS-specific extensions at API level
        if aws_config.api_key_required:
            openapi_spec["x-amazon-apigateway-api-key-source"] = aws_config.api_key_source

        # Process each service
        for service in config.services:
            self._add_service_paths(
                openapi_spec,
                service,
                aws_config,
                config.global_config
            )

        # Add security schemes
        self._add_security_schemes(openapi_spec, aws_config, config.global_config)

        # Add CORS configuration
        if aws_config.cors_enabled:
            self._add_cors_configuration(openapi_spec, aws_config)

        # Return formatted JSON
        return json.dumps(openapi_spec, indent=2)

    def _get_aws_config(self, global_config: Optional[GlobalConfig]) -> AWSAPIGatewayConfig:
        """Extract or create AWS API Gateway configuration."""
        if global_config and hasattr(global_config, 'aws_apigateway'):
            return global_config.aws_apigateway
        return AWSAPIGatewayConfig()

    def _build_servers(self, aws_config: AWSAPIGatewayConfig) -> List[Dict[str, Any]]:
        """
        Build OpenAPI servers section.

        For AWS API Gateway, servers are typically set during deployment.
        We provide a placeholder that will be replaced by AWS.
        """
        return [
            {
                "url": "https://{api_id}.execute-api.{region}.amazonaws.com/{stage}",
                "variables": {
                    "api_id": {
                        "default": "example",
                        "description": "API Gateway API ID (auto-generated)"
                    },
                    "region": {
                        "default": "us-east-1",
                        "description": "AWS Region"
                    },
                    "stage": {
                        "default": aws_config.stage_name,
                        "description": "API Gateway Stage"
                    }
                }
            }
        ]

    def _add_service_paths(
        self,
        openapi_spec: Dict[str, Any],
        service: Service,
        aws_config: AWSAPIGatewayConfig,
        global_config: Optional[GlobalConfig]
    ) -> None:
        """Add service routes to OpenAPI paths."""
        for route in service.routes:
            path = route.path_prefix or "/"

            # Normalize path for OpenAPI
            if not path.startswith("/"):
                path = f"/{path}"

            # Create path entry if not exists
            if path not in openapi_spec["paths"]:
                openapi_spec["paths"][path] = {}

            # Add methods
            methods = route.methods if route.methods else ["GET"]
            for method in methods:
                method_lower = method.lower()

                # Build operation
                operation = self._build_operation(
                    service,
                    route,
                    method,
                    aws_config,
                    global_config
                )

                openapi_spec["paths"][path][method_lower] = operation

            # Add OPTIONS for CORS if enabled
            if aws_config.cors_enabled and "options" not in openapi_spec["paths"][path]:
                openapi_spec["paths"][path]["options"] = self._build_cors_options(
                    aws_config
                )

    def _build_operation(
        self,
        service: Service,
        route: Route,
        method: str,
        aws_config: AWSAPIGatewayConfig,
        global_config: Optional[GlobalConfig]
    ) -> Dict[str, Any]:
        """Build OpenAPI operation with AWS integration."""
        operation = {
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object"
                            }
                        }
                    }
                }
            }
        }

        # Add security if configured
        if route.authentication:
            security_scheme = self._get_security_scheme_name(route.authentication.type)
            if security_scheme:
                operation["security"] = [{security_scheme: []}]
        elif aws_config.api_key_required:
            operation["security"] = [{"api_key": []}]

        # Add AWS integration extension
        operation["x-amazon-apigateway-integration"] = self._build_integration(
            service,
            route,
            method,
            aws_config
        )

        return operation

    def _build_integration(
        self,
        service: Service,
        route: Route,
        method: str,
        aws_config: AWSAPIGatewayConfig
    ) -> Dict[str, Any]:
        """
        Build x-amazon-apigateway-integration object.

        Supports:
        - HTTP_PROXY: Direct proxy to HTTP backend
        - AWS_PROXY: Lambda function integration
        - MOCK: Mock responses (for testing)
        """
        integration_type = aws_config.integration_type

        if integration_type == "AWS_PROXY" and aws_config.lambda_function_arn:
            # Lambda integration
            return self._build_lambda_integration(aws_config)

        elif integration_type == "MOCK":
            # Mock integration
            return self._build_mock_integration()

        else:
            # HTTP_PROXY (default)
            return self._build_http_proxy_integration(service, route, method, aws_config)

    def _build_http_proxy_integration(
        self,
        service: Service,
        route: Route,
        method: str,
        aws_config: AWSAPIGatewayConfig
    ) -> Dict[str, Any]:
        """Build HTTP_PROXY integration for backend services."""
        # Construct backend URL
        protocol = service.protocol if service.protocol else "http"
        host = service.upstream.host
        port = service.upstream.port if service.upstream.port else (443 if protocol == "https" else 80)
        path = route.path_prefix or "/"

        # Build full URI
        if port in [80, 443]:
            uri = f"{protocol}://{host}{path}"
        else:
            uri = f"{protocol}://{host}:{port}{path}"

        integration = {
            "type": "http_proxy",
            "httpMethod": method,
            "uri": uri,
            "connectionType": "INTERNET",
            "timeoutInMillis": aws_config.integration_timeout_ms,
            "passthroughBehavior": "when_no_match",
            "requestParameters": {},
            "responses": {
                "default": {
                    "statusCode": "200"
                }
            }
        }

        return integration

    def _build_lambda_integration(
        self,
        aws_config: AWSAPIGatewayConfig
    ) -> Dict[str, Any]:
        """Build AWS_PROXY integration for Lambda functions."""
        integration = {
            "type": "aws_proxy",
            "httpMethod": "POST",
            "uri": f"arn:aws:apigateway:{{region}}:lambda:path/2015-03-31/functions/{aws_config.lambda_function_arn}/invocations",
            "passthroughBehavior": "when_no_match",
            "timeoutInMillis": aws_config.integration_timeout_ms,
        }

        if aws_config.lambda_invoke_role_arn:
            integration["credentials"] = aws_config.lambda_invoke_role_arn

        return integration

    def _build_mock_integration(self) -> Dict[str, Any]:
        """Build MOCK integration for testing."""
        return {
            "type": "mock",
            "requestTemplates": {
                "application/json": '{"statusCode": 200}'
            },
            "responses": {
                "default": {
                    "statusCode": "200",
                    "responseTemplates": {
                        "application/json": '{"message": "Mock response"}'
                    }
                }
            }
        }

    def _build_cors_options(self, aws_config: AWSAPIGatewayConfig) -> Dict[str, Any]:
        """Build OPTIONS method for CORS preflight."""
        return {
            "responses": {
                "200": {
                    "description": "CORS preflight response",
                    "headers": {
                        "Access-Control-Allow-Origin": {
                            "schema": {
                                "type": "string"
                            }
                        },
                        "Access-Control-Allow-Methods": {
                            "schema": {
                                "type": "string"
                            }
                        },
                        "Access-Control-Allow-Headers": {
                            "schema": {
                                "type": "string"
                            }
                        }
                    }
                }
            },
            "x-amazon-apigateway-integration": {
                "type": "mock",
                "requestTemplates": {
                    "application/json": '{"statusCode": 200}'
                },
                "responses": {
                    "default": {
                        "statusCode": "200",
                        "responseParameters": {
                            "method.response.header.Access-Control-Allow-Origin": f"'{','.join(aws_config.cors_allow_origins)}'",
                            "method.response.header.Access-Control-Allow-Methods": f"'{','.join(aws_config.cors_allow_methods)}'",
                            "method.response.header.Access-Control-Allow-Headers": f"'{','.join(aws_config.cors_allow_headers)}'"
                        },
                        "responseTemplates": {
                            "application/json": "{}"
                        }
                    }
                }
            }
        }

    def _add_cors_configuration(
        self,
        openapi_spec: Dict[str, Any],
        aws_config: AWSAPIGatewayConfig
    ) -> None:
        """
        Add CORS configuration to OpenAPI spec.

        AWS API Gateway handles CORS via Gateway Responses and
        integration responses, not via OpenAPI-level CORS config.
        """
        # CORS is handled per-method via OPTIONS and response headers
        # Gateway Responses would be configured separately via AWS Console/CLI
        pass

    def _add_security_schemes(
        self,
        openapi_spec: Dict[str, Any],
        aws_config: AWSAPIGatewayConfig,
        global_config: Optional[GlobalConfig]
    ) -> None:
        """Add security schemes to OpenAPI components."""
        # API Key
        if aws_config.api_key_required:
            openapi_spec["components"]["securitySchemes"]["api_key"] = {
                "type": "apiKey",
                "name": "x-api-key",
                "in": "header"
            }

        # Lambda Authorizer
        if aws_config.authorizer_type == "lambda" and aws_config.lambda_authorizer_arn:
            openapi_spec["components"]["securitySchemes"]["lambda_authorizer"] = {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "x-amazon-apigateway-authtype": "custom",
                "x-amazon-apigateway-authorizer": {
                    "type": "token",
                    "authorizerUri": f"arn:aws:apigateway:{{region}}:lambda:path/2015-03-31/functions/{aws_config.lambda_authorizer_arn}/invocations",
                    "authorizerResultTtlInSeconds": aws_config.lambda_authorizer_ttl,
                }
            }

        # Cognito User Pool
        if aws_config.authorizer_type == "cognito" and aws_config.cognito_user_pool_arns:
            openapi_spec["components"]["securitySchemes"]["cognito_authorizer"] = {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "x-amazon-apigateway-authtype": "cognito_user_pools",
                "x-amazon-apigateway-authorizer": {
                    "type": "cognito_user_pools",
                    "providerARNs": aws_config.cognito_user_pool_arns
                }
            }

        # Check global authentication config
        if global_config and hasattr(global_config, 'authentication') and global_config.authentication:
            auth = global_config.authentication

            # JWT → Cognito or Lambda
            if auth.type == "jwt" and auth.jwt:
                # If Cognito ARNs are provided, use Cognito authorizer
                if aws_config.cognito_user_pool_arns:
                    # Already added above
                    pass
                else:
                    # Use Lambda authorizer for custom JWT validation
                    openapi_spec["components"]["securitySchemes"]["jwt"] = {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                        "description": "JWT Bearer token authentication"
                    }

            # API Key
            elif auth.type == "api_key" and auth.api_key:
                if "api_key" not in openapi_spec["components"]["securitySchemes"]:
                    openapi_spec["components"]["securitySchemes"]["api_key"] = {
                        "type": "apiKey",
                        "name": auth.api_key.header_name or "x-api-key",
                        "in": "header"
                    }

    def _get_security_scheme_name(self, auth_type: str) -> Optional[str]:
        """Map GAL auth type to OpenAPI security scheme name."""
        mapping = {
            "jwt": "lambda_authorizer",
            "api_key": "api_key",
            "basic": None,  # Not supported in AWS API Gateway REST APIs
        }
        return mapping.get(auth_type)
