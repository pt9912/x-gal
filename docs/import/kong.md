# Feature 2: Kong Import (YAML Parser)

**Status:** 🔄 Geplant
**Aufwand:** 1 Woche
**Release:** v1.3.0-alpha1 (Woche 2)
**Priorität:** 🔴 Hoch

## Übersicht

Import von Kong Declarative Config (YAML/JSON) nach GAL. Kong wird parallel mit Envoy in alpha1 implementiert, da:
- Kong's Declarative Config ist klar strukturiert
- Wir kennen die Kong-Struktur bereits (haben KongProvider.generate())
- Kong ist weit verbreitet und wichtig für Adoption

## Implementierung

### Provider.parse() Methode

```python
class KongProvider(Provider):
    """Kong API Gateway Provider with Import Support."""

    def parse(self, provider_config: str) -> Config:
        """Parse Kong declarative config to GAL format.

        Args:
            provider_config: Kong YAML/JSON configuration string

        Returns:
            Config: GAL configuration object

        Raises:
            ValueError: If config is invalid or cannot be parsed
        """
        try:
            # Try YAML first
            kong_config = yaml.safe_load(provider_config)
        except yaml.YAMLError:
            # Try JSON
            try:
                kong_config = json.loads(provider_config)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid YAML/JSON: {e}")

        self._import_warnings = []

        return Config(
            version="1.0",
            provider="kong",
            global_config=self._parse_global(kong_config),
            services=self._parse_services(kong_config)
        )

    def _parse_global(self, kong_config: dict) -> GlobalConfig:
        """Extract global config from Kong."""
        # Kong doesn't have explicit global config in declarative format
        # Defaults are used
        return GlobalConfig(
            host="0.0.0.0",
            port=8000,  # Kong proxy port
            timeout="60s"
        )

    def _parse_services(self, kong_config: dict) -> List[Service]:
        """Parse Kong services to GAL services."""
        services = []

        kong_services = kong_config.get("services", [])
        kong_routes = kong_config.get("routes", [])
        kong_plugins = kong_config.get("plugins", [])
        kong_upstreams = kong_config.get("upstreams", [])
        kong_targets = kong_config.get("targets", [])

        for kong_service in kong_services:
            service = self._parse_service(
                kong_service,
                kong_routes,
                kong_plugins,
                kong_upstreams,
                kong_targets
            )
            if service:
                services.append(service)

        return services

    def _parse_service(
        self,
        kong_service: dict,
        kong_routes: list,
        kong_plugins: list,
        kong_upstreams: list,
        kong_targets: list
    ) -> Optional[Service]:
        """Convert Kong service to GAL service."""
        name = kong_service.get("name")
        if not name:
            return None

        # Parse upstream
        upstream = self._parse_upstream(
            kong_service,
            kong_upstreams,
            kong_targets
        )

        # Parse routes for this service
        routes = []
        for kong_route in kong_routes:
            if kong_route.get("service", {}).get("name") == name:
                route = self._parse_route(kong_route, kong_plugins)
                if route:
                    routes.append(route)

        return Service(
            name=name,
            upstream=upstream,
            routes=routes
        )

    def _parse_upstream(
        self,
        kong_service: dict,
        kong_upstreams: list,
        kong_targets: list
    ) -> Optional[UpstreamConfig]:
        """Parse Kong upstream to GAL upstream."""
        # Check if service has upstream
        upstream_name = kong_service.get("host")

        # Find matching upstream
        kong_upstream = None
        for upstream in kong_upstreams:
            if upstream.get("name") == upstream_name:
                kong_upstream = upstream
                break

        if kong_upstream:
            # Service uses upstream with load balancing
            targets = self._parse_targets(upstream_name, kong_targets)

            # Parse load balancing algorithm
            algorithm = self._map_lb_algorithm(
                kong_upstream.get("algorithm", "round-robin")
            )

            # Parse health checks
            health_check = self._parse_health_check(kong_upstream)

            return UpstreamConfig(
                targets=targets,
                load_balancer=LoadBalancerConfig(algorithm=algorithm),
                health_check=health_check
            )
        else:
            # Direct host:port without upstream
            host = kong_service.get("host")
            port = kong_service.get("port", 80)

            if not host:
                return None

            return UpstreamConfig(
                targets=[UpstreamTarget(host=host, port=port)],
                load_balancer=LoadBalancerConfig(algorithm="round_robin")
            )

    def _parse_targets(self, upstream_name: str, kong_targets: list) -> List[UpstreamTarget]:
        """Parse Kong targets for upstream."""
        targets = []

        for target in kong_targets:
            if target.get("upstream", {}).get("name") != upstream_name:
                continue

            target_str = target.get("target")  # Format: "host:port"
            weight = target.get("weight", 1)

            if not target_str:
                continue

            # Parse host:port
            if ":" in target_str:
                host, port_str = target_str.rsplit(":", 1)
                try:
                    port = int(port_str)
                except ValueError:
                    port = 80
            else:
                host = target_str
                port = 80

            targets.append(UpstreamTarget(
                host=host,
                port=port,
                weight=weight
            ))

        return targets

    def _map_lb_algorithm(self, kong_algorithm: str) -> str:
        """Map Kong algorithm to GAL."""
        mapping = {
            "round-robin": "round_robin",
            "least-connections": "least_conn",
            "consistent-hashing": "ip_hash",
            "latency": "least_conn"
        }
        return mapping.get(kong_algorithm, "round_robin")

    def _parse_health_check(self, kong_upstream: dict) -> Optional[HealthCheckConfig]:
        """Parse Kong health checks."""
        healthchecks = kong_upstream.get("healthchecks", {})

        active = healthchecks.get("active", {})
        passive = healthchecks.get("passive", {})

        active_hc = None
        passive_hc = None

        if active and active.get("healthy", {}).get("interval"):
            # Active health checks enabled
            healthy = active.get("healthy", {})
            unhealthy = active.get("unhealthy", {})

            http_path = active.get("http_path", "/")
            interval = f"{healthy.get('interval', 10)}s"
            timeout = f"{active.get('timeout', 5)}s"
            healthy_threshold = healthy.get("successes", 2)
            unhealthy_threshold = unhealthy.get("http_failures", 3)

            active_hc = ActiveHealthCheck(
                enabled=True,
                http_path=http_path,
                interval=interval,
                timeout=timeout,
                healthy_threshold=healthy_threshold,
                unhealthy_threshold=unhealthy_threshold,
                healthy_status_codes=[200, 302]
            )

        if passive and passive.get("healthy", {}).get("successes"):
            # Passive health checks enabled
            unhealthy = passive.get("unhealthy", {})
            max_failures = unhealthy.get("http_failures", 3)

            passive_hc = PassiveHealthCheck(
                enabled=True,
                max_failures=max_failures
            )

        if active_hc or passive_hc:
            return HealthCheckConfig(
                active=active_hc,
                passive=passive_hc
            )

        return None

    def _parse_route(self, kong_route: dict, kong_plugins: list) -> Optional[Route]:
        """Parse Kong route to GAL route."""
        # Parse paths
        paths = kong_route.get("paths", [])
        if not paths:
            return None

        path_prefix = paths[0]  # Take first path

        # Parse methods
        methods = kong_route.get("methods")

        # Parse plugins for this route
        route_name = kong_route.get("name")

        rate_limit = None
        authentication = None
        headers = None
        cors = None

        for plugin in kong_plugins:
            # Check if plugin applies to this route
            plugin_route = plugin.get("route", {}).get("name")
            if plugin_route != route_name:
                continue

            plugin_name = plugin.get("name")
            plugin_config = plugin.get("config", {})

            if plugin_name == "rate-limiting":
                rate_limit = self._parse_rate_limiting_plugin(plugin_config)
            elif plugin_name == "key-auth":
                authentication = self._parse_key_auth_plugin(plugin_config)
            elif plugin_name == "basic-auth":
                authentication = self._parse_basic_auth_plugin(plugin_config)
            elif plugin_name == "jwt":
                authentication = self._parse_jwt_plugin(plugin_config)
            elif plugin_name == "request-transformer":
                headers = self._parse_request_transformer_plugin(plugin_config)
            elif plugin_name == "response-transformer":
                if headers:
                    self._enrich_response_headers(headers, plugin_config)
                else:
                    headers = self._parse_response_transformer_plugin(plugin_config)
            elif plugin_name == "cors":
                cors = self._parse_cors_plugin(plugin_config)

        return Route(
            path_prefix=path_prefix,
            methods=methods,
            rate_limit=rate_limit,
            authentication=authentication,
            headers=headers,
            cors=cors
        )

    def _parse_rate_limiting_plugin(self, config: dict) -> RateLimitConfig:
        """Parse Kong rate-limiting plugin."""
        # Kong supports minute, hour, day, month, year
        # We'll use minute and convert to per-second
        limit_by = config.get("limit_by", "consumer")
        minute = config.get("minute")
        second = config.get("second")

        if second:
            rps = second
        elif minute:
            rps = minute // 60  # Approximation
        else:
            rps = 100  # Default

        key_type = "ip_address" if limit_by == "ip" else "header"
        key_header = "X-Consumer-ID" if limit_by == "consumer" else None

        return RateLimitConfig(
            enabled=True,
            requests_per_second=rps,
            burst=rps * 2,
            key_type=key_type,
            key_header=key_header
        )

    def _parse_key_auth_plugin(self, config: dict) -> AuthenticationConfig:
        """Parse Kong key-auth plugin."""
        return AuthenticationConfig(
            enabled=True,
            type="api_key",
            api_key_auth=ApiKeyAuth(
                header_name=config.get("key_names", ["apikey"])[0]
            )
        )

    def _parse_basic_auth_plugin(self, config: dict) -> AuthenticationConfig:
        """Parse Kong basic-auth plugin."""
        # Kong stores users separately, we can't import them
        self._import_warnings.append(
            "Basic auth users not imported - configure manually"
        )

        return AuthenticationConfig(
            enabled=True,
            type="basic",
            basic_auth=BasicAuth(
                users={}  # Must be configured manually
            )
        )

    def _parse_jwt_plugin(self, config: dict) -> AuthenticationConfig:
        """Parse Kong JWT plugin."""
        key_claim_name = config.get("key_claim_name", "iss")
        secret_is_base64 = config.get("secret_is_base64", False)

        # Extract algorithm (Kong supports multiple)
        algorithms = config.get("algorithm", "HS256")

        self._import_warnings.append(
            "JWT keys/secrets not imported - configure manually"
        )

        return AuthenticationConfig(
            enabled=True,
            type="jwt",
            jwt_auth=JWTAuth(
                secret="CONFIGURE_MANUALLY",  # Not in config
                algorithm=algorithms,
                header_name=config.get("header_names", ["authorization"])[0]
            )
        )

    def _parse_request_transformer_plugin(self, config: dict) -> HeadersConfig:
        """Parse Kong request-transformer plugin."""
        add = config.get("add", {}).get("headers", [])
        remove = config.get("remove", {}).get("headers", [])

        request_add = {}
        for header_value in add:
            # Format: "Header-Name:value"
            if ":" in header_value:
                key, value = header_value.split(":", 1)
                request_add[key] = value.strip()

        request_remove = remove if remove else None

        return HeadersConfig(
            request_add=request_add if request_add else None,
            request_remove=request_remove
        )

    def _parse_response_transformer_plugin(self, config: dict) -> HeadersConfig:
        """Parse Kong response-transformer plugin."""
        add = config.get("add", {}).get("headers", [])
        remove = config.get("remove", {}).get("headers", [])

        response_add = {}
        for header_value in add:
            if ":" in header_value:
                key, value = header_value.split(":", 1)
                response_add[key] = value.strip()

        response_remove = remove if remove else None

        return HeadersConfig(
            response_add=response_add if response_add else None,
            response_remove=response_remove
        )

    def _enrich_response_headers(self, headers: HeadersConfig, config: dict):
        """Add response headers to existing HeadersConfig."""
        add = config.get("add", {}).get("headers", [])
        remove = config.get("remove", {}).get("headers", [])

        if not headers.response_add:
            headers.response_add = {}

        for header_value in add:
            if ":" in header_value:
                key, value = header_value.split(":", 1)
                headers.response_add[key] = value.strip()

        if remove and not headers.response_remove:
            headers.response_remove = remove

    def _parse_cors_plugin(self, config: dict) -> CorsConfig:
        """Parse Kong CORS plugin."""
        origins = config.get("origins", ["*"])
        methods = config.get("methods", ["GET", "POST", "PUT", "DELETE"])
        headers = config.get("headers", [])
        credentials = config.get("credentials", False)
        max_age = config.get("max_age", 86400)

        return CorsConfig(
            enabled=True,
            allowed_origins=origins,
            allowed_methods=methods,
            allowed_headers=headers if headers else None,
            allow_credentials=credentials,
            max_age=str(max_age)
        )

    def get_import_warnings(self) -> List[str]:
        """Return warnings from last import."""
        return getattr(self, '_import_warnings', [])
```

