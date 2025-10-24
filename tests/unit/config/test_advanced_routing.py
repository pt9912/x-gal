"""
Unit tests for Advanced Routing functionality.

Tests the configuration model, YAML parsing, and provider generation
for advanced routing features.
"""

import pytest
import yaml
from unittest.mock import MagicMock, patch

from gal.config import (
    AdvancedHeaderMatchRule,
    AdvancedRoutingConfig,
    AdvancedRoutingTarget,
    Config,
    GeoMatchRule,
    GlobalConfig,
    JWTClaimMatchRule,
    QueryParamMatchRule,
    Route,
    Service,
    Upstream,
    UpstreamTarget,
)
from gal.providers.envoy import EnvoyProvider


class TestAdvancedRoutingConfig:
    """Test Advanced Routing configuration models."""

    def test_header_match_rule_validation(self):
        """Test header match rule validation."""
        # Valid rule
        rule = AdvancedHeaderMatchRule(
            header_name="X-API-Version",
            match_type="exact",
            header_value="v2",
            target_name="v2_backend",
        )
        assert rule.header_name == "X-API-Version"
        assert rule.match_type == "exact"

        # Invalid match type
        with pytest.raises(ValueError) as exc_info:
            AdvancedHeaderMatchRule(
                header_name="X-Test",
                match_type="invalid",
                header_value="test",
                target_name="test",
            )
        assert "match_type must be one of" in str(exc_info.value)

    def test_jwt_claim_match_rule_validation(self):
        """Test JWT claim match rule validation."""
        # Valid rule
        rule = JWTClaimMatchRule(
            claim_name="role",
            claim_value="admin",
            match_type="exact",
            target_name="admin_backend",
        )
        assert rule.claim_name == "role"
        assert rule.claim_value == "admin"

        # Invalid match type
        with pytest.raises(ValueError) as exc_info:
            JWTClaimMatchRule(
                claim_name="test",
                claim_value="value",
                match_type="prefix",  # Not valid for JWT claims
                target_name="test",
            )
        assert "match_type must be one of" in str(exc_info.value)

    def test_geo_match_rule_validation(self):
        """Test geo match rule validation."""
        # Valid rule
        rule = GeoMatchRule(
            match_type="country",
            match_value="DE",
            target_name="eu_backend",
        )
        assert rule.match_type == "country"
        assert rule.match_value == "DE"

        # Invalid match type
        with pytest.raises(ValueError) as exc_info:
            GeoMatchRule(
                match_type="city",  # Not supported
                match_value="Berlin",
                target_name="test",
            )
        assert "match_type must be one of" in str(exc_info.value)

    def test_query_param_match_rule_validation(self):
        """Test query parameter match rule validation."""
        # Valid rule
        rule = QueryParamMatchRule(
            param_name="version",
            param_value="2",
            match_type="exact",
            target_name="v2_backend",
        )
        assert rule.param_name == "version"

        # Valid exists rule
        rule = QueryParamMatchRule(
            param_name="admin",
            param_value="",
            match_type="exists",
            target_name="admin_backend",
        )
        assert rule.match_type == "exists"

    def test_advanced_routing_config_validation(self):
        """Test advanced routing configuration validation."""
        # Valid config
        config = AdvancedRoutingConfig(
            enabled=True,
            header_rules=[
                AdvancedHeaderMatchRule(
                    "X-Version", "exact", "v2", "v2_backend"
                )
            ],
            jwt_claim_rules=[
                JWTClaimMatchRule("role", "admin", "exact", "admin_backend")
            ],
            evaluation_strategy="first_match",
        )
        assert config.enabled is True
        assert len(config.header_rules) == 1
        assert len(config.jwt_claim_rules) == 1

        # Invalid evaluation strategy
        with pytest.raises(ValueError) as exc_info:
            AdvancedRoutingConfig(evaluation_strategy="random_match")
        assert "evaluation_strategy must be one of" in str(exc_info.value)

    def test_advanced_routing_target(self):
        """Test advanced routing target configuration."""
        target = AdvancedRoutingTarget(
            name="v2_backend",
            upstream=UpstreamTarget(host="api-v2", port=8080),
            description="Version 2 API backend",
        )
        assert target.name == "v2_backend"
        assert target.upstream.host == "api-v2"
        assert target.upstream.port == 8080
        assert target.description == "Version 2 API backend"


