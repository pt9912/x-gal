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
class UpstreamTarget:
    """Individual backend server target configuration.

    Defines a single backend server in an upstream pool for load balancing.

    Attributes:
        host: Backend server hostname or IP address
        port: Backend server port number
        weight: Load balancing weight (default: 1)
                Higher weight = more traffic

    Example:
        >>> target = UpstreamTarget(host="api-1.internal", port=8080, weight=2)
        >>> f"{target.host}:{target.port} (weight: {target.weight})"
        'api-1.internal:8080 (weight: 2)'
    """
    host: str
    port: int
    weight: int = 1


@dataclass
class ActiveHealthCheck:
    """Active health check configuration.

    Defines periodic probing of backend servers to determine health status.

    Attributes:
        enabled: Whether active health checks are enabled (default: True)
        http_path: HTTP path to probe (default: "/health")
        interval: Check interval duration (default: "10s")
        timeout: Individual check timeout (default: "5s")
        healthy_threshold: Consecutive successes to mark healthy (default: 2)
        unhealthy_threshold: Consecutive failures to mark unhealthy (default: 3)
        healthy_status_codes: HTTP status codes considered healthy (default: [200, 201, 204])

    Example:
        >>> check = ActiveHealthCheck(
        ...     http_path="/api/health",
        ...     interval="5s",
        ...     healthy_threshold=2
        ... )
        >>> check.http_path
        '/api/health'
    """
    enabled: bool = True
    http_path: str = "/health"
    interval: str = "10s"
    timeout: str = "5s"
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3
    healthy_status_codes: List[int] = field(
        default_factory=lambda: [200, 201, 204]
    )


@dataclass
class PassiveHealthCheck:
    """Passive health check configuration.

    Monitors ongoing traffic to determine health status (circuit breaker).

    Attributes:
        enabled: Whether passive health checks are enabled (default: True)
        max_failures: Consecutive failures before marking unhealthy (default: 5)
        unhealthy_status_codes: HTTP status codes considered unhealthy
                                (default: [500, 502, 503, 504])

    Example:
        >>> check = PassiveHealthCheck(
        ...     max_failures=3,
        ...     unhealthy_status_codes=[500, 503]
        ... )
        >>> check.max_failures
        3
    """
    enabled: bool = True
    max_failures: int = 5
    unhealthy_status_codes: List[int] = field(
        default_factory=lambda: [500, 502, 503, 504]
    )


@dataclass
class HealthCheckConfig:
    """Combined health check configuration.

    Configures both active and passive health checking for an upstream.

    Attributes:
        active: Optional active health check configuration
        passive: Optional passive health check configuration

    Example:
        >>> health = HealthCheckConfig(
        ...     active=ActiveHealthCheck(http_path="/health"),
        ...     passive=PassiveHealthCheck(max_failures=3)
        ... )
        >>> health.active.http_path
        '/health'
    """
    active: Optional[ActiveHealthCheck] = None
    passive: Optional[PassiveHealthCheck] = None


@dataclass
class LoadBalancerConfig:
    """Load balancing configuration.

    Defines load balancing strategy and behavior for an upstream.

    Attributes:
        algorithm: Load balancing algorithm (default: "round_robin")
                   Options: "round_robin", "least_conn", "ip_hash", "weighted"
        sticky_sessions: Enable sticky sessions (default: False)
        cookie_name: Session cookie name if sticky_sessions enabled (default: "galSession")

    Example:
        >>> lb = LoadBalancerConfig(
        ...     algorithm="least_conn",
        ...     sticky_sessions=True
        ... )
        >>> lb.algorithm
        'least_conn'
    """
    algorithm: str = "round_robin"  # round_robin, least_conn, ip_hash, weighted
    sticky_sessions: bool = False
    cookie_name: str = "galSession"


