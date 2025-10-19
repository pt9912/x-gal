"""
Azure API Management provider implementation.

Generates Azure APIM ARM Templates and Policy XML from GAL configurations.
Supports subscription keys, Azure AD authentication, rate limiting, and caching.
"""

import json
import logging
from typing import Any, Dict

from ..config import (
    AzureAPIMConfig,
    AzureAPIMGlobalConfig,
    Config,
    Route,
    Service,
)
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
        """Parse Azure APIM configuration to GAL format.

        Azure APIM uses ARM Templates which are infrastructure-as-code
        templates, not runtime configurations. Parsing ARM Templates back
        to GAL format is not supported as it's not a practical use case.

        Use Azure APIM for exporting GAL configs to Azure, not for importing.

        Args:
            provider_config: ARM Template JSON string

        Raises:
            NotImplementedError: Always raises as parsing is not supported

        Note:
            For migrating from Azure APIM to GAL, manually create a GAL
            configuration that matches your APIM setup, then use GAL to
            migrate to another provider.
        """
        raise NotImplementedError(
            "Parsing Azure APIM ARM Templates to GAL format is not supported. "
            "Azure APIM is an export-only provider. To migrate from Azure APIM, "
            "manually create a GAL configuration matching your APIM setup."
        )

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
                    "metadata": {
                        "description": "The name of the API Management service instance"
                    }
                }
            },
            "variables": {},
            "resources": []
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

            # Backend
            if service.upstream and service.upstream.targets:
                backend = self._generate_backend(service)
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
            "sku": {
                "name": global_config.sku,
                "capacity": 1
            },
            "properties": {
                "publisherEmail": "admin@example.com",
                "publisherName": "GAL Admin"
            }
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
                "isCurrent": True
            }
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
                "responses": []
            }
        }

    def _generate_operation_policy(self, service: Service, route: Route, method: str) -> Dict[str, Any]:
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
            "properties": {
                "value": policy_xml,
                "format": "xml"
            }
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
        policies = ['<policies>']

        # Inbound Policies
        policies.append('    <inbound>')
        policies.append('        <base />')

        # Rate Limiting
        if route.rate_limit and route.rate_limit.enabled:
            calls = route.rate_limit.requests_per_second * 60
            policies.append(f'        <rate-limit calls="{calls}" renewal-period="60" />')

        # JWT Validation (Azure AD)
        if route.authentication and route.authentication.type == "jwt":
            jwt_config = route.authentication.jwt_config
            policies.append('        <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized">')
            policies.append(f'            <openid-config url="{jwt_config.issuer}/.well-known/openid-configuration" />')
            policies.append('            <audiences>')
            policies.append(f'                <audience>{jwt_config.audience}</audience>')
            policies.append('            </audiences>')

            # Required Claims
            if jwt_config.required_claims:
                policies.append('            <required-claims>')
                for claim in jwt_config.required_claims:
                    policies.append(f'                <claim name="{claim.name}" match="any">')
                    policies.append(f'                    <value>{claim.value}</value>')
                    policies.append('                </claim>')
                policies.append('            </required-claims>')

            policies.append('        </validate-jwt>')

        # API Key Authentication (Subscription Keys)
        elif route.authentication and route.authentication.type == "api_key":
            policies.append('        <check-header name="Ocp-Apim-Subscription-Key" failed-check-httpcode="401" failed-check-error-message="Missing or invalid subscription key" />')

        # Header Manipulation (Request)
        if route.headers and route.headers.request_add:
            for key, value in route.headers.request_add.items():
                policies.append(f'        <set-header name="{key}" exists-action="override">')
                policies.append(f'            <value>{value}</value>')
                policies.append('        </set-header>')

        # Backend URL
        if service.upstream and service.upstream.targets:
            target = service.upstream.targets[0]
            protocol = "https" if target.port in [443, 8443] else "http"
            backend_url = f"{protocol}://{target.host}:{target.port}"
            policies.append(f'        <set-backend-service base-url="{backend_url}" />')

        policies.append('    </inbound>')

        # Backend Policies
        policies.append('    <backend>')
        policies.append('        <base />')
        policies.append('    </backend>')

        # Outbound Policies
        policies.append('    <outbound>')
        policies.append('        <base />')

        # Header Manipulation (Response)
        if route.headers and route.headers.response_add:
            for key, value in route.headers.response_add.items():
                policies.append(f'        <set-header name="{key}" exists-action="override">')
                policies.append(f'            <value>{value}</value>')
                policies.append('        </set-header>')

        policies.append('    </outbound>')

        # On-Error Policies
        policies.append('    <on-error>')
        policies.append('        <base />')
        policies.append('    </on-error>')

        policies.append('</policies>')

        return '\n'.join(policies)

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
                "state": "published" if apim_config.product_published else "notPublished"
            }
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
                "resourceId": ""
            }
        }

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
                "description": "Generated by GAL - Gateway Abstraction Layer"
            },
            "servers": [],
            "paths": {},
            "components": {
                "securitySchemes": {}
            }
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
                            "200": {
                                "description": "Successful response"
                            },
                            "401": {
                                "description": "Unauthorized"
                            }
                        }
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
                                            "scopes": {}
                                        }
                                    }
                                }
                                has_oauth2 = True
                            operation["security"] = [{"oauth2": []}]

                        elif route.authentication.type == "api_key":
                            if "apiKey" not in openapi["components"]["securitySchemes"]:
                                openapi["components"]["securitySchemes"]["apiKey"] = {
                                    "type": "apiKey",
                                    "name": "Ocp-Apim-Subscription-Key",
                                    "in": "header"
                                }
                            operation["security"] = [{"apiKey": []}]

                    openapi["paths"][path][method.lower()] = operation

        return json.dumps(openapi, indent=2)
