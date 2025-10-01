"""
Configuration models for GAL
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import yaml


@dataclass
class GlobalConfig:
    """Global gateway configuration"""
    host: str = "0.0.0.0"
    port: int = 10000
    admin_port: int = 9901
    timeout: str = "30s"


@dataclass
class Upstream:
    """Upstream service configuration"""
    host: str
    port: int


@dataclass
class Route:
    """Route configuration"""
    path_prefix: str
    methods: Optional[List[str]] = None


@dataclass
class ComputedField:
    """Computed field configuration"""
    field: str
    generator: str  # uuid, timestamp, random
    prefix: str = ""
    suffix: str = ""
    expression: Optional[str] = None


@dataclass
class Validation:
    """Validation rules"""
    required_fields: List[str] = field(default_factory=list)


@dataclass
class Transformation:
    """Transformation configuration"""
    enabled: bool = True
    defaults: Dict[str, Any] = field(default_factory=dict)
    computed_fields: List[ComputedField] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    validation: Optional[Validation] = None


@dataclass
class Service:
    """Service configuration"""
    name: str
    type: str  # grpc or rest
    protocol: str
    upstream: Upstream
    routes: List[Route]
    transformation: Optional[Transformation] = None


@dataclass
class Plugin:
    """Plugin configuration"""
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    """Main GAL configuration"""
    version: str
    provider: str
    global_config: GlobalConfig
    services: List[Service]
    plugins: List[Plugin] = field(default_factory=list)
    
    @classmethod
    def from_yaml(cls, filepath: str) -> 'Config':
        """Load configuration from YAML file"""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        # Parse global config
        global_data = data.get('global', {})
        global_config = GlobalConfig(**global_data)
        
        # Parse services
        services = []
        for svc_data in data.get('services', []):
            upstream = Upstream(**svc_data['upstream'])
            routes = [Route(**r) for r in svc_data['routes']]
            
            transformation = None
            if 'transformation' in svc_data:
                trans_data = svc_data['transformation']
                computed_fields = [
                    ComputedField(**cf) for cf in trans_data.get('computed_fields', [])
                ]
                validation = None
                if 'validation' in trans_data:
                    validation = Validation(**trans_data['validation'])
                
                transformation = Transformation(
                    enabled=trans_data.get('enabled', True),
                    defaults=trans_data.get('defaults', {}),
                    computed_fields=computed_fields,
                    metadata=trans_data.get('metadata', {}),
                    validation=validation
                )
            
            service = Service(
                name=svc_data['name'],
                type=svc_data['type'],
                protocol=svc_data['protocol'],
                upstream=upstream,
                routes=routes,
                transformation=transformation
            )
            services.append(service)
        
        # Parse plugins
        plugins = []
        for plugin_data in data.get('plugins', []):
            plugin = Plugin(**plugin_data)
            plugins.append(plugin)
        
        return cls(
            version=data['version'],
            provider=data['provider'],
            global_config=global_config,
            services=services,
            plugins=plugins
        )
    
    def get_service(self, name: str) -> Optional[Service]:
        """Get service by name"""
        for svc in self.services:
            if svc.name == name:
                return svc
        return None
    
    def get_grpc_services(self) -> List[Service]:
        """Get all gRPC services"""
        return [s for s in self.services if s.type == 'grpc']
    
    def get_rest_services(self) -> List[Service]:
        """Get all REST services"""
        return [s for s in self.services if s.type == 'rest']
