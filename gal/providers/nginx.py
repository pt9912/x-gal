"""
Nginx Open Source provider implementation.

Generates Nginx configuration (nginx.conf) with support for reverse proxy,
load balancing, rate limiting, basic authentication, headers, and CORS.
"""

import logging
import os
from typing import List, Optional

from ..config import Config, Route, Service, Upstream
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

            # WebSocket timeouts
            output.append(f"            proxy_connect_timeout 5s;")
            output.append(f"            proxy_send_timeout 60s;")
            # Use idle_timeout for WebSocket connections
            output.append(f"            proxy_read_timeout {ws.idle_timeout};")
        else:
            output.append('            proxy_set_header Connection "";')

            # Regular HTTP timeouts
            output.append(f"            proxy_connect_timeout 5s;")
            output.append(f"            proxy_send_timeout 60s;")
            output.append(f"            proxy_read_timeout 60s;")

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
