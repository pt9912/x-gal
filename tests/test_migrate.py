"""
Tests for Migration Assistant (gal migrate command)
"""

import os
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from gal-cli.py (hyphen in filename)
import importlib.util

spec = importlib.util.spec_from_file_location(
    "gal_cli", Path(__file__).parent.parent / "gal-cli.py"
)
gal_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gal_cli)
cli = gal_cli.cli


class TestMigrateBasic:
    """Test basic migration functionality"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    @pytest.fixture
    def kong_config(self, tmp_path):
        """Create Kong config file"""
        config = tmp_path / "kong.yaml"
        config.write_text(
            """
_format_version: "3.0"
services:
  - name: api_service
    url: http://api.internal:8080
    routes:
      - name: api_route
        paths:
          - /api/v1
    plugins:
      - name: rate-limiting
        config:
          minute: 100
"""
        )
        return str(config)

    @pytest.fixture
    def envoy_config(self, tmp_path):
        """Create Envoy config file"""
        config = tmp_path / "envoy.yaml"
        config.write_text(
            """
static_resources:
  listeners:
    - name: main_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 10000
  clusters:
    - name: service_cluster
      connect_timeout: 1s
      type: STRICT_DNS
      load_assignment:
        cluster_name: service_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: backend
                      port_value: 8080
"""
        )
        return str(config)

    @pytest.fixture
    def traefik_config(self, tmp_path):
        """Create Traefik config file"""
        config = tmp_path / "traefik.yaml"
        config.write_text(
            """
http:
  routers:
    api_router:
      rule: "PathPrefix(`/api`)"
      service: api_service
  services:
    api_service:
      loadBalancer:
        servers:
          - url: http://backend:8080
