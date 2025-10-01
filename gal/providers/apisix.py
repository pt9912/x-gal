"""
Apache APISIX provider implementation
"""

import json
from ..provider import Provider
from ..config import Config


class APISIXProvider(Provider):
    """Apache APISIX provider"""
    
    def name(self) -> str:
        return "apisix"
    
    def validate(self, config: Config) -> bool:
        """Validate APISIX configuration"""
        return True
    
    def generate(self, config: Config) -> str:
        """Generate APISIX configuration as JSON"""
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
        """Generate Lua transformation script"""
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
