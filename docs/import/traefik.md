# Feature 4: Traefik Import (YAML Parser)

**Status:** 🔄 Geplant
**Aufwand:** 1 Woche
**Release:** v1.3.0-alpha2 (Woche 4)
**Priorität:** 🟡 Mittel

## Übersicht

Import von Traefik Static/Dynamic Configuration (YAML) nach GAL. Traefik wird in alpha2 mit APISIX implementiert:
- Traefik verwendet File Provider für static config
- Dynamic Configuration für Services/Routes/Middlewares
- Weit verbreitet in Cloud-Native/Kubernetes Umgebungen

## Implementierung

### Provider.parse() Methode

```python
class TraefikProvider(Provider):
    """Traefik Proxy Provider with Import Support."""

    def parse(self, provider_config: str) -> Config:
        """Parse Traefik YAML config to GAL format.

        Traefik has static config (entrypoints, providers) and
        dynamic config (routers, services, middlewares).

        Args:
            provider_config: Traefik YAML configuration string (dynamic config)

        Returns:
            Config: GAL configuration object

        Raises:
            ValueError: If config is invalid
        """
        try:
            traefik_config = yaml.safe_load(provider_config)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

        self._import_warnings = []

        # Traefik structure: http.routers, http.services, http.middlewares
        return Config(
            version="1.0",
            provider="traefik",
            global_config=self._parse_global(traefik_config),
            services=self._parse_services(traefik_config)
        )

    def _parse_global(self, traefik_config: dict) -> GlobalConfig:
        """Extract global config from Traefik."""
        # Traefik doesn't have global config in dynamic config
        # Static config defines entrypoints
        return GlobalConfig(
            host="0.0.0.0",
            port=80,  # Default HTTP entrypoint
            timeout="30s"
        )

    def _parse_services(self, traefik_config: dict) -> List[Service]:
        """Parse Traefik services to GAL services."""
        gal_services = []

        http_config = traefik_config.get("http", {})
        traefik_services = http_config.get("services", {})
        traefik_routers = http_config.get("routers", {})
        traefik_middlewares = http_config.get("middlewares", {})

        for service_name, service_config in traefik_services.items():
            service = self._parse_service(
                service_name,
                service_config,
                traefik_routers,
                traefik_middlewares
            )
            if service:
                gal_services.append(service)

        return gal_services

    def _parse_service(
        self,
        service_name: str,
        service_config: dict,
        traefik_routers: dict,
        traefik_middlewares: dict
    ) -> Optional[Service]:
        """Convert Traefik service to GAL service."""
        # Parse load balancer config
        load_balancer = service_config.get("loadBalancer", {})

        if not load_balancer:
            return None

        # Parse servers (targets)
        servers = load_balancer.get("servers", [])
        targets = []

        for server in servers:
            url = server.get("url")  # Format: "http://host:port"

            if not url:
                continue

            # Parse URL
            from urllib.parse import urlparse
            parsed = urlparse(url)

            host = parsed.hostname
            port = parsed.port or 80

            targets.append(UpstreamTarget(host=host, port=port))

        # Parse health check
        health_check = self._parse_health_check(load_balancer)

        # Parse sticky sessions
        sticky = load_balancer.get("sticky", {})
        sticky_sessions = sticky.get("cookie") is not None

        cookie_name = None
        if sticky_sessions:
            cookie_config = sticky.get("cookie", {})
            cookie_name = cookie_config.get("name", "lb")

        # Upstream config
        upstream = UpstreamConfig(
            targets=targets,
            load_balancer=LoadBalancerConfig(
                algorithm="round_robin",  # Traefik default
                sticky_sessions=sticky_sessions,
                cookie_name=cookie_name
            ),
            health_check=health_check
        )

        # Parse routes for this service
        routes = []
        for router_name, router_config in traefik_routers.items():
            if router_config.get("service") == service_name:
                route = self._parse_router(
                    router_name,
                    router_config,
                    traefik_middlewares
                )
                if route:
                    routes.append(route)

        return Service(
            name=service_name,
            upstream=upstream,
            routes=routes
        )

    def _parse_health_check(self, load_balancer: dict) -> Optional[HealthCheckConfig]:
        """Parse Traefik health check."""
        health_check = load_balancer.get("healthCheck", {})

        if not health_check:
            return None

        path = health_check.get("path", "/health")
        interval = health_check.get("interval", "30s")
        timeout = health_check.get("timeout", "5s")

        # Traefik only supports passive health checks by default
        # Active health checks in Traefik Plus
        self._import_warnings.append(
            "Traefik OSS only supports passive health checks - config may be simplified"
        )

        return HealthCheckConfig(
            passive=PassiveHealthCheck(
                enabled=True,
                max_failures=3  # Default
            )
        )

    def _parse_router(
        self,
        router_name: str,
        router_config: dict,
        traefik_middlewares: dict
    ) -> Optional[Route]:
        """Parse Traefik router to GAL route."""
        # Parse rule (Traefik matcher)
        rule = router_config.get("rule", "")

        if not rule:
            return None

        # Extract path from rule (simplified)
        # Example: "PathPrefix(`/api`)"
        path_prefix = self._extract_path_from_rule(rule)

        # Parse middlewares
        middleware_names = router_config.get("middlewares", [])

        rate_limit = None
        authentication = None
        headers = None
        cors = None

        for middleware_name in middleware_names:
            if middleware_name not in traefik_middlewares:
                continue

            middleware_config = traefik_middlewares[middleware_name]

            if "rateLimit" in middleware_config:
                rate_limit = self._parse_rate_limit_middleware(
                    middleware_config["rateLimit"]
                )
            elif "basicAuth" in middleware_config:
                authentication = self._parse_basic_auth_middleware(
                    middleware_config["basicAuth"]
                )
            elif "headers" in middleware_config:
                headers = self._parse_headers_middleware(
                    middleware_config["headers"]
                )
            elif "addPrefix" in middleware_config or "stripPrefix" in middleware_config:
                # Path manipulation - not directly mappable to GAL
                self._import_warnings.append(
                    f"Path manipulation middleware '{middleware_name}' not imported"
                )

        # Check for CORS in headers middleware
        if headers and headers.response_add:
            cors = self._extract_cors_from_headers(headers)

        return Route(
            path_prefix=path_prefix,
            rate_limit=rate_limit,
            authentication=authentication,
            headers=headers,
            cors=cors
        )

    def _extract_path_from_rule(self, rule: str) -> str:
        """Extract path from Traefik rule."""
        # Simple extraction for PathPrefix
        # Example: "PathPrefix(`/api`)" → "/api"
        # Example: "Host(`example.com`) && PathPrefix(`/api`)" → "/api"

        import re

        path_match = re.search(r"PathPrefix\(`([^`]+)`\)", rule)
        if path_match:
            return path_match.group(1)

        path_match = re.search(r"Path\(`([^`]+)`\)", rule)
        if path_match:
            return path_match.group(1)

        # Default
        return "/"

    def _parse_rate_limit_middleware(self, config: dict) -> RateLimitConfig:
        """Parse Traefik rateLimit middleware."""
        average = config.get("average", 100)
        burst = config.get("burst", 200)

        # Traefik average is per second
        return RateLimitConfig(
            enabled=True,
            requests_per_second=average,
            burst=burst,
            key_type="ip_address"
        )

    def _parse_basic_auth_middleware(self, config: dict) -> AuthenticationConfig:
        """Parse Traefik basicAuth middleware."""
        users = config.get("users", [])

        # Users are hashed in Traefik, cannot import plaintext
        self._import_warnings.append(
            "Basic auth users are hashed - configure manually in GAL"
        )

        return AuthenticationConfig(
            enabled=True,
            type="basic",
            basic_auth=BasicAuth(users={})
        )

    def _parse_headers_middleware(self, config: dict) -> HeadersConfig:
        """Parse Traefik headers middleware."""
        custom_request_headers = config.get("customRequestHeaders", {})
        custom_response_headers = config.get("customResponseHeaders", {})

        request_add = custom_request_headers if custom_request_headers else None
        response_add = custom_response_headers if custom_response_headers else None

        return HeadersConfig(
            request_add=request_add,
            response_add=response_add
        )

    def _extract_cors_from_headers(self, headers: HeadersConfig) -> Optional[CorsConfig]:
        """Extract CORS config from response headers."""
        if not headers.response_add:
            return None

        cors_headers = {}
        for key, value in headers.response_add.items():
            if key.startswith("Access-Control-"):
                cors_headers[key] = value

        if not cors_headers:
            return None

        # Build CORS config
        allowed_origins = cors_headers.get("Access-Control-Allow-Origin", "*").split(",")
        allowed_methods_str = cors_headers.get("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE")
        allowed_methods = allowed_methods_str.split(",")
        allowed_headers_str = cors_headers.get("Access-Control-Allow-Headers")
        allowed_headers = allowed_headers_str.split(",") if allowed_headers_str else None
        allow_credentials = cors_headers.get("Access-Control-Allow-Credentials") == "true"
        max_age = cors_headers.get("Access-Control-Max-Age", "86400")

        # Remove CORS headers from response_add (they're now in cors config)
        for key in list(headers.response_add.keys()):
            if key.startswith("Access-Control-"):
                del headers.response_add[key]

        return CorsConfig(
            enabled=True,
            allowed_origins=allowed_origins,
            allowed_methods=allowed_methods,
            allowed_headers=allowed_headers,
            allow_credentials=allow_credentials,
            max_age=max_age
        )

    def get_import_warnings(self) -> List[str]:
        """Return warnings from last import."""
        return getattr(self, '_import_warnings', [])
```

## Feature Mapping Matrix

| GAL Feature | Traefik Config | Mapping |
|-------------|---------------|---------|
| **Service** | `http.services.<name>` | Direct mapping |
| **Upstream Targets** | `loadBalancer.servers[].url` | URL parsing → host:port |
| **Load Balancing** | `loadBalancer` (implicit) | Default: round_robin |
| **Passive Health Checks** | `loadBalancer.healthCheck` | ✅ OSS support |
| **Active Health Checks** | - | ❌ Traefik Plus only |
| **Sticky Sessions** | `loadBalancer.sticky.cookie` | ✅ Direct mapping |
| **Routes** | `http.routers.<name>` | rule → path_prefix |
| **Rate Limiting** | `middlewares.<name>.rateLimit` | average → requests_per_second |
| **Basic Auth** | `middlewares.<name>.basicAuth` | ⚠️ Users hashed |
| **Headers** | `middlewares.<name>.headers` | customRequestHeaders/customResponseHeaders |
| **CORS** | headers middleware (Access-Control-*) | Extracted from headers |
| **JWT Auth** | `middlewares.<name>.forwardAuth` | ⚠️ External auth service |

## Beispiel-Konvertierung

### Traefik Config (Input)

```yaml
http:
  routers:
    api-router:
      rule: "PathPrefix(`/api`)"
      service: api-service
      middlewares:
        - api-rate-limit
        - api-headers

  services:
    api-service:
      loadBalancer:
        servers:
          - url: "http://api-1.internal:8080"
          - url: "http://api-2.internal:8080"
        healthCheck:
          path: /health
          interval: 10s
          timeout: 5s
        sticky:
          cookie:
            name: traefik-session

  middlewares:
    api-rate-limit:
      rateLimit:
        average: 100
        burst: 200

    api-headers:
      headers:
        customRequestHeaders:
          X-Gateway: Traefik
        customResponseHeaders:
          Access-Control-Allow-Origin: "https://app.example.com"
          Access-Control-Allow-Methods: "GET,POST,PUT,DELETE"
          Access-Control-Allow-Credentials: "true"
```

### GAL Config (Output)

```yaml
version: "1.0"
provider: traefik

global_config:
  host: 0.0.0.0
  port: 80
  timeout: 30s

services:
  - name: api-service
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
        - host: api-2.internal
          port: 8080

      load_balancer:
        algorithm: round_robin
        sticky_sessions: true
        cookie_name: traefik-session

      health_check:
        passive:
          enabled: true
          max_failures: 3

    routes:
      - path_prefix: /api

        rate_limit:
          enabled: true
          requests_per_second: 100
          burst: 200
          key_type: ip_address

        headers:
          request_add:
            X-Gateway: Traefik

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
```

## CLI Usage

```bash
# Import Traefik config
gal import --provider traefik --input traefik.yaml --output gal-config.yaml

# Generate for different provider
gal generate --config gal-config.yaml --provider kong --output kong.yaml
```

## Test Cases

20+ Tests:
- Basic import (routers, services)
- Load balancer servers
- Health checks (passive)
- Sticky sessions
- Rate limiting middleware
- Basic auth middleware
- Headers middleware
- CORS extraction from headers
- Path extraction from rules
- Round-trip test

## Edge Cases

- **Traefik Plus Features**: Active health checks nicht in OSS
- **ForwardAuth**: External auth services nicht gemappt
- **Path Manipulation**: stripPrefix, addPrefix nicht mappbar
- **TCP/UDP**: Nur HTTP unterstützt
- **Dynamic Providers**: Nur File Provider

## Akzeptanzkriterien

- ✅ Import von Traefik Dynamic Config (YAML)
- ✅ Mapping von Services/Routers/Middlewares
- ✅ Sticky Sessions Support
- ✅ CORS Extraktion aus Headers
- ✅ CLI Integration
- ✅ 20+ Tests, 90%+ Coverage
- ✅ Warnings für Traefik Plus Features
- ✅ Round-trip Test

## Implementierungs-Reihenfolge

1. **Tag 1-2**: parse() + Service/Router Parsing
2. **Tag 3**: Load Balancer + Sticky Sessions
3. **Tag 4**: Middlewares (rate-limit, headers)
4. **Tag 5**: CORS Extraction + Auth
5. **Tag 6-7**: Tests + Documentation

## Nächste Schritte

Nach Completion:
1. Release als v1.3.0-alpha2 (mit APISIX)
2. User Feedback
3. Nginx Import (Feature 5) beginnen