@dataclass
class Upstream:
    """Upstream backend service configuration.

    Defines the target host(s) and port(s) for a backend service that the
    gateway will proxy requests to, with optional health checks and load balancing.

    Supports two modes:
    1. Single host mode: Use 'host' and 'port' attributes
    2. Multiple targets mode: Use 'targets' list for load balancing

    Attributes:
        host: Single backend service hostname or IP address (simple mode)
        port: Single backend service port number (simple mode)
        targets: List of backend servers for load balancing (advanced mode)
                 If provided, 'host' and 'port' are ignored
        health_check: Optional health check configuration
        load_balancer: Optional load balancing configuration

    Example (simple mode):
        >>> upstream = Upstream(host="api.example.com", port=8080)
        >>> f"{upstream.host}:{upstream.port}"
        'api.example.com:8080'

    Example (load balancing mode):
        >>> upstream = Upstream(
        ...     targets=[
        ...         UpstreamTarget(host="api-1.internal", port=8080, weight=2),
        ...         UpstreamTarget(host="api-2.internal", port=8080, weight=1)
        ...     ],
        ...     health_check=HealthCheckConfig(
        ...         active=ActiveHealthCheck(http_path="/health")
        ...     ),
        ...     load_balancer=LoadBalancerConfig(algorithm="weighted")
        ... )
        >>> len(upstream.targets)
        2
    """
    host: str = ""
    port: int = 0
    targets: List[UpstreamTarget] = field(default_factory=list)
    health_check: Optional[HealthCheckConfig] = None
    load_balancer: Optional[LoadBalancerConfig] = None


@dataclass
class Route:
    """HTTP route configuration for a service.

    Defines how incoming requests are matched and routed to a service.

    Attributes:
        path_prefix: URL path prefix to match (e.g., "/api/users")
        methods: Optional list of HTTP methods (e.g., ["GET", "POST"])
                 If None, all methods are allowed
        rate_limit: Optional rate limiting configuration for this route
        authentication: Optional authentication configuration for this route
        headers: Optional header manipulation configuration for this route
        cors: Optional CORS policy configuration for this route
        circuit_breaker: Optional circuit breaker configuration for this route

    Example:
        >>> route = Route(path_prefix="/api/users", methods=["GET", "POST"])
        >>> route.path_prefix
        '/api/users'
    """
    path_prefix: str
    methods: Optional[List[str]] = None
    rate_limit: Optional['RateLimitConfig'] = None
    authentication: Optional['AuthenticationConfig'] = None
    headers: Optional['HeaderManipulation'] = None
    cors: Optional['CORSPolicy'] = None
    circuit_breaker: Optional['CircuitBreakerConfig'] = None


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
class BasicAuthConfig:
    """Basic Authentication configuration.

    Defines HTTP Basic Authentication with username/password credentials.

    Attributes:
        users: Dictionary mapping usernames to passwords
        realm: Authentication realm (default: "Protected")

    Example:
        >>> basic_auth = BasicAuthConfig(
        ...     users={"admin": "secret123", "user": "pass456"},
        ...     realm="API Gateway"
        ... )
        >>> "admin" in basic_auth.users
        True
    """
    users: Dict[str, str] = field(default_factory=dict)
    realm: str = "Protected"


@dataclass
class ApiKeyConfig:
    """API Key Authentication configuration.

    Defines API key-based authentication using headers or query parameters.

    Attributes:
        keys: List of valid API keys
        key_name: Name of header or query parameter (default: "X-API-Key")
        in_location: Where to look for key ("header" or "query", default: "header")

    Example:
        >>> api_key = ApiKeyConfig(
        ...     keys=["key123", "key456"],
        ...     key_name="X-API-Key",
        ...     in_location="header"
        ... )
        >>> len(api_key.keys)
        2
    """
    keys: List[str] = field(default_factory=list)
    key_name: str = "X-API-Key"
    in_location: str = "header"  # header or query


@dataclass
class JwtConfig:
    """JWT (JSON Web Token) Authentication configuration.

    Defines JWT-based authentication with support for JWKS and multiple issuers.

    Attributes:
        issuer: JWT issuer (iss claim)
        audience: JWT audience (aud claim)
        jwks_uri: JWKS endpoint URL for key discovery
        algorithms: List of allowed signing algorithms (default: ["RS256"])
        required_claims: List of required JWT claims (default: [])

    Example:
        >>> jwt = JwtConfig(
        ...     issuer="https://auth.example.com",
        ...     audience="api.example.com",
        ...     jwks_uri="https://auth.example.com/.well-known/jwks.json",
        ...     algorithms=["RS256", "ES256"]
        ... )
        >>> jwt.issuer
        'https://auth.example.com'
    """
    issuer: str = ""
    audience: str = ""
    jwks_uri: str = ""
    algorithms: List[str] = field(default_factory=lambda: ["RS256"])
    required_claims: List[str] = field(default_factory=list)


