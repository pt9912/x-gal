"""
Azure API Management provider implementation.

Generates Azure APIM ARM Templates and Policy XML from GAL configurations.
Supports subscription keys, Azure AD authentication, rate limiting, and caching.
"""

import json
import logging
from typing import Any, Dict
from urllib.parse import urlparse

from ..config import (
    ApiKeyConfig,
    AuthenticationConfig,
    AzureAPIMConfig,
    AzureAPIMGlobalConfig,
    Config,
    GlobalConfig,
    JwtConfig,
    MirroringConfig,
    Route,
    Service,
    TrafficSplitConfig,
    Upstream,
    UpstreamTarget,
)
from ..parsers.azure_apim_parser import AzureAPIMParser
from ..provider import Provider

logger = logging.getLogger(__name__)


class AzureAPIMProvider(Provider):
    """Azure API Management gateway provider.

    Generates ARM Templates for deploying Azure API Management resources
    including APIs, Operations, Products, Backends, and Policies.

    Output Format:
        JSON ARM Template with:
        - Microsoft.ApiManagement/service (APIM Service)
        - Microsoft.ApiManagement/service/apis (APIs)
        - Microsoft.ApiManagement/service/apis/operations (Endpoints)
        - Microsoft.ApiManagement/service/apis/operations/policies (Policy XML)
        - Microsoft.ApiManagement/service/products (Products)
        - Microsoft.ApiManagement/service/backends (Backends)

    Policies:
        Implemented using Azure APIM Policy XML:
        - Inbound: rate-limit, validate-jwt, set-header, cache-lookup
        - Backend: base policy
        - Outbound: set-header, cache-store
        - On-Error: base policy

    Azure-specific Features:
        - Subscription Keys (API Key Management)
        - Azure AD JWT Validation
        - Developer Portal Integration
        - OpenAPI 3.0 Export
        - Multi-Region Deployment
    """

    def __init__(self):
        """Initialize Azure APIM provider."""
        pass

    def name(self) -> str:
        """Return provider name.

        Returns:
            str: "azure_apim"
        """
        return "azure_apim"

    def parse(self, provider_config: str) -> Config:
        """Parse Azure APIM OpenAPI export to GAL format.

        Parses OpenAPI 3.0 specifications exported from Azure API Management
        using the Azure CLI command:
            az apim api export --api-id <api-id> \\
                --resource-group <resource-group> \\
                --service-name <service-name> \\
                --export-format OpenApiJsonFile \\
                --file-path <output-path>

        Args:
            provider_config: OpenAPI 3.0 JSON or YAML content

        Returns:
            Config: GAL configuration object

        Raises:
            ValueError: If OpenAPI content is invalid

        Example:
            >>> provider = AzureAPIMProvider()
            >>> with open("api-export.json") as f:
            ...     config = provider.parse(f.read())

        Note:
            Azure APIM policies (rate limiting, caching) are NOT included
            in OpenAPI exports. Only API structure, paths, and security
            schemes are imported. You may need to manually configure
            additional features in GAL.
        """
        logger.info("Parsing Azure APIM OpenAPI export to GAL configuration")

        # Initialize parser
        parser = AzureAPIMParser()
        api = parser.parse(provider_config, api_id="imported-api")

        logger.info(f"Parsed API: {api.title} v{api.version}")

        # Extract backend URL
        backend_url = parser.extract_backend_url(api)
        if not backend_url:
            logger.warning("No backend URL found in OpenAPI spec")
            backend_url = "https://backend.example.com"

        # Parse backend URL
        parsed_url = urlparse(backend_url)
        backend_host = parsed_url.hostname or "backend.example.com"
        backend_port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)

        # Extract routes
        routes_data = parser.extract_routes(api)
        routes = []

        for route_data in routes_data:
            # Extract authentication (per-route or global)
            auth_config = parser.extract_authentication(api)
            authentication = None

            if auth_config:
                auth_type = auth_config.get("type")
                if auth_type == "api_key":
                    authentication = AuthenticationConfig(
                        type="api_key",
                        api_key=ApiKeyConfig(
                            key_name=auth_config.get("key_name", "Ocp-Apim-Subscription-Key"),
                            in_location=auth_config.get("in_location", "header"),
                        ),
                    )
                elif auth_type == "jwt":
                    authentication = AuthenticationConfig(
                        type="jwt",
                        jwt=JwtConfig(
                            issuer=auth_config.get("issuer", ""),
                            audience=auth_config.get("audience"),
                        ),
                    )

            route = Route(
                path_prefix=route_data["path"],
                methods=route_data["methods"],
                authentication=authentication,
            )
            routes.append(route)

        # Create service
        service = Service(
            name=api.api_id,
            type="rest",  # Azure APIM OpenAPI exports are always REST APIs
            protocol="http",
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

        # Create GAL config
        config = Config(
            version="1.0",
            provider="gal",  # Imported from Azure APIM, converted to GAL format
            services=[service],
            global_config=GlobalConfig(
                host="0.0.0.0",
                port=8080,
            ),
        )

        logger.info(f"Generated GAL config with {len(routes)} routes for service '{api.api_id}'")
        logger.warning(
            "Azure APIM policies (rate limiting, caching) are not included in OpenAPI exports. "
            "Configure these features manually in GAL if needed."
        )

        return config

    def generate(self, config: Config) -> str:
        """Generate Azure APIM ARM Template from GAL configuration.

        Args:
            config: GAL configuration object

        Returns:
            JSON string containing ARM Template

        Example:
            >>> provider = AzureAPIMProvider()
            >>> config = Config(...)
            >>> arm_template = provider.generate(config)
        """
        arm_template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {
                "apimServiceName": {
                    "type": "string",
                    "defaultValue": self._get_apim_service_name(config),
                    "metadata": {"description": "The name of the API Management service instance"},
                }
            },
            "variables": {},
            "resources": [],
        }

        # APIM Service Resource
        apim_service = self._generate_apim_service(config)
        arm_template["resources"].append(apim_service)

        # Generate API, Operations, Products, Backends for each service
        for service in config.services:
            # API Resource
            api_resource = self._generate_api_resource(service)
            arm_template["resources"].append(api_resource)

            # Operations (one per route)
            for route in service.routes:
                # Generate operation for each HTTP method
                methods = route.methods or ["GET"]
                for method in methods:
                    operation = self._generate_operation(service, route, method)
                    arm_template["resources"].append(operation)

                    # Operation Policy
                    policy = self._generate_operation_policy(service, route, method)
                    arm_template["resources"].append(policy)

            # Product
            if service.azure_apim:
                product = self._generate_product(service)
                arm_template["resources"].append(product)

            # Backend (Traffic Splitting or Single Backend)
            # Check if any route uses traffic splitting
            has_traffic_split = any(
                route.traffic_split and route.traffic_split.enabled for route in service.routes
            )

            if has_traffic_split:
                # Generate individual backends for each target
                for route in service.routes:
                    if route.traffic_split and route.traffic_split.enabled:
                        for target in route.traffic_split.targets:
                            individual_backend = self._generate_individual_backend(
                                service, target.name, target.upstream
                            )
                            arm_template["resources"].append(individual_backend)
                        break  # Only process first traffic split route

                # Generate load-balanced backend pool
                backend_pool = self._generate_traffic_split_backend(service)
                arm_template["resources"].append(backend_pool)
            elif service.upstream:
                # Generate single backend (if upstream has host/port or targets)
                backend = self._generate_backend(service)
                if backend:  # Only append if backend was generated
                    arm_template["resources"].append(backend)

        return json.dumps(arm_template, indent=2)

    def validate(self, config: Config) -> bool:
        """Validate Azure APIM configuration.

        Args:
            config: GAL configuration to validate

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Check if global Azure APIM config exists
        if not config.global_config or not config.global_config.azure_apim:
            logger.warning(
                "Azure APIM global configuration missing. "
                "Using default values for resource_group, location, and SKU."
            )

        # Validate each service
        for service in config.services:
            if service.azure_apim:
                # Validate product name
                if not service.azure_apim.product_name:
                    raise ValueError(f"Service {service.name}: product_name is required")

                # Validate API revision
                if not service.azure_apim.api_revision:
                    raise ValueError(f"Service {service.name}: api_revision is required")

        return True

    def _get_apim_service_name(self, config: Config) -> str:
        """Get APIM service name from config or default."""
        if config.global_config and config.global_config.azure_apim:
            return config.global_config.azure_apim.apim_service_name
        return "gal-apim-service"

    def _get_global_config(self, config: Config) -> AzureAPIMGlobalConfig:
        """Get Azure APIM global config with defaults."""
        if config.global_config and config.global_config.azure_apim:
            return config.global_config.azure_apim
        # Return default config
        return AzureAPIMGlobalConfig()

    def _generate_apim_service(self, config: Config) -> Dict[str, Any]:
        """Generate Azure APIM Service Resource.

        Args:
            config: GAL configuration

        Returns:
            ARM Template resource for APIM service
        """
        global_config = self._get_global_config(config)

        return {
            "type": "Microsoft.ApiManagement/service",
            "apiVersion": "2021-08-01",
            "name": "[parameters('apimServiceName')]",
            "location": global_config.location,
            "sku": {"name": global_config.sku, "capacity": 1},
            "properties": {"publisherEmail": "admin@example.com", "publisherName": "GAL Admin"},
        }

    def _generate_api_resource(self, service: Service) -> Dict[str, Any]:
        """Generate API Resource.

        Args:
            service: GAL service configuration

        Returns:
            ARM Template resource for API
        """
        apim_config = service.azure_apim or AzureAPIMConfig()

        return {
            "type": "Microsoft.ApiManagement/service/apis",
            "apiVersion": "2021-08-01",
            "name": f"[concat(parameters('apimServiceName'), '/{service.name}')]",
            "dependsOn": [
                "[resourceId('Microsoft.ApiManagement/service', parameters('apimServiceName'))]"
            ],
            "properties": {
                "displayName": service.name,
                "apiRevision": apim_config.api_revision,
                "apiVersion": apim_config.api_version,
                "subscriptionRequired": apim_config.subscription_keys_required,
                "path": service.name,
                "protocols": ["https"],
                "isCurrent": True,
            },
        }

    def _generate_operation(self, service: Service, route: Route, method: str) -> Dict[str, Any]:
        """Generate API Operation (Endpoint).

        Args:
            service: GAL service configuration
            route: Route configuration
            method: HTTP method

        Returns:
            ARM Template resource for operation
        """
        # Sanitize path for operation name
        operation_name = f"{method.lower()}_{route.path_prefix.replace('/', '_').strip('_')}"

        return {
            "type": "Microsoft.ApiManagement/service/apis/operations",
            "apiVersion": "2021-08-01",
            "name": f"[concat(parameters('apimServiceName'), '/{service.name}/{operation_name}')]",
            "dependsOn": [
                f"[resourceId('Microsoft.ApiManagement/service/apis', parameters('apimServiceName'), '{service.name}')]"
            ],
            "properties": {
                "displayName": f"{method} {route.path_prefix}",
                "method": method,
                "urlTemplate": route.path_prefix,
                "templateParameters": [],
                "responses": [],
            },
        }

    def _generate_operation_policy(
        self, service: Service, route: Route, method: str
    ) -> Dict[str, Any]:
        """Generate Operation Policy (XML).

        Args:
            service: GAL service configuration
            route: Route configuration
            method: HTTP method

        Returns:
            ARM Template resource for policy
        """
        operation_name = f"{method.lower()}_{route.path_prefix.replace('/', '_').strip('_')}"
        policy_xml = self._build_policy_xml(service, route)

        return {
            "type": "Microsoft.ApiManagement/service/apis/operations/policies",
            "apiVersion": "2021-08-01",
            "name": f"[concat(parameters('apimServiceName'), '/{service.name}/{operation_name}/policy')]",
            "dependsOn": [
                f"[resourceId('Microsoft.ApiManagement/service/apis/operations', parameters('apimServiceName'), '{service.name}', '{operation_name}')]"
            ],
            "properties": {"value": policy_xml, "format": "xml"},
        }

    def _build_policy_xml(self, service: Service, route: Route) -> str:
        """Generate Azure APIM Policy XML.

        Creates policy XML with inbound, backend, outbound, and on-error sections.
        Includes rate limiting, JWT validation, caching, and header manipulation.

        Args:
            service: GAL service configuration
            route: Route configuration

        Returns:
            Policy XML string
        """
        policies = ["<policies>"]

        # Inbound Policies
        policies.append("    <inbound>")
        policies.append("        <base />")

        # Rate Limiting
        if route.rate_limit and route.rate_limit.enabled:
            calls = route.rate_limit.requests_per_second * 60
            policies.append(f'        <rate-limit calls="{calls}" renewal-period="60" />')

        # JWT Validation (Azure AD)
        if route.authentication and route.authentication.type == "jwt":
            jwt_config = route.authentication.jwt_config
            policies.append(
                '        <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized">'
            )
            policies.append(
                f'            <openid-config url="{jwt_config.issuer}/.well-known/openid-configuration" />'
            )
            policies.append("            <audiences>")
            policies.append(f"                <audience>{jwt_config.audience}</audience>")
            policies.append("            </audiences>")

            # Required Claims
            if jwt_config.required_claims:
                policies.append("            <required-claims>")
                for claim in jwt_config.required_claims:
                    policies.append(f'                <claim name="{claim.name}" match="any">')
                    policies.append(f"                    <value>{claim.value}</value>")
                    policies.append("                </claim>")
                policies.append("            </required-claims>")

            policies.append("        </validate-jwt>")

        # API Key Authentication (Subscription Keys)
        elif route.authentication and route.authentication.type == "api_key":
            policies.append(
                '        <check-header name="Ocp-Apim-Subscription-Key" failed-check-httpcode="401" failed-check-error-message="Missing or invalid subscription key" />'
            )

        # Header Manipulation (Request)
        if route.headers and route.headers.request_add:
            for key, value in route.headers.request_add.items():
                policies.append(f'        <set-header name="{key}" exists-action="override">')
                policies.append(f"            <value>{value}</value>")
                policies.append("        </set-header>")

        # Backend URL or Backend Pool
        if route.traffic_split and route.traffic_split.enabled:
            # Use load-balanced backend pool
            policies.append(
                f'        <set-backend-service backend-id="{service.name}-backend-pool" />'
            )
        elif service.upstream and service.upstream.targets:
            # Use single backend URL
            target = service.upstream.targets[0]
            protocol = "https" if target.port in [443, 8443] else "http"
            backend_url = f"{protocol}://{target.host}:{target.port}"
            policies.append(f'        <set-backend-service base-url="{backend_url}" />')

        policies.append("    </inbound>")

        # Backend Policies
        policies.append("    <backend>")
        policies.append("        <base />")

        # Request Mirroring (send-request policy)
        if route.mirroring and route.mirroring.enabled:
            for i, target in enumerate(route.mirroring.targets):
                mirror_url = f"http://{target.upstream.host}:{target.upstream.port}{route.path_prefix}"

                policies.append(f"        <!-- Mirror request to {target.name} -->")
                policies.append(f'        <send-request mode="copy" response-variable-name="mirror_response_{i}">')
                policies.append(f"            <set-url>{mirror_url}</set-url>")
                policies.append("            <set-method>@(context.Request.Method)</set-method>")

                # Copy headers
                if route.mirroring.mirror_headers:
                    policies.append("            <!-- Copy request headers -->")

                # Custom headers for mirror target
                if target.headers:
                    for key, value in target.headers.items():
                        policies.append(f'            <set-header name="{key}" exists-action="override">')
                        policies.append(f"                <value>{value}</value>")
                        policies.append("            </set-header>")

                # Copy body if enabled
                if route.mirroring.mirror_request_body:
                    policies.append("            <set-body>@(context.Request.Body.As<string>(preserveContent: true))</set-body>")

                # Sampling via condition
                if target.sample_percentage < 100.0:
                    sample_pct = int(target.sample_percentage)
                    policies.append(f'            <condition expression="@(new Random().Next(100) &lt; {sample_pct})" />')

                policies.append("        </send-request>")

        policies.append("    </backend>")

        # Outbound Policies
        policies.append("    <outbound>")
        policies.append("        <base />")

        # Header Manipulation (Response)
        if route.headers and route.headers.response_add:
            for key, value in route.headers.response_add.items():
                policies.append(f'        <set-header name="{key}" exists-action="override">')
                policies.append(f"            <value>{value}</value>")
                policies.append("        </set-header>")

        policies.append("    </outbound>")

        # On-Error Policies
        policies.append("    <on-error>")
        policies.append("        <base />")
        policies.append("    </on-error>")

        policies.append("</policies>")

        return "\n".join(policies)

    def _generate_product(self, service: Service) -> Dict[str, Any]:
        """Generate Product Resource.

        Args:
            service: GAL service configuration

        Returns:
            ARM Template resource for product
        """
        apim_config = service.azure_apim or AzureAPIMConfig()

        return {
            "type": "Microsoft.ApiManagement/service/products",
            "apiVersion": "2021-08-01",
            "name": f"[concat(parameters('apimServiceName'), '/{apim_config.product_name}')]",
            "dependsOn": [
                "[resourceId('Microsoft.ApiManagement/service', parameters('apimServiceName'))]"
            ],
            "properties": {
                "displayName": apim_config.product_name,
                "description": apim_config.product_description,
                "subscriptionRequired": apim_config.product_subscription_required,
                "approvalRequired": False,
                "state": "published" if apim_config.product_published else "notPublished",
            },
        }

    def _generate_individual_backend(
        self, service: Service, target_name: str, upstream: UpstreamTarget
    ) -> Dict[str, Any]:
        """Generate individual backend resource for a traffic split target.

        Args:
            service: GAL service configuration
            target_name: Name of the traffic split target
            upstream: Upstream target configuration

        Returns:
            ARM Template resource for individual backend
        """
        protocol = "https" if upstream.port in [443, 8443] else "http"
        url = f"{protocol}://{upstream.host}:{upstream.port}"

        return {
            "type": "Microsoft.ApiManagement/service/backends",
            "apiVersion": "2021-08-01",
            "name": f"[concat(parameters('apimServiceName'), '/{service.name}-{target_name}-backend')]",
            "dependsOn": [
                "[resourceId('Microsoft.ApiManagement/service', parameters('apimServiceName'))]"
            ],
            "properties": {
                "description": f"Backend for {service.name} - {target_name}",
                "url": url,
                "protocol": "http",
                "resourceId": "",
            },
        }

    def _generate_backend(self, service: Service) -> Dict[str, Any]:
        """Generate Backend Resource.

        Args:
            service: GAL service configuration

        Returns:
            ARM Template resource for backend
        """
        if not service.upstream or not service.upstream.targets:
            return {}

        target = service.upstream.targets[0]
        protocol = "https" if target.port in [443, 8443] else "http"
        url = f"{protocol}://{target.host}:{target.port}"

        return {
            "type": "Microsoft.ApiManagement/service/backends",
            "apiVersion": "2021-08-01",
            "name": f"[concat(parameters('apimServiceName'), '/{service.name}-backend')]",
            "dependsOn": [
                "[resourceId('Microsoft.ApiManagement/service', parameters('apimServiceName'))]"
            ],
            "properties": {
                "description": f"Backend for {service.name}",
                "url": url,
                "protocol": "http",
                "resourceId": "",
            },
        }

    def _generate_traffic_split_backend(self, service: Service) -> Dict[str, Any]:
        """Generate Load-Balanced Backend Pool for Traffic Splitting.

        Azure APIM supports load-balanced backend pools with weighted targets.
        This generates a backend pool containing all traffic split targets
        with their respective weights.

        Args:
            service: GAL service configuration

        Returns:
            ARM Template resource for load-balanced backend pool

        Example ARM Template:
            {
              "type": "Microsoft.ApiManagement/service/backends",
              "properties": {
                "description": "Load-balanced backend pool",
                "type": "pool",
                "pool": {
                  "services": [
                    {
                      "id": "/backends/stable-backend",
                      "priority": 1,
                      "weight": 90
                    },
                    {
                      "id": "/backends/canary-backend",
                      "priority": 1,
                      "weight": 10
                    }
                  ]
                }
              }
            }
        """
        # Find the first route with traffic splitting enabled
        traffic_split = None
        for route in service.routes:
            if route.traffic_split and route.traffic_split.enabled:
                traffic_split = route.traffic_split
                break

        if not traffic_split:
            # Fallback to single backend
            return self._generate_backend(service)

        # Generate backend pool services
        pool_services = []
        for target in traffic_split.targets:
            protocol = "https" if target.upstream.port in [443, 8443] else "http"
            backend_url = f"{protocol}://{target.upstream.host}:{target.upstream.port}"

            pool_services.append(
                {
                    "id": f"/subscriptions/{{subscriptionId}}/resourceGroups/{{resourceGroup}}/providers/Microsoft.ApiManagement/service/[parameters('apimServiceName')]/backends/{service.name}-{target.name}-backend",
                    "priority": 1,  # All targets have same priority
                    "weight": target.weight,
                }
            )

        backend_pool = {
            "type": "Microsoft.ApiManagement/service/backends",
            "apiVersion": "2021-08-01",
            "name": f"[concat(parameters('apimServiceName'), '/{service.name}-backend-pool')]",
            "dependsOn": [
                "[resourceId('Microsoft.ApiManagement/service', parameters('apimServiceName'))]"
            ],
            "properties": {
                "description": f"Load-balanced backend pool for {service.name}",
                "type": "pool",
                "pool": {"services": pool_services},
            },
        }

        return backend_pool

    def generate_openapi(self, config: Config) -> str:
        """Generate OpenAPI 3.0 Specification for Azure APIM import.

        Args:
            config: GAL configuration

        Returns:
            JSON string containing OpenAPI 3.0 spec

        Example:
            >>> provider = AzureAPIMProvider()
            >>> openapi_spec = provider.generate_openapi(config)
        """
        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": "GAL API",
                "version": "1.0.0",
                "description": "Generated by GAL - Gateway Abstraction Layer",
            },
            "servers": [],
            "paths": {},
            "components": {"securitySchemes": {}},
        }

        # Add security schemes
        has_oauth2 = False

        for service in config.services:
            # Add server URLs
            if service.upstream and service.upstream.targets:
                target = service.upstream.targets[0]
                protocol = "https" if target.port in [443, 8443] else "http"
                server_url = f"{protocol}://{target.host}:{target.port}"
                if {"url": server_url} not in openapi["servers"]:
                    openapi["servers"].append({"url": server_url})

            # Generate paths and operations
            for route in service.routes:
                path = route.path_prefix
                if path not in openapi["paths"]:
                    openapi["paths"][path] = {}

                methods = route.methods or ["GET"]
                for method in methods:
                    operation = {
                        "summary": f"{method} {path}",
                        "operationId": f"{method.lower()}_{path.replace('/', '_').strip('_')}",
                        "responses": {
                            "200": {"description": "Successful response"},
                            "401": {"description": "Unauthorized"},
                        },
                    }

                    # Add security
                    if route.authentication:
                        if route.authentication.type == "jwt":
                            if not has_oauth2:
                                jwt_config = route.authentication.jwt_config
                                openapi["components"]["securitySchemes"]["oauth2"] = {
                                    "type": "oauth2",
                                    "flows": {
                                        "implicit": {
                                            "authorizationUrl": jwt_config.issuer,
                                            "scopes": {},
                                        }
                                    },
                                }
                                has_oauth2 = True
                            operation["security"] = [{"oauth2": []}]

                        elif route.authentication.type == "api_key":
                            if "apiKey" not in openapi["components"]["securitySchemes"]:
                                openapi["components"]["securitySchemes"]["apiKey"] = {
                                    "type": "apiKey",
                                    "name": "Ocp-Apim-Subscription-Key",
                                    "in": "header",
                                }
                            operation["security"] = [{"apiKey": []}]

                    openapi["paths"][path][method.lower()] = operation

        return json.dumps(openapi, indent=2)
