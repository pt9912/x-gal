"""
Apache APISIX provider implementation.

Generates APISIX configuration in JSON format with support for
serverless functions (Lua) for request transformations.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests
import yaml

from ..config import (
    ActiveHealthCheck,
    ApiKeyConfig,
    AuthenticationConfig,
    BasicAuthConfig,
    Config,
    CORSPolicy,
    GlobalConfig,
    HeaderManipulation,
    HealthCheckConfig,
    JwtConfig,
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


class APISIXProvider(Provider):
    """Apache APISIX gateway provider.

    Generates configuration for Apache APISIX, a cloud-native API gateway
    with dynamic configuration and high performance. Uses etcd for
    configuration storage (or standalone mode).

    Output Format:
        JSON file containing:
        - routes: Route definitions with URI matching
        - services: Service definitions with upstream references
        - upstreams: Backend service endpoints with load balancing
        - plugins: Serverless functions for transformations

    Transformations:
        Implemented using serverless-pre-function plugin with Lua code.
        Full support for:
        - Setting default field values
        - Generating UUIDs with core.utils.uuid()
        - Timestamp generation with os.time()
        - Request body manipulation with cjson

    gRPC Support:
        Native gRPC protocol support in routes and upstreams.
        Automatic HTTP/2 handling.

    Load Balancing:
        Uses roundrobin load balancing by default.
        Supports multiple upstream nodes with weights.

    Example:
        >>> provider = APISIXProvider()
        >>> provider.name()
        'apisix'
        >>> config = Config.from_yaml("gateway.yaml")
        >>> output = provider.generate(config)
        >>> json.loads(output)
        {'routes': [...], 'services': [...], 'upstreams': [...]}

    See Also:
        https://apisix.apache.org/docs/apisix/getting-started/
    """

    def name(self) -> str:
        """Return provider name.

        Returns:
            str: "apisix"
        """
        return "apisix"

    def validate(self, config: Config) -> bool:
        """Validate configuration for APISIX.

        APISIX has minimal validation requirements at config generation time.
        Most validation occurs when config is applied to APISIX.

        Args:
            config: Configuration to validate

        Returns:
            True (APISIX validates at runtime)

        Example:
            >>> provider = APISIXProvider()
            >>> config = Config(...)
            >>> provider.validate(config)
            True
        """
        logger.debug(f"Validating APISIX configuration: {len(config.services)} services")
        return True

    def generate(self, config: Config) -> str:
        """Generate APISIX configuration in JSON format.

        Creates complete APISIX configuration with routes, services,
        upstreams, and serverless transformation functions.

        Configuration Structure (JSON):
            - routes: URI-based routing with service references
            - services: Service definitions with plugins
            - upstreams: Backend endpoints with load balancing

        Args:
            config: Configuration object containing services

        Returns:
            Complete APISIX JSON configuration as string

        Example:
            >>> provider = APISIXProvider()
            >>> config = Config.from_yaml("config.yaml")
            >>> json_output = provider.generate(config)
            >>> data = json.loads(json_output)
            >>> 'routes' in data and 'services' in data
            True
        """
        logger.info(f"Generating APISIX configuration for {len(config.services)} services")
        apisix_config = {"routes": [], "upstreams": [], "services": []}

        # Global plugins for logging and metrics
        global_plugins = {}
        if config.global_config and config.global_config.logging:
            global_plugins.update(
                self._generate_apisix_logging_plugins(config.global_config.logging)
            )
        if config.global_config and config.global_config.metrics:
            global_plugins.update(
                self._generate_apisix_metrics_plugins(config.global_config.metrics)
            )

        if global_plugins:
            apisix_config["global_plugins"] = global_plugins

        for service in config.services:
            # Create upstream with health checks and load balancing
            upstream = self._generate_upstream(service)
            apisix_config["upstreams"].append(upstream)

            # Create service with plugins
            svc_config = {"id": service.name, "upstream_id": f"{service.name}_upstream"}

            if service.transformation and service.transformation.enabled:
                svc_config["plugins"] = {}

                # Add body transformation if needed
                if service.transformation.defaults or service.transformation.computed_fields:
                    svc_config["plugins"]["serverless-pre-function"] = {
                        "phase": "rewrite",
                        "functions": [self._generate_lua_transformation(service)],
                    }

                # Add service-level header manipulation
                if service.transformation.headers:
                    headers = service.transformation.headers
                    # Request headers
                    if headers.request_add or headers.request_set or headers.request_remove:
                        proxy_rewrite_config = {"headers": {}}
                        if headers.request_set:
                            proxy_rewrite_config["headers"]["set"] = headers.request_set
                        if headers.request_add:
                            proxy_rewrite_config["headers"]["add"] = headers.request_add
                        if headers.request_remove:
                            proxy_rewrite_config["headers"]["remove"] = headers.request_remove
                        svc_config["plugins"]["proxy-rewrite"] = proxy_rewrite_config

                    # Response headers
                    if headers.response_add or headers.response_set or headers.response_remove:
                        response_rewrite_config = {"headers": {}}
                        if headers.response_set:
                            response_rewrite_config["headers"]["set"] = headers.response_set
                        if headers.response_add:
                            response_rewrite_config["headers"]["add"] = headers.response_add
                        if headers.response_remove:
                            response_rewrite_config["headers"]["remove"] = headers.response_remove
                        svc_config["plugins"]["response-rewrite"] = response_rewrite_config

            apisix_config["services"].append(svc_config)

            # Create routes
            for route in service.routes:
                route_config = {
                    "uri": f"{route.path_prefix}/*",
                    "name": f"{service.name}_route",
                    "service_id": service.name,
                }

                if route.methods:
                    route_config["methods"] = route.methods

                # Initialize plugins dict if needed
                if (
                    (route.rate_limit and route.rate_limit.enabled)
                    or (route.authentication and route.authentication.enabled)
                    or route.headers
                ):
                    if "plugins" not in route_config:
                        route_config["plugins"] = {}

                # Add authentication plugin if configured
                if route.authentication and route.authentication.enabled:
                    auth = route.authentication
                    if auth.type == "basic":
                        route_config["plugins"]["basic-auth"] = {}
                    elif auth.type == "api_key":
                        key_name = auth.api_key.key_name if auth.api_key else "X-API-Key"
                        in_location = auth.api_key.in_location if auth.api_key else "header"
                        route_config["plugins"]["key-auth"] = {
                            "header": key_name if in_location == "header" else None,
                            "query": key_name if in_location == "query" else None,
                        }
                        # Remove None values
                        route_config["plugins"]["key-auth"] = {
                            k: v
                            for k, v in route_config["plugins"]["key-auth"].items()
                            if v is not None
                        }
                    elif auth.type == "jwt":
                        jwt_config = {}
                        if auth.jwt:
                            if auth.jwt.issuer:
                                jwt_config["iss"] = auth.jwt.issuer
                            if auth.jwt.audience:
                                jwt_config["aud"] = auth.jwt.audience
                            if auth.jwt.algorithms:
                                jwt_config["algorithm"] = auth.jwt.algorithms[
                                    0
                                ]  # APISIX supports one algorithm
                        route_config["plugins"]["jwt-auth"] = jwt_config if jwt_config else {}

                # Add rate limiting plugin if configured
                if route.rate_limit and route.rate_limit.enabled:
                    route_config["plugins"]["limit-count"] = {
                        "count": route.rate_limit.requests_per_second,
                        "time_window": 1,
                        "rejected_code": route.rate_limit.response_status,
                        "rejected_msg": route.rate_limit.response_message,
                        "key": "remote_addr",  # or 'consumer_name', 'server_addr'
                        "policy": "local",
                    }

                # Add header manipulation plugin if configured
                if route.headers:
                    headers = route.headers
                    proxy_rewrite_config = {}

                    # Request headers
                    if headers.request_add or headers.request_set or headers.request_remove:
                        proxy_rewrite_config["headers"] = {}
                        if headers.request_set:
                            proxy_rewrite_config["headers"]["set"] = headers.request_set
                        if headers.request_add:
                            proxy_rewrite_config["headers"]["add"] = headers.request_add
                        if headers.request_remove:
                            proxy_rewrite_config["headers"]["remove"] = headers.request_remove

                    if proxy_rewrite_config:
                        route_config["plugins"]["proxy-rewrite"] = proxy_rewrite_config

                    # Response headers (using response-rewrite plugin)
                    if headers.response_add or headers.response_set or headers.response_remove:
                        response_rewrite_config = {"headers": {}}
                        if headers.response_set:
                            response_rewrite_config["headers"]["set"] = headers.response_set
                        if headers.response_add:
                            response_rewrite_config["headers"]["add"] = headers.response_add
                        if headers.response_remove:
                            response_rewrite_config["headers"]["remove"] = headers.response_remove
                        route_config["plugins"]["response-rewrite"] = response_rewrite_config

                # Add CORS plugin if configured
                if route.cors and route.cors.enabled:
                    if "plugins" not in route_config:
                        route_config["plugins"] = {}
                    cors = route.cors
                    cors_config = {
                        "allow_origins": ",".join(cors.allowed_origins),
                        "allow_methods": ",".join(cors.allowed_methods),
                        "allow_headers": ",".join(cors.allowed_headers),
                        "allow_credential": cors.allow_credentials,
                        "max_age": cors.max_age,
                    }
                    if cors.expose_headers:
                        cors_config["expose_headers"] = ",".join(cors.expose_headers)
                    route_config["plugins"]["cors"] = cors_config

                # Add Circuit Breaker plugin if configured
                if route.circuit_breaker and route.circuit_breaker.enabled:
                    if "plugins" not in route_config:
                        route_config["plugins"] = {}
                    cb = route.circuit_breaker
                    # Parse timeout (e.g., "30s" -> 30)
                    timeout_seconds = int(cb.timeout.rstrip("s"))
                    cb_config = {
                        "break_response_code": cb.failure_response_code,
                        "max_breaker_sec": timeout_seconds,
                        "unhealthy": {
                            "http_statuses": cb.unhealthy_status_codes,
                            "failures": cb.max_failures,
                        },
                        "healthy": {
                            "http_statuses": cb.healthy_status_codes,
                            "successes": cb.half_open_requests,
                        },
                    }
                    route_config["plugins"]["api-breaker"] = cb_config

                # Add timeout configuration if specified
                if route.timeout:
                    if "plugins" not in route_config:
                        route_config["plugins"] = {}
                    timeout = route.timeout
                    # Parse timeout strings (e.g., "5s" -> 5)
                    connect_seconds = int(timeout.connect.rstrip("sS"))
                    send_seconds = int(timeout.send.rstrip("sS"))
                    read_seconds = int(timeout.read.rstrip("sS"))
                    route_config["plugins"]["timeout"] = {
                        "connect": connect_seconds,
                        "send": send_seconds,
                        "read": read_seconds,
                    }

                # Add retry configuration if specified
                if route.retry and route.retry.enabled:
                    if "plugins" not in route_config:
                        route_config["plugins"] = {}
                    retry = route.retry
                    # APISIX uses proxy-retry plugin
                    # Map retry_on conditions to APISIX format
                    retry_status_codes = []
                    for condition in retry.retry_on:
                        if condition == "http_502":
                            retry_status_codes.append(502)
                        elif condition == "http_503":
                            retry_status_codes.append(503)
                        elif condition == "http_504":
                            retry_status_codes.append(504)
                        elif condition == "http_5xx":
                            retry_status_codes.extend([502, 503, 504])

                    # Remove duplicates
                    retry_status_codes = list(set(retry_status_codes))

                    route_config["plugins"]["proxy-retry"] = {
                        "retries": retry.attempts,
                        "retry_timeout": (
                            int(retry.max_interval.rstrip("msMS"))
                            if "ms" in retry.max_interval
                            else int(retry.max_interval.rstrip("sS")) * 1000
                        ),
                        "vars": (
                            [["status", "==", code] for code in retry_status_codes]
                            if retry_status_codes
                            else None
                        ),
                    }

                    # Remove None values
                    route_config["plugins"]["proxy-retry"] = {
                        k: v
                        for k, v in route_config["plugins"]["proxy-retry"].items()
                        if v is not None
                    }

                # Add WebSocket support if configured
                if route.websocket and route.websocket.enabled:
                    route_config["enable_websocket"] = True
                    # APISIX handles WebSocket timeout via upstream configuration

                # Add body transformation plugins if configured
                if route.body_transformation and route.body_transformation.enabled:
                    if "plugins" not in route_config:
                        route_config["plugins"] = {}

                    bt = route.body_transformation

                    # Request body transformation (serverless-pre-function)
                    if bt.request:
                        lua_request = self._generate_body_transformation_request_lua(bt.request)
                        route_config["plugins"]["serverless-pre-function"] = {
                            "phase": "rewrite",
                            "functions": [lua_request],
                        }

                    # Response body transformation (serverless-post-function)
                    if bt.response:
                        lua_response = self._generate_body_transformation_response_lua(bt.response)
                        route_config["plugins"]["serverless-post-function"] = {
                            "phase": "body_filter",
                            "functions": [lua_response],
                        }

                apisix_config["routes"].append(route_config)

        result = json.dumps(apisix_config, indent=2)
        logger.info(
            f"APISIX configuration generated: {len(result)} bytes, {len(config.services)} services"
        )
        return result

    def _generate_apisix_logging_plugins(self, logging_config) -> dict:
        """Generate APISIX logging plugins.

        Args:
            logging_config: LoggingConfig object

        Returns:
            Dictionary of plugins
        """
        plugins = {}

        if logging_config.enabled:
            # file-logger plugin
            log_config = {"path": logging_config.access_log_path}

            if logging_config.include_request_body:
                log_config["include_req_body"] = True
            if logging_config.include_response_body:
                log_config["include_resp_body"] = True

            plugins["file-logger"] = log_config

        return plugins

    def _generate_apisix_metrics_plugins(self, metrics_config) -> dict:
        """Generate APISIX metrics plugins.

        Args:
            metrics_config: MetricsConfig object

        Returns:
            Dictionary of plugins
        """
        plugins = {}

        if metrics_config.enabled and metrics_config.exporter in ("prometheus", "both"):
            # prometheus plugin
            plugins["prometheus"] = {}
            logger.info(
                f"Prometheus metrics enabled at http://<apisix_host>:9091/apisix/prometheus/metrics"
            )

        return plugins

    def _generate_upstream(self, service) -> dict:
        """Generate upstream configuration with health checks and load balancing.

        Creates APISIX upstream configuration supporting:
        - Multiple nodes (targets) with weights
        - Active health checks (HTTP/HTTPS/TCP probing)
        - Passive health checks (traffic monitoring)
        - Load balancing algorithms

        Args:
            service: Service object with upstream configuration

        Returns:
            dict: APISIX upstream configuration

        Example:
            >>> upstream = provider._generate_upstream(service)
            >>> upstream["type"]
            'roundrobin'
            >>> "checks" in upstream
            True
        """
        upstream = {
            "id": f"{service.name}_upstream",
            "type": "roundrobin",  # Default algorithm
            "nodes": {},
        }

        # Determine if using targets mode or simple host/port mode
        if service.upstream.targets:
            # Multiple targets mode (load balancing)
            for target in service.upstream.targets:
                node_key = f"{target.host}:{target.port}"
                upstream["nodes"][node_key] = target.weight
        else:
            # Simple mode (single host/port)
            node_key = f"{service.upstream.host}:{service.upstream.port}"
            upstream["nodes"][node_key] = 1

        # Configure load balancing algorithm
        if service.upstream.load_balancer:
            lb_algo_map = {
                "round_robin": "roundrobin",
                "least_conn": "least_conn",
                "ip_hash": "chash",
                "weighted": "roundrobin",  # Weighted uses roundrobin with node weights
            }
            algorithm = service.upstream.load_balancer.algorithm
            upstream["type"] = lb_algo_map.get(algorithm, "roundrobin")

            # For IP hash, configure key
            if algorithm == "ip_hash":
                upstream["hash_on"] = "vars"
                upstream["key"] = "remote_addr"

        # Configure health checks
        if service.upstream.health_check:
            checks_config = {}
            hc = service.upstream.health_check

            # Active health checks
            if hc.active and hc.active.enabled:
                active = hc.active
                checks_config["active"] = {
                    "type": "http",  # APISIX supports http, https, tcp
                    "http_path": active.http_path,
                    "timeout": self._parse_duration(active.timeout),
                    "healthy": {
                        "interval": self._parse_duration(active.interval),
                        "successes": active.healthy_threshold,
                        "http_statuses": active.healthy_status_codes,
                    },
                    "unhealthy": {
                        "interval": self._parse_duration(active.interval),
                        "http_failures": active.unhealthy_threshold,
                    },
                }

            # Passive health checks
            if hc.passive and hc.passive.enabled:
                passive = hc.passive
                checks_config["passive"] = {
                    "type": "http",
                    "healthy": {
                        "successes": 1,
                        "http_statuses": [200, 201, 202, 204, 301, 302, 303, 304, 307, 308],
                    },
                    "unhealthy": {
                        "http_failures": passive.max_failures,
                        "http_statuses": passive.unhealthy_status_codes,
                    },
                }

            if checks_config:
                upstream["checks"] = checks_config

        return upstream

    def _parse_duration(self, duration: str) -> int:
        """Parse duration string to seconds.

        Converts duration strings like "10s", "1m", "1h" to integer seconds.

        Args:
            duration: Duration string (e.g., "10s", "1m")

        Returns:
            int: Duration in seconds

        Example:
            >>> provider._parse_duration("10s")
            10
            >>> provider._parse_duration("1m")
            60
        """
        duration = duration.strip()
        if duration.endswith("s"):
            return int(duration[:-1])
        elif duration.endswith("m"):
            return int(duration[:-1]) * 60
        elif duration.endswith("h"):
            return int(duration[:-1]) * 3600
        else:
            # Assume seconds if no unit
            return int(duration)

    def _generate_lua_transformation(self, service) -> str:
        """Generate Lua transformation script for APISIX serverless plugin.

        Creates Lua code for the serverless-pre-function plugin that:
        - Parses request body as JSON
        - Applies default values for missing fields
        - Generates computed fields (UUID, timestamp)
        - Re-encodes modified body

        Args:
            service: Service object with transformation configuration

        Returns:
            Complete Lua function as string

        Example:
            >>> provider = APISIXProvider()
            >>> service = Service(
            ...     transformation=Transformation(
            ...         defaults={"status": "active"},
            ...         computed_fields=[ComputedField(field="id", generator="uuid")]
            ...     )
            ... )
            >>> lua = provider._generate_lua_transformation(service)
            >>> "return function(conf, ctx)" in lua
            True
        """
        lua_code = []
        lua_code.append("return function(conf, ctx)")
        lua_code.append("  local core = require('apisix.core')")
        lua_code.append("  local cjson = require('cjson.safe')")
        lua_code.append("  local body = core.request.get_body()")
        lua_code.append("  if body then")
        lua_code.append("    local json_body = cjson.decode(body)")
        lua_code.append("    if json_body then")

        # Add defaults
        for key, value in service.transformation.defaults.items():
            if isinstance(value, str):
                lua_code.append(f"      json_body.{key} = json_body.{key} or '{value}'")
            else:
                lua_code.append(f"      json_body.{key} = json_body.{key} or {value}")

        # Add computed fields
        for cf in service.transformation.computed_fields:
            if cf.generator == "timestamp":
                lua_code.append(f"      if not json_body.{cf.field} then")
                lua_code.append(f"        json_body.{cf.field} = os.time()")
                lua_code.append("      end")
            elif cf.generator == "uuid":
                lua_code.append(f"      if not json_body.{cf.field} then")
                lua_code.append(
                    f"        json_body.{cf.field} = '{cf.prefix}' .. core.utils.uuid()"
                )
                lua_code.append("      end")

        lua_code.append("      ngx.req.set_body_data(cjson.encode(json_body))")
        lua_code.append("    end")
        lua_code.append("  end")
        lua_code.append("end")

        return "\n".join(lua_code)

    def _generate_body_transformation_request_lua(self, request_transform) -> str:
        """Generate Lua script for request body transformation.

        Creates Lua code for serverless-pre-function plugin that:
        - Parses request body as JSON
        - Adds fields (with template variable support)
        - Removes fields
        - Renames fields
        - Re-encodes modified body

        Args:
            request_transform: RequestBodyTransformation object

        Returns:
            Complete Lua function as string
        """
        lua_code = []
        lua_code.append("return function(conf, ctx)")
        lua_code.append("  local core = require('apisix.core')")
        lua_code.append("  local cjson = require('cjson.safe')")
        lua_code.append("  local body = core.request.get_body()")
        lua_code.append("  if body then")
        lua_code.append("    local json_body = cjson.decode(body)")
        lua_code.append("    if json_body then")

        # Add fields
        if request_transform.add_fields:
            lua_code.append("      -- Add fields")
            for key, value in request_transform.add_fields.items():
                if value == "{{uuid}}":
                    lua_code.append(f"      json_body.{key} = core.utils.uuid()")
                elif value == "{{now}}" or value == "{{timestamp}}":
                    lua_code.append(f"      json_body.{key} = os.date('%Y-%m-%dT%H:%M:%SZ')")
                elif isinstance(value, str):
                    lua_code.append(f"      json_body.{key} = '{value}'")
                else:
                    lua_code.append(f"      json_body.{key} = {value}")

        # Remove fields
        if request_transform.remove_fields:
            lua_code.append("      -- Remove fields")
            for field in request_transform.remove_fields:
                lua_code.append(f"      json_body.{field} = nil")

        # Rename fields
        if request_transform.rename_fields:
            lua_code.append("      -- Rename fields")
            for old_name, new_name in request_transform.rename_fields.items():
                lua_code.append(f"      if json_body.{old_name} ~= nil then")
                lua_code.append(f"        json_body.{new_name} = json_body.{old_name}")
                lua_code.append(f"        json_body.{old_name} = nil")
                lua_code.append("      end")

        lua_code.append("      ngx.req.set_body_data(cjson.encode(json_body))")
        lua_code.append("    end")
        lua_code.append("  end")
        lua_code.append("end")

        return "\n".join(lua_code)

    def _generate_body_transformation_response_lua(self, response_transform) -> str:
        """Generate Lua script for response body transformation.

        Creates Lua code for serverless-post-function plugin that:
        - Parses response body as JSON
        - Filters (removes) sensitive fields
        - Adds metadata fields
        - Re-encodes modified body

        Args:
            response_transform: ResponseBodyTransformation object

        Returns:
            Complete Lua function as string
        """
        lua_code = []
        lua_code.append("return function(conf, ctx)")
        lua_code.append("  local core = require('apisix.core')")
        lua_code.append("  local cjson = require('cjson.safe')")
        lua_code.append("  local chunk = ngx.arg[1]")
        lua_code.append("  if chunk and chunk ~= '' then")
        lua_code.append("    local json_body = cjson.decode(chunk)")
        lua_code.append("    if json_body then")

        # Filter (remove) sensitive fields
        if response_transform.filter_fields:
            lua_code.append("      -- Filter sensitive fields")
            for field in response_transform.filter_fields:
                lua_code.append(f"      json_body.{field} = nil")

        # Add metadata fields
        if response_transform.add_fields:
            lua_code.append("      -- Add metadata fields")
            for key, value in response_transform.add_fields.items():
                if value == "{{uuid}}":
                    lua_code.append(f"      json_body.{key} = core.utils.uuid()")
                elif value == "{{now}}" or value == "{{timestamp}}":
                    lua_code.append(f"      json_body.{key} = os.date('%Y-%m-%dT%H:%M:%SZ')")
                elif isinstance(value, str):
                    lua_code.append(f"      json_body.{key} = '{value}'")
                else:
                    lua_code.append(f"      json_body.{key} = {value}")

        lua_code.append("      ngx.arg[1] = cjson.encode(json_body)")
        lua_code.append("    end")
        lua_code.append("  end")
        lua_code.append("end")

        return "\n".join(lua_code)

    def deploy(
        self,
        config: Config,
        output_file: Optional[str] = None,
        admin_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> bool:
        """Deploy APISIX configuration.

        Deploys configuration via APISIX Admin API or standalone file.

        Deployment Methods:
            1. Admin API (recommended): Upload routes/services/upstreams via REST API
            2. Standalone mode: Write config.yaml for APISIX standalone

        Args:
            config: Configuration to deploy
            output_file: Path to write config file (default: apisix.json)
            admin_url: APISIX Admin API URL (default: http://localhost:9180)
            api_key: Admin API key (default: edd1c9f034335f136f87ad84b625c8f1)

        Returns:
            True if deployment successful

        Raises:
            IOError: If file write fails
            requests.RequestException: If Admin API call fails

        Example:
            >>> provider = APISIXProvider()
            >>> config = Config.from_yaml("config.yaml")
            >>> # File-based deployment
            >>> provider.deploy(config, output_file="/etc/apisix/config.json")
            True
            >>> # Via Admin API
            >>> provider.deploy(config, admin_url="http://apisix:9180",
            ...                 api_key="your-api-key")
            True
        """
        logger.info(f"Deploying APISIX configuration to file: {output_file or 'apisix.json'}")
        # Generate configuration
        generated_config = self.generate(config)

        # Determine output file
        if output_file is None:
            output_file = "apisix.json"

        # Write configuration to file
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

            with open(output_file, "w") as f:
                f.write(generated_config)

            logger.info(f"APISIX configuration successfully written to {output_file}")
            print(f"✓ APISIX configuration written to {output_file}")
        except IOError as e:
            logger.error(f"Failed to write APISIX config file to {output_file}: {e}")
            print(f"✗ Failed to write config file: {e}")
            return False

        # Optionally deploy via Admin API
        if admin_url:
            admin_url = admin_url.rstrip("/")
            if api_key is None:
                api_key = "edd1c9f034335f136f87ad84b625c8f1"  # Default APISIX API key

            headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

            logger.debug(f"Deploying to APISIX Admin API at {admin_url}")
            try:
                # Load generated config
                apisix_data = json.loads(generated_config)

                # Deploy upstreams
                logger.debug(f"Deploying {len(apisix_data.get('upstreams', []))} upstreams")
                for upstream in apisix_data.get("upstreams", []):
                    upstream_id = upstream["id"]
                    response = requests.put(
                        f"{admin_url}/apisix/admin/upstreams/{upstream_id}",
                        json=upstream,
                        headers=headers,
                        timeout=10,
                    )
                    if response.status_code in (200, 201):
                        print(f"✓ Deployed upstream: {upstream_id}")
                    else:
                        print(f"✗ Failed to deploy upstream {upstream_id}: {response.status_code}")
                        print(f"  Response: {response.text}")
                        return False

                # Deploy services
                for service in apisix_data.get("services", []):
                    service_id = service["id"]
                    response = requests.put(
                        f"{admin_url}/apisix/admin/services/{service_id}",
                        json=service,
                        headers=headers,
                        timeout=10,
                    )
                    if response.status_code in (200, 201):
                        print(f"✓ Deployed service: {service_id}")
                    else:
                        print(f"✗ Failed to deploy service {service_id}: {response.status_code}")
                        print(f"  Response: {response.text}")
                        return False

                # Deploy routes
                for i, route in enumerate(apisix_data.get("routes", []), 1):
                    route_id = str(i)
                    response = requests.put(
                        f"{admin_url}/apisix/admin/routes/{route_id}",
                        json=route,
                        headers=headers,
                        timeout=10,
                    )
                    if response.status_code in (200, 201):
                        print(f"✓ Deployed route: {route.get('name', route_id)}")
                    else:
                        print(f"✗ Failed to deploy route {route_id}: {response.status_code}")
                        print(f"  Response: {response.text}")
                        return False

                logger.info("All configuration deployed successfully to APISIX")
                print(f"✓ All configuration deployed successfully to APISIX")
                return True

            except requests.RequestException as e:
                logger.error(f"Could not reach APISIX Admin API at {admin_url}: {e}")
                print(f"⚠ Could not reach APISIX Admin API: {e}")
                print(f"  Config written to {output_file}")
                return False
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON configuration: {e}")
                print(f"✗ Invalid JSON configuration: {e}")
                return False

        logger.info("APISIX deployment completed successfully")
        return True

    def parse(self, provider_config: str) -> Config:
        """Parse APISIX JSON/YAML configuration to GAL format.

        APISIX supports both etcd and standalone (config file) mode.
        This parser handles standalone config files.

        Args:
            provider_config: APISIX YAML/JSON configuration string

        Returns:
            Config: GAL configuration object

        Raises:
            ValueError: If config is invalid or cannot be parsed
        """
        logger.info("Parsing APISIX configuration to GAL format")

        # Try YAML first, then JSON
        try:
            apisix_config = yaml.safe_load(provider_config)
        except yaml.YAMLError:
            try:
                apisix_config = json.loads(provider_config)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid YAML/JSON: {e}")

        self._import_warnings = []

        # Create default global config (APISIX HTTP port 9080)
        global_config = GlobalConfig(host="0.0.0.0", port=9080, timeout="60s")

        return Config(
            version="1.0",
            provider="apisix",
            global_config=global_config,
            services=self._parse_services(apisix_config),
        )

    def _parse_services(self, apisix_config: dict) -> List[Service]:
        """Parse APISIX services to GAL services."""
        gal_services = []

        apisix_services = apisix_config.get("services", [])
        apisix_routes = apisix_config.get("routes", [])
        apisix_upstreams = apisix_config.get("upstreams", [])

        for apisix_service in apisix_services:
            service = self._parse_service(apisix_service, apisix_routes, apisix_upstreams)
            if service:
                gal_services.append(service)

        return gal_services

    def _parse_service(
        self, apisix_service: dict, apisix_routes: list, apisix_upstreams: list
    ) -> Optional[Service]:
        """Convert APISIX service to GAL service."""
        service_id = apisix_service.get("id")
        name = apisix_service.get("name", service_id)

        if not name:
            return None

        # Parse upstream
        upstream_id = apisix_service.get("upstream_id")
        upstream = self._parse_upstream(upstream_id, apisix_upstreams)

        # Parse routes for this service
        routes = []
        for apisix_route in apisix_routes:
            if apisix_route.get("service_id") == service_id:
                route = self._parse_route(apisix_route)
                if route:
                    routes.append(route)

        return Service(name=name, type="rest", protocol="http", upstream=upstream, routes=routes)

    def _parse_upstream(self, upstream_id: str, apisix_upstreams: list) -> Optional[Upstream]:
        """Parse APISIX upstream to GAL upstream."""
        # Find upstream by ID
        apisix_upstream = None
        for upstream in apisix_upstreams:
            if upstream.get("id") == upstream_id:
                apisix_upstream = upstream
                break

        if not apisix_upstream:
            return None

        # Parse nodes (targets)
        nodes = apisix_upstream.get("nodes", {})
        targets = []

        for node_str, weight in nodes.items():
            # Format: "host:port"
            if ":" in node_str:
                host, port_str = node_str.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    port = 80
            else:
                host = node_str
                port = 80

            targets.append(UpstreamTarget(host=host, port=port, weight=weight))

        # Parse load balancing type
        lb_type = apisix_upstream.get("type", "roundrobin")
        algorithm = self._map_lb_algorithm(lb_type)

        # Parse health checks
        health_check = self._parse_health_check(apisix_upstream)

        return Upstream(
            targets=targets,
            load_balancer=LoadBalancerConfig(algorithm=algorithm),
            health_check=health_check,
        )

    def _map_lb_algorithm(self, apisix_type: str) -> str:
        """Map APISIX load balancing type to GAL."""
        mapping = {
            "roundrobin": "round_robin",
            "chash": "ip_hash",
            "ewma": "least_conn",
            "least_conn": "least_conn",
        }
        return mapping.get(apisix_type, "round_robin")

    def _parse_health_check(self, apisix_upstream: dict) -> Optional[HealthCheckConfig]:
        """Parse APISIX health checks."""
        checks = apisix_upstream.get("checks", {})

        active = checks.get("active", {})
        passive = checks.get("passive", {})

        active_hc = None
        passive_hc = None

        if active and active.get("http_path"):
            # Active health checks
            healthy = active.get("healthy", {})
            unhealthy = active.get("unhealthy", {})

            active_hc = ActiveHealthCheck(
                enabled=True,
                http_path=active.get("http_path", "/"),
                interval=f"{active.get('interval', 10)}s",
                timeout=f"{active.get('timeout', 5)}s",
                healthy_threshold=healthy.get("successes", 2),
                unhealthy_threshold=unhealthy.get("http_failures", 3),
                healthy_status_codes=healthy.get("http_statuses", [200]),
            )

        if passive:
            # Passive health checks
            unhealthy = passive.get("unhealthy", {})

            passive_hc = PassiveHealthCheck(
                enabled=True, max_failures=unhealthy.get("http_failures", 3)
            )

        if active_hc or passive_hc:
            return HealthCheckConfig(active=active_hc, passive=passive_hc)

        return None

    def _parse_route(self, apisix_route: dict) -> Optional[Route]:
        """Parse APISIX route to GAL route."""
        # Parse URI
        uri = apisix_route.get("uri") or apisix_route.get("uris", ["/"])[0]

        # Parse methods
        methods = apisix_route.get("methods")

        # Parse plugins (route-level)
        plugins = apisix_route.get("plugins", {})

        rate_limit = None
        authentication = None
        headers = None
        cors = None

        # Parse each plugin
        if "limit-req" in plugins:
            rate_limit = self._parse_limit_req_plugin(plugins["limit-req"])
        elif "limit-count" in plugins:
            rate_limit = self._parse_limit_count_plugin(plugins["limit-count"])

        if "key-auth" in plugins:
            authentication = self._parse_key_auth_plugin(plugins["key-auth"])
        elif "basic-auth" in plugins:
            authentication = self._parse_basic_auth_plugin(plugins["basic-auth"])
        elif "jwt-auth" in plugins:
            authentication = self._parse_jwt_auth_plugin(plugins["jwt-auth"])

        if "proxy-rewrite" in plugins:
            headers = self._parse_proxy_rewrite_plugin(plugins["proxy-rewrite"])

        if "response-rewrite" in plugins:
            if headers:
                self._enrich_response_headers(headers, plugins["response-rewrite"])
            else:
                headers = self._parse_response_rewrite_plugin(plugins["response-rewrite"])

        if "cors" in plugins:
            cors = self._parse_cors_plugin(plugins["cors"])

        if "api-breaker" in plugins:
            self._import_warnings.append(f"Circuit breaker on route {uri} - review configuration")

        return Route(
            path_prefix=uri,
            methods=methods,
            rate_limit=rate_limit,
            authentication=authentication,
            headers=headers,
            cors=cors,
        )

    def _parse_limit_req_plugin(self, config: dict) -> RateLimitConfig:
        """Parse APISIX limit-req plugin (leaky bucket)."""
        rate = config.get("rate", 100)
        burst = config.get("burst", 200)

        return RateLimitConfig(
            enabled=True,
            requests_per_second=rate,
            burst=burst,
            key_type="ip_address",
        )

    def _parse_limit_count_plugin(self, config: dict) -> RateLimitConfig:
        """Parse APISIX limit-count plugin (fixed window)."""
        count = config.get("count", 100)
        time_window = config.get("time_window", 60)  # seconds

        # Convert to requests per second
        rps = count // time_window if time_window > 0 else count

        return RateLimitConfig(
            enabled=True,
            requests_per_second=rps,
            burst=count,
            key_type="ip_address",
        )

    def _parse_key_auth_plugin(self, config: dict) -> AuthenticationConfig:
        """Parse APISIX key-auth plugin."""
        header = config.get("header", "apikey")

        self._import_warnings.append("API keys not imported - configure in consumers")

        return AuthenticationConfig(
            enabled=True,
            type="api_key",
            api_key=ApiKeyConfig(keys=[], key_name=header, in_location="header"),
        )

    def _parse_basic_auth_plugin(self, config: dict) -> AuthenticationConfig:
        """Parse APISIX basic-auth plugin."""
        self._import_warnings.append("Basic auth users not imported - configure in consumers")

        return AuthenticationConfig(
            enabled=True, type="basic", basic_auth=BasicAuthConfig(users={}, realm="Protected")
        )

    def _parse_jwt_auth_plugin(self, config: dict) -> AuthenticationConfig:
        """Parse APISIX jwt-auth plugin."""
        self._import_warnings.append("JWT secret not imported - configure manually")

        return AuthenticationConfig(
            enabled=True,
            type="jwt",
            jwt=JwtConfig(
                issuer="CONFIGURE_MANUALLY",
                audience="CONFIGURE_MANUALLY",
                jwks_uri="",
                algorithms=["HS256"],
                required_claims=[],
            ),
        )

    def _parse_proxy_rewrite_plugin(self, config: dict) -> HeaderManipulation:
        """Parse APISIX proxy-rewrite plugin (request headers)."""
        headers_config = config.get("headers", {})

        request_add = {}
        request_remove = []

        for key, value in headers_config.items():
            if value is None or value == "":
                request_remove.append(key)
            else:
                request_add[key] = value

        return HeaderManipulation(
            request_add=request_add if request_add else None,
            request_remove=request_remove if request_remove else None,
        )

    def _parse_response_rewrite_plugin(self, config: dict) -> HeaderManipulation:
        """Parse APISIX response-rewrite plugin (response headers)."""
        headers_config = config.get("headers", {})

        response_add = {}
        response_remove = []

        for key, value in headers_config.items():
            if value is None or value == "":
                response_remove.append(key)
            else:
                response_add[key] = value

        return HeaderManipulation(
            response_add=response_add if response_add else None,
            response_remove=response_remove if response_remove else None,
        )

    def _enrich_response_headers(self, headers: HeaderManipulation, config: dict):
        """Add response headers to existing HeaderManipulation."""
        headers_config = config.get("headers", {})

        if not headers.response_add:
            headers.response_add = {}
        if not headers.response_remove:
            headers.response_remove = []

        for key, value in headers_config.items():
            if value is None or value == "":
                headers.response_remove.append(key)
            else:
                headers.response_add[key] = value

    def _parse_cors_plugin(self, config: dict) -> CORSPolicy:
        """Parse APISIX cors plugin."""
        origins = config.get("allow_origins", "*")
        methods = config.get("allow_methods", "*")
        headers_str = config.get("allow_headers", "*")
        credentials = config.get("allow_credential", False)
        max_age = config.get("max_age", 86400)

        # Parse comma-separated strings
        if isinstance(origins, str):
            origins = [origins] if origins != "*" else ["*"]

        if isinstance(methods, str):
            methods = methods.split(",") if methods != "*" else ["GET", "POST", "PUT", "DELETE"]

        headers_list = None
        if headers_str != "*":
            headers_list = headers_str.split(",") if isinstance(headers_str, str) else headers_str

        return CORSPolicy(
            enabled=True,
            allowed_origins=origins,
            allowed_methods=methods,
            allowed_headers=headers_list,
            allow_credentials=credentials,
            max_age=str(max_age),
        )

    def get_import_warnings(self) -> List[str]:
        """Return warnings from last import."""
        return getattr(self, "_import_warnings", [])
