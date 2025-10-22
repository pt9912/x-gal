"""
Tests for Traffic Splitting configuration and provider implementations.

Feature 5: A/B Testing & Traffic Splitting
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from gal.config import (
    Config,
    CookieMatchRule,
    GlobalConfig,
    HeaderMatchRule,
    Route,
    RoutingRules,
    Service,
    SplitTarget,
    TrafficSplitConfig,
    Upstream,
    UpstreamTarget,
)
from gal.providers.apisix import APISIXProvider
from gal.providers.aws_apigateway import AWSAPIGatewayProvider
from gal.providers.azure_apim import AzureAPIMProvider
from gal.providers.envoy import EnvoyProvider
from gal.providers.haproxy import HAProxyProvider
from gal.providers.kong import KongProvider
from gal.providers.nginx import NginxProvider
from gal.providers.traefik import TraefikProvider


class TestTrafficSplitConfig:
    """Test TrafficSplitConfig dataclass and validation"""

    def test_simple_weight_based_split(self):
        """Test simple 90/10 canary deployment"""
        target1 = SplitTarget(
            name="stable",
            weight=90,
            upstream=UpstreamTarget(host="api-stable", port=8080),
            description="Stable version",
        )
        target2 = SplitTarget(
            name="canary",
            weight=10,
            upstream=UpstreamTarget(host="api-canary", port=8080),
            description="Canary version",
        )

        config = TrafficSplitConfig(enabled=True, targets=[target1, target2])

        assert config.enabled is True
        assert len(config.targets) == 2
        assert config.targets[0].weight == 90
        assert config.targets[1].weight == 10

    def test_weight_validation_sum_100(self):
        """Test that weights must sum to 100"""
        target1 = SplitTarget(
            name="stable", weight=90, upstream=UpstreamTarget(host="api-stable", port=8080)
        )
        target2 = SplitTarget(
            name="canary", weight=20, upstream=UpstreamTarget(host="api-canary", port=8080)
        )

        with pytest.raises(ValueError, match="must sum to 100"):
            TrafficSplitConfig(enabled=True, targets=[target1, target2])

    def test_weight_range_validation(self):
        """Test that weight must be between 0 and 100"""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            SplitTarget(
                name="invalid",
                weight=150,
                upstream=UpstreamTarget(host="api", port=8080),
            )

    def test_unique_target_names(self):
        """Test that target names must be unique"""
        target1 = SplitTarget(
            name="stable", weight=50, upstream=UpstreamTarget(host="api-stable", port=8080)
        )
        target2 = SplitTarget(
            name="stable", weight=50, upstream=UpstreamTarget(host="api-canary", port=8080)
        )

        with pytest.raises(ValueError, match="must be unique"):
            TrafficSplitConfig(enabled=True, targets=[target1, target2])

    def test_fallback_target_validation(self):
        """Test that fallback_target must exist in targets"""
        target1 = SplitTarget(
            name="stable", weight=100, upstream=UpstreamTarget(host="api-stable", port=8080)
        )

        with pytest.raises(ValueError, match="not found in targets"):
            TrafficSplitConfig(enabled=True, targets=[target1], fallback_target="nonexistent")

    def test_header_based_routing(self):
        """Test header-based routing configuration"""
        target1 = SplitTarget(
            name="production", weight=100, upstream=UpstreamTarget(host="api-prod", port=8080)
        )
        target2 = SplitTarget(
            name="beta", weight=0, upstream=UpstreamTarget(host="api-beta", port=8080)
        )

        header_rule = HeaderMatchRule(
            header_name="X-Version", header_value="beta", target_name="beta"
        )

        routing_rules = RoutingRules(header_rules=[header_rule])

        config = TrafficSplitConfig(
            enabled=True,
            targets=[target1, target2],
            routing_rules=routing_rules,
            fallback_target="production",
        )

        assert config.routing_rules is not None
        assert len(config.routing_rules.header_rules) == 1
        assert config.routing_rules.header_rules[0].header_name == "X-Version"
        assert config.fallback_target == "production"

    def test_cookie_based_routing(self):
        """Test cookie-based routing configuration"""
        target1 = SplitTarget(
            name="stable", weight=100, upstream=UpstreamTarget(host="api-stable", port=8080)
        )
        target2 = SplitTarget(
            name="canary", weight=0, upstream=UpstreamTarget(host="api-canary", port=8080)
        )

        cookie_rule = CookieMatchRule(
            cookie_name="canary_user", cookie_value="true", target_name="canary"
        )

        routing_rules = RoutingRules(cookie_rules=[cookie_rule])

        config = TrafficSplitConfig(
            enabled=True,
            targets=[target1, target2],
            routing_rules=routing_rules,
            fallback_target="stable",
        )

        assert config.routing_rules is not None
        assert len(config.routing_rules.cookie_rules) == 1
        assert config.routing_rules.cookie_rules[0].cookie_name == "canary_user"


class TestTrafficSplitYAMLParsing:
    """Test YAML parsing for traffic splitting configuration"""

    def test_parse_simple_canary(self):
        """Test parsing simple canary deployment YAML"""
        yaml_content = """
