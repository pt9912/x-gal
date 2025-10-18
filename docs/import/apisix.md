# Feature 3: APISIX Import (JSON/YAML Parser)

**Status:** 🔄 Geplant
**Aufwand:** 1 Woche
**Release:** v1.3.0-alpha2 (Woche 4)
**Priorität:** 🟡 Mittel

## Übersicht

Import von Apache APISIX-Konfigurationen (YAML/JSON) nach GAL. APISIX wird in alpha2 implementiert, da:
- APISIX unterstützt sowohl YAML als auch JSON
- Moderne API Gateway Lösung mit wachsender Beliebtheit
- Ähnliche Struktur wie Kong, aber mit eigenen Besonderheiten

## Implementierung

### Provider.parse() Methode

```python
class APISIXProvider(Provider):
    """Apache APISIX Provider with Import Support."""

    def parse(self, provider_config: str) -> Config:
        """Parse APISIX YAML/JSON config to GAL format.

        APISIX supports both etcd and standalone (config file) mode.
        This parser handles standalone config files.

        Args:
            provider_config: APISIX YAML/JSON configuration string

        Returns:
            Config: GAL configuration object

        Raises:
            ValueError: If config is invalid or cannot be parsed
        """
        try:
            apisix_config = yaml.safe_load(provider_config)
        except yaml.YAMLError:
            try:
                apisix_config = json.loads(provider_config)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid YAML/JSON: {e}")

        self._import_warnings = []

        # APISIX config structure: routes, services, upstreams, consumers, plugins
        return Config(
            version="1.0",
            provider="apisix",
            global_config=self._parse_global(apisix_config),
            services=self._parse_services(apisix_config)
        )

    def _parse_global(self, apisix_config: dict) -> GlobalConfig:
        """Extract global config from APISIX."""
        # APISIX has deployment config separate from routes
        deployment = apisix_config.get("deployment", {})
        admin = deployment.get("admin", {})

        return GlobalConfig(
            host="0.0.0.0",
            port=9080,  # APISIX HTTP port
            timeout="60s"
        )

    def _parse_services(self, apisix_config: dict) -> List[Service]:
        """Parse APISIX services to GAL services."""
        gal_services = []

        apisix_services = apisix_config.get("services", [])
        apisix_routes = apisix_config.get("routes", [])
        apisix_upstreams = apisix_config.get("upstreams", [])
        apisix_plugins = apisix_config.get("global_rules", [])  # Global plugins

        for apisix_service in apisix_services:
            service = self._parse_service(
                apisix_service,
                apisix_routes,
                apisix_upstreams
            )
            if service:
                gal_services.append(service)

        return gal_services

    def _parse_service(
        self,
        apisix_service: dict,
        apisix_routes: list,
        apisix_upstreams: list
    ) -> Optional[Service]:
        """Convert APISIX service to GAL service."""
        service_id = apisix_service.get("id")
        name = apisix_service.get("name", f"service_{service_id}")

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

        return Service(
            name=name,
            upstream=upstream,
            routes=routes
        )

    def _parse_upstream(
        self,
        upstream_id: str,
        apisix_upstreams: list
    ) -> Optional[UpstreamConfig]:
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

            targets.append(UpstreamTarget(
                host=host,
                port=port,
                weight=weight
            ))

        # Parse load balancing type
        lb_type = apisix_upstream.get("type", "roundrobin")
        algorithm = self._map_lb_algorithm(lb_type)

        # Parse health checks
        health_check = self._parse_health_check(apisix_upstream)

        return UpstreamConfig(
            targets=targets,
            load_balancer=LoadBalancerConfig(algorithm=algorithm),
            health_check=health_check
        )

    def _map_lb_algorithm(self, apisix_type: str) -> str:
        """Map APISIX load balancing type to GAL."""
        mapping = {
            "roundrobin": "round_robin",
            "chash": "ip_hash",
            "ewma": "least_conn",
            "least_conn": "least_conn"
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
                healthy_status_codes=healthy.get("http_statuses", [200])
            )

        if passive:
            # Passive health checks
            unhealthy = passive.get("unhealthy", {})

            passive_hc = PassiveHealthCheck(
                enabled=True,
                max_failures=unhealthy.get("http_failures", 3)
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
        circuit_breaker = None

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
            circuit_breaker = self._parse_api_breaker_plugin(plugins["api-breaker"])
            self._import_warnings.append(
                f"Circuit breaker on route {uri} - review configuration"
            )

        return Route(
            path_prefix=uri,
            methods=methods,
            rate_limit=rate_limit,
            authentication=authentication,
            headers=headers,
            cors=cors
        )

    def _parse_limit_req_plugin(self, config: dict) -> RateLimitConfig:
        """Parse APISIX limit-req plugin (leaky bucket)."""
        rate = config.get("rate", 100)
        burst = config.get("burst", 200)

        return RateLimitConfig(
            enabled=True,
            requests_per_second=rate,
            burst=burst,
            key_type="ip_address"
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
            key_type="ip_address"
        )

    def _parse_key_auth_plugin(self, config: dict) -> AuthenticationConfig:
        """Parse APISIX key-auth plugin."""
        header = config.get("header", "apikey")

        return AuthenticationConfig(
            enabled=True,
            type="api_key",
            api_key_auth=ApiKeyAuth(header_name=header)
        )

    def _parse_basic_auth_plugin(self, config: dict) -> AuthenticationConfig:
        """Parse APISIX basic-auth plugin."""
        self._import_warnings.append(
            "Basic auth users not imported - configure in consumers"
        )

        return AuthenticationConfig(
            enabled=True,
            type="basic",
            basic_auth=BasicAuth(users={})
        )

    def _parse_jwt_auth_plugin(self, config: dict) -> AuthenticationConfig:
        """Parse APISIX jwt-auth plugin."""
        header = config.get("header", "authorization")
        secret = config.get("secret", "CONFIGURE_MANUALLY")

        self._import_warnings.append(
            "JWT secret not imported - configure manually"
        )

        return AuthenticationConfig(
            enabled=True,
            type="jwt",
            jwt_auth=JWTAuth(
                secret=secret,
                algorithm="HS256",
                header_name=header
            )
        )

    def _parse_proxy_rewrite_plugin(self, config: dict) -> HeadersConfig:
        """Parse APISIX proxy-rewrite plugin (request headers)."""
        headers_config = config.get("headers", {})

        request_add = {}
        request_remove = []

        for key, value in headers_config.items():
            if value is None or value == "":
                request_remove.append(key)
            else:
                request_add[key] = value

        return HeadersConfig(
            request_add=request_add if request_add else None,
            request_remove=request_remove if request_remove else None
        )

    def _parse_response_rewrite_plugin(self, config: dict) -> HeadersConfig:
        """Parse APISIX response-rewrite plugin (response headers)."""
        headers_config = config.get("headers", {})

        response_add = {}
        response_remove = []

        for key, value in headers_config.items():
            if value is None or value == "":
                response_remove.append(key)
            else:
                response_add[key] = value

        return HeadersConfig(
            response_add=response_add if response_add else None,
            response_remove=response_remove if response_remove else None
        )

    def _enrich_response_headers(self, headers: HeadersConfig, config: dict):
        """Add response headers to existing HeadersConfig."""
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

    def _parse_cors_plugin(self, config: dict) -> CorsConfig:
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

        return CorsConfig(
            enabled=True,
            allowed_origins=origins,
            allowed_methods=methods,
            allowed_headers=headers_list,
            allow_credentials=credentials,
            max_age=str(max_age)
        )

    def _parse_api_breaker_plugin(self, config: dict) -> dict:
        """Parse APISIX api-breaker plugin (Circuit Breaker)."""
        # GAL doesn't have circuit breaker in v1.2.0, store in provider_specific
        return {
            "break_response_code": config.get("break_response_code", 502),
            "max_breaker_sec": config.get("max_breaker_sec", 300),
            "unhealthy": config.get("unhealthy", {}),
            "healthy": config.get("healthy", {})
        }

    def get_import_warnings(self) -> List[str]:
        """Return warnings from last import."""
        return getattr(self, '_import_warnings', [])
```

