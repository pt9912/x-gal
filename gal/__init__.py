"""
Gateway Abstraction Layer (GAL)
Provider-agnostic API Gateway configuration system
"""

__version__ = "1.0.0"

from .config import Config, Service, Transformation
from .manager import Manager
from .provider import Provider

__all__ = ["Config", "Service", "Transformation", "Manager", "Provider"]