version: "1.0"
provider: envoy

services:
  - name: api
    type: rest
    protocol: http
    upstream:
      host: placeholder
      port: 8080
    routes:
      - path_prefix: /api
        traffic_split:
          enabled: true
          targets:
            - name: stable
              weight: 90
              upstream:
                host: api-stable
                port: 8080
            - name: canary
              weight: 10
              upstream:
                host: api-canary
                port: 8080
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            config = Config.from_yaml(f.name)

            assert len(config.services) == 1
            service = config.services[0]
            assert len(service.routes) == 1
            route = service.routes[0]

            assert route.traffic_split is not None
            assert route.traffic_split.enabled is True
            assert len(route.traffic_split.targets) == 2
            assert route.traffic_split.targets[0].name == "stable"
            assert route.traffic_split.targets[0].weight == 90
            assert route.traffic_split.targets[1].name == "canary"
            assert route.traffic_split.targets[1].weight == 10

            Path(f.name).unlink()

    def test_parse_with_routing_rules(self):
        """Test parsing traffic split with header and cookie rules"""
        yaml_content = """
version: "1.0"
provider: envoy

services:
  - name: api
    type: rest
    protocol: http
    upstream:
      host: placeholder
      port: 8080
    routes:
      - path_prefix: /api
        traffic_split:
          enabled: true
          targets:
            - name: production
              weight: 100
              upstream:
                host: api-prod
                port: 8080
            - name: beta
              weight: 0
              upstream:
                host: api-beta
                port: 8080
          routing_rules:
            header_rules:
              - header_name: X-Version
                header_value: beta
                target_name: beta
            cookie_rules:
              - cookie_name: user_tier
                cookie_value: premium
                target_name: beta
          fallback_target: production
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            config = Config.from_yaml(f.name)
            route = config.services[0].routes[0]

            assert route.traffic_split.routing_rules is not None
            assert len(route.traffic_split.routing_rules.header_rules) == 1
            assert len(route.traffic_split.routing_rules.cookie_rules) == 1
            assert route.traffic_split.fallback_target == "production"

            Path(f.name).unlink()


class TestEnvoyTrafficSplit:
    """Test Envoy provider traffic splitting generation"""

    def test_weighted_clusters_generation(self):
        """Test Envoy weighted_clusters configuration"""
        config = self._create_test_config()
        provider = EnvoyProvider()

        output = provider.generate(config)

        # Check for weighted_clusters configuration
        assert "weighted_clusters:" in output
        assert "api_stable_cluster" in output
        assert "api_canary_cluster" in output
        assert "weight: 90" in output
        assert "weight: 10" in output
        assert "total_weight: 100" in output

    def test_separate_clusters_per_target(self):
        """Test that Envoy generates separate clusters for each target"""
        config = self._create_test_config()
        provider = EnvoyProvider()

        output = provider.generate(config)

        # Check for individual cluster definitions
        assert "- name: api_stable_cluster" in output
        assert "- name: api_canary_cluster" in output
        assert "address: api-stable" in output
        assert "address: api-canary" in output

    @staticmethod
    def _create_test_config():
        """Create test configuration with traffic splitting"""
        target1 = SplitTarget(
            name="stable", weight=90, upstream=UpstreamTarget(host="api-stable", port=8080)
        )
        target2 = SplitTarget(
            name="canary", weight=10, upstream=UpstreamTarget(host="api-canary", port=8080)
        )

        traffic_split = TrafficSplitConfig(enabled=True, targets=[target1, target2])

        route = Route(path_prefix="/api", traffic_split=traffic_split)

        service = Service(
            name="api",
            type="rest",
            protocol="http",
            upstream=Upstream(host="placeholder", port=8080),
            routes=[route],
        )

        global_config = GlobalConfig()

        return Config(
            version="1.0", provider="envoy", global_config=global_config, services=[service]
        )


class TestNginxTrafficSplit:
    """Test Nginx provider traffic splitting generation"""

    def test_set_random_generation(self):
        """Test Nginx set_random directive for weight-based routing"""
        config = self._create_test_config()
        provider = NginxProvider()

        output = provider.generate(config)

        # Check for set_random and conditional routing
        assert "set_random $rand_split 0 100" in output
        assert "if ($rand_split < 90)" in output
        assert "proxy_pass http://api-stable:8080" in output
        assert "proxy_pass http://api-canary:8080" in output

    @staticmethod
    def _create_test_config():
        """Create test configuration with traffic splitting"""
        target1 = SplitTarget(
            name="stable", weight=90, upstream=UpstreamTarget(host="api-stable", port=8080)
        )
        target2 = SplitTarget(
            name="canary", weight=10, upstream=UpstreamTarget(host="api-canary", port=8080)
        )

        traffic_split = TrafficSplitConfig(enabled=True, targets=[target1, target2])

        route = Route(path_prefix="/api", traffic_split=traffic_split)

        service = Service(
            name="api",
            type="rest",
            protocol="http",
            upstream=Upstream(host="placeholder", port=8080),
            routes=[route],
        )

        global_config = GlobalConfig()

        return Config(
            version="1.0", provider="nginx", global_config=global_config, services=[service]
        )


class TestKongTrafficSplit:
    """Test Kong provider traffic splitting generation"""

    def test_weighted_upstream_targets(self):
        """Test Kong weighted upstream targets configuration"""
        config = self._create_test_config()
        provider = KongProvider()

        output = provider.generate(config)

        # Check for upstream with weighted targets
        assert "upstreams:" in output
        assert "api_route0_upstream" in output
        assert "weight: 900" in output  # Kong uses 0-1000 scale (90 * 10)
        assert "weight: 100" in output  # Kong uses 0-1000 scale (10 * 10)
        assert "target: api-stable:8080" in output
        assert "target: api-canary:8080" in output

    @staticmethod
    def _create_test_config():
        """Create test configuration with traffic splitting"""
        target1 = SplitTarget(
            name="stable", weight=90, upstream=UpstreamTarget(host="api-stable", port=8080)
        )
        target2 = SplitTarget(
            name="canary", weight=10, upstream=UpstreamTarget(host="api-canary", port=8080)
        )

        traffic_split = TrafficSplitConfig(enabled=True, targets=[target1, target2])

        route = Route(path_prefix="/api", traffic_split=traffic_split)

        service = Service(
            name="api",
            type="rest",
            protocol="http",
            upstream=Upstream(host="placeholder", port=8080),
            routes=[route],
        )

        global_config = GlobalConfig()

        return Config(
            version="1.0", provider="kong", global_config=global_config, services=[service]
        )


class TestAPISIXTrafficSplit:
    """Test APISIX provider traffic splitting generation"""

    def test_traffic_split_plugin(self):
        """Test APISIX traffic-split plugin configuration"""
        config = self._create_test_config()
        provider = APISIXProvider()

        output = provider.generate(config)

        # Check for traffic-split plugin
        assert '"traffic-split"' in output
        assert '"rules"' in output
        assert '"weighted_upstreams"' in output
        assert '"weight": 90' in output
        assert '"weight": 10' in output

    @staticmethod
    def _create_test_config():
        """Create test configuration with traffic splitting"""
        target1 = SplitTarget(
            name="stable", weight=90, upstream=UpstreamTarget(host="api-stable", port=8080)
        )
        target2 = SplitTarget(
            name="canary", weight=10, upstream=UpstreamTarget(host="api-canary", port=8080)
        )

        traffic_split = TrafficSplitConfig(enabled=True, targets=[target1, target2])

        route = Route(path_prefix="/api", traffic_split=traffic_split)

        service = Service(
            name="api",
            type="rest",
            protocol="http",
            upstream=Upstream(host="placeholder", port=8080),
            routes=[route],
        )

        global_config = GlobalConfig()

        return Config(
            version="1.0", provider="apisix", global_config=global_config, services=[service]
        )


class TestTraefikTrafficSplit:
    """Test Traefik provider traffic splitting generation"""

    def test_weighted_services(self):
        """Test Traefik weighted services configuration"""
        config = self._create_test_config()
        provider = TraefikProvider()

        output = provider.generate(config)

        # Check for weighted services
        assert "weighted:" in output
        assert "api_route0_service:" in output
        assert "api_stable_service:" in output
        assert "api_canary_service:" in output
        assert "weight: 90" in output
        assert "weight: 10" in output

    @staticmethod
    def _create_test_config():
        """Create test configuration with traffic splitting"""
        target1 = SplitTarget(
            name="stable", weight=90, upstream=UpstreamTarget(host="api-stable", port=8080)
        )
        target2 = SplitTarget(
            name="canary", weight=10, upstream=UpstreamTarget(host="api-canary", port=8080)
        )

        traffic_split = TrafficSplitConfig(enabled=True, targets=[target1, target2])

        route = Route(path_prefix="/api", traffic_split=traffic_split)

        service = Service(
            name="api",
            type="rest",
            protocol="http",
            upstream=Upstream(host="placeholder", port=8080),
            routes=[route],
        )

        global_config = GlobalConfig()

        return Config(
            version="1.0", provider="traefik", global_config=global_config, services=[service]
        )


class TestTrafficSplitUseCases:
    """Test common traffic splitting use cases"""

    def test_canary_deployment_5_percent(self):
        """Test 95/5 canary deployment"""
        target1 = SplitTarget(
            name="current", weight=95, upstream=UpstreamTarget(host="api-v1", port=8080)
        )
        target2 = SplitTarget(
            name="new", weight=5, upstream=UpstreamTarget(host="api-v2", port=8080)
        )

        config = TrafficSplitConfig(enabled=True, targets=[target1, target2])

        assert config.targets[0].weight == 95
        assert config.targets[1].weight == 5

    def test_ab_testing_50_50(self):
        """Test 50/50 A/B testing split"""
        target1 = SplitTarget(
            name="version_a", weight=50, upstream=UpstreamTarget(host="api-v2-a", port=8080)
        )
        target2 = SplitTarget(
            name="version_b", weight=50, upstream=UpstreamTarget(host="api-v2-b", port=8080)
        )

        config = TrafficSplitConfig(enabled=True, targets=[target1, target2])

        assert config.targets[0].weight == 50
        assert config.targets[1].weight == 50

    def test_blue_green_deployment(self):
        """Test blue/green deployment (100/0 or 0/100)"""
        target1 = SplitTarget(
            name="blue", weight=100, upstream=UpstreamTarget(host="api-blue", port=8080)
        )
        target2 = SplitTarget(
            name="green", weight=0, upstream=UpstreamTarget(host="api-green", port=8080)
        )

        config = TrafficSplitConfig(enabled=True, targets=[target1, target2])

        assert config.targets[0].weight == 100
        assert config.targets[1].weight == 0

    def test_multi_version_split(self):
        """Test multi-version traffic split (70/20/10)"""
        target1 = SplitTarget(
            name="stable", weight=70, upstream=UpstreamTarget(host="api-stable", port=8080)
        )
        target2 = SplitTarget(
            name="beta", weight=20, upstream=UpstreamTarget(host="api-beta", port=8080)
        )
        target3 = SplitTarget(
            name="canary", weight=10, upstream=UpstreamTarget(host="api-canary", port=8080)
        )

        config = TrafficSplitConfig(enabled=True, targets=[target1, target2, target3])

        assert len(config.targets) == 3
        assert sum(t.weight for t in config.targets) == 100


class TestHAProxyTrafficSplit:
    """Test HAProxy traffic splitting implementation"""

    def _create_test_config(self):
        """Helper to create test configuration"""
        global_config = GlobalConfig()
        route = Route(
            path_prefix="/api/v1",
            methods=["GET", "POST"],
            traffic_split=TrafficSplitConfig(
                enabled=True,
                targets=[
                    SplitTarget(
                        name="stable",
                        weight=90,
                        upstream=UpstreamTarget(host="api-v1-stable", port=8080),
                    ),
                    SplitTarget(
                        name="canary",
                        weight=10,
                        upstream=UpstreamTarget(host="api-v1-canary", port=8080),
                    ),
                ],
            ),
        )
        service = Service(
            name="canary_deployment_api",
            type="rest",
            protocol="http",
            upstream=Upstream(host="placeholder", port=8080),
            routes=[route],
        )
        return Config(
            version="1.0", provider="haproxy", global_config=global_config, services=[service]
        )

    def test_haproxy_weighted_servers(self):
        """Test HAProxy generates weighted servers correctly"""
        config = self._create_test_config()
        provider = HAProxyProvider()
        output = provider.generate(config)

        # Check weighted server entries
        assert "server server_stable api-v1-stable:8080" in output
        assert "server server_canary api-v1-canary:8080" in output

        # Check weight conversion (GAL 90 → HAProxy 230 = 90 × 2.56)
        assert "weight 230" in output  # 90 × 2.56 ≈ 230
        assert "weight 25" in output  # 10 × 2.56 ≈ 25

        # Check backend configuration
        assert "backend backend_canary_deployment_api" in output
        assert "balance roundrobin" in output

    def test_haproxy_health_checks(self):
        """Test HAProxy includes health checks"""
        config = self._create_test_config()
        provider = HAProxyProvider()
        output = provider.generate(config)

        # Check health check configuration
        assert "check inter 10s fall 3 rise 2" in output


class TestAzureAPIMTrafficSplit:
    """Test Azure API Management traffic splitting implementation"""

    def _create_test_config(self):
        """Helper to create test configuration"""
        global_config = GlobalConfig()
        route = Route(
            path_prefix="/api/v1",
            methods=["GET", "POST"],
            traffic_split=TrafficSplitConfig(
                enabled=True,
                targets=[
                    SplitTarget(
                        name="stable",
                        weight=90,
                        upstream=UpstreamTarget(host="api-v1-stable", port=8080),
                    ),
                    SplitTarget(
                        name="canary",
                        weight=10,
                        upstream=UpstreamTarget(host="api-v1-canary", port=8080),
                    ),
                ],
            ),
        )
        service = Service(
            name="canary_deployment_api",
            type="rest",
            protocol="http",
            upstream=Upstream(host="placeholder", port=8080),
            routes=[route],
        )
        return Config(
            version="1.0", provider="azure_apim", global_config=global_config, services=[service]
        )

    def test_azure_apim_backend_pool(self):
        """Test Azure APIM generates load-balanced backend pool"""
        config = self._create_test_config()
        provider = AzureAPIMProvider()
        output = provider.generate(config)

        import json

        arm_template = json.loads(output)

        # Find backend pool resource
        backend_pools = [
            r
            for r in arm_template["resources"]
            if r["type"] == "Microsoft.ApiManagement/service/backends"
            and "pool" in r.get("properties", {})
        ]

        assert len(backend_pools) > 0, "No backend pools found"

        pool = backend_pools[0]
        pool_services = pool["properties"]["pool"]["services"]

        # Check weights
        assert len(pool_services) == 2
        weights = [s["weight"] for s in pool_services]
        assert 90 in weights
        assert 10 in weights

    def test_azure_apim_individual_backends(self):
        """Test Azure APIM generates individual backends for each target"""
        config = self._create_test_config()
        provider = AzureAPIMProvider()
        output = provider.generate(config)

        import json

        arm_template = json.loads(output)

        # Find individual backend resources
        individual_backends = [
            r
            for r in arm_template["resources"]
            if r["type"] == "Microsoft.ApiManagement/service/backends"
            and "pool" not in r.get("properties", {})
        ]

        # Should have 2 individual backends (stable + canary)
        assert len(individual_backends) >= 2

        # Check backend names contain target names
        backend_names = [r["name"] for r in individual_backends]
        assert any("stable" in str(name) for name in backend_names)
        assert any("canary" in str(name) for name in backend_names)

    def test_azure_apim_policy_xml(self):
        """Test Azure APIM policy XML uses backend pool"""
        config = self._create_test_config()
        provider = AzureAPIMProvider()
        output = provider.generate(config)

        import json

        arm_template = json.loads(output)

        # Find policy resources
        policies = [
            r
            for r in arm_template["resources"]
            if r["type"] == "Microsoft.ApiManagement/service/apis/operations/policies"
        ]

        assert len(policies) > 0, "No policies found"

        # Check policy XML references backend pool
        policy_xml = policies[0]["properties"]["value"]
        assert "set-backend-service" in policy_xml
        assert "backend-pool" in policy_xml


class TestAWSAPIGatewayTrafficSplit:
    """Test AWS API Gateway traffic splitting implementation"""

    def _create_test_config(self):
        """Helper to create test configuration"""
        global_config = GlobalConfig()
        route = Route(
            path_prefix="/api/v1",
            methods=["GET", "POST"],
            traffic_split=TrafficSplitConfig(
                enabled=True,
                targets=[
                    SplitTarget(
                        name="stable",
                        weight=90,
                        upstream=UpstreamTarget(host="api-v1-stable", port=8080),
                    ),
                    SplitTarget(
                        name="canary",
                        weight=10,
                        upstream=UpstreamTarget(host="api-v1-canary", port=8080),
                    ),
                ],
            ),
        )
        service = Service(
            name="canary_deployment_api",
            type="rest",
            protocol="http",
            upstream=Upstream(host="placeholder", port=8080),
            routes=[route],
        )
        return Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=global_config,
            services=[service],
        )

    def test_aws_vtl_template(self):
        """Test AWS API Gateway generates VTL request templates"""
        config = self._create_test_config()
        provider = AWSAPIGatewayProvider()
        output = provider.generate(config)

        import json

        spec = json.loads(output)

        # Find integration with VTL template
        operation = spec["paths"]["/api/v1"]["get"]
        integration = operation["x-amazon-apigateway-integration"]

        # Check VTL template exists
        assert "requestTemplates" in integration
        assert "application/json" in integration["requestTemplates"]

        vtl_template = integration["requestTemplates"]["application/json"]

        # Check VTL logic
        assert "#set($random = $context.requestTimeEpoch % 100)" in vtl_template
        assert "#if($random < 90)" in vtl_template
        assert "stageVariables" in vtl_template

    def test_aws_stage_variables(self):
        """Test AWS API Gateway uses stage variables for backend URLs"""
        config = self._create_test_config()
        provider = AWSAPIGatewayProvider()
        output = provider.generate(config)

        import json

        spec = json.loads(output)

        # Find integration
        operation = spec["paths"]["/api/v1"]["get"]
        integration = operation["x-amazon-apigateway-integration"]

        # Check stage variable references
        assert "${stageVariables.backend_url}" in integration["uri"]

        vtl_template = integration["requestTemplates"]["application/json"]
        assert "canary_deployment_api_stable_url" in vtl_template
        assert "canary_deployment_api_canary_url" in vtl_template

    def test_aws_cumulative_weight_logic(self):
        """Test AWS VTL uses cumulative weight logic"""
        # Create 3-target config (70/20/10)
        global_config = GlobalConfig()
        route = Route(
            path_prefix="/api/multi",
            methods=["GET"],
            traffic_split=TrafficSplitConfig(
                enabled=True,
                targets=[
                    SplitTarget(
                        name="stable",
                        weight=70,
                        upstream=UpstreamTarget(host="api-stable", port=8080),
                    ),
                    SplitTarget(
                        name="beta",
                        weight=20,
                        upstream=UpstreamTarget(host="api-beta", port=8080),
                    ),
                    SplitTarget(
                        name="canary",
                        weight=10,
                        upstream=UpstreamTarget(host="api-canary", port=8080),
                    ),
                ],
            ),
        )
        service = Service(
            name="multi_rule_api",
            type="rest",
            protocol="http",
            upstream=Upstream(host="placeholder", port=8080),
            routes=[route],
        )
        config = Config(
            version="1.0",
            provider="aws_apigateway",
            global_config=global_config,
            services=[service],
        )

        provider = AWSAPIGatewayProvider()
        output = provider.generate(config)

        import json

        spec = json.loads(output)

        operation = spec["paths"]["/api/multi"]["get"]
        integration = operation["x-amazon-apigateway-integration"]
        vtl_template = integration["requestTemplates"]["application/json"]

        # Check cumulative weight conditions
        assert "#if($random < 70)" in vtl_template
        assert "#elseif($random < 90)" in vtl_template  # 70 + 20
        assert "#elseif($random < 100)" in vtl_template  # 70 + 20 + 10
