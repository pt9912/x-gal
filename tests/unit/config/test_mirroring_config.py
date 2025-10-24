"""Unit tests for Request Mirroring Configuration.

Tests the MirroringConfig and MirrorTarget dataclasses including:
- Config parsing from YAML
- Weight validation
- Target validation
- Fallback target validation
- Header manipulation
"""

import pytest

from gal.config import Config, MirroringConfig, MirrorTarget, UpstreamTarget


class TestMirrorTarget:
    """Test MirrorTarget dataclass."""

    def test_mirror_target_basic(self):
        """Test basic mirror target creation."""
        target = MirrorTarget(
            name="shadow-v2",
            upstream=UpstreamTarget(host="shadow-api", port=8080),
            sample_percentage=50.0,
        )

        assert target.name == "shadow-v2"
        assert target.upstream.host == "shadow-api"
        assert target.upstream.port == 8080
        assert target.sample_percentage == 50.0
        assert target.timeout == "5s"
        assert target.headers is None

    def test_mirror_target_with_headers(self):
        """Test mirror target with custom headers."""
        target = MirrorTarget(
            name="shadow-v3",
            upstream=UpstreamTarget(host="shadow-api-v3", port=9000),
            sample_percentage=100.0,
            headers={"X-Mirror": "true", "X-Version": "v3"},
        )

        assert target.headers == {"X-Mirror": "true", "X-Version": "v3"}

    def test_mirror_target_weight_validation(self):
        """Test that weight must be between 0 and 100."""
        # Valid weights
        MirrorTarget(
            name="test1",
            upstream=UpstreamTarget(host="test", port=8080),
            sample_percentage=0.0,
        )
        MirrorTarget(
            name="test2",
            upstream=UpstreamTarget(host="test", port=8080),
            sample_percentage=100.0,
        )

        # Invalid weights
        with pytest.raises(ValueError, match="sample_percentage must be between 0 and 100"):
            MirrorTarget(
                name="test3",
                upstream=UpstreamTarget(host="test", port=8080),
                sample_percentage=-1.0,
            )

        with pytest.raises(ValueError, match="sample_percentage must be between 0 and 100"):
            MirrorTarget(
                name="test4",
                upstream=UpstreamTarget(host="test", port=8080),
                sample_percentage=101.0,
            )


class TestMirroringConfig:
    """Test MirroringConfig dataclass."""

    def test_mirroring_config_basic(self):
        """Test basic mirroring configuration."""
        config = MirroringConfig(
            enabled=True,
            targets=[
                MirrorTarget(
                    name="shadow-v2",
                    upstream=UpstreamTarget(host="shadow-api", port=8080),
                    sample_percentage=50.0,
                )
            ],
        )

        assert config.enabled is True
        assert len(config.targets) == 1
        assert config.targets[0].name == "shadow-v2"
        assert config.mirror_request_body is True
        assert config.mirror_headers is True

    def test_mirroring_config_multiple_targets(self):
        """Test mirroring with multiple targets."""
        config = MirroringConfig(
            enabled=True,
            targets=[
                MirrorTarget(
                    name="shadow-v2",
                    upstream=UpstreamTarget(host="shadow-api-v2", port=8080),
                    sample_percentage=50.0,
                ),
                MirrorTarget(
                    name="shadow-v3",
                    upstream=UpstreamTarget(host="shadow-api-v3", port=8080),
                    sample_percentage=25.0,
                ),
            ],
        )

        assert len(config.targets) == 2
        assert config.targets[0].name == "shadow-v2"
        assert config.targets[1].name == "shadow-v3"

    def test_mirroring_config_validation_no_targets(self):
        """Test that at least one target is required when enabled."""
        with pytest.raises(ValueError, match="At least one mirror target is required"):
            MirroringConfig(enabled=True, targets=[])

    def test_mirroring_config_validation_unique_names(self):
        """Test that target names must be unique."""
        with pytest.raises(ValueError, match="Mirror target names must be unique"):
            MirroringConfig(
                enabled=True,
                targets=[
                    MirrorTarget(
                        name="shadow-v2",
                        upstream=UpstreamTarget(host="shadow-api-1", port=8080),
                        sample_percentage=50.0,
                    ),
                    MirrorTarget(
                        name="shadow-v2",  # Duplicate name
                        upstream=UpstreamTarget(host="shadow-api-2", port=8080),
                        sample_percentage=50.0,
                    ),
                ],
            )


class TestMirroringConfigYAML:
    """Test MirroringConfig YAML parsing."""

    def test_parse_simple_mirroring_yaml(self, tmp_path):
        """Test parsing simple mirroring configuration from YAML."""
        config_yaml = """
version: "1.0"
provider: gal

global:
  host: 0.0.0.0
  port: 8000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-v1
          port: 8080
    routes:
      - path_prefix: /api/v1
        methods: [GET, POST]
        mirroring:
          enabled: true
          mirror_request_body: true
          mirror_headers: true
          targets:
            - name: shadow-v2
              upstream:
                host: shadow-api-v2
                port: 8080
              sample_percentage: 100.0
              timeout: "5s"
              headers:
                X-Mirror: "true"
                X-Shadow-Version: "v2"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        config = Config.from_yaml(str(config_file))

        assert len(config.services) == 1
        service = config.services[0]
        assert len(service.routes) == 1
        route = service.routes[0]

        assert route.mirroring is not None
        assert route.mirroring.enabled is True
        assert route.mirroring.mirror_request_body is True
        assert route.mirroring.mirror_headers is True

        assert len(route.mirroring.targets) == 1
        target = route.mirroring.targets[0]
        assert target.name == "shadow-v2"
        assert target.upstream.host == "shadow-api-v2"
        assert target.upstream.port == 8080
        assert target.sample_percentage == 100.0
        assert target.timeout == "5s"
        assert target.headers == {"X-Mirror": "true", "X-Shadow-Version": "v2"}

    def test_parse_multiple_targets_yaml(self, tmp_path):
        """Test parsing mirroring with multiple targets."""
        config_yaml = """
