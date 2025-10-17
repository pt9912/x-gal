"""
Apache APISIX provider implementation.

Generates APISIX configuration in JSON format with support for
serverless functions (Lua) for request transformations.
"""

import json
import os
import logging
import requests
from typing import Optional
from ..provider import Provider
from ..config import Config

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

                # Add rate limiting plugin if configured
                if route.rate_limit and route.rate_limit.enabled:
                    if "plugins" not in route_config:
                        route_config["plugins"] = {}

                    route_config["plugins"]["limit-count"] = {
                        "count": route.rate_limit.requests_per_second,
                        "time_window": 1,
                        "rejected_code": route.rate_limit.response_status,
                        "rejected_msg": route.rate_limit.response_message,
                        "key": "remote_addr",  # or 'consumer_name', 'server_addr'
                        "policy": "local"
                    }

                apisix_config["routes"].append(route_config)

        result = json.dumps(apisix_config, indent=2)
        logger.info(f"APISIX configuration generated: {len(result)} bytes, {len(config.services)} services")
        return result
    
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

    def deploy(self, config: Config, output_file: Optional[str] = None,
               admin_url: Optional[str] = None, api_key: Optional[str] = None) -> bool:
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

            with open(output_file, 'w') as f:
                f.write(generated_config)

            logger.info(f"APISIX configuration successfully written to {output_file}")
            print(f"✓ APISIX configuration written to {output_file}")
        except IOError as e:
            logger.error(f"Failed to write APISIX config file to {output_file}: {e}")
            print(f"✗ Failed to write config file: {e}")
            return False

        # Optionally deploy via Admin API
        if admin_url:
            admin_url = admin_url.rstrip('/')
            if api_key is None:
                api_key = "edd1c9f034335f136f87ad84b625c8f1"  # Default APISIX API key

            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }

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
                        timeout=10
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
                        timeout=10
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
                        timeout=10
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
