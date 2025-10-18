"""
Tests for Body Transformation feature (v1.2.0 Feature 4).

Tests request and response body transformation across all providers.
"""

import json

import pytest
import yaml

from gal.config import (
    BodyTransformationConfig,
    Config,
    GlobalConfig,
    RequestBodyTransformation,
    ResponseBodyTransformation,
    Route,
    Service,
    Upstream,
    UpstreamTarget,
)
from gal.providers.apisix import APISIXProvider
from gal.providers.envoy import EnvoyProvider
from gal.providers.haproxy import HAProxyProvider
from gal.providers.kong import KongProvider
from gal.providers.nginx import NginxProvider
from gal.providers.traefik import TraefikProvider


class TestBodyTransformation:
    """Test body transformation for all providers."""

    def test_config_model(self):
        """Test BodyTransformationConfig data model."""
        # Request transformation
        request = RequestBodyTransformation(
            add_fields={"trace_id": "{{uuid}}", "timestamp": "{{now}}"},
            remove_fields=["internal_id", "secret"],
            rename_fields={"old_field": "new_field"},
        )

        # Response transformation
        response = ResponseBodyTransformation(
            filter_fields=["password", "api_key"], add_fields={"server_time": "{{now}}"}
        )

        # Combined transformation
        bt = BodyTransformationConfig(enabled=True, request=request, response=response)

        assert bt.enabled is True
        assert bt.request.add_fields["trace_id"] == "{{uuid}}"
        assert bt.request.remove_fields == ["internal_id", "secret"]
        assert bt.request.rename_fields["old_field"] == "new_field"
        assert bt.response.filter_fields == ["password", "api_key"]
        assert bt.response.add_fields["server_time"] == "{{now}}"

    def test_envoy_request_body_transformation(self):
        """Test Envoy request body transformation."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                request=RequestBodyTransformation(
                                    add_fields={"request_id": "{{uuid}}", "created_at": "{{now}}"},
                                    remove_fields=["internal_secret"],
                                    rename_fields={"user_id": "id"},
                                ),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = EnvoyProvider()
        output = provider.generate(config)

        # Check for Lua filter
        assert "envoy.filters.http.lua" in output
        assert "function envoy_on_request" in output

        # Check for add_fields logic
        assert "request_id" in output
        assert "created_at" in output
        assert "generate_uuid()" in output
        assert "get_timestamp()" in output

        # Check for remove_fields logic
        assert "internal_secret" in output
        assert "= nil" in output

        # Check for rename_fields logic
        assert "user_id" in output

    def test_envoy_response_body_transformation(self):
        """Test Envoy response body transformation."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                response=ResponseBodyTransformation(
                                    filter_fields=["password", "ssn"],
                                    add_fields={"server_time": "{{timestamp}}"},
                                ),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = EnvoyProvider()
        output = provider.generate(config)

        # Check for response transformation
        assert "function envoy_on_response" in output
        assert "password" in output
        assert "ssn" in output
        assert "server_time" in output

    def test_kong_request_body_transformation(self):
        """Test Kong request body transformation."""
        config = Config(
            version="1.0",
            provider="kong",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                request=RequestBodyTransformation(
                                    add_fields={"trace_id": "{{uuid}}"}, remove_fields=["secret"]
                                ),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = KongProvider()
        output = provider.generate(config)

        # Check for request-transformer plugin
        assert "request-transformer" in output
        assert "add" in output
        assert "json" in output
        assert "trace_id" in output
        assert "remove" in output
        assert "secret" in output

    def test_kong_response_body_transformation(self):
        """Test Kong response body transformation."""
        config = Config(
            version="1.0",
            provider="kong",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                response=ResponseBodyTransformation(
                                    filter_fields=["password"], add_fields={"version": "v1"}
                                ),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = KongProvider()
        output = provider.generate(config)

        # Check for response-transformer plugin
        assert "response-transformer" in output
        assert "remove" in output
        assert "password" in output
        assert "add" in output
        assert "version" in output

    def test_apisix_request_body_transformation(self):
        """Test APISIX request body transformation."""
        config = Config(
            version="1.0",
            provider="apisix",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                request=RequestBodyTransformation(
                                    add_fields={"request_id": "{{uuid}}"},
                                    remove_fields=["internal"],
                                    rename_fields={"old": "new"},
                                ),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = APISIXProvider()
        output = provider.generate(config)
        config_json = json.loads(output)

        # Check for serverless-pre-function plugin
        route = config_json["routes"][0]
        assert "serverless-pre-function" in route["plugins"]

        plugin = route["plugins"]["serverless-pre-function"]
        assert plugin["phase"] == "rewrite"
        assert "function" in plugin["functions"][0]

        lua_code = plugin["functions"][0]
        assert "request_id" in lua_code
        assert "core.utils.uuid()" in lua_code
        assert "internal" in lua_code
        assert "nil" in lua_code
        assert "old" in lua_code
        assert "new" in lua_code

    def test_apisix_response_body_transformation(self):
        """Test APISIX response body transformation."""
        config = Config(
            version="1.0",
            provider="apisix",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                response=ResponseBodyTransformation(
                                    filter_fields=["password"], add_fields={"api_version": "1.0"}
                                ),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = APISIXProvider()
        output = provider.generate(config)
        config_json = json.loads(output)

        # Check for serverless-post-function plugin
        route = config_json["routes"][0]
        assert "serverless-post-function" in route["plugins"]

        plugin = route["plugins"]["serverless-post-function"]
        assert plugin["phase"] == "body_filter"

        lua_code = plugin["functions"][0]
        assert "password" in lua_code
        assert "api_version" in lua_code

    def test_traefik_body_transformation_warning(self, caplog):
        """Test Traefik body transformation warning (not natively supported)."""
        import logging

        config = Config(
            version="1.0",
            provider="traefik",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                request=RequestBodyTransformation(
                                    add_fields={"trace_id": "{{uuid}}"}
                                ),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = TraefikProvider()

        # Should generate config and log warning
        with caplog.at_level(logging.WARNING):
            output = provider.generate(config)

        # Config should still be generated
        assert "routers:" in output

        # Check that warning was logged
        assert "does not natively support" in caplog.text
        assert "ForwardAuth" in caplog.text or "Custom Traefik plugin" in caplog.text

    def test_nginx_request_body_transformation(self):
        """Test Nginx request body transformation (OpenResty)."""
        config = Config(
            version="1.0",
            provider="nginx",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="api-1.internal", port=8080, weight=1)]
                    ),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                request=RequestBodyTransformation(
                                    add_fields={"request_id": "{{uuid}}"},
                                    remove_fields=["secret"],
                                    rename_fields={"user_id": "id"},
                                ),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = NginxProvider()
        output = provider.generate(config)

        # Check for Lua blocks
        assert "access_by_lua_block" in output
        assert "cjson" in output
        assert "request_id" in output
        assert "ngx.var.request_id" in output
        assert "secret" in output
        assert "user_id" in output

    def test_nginx_response_body_transformation(self):
        """Test Nginx response body transformation (OpenResty)."""
        config = Config(
            version="1.0",
            provider="nginx",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="api-1.internal", port=8080, weight=1)]
                    ),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                response=ResponseBodyTransformation(
                                    filter_fields=["password"], add_fields={"server": "nginx"}
                                ),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = NginxProvider()
        output = provider.generate(config)

        # Check for response transformation
        assert "body_filter_by_lua_block" in output
        assert "password" in output
        assert "server" in output

    def test_haproxy_body_transformation_lua_reference(self):
        """Test HAProxy body transformation Lua function references."""
        config = Config(
            version="1.0",
            provider="haproxy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(
                        targets=[UpstreamTarget(host="api-1.internal", port=8080, weight=1)]
                    ),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                request=RequestBodyTransformation(
                                    add_fields={"trace_id": "{{uuid}}"}
                                ),
                                response=ResponseBodyTransformation(filter_fields=["password"]),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = HAProxyProvider()

        # Should generate config with Lua references and log warning
        output = provider.generate(config)

        # Check for Lua function references
        assert "http-request lua." in output
        assert "http-response lua." in output
        assert "transform_request_" in output
        assert "transform_response_" in output

    def test_all_transformation_features_combined(self):
        """Test all transformation features combined (Envoy)."""
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[
                Service(
                    name="api_service",
                    type="rest",
                    protocol="http",
                    upstream=Upstream(host="api.internal", port=8080),
                    routes=[
                        Route(
                            path_prefix="/api/users",
                            body_transformation=BodyTransformationConfig(
                                enabled=True,
                                request=RequestBodyTransformation(
                                    add_fields={
                                        "trace_id": "{{uuid}}",
                                        "timestamp": "{{now}}",
                                        "api_version": "v1",
                                        "priority": 1,
                                    },
                                    remove_fields=["internal_id", "secret_key", "password"],
                                    rename_fields={
                                        "user_id": "id",
                                        "user_name": "name",
                                        "user_email": "email",
                                    },
                                ),
                                response=ResponseBodyTransformation(
                                    filter_fields=["password", "ssn", "credit_card"],
                                    add_fields={
                                        "server_time": "{{timestamp}}",
                                        "server_id": "envoy-1",
                                    },
                                ),
                            ),
                        )
                    ],
                )
            ],
        )

        provider = EnvoyProvider()
        output = provider.generate(config)

        # Verify all request transformations
        assert "trace_id" in output
        assert "timestamp" in output
        assert "api_version" in output
        assert "priority" in output
        assert "internal_id" in output
        assert "secret_key" in output
        assert "user_id" in output
        assert "id" in output

        # Verify all response transformations
        assert "password" in output
        assert "ssn" in output
        assert "credit_card" in output
        assert "server_time" in output
        assert "server_id" in output
