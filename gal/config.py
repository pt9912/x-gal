"""
Configuration models for GAL
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Export all public classes
__all__ = [
    # Global configuration
    "GlobalConfig",
    "LoggingConfig",
    "MetricsConfig",
    "AzureAPIMGlobalConfig",
    "AzureAPIMConfig",
    "AWSAPIGatewayConfig",
    "GCPAPIGatewayConfig",
    # Upstream configuration
    "UpstreamTarget",
    "Upstream",
    "ActiveHealthCheck",
    "PassiveHealthCheck",
    "HealthCheckConfig",
    "LoadBalancerConfig",
    # Rate limiting
    "RateLimitConfig",
    # Authentication
    "BasicAuthConfig",
    "ApiKeyConfig",
    "JwtConfig",
    "AuthenticationConfig",
    # Headers & CORS
    "HeaderManipulation",
    "CORSPolicy",
    # Circuit breaker
    "CircuitBreakerConfig",
    # Timeout & retry
    "TimeoutConfig",
    "RetryConfig",
    # WebSocket
    "WebSocketConfig",
    # Transformations
    "ComputedField",
    "Validation",
    "RequestBodyTransformation",
    "ResponseBodyTransformation",
    "BodyTransformationConfig",
    "Transformation",
    # gRPC
    "ProtoDescriptor",
    "GrpcTransformation",
    # Traffic splitting (Feature 5)
    "HeaderMatchRule",
    "CookieMatchRule",
    "RoutingRules",
    "SplitTarget",
    "TrafficSplitConfig",
    # Request mirroring (Feature 6)
    "MirrorTarget",
    "MirroringConfig",
    # Route & Service
    "Route",
    "Service",
    # Plugin
    "Plugin",
    # Config
    "Config",
]


@dataclass
class GlobalConfig:
    """Global gateway configuration settings.

    Attributes:
        host: Gateway listen address (default: "0.0.0.0")
        port: Gateway listen port (default: 10000)
        admin_port: Admin interface port (default: 9901)
        timeout: Request timeout duration (default: "30s")
        logging: Optional logging configuration
        metrics: Optional metrics configuration
        azure_apim: Optional Azure API Management global configuration
        aws_apigateway: Optional AWS API Gateway global configuration
        gcp_apigateway: Optional GCP API Gateway global configuration

    Example:
        >>> config = GlobalConfig(host="127.0.0.1", port=8080)
        >>> config.port
        8080
    """

    host: str = "0.0.0.0"
    port: int = 10000
    admin_port: int = 9901
    timeout: str = "30s"
    logging: Optional["LoggingConfig"] = None
    metrics: Optional["MetricsConfig"] = None
    azure_apim: Optional["AzureAPIMGlobalConfig"] = None
    aws_apigateway: Optional["AWSAPIGatewayConfig"] = None
    gcp_apigateway: Optional["GCPAPIGatewayConfig"] = None
    kong: Optional["KongGlobalConfig"] = None


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
    healthy_status_codes: List[int] = field(default_factory=lambda: [200, 201, 204])


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
    unhealthy_status_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504])


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
        websocket: Optional WebSocket configuration for this route
        circuit_breaker: Optional circuit breaker configuration for this route
        body_transformation: Optional request/response body transformation configuration
        timeout: Optional timeout configuration for this route
        retry: Optional retry policy configuration for this route
        grpc_transformation: Optional gRPC transformation configuration
        traffic_split: Optional traffic splitting configuration for A/B testing
        mirroring: Optional request mirroring/shadowing configuration
        advanced_routing: Optional advanced routing configuration for complex traffic management
        advanced_routing_targets: List of named backend targets for advanced routing

    Example:
        >>> route = Route(path_prefix="/api/users", methods=["GET", "POST"])
        >>> route.path_prefix
        '/api/users'
    """

    path_prefix: str
    methods: Optional[List[str]] = None
    rate_limit: Optional["RateLimitConfig"] = None
    authentication: Optional["AuthenticationConfig"] = None
    headers: Optional["HeaderManipulation"] = None
    cors: Optional["CORSPolicy"] = None
    websocket: Optional["WebSocketConfig"] = None
    circuit_breaker: Optional["CircuitBreakerConfig"] = None
    body_transformation: Optional["BodyTransformationConfig"] = None
    timeout: Optional["TimeoutConfig"] = None
    retry: Optional["RetryConfig"] = None
    grpc_transformation: Optional["GrpcTransformation"] = None
    traffic_split: Optional["TrafficSplitConfig"] = None
    mirroring: Optional["MirroringConfig"] = None
    advanced_routing: Optional["AdvancedRoutingConfig"] = None
    advanced_routing_targets: List["AdvancedRoutingTarget"] = field(default_factory=list)


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
    allowed_methods: List[str] = field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    allowed_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Authorization"])
    expose_headers: List[str] = field(default_factory=list)
    allow_credentials: bool = False
    max_age: int = 86400  # 24 hours


@dataclass
class WebSocketConfig:
    """WebSocket configuration for routes.

    Enables WebSocket support for real-time bidirectional communication,
    commonly used for chat applications, live dashboards, and streaming updates.

    Provider Support:
        - Envoy: Native WebSocket support via HTTP/1.1 Upgrade
        - Kong: Native WebSocket support
        - APISIX: Native WebSocket support
        - Traefik: Native WebSocket support
        - Nginx: WebSocket support via proxy_http_version 1.1
        - HAProxy: Native WebSocket support

    Attributes:
        enabled: Whether WebSocket is enabled for this route (default: True)
        idle_timeout: Maximum idle time before connection is closed (default: "300s")
        ping_interval: Interval for sending ping frames to keep connection alive (default: "30s")
        max_message_size: Maximum message size in bytes (default: 1MB)
        compression: Enable per-message compression (default: False)

    Example:
        >>> ws = WebSocketConfig(
        ...     enabled=True,
        ...     idle_timeout="600s",
        ...     ping_interval="60s",
        ...     compression=True
        ... )
        >>> ws.idle_timeout
        '600s'
    """

    enabled: bool = True
    idle_timeout: str = "300s"  # 5 minutes
    ping_interval: str = "30s"
    max_message_size: int = 1048576  # 1MB
    compression: bool = False


@dataclass
class RequestBodyTransformation:
    """Request body transformation configuration.

    Defines how incoming request bodies should be transformed,
    including adding fields, removing fields, and renaming fields.

    Attributes:
        add_fields: Dictionary of fields to add to request body (field_name: value/template)
        remove_fields: List of field names to remove from request body
        rename_fields: Dictionary mapping old field names to new field names

    Example:
        >>> req_transform = RequestBodyTransformation(
        ...     add_fields={"timestamp": "{{now}}", "trace_id": "{{uuid}}"},
        ...     remove_fields=["internal_id", "debug_info"],
        ...     rename_fields={"old_name": "new_name"}
        ... )
    """

    add_fields: Dict[str, Any] = field(default_factory=dict)
    remove_fields: List[str] = field(default_factory=list)
    rename_fields: Dict[str, str] = field(default_factory=dict)