@dataclass
class AuthenticationConfig:
    """Authentication configuration for routes.

    Defines authentication requirements for protecting routes with
    various authentication mechanisms.

    Attributes:
        enabled: Whether authentication is enabled (default: True)
        type: Authentication type ("basic", "api_key", or "jwt")
        basic_auth: Basic Auth configuration (when type="basic")
        api_key: API Key configuration (when type="api_key")
        jwt: JWT configuration (when type="jwt")
        fail_status: HTTP status code for auth failures (default: 401)
        fail_message: Error message for auth failures

    Example:
        >>> auth = AuthenticationConfig(
        ...     enabled=True,
        ...     type="api_key",
        ...     api_key=ApiKeyConfig(keys=["key123"])
        ... )
        >>> auth.type
        'api_key'
    """
    enabled: bool = True
    type: str = "api_key"  # basic, api_key, jwt
    basic_auth: Optional[BasicAuthConfig] = None
    api_key: Optional[ApiKeyConfig] = None
    jwt: Optional[JwtConfig] = None
    fail_status: int = 401
    fail_message: str = "Unauthorized"


@dataclass
class HeaderManipulation:
    """HTTP header manipulation configuration.

    Defines how request and response headers should be manipulated,
    including adding, setting, and removing headers.

    Attributes:
        request_add: Headers to add to requests (keeps existing)
        request_set: Headers to set on requests (overwrites existing)
        request_remove: Header names to remove from requests
        response_add: Headers to add to responses (keeps existing)
        response_set: Headers to set on responses (overwrites existing)
        response_remove: Header names to remove from responses

    Example:
        >>> headers = HeaderManipulation(
        ...     request_add={"X-Custom-Header": "value"},
        ...     request_remove=["X-Internal-Header"],
        ...     response_set={"X-Response-Time": "100ms"}
        ... )
        >>> headers.request_add["X-Custom-Header"]
        'value'
    """
    request_add: Dict[str, str] = field(default_factory=dict)
    request_set: Dict[str, str] = field(default_factory=dict)
    request_remove: List[str] = field(default_factory=list)
    response_add: Dict[str, str] = field(default_factory=dict)
    response_set: Dict[str, str] = field(default_factory=dict)
    response_remove: List[str] = field(default_factory=list)