## Feature Mapping Matrix

| GAL Feature | Kong Config | Mapping |
|-------------|------------|---------|
| **Service** | `services[].name` | Direct mapping |
| **Upstream Targets** | `targets[]` (if upstream exists) | target string → host:port |
| **Load Balancing** | `upstreams[].algorithm` | round-robin → round_robin, least-connections → least_conn |
| **Active Health Checks** | `upstreams[].healthchecks.active` | Direct mapping |
| **Passive Health Checks** | `upstreams[].healthchecks.passive` | Direct mapping |
| **Routes** | `routes[]` | paths[0] → path_prefix |
| **Rate Limiting** | `plugins[].rate-limiting` | minute/60 → requests_per_second |
| **Basic Auth** | `plugins[].basic-auth` | ✅ Supported (users not imported) |
| **API Key Auth** | `plugins[].key-auth` | ✅ Supported |
| **JWT Auth** | `plugins[].jwt` | ✅ Supported (secrets not imported) |
| **Headers** | `plugins[].request-transformer`, `response-transformer` | Direct mapping |
| **CORS** | `plugins[].cors` | Direct mapping |
| **Circuit Breaker** | - | ❌ Not available in Kong OSS |

## Beispiel-Konvertierung

### Kong Config (Input)

```yaml
_format_version: "3.0"

services:
  - name: api_service
    url: http://upstream_api
    protocol: http
    port: 80
    retries: 5

routes:
  - name: api_route
    service: api_service
    paths:
      - /api
    methods:
      - GET
      - POST

upstreams:
  - name: upstream_api
    algorithm: round-robin
    healthchecks:
      active:
        healthy:
          interval: 10
          successes: 2
        unhealthy:
          interval: 10
          http_failures: 3
        http_path: /health
        timeout: 5

targets:
  - upstream: upstream_api
    target: api-1.internal:8080
    weight: 100
  - upstream: upstream_api
    target: api-2.internal:8080
    weight: 100

plugins:
  - name: rate-limiting
    route: api_route
    config:
      minute: 6000
      policy: local

  - name: key-auth
    route: api_route
    config:
      key_names:
        - apikey

  - name: cors
    route: api_route
    config:
      origins:
        - https://app.example.com
      methods:
        - GET
        - POST
        - PUT
        - DELETE
      credentials: true
```

