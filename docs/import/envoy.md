# Feature 1: Envoy Import (YAML Parser)

**Status:** 🔄 Geplant
**Aufwand:** 1 Woche
**Release:** v1.3.0-alpha1 (Woche 2)
**Priorität:** 🔴 Hoch

## Übersicht

Import von Envoy YAML-Konfigurationen nach GAL. Envoy ist der erste Provider, der implementiert wird, da:
- Envoy YAML ist gut strukturiert und dokumentiert
- Wir kennen die Envoy-Struktur bereits (haben EnvoyProvider.generate())
- Dient als Referenz-Implementierung für andere YAML-Parser

## Implementierung

### Provider.parse() Methode

```python
class EnvoyProvider(Provider):
    """Envoy Gateway Provider with Import Support."""

    def parse(self, provider_config: str) -> Config:
        """Parse Envoy YAML config to GAL format.

        Args:
            provider_config: Envoy YAML configuration string

        Returns:
            Config: GAL configuration object

        Raises:
            ValueError: If config is invalid or cannot be parsed
        """
        try:
            envoy_config = yaml.safe_load(provider_config)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

        self._import_warnings = []

        return Config(
            version="1.0",
            provider="envoy",
            global_config=self._parse_global(envoy_config),
            services=self._parse_services(envoy_config)
        )

    def _parse_global(self, envoy_config: dict) -> GlobalConfig:
        """Extract global config from Envoy admin section."""
        admin = envoy_config.get("admin", {})

        return GlobalConfig(
            host="0.0.0.0",  # Envoy binds in listeners
            port=10000,      # Default admin port
            timeout="30s"
        )

    def _parse_services(self, envoy_config: dict) -> List[Service]:
        """Parse Envoy clusters and listeners to GAL services."""
        services = []

        # Parse clusters
        clusters = envoy_config.get("static_resources", {}).get("clusters", [])

        for cluster in clusters:
            service = self._parse_cluster(cluster)
            if service:
                services.append(service)

        # Parse listeners and routes
        listeners = envoy_config.get("static_resources", {}).get("listeners", [])

        for listener in listeners:
            self._enrich_services_from_listener(services, listener)

        return services

    def _parse_cluster(self, cluster: dict) -> Optional[Service]:
        """Convert Envoy cluster to GAL service."""
        name = cluster.get("name")
        if not name:
            return None

        # Parse upstream targets
        targets = []
        load_assignment = cluster.get("load_assignment", {})
        endpoints = load_assignment.get("endpoints", [])

        for endpoint_group in endpoints:
            lb_endpoints = endpoint_group.get("lb_endpoints", [])

            for lb_endpoint in lb_endpoints:
                endpoint = lb_endpoint.get("endpoint", {})
                address = endpoint.get("address", {}).get("socket_address", {})

                host = address.get("address")
                port = address.get("port_value")

                if host and port:
                    targets.append(UpstreamTarget(
                        host=host,
                        port=port
                    ))

        # Parse load balancing policy
        lb_policy = cluster.get("lb_policy", "ROUND_ROBIN")
        algorithm = self._map_lb_algorithm(lb_policy)

        # Parse health checks
        health_check = None
        health_checks = cluster.get("health_checks", [])

        if health_checks:
            health_check = self._parse_health_check(health_checks[0])

        # Build upstream config
        upstream = None
        if targets:
            upstream = UpstreamConfig(
                targets=targets,
                load_balancer=LoadBalancerConfig(algorithm=algorithm),
                health_check=health_check
            )

        return Service(
            name=name,
            upstream=upstream,
            routes=[]  # Routes added later from listeners
        )

    def _map_lb_algorithm(self, envoy_policy: str) -> str:
        """Map Envoy LB policy to GAL algorithm."""
        mapping = {
            "ROUND_ROBIN": "round_robin",
            "LEAST_REQUEST": "least_conn",
            "RING_HASH": "ip_hash",
            "RANDOM": "round_robin",
            "MAGLEV": "ip_hash"
        }
        return mapping.get(envoy_policy, "round_robin")

    def _parse_health_check(self, health_check: dict) -> HealthCheckConfig:
        """Parse Envoy health check to GAL format."""
        http_health_check = health_check.get("http_health_check", {})

        if not http_health_check:
            # No HTTP health check
            return None

        interval = health_check.get("interval", "10s")
        timeout = health_check.get("timeout", "5s")
        unhealthy_threshold = health_check.get("unhealthy_threshold", 3)
        healthy_threshold = health_check.get("healthy_threshold", 2)

        path = http_health_check.get("path", "/health")

        return HealthCheckConfig(
            active=ActiveHealthCheck(
                enabled=True,
                http_path=path,
                interval=interval,
                timeout=timeout,
                unhealthy_threshold=unhealthy_threshold,
                healthy_threshold=healthy_threshold,
                healthy_status_codes=[200]
            )
        )

    def _enrich_services_from_listener(self, services: List[Service], listener: dict):
        """Add routes to services from Envoy listener config."""
        filter_chains = listener.get("filter_chains", [])

        for filter_chain in filter_chains:
            filters = filter_chain.get("filters", [])

            for filter_config in filters:
                if filter_config.get("name") != "envoy.filters.network.http_connection_manager":
                    continue

                typed_config = filter_config.get("typed_config", {})
                route_config = typed_config.get("route_config", {})
                virtual_hosts = route_config.get("virtual_hosts", [])

                for vhost in virtual_hosts:
                    routes = vhost.get("routes", [])

                    for route_entry in routes:
                        self._add_route_to_service(services, route_entry)

    def _add_route_to_service(self, services: List[Service], route_entry: dict):
        """Add route from Envoy route config to matching service."""
        match = route_entry.get("match", {})
        route = route_entry.get("route", {})

        # Get cluster name (service name)
        cluster_name = route.get("cluster")
        if not cluster_name:
            return

        # Find service
        service = next((s for s in services if s.name == cluster_name), None)
        if not service:
            return

        # Parse path
        path_prefix = match.get("prefix", "/")

        # Parse rate limiting
        rate_limit_config = None
        rate_limits = route_entry.get("rate_limits", [])

        if rate_limits:
            rate_limit_config = self._parse_rate_limit(rate_limits[0])

        # Parse headers
        request_headers_to_add = route_entry.get("request_headers_to_add", [])
        response_headers_to_add = route_entry.get("response_headers_to_add", [])

        headers_config = None
        if request_headers_to_add or response_headers_to_add:
            headers_config = self._parse_headers(
                request_headers_to_add,
                response_headers_to_add
            )

        # Parse CORS
        cors_config = None
        cors = route_entry.get("cors", {})
        if cors:
            cors_config = self._parse_cors(cors)

        # Create route
        gal_route = Route(
            path_prefix=path_prefix,
            rate_limit=rate_limit_config,
            headers=headers_config,
            cors=cors_config
        )

        service.routes.append(gal_route)

    def _parse_rate_limit(self, rate_limit: dict) -> RateLimitConfig:
        """Parse Envoy rate limit to GAL format."""
        # Envoy rate limiting is complex, simplified here
        self._import_warnings.append(
            "Rate limiting config simplified - manual review recommended"
        )

        return RateLimitConfig(
            enabled=True,
            requests_per_second=100,  # Default
            burst=200
        )

    def _parse_headers(self, request_headers: list, response_headers: list) -> HeadersConfig:
        """Parse Envoy headers to GAL format."""
        request_add = {}
        response_add = {}

        for header in request_headers:
            key = header.get("header", {}).get("key")
            value = header.get("header", {}).get("value")
            if key and value:
                request_add[key] = value

        for header in response_headers:
            key = header.get("header", {}).get("key")
            value = header.get("header", {}).get("value")
            if key and value:
                response_add[key] = value

        return HeadersConfig(
            request_add=request_add if request_add else None,
            response_add=response_add if response_add else None
        )

    def _parse_cors(self, cors: dict) -> CorsConfig:
        """Parse Envoy CORS to GAL format."""
        return CorsConfig(
            enabled=True,
            allowed_origins=cors.get("allow_origin_string_match", []),
            allowed_methods=cors.get("allow_methods", "GET,POST,PUT,DELETE").split(","),
            allowed_headers=cors.get("allow_headers", "").split(",") if cors.get("allow_headers") else None,
            allow_credentials=cors.get("allow_credentials", False),
            max_age=cors.get("max_age", "86400")
        )

    def get_import_warnings(self) -> List[str]:
        """Return warnings from last import."""
        return getattr(self, '_import_warnings', [])
```

