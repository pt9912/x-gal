"""
Manager for orchestrating GAL operations
"""

import logging
from typing import Dict, List
from .config import Config
from .provider import Provider

logger = logging.getLogger(__name__)


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
        provider_name = provider.name()
        self.providers[provider_name] = provider
        logger.debug(f"Registered provider: {provider_name}")

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
        logger.info(f"Loading configuration from: {filepath}")
        try:
            config = Config.from_yaml(filepath)
            logger.info(f"Configuration loaded successfully: provider={config.provider}, services={len(config.services)}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration from {filepath}: {e}")
            raise

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
        logger.info(f"Validating configuration for provider: {config.provider}")
        provider = self.providers.get(config.provider)
        if not provider:
            logger.error(f"Provider '{config.provider}' not registered")
            raise ValueError(f"Provider '{config.provider}' not registered")

        try:
            if not provider.validate(config):
                logger.error(f"Configuration validation failed for {config.provider}")
                raise ValueError(f"Configuration validation failed for {config.provider}")
            logger.info(f"Configuration validation successful for {config.provider}")
            return True
        except Exception as e:
            logger.error(f"Validation error for {config.provider}: {e}")
            raise

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
        logger.info(f"Generating configuration for provider: {config.provider}")
        provider = self.providers.get(config.provider)
        if not provider:
            logger.error(f"Provider '{config.provider}' not registered")
            raise ValueError(f"Provider '{config.provider}' not registered")

        try:
            if not provider.validate(config):
                logger.error(f"Configuration validation failed for {config.provider}")
                raise ValueError(f"Configuration validation failed for {config.provider}")

            result = provider.generate(config)
            logger.info(f"Configuration generated successfully for {config.provider} ({len(result)} bytes)")
            return result
        except Exception as e:
            logger.error(f"Generation error for {config.provider}: {e}")
            raise

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
        logger.info(f"Deploying configuration for provider: {config.provider}")
        provider = self.providers.get(config.provider)
        if not provider:
            logger.error(f"Provider '{config.provider}' not registered")
            raise ValueError(f"Provider '{config.provider}' not registered")

        try:
            result = provider.deploy(config)
            if result:
                logger.info(f"Deployment successful for {config.provider}")
            else:
                logger.warning(f"Deployment returned False for {config.provider}")
            return result
        except Exception as e:
            logger.error(f"Deployment error for {config.provider}: {e}")
            raise

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
