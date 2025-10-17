"""
Tests for GAL Manager
"""

import pytest
import tempfile
from pathlib import Path
from gal.manager import Manager
from gal.provider import Provider
from gal.config import Config, Service, Upstream, Route, GlobalConfig


class MockProvider(Provider):
    """Mock provider for testing"""

    def __init__(self, provider_name="mock", should_validate=True):
        self._name = provider_name
        self._should_validate = should_validate
        self.generated_config = None
        self.deployed_config = None

    def name(self) -> str:
        return self._name

    def validate(self, config: Config) -> bool:
        return self._should_validate

    def generate(self, config: Config) -> str:
        self.generated_config = config
        return f"# Mock {self._name} configuration for {config.version}"

    def deploy(self, config: Config) -> bool:
        self.deployed_config = config
        return True


class TestManager:
    """Test Manager class"""

    def test_manager_creation(self):
        """Test creating a manager"""
        manager = Manager()
        assert manager is not None
        assert manager.providers == {}

    def test_register_provider(self):
        """Test registering a provider"""
        manager = Manager()
        provider = MockProvider("test")

        manager.register_provider(provider)

        assert "test" in manager.providers
        assert manager.providers["test"] == provider

    def test_register_multiple_providers(self):
        """Test registering multiple providers"""
        manager = Manager()
        provider1 = MockProvider("envoy")
        provider2 = MockProvider("kong")
        provider3 = MockProvider("apisix")

        manager.register_provider(provider1)
        manager.register_provider(provider2)
        manager.register_provider(provider3)

        assert len(manager.providers) == 3
        assert "envoy" in manager.providers
        assert "kong" in manager.providers
        assert "apisix" in manager.providers

    def test_list_providers(self):
        """Test listing registered providers"""
        manager = Manager()
        provider1 = MockProvider("envoy")
        provider2 = MockProvider("kong")

        manager.register_provider(provider1)
        manager.register_provider(provider2)

        providers = manager.list_providers()
        assert len(providers) == 2
        assert "envoy" in providers
        assert "kong" in providers

    def test_list_providers_empty(self):
        """Test listing providers when none are registered"""
        manager = Manager()
        providers = manager.list_providers()
        assert providers == []

    def test_load_config(self):
        """Test loading configuration from YAML file"""
        yaml_content = """
version: "1.0"
provider: test

services:
  - name: test_service
    type: rest
    protocol: http
    upstream:
      host: test.local
      port: 8080
    routes:
      - path_prefix: /api/test
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_file = f.name

        try:
            manager = Manager()
            config = manager.load_config(temp_file)

            assert config is not None
            assert config.version == "1.0"
            assert config.provider == "test"
            assert len(config.services) == 1
        finally:
            Path(temp_file).unlink()

    def test_generate_success(self):
        """Test successful configuration generation"""
        manager = Manager()
        provider = MockProvider("test")
        manager.register_provider(provider)

        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")
        service = Service(
            name="test",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="test",
            global_config=global_config,
            services=[service]
        )

        result = manager.generate(config)

        assert result is not None
        assert "Mock test configuration" in result
        assert provider.generated_config == config

    def test_generate_provider_not_registered(self):
        """Test generation with unregistered provider"""
        manager = Manager()

        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")
        service = Service(
            name="test",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="nonexistent",
            global_config=global_config,
            services=[service]
        )

        with pytest.raises(ValueError, match="Provider 'nonexistent' not registered"):
            manager.generate(config)

    def test_generate_validation_failed(self):
        """Test generation when validation fails"""
        manager = Manager()
        provider = MockProvider("test", should_validate=False)
        manager.register_provider(provider)

        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")
        service = Service(
            name="test",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="test",
            global_config=global_config,
            services=[service]
        )

        with pytest.raises(ValueError, match="Configuration validation failed"):
            manager.generate(config)

    def test_deploy_success(self):
        """Test successful deployment"""
        manager = Manager()
        provider = MockProvider("test")
        manager.register_provider(provider)

        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")
        service = Service(
            name="test",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="test",
            global_config=global_config,
            services=[service]
        )

        result = manager.deploy(config)

        assert result is True
        assert provider.deployed_config == config

    def test_deploy_provider_not_registered(self):
        """Test deployment with unregistered provider"""
        manager = Manager()

        global_config = GlobalConfig()
        upstream = Upstream(host="test.local", port=8080)
        route = Route(path_prefix="/api")
        service = Service(
            name="test",
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=[route]
        )

        config = Config(
            version="1.0",
            provider="nonexistent",
            global_config=global_config,
            services=[service]
        )

        with pytest.raises(ValueError, match="Provider 'nonexistent' not registered"):
            manager.deploy(config)

    def test_provider_override(self):
        """Test that registering a provider with same name overrides"""
        manager = Manager()
        provider1 = MockProvider("test")
        provider2 = MockProvider("test")

        manager.register_provider(provider1)
        manager.register_provider(provider2)

        assert len(manager.providers) == 1
        assert manager.providers["test"] == provider2