## Feature Mapping Matrix

| GAL Feature | Envoy Config | Mapping |
|-------------|-------------|---------|
| **Service** | `clusters[].name` | Direct mapping |
| **Upstream Targets** | `load_assignment.endpoints` | socket_address → host:port |
| **Load Balancing** | `lb_policy` | ROUND_ROBIN → round_robin, LEAST_REQUEST → least_conn |
| **Active Health Checks** | `health_checks[].http_health_check` | Direct mapping with interval/timeout |
| **Passive Health Checks** | `outlier_detection` | ⚠️ Supported but complex |
| **Routes** | `route_config.virtual_hosts[].routes` | match.prefix → path_prefix |
| **Rate Limiting** | `rate_limits` | ⚠️ Simplified - complex in Envoy |
| **Headers** | `request_headers_to_add`, `response_headers_to_add` | Direct mapping |
| **CORS** | `cors` policy | Direct mapping |
| **Circuit Breaker** | `circuit_breakers` | ⚠️ Not in initial import |
| **Authentication** | `jwt_authn`, `ext_authz` | ⚠️ Not in initial import |

## Beispiel-Konvertierung

### Envoy Config (Input)

```yaml
admin:
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 9901

static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 80
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/api"
                          route:
                            cluster: api_service
                          request_headers_to_add:
                            - header:
                                key: X-Gateway
                                value: Envoy
                http_filters:
                  - name: envoy.filters.http.router

  clusters:
    - name: api_service
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: api_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: api-1.internal
                      port_value: 8080
              - endpoint:
                  address:
                    socket_address:
                      address: api-2.internal
                      port_value: 8080
      health_checks:
        - timeout: 5s
          interval: 10s
          unhealthy_threshold: 3
          healthy_threshold: 2
          http_health_check:
            path: /health
```

