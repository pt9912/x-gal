"""
Tests for GCP API Gateway Provider
"""

import pytest
import yaml
from gal.config import (
    Config,
    GlobalConfig,
    GCPAPIGatewayConfig,
    Service,
    Upstream,
    UpstreamTarget,
    Route,
)
from gal.providers.gcp_apigateway import GCPAPIGatewayProvider


class TestGCPAPIGatewayProvider:
    """Test GCP API Gateway provider functionality."""

    def test_provider_initialization(self):
        """Test provider can be initialized."""
        provider = GCPAPIGatewayProvider()
        assert provider.name == "gcp_apigateway"

    def test_generate_basic_config(self):
        """Test generating basic OpenAPI 2.0 spec."""
        config = Config(
            version="1.0",
            provider="gcp_apigateway",
            global_config=GlobalConfig(
                gcp_apigateway=GCPAPIGatewayConfig(
                    project_id="test-project",
                    api_id="test-api",
                    backend_address="https://backend.example.com",
                )
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="backend.example.com", port=443)]
                    ),
                    routes=[
                        Route(path_prefix="/api/test", methods=["GET", "POST"])
                    ],
                )
            ],
        )

        provider = GCPAPIGatewayProvider()
        result = provider.generate(config)

        # Parse YAML
        spec = yaml.safe_load(result)

        # Validate OpenAPI 2.0
        assert spec["swagger"] == "2.0"
        assert spec["info"]["title"] == "GAL API"
        assert "https" in spec["schemes"]

        # Validate x-google-backend
        assert "x-google-backend" in spec
        assert spec["x-google-backend"]["address"] == "https://backend.example.com"

        # Validate paths
        assert "/api/test" in spec["paths"]
        assert "get" in spec["paths"]["/api/test"]
        assert "post" in spec["paths"]["/api/test"]
        assert "options" in spec["paths"]["/api/test"]  # CORS

    def test_generate_with_jwt_auth(self):
        """Test generating spec with JWT authentication."""
        config = Config(
            version="1.0",
            provider="gcp_apigateway",
            global_config=GlobalConfig(
                gcp_apigateway=GCPAPIGatewayConfig(
                    project_id="test-project",
                    api_id="secure-api",
                    backend_address="https://backend.example.com",
                    jwt_issuer="https://accounts.google.com",
                    jwt_jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
                    jwt_audiences=["https://test-project.example.com"],
                )
            ),
            services=[
                Service(
                    name="secure_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="backend.example.com", port=443)]
                    ),
                    routes=[Route(path_prefix="/api/secure", methods=["GET"])],
                )
            ],
        )

        provider = GCPAPIGatewayProvider()
        result = provider.generate(config)
        spec = yaml.safe_load(result)

        # Validate security definitions
        assert "securityDefinitions" in spec
        assert "google_jwt" in spec["securityDefinitions"]

        jwt_def = spec["securityDefinitions"]["google_jwt"]
        assert jwt_def["type"] == "oauth2"
        assert jwt_def["x-google-issuer"] == "https://accounts.google.com"
        assert jwt_def["x-google-jwks_uri"] == "https://www.googleapis.com/oauth2/v3/certs"
        assert "https://test-project.example.com" in jwt_def["x-google-audiences"]

        # Validate security requirement on operations
        assert "security" in spec["paths"]["/api/secure"]["get"]
        assert {"google_jwt": []} in spec["paths"]["/api/secure"]["get"]["security"]

    def test_generate_with_cors(self):
        """Test CORS configuration."""
        config = Config(
            version="1.0",
            provider="gcp_apigateway",
            global_config=GlobalConfig(
                gcp_apigateway=GCPAPIGatewayConfig(
                    project_id="test-project",
                    backend_address="https://backend.example.com",
                    cors_enabled=True,
                    cors_allow_origins=["https://app.example.com"],
                    cors_allow_methods=["GET", "POST"],
                    cors_allow_headers=["Content-Type", "Authorization"],
                    cors_max_age=7200,
                )
            ),
            services=[
                Service(
                    name="cors_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="backend.example.com", port=443)]
                    ),
                    routes=[Route(path_prefix="/api/data", methods=["GET"])],
                )
            ],
        )

        provider = GCPAPIGatewayProvider()
        result = provider.generate(config)
        spec = yaml.safe_load(result)

        # Validate OPTIONS method exists
        assert "options" in spec["paths"]["/api/data"]

        options_method = spec["paths"]["/api/data"]["options"]
        assert options_method["summary"] == "CORS preflight"
        assert "200" in options_method["responses"]

    def test_generate_missing_project_id(self):
        """Test error when project_id is missing."""
        config = Config(
            version="1.0",
            provider="gcp_apigateway",
            global_config=GlobalConfig(
                gcp_apigateway=GCPAPIGatewayConfig(
                    project_id="",  # Missing
                    backend_address="https://backend.example.com",
                )
            ),
            services=[],
        )

        provider = GCPAPIGatewayProvider()

        with pytest.raises(ValueError, match="project_id is required"):
            provider.generate(config)

    def test_generate_missing_gcp_config(self):
        """Test error when GCP config is missing."""
        config = Config(
            version="1.0",
            provider="gcp_apigateway",
            global_config=GlobalConfig(),  # No gcp_apigateway
            services=[],
        )

        provider = GCPAPIGatewayProvider()

        with pytest.raises(ValueError, match="GCP API Gateway configuration is required"):
            provider.generate(config)

    def test_parse_implemented(self):
        """Test parse method is now implemented."""
        openapi_spec = """
        swagger: "2.0"
        info:
          title: "Test API"
          version: "1.0.0"
        x-google-backend:
          address: "https://backend.example.com"
        paths:
          /api/test:
            get:
              responses:
                200:
                  description: "Success"
        """

        provider = GCPAPIGatewayProvider()
        config = provider.parse(openapi_spec)

        # Validate that parse works
        assert config is not None
        assert config.version == "1.0"
        assert len(config.services) == 1

    def test_backend_path_translation(self):
        """Test backend path translation configuration."""
        config = Config(
            version="1.0",
            provider="gcp_apigateway",
            global_config=GlobalConfig(
                gcp_apigateway=GCPAPIGatewayConfig(
                    project_id="test-project",
                    backend_address="https://backend.example.com",
                    backend_path_translation="CONSTANT_ADDRESS",
                    backend_deadline=60.0,
                )
            ),
            services=[
                Service(
                    name="test_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="backend.example.com", port=443)]
                    ),
                    routes=[Route(path_prefix="/api/test", methods=["GET"])],
                )
            ],
        )

        provider = GCPAPIGatewayProvider()
        result = provider.generate(config)
        spec = yaml.safe_load(result)

        # Validate x-google-backend settings
        backend = spec["x-google-backend"]
        assert backend["path_translation"] == "CONSTANT_ADDRESS"
        assert backend["deadline"] == 60.0

    def test_service_account_backend_auth(self):
        """Test backend authentication with service account."""
        config = Config(
            version="1.0",
            provider="gcp_apigateway",
            global_config=GlobalConfig(
                gcp_apigateway=GCPAPIGatewayConfig(
                    project_id="test-project",
                    backend_address="https://cloudrun-service.example.com",
                    service_account_email="api-gateway@test-project.iam.gserviceaccount.com",
                    backend_jwt_audience="https://cloudrun-service.example.com",
                    backend_disable_auth=False,
                )
            ),
            services=[
                Service(
                    name="cloudrun_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="cloudrun-service.example.com", port=443)]
                    ),
                    routes=[Route(path_prefix="/api/v1", methods=["GET"])],
                )
            ],
        )

        provider = GCPAPIGatewayProvider()
        result = provider.generate(config)
        spec = yaml.safe_load(result)

        # Validate backend JWT audience
        backend = spec["x-google-backend"]
        assert backend["jwt_audience"] == "https://cloudrun-service.example.com"
        assert "disable_auth" not in backend  # Should not be present when False