"""
        )
        return str(config)

    def test_migrate_kong_to_envoy(self, runner, kong_config, tmp_path):
        """Test migrating from Kong to Envoy"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert result.exit_code == 0
        assert "Migration complete!" in result.output
        assert (output_dir / "gal-config.yaml").exists()
        assert (output_dir / "envoy.yaml").exists()
        assert (output_dir / "migration-report.md").exists()

    def test_migrate_envoy_to_kong(self, runner, envoy_config, tmp_path):
        """Test migrating from Envoy to Kong"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "envoy",
                "-i",
                envoy_config,
                "-t",
                "kong",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert result.exit_code == 0
        assert "Migration complete!" in result.output
        assert (output_dir / "kong.yaml").exists()

    def test_migrate_traefik_to_nginx(self, runner, traefik_config, tmp_path):
        """Test migrating from Traefik to Nginx"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "traefik",
                "-i",
                traefik_config,
                "-t",
                "nginx",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert result.exit_code == 0
        assert "Migration complete!" in result.output
        assert (output_dir / "nginx.conf").exists()

    def test_migrate_creates_output_directory(self, runner, kong_config, tmp_path):
        """Test that migration creates output directory if it doesn't exist"""
        output_dir = tmp_path / "non-existent" / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert result.exit_code == 0
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_migrate_default_output_directory(self, runner, kong_config):
        """Test migration with default output directory"""
        # Run from temp directory
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [
                    "migrate",
                    "-s",
                    "kong",
                    "-i",
                    kong_config,
                    "-t",
                    "envoy",
                    "-o",
                    "./migration",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert Path("migration").exists()

    def test_migrate_shows_progress_steps(self, runner, kong_config, tmp_path):
        """Test that migration shows all 5 progress steps"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert "[1/5]" in result.output
        assert "[2/5]" in result.output
        assert "[3/5]" in result.output
        assert "[4/5]" in result.output
        assert "[5/5]" in result.output

    def test_migrate_displays_summary(self, runner, kong_config, tmp_path):
        """Test that migration displays summary information"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert "Files created:" in result.output
        assert "gal-config.yaml" in result.output
        assert "envoy.yaml" in result.output
        assert "migration-report.md" in result.output
        assert "Compatibility:" in result.output


class TestMigrateFileGeneration:
    """Test file generation during migration"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def kong_config(self, tmp_path):
        """Create Kong config with multiple services"""
        config = tmp_path / "kong.yaml"
        config.write_text(
            """
_format_version: "3.0"
services:
  - name: api_service
    url: http://api.internal:8080
    routes:
      - name: api_route
        paths:
          - /api/v1
  - name: web_service
    url: http://web.internal:8080
    routes:
      - name: web_route
        paths:
          - /web
"""
        )
        return str(config)

    def test_gal_config_format(self, runner, kong_config, tmp_path):
        """Test that gal-config.yaml is valid YAML"""
        import yaml

        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert result.exit_code == 0

        gal_config_path = output_dir / "gal-config.yaml"
        with open(gal_config_path) as f:
            gal_config = yaml.safe_load(f)

        assert "version" in gal_config
        assert "provider" in gal_config
        assert "services" in gal_config
        assert len(gal_config["services"]) >= 2

    def test_target_config_format(self, runner, kong_config, tmp_path):
        """Test that target config is valid YAML"""
        import yaml

        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert result.exit_code == 0

        envoy_config_path = output_dir / "envoy.yaml"
        with open(envoy_config_path) as f:
            envoy_config = yaml.safe_load(f)

        assert "static_resources" in envoy_config

    def test_migration_report_format(self, runner, kong_config, tmp_path):
        """Test that migration report is valid Markdown"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert result.exit_code == 0

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        # Check Markdown structure
        assert content.startswith("# Migration Report:")
        assert "## Summary" in content
        assert "## Features Status" in content
        assert "## Services" in content
        assert "## Testing Checklist" in content
        assert "## Next Steps" in content

    def test_migration_report_contains_compatibility(self, runner, kong_config, tmp_path):
        """Test that migration report contains compatibility information"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        assert "Compatibility:" in content
        assert "%" in content  # Percentage score

    def test_migration_report_contains_services(self, runner, kong_config, tmp_path):
        """Test that migration report lists all services"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        assert "api_service" in content
        assert "web_service" in content

    def test_migration_report_contains_timestamp(self, runner, kong_config, tmp_path):
        """Test that migration report contains timestamp"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        assert "**Date:**" in content

    def test_migration_report_checklist_format(self, runner, kong_config, tmp_path):
        """Test that migration report contains valid checklist"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        # Check for Markdown checklist items
        assert "- [ ]" in content


class TestMigrateCompatibility:
    """Test compatibility validation during migration"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def kong_config_with_features(self, tmp_path):
        """Create Kong config with various features"""
        config = tmp_path / "kong-features.yaml"
        config.write_text(
            """
_format_version: "3.0"
services:
  - name: api_service
    url: http://api.internal:8080
    routes:
      - name: api_route
        paths:
          - /api/v1
    plugins:
      - name: rate-limiting
        config:
          minute: 100
      - name: basic-auth
      - name: cors
"""
        )
        return str(config)

    def test_migrate_shows_compatibility_score(self, runner, kong_config_with_features, tmp_path):
        """Test that migration shows compatibility score"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config_with_features,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert "Compatibility:" in result.output
        assert "%" in result.output

    def test_migrate_validates_compatibility(self, runner, kong_config_with_features, tmp_path):
        """Test that migration validates compatibility"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config_with_features,
                "-t",
                "traefik",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert result.exit_code == 0
        # Should complete even if not 100% compatible

    def test_migrate_includes_compatibility_in_report(
        self, runner, kong_config_with_features, tmp_path
    ):
        """Test that compatibility info is in migration report"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config_with_features,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        assert "Compatibility:" in content
        assert "## Features Status" in content

    def test_migrate_shows_warnings_for_partial_support(
        self, runner, kong_config_with_features, tmp_path
    ):
        """Test that migration shows warnings for partial support"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config_with_features,
                "-t",
                "nginx",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        # Check report contains warning section
        assert "## Features Status" in content or "Warnings:" in content


class TestMigrateEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_migrate_invalid_source_provider(self, runner, tmp_path):
        """Test migration with invalid source provider"""
        config = tmp_path / "config.yaml"
        config.write_text("test: config")

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "invalid_provider",
                "-i",
                str(config),
                "-t",
                "envoy",
                "-o",
                "./migration",
                "--yes",
            ],
        )

        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()

    def test_migrate_invalid_target_provider(self, runner, tmp_path):
        """Test migration with invalid target provider"""
        config = tmp_path / "kong.yaml"
        config.write_text("_format_version: '3.0'\nservices: []")

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                str(config),
                "-t",
                "invalid_provider",
                "-o",
                "./migration",
                "--yes",
            ],
        )

        assert result.exit_code != 0

    def test_migrate_nonexistent_config_file(self, runner):
        """Test migration with non-existent config file"""
        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                "/non/existent/file.yaml",
                "-t",
                "envoy",
                "-o",
                "./migration",
                "--yes",
            ],
        )

        assert result.exit_code != 0

    def test_migrate_empty_config_file(self, runner, tmp_path):
        """Test migration with empty config file"""
        config = tmp_path / "empty.yaml"
        config.write_text("")

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                str(config),
                "-t",
                "envoy",
                "-o",
                "./migration",
                "--yes",
            ],
        )

        # Should handle gracefully
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_migrate_same_source_and_target(self, runner, tmp_path):
        """Test migration with same source and target provider"""
        config = tmp_path / "kong.yaml"
        config.write_text(
            """
_format_version: "3.0"
services:
  - name: test_service
    url: http://test:8080
"""
        )
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                str(config),
                "-t",
                "kong",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        # Should work - can be used for validation/reformatting
        assert result.exit_code == 0


class TestMigrateAllProviders:
    """Test migration between all provider combinations"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def minimal_kong_config(self, tmp_path):
        config = tmp_path / "kong.yaml"
        config.write_text(
            """
_format_version: "3.0"
services:
  - name: test
    url: http://backend:8080
"""
        )
        return str(config)

    def test_migrate_kong_to_all_providers(self, runner, minimal_kong_config, tmp_path):
        """Test migrating Kong config to all providers"""
        target_providers = ["envoy", "apisix", "traefik", "nginx", "haproxy"]

        for target in target_providers:
            output_dir = tmp_path / f"migration-{target}"

            result = runner.invoke(
                cli,
                [
                    "migrate",
                    "-s",
                    "kong",
                    "-i",
                    minimal_kong_config,
                    "-t",
                    target,
                    "-o",
                    str(output_dir),
                    "--yes",
                ],
            )

            assert result.exit_code == 0, f"Migration to {target} failed"
            assert (output_dir / "gal-config.yaml").exists()
            assert (output_dir / "migration-report.md").exists()


class TestMigrateYesFlag:
    """Test --yes flag behavior"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def kong_config(self, tmp_path):
        config = tmp_path / "kong.yaml"
        config.write_text(
            """
_format_version: "3.0"
services:
  - name: test
    url: http://backend:8080
"""
        )
        return str(config)

    def test_migrate_with_yes_flag(self, runner, kong_config, tmp_path):
        """Test that --yes flag skips confirmation"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        assert result.exit_code == 0
        assert "Proceed with migration?" not in result.output

    def test_migrate_with_y_short_flag(self, runner, kong_config, tmp_path):
        """Test that -y short flag works"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "-y",
            ],
        )

        assert result.exit_code == 0
        assert "Proceed with migration?" not in result.output


class TestMigrateReportContent:
    """Test migration report content in detail"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def complex_kong_config(self, tmp_path):
        """Create complex Kong config with multiple features"""
        config = tmp_path / "kong-complex.yaml"
        config.write_text(
            """
_format_version: "3.0"
services:
  - name: api_service
    url: http://api.internal:8080
    routes:
      - name: api_route
        paths:
          - /api/v1
        methods:
          - GET
          - POST
    plugins:
      - name: rate-limiting
        config:
          minute: 100
      - name: cors
  - name: web_service
    url: http://web.internal:9090
    routes:
      - name: web_route
        paths:
          - /web
"""
        )
        return str(config)

    def test_report_contains_all_sections(self, runner, complex_kong_config, tmp_path):
        """Test that report contains all expected sections"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                complex_kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        sections = [
            "# Migration Report:",
            "## Summary",
            "## Features Status",
            "## Services",
            "## Testing Checklist",
            "## Next Steps",
        ]

        for section in sections:
            assert section in content, f"Missing section: {section}"

    def test_report_summary_has_all_metrics(self, runner, complex_kong_config, tmp_path):
        """Test that summary section has all metrics"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                complex_kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        metrics = ["Compatibility:", "Services Migrated:", "Routes Migrated:"]

        for metric in metrics:
            assert metric in content, f"Missing metric: {metric}"

    def test_report_lists_service_details(self, runner, complex_kong_config, tmp_path):
        """Test that report lists service details"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                complex_kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        # Should contain service names
        assert "api_service" in content
        assert "web_service" in content

    def test_report_has_testing_checklist(self, runner, complex_kong_config, tmp_path):
        """Test that report has testing checklist"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                complex_kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        # Should have checkbox items
        assert "- [ ]" in content
        assert "Test" in content or "test" in content

    def test_report_has_next_steps(self, runner, complex_kong_config, tmp_path):
        """Test that report has next steps"""
        output_dir = tmp_path / "migration"

        result = runner.invoke(
            cli,
            [
                "migrate",
                "-s",
                "kong",
                "-i",
                complex_kong_config,
                "-t",
                "envoy",
                "-o",
                str(output_dir),
                "--yes",
            ],
        )

        report_path = output_dir / "migration-report.md"
        content = report_path.read_text()

        # Should have numbered steps
        assert "1." in content or "2." in content or "3." in content