class TestAdvancedRoutingYAMLParsing:
    """Test YAML parsing for advanced routing configuration."""

    def test_parse_advanced_routing_from_yaml(self):
        """Test parsing advanced routing configuration from YAML."""
        yaml_content = """
version: "1.0"
provider: envoy
global:
  host: 0.0.0.0
  port: 8080
services:
  - name: test_service
    type: http
    protocol: http
    upstream:
      host: default-backend
      port: 8080
    routes:
      - path_prefix: /api
        advanced_routing_targets:
          - name: v2_backend
            upstream:
              host: api-v2
              port: 8080
            description: "V2 backend"
          - name: admin_backend
            upstream:
              host: api-admin
              port: 8080
        advanced_routing:
          enabled: true
          evaluation_strategy: first_match
          header_rules:
            - header_name: X-Version
              match_type: exact
              header_value: "v2"
              target_name: v2_backend
          jwt_claim_rules:
            - claim_name: role
              claim_value: admin
              match_type: exact
              target_name: admin_backend
          geo_rules:
            - match_type: country
              match_value: DE
              target_name: v2_backend
          query_param_rules:
            - param_name: version
              param_value: "2"
              match_type: exact
              target_name: v2_backend
          fallback_target: v1_backend
"""
        # Save to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # Parse the config
            config = Config.from_yaml(temp_path)

            # Verify service and route
            assert len(config.services) == 1
            service = config.services[0]
            assert service.name == "test_service"
            assert len(service.routes) == 1
            route = service.routes[0]

            # Verify advanced routing targets
            assert len(route.advanced_routing_targets) == 2
            v2_target = route.advanced_routing_targets[0]
            assert v2_target.name == "v2_backend"
            assert v2_target.upstream.host == "api-v2"
            assert v2_target.upstream.port == 8080
            assert v2_target.description == "V2 backend"

            # Verify advanced routing config
            ar_config = route.advanced_routing
            assert ar_config is not None
            assert ar_config.enabled is True
            assert ar_config.evaluation_strategy == "first_match"
            assert ar_config.fallback_target == "v1_backend"

            # Verify rules
            assert len(ar_config.header_rules) == 1
            assert ar_config.header_rules[0].header_name == "X-Version"
            assert ar_config.header_rules[0].match_type == "exact"
            assert ar_config.header_rules[0].header_value == "v2"
            assert ar_config.header_rules[0].target_name == "v2_backend"

            assert len(ar_config.jwt_claim_rules) == 1
            assert ar_config.jwt_claim_rules[0].claim_name == "role"
            assert ar_config.jwt_claim_rules[0].claim_value == "admin"

            assert len(ar_config.geo_rules) == 1
            assert ar_config.geo_rules[0].match_type == "country"
            assert ar_config.geo_rules[0].match_value == "DE"

            assert len(ar_config.query_param_rules) == 1
            assert ar_config.query_param_rules[0].param_name == "version"
            assert ar_config.query_param_rules[0].param_value == "2"

        finally:
            import os
            os.unlink(temp_path)


