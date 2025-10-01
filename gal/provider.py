"""
Provider interface
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from .config import Config


class Provider(ABC):
    """Abstract base class for all gateway providers"""
    
    @abstractmethod
    def name(self) -> str:
        """Return provider name"""
        pass
    
    @abstractmethod
    def validate(self, config: Config) -> bool:
        """Validate configuration for this provider"""
        pass
    
    @abstractmethod
    def generate(self, config: Config) -> str:
        """Generate provider-specific configuration"""
        pass
    
    def deploy(self, config: Config) -> bool:
        """Deploy configuration (optional)"""
        raise NotImplementedError(f"Deployment not implemented for {self.name()}")