### GAL Config (Output)

```yaml
version: "1.0"
provider: envoy

global_config:
  host: 0.0.0.0
  port: 10000
  timeout: 30s

services:
  - name: api_service
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
        - host: api-2.internal
          port: 8080

      load_balancer:
        algorithm: round_robin

      health_check:
        active:
          enabled: true
          http_path: /health
          interval: 10s
          timeout: 5s
          unhealthy_threshold: 3
          healthy_threshold: 2
          healthy_status_codes: [200]

    routes:
      - path_prefix: /api
        headers:
          request_add:
            X-Gateway: Envoy
```

## CLI Usage

```bash
# Import Envoy config
gal import --provider envoy --input envoy.yaml --output gal-config.yaml

# Validate import
gal validate --config gal-config.yaml

# Generate for different provider
gal generate --config gal-config.yaml --provider kong --output kong.yaml

# Complete migration workflow
gal import --provider envoy --input envoy.yaml --output gal.yaml
gal generate --config gal.yaml --provider haproxy --output haproxy.cfg
```

## Test Cases

### Test 1: Basic Import

```python
def test_envoy_import_basic():
    """Test basic Envoy config import."""
    provider = EnvoyProvider()

    envoy_config = """
    static_resources:
      clusters:
        - name: test_service
          type: STATIC
          load_assignment:
            cluster_name: test_service
            endpoints:
              - lb_endpoints:
                  - endpoint:
                      address:
                        socket_address:
                          address: 127.0.0.1
                          port_value: 8080
    """

    config = provider.parse(envoy_config)

    assert len(config.services) == 1
    assert config.services[0].name == "test_service"
    assert len(config.services[0].upstream.targets) == 1
    assert config.services[0].upstream.targets[0].host == "127.0.0.1"
    assert config.services[0].upstream.targets[0].port == 8080
```

### Test 2: Load Balancing

```python
def test_envoy_import_load_balancing():
    """Test LB algorithm mapping."""
    provider = EnvoyProvider()

    envoy_config = """
    static_resources:
      clusters:
        - name: lb_service
          lb_policy: LEAST_REQUEST
          load_assignment:
            cluster_name: lb_service
            endpoints:
              - lb_endpoints:
                  - endpoint:
                      address:
                        socket_address:
                          address: server1
                          port_value: 8080
    """

    config = provider.parse(envoy_config)

    assert config.services[0].upstream.load_balancer.algorithm == "least_conn"
```

### Test 3: Health Checks

```python
def test_envoy_import_health_checks():
    """Test health check import."""
    provider = EnvoyProvider()

    envoy_config = """
    static_resources:
      clusters:
        - name: hc_service
          health_checks:
            - timeout: 3s
              interval: 5s
              unhealthy_threshold: 2
              healthy_threshold: 3
              http_health_check:
                path: /status
          load_assignment:
            cluster_name: hc_service
            endpoints:
              - lb_endpoints:
                  - endpoint:
                      address:
                        socket_address:
                          address: server1
                          port_value: 8080
    """

    config = provider.parse(envoy_config)

    hc = config.services[0].upstream.health_check
    assert hc.active.enabled is True
    assert hc.active.http_path == "/status"
    assert hc.active.interval == "5s"
    assert hc.active.timeout == "3s"
    assert hc.active.unhealthy_threshold == 2
    assert hc.active.healthy_threshold == 3
```

