"""Azure API Management OpenAPI Parser.

Parses OpenAPI 3.0 specifications exported from Azure APIM
into GAL configuration format.

Azure APIM exports APIs as OpenAPI 3.0 JSON/YAML which can be
obtained via:
    az apim api export --api-id <api-id> \\
        --resource-group <resource-group> \\
        --service-name <service-name> \\
        --export-format OpenApiJsonFile \\
        --file-path <output-path>
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class AzureAPIMAPI:
    """Represents an Azure APIM API from OpenAPI spec."""

    api_id: str
    title: str
    version: str
    description: Optional[str] = None
    base_url: Optional[str] = None
    paths: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    security_schemes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    servers: List[Dict[str, str]] = field(default_factory=list)


class AzureAPIMParser:
    """Parser for Azure APIM OpenAPI 3.0 exports.

    Parses OpenAPI 3.0 specifications exported from Azure API Management
    into structured API objects for conversion to GAL configuration.

    Supports:
        - OpenAPI 3.0 JSON/YAML
        - Multiple servers (backends)
        - Security schemes (apiKey, oauth2, openIdConnect)
        - Path operations with methods
        - x-azure-api-management extensions

    Example:
        >>> parser = AzureAPIMParser()
        >>> api = parser.parse(openapi_json)
        >>> print(f"API: {api.title} v{api.version}")
    """

    def __init__(self):
        """Initialize the Azure APIM parser."""
        self.openapi_spec = {}
        self.api_id = ""

    def parse(self, openapi_content: str, api_id: str = "imported-api") -> AzureAPIMAPI:
        """Parse OpenAPI 3.0 spec from Azure APIM export.

        Args:
            openapi_content: OpenAPI 3.0 JSON or YAML content
            api_id: API identifier (default: "imported-api")

        Returns:
            AzureAPIMAPI object with structured API information

        Raises:
            ValueError: If content is invalid or not OpenAPI 3.0
            json.JSONDecodeError: If JSON is malformed
            yaml.YAMLError: If YAML is malformed

        Example:
            >>> parser = AzureAPIMParser()
            >>> with open("api-export.json") as f:
            ...     api = parser.parse(f.read(), "my-api")
        """
        if not openapi_content or not openapi_content.strip():
            raise ValueError("Empty OpenAPI content")

        # Try JSON first, then YAML
        try:
            self.openapi_spec = json.loads(openapi_content)
        except json.JSONDecodeError:
            try:
                self.openapi_spec = yaml.safe_load(openapi_content)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid OpenAPI format (not JSON or YAML): {e}")

        # Validate OpenAPI version
        openapi_version = self.openapi_spec.get("openapi", "")
        if not openapi_version.startswith("3."):
            raise ValueError(
                f"Unsupported OpenAPI version: {openapi_version}. " "Only OpenAPI 3.x is supported."
            )

        self.api_id = api_id
        return self._parse_openapi_spec()

    def _parse_openapi_spec(self) -> AzureAPIMAPI:
        """Parse OpenAPI spec into AzureAPIMAPI object.

        Returns:
            AzureAPIMAPI with all API information
        """
        info = self.openapi_spec.get("info", {})
        title = info.get("title", "Imported API")
        version = info.get("version", "1.0.0")
        description = info.get("description")

        # Servers (backends)
        servers = self.openapi_spec.get("servers", [])
        base_url = servers[0]["url"] if servers else None

        # Paths (routes/operations)
        paths = self.openapi_spec.get("paths", {})

        # Security schemes
        components = self.openapi_spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})

        api = AzureAPIMAPI(
            api_id=self.api_id,
            title=title,
            version=version,
            description=description,
            base_url=base_url,
            paths=paths,
            security_schemes=security_schemes,
            servers=servers,
        )

        logger.info(
            f"Parsed Azure APIM API: {title} v{version} "
            f"({len(paths)} paths, {len(security_schemes)} security schemes)"
        )

        return api

    def extract_backend_url(self, api: AzureAPIMAPI) -> Optional[str]:
        """Extract backend URL from servers.

        Args:
            api: Parsed AzureAPIMAPI object

        Returns:
            Backend URL (first server) or None

        Example:
            >>> parser = AzureAPIMParser()
            >>> api = parser.parse(openapi_json)
            >>> backend = parser.extract_backend_url(api)
            >>> print(backend)  # https://backend.example.com
        """
        if api.servers:
            return api.servers[0].get("url")
        return api.base_url

    def extract_routes(self, api: AzureAPIMAPI) -> List[Dict[str, Any]]:
        """Extract routes (paths + operations) from API.

        Args:
            api: Parsed AzureAPIMAPI object

        Returns:
            List of route dictionaries with path, methods, operations

        Example:
            >>> parser = AzureAPIMParser()
            >>> api = parser.parse(openapi_json)
            >>> routes = parser.extract_routes(api)
            >>> for route in routes:
            ...     print(f"{route['path']}: {route['methods']}")
        """
        routes = []

        for path, operations in api.paths.items():
            methods = []
            operation_details = {}

            for method, details in operations.items():
                # Skip non-HTTP methods (like "parameters", "servers")
                if method.upper() not in [
                    "GET",
                    "POST",
                    "PUT",
                    "DELETE",
                    "PATCH",
                    "HEAD",
                    "OPTIONS",
                ]:
                    continue

                methods.append(method.upper())
                operation_details[method.upper()] = {
                    "summary": details.get("summary"),
                    "description": details.get("description"),
                    "operationId": details.get("operationId"),
                    "security": details.get("security", []),
                    "responses": details.get("responses", {}),
                }

            if methods:
                routes.append(
                    {
                        "path": path,
                        "methods": methods,
                        "operations": operation_details,
                    }
                )

        logger.info(f"Extracted {len(routes)} routes from API")
        return routes

    def extract_authentication(self, api: AzureAPIMAPI) -> Optional[Dict[str, Any]]:
        """Extract authentication configuration from security schemes.

        Args:
            api: Parsed AzureAPIMAPI object

        Returns:
            Authentication config dictionary or None

        Supported Schemes:
            - apiKey (Subscription Keys)
            - oauth2 (Azure AD OAuth2)
            - openIdConnect (Azure AD OIDC)

        Example:
            >>> parser = AzureAPIMParser()
            >>> api = parser.parse(openapi_json)
            >>> auth = parser.extract_authentication(api)
            >>> print(auth['type'])  # "api_key" or "jwt"
        """
        if not api.security_schemes:
            return None

        # Priority: apiKey > oauth2/openIdConnect
        for scheme_name, scheme in api.security_schemes.items():
            scheme_type = scheme.get("type")

            # API Key (Subscription Keys)
            if scheme_type == "apiKey":
                return {
                    "type": "api_key",
                    "key_name": scheme.get("name", "Ocp-Apim-Subscription-Key"),
                    "in_location": scheme.get("in", "header"),
                    "description": scheme.get("description"),
                }

            # OAuth2 (Azure AD)
            elif scheme_type == "oauth2":
                flows = scheme.get("flows", {})
                # Assume implicit flow (common for Azure AD)
                implicit = flows.get("implicit", {})
                if implicit:
                    return {
                        "type": "jwt",
                        "issuer": implicit.get("authorizationUrl", "").split("/oauth2")[0],
                        "audience": None,  # Cannot infer from OpenAPI
                        "description": scheme.get("description"),
                    }

            # OpenID Connect (Azure AD)
            elif scheme_type == "openIdConnect":
                return {
                    "type": "jwt",
                    "issuer": scheme.get("openIdConnectUrl", "").split("/.well-known")[0],
                    "audience": None,  # Cannot infer from OpenAPI
                    "description": scheme.get("description"),
                }

        return None

    def extract_rate_limiting(self, api: AzureAPIMAPI) -> Optional[Dict[str, Any]]:
        """Extract rate limiting from x-azure-api-management extensions.

        Azure APIM rate limiting is configured via policies (not in OpenAPI),
        so this method looks for x-azure-api-management-* extensions.

        Args:
            api: Parsed AzureAPIMAPI object

        Returns:
            Rate limiting config or None

        Note:
            Azure APIM policies are not fully represented in OpenAPI exports.
            This method can only extract rate limits if they are documented
            in custom x-azure-* extensions.
        """
        # Azure APIM policies are NOT in OpenAPI exports
        # They are only in the ARM Template or Policy XML
        # This is a placeholder for future enhancement
        logger.warning(
            "Rate limiting policies cannot be extracted from OpenAPI exports. "
            "Azure APIM policies are stored separately in Policy XML."
        )
        return None