@dataclass
class CORSPolicy:
    """CORS (Cross-Origin Resource Sharing) policy configuration.

    Defines CORS policies to control cross-origin access to APIs,
    including allowed origins, methods, headers, and credentials.

    Attributes:
        enabled: Whether CORS is enabled (default: True)
        allowed_origins: List of allowed origin URLs (e.g., ["https://example.com"])
                        Use ["*"] to allow all origins
        allowed_methods: List of allowed HTTP methods (default: GET, POST, PUT, DELETE, OPTIONS)
        allowed_headers: List of allowed request headers (default: Content-Type, Authorization)
        expose_headers: List of headers to expose to browser (default: [])
        allow_credentials: Whether to allow credentials (cookies, auth) (default: False)
        max_age: Preflight cache duration in seconds (default: 86400 = 24 hours)

    Example:
        >>> cors = CORSPolicy(
        ...     enabled=True,
        ...     allowed_origins=["https://example.com", "https://app.example.com"],
        ...     allowed_methods=["GET", "POST"],
        ...     allow_credentials=True
        ... )
        >>> cors.allowed_origins[0]
        'https://example.com'
    """
    enabled: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allowed_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Authorization"])
    expose_headers: List[str] = field(default_factory=list)
    allow_credentials: bool = False
    max_age: int = 86400  # 24 hours


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration for routes.

    Implements the circuit breaker pattern to prevent cascading failures
    by detecting unhealthy upstream services and temporarily blocking requests.

    Provider Support:
        - APISIX: Native api-breaker plugin (100%)
        - Traefik: Native CircuitBreaker middleware (100%)
        - Envoy: Outlier Detection (100%)
        - Kong: Third-party kong-circuit-breaker plugin (Limited)

    Attributes:
        enabled: Whether circuit breaker is enabled (default: True)
        max_failures: Maximum consecutive failures before opening circuit (default: 5)
        timeout: Duration to wait before attempting recovery (default: "30s")
        half_open_requests: Number of test requests in half-open state (default: 3)
        unhealthy_status_codes: HTTP status codes considered failures (default: [500, 502, 503, 504])
        healthy_status_codes: HTTP status codes considered healthy (default: [200, 201, 202, 204])
        failure_response_code: HTTP status code when circuit is open (default: 503)
        failure_response_message: Error message when circuit is open

    Circuit States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Circuit broken, requests fail immediately
        - HALF_OPEN: Testing recovery with limited requests

    Example:
        >>> cb = CircuitBreakerConfig(
        ...     enabled=True,
        ...     max_failures=5,
        ...     timeout="30s",
        ...     half_open_requests=3,
        ...     unhealthy_status_codes=[500, 502, 503, 504]
        ... )
        >>> cb.max_failures
        5
    """
    enabled: bool = True
    max_failures: int = 5
    timeout: str = "30s"
    half_open_requests: int = 3
    unhealthy_status_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
    healthy_status_codes: List[int] = field(default_factory=lambda: [200, 201, 202, 204])
    failure_response_code: int = 503
    failure_response_message: str = "Service temporarily unavailable"


@dataclass
class Transformation:
    """Request payload transformation configuration.

    Defines how incoming request payloads should be transformed,
    including default values, computed fields, validation rules,
    and header manipulation.

    Attributes:
        enabled: Whether transformations are enabled (default: True)
        defaults: Default values to set for missing fields
        computed_fields: List of fields to automatically generate
        metadata: Additional metadata to add to requests
        validation: Optional validation rules for requests
        headers: Optional header manipulation configuration

    Example:
        >>> trans = Transformation(
        ...     enabled=True,
        ...     defaults={"status": "active"},
        ...     computed_fields=[
        ...         ComputedField(field="id", generator="uuid")
        ...     ],
        ...     validation=Validation(required_fields=["email"]),
        ...     headers=HeaderManipulation(
        ...         request_add={"X-Service": "api"}
        ...     )
        ... )
        >>> trans.defaults["status"]
        'active'
    """
    enabled: bool = True
    defaults: Dict[str, Any] = field(default_factory=dict)
    computed_fields: List[ComputedField] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    validation: Optional[Validation] = None
    headers: Optional[HeaderManipulation] = None


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

            # Parse routes with optional rate limiting, authentication, headers, and CORS
            routes = []
            for route_data in svc_data['routes']:
                rate_limit = None
                if 'rate_limit' in route_data:
                    rate_limit = RateLimitConfig(**route_data['rate_limit'])

                authentication = None
                if 'authentication' in route_data:
                    auth_data = route_data['authentication']
                    auth_type = auth_data.get('type', 'api_key')

                    # Parse type-specific configuration
                    basic_auth = None
                    api_key = None
                    jwt = None

                    if auth_type == 'basic' and 'basic_auth' in auth_data:
                        basic_auth = BasicAuthConfig(**auth_data['basic_auth'])
                    elif auth_type == 'api_key' and 'api_key' in auth_data:
                        api_key = ApiKeyConfig(**auth_data['api_key'])
                    elif auth_type == 'jwt' and 'jwt' in auth_data:
                        jwt = JwtConfig(**auth_data['jwt'])

                    authentication = AuthenticationConfig(
                        enabled=auth_data.get('enabled', True),
                        type=auth_type,
                        basic_auth=basic_auth,
                        api_key=api_key,
                        jwt=jwt,
                        fail_status=auth_data.get('fail_status', 401),
                        fail_message=auth_data.get('fail_message', 'Unauthorized')
                    )

                # Parse route-level headers
                route_headers = None
                if 'headers' in route_data:
                    route_headers = HeaderManipulation(**route_data['headers'])

                # Parse route-level CORS
                cors_policy = None
                if 'cors' in route_data:
                    cors_policy = CORSPolicy(**route_data['cors'])

                # Parse route-level circuit breaker
                circuit_breaker = None
                if 'circuit_breaker' in route_data:
                    circuit_breaker = CircuitBreakerConfig(**route_data['circuit_breaker'])

                route = Route(
                    path_prefix=route_data['path_prefix'],
                    methods=route_data.get('methods'),
                    rate_limit=rate_limit,
                    authentication=authentication,
                    headers=route_headers,
                    cors=cors_policy,
                    circuit_breaker=circuit_breaker
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

                # Parse transformation headers
                trans_headers = None
                if 'headers' in trans_data:
                    trans_headers = HeaderManipulation(**trans_data['headers'])

                transformation = Transformation(
                    enabled=trans_data.get('enabled', True),
                    defaults=trans_data.get('defaults', {}),
                    computed_fields=computed_fields,
                    metadata=trans_data.get('metadata', {}),
                    validation=validation,
                    headers=trans_headers
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