### GAL Config (Output)

```yaml
version: "1.0"
provider: kong

global_config:
  host: 0.0.0.0
  port: 8000
  timeout: 60s

services:
  - name: api_service
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
          weight: 100
        - host: api-2.internal
          port: 8080
          weight: 100

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
          healthy_status_codes: [200, 302]

    routes:
      - path_prefix: /api
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
            header_name: apikey

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
          max_age: "86400"
```

## CLI Usage

```bash
# Import Kong config
gal import --provider kong --input kong.yaml --output gal-config.yaml

# Import Kong JSON format
gal import --provider kong --input kong.json --output gal-config.yaml

# Validate import
gal validate --config gal-config.yaml

# Generate for different provider
gal generate --config gal-config.yaml --provider envoy --output envoy.yaml
```

## Test Cases

### Test 1: Basic Import

```python
def test_kong_import_basic():
    """Test basic Kong config import."""
    provider = KongProvider()

    kong_config = """
    _format_version: "3.0"
    services:
      - name: test_service
        url: http://test-backend:8080
    """

    config = provider.parse(kong_config)

    assert len(config.services) == 1
    assert config.services[0].name == "test_service"
    assert len(config.services[0].upstream.targets) == 1
    assert config.services[0].upstream.targets[0].host == "test-backend"
    assert config.services[0].upstream.targets[0].port == 8080
```