@dataclass
class ResponseBodyTransformation:
    """Response body transformation configuration.

    Defines how outgoing response bodies should be transformed,
    primarily for filtering sensitive data and adding metadata.

    Attributes:
        filter_fields: List of sensitive field names to remove from response
        add_fields: Dictionary of fields to add to response body

    Example:
        >>> resp_transform = ResponseBodyTransformation(
        ...     filter_fields=["password", "secret_key", "api_token"],
        ...     add_fields={"server_timestamp": "{{now}}"}
        ... )
    """

    filter_fields: List[str] = field(default_factory=list)
    add_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BodyTransformationConfig:
    """Complete body transformation configuration for requests and responses.

    Provides comprehensive body transformation capabilities for both
    request and response bodies, enabling data enrichment, filtering,
    and field manipulation.

    Provider Support:
        - Envoy: Lua filter (100% - full scripting support)
        - Kong: request-transformer & response-transformer plugins (100%)
        - APISIX: serverless-pre-function & serverless-post-function (100%)
        - Traefik: Custom middleware via ForwardAuth (Limited - requires external service)
        - Nginx: Lua scripting via OpenResty (100% with OpenResty)
        - HAProxy: Lua scripting (100%)

    Attributes:
        enabled: Whether body transformation is enabled (default: True)
        request: Request body transformation configuration
        response: Response body transformation configuration

    Example:
        >>> body_transform = BodyTransformationConfig(
        ...     enabled=True,
        ...     request=RequestBodyTransformation(
        ...         add_fields={"timestamp": "{{now}}"},
        ...         remove_fields=["internal_id"]
        ...     ),
        ...     response=ResponseBodyTransformation(
        ...         filter_fields=["password", "secret"]
        ...     )
        ... )
    """

    enabled: bool = True
    request: Optional[RequestBodyTransformation] = None
    response: Optional[ResponseBodyTransformation] = None


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
class TimeoutConfig:
    """Timeout configuration for requests.

    Configures various timeout parameters for upstream connections
    and requests to prevent hanging connections and ensure responsiveness.

    Provider Support:
        - Envoy: Full support (connect, idle, request timeouts)
        - Kong: Full support (connect, send, read timeouts)
        - APISIX: Full support (connect, send, read timeouts)
        - Traefik: Full support (dial, response header, idle timeouts)
        - Nginx: Full support (proxy_connect, proxy_send, proxy_read)
        - HAProxy: Full support (timeout connect, client, server)

    Attributes:
        connect: Maximum time to establish connection (default: "5s")
        send: Maximum time to send request to upstream (default: "30s")
        read: Maximum time to receive response from upstream (default: "60s")
        idle: Maximum time to keep idle connection (default: "300s")

    Example:
        >>> timeout = TimeoutConfig(
        ...     connect="5s",
        ...     send="30s",
        ...     read="60s",
        ...     idle="300s"
        ... )
        >>> timeout.connect
        '5s'
    """

    connect: str = "5s"
    send: str = "30s"
    read: str = "60s"
    idle: str = "300s"


@dataclass
class RetryConfig:
    """Retry policy configuration for failed requests.

    Implements automatic retry logic for failed upstream requests
    with configurable backoff strategies and retry conditions.

    Provider Support:
        - Envoy: Full support (retry_on, num_retries, retry_host_predicate)
        - Kong: Full support (retries plugin)
        - APISIX: Full support (retry plugin with exponential backoff)
        - Traefik: Full support (attempts parameter)
        - Nginx: Partial support (proxy_next_upstream)
        - HAProxy: Full support (retry-on parameter)

    Attributes:
        enabled: Whether retry is enabled (default: True)
        attempts: Number of retry attempts (default: 3)
        backoff: Backoff strategy - "exponential" or "linear" (default: "exponential")
        base_interval: Base interval for exponential backoff (default: "25ms")
        max_interval: Maximum interval between retries (default: "250ms")
        retry_on: List of conditions to trigger retry (default: connection errors + 5xx)

    Retry Conditions:
        - "connect_timeout": Connection timeout
        - "http_5xx": Any 5xx HTTP status code
        - "http_502": HTTP 502 Bad Gateway
        - "http_503": HTTP 503 Service Unavailable
        - "http_504": HTTP 504 Gateway Timeout
        - "retriable_4xx": Retriable 4xx errors (429)
        - "reset": Connection reset
        - "refused": Connection refused

    Example:
        >>> retry = RetryConfig(
        ...     enabled=True,
        ...     attempts=3,
        ...     backoff="exponential",
        ...     retry_on=["connect_timeout", "http_5xx"]
        ... )
        >>> retry.attempts
        3
    """

    enabled: bool = True
    attempts: int = 3
    backoff: str = "exponential"
    base_interval: str = "25ms"
    max_interval: str = "250ms"
    retry_on: List[str] = field(default_factory=lambda: ["connect_timeout", "http_5xx"])


@dataclass
class LoggingConfig:
    """Logging configuration for access logs and observability.

    Attributes:
        enabled: Enable structured logging (default: True)
        format: Log format - "json", "text", "custom" (default: "json")
        level: Log level - "debug", "info", "warning", "error" (default: "info")
        access_log_path: Path to access log file (default: "/var/log/gateway/access.log")
        error_log_path: Path to error log file (default: "/var/log/gateway/error.log")
        sample_rate: Sampling rate 0.0-1.0 for high-traffic (default: 1.0 = all logs)
        include_request_body: Include request body in logs (default: False)
        include_response_body: Include response body in logs (default: False)
        include_headers: Headers to include in logs (default: ["X-Request-ID", "User-Agent"])
        exclude_paths: Paths to exclude from logging (e.g., health checks)
        custom_fields: Additional custom fields to add to logs
    """

    enabled: bool = True
    format: str = "json"  # json, text, custom
    level: str = "info"  # debug, info, warning, error
    access_log_path: str = "/var/log/gateway/access.log"
    error_log_path: str = "/var/log/gateway/error.log"
    sample_rate: float = 1.0  # 0.0-1.0
    include_request_body: bool = False
    include_response_body: bool = False
    include_headers: List[str] = field(default_factory=lambda: ["X-Request-ID", "User-Agent"])
    exclude_paths: List[str] = field(default_factory=lambda: ["/health", "/metrics"])
    custom_fields: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricsConfig:
    """Metrics configuration for Prometheus/OpenTelemetry export.

    Attributes:
        enabled: Enable metrics export (default: True)
        exporter: Metrics exporter - "prometheus", "opentelemetry", "both" (default: "prometheus")
        prometheus_port: Prometheus metrics port (default: 9090)
        prometheus_path: Prometheus metrics path (default: "/metrics")
        opentelemetry_endpoint: OpenTelemetry collector endpoint
        include_histograms: Include request duration histograms (default: True)
        include_counters: Include request/error counters (default: True)
        custom_labels: Additional labels for metrics
    """

    enabled: bool = True
    exporter: str = "prometheus"  # prometheus, opentelemetry, both
    prometheus_port: int = 9090
    prometheus_path: str = "/metrics"
    opentelemetry_endpoint: str = ""
    include_histograms: bool = True
    include_counters: bool = True
    custom_labels: Dict[str, str] = field(default_factory=dict)


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
class AzureAPIMGlobalConfig:
    """Azure API Management global configuration.

    Global configuration for Azure APIM deployment, including
    resource group, service name, location, and SKU.

    Attributes:
        resource_group: Azure resource group name
        apim_service_name: APIM service instance name
        location: Azure region (e.g., "westeurope", "eastus")
        sku: APIM pricing tier (Developer, Basic, Standard, Premium)

    Example:
        >>> global_config = AzureAPIMGlobalConfig(
        ...     resource_group="my-resource-group",
        ...     apim_service_name="my-apim-service",
        ...     location="westeurope",
        ...     sku="Developer"
        ... )
        >>> global_config.location
        'westeurope'
    """

    resource_group: str = "gal-resource-group"
    apim_service_name: str = "gal-apim-service"
    location: str = "westeurope"
    sku: str = "Developer"


