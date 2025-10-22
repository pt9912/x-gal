"""
AWS API Gateway OpenAPI 3.0 Parser

Parses OpenAPI 3.0 specifications exported from AWS API Gateway
(with x-amazon-apigateway extensions) and converts them to GAL Config.

AWS CLI Export Command:
    aws apigateway get-export --rest-api-id <api-id> --stage-name <stage> --export-type oas30

Supported Extensions:
- x-amazon-apigateway-integration: Backend integration configuration
- x-amazon-apigateway-authorizer: Custom authorizer configuration
- x-amazon-apigateway-api-key-source: API key source configuration

References:
- https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions.html
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import yaml

logger = logging.getLogger(__name__)


class AWSAPIGatewayAPI:
    """Represents an AWS API Gateway API parsed from OpenAPI 3.0"""

    def __init__(
        self,
        api_id: str,
        title: str,
        version: str,
        description: str = "",
        paths: Optional[Dict[str, Any]] = None,
        components: Optional[Dict[str, Any]] = None,
        servers: Optional[List[Dict[str, Any]]] = None,
        extensions: Optional[Dict[str, Any]] = None,
    ):
        self.api_id = api_id
        self.title = title
        self.version = version
        self.description = description
        self.paths = paths or {}
        self.components = components or {}
        self.servers = servers or []
        self.extensions = extensions or {}


class AWSAPIGatewayParser:
    """Parser for AWS API Gateway OpenAPI 3.0 exports"""

    def __init__(self):
        self.openapi_spec: Dict[str, Any] = {}

    def parse(self, openapi_content: str, api_id: str = "imported-api") -> AWSAPIGatewayAPI:
        """
        Parse AWS API Gateway OpenAPI 3.0 export to AWSAPIGatewayAPI object.

        Args:
            openapi_content: OpenAPI 3.0 JSON or YAML string
            api_id: API ID (default: "imported-api")

        Returns:
            AWSAPIGatewayAPI object

        Raises:
            ValueError: If OpenAPI spec is invalid or unsupported version
        """
        # Try JSON first, then YAML
        try:
            self.openapi_spec = json.loads(openapi_content)
        except (json.JSONDecodeError, TypeError):
            try:
                self.openapi_spec = yaml.safe_load(openapi_content)
            except (yaml.YAMLError, AttributeError) as e:
                raise ValueError(f"Invalid OpenAPI format (not JSON or YAML): {e}")

        # Validate that we got a dict
        if not isinstance(self.openapi_spec, dict):
            raise ValueError("Invalid OpenAPI format: expected dictionary/object structure")

        # Validate OpenAPI version
        openapi_version = self.openapi_spec.get("openapi", "")
        if not openapi_version.startswith("3.0"):
            raise ValueError(
                f"Unsupported OpenAPI version: {openapi_version}. "
                "Only OpenAPI 3.0.x is supported."
            )

        # Extract info
        info = self.openapi_spec.get("info", {})
        title = info.get("title", "Imported API")
        version = info.get("version", "1.0")
        description = info.get("description", "")

        # Extract components
        components = self.openapi_spec.get("components", {})

        # Extract servers
        servers = self.openapi_spec.get("servers", [])

        # Extract paths
        paths = self.openapi_spec.get("paths", {})

        # Extract AWS-specific extensions
        extensions = {
            "api_key_source": self.openapi_spec.get("x-amazon-apigateway-api-key-source"),
            "request_validator": self.openapi_spec.get("x-amazon-apigateway-request-validator"),
            "request_validators": self.openapi_spec.get("x-amazon-apigateway-request-validators"),
        }

        return AWSAPIGatewayAPI(
            api_id=api_id,
            title=title,
            version=version,
            description=description,
            paths=paths,
            components=components,
            servers=servers,
            extensions=extensions,
        )

    def extract_backend_url(self, api: AWSAPIGatewayAPI) -> Optional[str]:
        """
        Extract backend URL from AWS API Gateway integration.

        For HTTP_PROXY integrations, extracts the URI from the first route.
        For AWS_PROXY (Lambda), returns None (no backend URL).

        Args:
            api: AWSAPIGatewayAPI object

        Returns:
            Backend URL string or None
        """
        # Iterate through paths to find first HTTP_PROXY integration
        for path, methods in api.paths.items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete", "patch", "head", "options"]:
                    integration = operation.get("x-amazon-apigateway-integration", {})
                    integration_type = integration.get("type", "").lower()

                    if integration_type == "http_proxy":
                        uri = integration.get("uri", "")
                        if uri:
                            # Extract base URL (remove path)
                            parsed = urlparse(uri)
                            if parsed.scheme and parsed.netloc:
                                return f"{parsed.scheme}://{parsed.netloc}"

        # Check servers (fallback)
        if api.servers:
            server_url = api.servers[0].get("url", "")
            if server_url and not server_url.startswith("{"):
                return server_url

        return None

    def extract_routes(self, api: AWSAPIGatewayAPI) -> List[Dict[str, Any]]:
        """
        Extract routes from AWS API Gateway paths.

        Args:
            api: AWSAPIGatewayAPI object

        Returns:
            List of route dictionaries with path, methods, integration_type
        """
        routes = []

        for path, methods in api.paths.items():
            # Skip OPTIONS (auto-generated for CORS)
            valid_methods = []
            integration_type = None
            integration_uri = None

            for method, operation in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]:
                    valid_methods.append(method.upper())

                    # Extract integration info from first method
                    if integration_type is None:
                        integration = operation.get("x-amazon-apigateway-integration", {})
                        integration_type = integration.get("type", "http_proxy")
                        integration_uri = integration.get("uri", "")

            if valid_methods:
                routes.append(
                    {
                        "path": path,
                        "methods": valid_methods,
                        "integration_type": integration_type,
                        "integration_uri": integration_uri,
                    }
                )

        return routes

    def extract_authentication(
        self, api: AWSAPIGatewayAPI
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Extract authentication configuration from AWS API Gateway.

        Supports:
        - API Keys (x-api-key header)
        - Lambda Authorizers (custom JWT validation)
        - Cognito User Pools (OAuth2/JWT)

        Args:
            api: AWSAPIGatewayAPI object

        Returns:
            Tuple of (auth_type, auth_config)
            auth_type: "api_key", "jwt", or None
            auth_config: Dictionary with auth details
        """
        security_schemes = api.components.get("securitySchemes", {})

        # Check for API Key
        for scheme_name, scheme in security_schemes.items():
            if scheme.get("type") == "apiKey":
                # Check if it's a Cognito or Lambda authorizer
                authtype = scheme.get("x-amazon-apigateway-authtype")
                authorizer = scheme.get("x-amazon-apigateway-authorizer")

                if authtype == "cognito_user_pools" and authorizer:
                    # Cognito User Pool
                    return "jwt", {
                        "authorizer_type": "cognito",
                        "provider_arns": authorizer.get("providerARNs", []),
                        "header_name": scheme.get("name", "Authorization"),
                    }
                elif authtype == "custom" and authorizer:
                    # Lambda Authorizer
                    authorizer_uri = authorizer.get("authorizerUri", "")
                    # Extract Lambda ARN from URI
                    # Format: arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:name/invocations
                    lambda_arn = None
                    if "functions/" in authorizer_uri:
                        parts = authorizer_uri.split("functions/")
                        if len(parts) > 1:
                            lambda_arn = parts[1].split("/invocations")[0]

                    return "jwt", {
                        "authorizer_type": "lambda",
                        "lambda_arn": lambda_arn,
                        "ttl": authorizer.get("authorizerResultTtlInSeconds", 300),
                        "header_name": scheme.get("name", "Authorization"),
                    }
                else:
                    # Simple API Key
                    return "api_key", {
                        "header_name": scheme.get("name", "x-api-key"),
                    }

        # Check for HTTP bearer (JWT without AWS authorizer)
        for scheme_name, scheme in security_schemes.items():
            if scheme.get("type") == "http" and scheme.get("scheme") == "bearer":
                return "jwt", {
                    "authorizer_type": None,
                    "bearer_format": scheme.get("bearerFormat", "JWT"),
                }

        # No authentication found
        return None, None

    def extract_integration_type(self, api: AWSAPIGatewayAPI) -> str:
        """
        Extract primary integration type from API.

        Returns:
        - "HTTP_PROXY" for HTTP backend integrations
        - "AWS_PROXY" for Lambda integrations
        - "MOCK" for mock integrations

        Args:
            api: AWSAPIGatewayAPI object

        Returns:
            Integration type string
        """
        # Check first route's integration
        for path, methods in api.paths.items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    integration = operation.get("x-amazon-apigateway-integration", {})
                    integration_type = integration.get("type", "").lower()

                    if integration_type == "aws_proxy":
                        return "AWS_PROXY"
                    elif integration_type == "http_proxy":
                        return "HTTP_PROXY"
                    elif integration_type == "mock":
                        return "MOCK"

        # Default to HTTP_PROXY
        return "HTTP_PROXY"

    def extract_lambda_arn(self, api: AWSAPIGatewayAPI) -> Optional[str]:
        """
        Extract Lambda function ARN from AWS_PROXY integration.

        Args:
            api: AWSAPIGatewayAPI object

        Returns:
            Lambda function ARN or None
        """
        for path, methods in api.paths.items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    integration = operation.get("x-amazon-apigateway-integration", {})
                    integration_type = integration.get("type", "").lower()

                    if integration_type == "aws_proxy":
                        uri = integration.get("uri", "")
                        # Extract Lambda ARN from URI
                        # Format: arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:name/invocations
                        if "functions/" in uri:
                            parts = uri.split("functions/")
                            if len(parts) > 1:
                                return parts[1].split("/invocations")[0]

        return None

    def extract_cors_config(self, api: AWSAPIGatewayAPI) -> Dict[str, Any]:
        """
        Extract CORS configuration from OPTIONS methods.

        Args:
            api: AWSAPIGatewayAPI object

        Returns:
            Dictionary with CORS configuration
        """
        cors_config = {
            "enabled": False,
            "allow_origins": [],
            "allow_methods": [],
            "allow_headers": [],
        }

        # Look for OPTIONS methods with CORS integration
        for path, methods in api.paths.items():
            if "options" in methods:
                options = methods["options"]
                integration = options.get("x-amazon-apigateway-integration", {})

                if integration.get("type") == "mock":
                    # This is likely a CORS preflight
                    cors_config["enabled"] = True

                    # Extract CORS headers from response parameters
                    responses = integration.get("responses", {})
                    default_response = responses.get("default", {})
                    response_params = default_response.get("responseParameters", {})

                    # Extract Allow-Origin
                    origin_param = response_params.get(
                        "method.response.header.Access-Control-Allow-Origin", ""
                    )
                    if origin_param:
                        # Remove quotes
                        origin = origin_param.strip("'\"")
                        cors_config["allow_origins"].append(origin)

                    # Extract Allow-Methods
                    methods_param = response_params.get(
                        "method.response.header.Access-Control-Allow-Methods", ""
                    )
                    if methods_param:
                        methods_str = methods_param.strip("'\"")
                        cors_config["allow_methods"] = [m.strip() for m in methods_str.split(",")]

                    # Extract Allow-Headers
                    headers_param = response_params.get(
                        "method.response.header.Access-Control-Allow-Headers", ""
                    )
                    if headers_param:
                        headers_str = headers_param.strip("'\"")
                        cors_config["allow_headers"] = [h.strip() for h in headers_str.split(",")]

                    # Found CORS, no need to check other paths
                    break

        return cors_config

    def extract_api_key_required(self, api: AWSAPIGatewayAPI) -> bool:
        """
        Check if API key is required globally.

        Args:
            api: AWSAPIGatewayAPI object

        Returns:
            True if API key is required
        """
        # Check if x-amazon-apigateway-api-key-source is set
        api_key_source = api.extensions.get("api_key_source")
        if api_key_source:
            return True

        # Check if any route has API key security
        for path, methods in api.paths.items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    security = operation.get("security", [])
                    for sec_req in security:
                        if "api_key" in sec_req or "x-api-key" in sec_req:
                            return True

        return False
