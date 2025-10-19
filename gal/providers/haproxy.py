"""
HAProxy Load Balancer Provider

Generates haproxy.cfg configuration for HAProxy Open Source.
Supports advanced load balancing, health checks, rate limiting, headers, ACLs.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from gal.config import (
    ActiveHealthCheck,
    Config,
    GlobalConfig,
    HeaderManipulation,
    HealthCheckConfig,
    LoadBalancerConfig,
    RateLimitConfig,
    Route,
    Service,
    Transformation,
    Upstream,
    UpstreamTarget,
)
from gal.parsers.haproxy_parser import HAProxyConfigParser, HAProxySection, SectionType
from gal.provider import Provider

logger = logging.getLogger(__name__)


class HAProxyProvider(Provider):
    """HAProxy Load Balancer Provider.

    Generates haproxy.cfg configuration for HAProxy Open Source.

    Supported Features:
    - Advanced Load Balancing (10+ algorithms)
    - Active & Passive Health Checks
    - Rate Limiting (stick-table based)
    - Basic Authentication
    - Header Manipulation (request/response)
    - ACLs (Access Control Lists)
    - Circuit Breaker (via server checks)
    - Sticky Sessions (cookie, source-based)
    - Connection Pooling

    Limitations:
    - JWT Auth requires Lua scripting
    - CORS requires custom header configuration
    """

    def name(self) -> str:
        """Return provider name."""
        return "haproxy"

    def validate(self, config: Config) -> bool:
        """Validate configuration for HAProxy-specific constraints.

        Args:
            config: Configuration to validate

        Returns:
            True if validation passes
        """
        warnings = []

        # Check for JWT authentication
        for service in config.services:
            for route in service.routes:
                if route.authentication and route.authentication.enabled:
                    if route.authentication.type == "jwt":
                        warnings.append(
                            f"Service '{service.name}' route '{route.path_prefix}': "
                            "JWT authentication requires Lua scripting in HAProxy. "
                            "Consider using external auth service or Kong/APISIX for native JWT support."
                        )

        if warnings:
            for warning in warnings:
                logger.warning(f"HAProxy validation: {warning}")

        logger.debug("HAProxy validation successful")
        return True

    def generate(self, config: Config) -> str:
        """Generate haproxy.cfg configuration."""
        output: List[str] = []

        # Global section
        output.extend(self._generate_global(config))
        output.append("")

        # Defaults section
        output.extend(self._generate_defaults(config))
        output.append("")

        # Frontend sections (one per service or combined)
        # We'll create a single frontend for simplicity, routing via ACLs
        output.extend(self._generate_frontend(config))
        output.append("")

        # Backend sections (one per service)
        for service in config.services:
            output.extend(self._generate_backend(service, config))
            output.append("")

        return "\n".join(output).rstrip() + "\n"

    def _generate_global(self, config: Config) -> List[str]:
        """Generate global section."""
        output = [
            "#---------------------------------------------------------------------",
            "# Global settings",
            "#---------------------------------------------------------------------",
            "global",
        ]

        # Logging configuration
        if config.global_config and config.global_config.logging:
            self._generate_haproxy_logging(config.global_config.logging, output)
        else:
            output.append("    log         127.0.0.1 local0")
            output.append("    log         127.0.0.1 local1 notice")

        output.extend(
            [
                "    chroot      /var/lib/haproxy",
                "    pidfile     /var/run/haproxy.pid",
                "    maxconn     4000",
                "    user        haproxy",
                "    group       haproxy",
                "    daemon",
                "",
                "    # Stats socket for runtime API",
                "    stats socket /var/lib/haproxy/stats level admin",
                "    stats timeout 30s",
            ]
        )

        # Metrics configuration
        if config.global_config and config.global_config.metrics:
            self._generate_haproxy_metrics(config.global_config.metrics, output)

        return output

    def _generate_defaults(self, config: Config) -> List[str]:
        """Generate defaults section."""
        timeout = config.global_config.timeout if config.global_config.timeout else "30s"

        output = [
            "#---------------------------------------------------------------------",
            "# Common defaults",
            "#---------------------------------------------------------------------",
            "defaults",
            "    mode                    http",
            "    log                     global",
            "    option                  httplog",
            "    option                  dontlognull",
            "    option                  http-server-close",
            "    option                  forwardfor except 127.0.0.0/8",
            "    option                  redispatch",
            "    retries                 3",
            f"    timeout http-request    {timeout}",
            f"    timeout queue           {timeout}",
            f"    timeout connect         5s",
            f"    timeout client          {timeout}",
            f"    timeout server          {timeout}",
            "    timeout http-keep-alive 10s",
            "    timeout check           5s",
            "    maxconn                 3000",
        ]

        return output

    def _generate_frontend(self, config: Config) -> List[str]:
        """Generate frontend section with routing ACLs."""
        output = [
            "#---------------------------------------------------------------------",
            "# Frontend - Main HTTP Router",
            "#---------------------------------------------------------------------",
            "frontend http_frontend",
        ]

        # Bind address
        host = config.global_config.host if config.global_config.host else "0.0.0.0"
        port = config.global_config.port if config.global_config.port else 80
        output.append(f"    bind {host}:{port}")
        output.append("")

        # Collect all rate limiting configurations
        rate_limit_zones: Dict[str, Any] = {}

        # Generate ACLs and rate limiting for each service/route
        for service in config.services:
            backend_name = f"backend_{service.name}"

            for idx, route in enumerate(service.routes):
                acl_name = f"is_{service.name}_route{idx}"

                # ACL for path matching
                output.append(f"    # ACL for {service.name} - {route.path_prefix}")
                output.append(f"    acl {acl_name} path_beg {route.path_prefix}")

                # Method filtering
                if route.methods:
                    methods_str = " ".join(route.methods)
                    output.append(f"    acl {acl_name}_method method {methods_str}")

                # Rate limiting
                if route.rate_limit and route.rate_limit.enabled:
                    rl_name = f"rl_{service.name}_route{idx}"
                    rate_limit_zones[rl_name] = route.rate_limit

                    output.append(f"    # Rate limiting for {route.path_prefix}")

                    # Determine key for rate limiting
                    if route.rate_limit.key_type == "ip_address":
                        track_key = "src"
                    elif route.rate_limit.key_type == "header" and route.rate_limit.key_header:
                        header_name = route.rate_limit.key_header.replace("-", "_").lower()
                        track_key = f"hdr({route.rate_limit.key_header})"
                    else:
                        track_key = "src"

                    # Track request rate
                    output.append(f"    http-request track-sc0 {track_key} if {acl_name}")

                    # Deny if rate exceeded
                    rps = route.rate_limit.requests_per_second
                    status = (
                        route.rate_limit.response_status
                        if route.rate_limit.response_status
                        else 429
                    )
                    output.append(
                        f"    http-request deny deny_status {status} if {acl_name} {{ sc_http_req_rate(0) gt {rps} }}"
                    )

                # Headers manipulation
                if route.headers:
                    output.append(f"    # Headers for {route.path_prefix}")

                    # Request headers (add)
                    if route.headers.request_add:
                        for header, value in route.headers.request_add.items():
                            # Convert template variables
                            value = self._convert_template_vars(value)
                            output.append(
                                f'    http-request set-header {header} "{value}" if {acl_name}'
                            )

                    # Request headers (set)
                    if route.headers.request_set:
                        for header, value in route.headers.request_set.items():
                            value = self._convert_template_vars(value)
                            output.append(
                                f'    http-request set-header {header} "{value}" if {acl_name}'
                            )

                    # Request headers (remove)
                    if route.headers.request_remove:
                        for header in route.headers.request_remove:
                            output.append(f"    http-request del-header {header} if {acl_name}")

                # CORS headers (add to response)
                if route.cors and route.cors.enabled:
                    output.append(f"    # CORS headers for {route.path_prefix}")

                    if route.cors.allowed_origins:
                        origins = " ".join(route.cors.allowed_origins)
                        # For simplicity, use first origin or * for multiple
                        origin = (
                            route.cors.allowed_origins[0]
                            if len(route.cors.allowed_origins) == 1
                            else "*"
                        )
                        output.append(
                            f'    http-response set-header Access-Control-Allow-Origin "{origin}" if {acl_name}'
                        )

                    if route.cors.allowed_methods:
                        methods = ", ".join(route.cors.allowed_methods)
                        output.append(
                            f'    http-response set-header Access-Control-Allow-Methods "{methods}" if {acl_name}'
                        )

                    if route.cors.allowed_headers:
                        headers = ", ".join(route.cors.allowed_headers)
                        output.append(
                            f'    http-response set-header Access-Control-Allow-Headers "{headers}" if {acl_name}'
                        )

                    if route.cors.allow_credentials:
                        output.append(
                            f'    http-response set-header Access-Control-Allow-Credentials "true" if {acl_name}'
                        )

                    if route.cors.max_age:
                        output.append(
                            f'    http-response set-header Access-Control-Max-Age "{route.cors.max_age}" if {acl_name}'
                        )

                # Response headers
                if route.headers and route.headers.response_add:
                    for header, value in route.headers.response_add.items():
                        output.append(
                            f'    http-response set-header {header} "{value}" if {acl_name}'
                        )

                if route.headers and route.headers.response_set:
                    for header, value in route.headers.response_set.items():
                        output.append(
                            f'    http-response set-header {header} "{value}" if {acl_name}'
                        )

                if route.headers and route.headers.response_remove:
                    for header in route.headers.response_remove:
                        output.append(f"    http-response del-header {header} if {acl_name}")

                # Body transformation (requires Lua scripting)
                if route.body_transformation and route.body_transformation.enabled:
                    output.append(
                        f"    # Body transformation for {route.path_prefix} (requires Lua)"
                    )
                    bt = route.body_transformation

                    # Request body transformation
                    if bt.request:
                        lua_func_name = f"transform_request_{service.name}_route{idx}"
                        output.append(f"    http-request lua.{lua_func_name} if {acl_name}")
                        # Note: Actual Lua function must be registered in haproxy.cfg global section

                    # Response body transformation
                    if bt.response:
                        lua_func_name = f"transform_response_{service.name}_route{idx}"
                        output.append(f"    http-response lua.{lua_func_name} if {acl_name}")
                        # Note: Actual Lua function must be registered in haproxy.cfg global section

                    # Add warning about Lua requirement
                    logger.warning(
                        f"Body transformation configured for {service.name}/{route.path_prefix}. "
                        "HAProxy requires Lua scripts to be loaded in global section. "
                        "Add 'lua-load /path/to/transform.lua' directive to global section and "
                        "implement transformation functions in Lua. "
                        "See HAProxy Lua documentation for details."
                    )

                output.append("")

        # Add stick-table for rate limiting at the end of frontend
        if rate_limit_zones:
            output.append("    # Rate limiting stick-table")
            # Use a general stick-table for all rate limits
            output.append("    stick-table type ip size 100k expire 30s store http_req_rate(10s)")
            output.append("")

        # Backend routing
        output.append("    # Backend routing")
        for service in config.services:
            backend_name = f"backend_{service.name}"

            for idx, route in enumerate(service.routes):
                acl_name = f"is_{service.name}_route{idx}"

                if route.methods:
                    output.append(f"    use_backend {backend_name} if {acl_name} {acl_name}_method")
                else:
                    output.append(f"    use_backend {backend_name} if {acl_name}")

        return output

    def _generate_backend(self, service: Service, config: Config) -> List[str]:
        """Generate backend section for service."""
        backend_name = f"backend_{service.name}"

        output = [
            "#---------------------------------------------------------------------",
            f"# Backend - {service.name}",
            "#---------------------------------------------------------------------",
            f"backend {backend_name}",
        ]

        # Load balancing algorithm
        algorithm = "roundrobin"  # Default
        if service.upstream and service.upstream.load_balancer:
            lb_algo = service.upstream.load_balancer.algorithm

            # Map GAL algorithms to HAProxy
            algo_map = {
                "round_robin": "roundrobin",
                "least_conn": "leastconn",
                "ip_hash": "source",
                "weighted": "roundrobin",  # Weights are per-server in HAProxy
            }
            algorithm = algo_map.get(lb_algo, "roundrobin")

        output.append(f"    balance {algorithm}")

        # Sticky sessions
        if service.upstream and service.upstream.load_balancer:
            if service.upstream.load_balancer.sticky_sessions:
                cookie_name = service.upstream.load_balancer.cookie_name or "SERVERID"
                output.append(f"    cookie {cookie_name} insert indirect nocache")

        # WebSocket support
        has_websocket = any(route.websocket and route.websocket.enabled for route in service.routes)
        if has_websocket:
            # Get idle_timeout from first WebSocket route
            for route in service.routes:
                if route.websocket and route.websocket.enabled:
                    ws = route.websocket
                    # timeout tunnel is for WebSocket connections
                    output.append(f"    timeout tunnel {ws.idle_timeout}")
                    break

        # Timeout configuration (from first route with timeout configured)
        has_timeout = any(route.timeout for route in service.routes)
        if has_timeout:
            for route in service.routes:
                if route.timeout:
                    timeout = route.timeout
                    output.append(f"    timeout connect {timeout.connect}")
                    output.append(f"    timeout server {timeout.read}")
                    # timeout client is set in frontend, but we can also set it here
                    output.append(f"    timeout client {timeout.idle}")
                    break

        # Retry configuration (from first route with retry configured)
        has_retry = any(route.retry and route.retry.enabled for route in service.routes)
        if has_retry:
            for route in service.routes:
                if route.retry and route.retry.enabled:
                    retry = route.retry
                    # HAProxy retry-on conditions
                    retry_conditions = []
                    for condition in retry.retry_on:
                        if condition == "connect_timeout":
                            retry_conditions.append("conn-failure")
                        elif condition == "http_5xx":
                            retry_conditions.append("500 502 503 504")
                        elif condition == "http_502":
                            retry_conditions.append("502")
                        elif condition == "http_503":
                            retry_conditions.append("503")
                        elif condition == "http_504":
                            retry_conditions.append("504")
                        elif condition == "reset":
                            retry_conditions.append("conn-failure")
                        elif condition == "refused":
                            retry_conditions.append("conn-failure")

                    if retry_conditions:
                        # Flatten and deduplicate
                        all_conditions = []
                        seen = set()
                        for cond in retry_conditions:
                            for part in cond.split():
                                if part not in seen:
                                    all_conditions.append(part)
                                    seen.add(part)
                        output.append(f"    retry-on {' '.join(all_conditions)}")
                        # HAProxy uses retries for attempts
                        output.append(f"    retries {retry.attempts}")
                    break

        # Health checks
        if service.upstream and service.upstream.health_check:
            hc = service.upstream.health_check

            # Active health checks
            if hc.active and hc.active.enabled:
                health_path = hc.active.http_path or "/health"
                output.append(f"    option httpchk GET {health_path} HTTP/1.1")

                # Expected status codes
                if hc.active.healthy_status_codes:
                    status_codes = "|".join(map(str, hc.active.healthy_status_codes))
                    output.append(f"    http-check expect status {status_codes}")
                else:
                    output.append("    http-check expect status 200")

        # Circuit breaker would be implemented via health check parameters
        # HAProxy uses fall/rise for circuit breaking

        # Connection pooling
        output.append("    option httpclose")
        output.append("    option forwardfor")

        # Backend servers
        output.append("")
        output.append("    # Backend servers")

        if service.upstream and service.upstream.targets:
            for idx, target in enumerate(service.upstream.targets):
                # Handle both dict and UpstreamTarget object
                if isinstance(target, dict):
                    target_host = target.get("host")
                    target_port = target.get("port")
                    target_weight = target.get("weight", 1)
                else:
                    target_host = target.host
                    target_port = target.port
                    target_weight = target.weight if hasattr(target, "weight") else 1

                server_name = f"server{idx + 1}"
                server_line = f"    server {server_name} {target_host}:{target_port}"

                # Add check if health checks enabled
                if service.upstream.health_check:
                    hc = service.upstream.health_check

                    if hc.active and hc.active.enabled:
                        # Active health check parameters
                        interval = hc.active.interval or "10s"
                        fall = hc.active.unhealthy_threshold or 3
                        rise = hc.active.healthy_threshold or 2

                        server_line += f" check inter {interval} fall {fall} rise {rise}"
                    elif hc.passive and hc.passive.enabled:
                        # Passive health check
                        max_fails = hc.passive.max_failures or 3
                        server_line += f" check fall {max_fails} rise 2"

                # Weight
                if target_weight and target_weight != 1:
                    server_line += f" weight {target_weight}"

                # Cookie for sticky sessions
                if (
                    service.upstream.load_balancer
                    and service.upstream.load_balancer.sticky_sessions
                ):
                    server_line += f" cookie {server_name}"

                output.append(server_line)

        elif hasattr(service, "host") and hasattr(service, "port"):
            # Single backend server
            server_line = f"    server server1 {service.host}:{service.port}"

            # Add basic health check
            server_line += " check inter 10s fall 3 rise 2"

            output.append(server_line)

        elif service.upstream:
            # Fallback to upstream host/port
            server_line = f"    server server1 {service.upstream.host}:{service.upstream.port}"
            server_line += " check inter 10s fall 3 rise 2"
            output.append(server_line)

        return output

    def _generate_haproxy_logging(self, logging_config, output: List[str]) -> None:
        """Generate HAProxy logging configuration.

        Args:
            logging_config: LoggingConfig object
            output: Output list to append to
        """
        # HAProxy logging
        if logging_config.format == "json":
            output.append("    log         127.0.0.1 local0 info")
            output.append("    # JSON format requires log-format directive in defaults/frontend")
        else:
            log_level_map = {"debug": "debug", "info": "info", "warning": "notice", "error": "err"}
            haproxy_level = log_level_map.get(logging_config.level, "notice")
            output.append(f"    log         127.0.0.1 local0 {haproxy_level}")

    def _generate_haproxy_metrics(self, metrics_config, output: List[str]) -> None:
        """Generate HAProxy metrics configuration.

        Args:
            metrics_config: MetricsConfig object
            output: Output list to append to
        """
        if metrics_config.enabled and metrics_config.exporter in ("prometheus", "both"):
            output.append("")
            output.append("    # Prometheus metrics endpoint")
            output.append(
                f"    # Configure prometheus-exporter on port {metrics_config.prometheus_port}"
            )
            output.append("    # or use stats endpoint: http://<haproxy_host>:8404/stats;csv")
            logger.info(f"Prometheus metrics: Configure external exporter or use stats endpoint")

    def _convert_template_vars(self, value: str) -> str:
        """Convert GAL template variables to HAProxy format."""
        # {{uuid}} → %[uuid()]
        value = value.replace("{{uuid}}", "%[uuid()]")

        # {{now}} or {{timestamp}} → %[date()]
        value = value.replace("{{now}}", "%[date()]")
        value = value.replace("{{timestamp}}", "%[date()]")

        return value

    def parse(self, provider_config: str) -> Config:
        """Parse HAProxy configuration to GAL format.

        Parses haproxy.cfg format with custom parser.
        Extracts frontends, backends, servers, and directives.

        Args:
            provider_config: HAProxy haproxy.cfg configuration string

        Returns:
            Config: GAL configuration object

        Raises:
            ValueError: If config is invalid or cannot be parsed
        """
        logger.info("Parsing HAProxy configuration to GAL format")

        if not provider_config or not provider_config.strip():
            raise ValueError("Empty configuration")

        self._import_warnings = []

        # Parse config into sections
        parser = HAProxyConfigParser()
        sections = parser.parse(provider_config)

        # Extract global config
        global_config = self._parse_global(sections)

        # Parse services from backends
        services = self._parse_services(sections)

        return Config(
            version="1.0",
            provider="haproxy",
            global_config=global_config,
            services=services,
        )

    def _parse_global(self, sections: List[HAProxySection]) -> GlobalConfig:
        """Extract global config from sections.

        Args:
            sections: List of all configuration sections

        Returns:
            GlobalConfig: Global configuration
        """
        # Try to extract from defaults or first frontend
        defaults = [s for s in sections if s.type == SectionType.DEFAULTS]
        frontends = [s for s in sections if s.type == SectionType.FRONTEND]

        host = "0.0.0.0"
        port = 80
        timeout = "30s"

        # Try to get bind from first frontend
        if frontends:
            frontend = frontends[0]
            for directive in frontend.directives:
                if directive["name"] == "bind":
                    # Parse bind directive: "bind *:80" or "bind 0.0.0.0:8080"
                    bind_value = directive["value"]
                    match = re.match(r"([^:]+):(\d+)", bind_value)
                    if match:
                        bind_host, bind_port = match.groups()
                        if bind_host != "*":
                            host = bind_host
                        port = int(bind_port)
                    elif bind_value.isdigit():
                        port = int(bind_value)

        # Try to get timeout from defaults
        if defaults:
            for directive in defaults[0].directives:
                if directive["name"] == "timeout" and "client" in directive["value"]:
                    timeout = self._parse_timeout(directive["value"])

        return GlobalConfig(host=host, port=port, timeout=timeout)

    def _parse_services(self, sections: List[HAProxySection]) -> List[Service]:
        """Parse HAProxy backends to GAL services.

        Args:
            sections: List of all configuration sections

        Returns:
            List of Service objects
        """
        services = []

        # Collect backends and frontends
        backends = [s for s in sections if s.type == SectionType.BACKEND]
        frontends = [s for s in sections if s.type == SectionType.FRONTEND]
        listen_sections = [s for s in sections if s.type == SectionType.LISTEN]

        # Parse backends
        for backend in backends:
            service = self._parse_backend(backend, frontends)
            if service:
                services.append(service)

        # Parse listen sections (combined frontend+backend)
        for listen in listen_sections:
            service = self._parse_listen(listen)
            if service:
                services.append(service)

        return services

    def _parse_backend(
        self, backend: HAProxySection, frontends: List[HAProxySection]
    ) -> Optional[Service]:
        """Parse HAProxy backend to GAL service.

        Args:
            backend: Backend section
            frontends: List of frontend sections for routing info

        Returns:
            Service object or None if cannot parse
        """
        name = backend.name or "unnamed_backend"

        # Parse server targets
        targets = []
        lb_algorithm = "round_robin"
        health_check = None
        sticky_sessions = False
        cookie_name = None
        headers_config = None

        for directive in backend.directives:
            if directive["name"] == "server":
                target = self._parse_server_directive(directive["value"])
                if target:
                    targets.append(target)

            elif directive["name"] == "balance":
                lb_algorithm = self._map_lb_algorithm(directive["value"])

            elif directive["name"] == "option":
                if "httpchk" in directive["value"]:
                    health_check = self._parse_httpchk(directive["value"])

            elif directive["name"] == "http-check":
                # HAProxy 2.0+ health check syntax
                if not health_check:
                    health_check = HealthCheckConfig(
                        active=ActiveHealthCheck(
                            enabled=True,
                            http_path="/",
                            interval="10s",
                            timeout="5s",
                            healthy_threshold=3,
                            unhealthy_threshold=2,
                        )
                    )

            elif directive["name"] == "cookie":
                # Sticky sessions via cookie
                cookie_parts = directive["value"].split()
                if cookie_parts:
                    cookie_name = cookie_parts[0]
                    sticky_sessions = True

            elif directive["name"] == "http-request" and "set-header" in directive["value"]:
                # Header manipulation
                if not headers_config:
                    headers_config = HeaderManipulation(request_add={})
                header_match = re.search(r"set-header\s+(\S+)\s+(.+)", directive["value"])
                if header_match:
                    header_name, header_value = header_match.groups()
                    headers_config.request_add[header_name] = header_value.strip('"')

        # Build upstream
        upstream = Upstream(
            targets=targets,
            load_balancer=(
                LoadBalancerConfig(
                    algorithm=lb_algorithm,
                    sticky_sessions=sticky_sessions,
                    cookie_name=cookie_name,
                )
                if targets
                else None
            ),
            health_check=health_check,
        )

        # Find routes from frontends
        routes = self._find_routes_for_backend(name, frontends)

        # Create transformation if headers are present
        transformation = None
        if headers_config:
            transformation = Transformation(headers=headers_config)

        return Service(
            name=name,
            type="rest",  # HAProxy is HTTP-focused
            protocol="http",
            upstream=upstream,
            routes=routes if routes else [Route(path_prefix="/")],
            transformation=transformation,
        )

    def _parse_listen(self, listen: HAProxySection) -> Optional[Service]:
        """Parse HAProxy listen section (combined frontend+backend).

        Args:
            listen: Listen section

        Returns:
            Service object or None if cannot parse
        """
        name = listen.name or "unnamed_listen"

        # Parse similar to backend
        targets = []
        lb_algorithm = "round_robin"
        routes = [Route(path_prefix="/")]
        bind_port = 80

        for directive in listen.directives:
            if directive["name"] == "server":
                target = self._parse_server_directive(directive["value"])
                if target:
                    targets.append(target)

            elif directive["name"] == "balance":
                lb_algorithm = self._map_lb_algorithm(directive["value"])

            elif directive["name"] == "bind":
                # Extract port from bind
                bind_value = directive["value"]
                match = re.match(r"[^:]+:(\d+)", bind_value)
                if match:
                    bind_port = int(match.group(1))

        upstream = Upstream(
            targets=targets,
            load_balancer=LoadBalancerConfig(algorithm=lb_algorithm) if targets else None,
        )

        return Service(
            name=name,
            type="rest",
            protocol="http",
            upstream=upstream,
            routes=routes,
        )

    def _parse_server_directive(self, value: str) -> Optional[UpstreamTarget]:
        """Parse server directive.

        Format: name host:port [options]

        Args:
            value: Server directive value

        Returns:
            UpstreamTarget or None if cannot parse
        """
        parts = value.split()
        if len(parts) < 2:
            return None

        # parts[0] is server name, parts[1] is host:port
        server_name = parts[0]
        address = parts[1]

        # Parse host:port
        match = re.match(r"([^:]+):(\d+)", address)
        if not match:
            return None

        host, port = match.groups()

        # Parse options (weight, check, etc.)
        weight = 1
        i = 2
        while i < len(parts):
            if parts[i] == "weight" and i + 1 < len(parts):
                try:
                    weight = int(parts[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                i += 1

        return UpstreamTarget(host=host, port=int(port), weight=weight)

    def _map_lb_algorithm(self, balance_value: str) -> str:
        """Map HAProxy balance algorithm to GAL.

        Args:
            balance_value: HAProxy balance directive value

        Returns:
            GAL load balancing algorithm name
        """
        balance_map = {
            "roundrobin": "round_robin",
            "leastconn": "least_connections",
            "source": "ip_hash",
            "uri": "uri_hash",
            "hdr": "header_hash",
            "first": "first",
        }

        balance_type = balance_value.split()[0]
        return balance_map.get(balance_type, "round_robin")

    def _parse_httpchk(self, value: str) -> HealthCheckConfig:
        """Parse option httpchk directive.

        Format: httpchk [METHOD] [URI] [VERSION]

        Args:
            value: httpchk directive value

        Returns:
            HealthCheckConfig
        """
        parts = value.split()
        path = "/"
        method = "GET"

        # Parse parts: httpchk GET /health HTTP/1.1
        if len(parts) > 1:
            method = parts[1]
        if len(parts) > 2:
            path = parts[2]

        return HealthCheckConfig(
            active=ActiveHealthCheck(
                enabled=True,
                http_path=path,
                interval="10s",
                timeout="5s",
                healthy_threshold=3,
                unhealthy_threshold=2,
            )
        )

    def _parse_timeout(self, value: str) -> str:
        """Parse timeout directive value.

        Args:
            value: Timeout value (e.g., "client 30s" or "50s")

        Returns:
            Timeout string in GAL format
        """
        parts = value.split()
        if len(parts) >= 2:
            # "client 30s" -> "30s"
            return parts[1]
        return "30s"

    def _find_routes_for_backend(
        self, backend_name: str, frontends: List[HAProxySection]
    ) -> List[Route]:
        """Find routes that use this backend.

        Args:
            backend_name: Name of backend
            frontends: List of frontend sections

        Returns:
            List of Route objects
        """
        routes = []

        for frontend in frontends:
            # Look for use_backend or default_backend directives
            for directive in frontend.directives:
                if directive["name"] == "use_backend":
                    # Parse: use_backend backend_name if condition
                    parts = directive["value"].split()
                    if parts and parts[0] == backend_name:
                        # Try to extract path from ACL condition
                        route = self._parse_use_backend_condition(directive["value"])
                        if route:
                            routes.append(route)

                elif directive["name"] == "default_backend":
                    if directive["value"] == backend_name:
                        routes.append(Route(path_prefix="/"))

        return routes if routes else [Route(path_prefix="/")]

    def _parse_use_backend_condition(self, value: str) -> Optional[Route]:
        """Parse use_backend condition to extract route.

        Args:
            value: use_backend directive value

        Returns:
            Route object or None
        """
        # Simple path extraction from ACL
        # Example: "backend_api if { path_beg /api }"
        path_match = re.search(r"path_beg\s+(/\S+)", value)
        if path_match:
            return Route(path_prefix=path_match.group(1))

        # Example: "backend_api if { path /api }"
        path_match = re.search(r"path\s+(/\S+)", value)
        if path_match:
            return Route(path_prefix=path_match.group(1))

        return None
