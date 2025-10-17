"""
Configuration models for GAL
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging
import yaml

logger = logging.getLogger(__name__)


@dataclass
class GlobalConfig:
    """Global gateway configuration settings.

    Attributes:
        host: Gateway listen address (default: "0.0.0.0")
        port: Gateway listen port (default: 10000)
        admin_port: Admin interface port (default: 9901)
        timeout: Request timeout duration (default: "30s")

    Example:
        >>> config = GlobalConfig(host="127.0.0.1", port=8080)
        >>> config.port
        8080
    """
    host: str = "0.0.0.0"
    port: int = 10000
    admin_port: int = 9901
    timeout: str = "30s"


@dataclass
class Upstream:
    """Upstream backend service configuration.

    Defines the target host and port for a backend service that the
    gateway will proxy requests to.

    Attributes:
        host: Backend service hostname or IP address
        port: Backend service port number

    Example:
        >>> upstream = Upstream(host="api.example.com", port=8080)
        >>> f"{upstream.host}:{upstream.port}"
        'api.example.com:8080'
    """
    host: str
    port: int


@dataclass
class Route:
    """HTTP route configuration for a service.

    Defines how incoming requests are matched and routed to a service.

    Attributes:
        path_prefix: URL path prefix to match (e.g., "/api/users")
        methods: Optional list of HTTP methods (e.g., ["GET", "POST"])
                 If None, all methods are allowed
        rate_limit: Optional rate limiting configuration for this route

    Example:
        >>> route = Route(path_prefix="/api/users", methods=["GET", "POST"])
        >>> route.path_prefix
        '/api/users'
    """
    path_prefix: str
    methods: Optional[List[str]] = None
    rate_limit: Optional['RateLimitConfig'] = None


@dataclass
class ComputedField:
    """Configuration for automatically computed/generated fields.

    Defines a field that should be automatically generated in the request
    payload using a specified generator.

    Attributes:
        field: Name of the field to generate
        generator: Generator type ("uuid", "timestamp", or "random")
        prefix: Optional prefix to prepend to generated value
        suffix: Optional suffix to append to generated value
        expression: Optional custom expression (not currently used)

    Example:
        >>> field = ComputedField(
        ...     field="user_id",
        ...     generator="uuid",
        ...     prefix="usr_"
        ... )
        >>> field.generator
        'uuid'
    """
    field: str
    generator: str  # uuid, timestamp, random
    prefix: str = ""
    suffix: str = ""
    expression: Optional[str] = None


@dataclass
class Validation:
    """Request payload validation rules.

    Defines which fields are required in incoming request payloads.

    Attributes:
        required_fields: List of field names that must be present in requests

    Example:
        >>> validation = Validation(required_fields=["email", "name"])
        >>> "email" in validation.required_fields
        True
    """
    required_fields: List[str] = field(default_factory=list)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for routes.

    Defines rate limiting policies to protect APIs from abuse and ensure
    fair resource usage across clients.

    Attributes:
        enabled: Whether rate limiting is enabled (default: True)
        requests_per_second: Maximum requests allowed per second
        burst: Maximum burst size for spike handling (default: 2x rate)
        key_type: How to identify clients ("ip_address", "header", "jwt_claim")
        key_header: Header name when key_type="header" (e.g., "X-API-Key")
        key_claim: JWT claim when key_type="jwt_claim" (e.g., "sub")
        response_status: HTTP status code for rate limited requests (default: 429)
        response_message: Error message for rate limited requests

    Example:
        >>> rate_limit = RateLimitConfig(
        ...     enabled=True,
        ...     requests_per_second=100,
        ...     burst=200,
        ...     key_type="ip_address"
        ... )
        >>> rate_limit.requests_per_second
        100
    """
    enabled: bool = True
    requests_per_second: int = 100
    burst: Optional[int] = None
    key_type: str = "ip_address"  # ip_address, header, jwt_claim
    key_header: Optional[str] = None
    key_claim: Optional[str] = None
    response_status: int = 429
    response_message: str = "Rate limit exceeded"

    def __post_init__(self):
        """Set default burst value if not specified."""
        if self.burst is None:
            self.burst = self.requests_per_second * 2


@dataclass
class Transformation:
    """Request payload transformation configuration.

    Defines how incoming request payloads should be transformed,
    including default values, computed fields, and validation rules.

    Attributes:
        enabled: Whether transformations are enabled (default: True)
        defaults: Default values to set for missing fields
        computed_fields: List of fields to automatically generate
        metadata: Additional metadata to add to requests
        validation: Optional validation rules for requests

    Example:
        >>> trans = Transformation(
        ...     enabled=True,
        ...     defaults={"status": "active"},
        ...     computed_fields=[
        ...         ComputedField(field="id", generator="uuid")
        ...     ],
        ...     validation=Validation(required_fields=["email"])
        ... )
        >>> trans.defaults["status"]
        'active'
    """
    enabled: bool = True
    defaults: Dict[str, Any] = field(default_factory=dict)
    computed_fields: List[ComputedField] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    validation: Optional[Validation] = None