version: "1.0"
provider: gal

global:
  host: 0.0.0.0
  port: 8000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-v1
          port: 8080
    routes:
      - path_prefix: /api/v1
        methods: [GET]
        mirroring:
          enabled: true
          targets:
            - name: shadow-v2
              upstream:
                host: shadow-api-v2
                port: 8080
              sample_percentage: 50.0
            - name: shadow-v3
              upstream:
                host: shadow-api-v3
                port: 9000
              sample_percentage: 25.0
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        config = Config.from_yaml(str(config_file))
        route = config.services[0].routes[0]

        assert len(route.mirroring.targets) == 2
        assert route.mirroring.targets[0].name == "shadow-v2"
        assert route.mirroring.targets[0].sample_percentage == 50.0
        assert route.mirroring.targets[1].name == "shadow-v3"
        assert route.mirroring.targets[1].sample_percentage == 25.0

    def test_parse_disabled_mirroring(self, tmp_path):
        """Test parsing disabled mirroring configuration."""
        config_yaml = """
version: "1.0"
provider: gal

global:
  host: 0.0.0.0
  port: 8000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-v1
          port: 8080
    routes:
      - path_prefix: /api/v1
        methods: [GET]
        mirroring:
          enabled: false
          targets: []
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        config = Config.from_yaml(str(config_file))
        route = config.services[0].routes[0]

        # Disabled mirroring should still parse, but enabled=false
        assert route.mirroring.enabled is False


class TestKongGlobalConfig:
    """Test KongGlobalConfig parsing."""

    def test_parse_kong_enterprise_config(self, tmp_path):
        """Test parsing Kong Enterprise global config."""
        config_yaml = """
version: "1.0"
provider: gal

global:
  host: 0.0.0.0
  port: 8000
  kong:
    version: Enterprise
    admin_api_url: http://kong-admin:8001
    workspace: production
    control_plane_url: http://kong-cp:8005

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-v1
          port: 8080
    routes:
      - path_prefix: /api/v1
        methods: [GET]
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        config = Config.from_yaml(str(config_file))

        assert config.global_config is not None
        assert config.global_config.kong is not None
        assert config.global_config.kong.version == "Enterprise"
        assert config.global_config.kong.admin_api_url == "http://kong-admin:8001"
        assert config.global_config.kong.workspace == "production"
        assert config.global_config.kong.control_plane_url == "http://kong-cp:8005"

    def test_parse_kong_opensource_default(self, tmp_path):
        """Test that Kong defaults to OpenSource if not specified."""
        config_yaml = """
version: "1.0"
provider: gal

global:
  host: 0.0.0.0
  port: 8000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-v1
          port: 8080
    routes:
      - path_prefix: /api/v1
        methods: [GET]
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        config = Config.from_yaml(str(config_file))

        # No kong config = defaults to None (OpenSource is assumed in provider)
        assert config.global_config.kong is None


class TestAWSGCPMirroringWorkarounds:
    """Test AWS and GCP mirroring workaround configs."""

    def test_parse_aws_lambda_edge_workaround(self, tmp_path):
        """Test parsing AWS Lambda@Edge mirroring workaround."""
        config_yaml = """
version: "1.0"
provider: gal

global:
  host: 0.0.0.0
  port: 8000
  aws_apigateway:
    api_name: TestAPI
    mirroring_workaround: lambda_edge
    mirroring_lambda_edge_arn: arn:aws:lambda:us-east-1:123456789012:function:mirror

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-v1
          port: 8080
    routes:
      - path_prefix: /api/v1
        methods: [GET]
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        config = Config.from_yaml(str(config_file))

        assert config.global_config.aws_apigateway is not None
        assert config.global_config.aws_apigateway.mirroring_workaround == "lambda_edge"
        assert (
            config.global_config.aws_apigateway.mirroring_lambda_edge_arn
            == "arn:aws:lambda:us-east-1:123456789012:function:mirror"
        )

    def test_parse_gcp_cloud_functions_workaround(self, tmp_path):
        """Test parsing GCP Cloud Functions mirroring workaround."""
        config_yaml = """
version: "1.0"
provider: gal

global:
  host: 0.0.0.0
  port: 8000
  gcp_apigateway:
    api_id: test-api
    project_id: my-project
    mirroring_workaround: cloud_functions
    mirroring_cloud_function_url: https://us-central1-project.cloudfunctions.net/mirror

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-v1
          port: 8080
    routes:
      - path_prefix: /api/v1
        methods: [GET]
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_yaml)

        config = Config.from_yaml(str(config_file))

        assert config.global_config.gcp_apigateway is not None
        assert config.global_config.gcp_apigateway.mirroring_workaround == "cloud_functions"
        assert (
            config.global_config.gcp_apigateway.mirroring_cloud_function_url
            == "https://us-central1-project.cloudfunctions.net/mirror"
        )