@dataclass
class AzureAPIMConfig:
    """Azure API Management specific configuration.

    Configuration for Azure API Management provider, including
    product settings, API versioning, and subscription keys.

    Attributes:
        product_name: APIM Product name (default: "GAL-Product")
        product_description: Product description
        product_published: Whether product is published (default: True)
        product_subscription_required: Require subscription keys (default: True)
        api_revision: API revision number (default: "1")
        api_version: API version identifier (e.g., "v1")
        api_version_set_id: API version set ID for grouping
        openapi_export: Generate OpenAPI spec (default: True)
        openapi_version: OpenAPI specification version (default: "3.0.0")
        subscription_keys_required: Require subscription keys (default: True)
        rate_limit_calls: Maximum calls in renewal period (default: 100)
        rate_limit_renewal_period: Period in seconds (default: 60)

    Example:
        >>> apim_config = AzureAPIMConfig(
        ...     product_name="UserAPI-Product",
        ...     api_revision="1",
        ...     api_version="v1",
        ...     rate_limit_calls=1000
        ... )
        >>> apim_config.product_name
        'UserAPI-Product'
    """

    product_name: str = "GAL-Product"
    product_description: str = "API Product managed by GAL"
    product_published: bool = True
    product_subscription_required: bool = True
    api_revision: str = "1"
    api_version: Optional[str] = None
    api_version_set_id: Optional[str] = None
    openapi_export: bool = True
    openapi_version: str = "3.0.0"
    subscription_keys_required: bool = True
    rate_limit_calls: int = 100
    rate_limit_renewal_period: int = 60


@dataclass
class AWSAPIGatewayConfig:
    """AWS API Gateway specific configuration.

    Configuration for AWS API Gateway REST API provider, including
    integration types, authorizers, and stage settings.

    Attributes:
        api_name: API Gateway API name (default: "GAL-API")
        api_description: API description
        endpoint_type: Endpoint type - REGIONAL, EDGE, or PRIVATE (default: "REGIONAL")
        stage_name: Deployment stage name (default: "prod")
        stage_description: Stage description
        integration_type: Backend integration type (default: "HTTP_PROXY")
        integration_timeout_ms: Integration timeout in milliseconds (default: 29000, max: 29000)
        lambda_function_arn: Lambda function ARN (for AWS_PROXY integration)
        lambda_invoke_role_arn: IAM role ARN for Lambda invocation
        authorizer_type: Authorizer type - "lambda", "cognito", "iam", or None
        lambda_authorizer_arn: Lambda authorizer function ARN
        lambda_authorizer_ttl: Authorizer result TTL in seconds (default: 300)
        cognito_user_pool_arns: List of Cognito User Pool ARNs
        api_key_required: Require API key for requests (default: False)
        api_key_source: API key source - HEADER or AUTHORIZER (default: "HEADER")
        cors_enabled: Enable CORS (default: True)
        cors_allow_origins: Allowed origins for CORS (default: ["*"])
        cors_allow_methods: Allowed HTTP methods for CORS
        cors_allow_headers: Allowed headers for CORS
        openapi_version: OpenAPI specification version (default: "3.0.1")
        export_format: Export format - oas30 (OpenAPI 3.0) (default: "oas30")

    Example:
        >>> aws_config = AWSAPIGatewayConfig(
        ...     api_name="UserAPI",
        ...     stage_name="prod",
        ...     integration_type="HTTP_PROXY",
        ...     authorizer_type="cognito"
        ... )
        >>> aws_config.endpoint_type
        'REGIONAL'
    """

    # API Configuration
    api_name: str = "GAL-API"
    api_description: str = "API managed by GAL"
    endpoint_type: str = "REGIONAL"  # REGIONAL, EDGE, PRIVATE

    # Stage Configuration
    stage_name: str = "prod"
    stage_description: str = ""

    # Integration Configuration
    integration_type: str = "HTTP_PROXY"  # HTTP_PROXY, AWS_PROXY, MOCK
    integration_timeout_ms: int = 29000  # Max 29 seconds

    # Lambda Integration (if integration_type == "AWS_PROXY")
    lambda_function_arn: Optional[str] = None
    lambda_invoke_role_arn: Optional[str] = None

    # Authorization
    authorizer_type: Optional[str] = None  # "lambda", "cognito", "iam"
    lambda_authorizer_arn: Optional[str] = None
    lambda_authorizer_ttl: int = 300  # seconds
    cognito_user_pool_arns: List[str] = field(default_factory=list)

    # API Keys
    api_key_required: bool = False
    api_key_source: str = "HEADER"  # HEADER, AUTHORIZER

    # CORS
    cors_enabled: bool = True
    cors_allow_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_allow_methods: List[str] = field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    cors_allow_headers: List[str] = field(
        default_factory=lambda: ["Content-Type", "Authorization", "X-Api-Key"]
    )

    # OpenAPI Export
    openapi_version: str = "3.0.1"
    export_format: str = "oas30"  # oas30 (OpenAPI 3.0)

    # Request Mirroring (not natively supported)
    mirroring_workaround: str = ""  # "lambda_edge", "cloudwatch_logs", or "" (disabled)
    mirroring_lambda_edge_arn: str = ""  # Lambda@Edge function ARN for mirroring
    mirroring_cloudwatch_log_group: str = ""  # CloudWatch Logs group name


@dataclass
class GCPAPIGatewayConfig:
    """GCP API Gateway specific configuration.

    Configuration for Google Cloud API Gateway provider (lightweight implementation).
    Supports OpenAPI 2.0 (Swagger) with x-google-backend extensions.

    Attributes:
        api_id: API Gateway API ID (default: "gal-api")
        api_display_name: Display name for the API
        api_config_id: API Config ID (default: "gal-api-config")
        gateway_id: Gateway ID (default: "gal-gateway")
        project_id: GCP Project ID
        region: GCP region for gateway deployment (default: "us-central1")
        backend_address: Backend service address (URL)
        backend_protocol: Backend protocol - http or https (default: "https")
        backend_path_translation: Path translation - APPEND_PATH_TO_ADDRESS or CONSTANT_ADDRESS (default: "APPEND_PATH_TO_ADDRESS")
        backend_deadline: Backend request deadline in seconds (default: 30.0)
        backend_disable_auth: Disable backend authentication (default: False)
        backend_jwt_audience: JWT audience for backend authentication
        jwt_issuer: JWT token issuer URL (for x-google-issuer)
        jwt_jwks_uri: JWKS URI for JWT validation (for x-google-jwks_uri)
        jwt_audiences: List of valid JWT audiences
        service_account_email: Service account email for backend authentication
        cors_enabled: Enable CORS (default: True)
        cors_allow_origins: Allowed origins for CORS (default: ["*"])
        cors_allow_methods: Allowed HTTP methods for CORS
        cors_allow_headers: Allowed headers for CORS
        cors_expose_headers: Exposed headers for CORS
        cors_max_age: CORS preflight cache duration in seconds (default: 3600)
        openapi_version: OpenAPI specification version (default: "2.0" - Swagger)

    Example:
        >>> gcp_config = GCPAPIGatewayConfig(
        ...     api_id="user-api",
        ...     project_id="my-gcp-project",
        ...     region="us-central1",
        ...     backend_address="https://backend.example.com",
        ...     jwt_issuer="https://accounts.google.com"
        ... )
        >>> gcp_config.openapi_version
        '2.0'

    Note:
        GCP API Gateway only supports OpenAPI 2.0 (Swagger), not OpenAPI 3.0.
    """

    # API Configuration
    api_id: str = "gal-api"
    api_display_name: str = "GAL API"
    api_config_id: str = "gal-api-config"
    gateway_id: str = "gal-gateway"

    # GCP Project & Region
    project_id: str = ""
    region: str = "us-central1"

    # Backend Configuration (x-google-backend)
    backend_address: str = ""
    backend_protocol: str = "https"  # http, https
    backend_path_translation: str = (
        "APPEND_PATH_TO_ADDRESS"  # APPEND_PATH_TO_ADDRESS, CONSTANT_ADDRESS
    )
    backend_deadline: float = 30.0  # seconds
    backend_disable_auth: bool = False
    backend_jwt_audience: str = ""

    # JWT Authentication (x-google-issuer, x-google-jwks_uri)
    jwt_issuer: str = ""
    jwt_jwks_uri: str = ""
    jwt_audiences: List[str] = field(default_factory=list)

    # Service Account
    service_account_email: str = ""

    # CORS Configuration
    cors_enabled: bool = True
    cors_allow_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_allow_methods: List[str] = field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    cors_allow_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Authorization"])
    cors_expose_headers: List[str] = field(default_factory=list)
    cors_max_age: int = 3600  # seconds

    # OpenAPI Export (Swagger 2.0 only!)
    openapi_version: str = "2.0"

    # Request Mirroring (not natively supported)
    mirroring_workaround: str = ""  # "cloud_functions", "cloud_run", or "" (disabled)
    mirroring_cloud_function_url: str = ""  # Cloud Function URL for mirroring
    mirroring_cloud_run_url: str = ""  # Cloud Run service URL for mirroring