## Feature Mapping Matrix

| GAL Feature | APISIX Config | Mapping |
|-------------|--------------|---------|
| **Service** | `services[].name` | Direct mapping |
| **Upstream Targets** | `upstreams[].nodes` | "host:port" → UpstreamTarget |
| **Load Balancing** | `upstreams[].type` | roundrobin → round_robin, chash → ip_hash |
| **Active Health Checks** | `upstreams[].checks.active` | Direct mapping |
| **Passive Health Checks** | `upstreams[].checks.passive` | Direct mapping |
| **Routes** | `routes[].uri` | Direct mapping |
| **Rate Limiting** | `plugins.limit-req` or `limit-count` | rate/time_window → requests_per_second |
| **Basic Auth** | `plugins.basic-auth` | ✅ (users in consumers) |
| **API Key Auth** | `plugins.key-auth` | ✅ Direct mapping |
| **JWT Auth** | `plugins.jwt-auth` | ✅ (secret must be configured) |
| **Headers** | `plugins.proxy-rewrite`, `response-rewrite` | Direct mapping |
| **CORS** | `plugins.cors` | Direct mapping |
| **Circuit Breaker** | `plugins.api-breaker` | ⚠️ Future feature |

## Beispiel-Konvertierung

### APISIX Config (Input)

