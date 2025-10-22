"""
GCP API Gateway OpenAPI 2.0 Parser

Parses OpenAPI 2.0 (Swagger) specifications exported from GCP API Gateway
(with x-google-* extensions) and converts them to GAL Config.

GCP Export Command:
    gcloud api-gateway api-configs describe CONFIG_ID \
      --api=API_ID \
      --project=PROJECT_ID \
      --format=json > api-config.json

    # Extract OpenAPI spec from gatewayConfig.gatewayServiceAccount
    # Or directly from the OpenAPI spec file used during deployment

Supported Extensions:
- x-google-backend: Backend service configuration
- x-google-issuer: JWT issuer URL
- x-google-jwks_uri: JWKS URI for JWT validation
- x-google-audiences: Valid JWT audiences

Note:
    GCP API Gateway only supports OpenAPI 2.0 (Swagger), not OpenAPI 3.0.

References:
- https://cloud.google.com/api-gateway/docs/openapi-overview
- https://cloud.google.com/endpoints/docs/openapi/openapi-extensions
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import yaml

logger = logging.getLogger(__name__)


class GCPAPIGatewayAPI:
    """Represents a GCP API Gateway API parsed from OpenAPI 2.0 (Swagger)"""

    def __init__(
        self,
        api_id: str,
        title: str,
        version: str,
        description: str = "",
        paths: Optional[Dict[str, Any]] = None,
        definitions: Optional[Dict[str, Any]] = None,
        security_definitions: Optional[Dict[str, Any]] = None,
        schemes: Optional[List[str]] = None,
        backend: Optional[Dict[str, Any]] = None,
    ):
        self.api_id = api_id
        self.title = title
        self.version = version
        self.description = description
        self.paths = paths or {}
        self.definitions = definitions or {}
        self.security_definitions = security_definitions or {}
        self.schemes = schemes or ["https"]
        self.backend = backend or {}


class GCPAPIGatewayParser:
    """Parser for GCP API Gateway OpenAPI 2.0 (Swagger) exports"""

    def __init__(self):
        self.openapi_spec: Dict[str, Any] = {}

    def parse(self, openapi_content: str, api_id: str = "imported-api") -> GCPAPIGatewayAPI:
        """
        Parse GCP API Gateway OpenAPI 2.0 export to GCPAPIGatewayAPI object.

        Args:
            openapi_content: OpenAPI 2.0 (Swagger) JSON or YAML string
            api_id: API ID (default: "imported-api")

        Returns:
            GCPAPIGatewayAPI object

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

        # Validate OpenAPI version (Swagger 2.0)
        swagger_version = self.openapi_spec.get("swagger", "")
        if not swagger_version.startswith("2.0"):
            raise ValueError(
                f"Unsupported OpenAPI version: {swagger_version}. "
                "GCP API Gateway only supports OpenAPI 2.0 (Swagger)."
            )

        # Extract info
        info = self.openapi_spec.get("info", {})
        title = info.get("title", "Imported API")
        version = info.get("version", "1.0")
        description = info.get("description", "")

        # Extract definitions (OpenAPI 2.0 equivalent of components/schemas)
        definitions = self.openapi_spec.get("definitions", {})

        # Extract security definitions
        security_definitions = self.openapi_spec.get("securityDefinitions", {})

        # Extract schemes
        schemes = self.openapi_spec.get("schemes", ["https"])

        # Extract paths
        paths = self.openapi_spec.get("paths", {})

        # Extract x-google-backend (global default)
        backend = self.openapi_spec.get("x-google-backend", {})

        return GCPAPIGatewayAPI(
            api_id=api_id,
            title=title,
            version=version,
            description=description,
            paths=paths,
            definitions=definitions,
            security_definitions=security_definitions,
            schemes=schemes,
            backend=backend,
        )

    def extract_backend_url(self, api: GCPAPIGatewayAPI) -> Optional[str]:
        """
        Extract backend URL from GCP API Gateway x-google-backend.

        Args:
            api: GCPAPIGatewayAPI object

        Returns:
            Backend URL string or None
        """
        # Check global x-google-backend
        if api.backend:
            address = api.backend.get("address", "")
            if address:
                return address

        # Check per-operation x-google-backend (first route)
        for path, methods in api.paths.items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete", "patch", "head", "options"]:
                    backend = operation.get("x-google-backend", {})
                    address = backend.get("address", "")
                    if address:
                        return address

        return None

    def extract_project_id(self, api: GCPAPIGatewayAPI) -> Optional[str]:
        """
        Extract GCP project ID from backend address or host.

        Attempts to extract project ID from Cloud Run URLs or other GCP service URLs.

        Args:
            api: GCPAPIGatewayAPI object

        Returns:
            Project ID string or None
        """
        backend_url = self.extract_backend_url(api)
        if not backend_url:
            return None

        # Try to extract from Cloud Run URL pattern
        # Format: https://SERVICE-PROJECT_ID-REGION.a.run.app
        parsed = urlparse(backend_url)
        host = parsed.netloc

        # Cloud Run pattern
        if ".run.app" in host:
            parts = host.split("-")
            if len(parts) >= 2:
                # Second part might be project ID
                return parts[1]

        # Cloud Functions pattern
        # Format: https://REGION-PROJECT_ID.cloudfunctions.net
        if ".cloudfunctions.net" in host:
            parts = host.split("-")
            if len(parts) >= 2:
                return parts[1]

        return None

    def extract_routes(self, api: GCPAPIGatewayAPI) -> List[Dict[str, Any]]:
        """
        Extract routes from GCP API Gateway paths.

        Args:
            api: GCPAPIGatewayAPI object

        Returns:
            List of route dictionaries with path, methods, backend
        """
        routes = []

        for path, methods in api.paths.items():
            # Skip OPTIONS (auto-generated for CORS)
            valid_methods = []
            backend_address = None

            for method, operation in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]:
                    valid_methods.append(method.upper())

                    # Extract backend info from first method
                    if backend_address is None:
                        backend = operation.get("x-google-backend", {})
                        backend_address = backend.get("address", "")

            if valid_methods:
                routes.append(
                    {
                        "path": path,
                        "methods": valid_methods,
                        "backend_address": backend_address,
                    }
                )

        return routes

    def extract_jwt_config(self, api: GCPAPIGatewayAPI) -> Optional[Dict[str, Any]]:
        """
        Extract JWT configuration from GCP API Gateway securityDefinitions.

        Looks for x-google-issuer and x-google-jwks_uri extensions.

        Args:
            api: GCPAPIGatewayAPI object

        Returns:
            JWT config dictionary or None
        """
        # Check securityDefinitions for JWT with x-google extensions
        for scheme_name, scheme in api.security_definitions.items():
            if scheme.get("type") == "oauth2":
                issuer = scheme.get("x-google-issuer")
                jwks_uri = scheme.get("x-google-jwks_uri")
                audiences = scheme.get("x-google-audiences", "")

                if issuer:
                    jwt_config = {
                        "issuer": issuer,
                        "jwks_uri": jwks_uri or "",
                        "audiences": audiences.split(",") if audiences else [],
                    }
                    return jwt_config

        return None

    def extract_cors_config(self, api: GCPAPIGatewayAPI) -> Dict[str, Any]:
        """
        Extract CORS configuration from GCP API Gateway.

        Checks for OPTIONS methods with CORS-related responses.

        Args:
            api: GCPAPIGatewayAPI object

        Returns:
            CORS configuration dictionary
        """
        cors_config = {
            "enabled": False,
            "allow_origins": ["*"],
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": [],
            "max_age": 3600,
        }

        # Check for OPTIONS methods
        for path, methods in api.paths.items():
            if "options" in methods:
                cors_config["enabled"] = True  # OPTIONS method exists, CORS is enabled

                options_operation = methods["options"]
                responses = options_operation.get("responses", {})

                # Check for 200 response with CORS headers
                response_200 = responses.get("200", {})
                headers = response_200.get("headers", {})

                if headers:
                    # Extract CORS headers if present
                    for header_name, header_def in headers.items():
                        if header_name == "Access-Control-Allow-Origin":
                            # Extract from description or default value
                            desc = header_def.get("description", "*")
                            cors_config["allow_origins"] = [desc] if desc else ["*"]
                        elif header_name == "Access-Control-Allow-Methods":
                            desc = header_def.get("description", "")
                            if desc:
                                cors_config["allow_methods"] = [m.strip() for m in desc.split(",")]
                        elif header_name == "Access-Control-Allow-Headers":
                            desc = header_def.get("description", "")
                            if desc:
                                cors_config["allow_headers"] = [h.strip() for h in desc.split(",")]
                        elif header_name == "Access-Control-Expose-Headers":
                            desc = header_def.get("description", "")
                            if desc:
                                cors_config["expose_headers"] = [h.strip() for h in desc.split(",")]
                        elif header_name == "Access-Control-Max-Age":
                            desc = header_def.get("description", "")
                            if desc and desc.isdigit():
                                cors_config["max_age"] = int(desc)

                # Found CORS config, no need to check further
                break

        return cors_config

    def extract_backend_config(self, api: GCPAPIGatewayAPI) -> Dict[str, Any]:
        """
        Extract x-google-backend configuration details.

        Args:
            api: GCPAPIGatewayAPI object

        Returns:
            Backend configuration dictionary
        """
        backend = api.backend or {}

        backend_config = {
            "address": backend.get("address", ""),
            "path_translation": backend.get("path_translation", "APPEND_PATH_TO_ADDRESS"),
            "deadline": backend.get("deadline", 30.0),
            "disable_auth": backend.get("disable_auth", False),
            "jwt_audience": backend.get("jwt_audience", ""),
            "protocol": "https" if "https://" in backend.get("address", "") else "http",
        }

        return backend_config

    def extract_service_account(self, api: GCPAPIGatewayAPI) -> Optional[str]:
        """
        Extract service account email from backend configuration.

        Note: Service account is typically configured during API Config creation,
        not in the OpenAPI spec itself. This returns None by default.

        Args:
            api: GCPAPIGatewayAPI object

        Returns:
            Service account email or None
        """
        # Service account is not stored in OpenAPI spec
        # It's configured via gcloud during api-config creation
        # Return None (user must configure manually)
        return None
