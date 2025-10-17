"""
Tests for CLI commands
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner

# Import CLI directly
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from gal-cli.py (hyphen in filename)
import importlib.util
spec = importlib.util.spec_from_file_location("gal_cli", Path(__file__).parent.parent / "gal-cli.py")
gal_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gal_cli)
cli = gal_cli.cli


class TestCLIGenerate:
    """Test generate command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    @pytest.fixture
    def config_file(self, tmp_path):
        """Create temporary config file"""
        config = tmp_path / "test-config.yaml"
        config.write_text("""
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901
  timeout: 30

services:
  - name: test_service
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api
        methods: [GET, POST]
""")
        return str(config)

    def test_generate_to_stdout(self, runner, config_file):
        """Test generating config to stdout"""
        result = runner.invoke(cli, ['generate', '-c', config_file])

        assert result.exit_code == 0
        assert "Generating configuration for: envoy" in result.output
        assert "Services: 1" in result.output
        assert "static_resources:" in result.output

    def test_generate_to_file(self, runner, config_file, tmp_path):
        """Test generating config to file"""
        output_file = tmp_path / "output" / "envoy.yaml"

        result = runner.invoke(cli, [
            'generate',
            '-c', config_file,
            '-o', str(output_file)
        ])

        assert result.exit_code == 0
        assert "Configuration written to:" in result.output
        assert output_file.exists()

        # Verify content
        content = output_file.read_text()
        assert "static_resources:" in content
        assert "test_service" in content

    def test_generate_override_provider(self, runner, config_file, tmp_path):
        """Test overriding provider"""
        output_file = tmp_path / "kong.yaml"

        result = runner.invoke(cli, [
            'generate',
            '-c', config_file,
            '-p', 'kong',
            '-o', str(output_file)
        ])

        assert result.exit_code == 0
        assert "Generating configuration for: kong" in result.output

        # Verify Kong-specific content
        content = output_file.read_text()
        assert "_format_version:" in content

    def test_generate_missing_config(self, runner):
        """Test error with missing config file"""
        result = runner.invoke(cli, ['generate', '-c', 'nonexistent.yaml'])

        assert result.exit_code != 0
        assert "Error:" in result.output

    def test_generate_creates_output_directory(self, runner, config_file, tmp_path):
        """Test that output directory is created"""
        output_file = tmp_path / "deep" / "nested" / "dir" / "config.yaml"

        result = runner.invoke(cli, [
            'generate',
            '-c', config_file,
            '-o', str(output_file)
        ])

        assert result.exit_code == 0
        assert output_file.exists()


class TestCLIValidate:
    """Test validate command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    @pytest.fixture
    def valid_config_file(self, tmp_path):
        """Create valid config file"""
        config = tmp_path / "valid-config.yaml"
        config.write_text("""
version: "1.0"
provider: kong

global:
  host: 0.0.0.0
  port: 8000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 3000
    routes:
      - path_prefix: /api/v1
""")
        return str(config)

    @pytest.fixture
    def invalid_config_file(self, tmp_path):
        """Create invalid config file"""
        config = tmp_path / "invalid-config.yaml"
        config.write_text("""
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 0

services: []
""")
        return str(config)

    def test_validate_success(self, runner, valid_config_file):
        """Test validating valid configuration"""
        result = runner.invoke(cli, ['validate', '-c', valid_config_file])

        assert result.exit_code == 0
        assert "Configuration is valid" in result.output
        assert "Provider: kong" in result.output
        assert "Services: 1" in result.output

    def test_validate_failure(self, runner, invalid_config_file):
        """Test validating invalid configuration (port 0)"""
        result = runner.invoke(cli, ['validate', '-c', invalid_config_file])

        # Note: Port 0 validation only fails for Envoy provider
        # This test verifies Envoy-specific validation
        assert result.exit_code != 0
        assert "Configuration is invalid" in result.output or "Port must be specified" in result.output

    def test_validate_missing_file(self, runner):
        """Test error with missing config file"""
        result = runner.invoke(cli, ['validate', '-c', 'missing.yaml'])

        assert result.exit_code != 0
        assert "Configuration is invalid" in result.output


class TestCLIGenerateAll:
    """Test generate-all command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    @pytest.fixture
    def config_file(self, tmp_path):
        """Create config file"""
        config = tmp_path / "config.yaml"
        config.write_text("""
version: "1.0"
provider: envoy

services:
  - name: service1
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api
""")
        return str(config)

    def test_generate_all_default_dir(self, runner, config_file, tmp_path):
        """Test generating all configs to default directory"""
        # Change to tmp directory
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ['generate-all', '-c', config_file])

            assert result.exit_code == 0
            assert "Generating configurations for all providers" in result.output
            assert "envoy" in result.output
            assert "kong" in result.output
            assert "apisix" in result.output
            assert "traefik" in result.output

            # Verify files exist
            assert Path("generated/envoy.yaml").exists()
            assert Path("generated/kong.yaml").exists()
            assert Path("generated/apisix.json").exists()
            assert Path("generated/traefik.yaml").exists()

    def test_generate_all_custom_dir(self, runner, config_file, tmp_path):
        """Test generating all configs to custom directory"""
        output_dir = tmp_path / "custom-output"

        result = runner.invoke(cli, [
            'generate-all',
            '-c', config_file,
            '-o', str(output_dir)
        ])

        assert result.exit_code == 0
        assert "All configurations generated successfully" in result.output

        # Verify files
        assert (output_dir / "envoy.yaml").exists()
        assert (output_dir / "kong.yaml").exists()
        assert (output_dir / "apisix.json").exists()
        assert (output_dir / "traefik.yaml").exists()

    def test_generate_all_verifies_content(self, runner, config_file, tmp_path):
        """Test that generated configs have correct format"""
        output_dir = tmp_path / "output"

        result = runner.invoke(cli, [
            'generate-all',
            '-c', config_file,
            '-o', str(output_dir)
        ])

        assert result.exit_code == 0

        # Verify Envoy YAML
        envoy_content = (output_dir / "envoy.yaml").read_text()
        assert "static_resources:" in envoy_content

        # Verify Kong YAML
        kong_content = (output_dir / "kong.yaml").read_text()
        assert "_format_version:" in kong_content

        # Verify APISIX JSON
        apisix_content = (output_dir / "apisix.json").read_text()
        assert '"routes"' in apisix_content
        assert '"services"' in apisix_content

        # Verify Traefik YAML
        traefik_content = (output_dir / "traefik.yaml").read_text()
        assert "http:" in traefik_content


