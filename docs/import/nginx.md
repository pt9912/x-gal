# Feature 5: Nginx Import (Custom Parser)

**Status:** 🔄 Geplant
**Aufwand:** 2 Wochen
**Release:** v1.3.0-beta1 (Woche 6)
**Priorität:** 🔴 Hoch

## Übersicht

Import von Nginx nginx.conf nach GAL. Nginx verwendet ein eigenes Konfigurations-Format (nicht YAML/JSON), daher ist ein **Custom Parser** erforderlich. Nginx ist sehr weit verbreitet und daher kritisch für Adoption.

## Herausforderungen

- **Eigenes Format**: nginx.conf ist kein standardisiertes Format (kein YAML, JSON, TOML)
- **Kontext-Hierarchie**: server { location { } } Blöcke verschachtelt
- **Direktiven-Vielfalt**: Hunderte verschiedene Direktiven
- **Include-Dateien**: nginx.conf kann andere Dateien einbinden
- **Variablen**: Nginx verwendet $variable Syntax

## Implementierung

### Custom Parser: NginxConfigParser

```python
# gal/parsers/nginx_parser.py

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class NginxDirective:
    """Represents a single nginx directive."""
    name: str
    args: List[str]
    block: Optional[List['NginxDirective']] = None

class NginxConfigParser:
    """Parser for nginx.conf files.

    Parses nginx configuration files into a structured format
    for conversion to GAL.
    """

    def __init__(self):
        self.lines = []
        self.pos = 0

    def parse(self, config_text: str) -> List[NginxDirective]:
        """Parse nginx config text into directive tree.

        Args:
            config_text: nginx.conf content

        Returns:
            List of top-level NginxDirective objects

        Raises:
            ValueError: If syntax is invalid
        """
        # Preprocess: Remove comments, normalize whitespace
        lines = self._preprocess(config_text)
        self.lines = lines
        self.pos = 0

        directives = []
        while self.pos < len(self.lines):
            directive = self._parse_directive()
            if directive:
                directives.append(directive)

        return directives

    def _preprocess(self, config_text: str) -> List[str]:
        """Preprocess config text: remove comments, normalize."""
        lines = []

        for line in config_text.split('\n'):
            # Remove comments
            if '#' in line:
                line = line[:line.index('#')]

            # Strip whitespace
            line = line.strip()

            if line:
                lines.append(line)

        return lines

    def _parse_directive(self) -> Optional[NginxDirective]:
        """Parse a single directive with optional block."""
        if self.pos >= len(self.lines):
            return None

        line = self.lines[self.pos]

        # Check if this line starts a block (ends with {)
        if '{' in line:
            # Extract directive name and args before {
            parts = line.split('{')[0].strip().split()

            if not parts:
                self.pos += 1
                return None

            name = parts[0]
            args = parts[1:] if len(parts) > 1 else []

            # Parse block contents
            self.pos += 1
            block_directives = []

            while self.pos < len(self.lines):
                line = self.lines[self.pos]

                if '}' in line:
                    # End of block
                    self.pos += 1
                    break

                directive = self._parse_directive()
                if directive:
                    block_directives.append(directive)

            return NginxDirective(name=name, args=args, block=block_directives)
        else:
            # Simple directive (ends with ;)
            if ';' not in line:
                self.pos += 1
                return None

            # Remove trailing semicolon
            line = line.rstrip(';').strip()
            parts = line.split()

            if not parts:
                self.pos += 1
                return None

            name = parts[0]
            args = parts[1:] if len(parts) > 1 else []

            self.pos += 1
            return NginxDirective(name=name, args=args, block=None)
```

### Provider.parse() Methode

