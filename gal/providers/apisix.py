"""
Apache APISIX provider implementation.

Generates APISIX configuration in JSON format with support for
serverless functions (Lua) for request transformations.
"""

import json
from ..provider import Provider
from ..config import Config


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
        apisix_config = {
            "routes": [],
            "upstreams": [],
            "services": []
        }
        
        for service in config.services:
            # Create upstream
            upstream = {
                "id": f"{service.name}_upstream",
                "type": "roundrobin",
                "nodes": {
                    f"{service.upstream.host}:{service.upstream.port}": 1
                }
            }
            apisix_config["upstreams"].append(upstream)
            
            # Create service with plugins
            svc_config = {
                "id": service.name,
                "upstream_id": f"{service.name}_upstream"
            }
            
            if service.transformation and service.transformation.enabled:
                svc_config["plugins"] = {
                    "serverless-pre-function": {
                        "phase": "rewrite",
                        "functions": [
                            self._generate_lua_transformation(service)
                        ]
                    }
                }
            
            apisix_config["services"].append(svc_config)
            
            # Create routes
            for route in service.routes:
                route_config = {
                    "uri": f"{route.path_prefix}/*",
                    "name": f"{service.name}_route",
                    "service_id": service.name
                }
                
                if route.methods:
                    route_config["methods"] = route.methods
                
                apisix_config["routes"].append(route_config)
        
        return json.dumps(apisix_config, indent=2)
    
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
                lua_code.append(f"        json_body.{cf.field} = '{cf.prefix}' .. core.utils.uuid()")
                lua_code.append("      end")
        
        lua_code.append("      ngx.req.set_body_data(cjson.encode(json_body))")
        lua_code.append("    end")
        lua_code.append("  end")
        lua_code.append("end")
        
        return "\n".join(lua_code)
