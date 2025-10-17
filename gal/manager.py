"""
Manager for orchestrating GAL operations
"""

from typing import Dict, List
from .config import Config
from .provider import Provider


class Manager:
    """Main GAL manager for orchestrating gateway operations.

    The Manager coordinates all GAL operations including provider registration,
    configuration loading, validation, and generation. It uses a registry
    pattern to manage multiple gateway providers.

    Attributes:
        providers: Dictionary mapping provider names to Provider instances

    Example:
        >>> manager = Manager()
        >>> manager.register_provider(EnvoyProvider())
        >>> manager.register_provider(KongProvider())
        >>> config = manager.load_config("config.yaml")
        >>> output = manager.generate(config)
    """

    def __init__(self):
        """Initialize the Manager with an empty provider registry."""
        self.providers: Dict[str, Provider] = {}

    def register_provider(self, provider: Provider):
        """Register a gateway provider.

        Adds a provider to the registry, making it available for
        configuration generation. Providers are indexed by their name.

        Args:
            provider: Provider instance to register

        Example:
            >>> manager = Manager()
            >>> manager.register_provider(EnvoyProvider())
            >>> "envoy" in manager.list_providers()
            True
        """
        self.providers[provider.name()] = provider

    def load_config(self, filepath: str) -> Config:
        """Load configuration from YAML file.

        Args:
            filepath: Path to the YAML configuration file

        Returns:
            Parsed Config object

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML syntax is invalid

        Example:
            >>> manager = Manager()
            >>> config = manager.load_config("gateway.yaml")
            >>> config.version
            '1.0'
        """
        return Config.from_yaml(filepath)

    def validate(self, config: Config) -> bool:
        """Validate configuration for the specified provider.

        Args:
            config: Configuration object to validate

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If provider not registered or validation fails

        Example:
            >>> manager = Manager()
            >>> manager.register_provider(EnvoyProvider())
            >>> config = manager.load_config("config.yaml")
            >>> manager.validate(config)
            True
        """
        provider = self.providers.get(config.provider)
        if not provider:
            raise ValueError(f"Provider '{config.provider}' not registered")

        if not provider.validate(config):
            raise ValueError(f"Configuration validation failed for {config.provider}")

        return True

    def generate(self, config: Config) -> str:
        """Generate provider-specific configuration.

        Validates the configuration and generates the provider-specific
        output format (YAML, JSON, etc.).

        Args:
            config: Configuration object to generate from

        Returns:
            Generated configuration as string

        Raises:
            ValueError: If provider not registered or validation fails

        Example:
            >>> manager = Manager()
            >>> manager.register_provider(EnvoyProvider())
            >>> config = manager.load_config("config.yaml")
            >>> output = manager.generate(config)
            >>> "static_resources" in output
            True
        """
        provider = self.providers.get(config.provider)
        if not provider:
            raise ValueError(f"Provider '{config.provider}' not registered")

        if not provider.validate(config):
            raise ValueError(f"Configuration validation failed for {config.provider}")

        return provider.generate(config)

    def deploy(self, config: Config) -> bool:
        """Deploy configuration to gateway.

        Optional deployment method that delegates to the provider's
        deploy implementation.

        Args:
            config: Configuration object to deploy

        Returns:
            True if deployment successful

        Raises:
            ValueError: If provider not registered
            NotImplementedError: If provider doesn't support deployment

        Example:
            >>> manager = Manager()
            >>> manager.register_provider(EnvoyProvider())
            >>> config = manager.load_config("config.yaml")
            >>> success = manager.deploy(config)
        """
        provider = self.providers.get(config.provider)
        if not provider:
            raise ValueError(f"Provider '{config.provider}' not registered")

        return provider.deploy(config)

    def list_providers(self) -> List[str]:
        """List all registered providers.

        Returns:
            List of provider names

        Example:
            >>> manager = Manager()
            >>> manager.register_provider(EnvoyProvider())
            >>> manager.register_provider(KongProvider())
            >>> manager.list_providers()
            ['envoy', 'kong']
        """
        return list(self.providers.keys())