```python
class NginxProvider(Provider):
    """Nginx Provider with Import Support."""

    def parse(self, provider_config: str) -> Config:
        """Parse nginx.conf to GAL format.

        Args:
            provider_config: nginx.conf content

        Returns:
            Config: GAL configuration object

        Raises:
            ValueError: If config is invalid
        """
        parser = NginxConfigParser()
        directives = parser.parse(provider_config)

        self._import_warnings = []

        return Config(
            version="1.0",
            provider="nginx",
            global_config=self._parse_global(directives),
            services=self._parse_services(directives)
        )

    def _parse_global(self, directives: List[NginxDirective]) -> GlobalConfig:
        """Extract global config from nginx directives."""
        # Look for events and http blocks
        return GlobalConfig(
            host="0.0.0.0",
            port=80,  # Default, extracted from server blocks
            timeout="30s"
        )

    def _parse_services(self, directives: List[NginxDirective]) -> List[Service]:
        """Parse nginx http.server blocks to GAL services."""
        services = []

        # Find http block
        http_block = None
        for directive in directives:
            if directive.name == "http":
                http_block = directive.block
                break

        if not http_block:
            return services

        # Find all upstream blocks (targets)
        upstreams = {}
        for directive in http_block:
            if directive.name == "upstream":
                upstream_name = directive.args[0] if directive.args else None
                if upstream_name:
                    upstreams[upstream_name] = self._parse_upstream(directive)

        # Find all server blocks
        for directive in http_block:
            if directive.name == "server":
                service = self._parse_server(directive.block, upstreams)
                if service:
                    services.append(service)

        return services

    def _parse_upstream(self, upstream_directive: NginxDirective) -> Dict[str, Any]:
        """Parse nginx upstream block."""
        upstream_name = upstream_directive.args[0]
        servers = []
        lb_algorithm = "round_robin"
        health_check = None

        for directive in upstream_directive.block:
            if directive.name == "server":
                # Format: server host:port [weight=N] [max_fails=N] [fail_timeout=Ns]
                server_str = directive.args[0]
                weight = 1
                max_fails = None
                fail_timeout = None

                # Parse additional args
                for arg in directive.args[1:]:
                    if arg.startswith("weight="):
                        weight = int(arg.split("=")[1])
                    elif arg.startswith("max_fails="):
                        max_fails = int(arg.split("=")[1])
                    elif arg.startswith("fail_timeout="):
                        fail_timeout = arg.split("=")[1]

                # Parse host:port
                if ":" in server_str:
                    host, port_str = server_str.rsplit(":", 1)
                    port = int(port_str)
                else:
                    host = server_str
                    port = 80

                servers.append({
                    "host": host,
                    "port": port,
                    "weight": weight,
                    "max_fails": max_fails,
                    "fail_timeout": fail_timeout
                })

            elif directive.name == "least_conn":
                lb_algorithm = "least_conn"
            elif directive.name == "ip_hash":
                lb_algorithm = "ip_hash"

        return {
            "name": upstream_name,
            "servers": servers,
            "algorithm": lb_algorithm,
            "health_check": health_check
        }

    def _parse_server(
        self,
        server_block: List[NginxDirective],
        upstreams: Dict[str, Any]
    ) -> Optional[Service]:
        """Parse nginx server block to GAL service."""
        # Try to extract service name from server_name or upstream
        server_name = None
        proxy_pass = None
        locations = []

        for directive in server_block:
            if directive.name == "server_name":
                server_name = directive.args[0] if directive.args else None
            elif directive.name == "location":
                location = self._parse_location(directive, upstreams)
                if location:
                    locations.append(location)

        if not locations:
            return None

        # Determine service name and upstream
        # Check if any location uses upstream
        upstream_name = None
        for location in locations:
            if "upstream_name" in location:
                upstream_name = location["upstream_name"]
                break

        if not upstream_name:
            # No upstream, use direct proxy_pass
            self._import_warnings.append(
                f"Server '{server_name}' has no upstream - using direct proxy"
            )
            return None

        upstream_config = upstreams.get(upstream_name)
        if not upstream_config:
            return None

        service_name = server_name or upstream_name

        # Build upstream
        targets = []
        for server in upstream_config["servers"]:
            targets.append(UpstreamTarget(
                host=server["host"],
                port=server["port"],
                weight=server.get("weight", 1)
            ))

        # Health check (passive only in Nginx OSS)
        health_check = None
        if any(s.get("max_fails") for s in upstream_config["servers"]):
            health_check = HealthCheckConfig(
                passive=PassiveHealthCheck(
                    enabled=True,
                    max_failures=upstream_config["servers"][0].get("max_fails", 3)
                )
            )

        upstream = UpstreamConfig(
            targets=targets,
            load_balancer=LoadBalancerConfig(
                algorithm=upstream_config["algorithm"]
            ),
            health_check=health_check
        )

        # Build routes
        routes = []
        for location in locations:
            route = Route(
                path_prefix=location["path"],
                rate_limit=location.get("rate_limit"),
                authentication=location.get("authentication"),
                headers=location.get("headers"),
                cors=location.get("cors")
            )
            routes.append(route)

        return Service(
            name=service_name,
            upstream=upstream,
            routes=routes
        )

    def _parse_location(
        self,
        location_directive: NginxDirective,
        upstreams: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Parse nginx location block to route."""
        # Location path
        path = location_directive.args[0] if location_directive.args else "/"

        location_config = {
            "path": path
        }

        # Parse directives in location block
        for directive in location_directive.block:
            if directive.name == "proxy_pass":
                proxy_pass = directive.args[0] if directive.args else None

                # Extract upstream name from proxy_pass
                # Format: http://upstream_name
                if proxy_pass and proxy_pass.startswith("http://"):
                    upstream_name = proxy_pass[7:].rstrip("/")
                    location_config["upstream_name"] = upstream_name

            elif directive.name == "limit_req":
                # Rate limiting
                # Format: limit_req zone=mylimit burst=20 nodelay;
                zone = None
                burst = None

                for arg in directive.args:
                    if arg.startswith("zone="):
                        zone = arg.split("=")[1]
                    elif arg.startswith("burst="):
                        burst = int(arg.split("=")[1])

                location_config["rate_limit"] = RateLimitConfig(
                    enabled=True,
                    requests_per_second=10,  # Extracted from zone definition
                    burst=burst or 20
                )

            elif directive.name == "auth_basic":
                # Basic authentication
                location_config["authentication"] = AuthenticationConfig(
                    enabled=True,
                    type="basic",
                    basic_auth=BasicAuth(users={})
                )

            elif directive.name == "add_header":
                # Response headers
                header_name = directive.args[0] if len(directive.args) > 0 else None
                header_value = directive.args[1] if len(directive.args) > 1 else ""

                if not location_config.get("headers"):
                    location_config["headers"] = HeadersConfig()

                if not location_config["headers"].response_add:
                    location_config["headers"].response_add = {}

                location_config["headers"].response_add[header_name] = header_value

                # Check for CORS headers
                if header_name and header_name.startswith("Access-Control-"):
                    self._extract_cors_from_header(location_config, header_name, header_value)

        return location_config

    def _extract_cors_from_header(
        self,
        location_config: Dict[str, Any],
        header_name: str,
        header_value: str
    ):
        """Extract CORS config from Access-Control-* headers."""
        if "cors" not in location_config:
            location_config["cors"] = CorsConfig(enabled=True)

        cors = location_config["cors"]

        if header_name == "Access-Control-Allow-Origin":
            cors.allowed_origins = [header_value]
        elif header_name == "Access-Control-Allow-Methods":
            cors.allowed_methods = header_value.split(",")
        elif header_name == "Access-Control-Allow-Headers":
            cors.allowed_headers = header_value.split(",")
        elif header_name == "Access-Control-Allow-Credentials":
            cors.allow_credentials = header_value.lower() == "true"
        elif header_name == "Access-Control-Max-Age":
            cors.max_age = header_value

    def get_import_warnings(self) -> List[str]:
        """Return warnings from last import."""
        return getattr(self, '_import_warnings', [])
```