class TestEnvoyProviderAdvancedRouting:
    """Test Envoy provider advanced routing generation."""

    def test_generate_envoy_with_advanced_routing(self):
        """Test generating Envoy configuration with advanced routing."""
        # Create a config with advanced routing
        upstream = Upstream(host="default-backend", port=8080)

        # Create advanced routing targets
        targets = [
            AdvancedRoutingTarget(
                name="v2_backend",
                upstream=UpstreamTarget(host="api-v2", port=8080),
            ),
            AdvancedRoutingTarget(
                name="admin_backend",
                upstream=UpstreamTarget(host="api-admin", port=8080),
            ),
        ]

        # Create advanced routing config
        ar_config = AdvancedRoutingConfig(
            enabled=True,
            header_rules=[
                AdvancedHeaderMatchRule(
                    header_name="X-Version",
                    match_type="exact",
                    header_value="v2",
                    target_name="v2_backend",
                )
            ],
            query_param_rules=[
                QueryParamMatchRule(
                    param_name="admin",
                    param_value="",
                    match_type="exists",
                    target_name="admin_backend",
                )
            ],
            fallback_target="default",
        )

        # Create route with advanced routing
        route = Route(
            path_prefix="/api",
            advanced_routing=ar_config,
            advanced_routing_targets=targets,
        )

        # Create service
        service = Service(
            name="test_service",
            type="http",
            protocol="http",
            upstream=upstream,
            routes=[route],
        )

        # Create config
        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[service],
        )

        # Generate Envoy config
        provider = EnvoyProvider()
        envoy_yaml = provider.generate(config)

        # Verify the generated config contains advanced routing
        assert "routes:" in envoy_yaml

        # Check header-based route
        assert "X-Version" in envoy_yaml
        assert "exact_match: 'v2'" in envoy_yaml
        assert "test_service_v2_backend_cluster" in envoy_yaml

        # Check query parameter route
        assert "query_parameters:" in envoy_yaml
        assert "present_match: true" in envoy_yaml
        assert "test_service_admin_backend_cluster" in envoy_yaml

        # Check clusters are generated
        assert "clusters:" in envoy_yaml
        assert "test_service_v2_backend_cluster" in envoy_yaml
        assert "test_service_admin_backend_cluster" in envoy_yaml
        assert "test_service_cluster" in envoy_yaml  # Default cluster

    def test_generate_envoy_header_match_types(self):
        """Test different header match types in Envoy generation."""
        # Create routes with different header match types
        targets = [
            AdvancedRoutingTarget(
                name="target",
                upstream=UpstreamTarget(host="backend", port=8080),
            )
        ]

        test_cases = [
            ("exact", "exact_match: 'test'"),
            ("prefix", "prefix_match: 'test'"),
            ("contains", "contains_match: 'test'"),
            ("regex", "safe_regex_match:"),
        ]

        provider = EnvoyProvider()

        for match_type, expected_output in test_cases:
            ar_config = AdvancedRoutingConfig(
                enabled=True,
                header_rules=[
                    AdvancedHeaderMatchRule(
                        header_name="X-Test",
                        match_type=match_type,
                        header_value="test",
                        target_name="target",
                    )
                ],
            )

            route = Route(
                path_prefix="/api",
                advanced_routing=ar_config,
                advanced_routing_targets=targets,
            )

            service = Service(
                name="test",
                type="http",
                protocol="http",
                upstream=Upstream(host="default", port=8080),
                routes=[route],
            )

            config = Config(
                version="1.0",
                provider="envoy",
                global_config=GlobalConfig(host="0.0.0.0", port=8080),
                services=[service],
            )

            envoy_yaml = provider.generate(config)
            assert expected_output in envoy_yaml, f"Failed for match_type: {match_type}"

    def test_generate_envoy_query_param_match_types(self):
        """Test different query parameter match types in Envoy generation."""
        targets = [
            AdvancedRoutingTarget(
                name="target",
                upstream=UpstreamTarget(host="backend", port=8080),
            )
        ]

        test_cases = [
            ("exact", "string_match:", "exact: '2'"),
            ("exists", "present_match: true", None),
            ("regex", "safe_regex:", "regex: '^v[2-9]$'"),
        ]

        provider = EnvoyProvider()

        for match_type, expected1, expected2 in test_cases:
            ar_config = AdvancedRoutingConfig(
                enabled=True,
                query_param_rules=[
                    QueryParamMatchRule(
                        param_name="version",
                        param_value="2" if match_type != "regex" else "^v[2-9]$",
                        match_type=match_type,
                        target_name="target",
                    )
                ],
            )

            route = Route(
                path_prefix="/api",
                advanced_routing=ar_config,
                advanced_routing_targets=targets,
            )

            service = Service(
                name="test",
                type="http",
                protocol="http",
                upstream=Upstream(host="default", port=8080),
                routes=[route],
            )

            config = Config(
                version="1.0",
                provider="envoy",
                global_config=GlobalConfig(host="0.0.0.0", port=8080),
                services=[service],
            )

            envoy_yaml = provider.generate(config)
            assert expected1 in envoy_yaml, f"Failed for match_type: {match_type}"
            if expected2:
                assert expected2 in envoy_yaml, f"Failed for match_type: {match_type}"

    def test_jwt_and_geo_rules_as_comments(self):
        """Test that JWT and Geo rules are added as comments (since they need Lua)."""
        targets = [
            AdvancedRoutingTarget(
                name="target",
                upstream=UpstreamTarget(host="backend", port=8080),
            )
        ]

        ar_config = AdvancedRoutingConfig(
            enabled=True,
            jwt_claim_rules=[
                JWTClaimMatchRule(
                    claim_name="role",
                    claim_value="admin",
                    match_type="exact",
                    target_name="target",
                )
            ],
            geo_rules=[
                GeoMatchRule(
                    match_type="country",
                    match_value="DE",
                    target_name="target",
                )
            ],
        )

        route = Route(
            path_prefix="/api",
            advanced_routing=ar_config,
            advanced_routing_targets=targets,
        )

        service = Service(
            name="test",
            type="http",
            protocol="http",
            upstream=Upstream(host="default", port=8080),
            routes=[route],
        )

        config = Config(
            version="1.0",
            provider="envoy",
            global_config=GlobalConfig(host="0.0.0.0", port=8080),
            services=[service],
        )

        provider = EnvoyProvider()
        envoy_yaml = provider.generate(config)

        # Check that JWT and Geo rules are mentioned in comments
        assert "# JWT claim-based routing requires Lua filter" in envoy_yaml
        assert "# - role=admin -> target" in envoy_yaml
        assert "# Geo-based routing requires GeoIP database and Lua filter" in envoy_yaml
        assert "# - country=DE -> target" in envoy_yaml


if __name__ == "__main__":
    pytest.main([__file__, "-v"])