@dataclass
class KongGlobalConfig:
    """Kong API Gateway specific configuration.

    Configuration for Kong Gateway provider, supporting both Open Source
    and Enterprise editions with different feature sets.

    Attributes:
        version: Kong version - "OpenSource" or "Enterprise" (default: "OpenSource")
                 - OpenSource: Only native Kong features (plugins require external installation)
                 - Enterprise: Full access to Kong Enterprise plugins (request-mirror, etc.)
        admin_api_url: Kong Admin API URL (default: "http://localhost:8001")
        control_plane_url: Kong Control Plane URL for Enterprise deployments
        workspace: Kong Enterprise workspace name (default: "default")

    Example:
        >>> kong_config = KongGlobalConfig(
        ...     version="Enterprise",
        ...     admin_api_url="http://kong-admin:8001",
        ...     workspace="production"
        ... )
        >>> kong_config.version
        'Enterprise'
    """

    version: str = "OpenSource"  # or "Enterprise"
    admin_api_url: str = "http://localhost:8001"
    control_plane_url: str = ""
    workspace: str = "default"


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
        azure_apim: Optional Azure API Management specific configuration

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
    azure_apim: Optional[AzureAPIMConfig] = None


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
class ProtoDescriptor:
    """Protobuf descriptor configuration for gRPC services.

    Defines how to load Protocol Buffer (.proto) files that describe
    gRPC service interfaces and message types.

    Attributes:
        name: Unique identifier for this descriptor (used as reference)
        source: Source type - "file", "inline", or "url"
        path: File path to .proto or .desc file (when source="file")
        content: Inline proto definition (when source="inline")
        url: Download URL for proto file (when source="url")

    Examples:
        >>> # File-based descriptor
        >>> desc = ProtoDescriptor(
        ...     name="user_service",
        ...     source="file",
        ...     path="/etc/gal/protos/user.desc"
        ... )

        >>> # Inline descriptor
        >>> desc = ProtoDescriptor(
        ...     name="order_service",
        ...     source="inline",
        ...     content='syntax = "proto3"; package order.v1;'
        ... )

        >>> # URL-based descriptor
        >>> desc = ProtoDescriptor(
        ...     name="payment_service",
        ...     source="url",
        ...     url="https://api.example.com/protos/payment.proto"
        ... )

    Validation:
        - name: Required, non-empty
        - source: Must be "file", "inline", or "url"
        - path: Required if source="file", must exist
        - content: Required if source="inline"
        - url: Required if source="url", must be valid HTTP(S) URL
    """

    name: str
    source: str  # "file", "inline", "url"
    path: str = ""
    content: str = ""
    url: str = ""

    def __post_init__(self):
        """Validate proto descriptor configuration."""
        if not self.name:
            raise ValueError("ProtoDescriptor.name is required")

        if self.source not in ["file", "inline", "url"]:
            raise ValueError(f"Invalid source: {self.source}. Must be 'file', 'inline', or 'url'")

        if self.source == "file" and not self.path:
            raise ValueError("ProtoDescriptor.path is required when source='file'")

        if self.source == "inline" and not self.content:
            raise ValueError("ProtoDescriptor.content is required when source='inline'")

        if self.source == "url" and not self.url:
            raise ValueError("ProtoDescriptor.url is required when source='url'")


@dataclass
class GrpcTransformation:
    """gRPC-specific transformation configuration.

    Defines transformations to apply to gRPC request and response messages
    using Protocol Buffer descriptors.

    Attributes:
        enabled: Enable/disable gRPC transformation (default: True)
        proto_descriptor: Reference to ProtoDescriptor name
        package: Protobuf package name (e.g., "user.v1")
        service: Service name from proto (e.g., "UserService")
        request_type: Request message type (e.g., "CreateUserRequest")
        response_type: Response message type (e.g., "CreateUserResponse")
        request_transform: Request transformation rules
        response_transform: Response transformation rules

    Examples:
        >>> transform = GrpcTransformation(
        ...     enabled=True,
        ...     proto_descriptor="user_service",
        ...     package="user.v1",
        ...     service="UserService",
        ...     request_type="CreateUserRequest",
        ...     response_type="CreateUserResponse",
        ...     request_transform=RequestBodyTransformation(
        ...         add_fields={"trace_id": "{{uuid}}"}
        ...     )
        ... )

    Validation:
        - proto_descriptor: Required when enabled=True
        - package: Required when enabled=True
        - service: Required when enabled=True
        - request_type: Required when enabled=True
        - response_type: Required when enabled=True
    """

    enabled: bool = True
    proto_descriptor: str = ""
    package: str = ""
    service: str = ""
    request_type: str = ""
    response_type: str = ""
    request_transform: Optional["RequestBodyTransformation"] = None
    response_transform: Optional["ResponseBodyTransformation"] = None

    def __post_init__(self):
        """Validate gRPC transformation configuration."""
        if self.enabled:
            if not self.proto_descriptor:
                raise ValueError("proto_descriptor is required when enabled=True")
            if not self.package:
                raise ValueError("package is required when enabled=True")
            if not self.service:
                raise ValueError("service is required when enabled=True")
            if not self.request_type:
                raise ValueError("request_type is required when enabled=True")
            if not self.response_type:
                raise ValueError("response_type is required when enabled=True")


@dataclass
class HeaderMatchRule:
    """Header-based routing rule for traffic splitting.

    Routes traffic based on HTTP header values.

    Attributes:
        header_name: HTTP header name to match (e.g., "X-Version", "X-User-Segment")
        header_value: Header value to match (exact match)
        target_name: Name of the upstream target to route to when matched

    Example:
        >>> rule = HeaderMatchRule(
        ...     header_name="X-Version",
        ...     header_value="beta",
        ...     target_name="backend_beta"
        ... )
        >>> rule.header_name
        'X-Version'
    """

    header_name: str
    header_value: str
    target_name: str


@dataclass
class CookieMatchRule:
    """Cookie-based routing rule for traffic splitting.

    Routes traffic based on cookie values for user-based canary testing.

    Attributes:
        cookie_name: Cookie name to match (e.g., "canary_user", "beta_tester")
        cookie_value: Cookie value to match (exact match)
        target_name: Name of the upstream target to route to when matched

    Example:
        >>> rule = CookieMatchRule(
            cookie_name="canary_user",
            cookie_value="true",
            target_name="canary_backend"
        ... )
        >>> rule.cookie_name
        'canary_user'
    """

    cookie_name: str
    cookie_value: str
    target_name: str