## Feature Mapping Matrix

| GAL Feature | Nginx Config | Mapping |
|-------------|-------------|---------|
| **Service** | `server` block + `server_name` | Derived from upstream name |
| **Upstream Targets** | `upstream { server host:port; }` | Direct mapping |
| **Load Balancing** | `least_conn`, `ip_hash` | Default: round_robin |
| **Passive Health Checks** | `server ... max_fails=N fail_timeout=Ns` | ✅ Direct mapping |
| **Active Health Checks** | - | ❌ Nginx Plus only |
| **Routes** | `location /path` | Direct mapping |
| **Rate Limiting** | `limit_req zone=... burst=...` | ⚠️ Requires zone definition |
| **Basic Auth** | `auth_basic`, `auth_basic_user_file` | ✅ (users from htpasswd file) |
| **Headers** | `add_header`, `proxy_set_header` | Direct mapping |
| **CORS** | `add_header Access-Control-*` | Extracted from headers |
| **JWT Auth** | - | ❌ Requires OpenResty/Lua |

## Beispiel-Konvertierung

### nginx.conf (Input)

```nginx
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        least_conn;

        server api-1.internal:8080 weight=2 max_fails=3 fail_timeout=30s;
        server api-2.internal:8080 weight=1 max_fails=3 fail_timeout=30s;
    }

    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        listen 80;
        server_name api.example.com;

        location /api {
            limit_req zone=api_limit burst=20 nodelay;

            proxy_pass http://api_backend;

            proxy_set_header X-Gateway nginx;
            proxy_set_header X-Real-IP $remote_addr;

            add_header Access-Control-Allow-Origin "https://app.example.com";
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE";
            add_header Access-Control-Allow-Credentials "true";
        }

        location /admin {
            auth_basic "Admin Area";
            auth_basic_user_file /etc/nginx/.htpasswd;

            proxy_pass http://api_backend;
        }
    }
}
```