### Test 4: Routes and Headers

```python
def test_envoy_import_routes_headers():
    """Test route and header import."""
    provider = EnvoyProvider()

    envoy_config = """
    static_resources:
      listeners:
        - name: listener_0
          filter_chains:
            - filters:
                - name: envoy.filters.network.http_connection_manager
                  typed_config:
                    route_config:
                      virtual_hosts:
                        - name: backend
                          domains: ["*"]
                          routes:
                            - match:
                                prefix: "/api/v1"
                              route:
                                cluster: api_service
                              request_headers_to_add:
                                - header:
                                    key: X-Version
                                    value: "1.0"
      clusters:
        - name: api_service
          load_assignment:
            cluster_name: api_service
            endpoints:
              - lb_endpoints:
                  - endpoint:
                      address:
                        socket_address:
                          address: api
                          port_value: 8080
    """

    config = provider.parse(envoy_config)

    assert len(config.services[0].routes) == 1
    route = config.services[0].routes[0]
    assert route.path_prefix == "/api/v1"
    assert route.headers.request_add["X-Version"] == "1.0"
```

### Test 5: Round-trip (Import → Export)

```python
def test_envoy_import_export_roundtrip():
    """Test import + export produces equivalent config."""
    provider = EnvoyProvider()

    original_envoy_config = load_fixture("envoy-sample.yaml")

    # Import
    gal_config = provider.parse(original_envoy_config)

    # Export
    regenerated_envoy_config = provider.generate(gal_config)

    # Validate equivalence (semantically, not byte-for-byte)
    original_parsed = yaml.safe_load(original_envoy_config)
    regenerated_parsed = yaml.safe_load(regenerated_envoy_config)

    assert_configs_equivalent(original_parsed, regenerated_parsed)
```

## Edge Cases und Limitationen

### Nicht unterstützte Features

1. **JWT Authentication** (`jwt_authn`)
   - Warnung beim Import
   - In `provider_specific` Section gespeichert
   - Muss manuell gemappt werden

2. **External Authorization** (`ext_authz`)
   - Nicht direkt mappbar
   - Warnung + provider_specific

3. **Complex Rate Limiting** (mit externem Rate Limit Service)
   - Vereinfachung auf einfache Limits
   - Warnung ausgeben

4. **Circuit Breaker** (`circuit_breakers`)
   - Zukünftige Erweiterung
   - Aktuell: Warnung

### Nicht-Standard Envoy Configs

- **Dynamic Resources** (xDS): Nicht unterstützt, nur static_resources
- **Filters**: Nur http_connection_manager und router unterstützt
- **Custom Filters**: In provider_specific gespeichert

## Warnings

Import gibt Warnungen aus für:
- Vereinfachte Rate Limiting Konfiguration
- Nicht gemappte Filter
- Fehlende Cluster-Definitionen
- Nicht unterstützte Features

```python
warnings = provider.get_import_warnings()
for warning in warnings:
    print(f"⚠️  {warning}")
```

## Akzeptanzkriterien

- ✅ Import von Envoy YAML-Konfigurationen
- ✅ Mapping von Clusters → Services
- ✅ Mapping von Load Balancing Policies
- ✅ Import von Health Checks (active)
- ✅ Import von Routes aus Listeners
- ✅ Import von Headers (request/response)
- ✅ Import von CORS Policies
- ✅ CLI Integration (`gal import --provider envoy`)
- ✅ 20+ Tests mit 90%+ Coverage
- ✅ Warnings für nicht unterstützte Features
- ✅ Round-trip Test (Import → Export → Import)

## Implementierungs-Reihenfolge

1. **Tag 1-2**: Provider.parse() Methode + Cluster Parsing
2. **Tag 3**: Load Balancing + Health Checks
3. **Tag 4**: Listener + Route Parsing
4. **Tag 5**: Headers + CORS Import
5. **Tag 6-7**: Tests + Documentation

## Nächste Schritte

Nach Completion:
1. Release als v1.3.0-alpha1
2. User Feedback sammeln
3. Kong Import (Feature 2) beginnen