@dataclass
class SplitTarget:
    """Weighted traffic split target configuration.

    Defines a backend target with its traffic weight for A/B testing and canary deployments.

    Attributes:
        name: Unique identifier for this target
        weight: Traffic weight (0-100). Weights across all targets should sum to 100.
        upstream: Backend target configuration
        description: Optional human-readable description

    Example:
        >>> target = SplitTarget(
        ...     name="version_a",
        ...     weight=70,
        ...     upstream=UpstreamTarget(host="api-v1.internal", port=8080)
        ... )
        >>> target.weight
        70
    """

    name: str
    weight: int
    upstream: UpstreamTarget
    description: Optional[str] = None

    def __post_init__(self):
        """Validate split target configuration."""
        if not 0 <= self.weight <= 100:
            raise ValueError(f"Weight must be between 0 and 100, got {self.weight}")


@dataclass
class RoutingRules:
    """Advanced routing rules for traffic splitting.

    Combines header-based and cookie-based routing rules.
    Rules are evaluated in order: header rules first, then cookie rules.

    Attributes:
        header_rules: List of header-based routing rules
        cookie_rules: List of cookie-based routing rules

    Example:
        >>> rules = RoutingRules(
        ...     header_rules=[
        ...         HeaderMatchRule("X-Version", "beta", "backend_beta")
        ...     ],
        ...     cookie_rules=[
        ...         CookieMatchRule("canary_user", "true", "canary_backend")
        ...     ]
        ... )
        >>> len(rules.header_rules)
        1
    """

    header_rules: List[HeaderMatchRule] = field(default_factory=list)
    cookie_rules: List[CookieMatchRule] = field(default_factory=list)


@dataclass
class TrafficSplitConfig:
    """Traffic splitting configuration for A/B testing and canary deployments.

    Enables weight-based traffic distribution and rule-based routing across
    multiple backend targets.

    Attributes:
        enabled: Whether traffic splitting is enabled
        targets: List of weighted backend targets
        routing_rules: Optional header/cookie-based routing rules
        fallback_target: Optional fallback target name if no rules match

    Example (Weight-based):
        >>> config = TrafficSplitConfig(
        ...     enabled=True,
        ...     targets=[
        ...         SplitTarget("stable", 90, UpstreamTarget("api-v1", 8080)),
        ...         SplitTarget("canary", 10, UpstreamTarget("api-v2", 8080))
        ...     ]
        ... )
        >>> sum(t.weight for t in config.targets)
        100

    Example (Header-based):
        >>> config = TrafficSplitConfig(
        ...     enabled=True,
        ...     targets=[
        ...         SplitTarget("stable", 100, UpstreamTarget("api-v1", 8080)),
        ...         SplitTarget("beta", 0, UpstreamTarget("api-v2-beta", 8080))
        ...     ],
        ...     routing_rules=RoutingRules(
        ...         header_rules=[HeaderMatchRule("X-Version", "beta", "beta")]
        ...     ),
        ...     fallback_target="stable"
        ... )
    """

    enabled: bool = False
    targets: List[SplitTarget] = field(default_factory=list)
    routing_rules: Optional[RoutingRules] = None
    fallback_target: Optional[str] = None

    def __post_init__(self):
        """Validate traffic split configuration."""
        if self.enabled:
            if not self.targets:
                raise ValueError("At least one target is required when enabled=True")

            # Validate total weight sums to 100 (or 0 for rule-based routing)
            total_weight = sum(t.weight for t in self.targets)
            has_rules = self.routing_rules and (
                self.routing_rules.header_rules or self.routing_rules.cookie_rules
            )

            if not has_rules and total_weight != 100:
                raise ValueError(
                    f"Total weight must sum to 100 for weight-based routing, got {total_weight}"
                )

            # Validate unique target names
            names = [t.name for t in self.targets]
            if len(names) != len(set(names)):
                raise ValueError("Target names must be unique")

            # Validate fallback target exists
            if self.fallback_target and self.fallback_target not in names:
                raise ValueError(f"Fallback target '{self.fallback_target}' not found in targets")