@dataclass
class Service:
    """Backend service configuration.

    Defines a backend service that the gateway will proxy to,
    including routing rules and optional transformations.

    Attributes:
        name: Unique service identifier
        type: Service type ("grpc" or "rest")
        protocol: Communication protocol ("http", "http2", or "grpc")
        upstream: Backend service endpoint configuration
        routes: List of routing rules for this service
        transformation: Optional request transformation configuration

    Example:
        >>> service = Service(
        ...     name="user_service",
        ...     type="rest",
        ...     protocol="http",
        ...     upstream=Upstream(host="users", port=8080),
        ...     routes=[Route(path_prefix="/api/users")]
        ... )
        >>> service.name
        'user_service'
    """
    name: str
    type: str  # grpc or rest
    protocol: str
    upstream: Upstream
    routes: List[Route]
    transformation: Optional[Transformation] = None


@dataclass
class Plugin:
    """Gateway plugin configuration.

    Defines a plugin to be enabled on the gateway with its configuration.

    Attributes:
        name: Plugin name/identifier
        enabled: Whether the plugin is enabled (default: True)
        config: Plugin-specific configuration parameters

    Example:
        >>> plugin = Plugin(
        ...     name="rate_limiting",
        ...     enabled=True,
        ...     config={"requests_per_second": 100}
        ... )
        >>> plugin.config["requests_per_second"]
        100
    """
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    """Main GAL configuration container.

    Top-level configuration object that contains all gateway settings,
    services, and plugins.

    Attributes:
        version: Configuration version string
        provider: Target gateway provider ("envoy", "kong", "apisix", "traefik")
        global_config: Global gateway settings
        services: List of backend services
        plugins: List of gateway plugins (default: empty list)

    Example:
        >>> config = Config(
        ...     version="1.0",
        ...     provider="envoy",
        ...     global_config=GlobalConfig(),
        ...     services=[service1, service2]
        ... )
        >>> config.provider
        'envoy'
    """
    version: str
    provider: str
    global_config: GlobalConfig
    services: List[Service]
    plugins: List[Plugin] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, filepath: str) -> 'Config':
        """Load configuration from YAML file.

        Parses a YAML configuration file and creates a Config object
        with all services, transformations, and plugins.

        Args:
            filepath: Path to the YAML configuration file

        Returns:
            Config: Parsed configuration object

        Raises:
            FileNotFoundError: If the config file doesn't exist
            yaml.YAMLError: If the YAML syntax is invalid
            KeyError: If required fields are missing
            TypeError: If field types don't match

        Example:
            >>> config = Config.from_yaml("gateway.yaml")
            >>> len(config.services)
            5
        """
        logger.debug(f"Loading configuration from {filepath}")
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {filepath}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML syntax in {filepath}: {e}")
            raise

        # Parse global config
        global_data = data.get('global', {})
        global_config = GlobalConfig(**global_data)
        logger.debug(f"Parsed global config: {global_config.host}:{global_config.port}")
        
        # Parse services
        services = []
        for svc_data in data.get('services', []):
            upstream = Upstream(**svc_data['upstream'])

            # Parse routes with optional rate limiting
            routes = []
            for route_data in svc_data['routes']:
                rate_limit = None
                if 'rate_limit' in route_data:
                    rate_limit = RateLimitConfig(**route_data['rate_limit'])

                route = Route(
                    path_prefix=route_data['path_prefix'],
                    methods=route_data.get('methods'),
                    rate_limit=rate_limit
                )
                routes.append(route)
            
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

        logger.debug(f"Parsed {len(services)} services and {len(plugins)} plugins")
        logger.info(f"Configuration loaded: provider={data['provider']}, services={len(services)}")

        return cls(
            version=data['version'],
            provider=data['provider'],
            global_config=global_config,
            services=services,
            plugins=plugins
        )
    
    def get_service(self, name: str) -> Optional[Service]:
        """Get service by name.

        Args:
            name: Service name to search for

        Returns:
            Service object if found, None otherwise

        Example:
            >>> service = config.get_service("user_service")
            >>> service.name if service else "Not found"
            'user_service'
        """
        for svc in self.services:
            if svc.name == name:
                return svc
        return None
    
    def get_grpc_services(self) -> List[Service]:
        """Get all gRPC services.

        Returns:
            List of services with type="grpc"

        Example:
            >>> grpc_services = config.get_grpc_services()
            >>> len(grpc_services)
            3
        """
        return [s for s in self.services if s.type == 'grpc']
    
    def get_rest_services(self) -> List[Service]:
        """Get all REST services.

        Returns:
            List of services with type="rest"

        Example:
            >>> rest_services = config.get_rest_services()
            >>> all(s.type == "rest" for s in rest_services)
            True
        """
        return [s for s in self.services if s.type == 'rest']
