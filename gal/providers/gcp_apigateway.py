"""
GCP API Gateway Provider

Generates OpenAPI 2.0 (Swagger) specifications for Google Cloud API Gateway
with x-google-backend extensions.

GCP API Gateway only supports OpenAPI 2.0 (Swagger), not OpenAPI 3.0.

gcloud CLI Deployment Commands:
    # Create API
    gcloud api-gateway apis create API_ID --project=PROJECT_ID

    # Create API Config
    gcloud api-gateway api-configs create CONFIG_ID \
      --api=API_ID \
      --openapi-spec=openapi.yaml \
      --project=PROJECT_ID \
      --backend-auth-service-account=SERVICE_ACCOUNT_EMAIL

    # Create Gateway
    gcloud api-gateway gateways create GATEWAY_ID \
      --api=API_ID \
      --api-config=CONFIG_ID \
      --location=REGION \
      --project=PROJECT_ID

References:
- https://cloud.google.com/api-gateway/docs/openapi-overview
- https://cloud.google.com/endpoints/docs/openapi/openapi-extensions
"""

import json
import logging
from typing import Any, Dict, List

from gal.config import Config, GCPAPIGatewayConfig, Route, Service
from gal.provider import Provider

logger = logging.getLogger(__name__)


class GCPAPIGatewayProvider(Provider):
    """GCP API Gateway provider for GAL.

    Generates OpenAPI 2.0 (Swagger) specifications with x-google-backend extensions
    for deployment to Google Cloud API Gateway.

    Supported Features:
    - OpenAPI 2.0 (Swagger) export
    - OpenAPI 2.0 (Swagger) import
    - HTTP backend integration (x-google-backend)
    - JWT authentication (x-google-issuer, x-google-jwks_uri)
    - CORS configuration
    - Basic path routing

    Limitations:
    - No OpenAPI 3.0 support (GCP limitation)
    - gcloud CLI deployment required (no declarative IaC templates)
    """

    def __init__(self):
        pass

    def name(self) -> str:
        """Return provider name."""
        return "gcp_apigateway"

    def validate(self, config: Config) -> bool:
        """Validate GCP API Gateway configuration.

        Args:
            config: GAL configuration to validate

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not config.global_config or not config.global_config.gcp_apigateway:
            raise ValueError("GCP API Gateway configuration is required in global_config")

        gcp_config = config.global_config.gcp_apigateway

        if not gcp_config.project_id:
            raise ValueError("GCP project_id is required")

        if not gcp_config.backend_address and config.services:
            # Check if at least one service has upstream configured
            has_upstream = any(
                service.upstream and service.upstream.targets for service in config.services
            )
            if not has_upstream:
                raise ValueError("Either backend_address or service upstream must be configured")

        return True

    def generate(self, config: Config) -> str:
        """Generate OpenAPI 2.0 (Swagger) specification for GCP API Gateway.

        Args:
            config: GAL configuration object

        Returns:
            OpenAPI 2.0 YAML string

        Raises:
            ValueError: If configuration is invalid
        """
        logger.info("Generating GCP API Gateway OpenAPI 2.0 specification")

        if not config.global_config or not config.global_config.gcp_apigateway:
            raise ValueError("GCP API Gateway configuration is required in global_config")

        gcp_config = config.global_config.gcp_apigateway

        # Validate required fields
        if not gcp_config.project_id:
            raise ValueError("GCP project_id is required")
        if not gcp_config.backend_address:
            logger.warning("No backend_address configured, using default from first service")

        # Build OpenAPI 2.0 (Swagger) specification
        openapi_spec = self._build_openapi_spec(config, gcp_config)

        # Convert to YAML (more readable than JSON for gcloud deployment)
        import yaml

        return yaml.dump(openapi_spec, default_flow_style=False, sort_keys=False)

    def parse(self, provider_config: str) -> Config:
        """Parse GCP API Gateway OpenAPI 2.0 spec to GAL Config.

        Converts an OpenAPI 2.0 (Swagger) specification exported from GCP API Gateway
        (with x-google-* extensions) into GAL configuration format.

        Args:
            provider_config: OpenAPI 2.0 (Swagger) specification string (JSON or YAML)

        Returns:
            GAL Config object

        Raises:
            ValueError: If OpenAPI spec is invalid
        """
        from urllib.parse import urlparse

        from gal.config import (
            AuthenticationConfig,
            Config,
            GCPAPIGatewayConfig,
            GlobalConfig,
            JwtConfig,
            Route,
            Service,
            Upstream,
            UpstreamTarget,
        )
        from gal.parsers.gcp_apigateway_parser import GCPAPIGatewayParser

        logger.info("Parsing GCP API Gateway OpenAPI 2.0 specification")

        parser = GCPAPIGatewayParser()
        api = parser.parse(provider_config)

        # Extract backend URL
        backend_url = parser.extract_backend_url(api)
        if not backend_url:
            raise ValueError("No backend URL found in OpenAPI spec (x-google-backend.address)")

        # Parse backend URL
        parsed = urlparse(backend_url)
        backend_protocol = parsed.scheme or "https"
        backend_host = parsed.netloc
        backend_port = parsed.port or (443 if backend_protocol == "https" else 80)

        # Extract routes
        routes_data = parser.extract_routes(api)
        routes = []

        # Extract JWT config
        jwt_config = parser.extract_jwt_config(api)
        authentication = None

        if jwt_config:
            authentication = AuthenticationConfig(
                type="jwt",
                jwt=JwtConfig(
                    issuer=jwt_config["issuer"],
                    jwks_uri=jwt_config["jwks_uri"],
                    audience=jwt_config["audiences"][0] if jwt_config["audiences"] else "",
                ),
            )

        # Create routes
        for route_data in routes_data:
            route = Route(
                path_prefix=route_data["path"],
                methods=route_data["methods"],
                authentication=authentication,
            )
            routes.append(route)

        # Extract CORS config
        cors_config = parser.extract_cors_config(api)

        # Extract backend config
        backend_config = parser.extract_backend_config(api)

        # Extract project ID (attempt)
        project_id = parser.extract_project_id(api) or "gcp-project"

        # Build GCP API Gateway config
        gcp_config = GCPAPIGatewayConfig(
            api_id=api.api_id,
            api_display_name=api.title,
            project_id=project_id,
            region="us-central1",  # Default, cannot be determined from OpenAPI export
            backend_address=backend_url,
            backend_protocol=backend_protocol,
            backend_path_translation=backend_config["path_translation"],
            backend_deadline=backend_config["deadline"],
            backend_disable_auth=backend_config["disable_auth"],
            backend_jwt_audience=backend_config["jwt_audience"],
            jwt_issuer=jwt_config["issuer"] if jwt_config else "",
            jwt_jwks_uri=jwt_config["jwks_uri"] if jwt_config else "",
            jwt_audiences=jwt_config["audiences"] if jwt_config else [],
            cors_enabled=cors_config["enabled"],
            cors_allow_origins=cors_config["allow_origins"],
            cors_allow_methods=cors_config["allow_methods"],
            cors_allow_headers=cors_config["allow_headers"],
            cors_expose_headers=cors_config["expose_headers"],
            cors_max_age=cors_config["max_age"],
        )

        # Create service
        service = Service(
            name=api.api_id,
            type="rest",
            protocol=backend_protocol,
            upstream=Upstream(
                targets=[
                    UpstreamTarget(
                        host=backend_host,
                        port=backend_port,
                    )
                ]
            ),
            routes=routes,
        )

        # Create config
        config = Config(
            version="1.0",
            provider="gal",  # Imported config is converted to GAL format
            global_config=GlobalConfig(
                gcp_apigateway=gcp_config,
            ),
            services=[service],
        )

        logger.info(
            f"Imported GCP API Gateway: {len(routes)} routes, "
            f"JWT: {'enabled' if jwt_config else 'disabled'}, "
            f"CORS: {'enabled' if cors_config['enabled'] else 'disabled'}"
        )

        return config

    def _build_openapi_spec(
        self, config: Config, gcp_config: GCPAPIGatewayConfig
    ) -> Dict[str, Any]:
        """Build OpenAPI 2.0 specification dictionary.

        Args:
            config: GAL configuration
            gcp_config: GCP API Gateway configuration

        Returns:
            OpenAPI 2.0 specification dictionary
        """
        spec = {
            "swagger": "2.0",
            "info": {
                "title": gcp_config.api_display_name,
                "description": f"API managed by GAL - Project: {gcp_config.project_id}",
                "version": "1.0.0",
            },
            "schemes": [gcp_config.backend_protocol],
            "produces": ["application/json"],
            "consumes": ["application/json"],
        }

        # Add x-google-backend (global default)
        backend_address = gcp_config.backend_address
        if not backend_address and config.services:
            # Fallback to first service upstream
            first_service = config.services[0]
            if first_service.upstream and first_service.upstream.targets:
                target = first_service.upstream.targets[0]
                backend_address = f"{gcp_config.backend_protocol}://{target.host}"
                if target.port and target.port not in [80, 443]:
                    backend_address += f":{target.port}"

        if backend_address:
            spec["x-google-backend"] = self._build_google_backend(gcp_config, backend_address)

        # Add security definitions (JWT)
        if gcp_config.jwt_issuer:
            spec["securityDefinitions"] = self._build_security_definitions(gcp_config)

        # Add paths
        spec["paths"] = self._build_paths(config, gcp_config)

        return spec

    def _build_google_backend(
        self, gcp_config: GCPAPIGatewayConfig, address: str
    ) -> Dict[str, Any]:
        """Build x-google-backend extension.

        Args:
            gcp_config: GCP API Gateway configuration
            address: Backend service address

        Returns:
            x-google-backend dictionary
        """
        backend = {
            "address": address,
            "path_translation": gcp_config.backend_path_translation,
            "deadline": gcp_config.backend_deadline,
        }

        if gcp_config.backend_disable_auth:
            backend["disable_auth"] = True

        if gcp_config.backend_jwt_audience:
            backend["jwt_audience"] = gcp_config.backend_jwt_audience

        return backend

    def _build_security_definitions(self, gcp_config: GCPAPIGatewayConfig) -> Dict[str, Any]:
        """Build OpenAPI 2.0 securityDefinitions with x-google extensions.

        Args:
            gcp_config: GCP API Gateway configuration

        Returns:
            Security definitions dictionary
        """
        security_defs = {}

        if gcp_config.jwt_issuer:
            jwt_def = {
                "authorizationUrl": "",
                "flow": "implicit",
                "type": "oauth2",
                "x-google-issuer": gcp_config.jwt_issuer,
            }

            if gcp_config.jwt_jwks_uri:
                jwt_def["x-google-jwks_uri"] = gcp_config.jwt_jwks_uri

            if gcp_config.jwt_audiences:
                jwt_def["x-google-audiences"] = ",".join(gcp_config.jwt_audiences)

            security_defs["google_jwt"] = jwt_def

        return security_defs

    def _build_paths(self, config: Config, gcp_config: GCPAPIGatewayConfig) -> Dict[str, Any]:
        """Build OpenAPI 2.0 paths from GAL routes.

        Args:
            config: GAL configuration
            gcp_config: GCP API Gateway configuration

        Returns:
            Paths dictionary
        """
        paths = {}

        for service in config.services:
            for route in service.routes:
                # Convert GAL route to OpenAPI path
                path = route.path_prefix or route.path_exact or "/"

                if path not in paths:
                    paths[path] = {}

                # Add methods
                methods = route.methods or ["GET"]
                for method in methods:
                    method_lower = method.lower()
                    paths[path][method_lower] = self._build_operation(
                        route, service, gcp_config, method
                    )

                # Add CORS OPTIONS method if enabled
                if gcp_config.cors_enabled and "options" not in paths[path]:
                    paths[path]["options"] = self._build_cors_options(gcp_config)

        return paths

    def _build_operation(
        self,
        route: Route,
        service: Service,
        gcp_config: GCPAPIGatewayConfig,
        method: str,
    ) -> Dict[str, Any]:
        """Build OpenAPI 2.0 operation for a route.

        Args:
            route: GAL route configuration
            service: GAL service configuration
            gcp_config: GCP API Gateway configuration
            method: HTTP method

        Returns:
            Operation dictionary
        """
        operation = {
            "summary": f"{method} {route.path_prefix or route.path_exact}",
            "operationId": f"{method.lower()}_{service.name}",
            "responses": {
                "200": {
                    "description": "Successful response",
                    "schema": {"type": "string"},
                }
            },
        }

        # Add security requirement if JWT is configured
        if gcp_config.jwt_issuer:
            operation["security"] = [{"google_jwt": []}]

        # Add per-route x-google-backend if service has specific upstream
        if service.upstream and service.upstream.targets:
            target = service.upstream.targets[0]
            backend_address = f"{gcp_config.backend_protocol}://{target.host}"
            if target.port and target.port not in [80, 443]:
                backend_address += f":{target.port}"

            operation["x-google-backend"] = self._build_google_backend(gcp_config, backend_address)

        return operation

    def _build_cors_options(self, gcp_config: GCPAPIGatewayConfig) -> Dict[str, Any]:
        """Build CORS OPTIONS method.

        Args:
            gcp_config: GCP API Gateway configuration

        Returns:
            OPTIONS operation dictionary
        """
        cors_headers = {
            "Access-Control-Allow-Origin": ",".join(gcp_config.cors_allow_origins),
            "Access-Control-Allow-Methods": ",".join(gcp_config.cors_allow_methods),
            "Access-Control-Allow-Headers": ",".join(gcp_config.cors_allow_headers),
        }

        if gcp_config.cors_expose_headers:
            cors_headers["Access-Control-Expose-Headers"] = ",".join(gcp_config.cors_expose_headers)

        if gcp_config.cors_max_age:
            cors_headers["Access-Control-Max-Age"] = str(gcp_config.cors_max_age)

        return {
            "summary": "CORS preflight",
            "operationId": "cors_preflight",
            "responses": {
                "200": {
                    "description": "CORS preflight response",
                    "headers": {
                        key: {"type": "string", "description": key} for key in cors_headers.keys()
                    },
                }
            },
        }
