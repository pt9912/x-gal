"""
Manager for orchestrating GAL operations
"""

from typing import Dict, List
from .config import Config
from .provider import Provider


class Manager:
    """Main GAL manager"""
    
    def __init__(self):
        self.providers: Dict[str, Provider] = {}
    
    def register_provider(self, provider: Provider):
        """Register a gateway provider"""
        self.providers[provider.name()] = provider
    
    def load_config(self, filepath: str) -> Config:
        """Load configuration from YAML file"""
        return Config.from_yaml(filepath)
    
    def generate(self, config: Config) -> str:
        """Generate provider-specific configuration"""
        provider = self.providers.get(config.provider)
        if not provider:
            raise ValueError(f"Provider '{config.provider}' not registered")
        
        if not provider.validate(config):
            raise ValueError(f"Configuration validation failed for {config.provider}")
        
        return provider.generate(config)
    
    def deploy(self, config: Config) -> bool:
        """Deploy configuration to gateway"""
        provider = self.providers.get(config.provider)
        if not provider:
            raise ValueError(f"Provider '{config.provider}' not registered")
        
        return provider.deploy(config)
    
    def list_providers(self) -> List[str]:
        """List all registered providers"""
        return list(self.providers.keys())