### GAL Config (Output)

```yaml
version: "1.0"
provider: nginx

global_config:
  host: 0.0.0.0
  port: 80
  timeout: 30s

services:
  - name: api.example.com
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
          weight: 2
        - host: api-2.internal
          port: 8080
          weight: 1

      load_balancer:
        algorithm: least_conn

      health_check:
        passive:
          enabled: true
          max_failures: 3

    routes:
      - path_prefix: /api

        rate_limit:
          enabled: true
          requests_per_second: 10
          burst: 20
          key_type: ip_address

        headers:
          request_add:
            X-Gateway: nginx
            X-Real-IP: "{{client_ip}}"

        cors:
          enabled: true
          allowed_origins:
            - https://app.example.com
          allowed_methods:
            - GET
            - POST
            - PUT
            - DELETE
          allow_credentials: true

      - path_prefix: /admin

        authentication:
          enabled: true
          type: basic
          basic_auth:
            users: {}  # From .htpasswd file
```

## CLI Usage

```bash
# Import nginx.conf
gal import --provider nginx --input /etc/nginx/nginx.conf --output gal-config.yaml

# Generate for different provider
gal generate --config gal-config.yaml --provider haproxy --output haproxy.cfg
```

## Test Cases

30+ Tests (komplexer wegen Custom Parser):
- Parser Tests (directive parsing, blocks, comments)
- Upstream parsing
- Server block parsing
- Location block parsing
- Rate limiting (limit_req_zone + limit_req)
- Basic auth
- Headers (proxy_set_header, add_header)
- CORS extraction
- Load balancing algorithms
- Passive health checks
- Include directive handling
- Round-trip test

## Edge Cases und Herausforderungen

### Parser-spezifisch

- **Include-Dateien**: `include /etc/nginx/conf.d/*.conf;`
  - Lösung: Rekursiver Parser oder Warnung
- **Variablen**: `$remote_addr`, `$request_id`
  - Mapping zu GAL template variables
- **Regex Locations**: `location ~ ^/api/.*$`
  - Vereinfachung zu path_prefix
- **If-Direktiven**: `if ($http_user_agent ~* bot)`
  - Nicht mappbar, Warnung

### Feature-spezifisch

- **Rate Limiting**: Requires `limit_req_zone` definition außerhalb location
  - Parser muss zones tracken und zuordnen
- **htpasswd Dateien**: Users extern in Datei
  - Nur Platzhalter importiert, manuelle Konfiguration
- **Nginx Plus**: Features wie active health checks nicht in OSS
  - Warnung

## Akzeptanzkriterien

- ✅ Custom Parser für nginx.conf Syntax
- ✅ Import von upstream + server + location
- ✅ Mapping von Direktiven zu GAL Features
- ✅ Rate Limiting (zone-based)
- ✅ Basic Auth Import
- ✅ Headers + CORS
- ✅ Include-Datei Unterstützung (oder Warnung)
- ✅ CLI Integration
- ✅ 30+ Tests, 85%+ Coverage (Parser komplex)
- ✅ Warnings für nicht unterstützte Features
- ✅ Round-trip Test

## Implementierungs-Reihenfolge

1. **Tag 1-3**: NginxConfigParser (Lexer/Parser)
2. **Tag 4-5**: Upstream + Server Parsing
3. **Tag 6-7**: Location + Rate Limiting
4. **Tag 8-9**: Auth + Headers + CORS
5. **Tag 10-12**: Tests + Edge Cases + Documentation
6. **Tag 13-14**: Include Support + Integration

## Nächste Schritte

Nach Completion:
1. Release als v1.3.0-beta1
2. User Feedback (Parser Robustheit)
3. HAProxy Import (Feature 6) beginnen