```yaml
routes:
  - id: 1
    name: api_route
    uri: /api/*
    methods:
      - GET
      - POST
    service_id: api_service
    plugins:
      limit-req:
        rate: 100
        burst: 200
        key: remote_addr
      key-auth:
        header: X-API-Key
      cors:
        allow_origins: https://app.example.com
        allow_methods: GET,POST,PUT,DELETE
        allow_credential: true

services:
  - id: api_service
    name: api_service
    upstream_id: api_upstream

upstreams:
  - id: api_upstream
    name: api_upstream
    type: roundrobin
    nodes:
      "api-1.internal:8080": 1
      "api-2.internal:8080": 1
    checks:
      active:
        http_path: /health
        interval: 10
        timeout: 5
        healthy:
          successes: 2
          http_statuses: [200]
        unhealthy:
          http_failures: 3
```

### GAL Config (Output)

```yaml
version: "1.0"
provider: apisix

global_config:
  host: 0.0.0.0
  port: 9080
  timeout: 60s

services:
  - name: api_service
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
          weight: 1
        - host: api-2.internal
          port: 8080
          weight: 1

      load_balancer:
        algorithm: round_robin

      health_check:
        active:
          enabled: true
          http_path: /health
          interval: 10s
          timeout: 5s
          healthy_threshold: 2
          unhealthy_threshold: 3
          healthy_status_codes: [200]

    routes:
      - path_prefix: /api/*
        methods:
          - GET
          - POST

        rate_limit:
          enabled: true
          requests_per_second: 100
          burst: 200
          key_type: ip_address

        authentication:
          enabled: true
          type: api_key
          api_key_auth:
            header_name: X-API-Key

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
# Import APISIX config
gal import --provider apisix --input apisix.yaml --output gal-config.yaml

# Validate
gal validate --config gal-config.yaml

# Generate for different provider
gal generate --config gal-config.yaml --provider nginx --output nginx.conf
```

## Test Cases

20+ Tests abdecken:
- Basic import (services, upstreams, routes)
- Load balancing algorithms
- Health checks (active + passive)
- Rate limiting (limit-req, limit-count)
- Authentication (key-auth, basic-auth, jwt-auth)
- Headers (proxy-rewrite, response-rewrite)
- CORS
- Circuit breaker (api-breaker)
- Round-trip test

## Edge Cases

- **etcd Mode**: Nicht unterstützt, nur standalone config
- **Consumers**: Nicht importiert, Warnung
- **Custom Plugins**: Nicht gemappt, provider_specific
- **Stream Routes**: Nicht unterstützt (nur HTTP)

## Akzeptanzkriterien

- ✅ Import von APISIX YAML/JSON
- ✅ Mapping von Services/Upstreams/Routes
- ✅ Import von allen Standard-Plugins
- ✅ CLI Integration
- ✅ 20+ Tests, 90%+ Coverage
- ✅ Warnings für nicht unterstützte Features
- ✅ Round-trip Test

## Implementierungs-Reihenfolge

1. **Tag 1-2**: parse() + Service/Upstream Parsing
2. **Tag 3**: Routes + Basic Plugins (rate-limit)
3. **Tag 4**: Auth Plugins
4. **Tag 5**: Headers + CORS
5. **Tag 6-7**: Tests + Documentation

## Nächste Schritte

Nach Completion:
1. Release als v1.3.0-alpha2 (mit Traefik Import)
2. User Feedback
3. Traefik Import (Feature 4) testen