@dataclass
class MirrorTarget:
    """Shadow backend configuration for request mirroring.

    Defines a mirror/shadow target that receives duplicated requests
    for testing, analysis, or performance validation without affecting
    the primary response.

    Attributes:
        name: Unique identifier for the mirror target
        upstream: Backend server configuration (host, port, scheme)
        sample_percentage: Percentage of requests to mirror (0-100, default: 100)
        timeout: Timeout for mirror requests (default: "5s")
        headers: Optional additional headers to inject (e.g., X-Mirror: true)

    Example:
        >>> target = MirrorTarget(
        ...     name="shadow-v2",
        ...     upstream=UpstreamTarget("shadow-api-v2", 8080),
        ...     sample_percentage=50.0,
        ...     timeout="3s",
        ...     headers={"X-Mirror": "true", "X-Shadow-Version": "v2"}
        ... )
        >>> target.sample_percentage
        50.0
    """

    name: str
    upstream: UpstreamTarget
    sample_percentage: float = 100.0
    timeout: str = "5s"
    headers: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Validate mirror target configuration."""
        if not (0 <= self.sample_percentage <= 100):
            raise ValueError(
                f"sample_percentage must be between 0 and 100, got {self.sample_percentage}"
            )


@dataclass
class MirroringConfig:
    """Request mirroring/shadowing configuration.

    Enables shadow traffic by duplicating requests to mirror targets
    while returning responses from the primary backend. Useful for:
    - Production testing without user impact
    - Performance validation under real load
    - Bug detection before full rollout
    - Data collection from new versions

    Attributes:
        enabled: Whether request mirroring is enabled
        targets: List of mirror/shadow backend targets
        mirror_request_body: Whether to copy request body (default: True)
        mirror_headers: Whether to copy request headers (default: True)

    Example (Simple Mirroring):
        >>> config = MirroringConfig(
        ...     enabled=True,
        ...     targets=[
        ...         MirrorTarget("shadow", UpstreamTarget("shadow-api", 8080))
        ...     ]
        ... )
        >>> config.targets[0].sample_percentage
        100.0

    Example (Sampled Mirroring):
        >>> config = MirroringConfig(
        ...     enabled=True,
        ...     targets=[
        ...         MirrorTarget(
        ...             "shadow-v2",
        ...             UpstreamTarget("shadow-api-v2", 8080),
        ...             sample_percentage=10.0
        ...         )
        ...     ],
        ...     mirror_headers=True,
        ...     mirror_request_body=True
        ... )
        >>> config.targets[0].sample_percentage
        10.0

    Example (Multiple Shadows):
        >>> config = MirroringConfig(
        ...     enabled=True,
        ...     targets=[
        ...         MirrorTarget("shadow-v2", UpstreamTarget("api-v2", 8080), sample_percentage=50.0),
        ...         MirrorTarget("shadow-v3", UpstreamTarget("api-v3", 8080), sample_percentage=10.0)
        ...     ]
        ... )
        >>> len(config.targets)
        2
    """

    enabled: bool = False
    targets: List[MirrorTarget] = field(default_factory=list)
    mirror_request_body: bool = True
    mirror_headers: bool = True

    def __post_init__(self):
        """Validate mirroring configuration."""
        if self.enabled:
            if not self.targets:
                raise ValueError("At least one mirror target is required when enabled=True")

            # Validate unique target names
            names = [t.name for t in self.targets]
            if len(names) != len(set(names)):
                raise ValueError("Mirror target names must be unique")


@dataclass
class AdvancedHeaderMatchRule:
    """Advanced header-based routing rule with multiple match types.

    Routes traffic based on HTTP header values with flexible matching options.

    Attributes:
        header_name: HTTP header name to match (e.g., "X-API-Version", "User-Agent")
        match_type: Matching strategy ("exact", "prefix", "regex", "contains")
        header_value: Header value or pattern to match
        target_name: Name of the upstream target to route to when matched

    Example:
        >>> rule = AdvancedHeaderMatchRule(
        ...     header_name="User-Agent",
        ...     match_type="contains",
        ...     header_value="Mobile",
        ...     target_name="mobile_backend"
        ... )
    """

    header_name: str
    match_type: str = "exact"  # "exact", "prefix", "regex", "contains"
    header_value: str = ""
    target_name: str = ""

    def __post_init__(self):
        """Validate header match rule."""
        valid_match_types = ["exact", "prefix", "regex", "contains"]
        if self.match_type not in valid_match_types:
            raise ValueError(
                f"match_type must be one of {valid_match_types}, got {self.match_type}"
            )


@dataclass
class JWTClaimMatchRule:
    """JWT Claims-based routing rule.

    Routes traffic based on JWT token claims for role-based or tenant-based routing.

    Attributes:
        claim_name: JWT claim name to match (e.g., "role", "tenant_id", "scope")
        claim_value: Claim value or pattern to match
        match_type: Matching strategy ("exact", "contains", "regex")
        target_name: Name of the upstream target to route to when matched

    Example:
        >>> rule = JWTClaimMatchRule(
        ...     claim_name="role",
        ...     claim_value="admin",
        ...     match_type="exact",
        ...     target_name="admin_backend"
        ... )
    """

    claim_name: str
    claim_value: str
    match_type: str = "exact"  # "exact", "contains", "regex"
    target_name: str = ""

    def __post_init__(self):
        """Validate JWT claim match rule."""
        valid_match_types = ["exact", "contains", "regex"]
        if self.match_type not in valid_match_types:
            raise ValueError(
                f"match_type must be one of {valid_match_types}, got {self.match_type}"
            )


@dataclass
class GeoMatchRule:
    """Geo-location based routing rule.

    Routes traffic based on client geographic location for data residency
    or region-specific services.

    Attributes:
        match_type: Geographic matching level ("country", "region", "continent")
        match_value: Location code to match (e.g., "DE", "eu-west-1", "EU")
        target_name: Name of the upstream target to route to when matched

    Example:
        >>> rule = GeoMatchRule(
        ...     match_type="country",
        ...     match_value="DE",
        ...     target_name="eu_backend"
        ... )
    """

    match_type: str  # "country", "region", "continent"
    match_value: str
    target_name: str = ""

    def __post_init__(self):
        """Validate geo match rule."""
        valid_match_types = ["country", "region", "continent"]
        if self.match_type not in valid_match_types:
            raise ValueError(
                f"match_type must be one of {valid_match_types}, got {self.match_type}"
            )


@dataclass
class QueryParamMatchRule:
    """Query parameter-based routing rule.

    Routes traffic based on URL query parameters for feature flags
    or API versioning.

    Attributes:
        param_name: Query parameter name to match (e.g., "version", "beta")
        param_value: Parameter value or pattern to match
        match_type: Matching strategy ("exact", "exists", "regex")
        target_name: Name of the upstream target to route to when matched

    Example:
        >>> rule = QueryParamMatchRule(
        ...     param_name="version",
        ...     param_value="2",
        ...     match_type="exact",
        ...     target_name="v2_backend"
        ... )
    """

    param_name: str
    param_value: str
    match_type: str = "exact"  # "exact", "exists", "regex"
    target_name: str = ""

    def __post_init__(self):
        """Validate query param match rule."""
        valid_match_types = ["exact", "exists", "regex"]
        if self.match_type not in valid_match_types:
            raise ValueError(
                f"match_type must be one of {valid_match_types}, got {self.match_type}"
            )


@dataclass
class JWTFilterConfig:
    """JWT Authentication Filter configuration for Envoy.

    Configures JWT token validation and claim extraction for advanced routing.

    Attributes:
        enabled: Whether JWT filter is enabled
        issuer: JWT token issuer (iss claim)
        audience: JWT token audience (aud claim)
        jwks_uri: JWKS endpoint URL for key discovery
        jwks_cluster: Cluster name for JWKS fetching
        payload_in_metadata: Metadata key to store JWT payload
        forward_payload_header: Header name to forward JWT payload

    Example:
        >>> jwt_config = JWTFilterConfig(
        ...     enabled=True,
        ...     issuer="https://jwks-service",
        ...     audience="x-gal-test",
        ...     jwks_uri="http://jwks-service:8080/.well-known/jwks.json",
        ...     jwks_cluster="jwks_cluster"
        ... )
    """

    enabled: bool = False
    issuer: str = ""
    audience: str = ""
    jwks_uri: str = ""
    jwks_cluster: str = "jwks_cluster"
    payload_in_metadata: str = "jwt_payload"
    forward_payload_header: str = "X-JWT-Payload"


@dataclass
class GeoIPFilterConfig:
    """GeoIP Filter configuration for Envoy ext_authz.

    Configures GeoIP lookup service for geographic routing.

    Attributes:
        enabled: Whether GeoIP filter is enabled
        geoip_service_uri: GeoIP service URI (HTTP or gRPC)
        geoip_cluster: Cluster name for GeoIP service
        timeout_ms: Timeout for GeoIP lookup in milliseconds
        failure_mode_allow: Allow traffic if GeoIP service fails

    Example:
        >>> geoip_config = GeoIPFilterConfig(
        ...     enabled=True,
        ...     geoip_service_uri="http://geoip-service:8080/check",
        ...     geoip_cluster="geoip_service"
        ... )
    """

    enabled: bool = False
    geoip_service_uri: str = ""
    geoip_cluster: str = "geoip_service"
    timeout_ms: int = 500
    failure_mode_allow: bool = True


@dataclass
class AdvancedRoutingTarget:
    """Target backend for advanced routing.

    Defines a named backend target that can be referenced by routing rules.

    Attributes:
        name: Unique identifier for the routing target
        upstream: Backend service configuration
        description: Optional description of the target

    Example:
        >>> target = AdvancedRoutingTarget(
        ...     name="v2_backend",
        ...     upstream=UpstreamTarget("api-v2", 8080),
        ...     description="Version 2 API backend"
        ... )
    """

    name: str
    upstream: UpstreamTarget
    description: Optional[str] = None


@dataclass
class AdvancedRoutingConfig:
    """Advanced routing configuration for complex traffic management.

    Enables sophisticated routing based on headers, JWT claims, geographic location,
    and query parameters. Useful for:
    - API versioning via headers or query parameters
    - Role-based routing using JWT claims
    - Geographic routing for data residency
    - A/B testing and feature flags
    - Multi-tenant routing

    Provider Support:
        - Envoy: Full support via route matching and Lua scripting
        - Nginx: Full support via map, geo, and OpenResty Lua
        - Kong: Full support via Route by Header and custom plugins
        - APISIX: Full support via vars and serverless functions
        - HAProxy: Full support via ACL routing
        - Traefik: Full support via rule matchers

    Attributes:
        enabled: Whether advanced routing is enabled
        header_rules: List of header-based routing rules
        jwt_claim_rules: List of JWT claim-based routing rules
        geo_rules: List of geographic routing rules
        query_param_rules: List of query parameter routing rules
        fallback_target: Optional fallback target if no rules match
        evaluation_strategy: Rule evaluation strategy ("first_match" or "all_match")

    Example (Header-based API versioning):
        >>> config = AdvancedRoutingConfig(
        ...     enabled=True,
        ...     header_rules=[
        ...         AdvancedHeaderMatchRule("X-API-Version", "exact", "v2", "v2_backend")
        ...     ],
        ...     fallback_target="v1_backend"
        ... )

    Example (JWT role-based routing):
        >>> config = AdvancedRoutingConfig(
        ...     enabled=True,
        ...     jwt_claim_rules=[
        ...         JWTClaimMatchRule("role", "admin", "exact", "admin_backend")
        ...     ]
        ... )
    """

    enabled: bool = True
    header_rules: List[AdvancedHeaderMatchRule] = field(default_factory=list)
    jwt_claim_rules: List[JWTClaimMatchRule] = field(default_factory=list)
    geo_rules: List[GeoMatchRule] = field(default_factory=list)
    query_param_rules: List[QueryParamMatchRule] = field(default_factory=list)
    fallback_target: Optional[str] = None
    evaluation_strategy: str = "first_match"  # "first_match", "all_match"

    # Filter configurations (optional - auto-enabled if rules exist)
    jwt_filter: Optional[JWTFilterConfig] = None
    geoip_filter: Optional[GeoIPFilterConfig] = None

    def __post_init__(self):
        """Validate advanced routing configuration."""
        valid_strategies = ["first_match", "all_match"]
        if self.evaluation_strategy not in valid_strategies:
            raise ValueError(
                f"evaluation_strategy must be one of {valid_strategies}, "
                f"got {self.evaluation_strategy}"
            )

        # Collect all target names referenced in rules
        referenced_targets = set()
        for rule in self.header_rules:
            referenced_targets.add(rule.target_name)
        for rule in self.jwt_claim_rules:
            referenced_targets.add(rule.target_name)
        for rule in self.geo_rules:
            referenced_targets.add(rule.target_name)
        for rule in self.query_param_rules:
            referenced_targets.add(rule.target_name)

        # Note: Actual validation of target existence happens in Route.__post_init__


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
        proto_descriptors: List of Protocol Buffer descriptors for gRPC (default: empty list)

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
    proto_descriptors: List[ProtoDescriptor] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, filepath: str) -> "Config":
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
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {filepath}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML syntax in {filepath}: {e}")
            raise

        # Parse global config
        global_data = data.get("global", {})

        # Parse provider-specific global configs
        azure_apim_config = None
        if "azure_apim" in global_data:
            azure_apim_config = AzureAPIMGlobalConfig(**global_data["azure_apim"])
            global_data["azure_apim"] = azure_apim_config

        aws_config = None
        if "aws_apigateway" in global_data:
            aws_config = AWSAPIGatewayConfig(**global_data["aws_apigateway"])
            global_data["aws_apigateway"] = aws_config

        gcp_config = None
        if "gcp_apigateway" in global_data:
            gcp_config = GCPAPIGatewayConfig(**global_data["gcp_apigateway"])
            global_data["gcp_apigateway"] = gcp_config

        kong_config = None
        if "kong" in global_data:
            kong_config = KongGlobalConfig(**global_data["kong"])
            global_data["kong"] = kong_config

        global_config = GlobalConfig(**global_data)
        logger.debug(f"Parsed global config: {global_config.host}:{global_config.port}")

        # Parse services
        services = []
        for svc_data in data.get("services", []):
            # Parse upstream with targets
            upstream_data = svc_data["upstream"]
            upstream_targets = None
            if "targets" in upstream_data:
                upstream_targets = [UpstreamTarget(**t) for t in upstream_data["targets"]]
                upstream_data["targets"] = upstream_targets

            upstream = Upstream(**upstream_data)

            # Parse routes with optional rate limiting, authentication, headers, and CORS
            routes = []
            for route_data in svc_data["routes"]:
                rate_limit = None
                if "rate_limit" in route_data:
                    rate_limit = RateLimitConfig(**route_data["rate_limit"])

                authentication = None
                if "authentication" in route_data:
                    auth_data = route_data["authentication"]
                    auth_type = auth_data.get("type", "api_key")

                    # Parse type-specific configuration
                    basic_auth = None
                    api_key = None
                    jwt = None

                    if auth_type == "basic" and "basic_auth" in auth_data:
                        basic_auth = BasicAuthConfig(**auth_data["basic_auth"])
                    elif auth_type == "api_key" and "api_key" in auth_data:
                        api_key = ApiKeyConfig(**auth_data["api_key"])
                    elif auth_type == "jwt" and "jwt" in auth_data:
                        jwt = JwtConfig(**auth_data["jwt"])

                    authentication = AuthenticationConfig(
                        enabled=auth_data.get("enabled", True),
                        type=auth_type,
                        basic_auth=basic_auth,
                        api_key=api_key,
                        jwt=jwt,
                        fail_status=auth_data.get("fail_status", 401),
                        fail_message=auth_data.get("fail_message", "Unauthorized"),
                    )

                # Parse route-level headers
                route_headers = None
                if "headers" in route_data:
                    route_headers = HeaderManipulation(**route_data["headers"])

                # Parse route-level CORS
                cors_policy = None
                if "cors" in route_data:
                    cors_policy = CORSPolicy(**route_data["cors"])

                # Parse route-level WebSocket
                websocket = None
                if "websocket" in route_data:
                    websocket = WebSocketConfig(**route_data["websocket"])

                # Parse route-level circuit breaker
                circuit_breaker = None
                if "circuit_breaker" in route_data:
                    circuit_breaker = CircuitBreakerConfig(**route_data["circuit_breaker"])

                # Parse route-level body transformation
                body_transformation = None
                if "body_transformation" in route_data:
                    bt_data = route_data["body_transformation"]
                    request_transform = None
                    if "request" in bt_data:
                        request_transform = RequestBodyTransformation(**bt_data["request"])

                    response_transform = None
                    if "response" in bt_data:
                        response_transform = ResponseBodyTransformation(**bt_data["response"])

                    body_transformation = BodyTransformationConfig(
                        enabled=bt_data.get("enabled", True),
                        request=request_transform,
                        response=response_transform,
                    )

                # Parse route-level timeout
                timeout = None
                if "timeout" in route_data:
                    timeout = TimeoutConfig(**route_data["timeout"])

                # Parse route-level retry
                retry = None
                if "retry" in route_data:
                    retry = RetryConfig(**route_data["retry"])

                # Parse route-level traffic split
                traffic_split = None
                if "traffic_split" in route_data:
                    ts_data = route_data["traffic_split"]

                    # Parse split targets
                    targets = []
                    for target_data in ts_data.get("targets", []):
                        upstream_target = UpstreamTarget(**target_data["upstream"])
                        split_target = SplitTarget(
                            name=target_data["name"],
                            weight=target_data["weight"],
                            upstream=upstream_target,
                            description=target_data.get("description"),
                        )
                        targets.append(split_target)

                    # Parse routing rules
                    routing_rules = None
                    if "routing_rules" in ts_data:
                        rules_data = ts_data["routing_rules"]
                        header_rules = [
                            HeaderMatchRule(**hr) for hr in rules_data.get("header_rules", [])
                        ]
                        cookie_rules = [
                            CookieMatchRule(**cr) for cr in rules_data.get("cookie_rules", [])
                        ]
                        routing_rules = RoutingRules(
                            header_rules=header_rules,
                            cookie_rules=cookie_rules,
                        )

                    traffic_split = TrafficSplitConfig(
                        enabled=ts_data.get("enabled", False),
                        targets=targets,
                        routing_rules=routing_rules,
                        fallback_target=ts_data.get("fallback_target"),
                    )

                # Parse mirroring
                mirroring = None
                if "mirroring" in route_data:
                    mir_data = route_data["mirroring"]

                    # Parse mirror targets
                    mirror_targets = []
                    for target_data in mir_data.get("targets", []):
                        upstream_target = UpstreamTarget(**target_data["upstream"])
                        mirror_target = MirrorTarget(
                            name=target_data["name"],
                            upstream=upstream_target,
                            sample_percentage=target_data.get("sample_percentage", 100.0),
                            timeout=target_data.get("timeout", "5s"),
                            headers=target_data.get("headers"),
                        )
                        mirror_targets.append(mirror_target)

                    mirroring = MirroringConfig(
                        enabled=mir_data.get("enabled", False),
                        targets=mirror_targets,
                        mirror_request_body=mir_data.get("mirror_request_body", True),
                        mirror_headers=mir_data.get("mirror_headers", True),
                    )

                # Parse advanced routing
                advanced_routing = None
                advanced_routing_targets = []
                if "advanced_routing" in route_data:
                    ar_data = route_data["advanced_routing"]

                    # Parse header rules
                    header_rules = []
                    for hr_data in ar_data.get("header_rules", []):
                        header_rule = AdvancedHeaderMatchRule(
                            header_name=hr_data["header_name"],
                            match_type=hr_data.get("match_type", "exact"),
                            header_value=hr_data.get("header_value", ""),
                            target_name=hr_data.get("target_name", ""),
                        )
                        header_rules.append(header_rule)

                    # Parse JWT claim rules
                    jwt_claim_rules = []
                    for jc_data in ar_data.get("jwt_claim_rules", []):
                        jwt_rule = JWTClaimMatchRule(
                            claim_name=jc_data["claim_name"],
                            claim_value=jc_data["claim_value"],
                            match_type=jc_data.get("match_type", "exact"),
                            target_name=jc_data.get("target_name", ""),
                        )
                        jwt_claim_rules.append(jwt_rule)

                    # Parse geo rules
                    geo_rules = []
                    for geo_data in ar_data.get("geo_rules", []):
                        geo_rule = GeoMatchRule(
                            match_type=geo_data["match_type"],
                            match_value=geo_data["match_value"],
                            target_name=geo_data.get("target_name", ""),
                        )
                        geo_rules.append(geo_rule)

                    # Parse query param rules
                    query_param_rules = []
                    for qp_data in ar_data.get("query_param_rules", []):
                        query_rule = QueryParamMatchRule(
                            param_name=qp_data["param_name"],
                            param_value=qp_data["param_value"],
                            match_type=qp_data.get("match_type", "exact"),
                            target_name=qp_data.get("target_name", ""),
                        )
                        query_param_rules.append(query_rule)

                    # Parse JWT filter config (optional)
                    jwt_filter = None
                    if "jwt_filter" in ar_data:
                        jwt_filter_data = ar_data["jwt_filter"]
                        jwt_filter = JWTFilterConfig(
                            enabled=jwt_filter_data.get("enabled", False),
                            issuer=jwt_filter_data.get("issuer", ""),
                            audience=jwt_filter_data.get("audience", ""),
                            jwks_uri=jwt_filter_data.get("jwks_uri", ""),
                            jwks_cluster=jwt_filter_data.get("jwks_cluster", "jwks_cluster"),
                            payload_in_metadata=jwt_filter_data.get(
                                "payload_in_metadata", "jwt_payload"
                            ),
                            forward_payload_header=jwt_filter_data.get(
                                "forward_payload_header", "X-JWT-Payload"
                            ),
                        )

                    # Parse GeoIP filter config (optional)
                    geoip_filter = None
                    if "geoip_filter" in ar_data:
                        geoip_filter_data = ar_data["geoip_filter"]
                        geoip_filter = GeoIPFilterConfig(
                            enabled=geoip_filter_data.get("enabled", False),
                            geoip_service_uri=geoip_filter_data.get("geoip_service_uri", ""),
                            geoip_cluster=geoip_filter_data.get("geoip_cluster", "geoip_service"),
                            timeout_ms=geoip_filter_data.get("timeout_ms", 500),
                            failure_mode_allow=geoip_filter_data.get("failure_mode_allow", True),
                        )

                    advanced_routing = AdvancedRoutingConfig(
                        enabled=ar_data.get("enabled", True),
                        header_rules=header_rules,
                        jwt_claim_rules=jwt_claim_rules,
                        geo_rules=geo_rules,
                        query_param_rules=query_param_rules,
                        fallback_target=ar_data.get("fallback_target"),
                        evaluation_strategy=ar_data.get("evaluation_strategy", "first_match"),
                        jwt_filter=jwt_filter,
                        geoip_filter=geoip_filter,
                    )

                # Parse advanced routing targets
                if "advanced_routing_targets" in route_data:
                    for target_data in route_data["advanced_routing_targets"]:
                        upstream_target = UpstreamTarget(**target_data["upstream"])
                        routing_target = AdvancedRoutingTarget(
                            name=target_data["name"],
                            upstream=upstream_target,
                            description=target_data.get("description"),
                        )
                        advanced_routing_targets.append(routing_target)

                route = Route(
                    path_prefix=route_data["path_prefix"],
                    methods=route_data.get("methods"),
                    rate_limit=rate_limit,
                    authentication=authentication,
                    headers=route_headers,
                    cors=cors_policy,
                    websocket=websocket,
                    circuit_breaker=circuit_breaker,
                    body_transformation=body_transformation,
                    timeout=timeout,
                    retry=retry,
                    traffic_split=traffic_split,
                    mirroring=mirroring,
                    advanced_routing=advanced_routing,
                    advanced_routing_targets=advanced_routing_targets,
                )
                routes.append(route)

            transformation = None
            if "transformation" in svc_data:
                trans_data = svc_data["transformation"]
                computed_fields = [
                    ComputedField(**cf) for cf in trans_data.get("computed_fields", [])
                ]
                validation = None
                if "validation" in trans_data:
                    validation = Validation(**trans_data["validation"])

                # Parse transformation headers
                trans_headers = None
                if "headers" in trans_data:
                    trans_headers = HeaderManipulation(**trans_data["headers"])

                transformation = Transformation(
                    enabled=trans_data.get("enabled", True),
                    defaults=trans_data.get("defaults", {}),
                    computed_fields=computed_fields,
                    metadata=trans_data.get("metadata", {}),
                    validation=validation,
                    headers=trans_headers,
                )

            service = Service(
                name=svc_data["name"],
                type=svc_data["type"],
                protocol=svc_data["protocol"],
                upstream=upstream,
                routes=routes,
                transformation=transformation,
            )
            services.append(service)

        # Parse plugins
        plugins = []
        for plugin_data in data.get("plugins", []):
            plugin = Plugin(**plugin_data)
            plugins.append(plugin)

        logger.debug(f"Parsed {len(services)} services and {len(plugins)} plugins")
        logger.info(f"Configuration loaded: provider={data['provider']}, services={len(services)}")

        return cls(
            version=data["version"],
            provider=data["provider"],
            global_config=global_config,
            services=services,
            plugins=plugins,
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
        return [s for s in self.services if s.type == "grpc"]

    def get_rest_services(self) -> List[Service]:
        """Get all REST services.

        Returns:
            List of services with type="rest"

        Example:
            >>> rest_services = config.get_rest_services()
            >>> all(s.type == "rest" for s in rest_services)
            True
        """
        return [s for s in self.services if s.type == "rest"]
