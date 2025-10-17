"""
Provider interface module.

Defines the abstract base class that all gateway providers must implement.
This ensures a consistent interface across different gateway implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from .config import Config


class Provider(ABC):
    """Abstract base class for all gateway providers.

    All gateway provider implementations (Envoy, Kong, APISIX, Traefik)
    must inherit from this class and implement its abstract methods.

    This class defines the contract that all providers must follow,
    ensuring consistent behavior across different gateway implementations.

    Methods to implement:
        - name(): Return the provider's unique identifier
        - validate(): Validate configuration for this specific provider
        - generate(): Generate provider-specific configuration output

    Optional methods:
        - deploy(): Deploy configuration to gateway (if supported)

    Example:
        >>> class MyProvider(Provider):
        ...     def name(self) -> str:
        ...         return "myprovider"
        ...
        ...     def validate(self, config: Config) -> bool:
        ...         return len(config.services) > 0
        ...
        ...     def generate(self, config: Config) -> str:
        ...         return "# Generated config"
    """

    @abstractmethod
    def name(self) -> str:
        """Return the unique provider name.

        This name is used to identify the provider in the registry
        and must match the provider name in configurations.

        Returns:
            Provider name as lowercase string (e.g., "envoy", "kong")

        Example:
            >>> provider = EnvoyProvider()
            >>> provider.name()
            'envoy'
        """
        pass

    @abstractmethod
    def validate(self, config: Config) -> bool:
        """Validate configuration for this provider.

        Performs provider-specific validation to ensure the configuration
        is compatible with this gateway provider.

        Args:
            config: Configuration object to validate

        Returns:
            True if validation passes

        Raises:
            ValueError: If validation fails with specific error message

        Example:
            >>> provider = EnvoyProvider()
            >>> config = Config(...)
            >>> provider.validate(config)
            True
        """
        pass

    @abstractmethod
    def generate(self, config: Config) -> str:
        """Generate provider-specific configuration.

        Transforms the generic GAL configuration into the provider's
        specific format (YAML, JSON, etc.).

        Args:
            config: Configuration object to transform

        Returns:
            Generated configuration as string in provider-specific format

        Example:
            >>> provider = EnvoyProvider()
            >>> config = Config(...)
            >>> output = provider.generate(config)
            >>> "static_resources:" in output
            True
        """
        pass

    def deploy(self, config: Config) -> bool:
        """Deploy configuration to gateway (optional).

        Optional method for deploying the generated configuration
        directly to the gateway. Not all providers may support this.

        Args:
            config: Configuration to deploy

        Returns:
            True if deployment successful

        Raises:
            NotImplementedError: If provider doesn't support deployment

        Example:
            >>> provider = MyProvider()
            >>> config = Config(...)
            >>> provider.deploy(config)
            NotImplementedError: Deployment not implemented for myprovider
        """
        raise NotImplementedError(f"Deployment not implemented for {self.name()}")
