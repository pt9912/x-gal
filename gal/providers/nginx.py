"""
Nginx Open Source provider implementation.

Generates Nginx configuration (nginx.conf) with support for reverse proxy,
load balancing, rate limiting, basic authentication, headers, and CORS.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

from ..config import (
    AuthenticationConfig,
    BasicAuthConfig,
    Config,
    CORSPolicy,
    GlobalConfig,
    HeaderManipulation,
    HealthCheckConfig,
    LoadBalancerConfig,
    PassiveHealthCheck,
    RateLimitConfig,
    Route,
    Service,
    Upstream,
    UpstreamTarget,
)
from ..provider import Provider

logger = logging.getLogger(__name__)


class NginxProvider(Provider):
    """Nginx Open Source reverse proxy and load balancer provider.

    Generates nginx.conf configuration for Nginx, the #1 web server
    worldwide with >30% market share. Nginx is lightweight, performant,
    and widely used as a reverse proxy and load balancer.

    Output Format:
        nginx.conf file with:
        - http block configuration
        - upstream blocks for load balancing
        - server blocks for virtual hosts
        - location blocks for routing
        - Rate limiting zones
        - Basic authentication
        - Header manipulation
        - CORS policies

    Supported Features:
        ✅ Reverse Proxy
        ✅ Load Balancing (round_robin, least_conn, ip_hash, weighted)
        ✅ Rate Limiting (limit_req_zone, limit_req)
        ✅ Basic Authentication (auth_basic)
        ✅ Header Manipulation (add_header, proxy_set_header)
        ✅ CORS (via add_header directives)
        ✅ Passive Health Checks (max_fails, fail_timeout)
        ✅ Upstream Targets with Weights
        ⚠️ JWT Auth (requires OpenResty/Lua)
        ⚠️ Circuit Breaker (limited, requires Lua)

    Limitations:
        ❌ No Active Health Checks (Nginx Plus only)
        ❌ No native JWT Validation (requires Lua/OpenResty)
        ❌ No Dynamic Configuration (without Plus)
        ❌ Limited Observability (without Plus)

    Ideal For:
        - High-performance reverse proxy
        - Static content serving
        - Load balancing
        - SSL/TLS termination
        - Development and production environments

    Example:
        >>> provider = NginxProvider()
        >>> provider.name()
        'nginx'
        >>> config = Config.from_yaml("gateway.yaml")
        >>> output = provider.generate(config)
        >>> "http {" in output
        True

    See Also:
        https://nginx.org/en/docs/
    """

    def name(self) -> str:
        """Return provider name.

        Returns:
            str: "nginx"
        """
        return "nginx"

    def validate(self, config: Config) -> bool:
        """Validate configuration for Nginx.

        Checks for Nginx compatibility and warns about unsupported features.

        Args:
            config: Configuration to validate

        Returns:
            True if validation passes

        Raises:
            ValueError: If critical validation fails

        Example:
            >>> provider = NginxProvider()
            >>> config = Config(...)
            >>> provider.validate(config)
            True
        """
        logger.debug(f"Validating Nginx configuration: {len(config.services)} services")

        # Check for unsupported features
        for service in config.services:
            for route in service.routes:
                # Warn about Active Health Checks
                if (
                    service.upstream
                    and service.upstream.health_check
                    and service.upstream.health_check.active
                    and service.upstream.health_check.active.enabled
                ):
                    logger.warning(
                        f"Service '{service.name}': Active health checks are not supported "
                        "in Nginx Open Source (Nginx Plus only). Using passive health checks."
                    )

                # Warn about JWT Authentication
                if (
                    route.authentication
                    and route.authentication.enabled
                    and route.authentication.type == "jwt"
                ):
                    logger.warning(
                        f"Service '{service.name}', Route '{route.path_prefix}': "
                        "JWT authentication requires OpenResty/Lua. "
                        "Consider using Basic Auth or API Key instead."
                    )

                # Warn about Circuit Breaker
                if route.circuit_breaker and route.circuit_breaker.enabled:
                    logger.warning(
                        f"Service '{service.name}', Route '{route.path_prefix}': "
                        "Circuit breaker support is limited in Nginx Open Source. "
                        "Requires Lua scripting."
                    )

        logger.debug("Nginx validation successful")
        return True

    def generate(self, config: Config) -> str:
        """Generate Nginx configuration (nginx.conf) format.

        Creates a complete nginx.conf with http, upstream, server, and
        location blocks based on the GAL configuration.

        Configuration Structure:
            - events: Worker configuration
            - http:
                - limit_req_zone: Rate limiting zones
                - upstream: Load balancing configurations
                - server: Virtual host configurations
                    - location: Route configurations

        Args:
            config: Configuration object containing services

        Returns:
            Complete nginx.conf configuration as string

        Example:
            >>> provider = NginxProvider()
            >>> config = Config.from_yaml("config.yaml")
            >>> nginx_conf = provider.generate(config)
            >>> "upstream" in nginx_conf
            True
        """
        logger.info(f"Generating Nginx configuration for {len(config.services)} services")
        output = []

        # Header comments
        output.append("# Nginx Configuration Generated by GAL")
        output.append("# Gateway Abstraction Layer - https://github.com/pt9912/x-gal")
        output.append("")

        # Events block (worker configuration)
        output.append("events {")
        output.append("    worker_connections 1024;")
        output.append("}")
        output.append("")

        # HTTP block
        output.append("http {")
        output.append("    # Basic Settings")
        output.append("    include /etc/nginx/mime.types;")
        output.append("    default_type application/octet-stream;")
        output.append("    sendfile on;")
        output.append("    keepalive_timeout 65;")
        output.append("")

        # Logging
        output.append("    # Logging")
        if config.global_config and config.global_config.logging:
            self._generate_nginx_logging(config.global_config.logging, output)
        else:
            output.append("    access_log /var/log/nginx/access.log;")
            output.append("    error_log /var/log/nginx/error.log;")
        output.append("")

        # Rate limiting zones (global definition)
        self._generate_rate_limit_zones(config, output)

        # Upstream blocks (load balancing)
        for service in config.services:
            if service.upstream and service.upstream.targets:
                self._generate_upstream(service, output)

        # Server blocks
        for service in config.services:
            self._generate_server(service, config, output)

        output.append("}")  # Close http block
        output.append("")

        result = "\n".join(output)
        logger.debug(f"Generated Nginx config: {len(result)} characters")
        return result

    def _generate_nginx_logging(self, logging_config, output: List[str]) -> None:
        """Generate Nginx logging configuration.

        Args:
            logging_config: LoggingConfig object
            output: Output list to append to
        """
        # Log format
        if logging_config.format == "json":
            output.append("    # JSON Access Log Format")
            output.append("    log_format json_combined escape=json")
            output.append("      '{'")
            output.append('        \'"time_local":"$time_local",\'')
            output.append('        \'"remote_addr":"$remote_addr",\'')
            output.append('        \'"request_method":"$request_method",\'')
            output.append('        \'"request_uri":"$request_uri",\'')
            output.append('        \'"status":"$status",\'')
            output.append('        \'"body_bytes_sent":"$body_bytes_sent",\'')
            output.append('        \'"http_referer":"$http_referer",\'')
            output.append('        \'"http_user_agent":"$http_user_agent",\'')
            output.append('        \'"request_time":"$request_time"\'')

            # Add custom fields
            for key, value in logging_config.custom_fields.items():
                output.append(f'        \'",{key}":"{value}"\'')

            output.append("      '};'")
            output.append("")

        # Access log
        if logging_config.format == "json":
            output.append(f"    access_log {logging_config.access_log_path} json_combined;")
        else:
            output.append(f"    access_log {logging_config.access_log_path};")

        # Error log with level
        log_level_map = {"debug": "debug", "info": "info", "warning": "warn", "error": "error"}
        nginx_level = log_level_map.get(logging_config.level, "warn")
        output.append(f"    error_log {logging_config.error_log_path} {nginx_level};")

    def _generate_rate_limit_zones(self, config: Config, output: List[str]) -> None:
        """Generate rate limiting zone definitions.

        Args:
            config: Configuration object
            output: Output buffer to append to
        """
        has_rate_limits = any(
            route.rate_limit and route.rate_limit.enabled
            for service in config.services
            for route in service.routes
        )

        if has_rate_limits:
            output.append("    # Rate Limiting Zones")

            for service in config.services:
                for i, route in enumerate(service.routes):
                    if route.rate_limit and route.rate_limit.enabled:
                        zone_name = f"{service.name}_route_{i}_ratelimit"
                        rl = route.rate_limit

                        # Determine key based on key_type
                        if rl.key_type == "ip_address":
                            key = "$binary_remote_addr"
                        elif rl.key_type == "header" and rl.key_header:
                            key = f"$http_{rl.key_header.lower().replace('-', '_')}"
                        else:
                            key = "$binary_remote_addr"  # default

                        # Zone: 10m = ~160k IP addresses
                        rate_per_sec = rl.requests_per_second or 100
                        output.append(
                            f"    limit_req_zone {key} zone={zone_name}:10m rate={rate_per_sec}r/s;"
                        )

            output.append("")

    def _generate_upstream(self, service: Service, output: List[str]) -> None:
        """Generate upstream block for load balancing.

        Args:
            service: Service configuration
            output: Output buffer to append to
        """
        upstream_name = f"upstream_{service.name}"
        output.append(f"    # Upstream for {service.name}")
        output.append(f"    upstream {upstream_name} {{")

        # Load balancing algorithm
        if service.upstream.load_balancer:
            lb = service.upstream.load_balancer
            if lb.algorithm == "least_conn":
                output.append("        least_conn;")
            elif lb.algorithm == "ip_hash":
                output.append("        ip_hash;")
            # round_robin is default, no directive needed
            # weighted is handled via server weights

        # Backend servers with passive health checks
        for target in service.upstream.targets:
            # Handle both dict and UpstreamTarget object
            if isinstance(target, dict):
                target_host = target.get("host")
                target_port = target.get("port")
                target_weight = target.get("weight", 1)
            else:
                target_host = target.host
                target_port = target.port
                target_weight = target.weight if hasattr(target, "weight") else 1

            server_line = f"        server {target_host}:{target_port}"

            # Weight
            if target_weight and target_weight != 1:
                server_line += f" weight={target_weight}"

            # Passive health check parameters
            if service.upstream.health_check and service.upstream.health_check.passive:
                passive = service.upstream.health_check.passive
                if passive.enabled:
                    max_fails = passive.max_failures or 3
                    # Parse timeout (e.g., "30s" -> 30s)
                    fail_timeout = "30s"  # default
                    server_line += f" max_fails={max_fails} fail_timeout={fail_timeout}"

            server_line += ";"
            output.append(server_line)

        # Connection pooling
        output.append("        keepalive 32;")

        output.append("    }")
        output.append("")

    def _generate_server(self, service: Service, config: Config, output: List[str]) -> None:
        """Generate server block for virtual host.

        Args:
            service: Service configuration
            config: Full configuration object
            output: Output buffer to append to
        """
        output.append(f"    # Server for {service.name}")
        output.append("    server {")

        # Listen port
        listen_port = config.global_config.port if config.global_config else 80
        output.append(f"        listen {listen_port};")

        # Server name (optional)
        output.append(f"        server_name {service.name}.local;")
        output.append("")

        # Location blocks for routes
        for i, route in enumerate(service.routes):
            self._generate_location(service, route, i, output)

        output.append("    }")
        output.append("")

    def _generate_location(
        self, service: Service, route: Route, route_index: int, output: List[str]
    ) -> None:
        """Generate location block for route.

        Args:
            service: Service configuration
            route: Route configuration
            route_index: Index of route in service
            output: Output buffer to append to
        """
        output.append(f"        # Route: {route.path_prefix}")
        output.append(f"        location {route.path_prefix} {{")

        # Rate limiting
        if route.rate_limit and route.rate_limit.enabled:
            self._generate_rate_limit_directives(service, route, route_index, output)

        # Basic Authentication
        if route.authentication and route.authentication.enabled:
            if route.authentication.type == "basic":
                self._generate_basic_auth(route, output)
            elif route.authentication.type == "api_key":
                output.append("            # API Key authentication not natively supported")
                output.append("            # Requires Lua or external authentication")
            elif route.authentication.type == "jwt":
                output.append("            # JWT authentication requires OpenResty/Lua")
                output.append("            # access_by_lua_block { ... }")

        # CORS handling
        if route.cors and route.cors.enabled:
            self._generate_cors(route, output)

        # Request headers
        if route.headers:
            self._generate_request_headers(route, output)

        # Response headers
        if route.headers:
            self._generate_response_headers(route, output)

        # Body transformation (requires OpenResty)
        if route.body_transformation and route.body_transformation.enabled:
            self._generate_body_transformation(route, output)

        # Proxy pass to upstream or direct backend
        self._generate_proxy_pass(service, route, output)

        # Proxy headers (default)
        output.append("            proxy_http_version 1.1;")

        # WebSocket support
        if route.websocket and route.websocket.enabled:
            ws = route.websocket
            output.append("            proxy_set_header Upgrade $http_upgrade;")
            output.append('            proxy_set_header Connection "upgrade";')

            # WebSocket timeouts (use configured timeout or defaults)
            if route.timeout:
                output.append(f"            proxy_connect_timeout {route.timeout.connect};")
                output.append(f"            proxy_send_timeout {route.timeout.send};")
                output.append(f"            proxy_read_timeout {ws.idle_timeout};")
            else:
                output.append(f"            proxy_connect_timeout 5s;")
                output.append(f"            proxy_send_timeout 60s;")
                output.append(f"            proxy_read_timeout {ws.idle_timeout};")
        else:
            output.append('            proxy_set_header Connection "";')

            # Regular HTTP timeouts (use configured timeout or defaults)
            if route.timeout:
                output.append(f"            proxy_connect_timeout {route.timeout.connect};")
                output.append(f"            proxy_send_timeout {route.timeout.send};")
                output.append(f"            proxy_read_timeout {route.timeout.read};")
            else:
                output.append(f"            proxy_connect_timeout 5s;")
                output.append(f"            proxy_send_timeout 60s;")
                output.append(f"            proxy_read_timeout 60s;")

        # Retry configuration
        if route.retry and route.retry.enabled:
            retry = route.retry
            # Map retry_on conditions to Nginx format
            retry_conditions = []
            for condition in retry.retry_on:
                if condition == "connect_timeout":
                    retry_conditions.append("timeout")
                elif condition == "http_5xx":
                    retry_conditions.append("http_500 http_502 http_503 http_504")
                elif condition == "http_502":
                    retry_conditions.append("http_502")
                elif condition == "http_503":
                    retry_conditions.append("http_503")
                elif condition == "http_504":
                    retry_conditions.append("http_504")
                elif condition == "reset":
                    retry_conditions.append("error")
                elif condition == "refused":
                    retry_conditions.append("error")

            if retry_conditions:
                # Join all conditions and remove duplicates
                unique_conditions = []
                seen = set()
                for cond in retry_conditions:
                    for part in cond.split():
                        if part not in seen:
                            unique_conditions.append(part)
                            seen.add(part)
                output.append(f"            proxy_next_upstream {' '.join(unique_conditions)};")
                output.append(f"            proxy_next_upstream_tries {retry.attempts};")
                # Use max_interval as overall timeout
                output.append(f"            proxy_next_upstream_timeout {retry.max_interval};")

        output.append("        }")
        output.append("")

    def _generate_rate_limit_directives(
        self, service: Service, route: Route, route_index: int, output: List[str]
    ) -> None:
        """Generate rate limit directives for location.

        Args:
            service: Service configuration
            route: Route configuration
            route_index: Index of route
            output: Output buffer to append to
        """
        zone_name = f"{service.name}_route_{route_index}_ratelimit"
        rl = route.rate_limit

        burst = rl.burst if rl.burst else (rl.requests_per_second * 2)
        output.append(f"            # Rate Limiting: {rl.requests_per_second} req/s, burst {burst}")
        output.append(f"            limit_req zone={zone_name} burst={burst} nodelay;")

        # Custom status code for rate limit exceeded
        status_code = rl.response_status if rl.response_status else 429
        output.append(f"            limit_req_status {status_code};")
        output.append("")

    def _generate_basic_auth(self, route: Route, output: List[str]) -> None:
        """Generate basic authentication directives.

        Args:
            route: Route configuration
            output: Output buffer to append to
        """
        auth = route.authentication
        if auth.basic_auth:
            realm = auth.basic_auth.realm or "Protected Area"
            output.append(f"            # Basic Authentication")
            output.append(f'            auth_basic "{realm}";')
            output.append(f"            auth_basic_user_file /etc/nginx/.htpasswd;")
            output.append("")

    def _generate_cors(self, route: Route, output: List[str]) -> None:
        """Generate CORS headers.

        Args:
            route: Route configuration
            output: Output buffer to append to
        """
        cors = route.cors
        output.append("            # CORS Configuration")

        # Allowed origins
        if cors.allowed_origins:
            # For simplicity, use the first origin or wildcard
            origin = cors.allowed_origins[0] if cors.allowed_origins else "*"
            output.append(
                f"            add_header 'Access-Control-Allow-Origin' '{origin}' always;"
            )

        # Allowed methods
        if cors.allowed_methods:
            methods = ", ".join(cors.allowed_methods)
            output.append(
                f"            add_header 'Access-Control-Allow-Methods' '{methods}' always;"
            )

        # Allowed headers
        if cors.allowed_headers:
            headers = ", ".join(cors.allowed_headers)
            output.append(
                f"            add_header 'Access-Control-Allow-Headers' '{headers}' always;"
            )

        # Exposed headers
        if cors.expose_headers:
            headers = ", ".join(cors.expose_headers)
            output.append(
                f"            add_header 'Access-Control-Expose-Headers' '{headers}' always;"
            )

        # Credentials
        if cors.allow_credentials:
            output.append(
                f"            add_header 'Access-Control-Allow-Credentials' 'true' always;"
            )

        # Max age
        if cors.max_age:
            output.append(
                f"            add_header 'Access-Control-Max-Age' '{cors.max_age}' always;"
            )

        # OPTIONS preflight handling
        output.append("")
        output.append("            # Handle preflight requests")
        output.append("            if ($request_method = 'OPTIONS') {")
        output.append("                return 204;")
        output.append("            }")
        output.append("")

    def _generate_request_headers(self, route: Route, output: List[str]) -> None:
        """Generate request header manipulation.

        Args:
            route: Route configuration
            output: Output buffer to append to
        """
        headers = route.headers

        if headers.request_add or headers.request_set:
            output.append("            # Request Headers")

        # Add headers
        if headers.request_add:
            for name, value in headers.request_add.items():
                # Replace template variables
                nginx_value = self._convert_template_value(value)
                output.append(f"            proxy_set_header {name} {nginx_value};")

        # Set headers (same as add in Nginx)
        if headers.request_set:
            for name, value in headers.request_set.items():
                nginx_value = self._convert_template_value(value)
                output.append(f"            proxy_set_header {name} {nginx_value};")

        # Remove headers (via proxy_set_header with empty value)
        if headers.request_remove:
            for name in headers.request_remove:
                output.append(f"            proxy_set_header {name} '';")

        if headers.request_add or headers.request_set:
            output.append("")

    def _generate_response_headers(self, route: Route, output: List[str]) -> None:
        """Generate response header manipulation.

        Args:
            route: Route configuration
            output: Output buffer to append to
        """
        headers = route.headers

        if headers.response_add or headers.response_set:
            output.append("            # Response Headers")

        # Add headers
        if headers.response_add:
            for name, value in headers.response_add.items():
                output.append(f"            add_header {name} '{value}' always;")

        # Set headers (same as add in Nginx)
        if headers.response_set:
            for name, value in headers.response_set.items():
                output.append(f"            add_header {name} '{value}' always;")

        # Remove headers (more_clear_headers module required, not in core)
        if headers.response_remove:
            output.append(
                "            # Note: Response header removal requires ngx_headers_more module"
            )
            for name in headers.response_remove:
                output.append(f"            # more_clear_headers '{name}';")

        if headers.response_add or headers.response_set:
            output.append("")

    def _generate_proxy_pass(self, service: Service, route: Route, output: List[str]) -> None:
        """Generate proxy_pass directive.

        Args:
            service: Service configuration
            route: Route configuration
            output: Output buffer to append to
        """
        # Determine proxy pass URL
        if service.upstream and service.upstream.targets:
            # Use upstream block
            upstream_name = f"upstream_{service.name}"
            proxy_url = f"http://{upstream_name}"
        elif hasattr(service, "host") and hasattr(service, "port"):
            # Direct backend
            proxy_url = f"http://{service.host}:{service.port}"
        elif service.upstream:
            # Fallback to upstream.host/port
            proxy_url = f"http://{service.upstream.host}:{service.upstream.port}"
        else:
            # Should not happen if config is valid
            raise ValueError(f"Service {service.name} has no valid upstream configuration")

        output.append("            # Proxy to backend")
        output.append(f"            proxy_pass {proxy_url};")

    def _generate_body_transformation(self, route: Route, output: List[str]) -> None:
        """Generate Lua blocks for body transformation (OpenResty required).

        Args:
            route: Route configuration
            output: Output buffer to append to
        """
        bt = route.body_transformation

        # Request body transformation
        if bt.request:
            output.append("")
            output.append("            # Request body transformation (requires OpenResty)")
            output.append("            access_by_lua_block {")
            output.append("                local cjson = require('cjson')")
            output.append("                ngx.req.read_body()")
            output.append("                local body_data = ngx.req.get_body_data()")
            output.append("                if body_data then")
            output.append(
                "                    local success, body_json = pcall(cjson.decode, body_data)"
            )
            output.append("                    if success then")

            # Add fields
            if bt.request.add_fields:
                output.append("                        -- Add fields")
                for key, value in bt.request.add_fields.items():
                    if value == "{{uuid}}":
                        output.append(
                            f"                        body_json.{key} = ngx.var.request_id"
                        )
                    elif value == "{{now}}" or value == "{{timestamp}}":
                        output.append(f"                        body_json.{key} = ngx.utctime()")
                    elif isinstance(value, str):
                        output.append(f"                        body_json.{key} = '{value}'")
                    else:
                        output.append(f"                        body_json.{key} = {value}")

            # Remove fields
            if bt.request.remove_fields:
                output.append("                        -- Remove fields")
                for field in bt.request.remove_fields:
                    output.append(f"                        body_json.{field} = nil")

            # Rename fields
            if bt.request.rename_fields:
                output.append("                        -- Rename fields")
                for old_name, new_name in bt.request.rename_fields.items():
                    output.append(f"                        if body_json.{old_name} ~= nil then")
                    output.append(
                        f"                            body_json.{new_name} = body_json.{old_name}"
                    )
                    output.append(f"                            body_json.{old_name} = nil")
                    output.append("                        end")

            output.append("                        local new_body = cjson.encode(body_json)")
            output.append("                        ngx.req.set_body_data(new_body)")
            output.append("                    end")
            output.append("                end")
            output.append("            }")

        # Response body transformation
        if bt.response:
            output.append("")
            output.append("            # Response body transformation (requires OpenResty)")
            output.append("            body_filter_by_lua_block {")
            output.append("                local cjson = require('cjson')")
            output.append("                local chunk = ngx.arg[1]")
            output.append("                if chunk and chunk ~= '' then")
            output.append(
                "                    local success, body_json = pcall(cjson.decode, chunk)"
            )
            output.append("                    if success then")

            # Filter sensitive fields
            if bt.response.filter_fields:
                output.append("                        -- Filter sensitive fields")
                for field in bt.response.filter_fields:
                    output.append(f"                        body_json.{field} = nil")

            # Add metadata fields
            if bt.response.add_fields:
                output.append("                        -- Add metadata fields")
                for key, value in bt.response.add_fields.items():
                    if value == "{{uuid}}":
                        output.append(
                            f"                        body_json.{key} = ngx.var.request_id"
                        )
                    elif value == "{{now}}" or value == "{{timestamp}}":
                        output.append(f"                        body_json.{key} = ngx.utctime()")
                    elif isinstance(value, str):
                        output.append(f"                        body_json.{key} = '{value}'")
                    else:
                        output.append(f"                        body_json.{key} = {value}")

            output.append("                        ngx.arg[1] = cjson.encode(body_json)")
            output.append("                    end")
            output.append("                end")
            output.append("            }")

        output.append("")

    def _convert_template_value(self, value: str) -> str:
        """Convert GAL template variables to Nginx variables.

        Args:
            value: Template value (e.g., "{{uuid}}", "{{now}}")

        Returns:
            Nginx variable equivalent

        Example:
            >>> self._convert_template_value("{{uuid}}")
            '$request_id'
            >>> self._convert_template_value("fixed-value")
            'fixed-value'
        """
        # Map GAL template variables to Nginx variables
        if value == "{{uuid}}":
            return "$request_id"
        elif value == "{{now}}" or value == "{{timestamp}}":
            return "$time_iso8601"
        else:
            # Static value, quote it
            return f"'{value}'"

    def parse(self, provider_config: str) -> Config:
        """Parse Nginx configuration to GAL format.

        Parses nginx.conf format with custom regex-based parser.
        Extracts upstreams, servers, locations, and directives.

        Args:
            provider_config: Nginx nginx.conf configuration string

        Returns:
            Config: GAL configuration object

        Raises:
            ValueError: If config is invalid or cannot be parsed
        """
        logger.info("Parsing Nginx configuration to GAL format")

        if not provider_config or not provider_config.strip():
            raise ValueError("Empty configuration")

        self._import_warnings = []

        # Remove comments
        config_text = self._remove_comments(provider_config)

        # Extract http block
        http_block = self._extract_http_block(config_text)
        if not http_block:
            raise ValueError("No http block found in nginx configuration")

        # Parse upstreams
        upstreams = self._parse_upstreams(http_block)

        # Parse rate limiting zones
        rate_limit_zones = self._parse_rate_limit_zones(http_block)

        # Parse servers with locations
        services = self._parse_servers(http_block, upstreams, rate_limit_zones)

        # Create default global config
        global_config = GlobalConfig(host="0.0.0.0", port=80, timeout="60s")

        return Config(
            version="1.0",
            provider="nginx",
            global_config=global_config,
            services=services,
        )

    def _remove_comments(self, config_text: str) -> str:
        """Remove comments from nginx config."""
        lines = []
        for line in config_text.split("\n"):
            # Remove comments (but preserve strings with #)
            if "#" in line:
                # Simple approach: remove # and everything after if not in quotes
                # This is simplified - full parser would handle quoted strings
                line = re.sub(r"#.*$", "", line)
            lines.append(line)
        return "\n".join(lines)

    def _extract_http_block(self, config_text: str) -> Optional[str]:
        """Extract http {} block from nginx config."""
        # Find http block
        match = re.search(r"http\s*\{", config_text, re.MULTILINE)
        if not match:
            return None

        # Find matching closing brace
        start = match.end()
        depth = 1
        pos = start

        while pos < len(config_text) and depth > 0:
            if config_text[pos] == "{":
                depth += 1
            elif config_text[pos] == "}":
                depth -= 1
            pos += 1

        if depth == 0:
            return config_text[start : pos - 1]
        return None

    def _parse_upstreams(self, http_block: str) -> Dict[str, Dict[str, Any]]:
        """Parse upstream blocks from http block."""
        upstreams = {}

        # Find all upstream blocks
        for match in re.finditer(
            r"upstream\s+(\w+)\s*\{([^}]+)\}", http_block, re.MULTILINE | re.DOTALL
        ):
            upstream_name = match.group(1)
            upstream_body = match.group(2)

            # Parse upstream configuration
            upstream_config = {
                "name": upstream_name,
                "targets": [],
                "algorithm": "round_robin",  # Default
            }

            # Check for load balancing algorithm
            if re.search(r"\bleast_conn\s*;", upstream_body):
                upstream_config["algorithm"] = "least_conn"
            elif re.search(r"\bip_hash\s*;", upstream_body):
                upstream_config["algorithm"] = "ip_hash"

            # Parse server directives
            for server_match in re.finditer(
                r"server\s+([\w\.\-]+):(\d+)(?:\s+weight=(\d+))?(?:\s+max_fails=(\d+))?(?:\s+fail_timeout=(\w+))?",
                upstream_body,
            ):
                host = server_match.group(1)
                port = int(server_match.group(2))
                weight = int(server_match.group(3)) if server_match.group(3) else 1
                max_fails = int(server_match.group(4)) if server_match.group(4) else None
                fail_timeout = server_match.group(5) if server_match.group(5) else None

                upstream_config["targets"].append(
                    {
                        "host": host,
                        "port": port,
                        "weight": weight,
                        "max_fails": max_fails,
                        "fail_timeout": fail_timeout,
                    }
                )

            upstreams[upstream_name] = upstream_config

        return upstreams

    def _parse_rate_limit_zones(self, http_block: str) -> Dict[str, Dict[str, Any]]:
        """Parse limit_req_zone directives."""
        zones = {}

        # Pattern: limit_req_zone $binary_remote_addr zone=myzone:10m rate=10r/s;
        for match in re.finditer(
            r"limit_req_zone\s+\$[\w_]+\s+zone=(\w+):[\w]+\s+rate=(\d+)r/([smhd])", http_block
        ):
            zone_name = match.group(1)
            rate = int(match.group(2))
            unit = match.group(3)

            # Convert to requests per second
            if unit == "s":
                requests_per_second = rate
            elif unit == "m":
                requests_per_second = rate / 60
            elif unit == "h":
                requests_per_second = rate / 3600
            elif unit == "d":
                requests_per_second = rate / 86400
            else:
                requests_per_second = rate

            zones[zone_name] = {
                "requests_per_second": requests_per_second,
                "rate": rate,
                "unit": unit,
            }

        return zones

    def _parse_servers(
        self,
        http_block: str,
        upstreams: Dict[str, Dict[str, Any]],
        rate_limit_zones: Dict[str, Dict[str, Any]],
    ) -> List[Service]:
        """Parse server blocks and create GAL services."""
        services = []

        # Find all server blocks using brace counting
        server_blocks = self._extract_blocks(http_block, "server")

        for server_body in server_blocks:
            # Parse locations in this server
            service = self._parse_server_block(server_body, upstreams, rate_limit_zones)
            if service:
                services.append(service)

        return services

    def _extract_blocks(self, text: str, block_name: str) -> List[str]:
        """Extract all blocks of a given type using brace counting."""
        blocks = []
        pattern = rf"{block_name}\s+[^{{]*\{{"

        pos = 0
        while True:
            match = re.search(pattern, text[pos:], re.MULTILINE)
            if not match:
                break

            # Find matching closing brace
            start = pos + match.end()
            depth = 1
            curr_pos = start

            while curr_pos < len(text) and depth > 0:
                if text[curr_pos] == "{":
                    depth += 1
                elif text[curr_pos] == "}":
                    depth -= 1
                curr_pos += 1

            if depth == 0:
                blocks.append(text[start : curr_pos - 1])

            pos = curr_pos

        return blocks

    def _parse_server_block(
        self,
        server_body: str,
        upstreams: Dict[str, Dict[str, Any]],
        rate_limit_zones: Dict[str, Dict[str, Any]],
    ) -> Optional[Service]:
        """Parse a single server block."""
        routes = []

        # Find all location blocks using brace counting
        location_blocks = self._extract_location_blocks(server_body)

        for path_prefix, location_body in location_blocks:
            route = self._parse_location_block(path_prefix, location_body, rate_limit_zones)
            if route:
                routes.append(route)

        if not routes:
            return None

        # Extract proxy_pass to determine upstream (check all locations)
        upstream_name = None
        for _, location_body in location_blocks:
            proxy_pass_match = re.search(r"proxy_pass\s+http://([\w_]+)", location_body)
            if proxy_pass_match:
                upstream_name = proxy_pass_match.group(1)
                break

        if not upstream_name:
            return None

        # Get upstream configuration
        upstream_config = upstreams.get(upstream_name)
        if not upstream_config:
            # No upstream found, create simple service
            service_name = "default_service"
        else:
            service_name = upstream_config["name"].replace("upstream_", "")

            # Build upstream
            targets = []
            for target_info in upstream_config["targets"]:
                targets.append(
                    UpstreamTarget(
                        host=target_info["host"],
                        port=target_info["port"],
                        weight=target_info.get("weight", 1),
                    )
                )

            # Health check (passive only for nginx OSS)
            health_check = None
            if any(t.get("max_fails") for t in upstream_config["targets"]):
                max_fails = upstream_config["targets"][0].get("max_fails", 3)
                health_check = HealthCheckConfig(
                    passive=PassiveHealthCheck(enabled=True, max_failures=max_fails)
                )

            upstream = Upstream(
                targets=targets,
                load_balancer=LoadBalancerConfig(
                    algorithm=upstream_config.get("algorithm", "round_robin")
                ),
                health_check=health_check,
            )

        return Service(
            name=service_name,
            type="rest",
            protocol="http",
            upstream=upstream if upstream_config else None,
            routes=routes,
        )

    def _parse_location_block(
        self, path_prefix: str, location_body: str, rate_limit_zones: Dict[str, Dict[str, Any]]
    ) -> Optional[Route]:
        """Parse a single location block."""
        # Rate limiting
        rate_limit = None
        limit_req_match = re.search(r"limit_req\s+zone=(\w+)(?:\s+burst=(\d+))?", location_body)
        if limit_req_match:
            zone_name = limit_req_match.group(1)
            burst = int(limit_req_match.group(2)) if limit_req_match.group(2) else None

            zone_config = rate_limit_zones.get(zone_name)
            if zone_config:
                rate_limit = RateLimitConfig(
                    enabled=True,
                    requests_per_second=zone_config["requests_per_second"],
                    burst=burst,
                    key_type="ip_address",
                )

        # Authentication (Basic Auth)
        authentication = None
        if re.search(r'auth_basic\s+"([^"]+)"', location_body):
            self._import_warnings.append(
                f"Basic auth detected for {path_prefix} - htpasswd file not imported"
            )
            authentication = AuthenticationConfig(
                enabled=True, type="basic", basic_auth=BasicAuthConfig(users={}, realm="Protected")
            )

        # Headers
        headers = self._parse_headers(location_body)

        # CORS
        cors = self._extract_cors_from_headers(headers) if headers else None

        return Route(
            path_prefix=path_prefix,
            rate_limit=rate_limit,
            authentication=authentication,
            headers=headers,
            cors=cors,
        )

    def _parse_headers(self, location_body: str) -> Optional[HeaderManipulation]:
        """Parse header directives."""
        request_add = {}
        response_add = {}

        # proxy_set_header (request headers)
        for match in re.finditer(r'proxy_set_header\s+([\w\-]+)\s+"?([^";]+)"?', location_body):
            header_name = match.group(1)
            header_value = match.group(2).strip()
            request_add[header_name] = header_value

        # add_header (response headers)
        for match in re.finditer(r'add_header\s+([\w\-]+)\s+"?([^";]+)"?', location_body):
            header_name = match.group(1)
            header_value = match.group(2).strip()
            response_add[header_name] = header_value

        if not request_add and not response_add:
            return None

        return HeaderManipulation(
            request_add=request_add if request_add else None,
            response_add=response_add if response_add else None,
        )

    def _extract_cors_from_headers(self, headers: HeaderManipulation) -> Optional[CORSPolicy]:
        """Extract CORS config from response headers."""
        if not headers or not headers.response_add:
            return None

        cors_headers = {}
        for key, value in headers.response_add.items():
            if key.startswith("Access-Control-"):
                cors_headers[key] = value

        if not cors_headers:
            return None

        # Build CORS config
        allowed_origins_str = cors_headers.get("Access-Control-Allow-Origin", "*")
        allowed_origins = [allowed_origins_str] if allowed_origins_str != "*" else ["*"]

        allowed_methods_str = cors_headers.get(
            "Access-Control-Allow-Methods", "GET,POST,PUT,DELETE"
        )
        allowed_methods = [m.strip() for m in allowed_methods_str.split(",")]

        allowed_headers_str = cors_headers.get("Access-Control-Allow-Headers")
        allowed_headers = (
            [h.strip() for h in allowed_headers_str.split(",")] if allowed_headers_str else None
        )

        allow_credentials = cors_headers.get("Access-Control-Allow-Credentials") == "true"

        max_age = cors_headers.get("Access-Control-Max-Age", "86400")

        # Remove CORS headers from response_add
        for key in list(headers.response_add.keys()):
            if key.startswith("Access-Control-"):
                del headers.response_add[key]

        return CORSPolicy(
            enabled=True,
            allowed_origins=allowed_origins,
            allowed_methods=allowed_methods,
            allowed_headers=allowed_headers,
            allow_credentials=allow_credentials,
            max_age=max_age,
        )

    def _extract_location_blocks(self, server_body: str) -> List[tuple]:
        """Extract location blocks with their paths."""
        locations = []
        pattern = r"location\s+([\w/\-\.]+)\s*\{"

        pos = 0
        while True:
            match = re.search(pattern, server_body[pos:])
            if not match:
                break

            path_prefix = match.group(1)

            # Find matching closing brace
            start = pos + match.end()
            depth = 1
            curr_pos = start

            while curr_pos < len(server_body) and depth > 0:
                if server_body[curr_pos] == "{":
                    depth += 1
                elif server_body[curr_pos] == "}":
                    depth -= 1
                curr_pos += 1

            if depth == 0:
                location_body = server_body[start : curr_pos - 1]
                locations.append((path_prefix, location_body))

            pos = curr_pos

        return locations

    def get_import_warnings(self) -> List[str]:
        """Return warnings from last import."""
        return getattr(self, "_import_warnings", [])
