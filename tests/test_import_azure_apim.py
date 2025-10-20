"""Tests for Azure APIM Import (OpenAPI 3.0 parsing)."""

import json
import pytest

# No need to import AuthenticationType, it's just a string
from gal.parsers.azure_apim_parser import AzureAPIMParser
from gal.providers.azure_apim import AzureAPIMProvider


# Sample OpenAPI 3.0 spec (minimal)
MINIMAL_OPENAPI = """
{
  "openapi": "3.0.0",
  "info": {
    "title": "Pet Store API",
    "version": "1.0.0",
    "description": "A simple Pet Store API"
  },
  "servers": [
    {"url": "https://pet store.example.com"}
  ],
  "paths": {
    "/pets": {
      "get": {
        "summary": "List all pets",
        "operationId": "listPets",
        "responses": {
          "200": {"description": "Success"}
        }
      }
    }
  }
}
"""

# OpenAPI with API Key security
OPENAPI_WITH_APIKEY = """
{
  "openapi": "3.0.1",
  "info": {
    "title": "User API",
    "version": "v1"
  },
  "servers": [
    {"url": "https://backend.example.com:8080"}
  ],
  "paths": {
    "/api/users": {
      "get": {
        "summary": "Get users",
        "security": [{"apiKey": []}],
        "responses": {"200": {"description": "OK"}}
      },
      "post": {
        "summary": "Create user",
        "security": [{"apiKey": []}],
        "responses": {"201": {"description": "Created"}}
      }
    }
  },
  "components": {
    "securitySchemes": {
      "apiKey": {
        "type": "apiKey",
        "name": "Ocp-Apim-Subscription-Key",
        "in": "header"
      }
    }
  }
}
"""

# OpenAPI with OAuth2 security
OPENAPI_WITH_OAUTH = """
{
  "openapi": "3.0.2",
  "info": {
    "title": "Admin API",
    "version": "2.0.0"
  },
  "servers": [
    {"url": "https://admin-backend.example.com"}
  ],
  "paths": {
    "/api/admin/users": {
      "delete": {
        "summary": "Delete user",
        "security": [{"oauth2": ["admin"]}],
        "responses": {"204": {"description": "No Content"}}
      }
    }
  },
  "components": {
    "securitySchemes": {
      "oauth2": {
        "type": "oauth2",
        "flows": {
          "implicit": {
            "authorizationUrl": "https://login.microsoftonline.com/tenant-id/oauth2/authorize",
            "scopes": {"admin": "Admin access"}
          }
        }
      }
    }
  }
}
"""

# Multiple paths and methods
COMPLEX_OPENAPI = """
{
  "openapi": "3.0.3",
  "info": {
    "title": "E-Commerce API",
    "version": "3.0.0",
    "description": "Multi-resource API"
  },
  "servers": [
    {"url": "https://api.ecommerce.example.com:443"}
  ],
  "paths": {
    "/products": {
      "get": {"summary": "List products", "responses": {"200": {"description": "OK"}}},
      "post": {"summary": "Create product", "responses": {"201": {"description": "Created"}}}
    },
    "/products/{id}": {
      "get": {"summary": "Get product", "responses": {"200": {"description": "OK"}}},
      "put": {"summary": "Update product", "responses": {"200": {"description": "OK"}}},
      "delete": {"summary": "Delete product", "responses": {"204": {"description": "No Content"}}}
    },
    "/orders": {
      "get": {"summary": "List orders", "responses": {"200": {"description": "OK"}}},
      "post": {"summary": "Create order", "responses": {"201": {"description": "Created"}}}
    }
  }
}
"""