### Test 2: Upstream with Targets

```python
def test_kong_import_upstream_targets():
    """Test upstream and targets import."""
    provider = KongProvider()

    kong_config = """
    _format_version: "3.0"
    services:
      - name: lb_service
        url: http://lb_upstream
    upstreams:
      - name: lb_upstream
        algorithm: least-connections
    targets:
      - upstream: lb_upstream
        target: server1:8080
        weight: 2
      - upstream: lb_upstream
        target: server2:8080
        weight: 1
    """

    config = provider.parse(kong_config)

    assert config.services[0].upstream.load_balancer.algorithm == "least_conn"
    assert len(config.services[0].upstream.targets) == 2
    assert config.services[0].upstream.targets[0].weight == 2
    assert config.services[0].upstream.targets[1].weight == 1
```

### Test 3: Rate Limiting Plugin

```python
def test_kong_import_rate_limiting():
    """Test rate-limiting plugin import."""
    provider = KongProvider()

    kong_config = """
    _format_version: "3.0"
    services:
      - name: api_service
        url: http://api:8080
    routes:
      - name: api_route
        service: api_service
        paths:
          - /api
    plugins:
      - name: rate-limiting
        route: api_route
        config:
          second: 10
          minute: 600
    """

    config = provider.parse(kong_config)

    route = config.services[0].routes[0]
    assert route.rate_limit.enabled is True
    assert route.rate_limit.requests_per_second == 10
```