class TestCLIInfo:
    """Test info command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    @pytest.fixture
    def detailed_config_file(self, tmp_path):
        """Create config with transformations"""
        config = tmp_path / "detailed-config.yaml"
        config.write_text("""
version: "1.0"
provider: apisix

global:
  host: 0.0.0.0
  port: 9080
  admin_port: 9180
  timeout: 60

services:
  - name: user_service
    type: grpc
    protocol: http2
    upstream:
      host: user-grpc
      port: 50051
    routes:
      - path_prefix: /user.UserService
    transformation:
      enabled: true
      defaults:
        status: active
      computed_fields:
        - field: user_id
          generator: uuid
          prefix: usr_
      validation:
        required_fields:
          - email
          - username

plugins:
  - name: auth
    enabled: true
    config:
      key: secret
""")
        return str(config)

    def test_info_displays_configuration(self, runner, detailed_config_file):
        """Test that info displays all configuration details"""
        result = runner.invoke(cli, ['info', '-c', detailed_config_file])

        assert result.exit_code == 0
        assert "GAL Configuration Information" in result.output
        assert "Provider: apisix" in result.output
        assert "Version: 1.0" in result.output
        assert "Host: 0.0.0.0" in result.output
        assert "Port: 9080" in result.output
        assert "Admin Port: 9180" in result.output
        assert "Timeout: 60" in result.output

    def test_info_displays_services(self, runner, detailed_config_file):
        """Test that info displays service details"""
        result = runner.invoke(cli, ['info', '-c', detailed_config_file])

        assert result.exit_code == 0
        assert "user_service" in result.output
        assert "Type: grpc" in result.output
        assert "Upstream: user-grpc:50051" in result.output
        assert "Routes: 1" in result.output

    def test_info_displays_transformations(self, runner, detailed_config_file):
        """Test that info displays transformation details"""
        result = runner.invoke(cli, ['info', '-c', detailed_config_file])

        assert result.exit_code == 0
        assert "Transformations: ✓ Enabled" in result.output
        assert "Defaults: 1 fields" in result.output
        assert "Computed: 1 fields" in result.output
        assert "Required: email, username" in result.output

    def test_info_displays_plugins(self, runner, detailed_config_file):
        """Test that info displays plugin details"""
        result = runner.invoke(cli, ['info', '-c', detailed_config_file])

        assert result.exit_code == 0
        assert "Plugins (1):" in result.output
        assert "✓ auth" in result.output


class TestCLIListProviders:
    """Test list-providers command"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    def test_list_providers(self, runner):
        """Test listing all providers"""
        result = runner.invoke(cli, ['list-providers'])

        assert result.exit_code == 0
        assert "Available providers:" in result.output
        assert "envoy" in result.output
        assert "kong" in result.output
        assert "apisix" in result.output
        assert "traefik" in result.output

    def test_list_providers_descriptions(self, runner):
        """Test that provider descriptions are shown"""
        result = runner.invoke(cli, ['list-providers'])

        assert result.exit_code == 0
        assert "Envoy Proxy" in result.output
        assert "Kong API Gateway" in result.output
        assert "Apache APISIX" in result.output
        assert "Traefik" in result.output


class TestCLIHelp:
    """Test help commands"""

    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()

    def test_main_help(self, runner):
        """Test main help command"""
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert "Gateway Abstraction Layer (GAL) CLI" in result.output
        assert "generate" in result.output
        assert "validate" in result.output
        assert "generate-all" in result.output
        assert "info" in result.output
        assert "list-providers" in result.output

    def test_generate_help(self, runner):
        """Test generate command help"""
        result = runner.invoke(cli, ['generate', '--help'])

        assert result.exit_code == 0
        assert "Generate gateway configuration" in result.output
        assert "--config" in result.output
        assert "--provider" in result.output
        assert "--output" in result.output