class TestAzureAPIMParser:
    """Test Azure APIM OpenAPI parser."""

    def test_parse_minimal_openapi(self):
        """Test parsing minimal valid OpenAPI spec."""
        parser = AzureAPIMParser()
        api = parser.parse(MINIMAL_OPENAPI, "petstore")

        assert api.api_id == "petstore"
        assert api.title == "Pet Store API"
        assert api.version == "1.0.0"
        assert api.description == "A simple Pet Store API"
        assert len(api.servers) == 1
        assert api.servers[0]["url"] == "https://petstore.example.com"
        assert len(api.paths) == 1
        assert "/pets" in api.paths

    def test_parse_empty_content(self):
        """Test parsing empty content raises ValueError."""
        parser = AzureAPIMParser()

        with pytest.raises(ValueError, match="Empty OpenAPI content"):
            parser.parse("", "test")

        with pytest.raises(ValueError, match="Empty OpenAPI content"):
            parser.parse("   ", "test")

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises ValueError."""
        parser = AzureAPIMParser()

        with pytest.raises(ValueError, match="Invalid OpenAPI format"):
            parser.parse("{invalid json", "test")

    def test_parse_unsupported_openapi_version(self):
        """Test parsing OpenAPI 2.0 (Swagger) raises ValueError."""
        swagger_spec = '{"swagger": "2.0", "info": {"title": "API", "version": "1.0.0"}}'
        parser = AzureAPIMParser()

        with pytest.raises(ValueError, match="Unsupported OpenAPI version"):
            parser.parse(swagger_spec, "test")

    def test_extract_backend_url(self):
        """Test backend URL extraction."""
        parser = AzureAPIMParser()
        api = parser.parse(OPENAPI_WITH_APIKEY, "user-api")

        backend_url = parser.extract_backend_url(api)
        assert backend_url == "https://backend.example.com:8080"

    def test_extract_backend_url_no_servers(self):
        """Test backend URL extraction when no servers defined."""
        parser = AzureAPIMParser()
        openapi_no_servers = json.loads(MINIMAL_OPENAPI)
        del openapi_no_servers["servers"]
        api = parser.parse(json.dumps(openapi_no_servers), "test")

        backend_url = parser.extract_backend_url(api)
        assert backend_url is None

    def test_extract_routes(self):
        """Test route extraction."""
        parser = AzureAPIMParser()
        api = parser.parse(OPENAPI_WITH_APIKEY, "user-api")

        routes = parser.extract_routes(api)
        assert len(routes) == 1
        assert routes[0]["path"] == "/api/users"
        assert set(routes[0]["methods"]) == {"GET", "POST"}

    def test_extract_routes_complex(self):
        """Test route extraction from complex API."""
        parser = AzureAPIMParser()
        api = parser.parse(COMPLEX_OPENAPI, "ecommerce")

        routes = parser.extract_routes(api)
        assert len(routes) == 3

        # Check /products
        products_route = next(r for r in routes if r["path"] == "/products")
        assert set(products_route["methods"]) == {"GET", "POST"}

        # Check /products/{id}
        product_route = next(r for r in routes if r["path"] == "/products/{id}")
        assert set(product_route["methods"]) == {"GET", "PUT", "DELETE"}

        # Check /orders
        orders_route = next(r for r in routes if r["path"] == "/orders")
        assert set(orders_route["methods"]) == {"GET", "POST"}

    def test_extract_authentication_apikey(self):
        """Test API Key authentication extraction."""
        parser = AzureAPIMParser()
        api = parser.parse(OPENAPI_WITH_APIKEY, "user-api")

        auth = parser.extract_authentication(api)
        assert auth is not None
        assert auth["type"] == "api_key"
        assert auth["key_name"] == "Ocp-Apim-Subscription-Key"
        assert auth["in_location"] == "header"

    def test_extract_authentication_oauth2(self):
        """Test OAuth2 authentication extraction."""
        parser = AzureAPIMParser()
        api = parser.parse(OPENAPI_WITH_OAUTH, "admin-api")

        auth = parser.extract_authentication(api)
        assert auth is not None
        assert auth["type"] == "jwt"
        assert "login.microsoftonline.com" in auth["issuer"]

    def test_extract_authentication_none(self):
        """Test authentication extraction when no security schemes."""
        parser = AzureAPIMParser()
        api = parser.parse(MINIMAL_OPENAPI, "test")

        auth = parser.extract_authentication(api)
        assert auth is None


class TestAzureAPIMProviderImport:
    """Test Azure APIM provider import functionality."""

    def test_import_minimal_openapi(self):
        """Test importing minimal OpenAPI spec."""
        provider = AzureAPIMProvider()
        config = provider.parse(MINIMAL_OPENAPI)

        assert config.version == "1.0"
        assert len(config.services) == 1

        service = config.services[0]
        assert service.name == "imported-api"
        assert service.protocol == "http"
        assert len(service.routes) == 1

        route = service.routes[0]
        assert route.path_prefix == "/pets"
        assert route.http_methods == ["GET"]

    def test_import_with_apikey(self):
        """Test importing OpenAPI with API Key security."""
        provider = AzureAPIMProvider()
        config = provider.parse(OPENAPI_WITH_APIKEY)

        service = config.services[0]
        assert len(service.routes) == 1

        route = service.routes[0]
        assert route.path_prefix == "/api/users"
        assert set(route.http_methods) == {"GET", "POST"}
        assert route.authentication is not None
        assert route.authentication.type == "api_key"
        assert route.authentication.api_key.key_name == "Ocp-Apim-Subscription-Key"
        assert route.authentication.api_key.in_location == "header"

    def test_import_with_oauth2(self):
        """Test importing OpenAPI with OAuth2 security."""
        provider = AzureAPIMProvider()
        config = provider.parse(OPENAPI_WITH_OAUTH)

        service = config.services[0]
        route = service.routes[0]

        assert route.authentication is not None
        assert route.authentication.type == "jwt"
        assert "login.microsoftonline.com" in route.authentication.jwt.issuer

    def test_import_complex_openapi(self):
        """Test importing complex OpenAPI with multiple paths."""
        provider = AzureAPIMProvider()
        config = provider.parse(COMPLEX_OPENAPI)

        service = config.services[0]
        assert len(service.routes) == 3

        # Verify backend
        assert service.upstream is not None
        assert len(service.upstream.targets) == 1
        assert service.upstream.targets[0].host == "api.ecommerce.example.com"
        assert service.upstream.targets[0].port == 443

    def test_import_backend_url_parsing(self):
        """Test backend URL parsing (host and port extraction)."""
        provider = AzureAPIMProvider()
        config = provider.parse(OPENAPI_WITH_APIKEY)

        service = config.services[0]
        upstream = service.upstream

        assert upstream.targets[0].host == "backend.example.com"
        assert upstream.targets[0].port == 8080

    def test_import_no_backend_url(self):
        """Test import when no backend URL in spec."""
        openapi_no_servers = json.loads(MINIMAL_OPENAPI)
        del openapi_no_servers["servers"]

        provider = AzureAPIMProvider()
        config = provider.parse(json.dumps(openapi_no_servers))

        service = config.services[0]
        assert service.upstream.targets[0].host == "backend.example.com"
        assert service.upstream.targets[0].port == 443

    def test_import_invalid_openapi(self):
        """Test importing invalid OpenAPI raises ValueError."""
        provider = AzureAPIMProvider()

        with pytest.raises(ValueError):
            provider.parse("{invalid json")

        with pytest.raises(ValueError):
            provider.parse("")


# Integration test: Full import workflow
class TestAzureAPIMImportIntegration:
    """Integration tests for Azure APIM import workflow."""

    def test_full_import_workflow(self):
        """Test complete import workflow: OpenAPI -> GAL Config."""
        provider = AzureAPIMProvider()
        config = provider.parse(COMPLEX_OPENAPI)

        # Validate generated config
        assert config.version == "1.0"
        assert len(config.services) == 1

        service = config.services[0]
        assert service.name == "imported-api"
        assert service.protocol == "http"
        assert len(service.routes) == 3

        # Validate routes
        route_paths = {r.path_prefix for r in service.routes}
        assert route_paths == {"/products", "/products/{id}", "/orders"}

        # Validate upstream
        assert service.upstream.targets[0].host == "api.ecommerce.example.com"
        assert service.upstream.targets[0].port == 443

    def test_import_and_export(self):
        """Test importing OpenAPI and exporting to another provider."""
        # Import from Azure APIM
        azure_provider = AzureAPIMProvider()
        config = azure_provider.parse(OPENAPI_WITH_APIKEY)

        # Validate we can now generate for other providers
        # (This would fail if import didn't produce valid GAL config)
        assert config.services[0].name == "imported-api"
        assert len(config.services[0].routes) == 1

        # Verify authentication is correctly converted
        route = config.services[0].routes[0]
        assert route.authentication is not None
        assert route.authentication.type == "api_key"