### Test 4: Authentication Plugins

```python
def test_kong_import_authentication():
    """Test authentication plugin import."""
    provider = KongProvider()

    kong_config = """
    _format_version: "3.0"
    services:
      - name: api_service
        url: http://api:8080
    routes:
      - name: api_route
        service: api_service
        paths:
          - /api
    plugins:
      - name: key-auth
        route: api_route
        config:
          key_names:
            - X-API-Key
    """

    config = provider.parse(kong_config)

    route = config.services[0].routes[0]
    assert route.authentication.enabled is True
    assert route.authentication.type == "api_key"
    assert route.authentication.api_key_auth.header_name == "X-API-Key"
```

### Test 5: Round-trip Test

```python
def test_kong_import_export_roundtrip():
    """Test import → export produces equivalent config."""
    provider = KongProvider()

    original_kong_config = load_fixture("kong-sample.yaml")

    # Import
    gal_config = provider.parse(original_kong_config)

    # Export
    regenerated_kong_config = provider.generate(gal_config)

    # Validate equivalence
    original_parsed = yaml.safe_load(original_kong_config)
    regenerated_parsed = yaml.safe_load(regenerated_kong_config)

    assert_configs_equivalent(original_parsed, regenerated_parsed)
```

## Edge Cases und Limitationen

### Nicht unterstützte Features

1. **Consumers** (User Management)
   - Consumers werden nicht importiert
   - Warnung beim Import
   - Muss manuell konfiguriert werden

2. **API Keys/Secrets**
   - Secrets werden aus Sicherheitsgründen nicht exportiert
   - Platzhalter in GAL Config
   - Warnung: "Configure manually"

3. **Custom Plugins**
   - Nur Standard-Plugins unterstützt
   - Custom Plugins → provider_specific

4. **Service Mesh Mode**
   - Nicht unterstützt (Kong for Kubernetes)
   - Nur Declarative Config

### Besonderheiten

- **Rate Limiting Units**: Kong unterstützt second/minute/hour/day/month/year, GAL nur requests_per_second
  - Konvertierung: minute/60 → requests_per_second
  - Warnung bei Ungenauigkeit

- **Plugin Scope**: Kong Plugins können auf service/route/consumer angewendet werden
  - Import nur für route-scoped Plugins
  - Service-scoped → alle Routes bekommen Plugin

## Warnings

Import gibt Warnungen aus für:
- Nicht importierte Consumers
- Fehlende API Keys/Secrets
- Ungenaue Rate Limit Konvertierung
- Nicht unterstützte Custom Plugins

## Akzeptanzkriterien

- ✅ Import von Kong Declarative Config (YAML/JSON)
- ✅ Mapping von Services → GAL Services
- ✅ Mapping von Upstreams + Targets
- ✅ Import von Health Checks (active + passive)
- ✅ Import von Routes
- ✅ Import von Plugins (rate-limiting, auth, cors, headers)
- ✅ CLI Integration (`gal import --provider kong`)
- ✅ 20+ Tests mit 90%+ Coverage
- ✅ Warnings für nicht importierte Secrets
- ✅ Round-trip Test

## Implementierungs-Reihenfolge

1. **Tag 1-2**: Provider.parse() + Service/Upstream Parsing
2. **Tag 3**: Routes + Basic Plugins
3. **Tag 4**: Auth Plugins (key-auth, basic-auth, jwt)
4. **Tag 5**: Headers + CORS Plugins
5. **Tag 6-7**: Tests + Documentation

## Nächste Schritte

Nach Completion:
1. Release als v1.3.0-alpha1 (zusammen mit Envoy Import)
2. User Feedback sammeln
3. APISIX Import (Feature 3) beginnen
