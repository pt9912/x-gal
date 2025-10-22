# Envoy Feature-Implementierungen

**Detaillierte Implementierung aller Features für Envoy Proxy Provider in GAL**

**Navigation:**
- [← Zurück zur Envoy Übersicht](ENVOY.md)
- [→ Migration & Best Practices](ENVOY_DEPLOYMENT.md)

## Inhaltsverzeichnis

1. [Feature-Implementierungen](#feature-implementierungen)
2. [Envoy Feature Coverage](#envoy-feature-coverage)
3. [Envoy-spezifische Details](#envoy-spezifische-details)
4. [Advanced Features](#advanced-features)
5. [Request Mirroring/Shadowing](#request-mirroringshadowing)

---
## Feature-Implementierungen

### 1. Load Balancing

Envoy unterstützt die meisten Load Balancing Algorithmen:

```yaml
load_balancer:
  algorithm: round_robin    # ROUND_ROBIN
  # algorithm: least_conn    # LEAST_REQUEST
  # algorithm: ip_hash       # RING_HASH (Consistent Hashing)
  # algorithm: weighted      # ROUND_ROBIN mit Weights
```

**Generierte Envoy Config**:
```yaml
lb_policy: ROUND_ROBIN      # oder LEAST_REQUEST, RING_HASH
```

**Algorithmen**:
- `round_robin` → `ROUND_ROBIN` (Default)
- `least_conn` → `LEAST_REQUEST` (bevorzugt Server mit wenigsten aktiven Requests)
- `ip_hash` → `RING_HASH` (Consistent Hashing, Session Persistence)
- `weighted` → `ROUND_ROBIN` + `load_balancing_weight`

### 2. Health Checks

**Active Health Checks**:
```yaml
health_check:
  active:
    enabled: true
    interval: "10s"           # Probe-Intervall
    timeout: "5s"             # Probe-Timeout
    http_path: "/health"      # Health Endpoint
    healthy_threshold: 2      # Erfolge bis "healthy"
    unhealthy_threshold: 3    # Fehler bis "unhealthy"
    healthy_status_codes: [200, 204]
```

**Generiert**:
```yaml
health_checks:
- timeout: 5s
  interval: 10s
  unhealthy_threshold: 3
  healthy_threshold: 2
  http_health_check:
    path: /health
    expected_statuses:
    - start: 200
      end: 201
    - start: 204
      end: 205
```

**Passive Health Checks** (Outlier Detection):
```yaml
health_check:
  passive:
    enabled: true
    max_failures: 5           # Max Fehler
    failure_window: "30s"     # Zeitfenster
```

**Generiert**:
```yaml
outlier_detection:
  consecutive_5xx: 5
  interval: 30s
  base_ejection_time: 30s
  max_ejection_percent: 50
```

### 3. Rate Limiting

```yaml
rate_limit:
  enabled: true
  requests_per_second: 100
  burst: 200
  response_status: 429
```

**Generiert** (Global Rate Limit Service):
```yaml
http_filters:
- name: envoy.filters.http.ratelimit
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
    domain: gal_ratelimit
    rate_limit_service:
      grpc_service:
        envoy_grpc:
          cluster_name: rate_limit_service
```

**Hinweis**: Envoy benötigt einen externen Rate Limit Service (z.B. [lyft/ratelimit](https://github.com/envoyproxy/ratelimit)).

### 4. Authentication

**JWT Validation**:
```yaml
authentication:
  enabled: true
  type: jwt
  jwt:
    issuer: "https://auth.example.com"
    audiences: ["api"]
    jwks_uri: "https://auth.example.com/.well-known/jwks.json"
```

**Generiert**:
```yaml
http_filters:
- name: envoy.filters.http.jwt_authn
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication
    providers:
      jwt_provider:
        issuer: https://auth.example.com
        audiences:
        - api
        remote_jwks:
          http_uri:
            uri: https://auth.example.com/.well-known/jwks.json
            cluster: jwt_cluster
          cache_duration: 3600s
    rules:
    - match:
        prefix: /api
      requires:
        provider_name: jwt_provider
```

**Basic Auth** (via Lua Filter):
```yaml
authentication:
  enabled: true
  type: basic
  basic_auth:
    users:
      admin: password123
```

**Generiert Lua Filter** für Basic Auth Validation.

### 5. CORS

```yaml
cors:
  enabled: true
  allowed_origins: ["https://app.example.com"]
  allowed_methods: ["GET", "POST", "PUT", "DELETE"]
  allowed_headers: ["Content-Type", "Authorization"]
  allow_credentials: true
  max_age: 86400
```

**Generiert**:
```yaml
cors:
  allow_origin_string_match:
  - exact: https://app.example.com
  allow_methods: "GET,POST,PUT,DELETE"
  allow_headers: "Content-Type,Authorization"
  allow_credentials: true
  max_age: "86400"
```

### 6. Timeout & Retry

```yaml
timeout:
  connect: "5s"
  read: "60s"
  idle: "300s"
retry:
  enabled: true
  attempts: 3
  backoff: exponential
  base_interval: "25ms"
  max_interval: "250ms"
  retry_on:
    - connect_timeout
    - http_5xx
```

**Generiert**:
```yaml
# Cluster-level
connect_timeout: 5s

# Route-level
timeout: 60s
idle_timeout: 300s
retry_policy:
  num_retries: 3
  per_try_timeout: 25ms
  retry_on: "connect-failure,5xx"
```

### 7. Circuit Breaker

```yaml
circuit_breaker:
  enabled: true
  max_failures: 5
  timeout: "30s"
  unhealthy_status_codes: [500, 502, 503, 504]
```

**Generiert** (Outlier Detection):
```yaml
outlier_detection:
  consecutive_5xx: 5
  interval: 30s
  base_ejection_time: 30s
  max_ejection_percent: 50
  enforcing_consecutive_5xx: 100
```

### 8. WebSocket

```yaml
websocket:
  enabled: true
  idle_timeout: "600s"
  ping_interval: "30s"
```

**Generiert**:
```yaml
upgrade_configs:
- upgrade_type: websocket
http_protocol_options:
  idle_timeout: 600s
```

### 9. Request/Response Headers

```yaml
headers:
  request_add:
    X-Request-ID: "{{uuid}}"
    X-Forwarded-Proto: "https"
  request_remove:
    - X-Internal-Secret
  response_add:
    X-Gateway: "GAL-Envoy"
  response_remove:
    - X-Powered-By
```

**Generiert**:
```yaml
request_headers_to_add:
- header:
    key: X-Request-ID
    value: "%REQ(X-REQUEST-ID)%"
  append: false
request_headers_to_remove:
- X-Internal-Secret
response_headers_to_add:
- header:
    key: X-Gateway
    value: GAL-Envoy
response_headers_to_remove:
- X-Powered-By
```

### 10. Body Transformation

```yaml
body_transformation:
  enabled: true
  request:
    add_fields:
      trace_id: "{{uuid}}"
    remove_fields:
      - secret_key
  response:
    filter_fields:
      - password
```

**Generiert Lua Filter**:
```yaml
http_filters:
- name: envoy.filters.http.lua
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
    inline_code: |
      function envoy_on_request(request_handle)
        -- Transform request body
      end
      function envoy_on_response(response_handle)
        -- Transform response body
      end
```

---

## Provider-Vergleich

### Envoy vs. Andere Provider

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy |
|---------|-------|------|--------|---------|-------|---------|
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Feature-Set** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Observability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Cloud-Native** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Lernkurve** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Dokumentation** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**Envoy Stärken**:
- ✅ **Umfassendstes Feature-Set** aller Provider
- ✅ **Native Observability** (Metrics, Tracing, Logging)
- ✅ **Service Mesh Ready** (Istio, Consul, Linkerd)
- ✅ **Modern & Cloud-Native**
- ✅ **Hot Reload** ohne Downtime
- ✅ **gRPC Native** (HTTP/2)

**Envoy Schwächen**:
- ❌ **Steile Lernkurve** (komplexe YAML-Config)
- ❌ **Verbose Config** (sehr lang)
- ⚠️ **Basic Auth** nicht nativ (Lua/External)
- ⚠️ **Rate Limiting** benötigt externen Service

---

## Envoy Feature Coverage

Detaillierte Analyse basierend auf der [offiziellen Envoy Dokumentation](https://www.envoyproxy.io/docs).

### HTTP Filters (envoy.filters.http.*)

| Filter | Import | Export | Status | Bemerkung |
|--------|--------|--------|--------|-----------|
| `router` | ✅ | ✅ | Voll | HTTP Routing, immer aktiviert |
| `jwt_authn` | ✅ | ✅ | Voll | JWT Validation mit JWKS |
| `cors` | ✅ | ✅ | Voll | CORS Policy (native) |
| `lua` | ❌ | ✅ | Export | Body Transformation, Basic Auth |
| `ratelimit` | ⚠️ | ⚠️ | Teilweise | Benötigt externen Service |
| `local_ratelimit` | ❌ | ⚠️ | Export | Local Rate Limiting (ohne Service) |
| `ext_authz` | ❌ | ⚠️ | Export | External Authorization (OPA, etc.) |
| `fault` | ❌ | ❌ | Nicht | Fault Injection |
| `grpc_json_transcoder` | ❌ | ❌ | Nicht | gRPC-JSON Transformation |
| `header_to_metadata` | ❌ | ❌ | Nicht | Header → Metadata Mapping |
| `ip_tagging` | ❌ | ❌ | Nicht | IP Tagging |
| `buffer` | ❌ | ❌ | Nicht | Request/Response Buffering |
| `gzip` | ❌ | ❌ | Nicht | Compression |
| `adaptive_concurrency` | ❌ | ❌ | Nicht | Adaptive Concurrency Control |

### Network Filters (envoy.filters.network.*)

| Filter | Import | Export | Status | Bemerkung |
|--------|--------|--------|--------|-----------|
| `http_connection_manager` | ✅ | ✅ | Voll | HTTP Connection Manager (core) |
| `tcp_proxy` | ❌ | ❌ | Nicht | TCP Proxying |
| `redis_proxy` | ❌ | ❌ | Nicht | Redis Proxying |
| `mongo_proxy` | ❌ | ❌ | Nicht | MongoDB Proxying |
| `mysql_proxy` | ❌ | ❌ | Nicht | MySQL Proxying |

### Cluster Features

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| `load_assignment` | ✅ | ✅ | Voll | Endpoints mit IP:Port |
| `lb_policy` (ROUND_ROBIN) | ✅ | ✅ | Voll | Round Robin Load Balancing |
| `lb_policy` (LEAST_REQUEST) | ✅ | ✅ | Voll | Least Connections |
| `lb_policy` (RING_HASH) | ✅ | ✅ | Voll | Consistent Hashing (IP Hash) |
| `lb_policy` (RANDOM) | ⚠️ | ⚠️ | Teilweise | Random Selection |
| `lb_policy` (MAGLEV) | ❌ | ❌ | Nicht | Maglev Hashing |
| `health_checks` (HTTP) | ✅ | ✅ | Voll | Active Health Checks |
| `health_checks` (TCP) | ❌ | ❌ | Nicht | TCP Health Checks |
| `health_checks` (gRPC) | ❌ | ❌ | Nicht | gRPC Health Checks |
| `outlier_detection` | ✅ | ✅ | Voll | Passive Health Checks / Circuit Breaker |
| `circuit_breakers` | ⚠️ | ⚠️ | Teilweise | Connection/Request Limits |
| `upstream_connection_options` | ❌ | ❌ | Nicht | TCP Keepalive |
| `dns_lookup_family` | ❌ | ✅ | Export | V4_ONLY (Default) |
| `transport_socket` (TLS) | ❌ | ❌ | Nicht | Upstream TLS |

### Route Configuration Features

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| `match.prefix` | ✅ | ✅ | Voll | Path Prefix Matching |
| `match.path` | ✅ | ✅ | Voll | Exact Path Matching |
| `match.safe_regex` | ❌ | ❌ | Nicht | Regex Path Matching |
| `match.headers` | ❌ | ❌ | Nicht | Header-based Routing |
| `match.query_parameters` | ❌ | ❌ | Nicht | Query Parameter Matching |
| `route.cluster` | ✅ | ✅ | Voll | Single Cluster Routing |
| `route.weighted_clusters` | ⚠️ | ⚠️ | Teilweise | Traffic Splitting |
| `route.timeout` | ✅ | ✅ | Voll | Request Timeout |
| `route.idle_timeout` | ✅ | ✅ | Voll | Idle Timeout |
| `route.retry_policy` | ✅ | ✅ | Voll | Retry mit Exponential Backoff |
| `route.cors` | ✅ | ✅ | Voll | Per-Route CORS |
| `route.upgrade_configs` (WebSocket) | ✅ | ✅ | Voll | WebSocket Support |
| `request_headers_to_add` | ✅ | ✅ | Voll | Request Header Manipulation |
| `request_headers_to_remove` | ✅ | ✅ | Voll | Request Header Removal |
| `response_headers_to_add` | ✅ | ✅ | Voll | Response Header Manipulation |
| `response_headers_to_remove` | ✅ | ✅ | Voll | Response Header Removal |
| `route.metadata` | ❌ | ❌ | Nicht | Route Metadata |
| `route.decorator` | ❌ | ❌ | Nicht | Tracing Decorator |

### Listener Features

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| `address.socket_address` | ✅ | ✅ | Voll | TCP Socket (IP:Port) |
| `filter_chains` | ✅ | ✅ | Voll | Filter Chain |
| `listener_filters` | ❌ | ❌ | Nicht | TLS Inspector, HTTP Inspector |
| `per_connection_buffer_limit_bytes` | ❌ | ❌ | Nicht | Buffer Limits |
| `socket_options` | ❌ | ❌ | Nicht | TCP Socket Options |
| `transport_socket` (TLS) | ❌ | ❌ | Nicht | TLS Termination |

### Access Logging

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| `file` (stdout/stderr) | ✅ | ✅ | Voll | File Access Logs |
| `json_format` | ✅ | ✅ | Voll | JSON Structured Logs |
| `text_format` | ⚠️ | ⚠️ | Teilweise | Text Logs (CEL Format) |
| `grpc` | ❌ | ❌ | Nicht | gRPC Access Log Service |
| `http` | ❌ | ❌ | Nicht | HTTP Access Log Service |

### Metrics & Observability

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| Admin Interface (`/stats`) | N/A | ✅ | Export | Prometheus Metrics |
| Admin Interface (`/clusters`) | N/A | ✅ | Export | Cluster Health Status |
| Admin Interface (`/config_dump`) | N/A | ✅ | Export | Config Dump |
| Tracing (Zipkin) | ❌ | ❌ | Nicht | Distributed Tracing |
| Tracing (Jaeger) | ❌ | ❌ | Nicht | Distributed Tracing |
| Tracing (OpenTelemetry) | ❌ | ❌ | Nicht | Distributed Tracing |
| StatsD | ❌ | ❌ | Nicht | Metrics Export |
| DogStatsD | ❌ | ❌ | Nicht | Datadog Metrics |

### Advanced Features

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| xDS API (Dynamic Config) | ❌ | ❌ | Nicht | LDS, RDS, CDS, EDS, SDS |
| Hot Restart | N/A | N/A | N/A | Envoy-native Feature |
| Runtime Configuration | ❌ | ❌ | Nicht | Feature Flags |
| Overload Manager | ❌ | ❌ | Nicht | Resource Limits |
| Wasm Filters | ❌ | ❌ | Nicht | WebAssembly Extensions |

### Coverage Score nach Kategorie

| Kategorie | Features Total | Unterstützt | Coverage |
|-----------|----------------|-------------|----------|
| HTTP Filters | 14 | 3 voll, 3 teilweise | ~40% |
| Network Filters | 5 | 1 voll | 20% |
| Cluster Features | 14 | 7 voll, 3 teilweise | ~65% |
| Route Configuration | 18 | 11 voll, 2 teilweise | ~70% |
| Listener Features | 6 | 2 voll | 33% |
| Access Logging | 5 | 2 voll, 1 teilweise | ~50% |
| Metrics & Observability | 8 | 3 export | 37% |
| Advanced Features | 5 | 0 | 0% |

**Gesamt (API Gateway relevante Features):** ~52% Coverage

**Import Coverage:** ~55% (Import bestehender Envoy Configs → GAL)
**Export Coverage:** ~75% (GAL → Envoy Config Generation)

### Bidirektionale Feature-Unterstützung

**Vollständig bidirektional (Import ↔ Export):**
1. ✅ HTTP Routing (Prefix, Exact)
2. ✅ Cluster Configuration (Endpoints, LB Policy)
3. ✅ Health Checks (Active + Passive)
4. ✅ Load Balancing (Round Robin, Least Request, Ring Hash)
5. ✅ CORS Policy
6. ✅ JWT Authentication
7. ✅ Timeout & Retry
8. ✅ Request/Response Headers
9. ✅ WebSocket Support
10. ✅ Access Logs (JSON)

**Nur Export (GAL → Envoy):**
11. ⚠️ Lua Filters (Body Transformation, Basic Auth)
12. ⚠️ Local Rate Limiting
13. ⚠️ External Authorization (ext_authz)

**Features mit Einschränkungen:**
- **Rate Limiting**: Benötigt externen lyft/ratelimit Service (nicht in GAL Scope)
- **TLS**: Keine TLS Termination/Upstream TLS (muss manuell konfiguriert werden)
- **Advanced Routing**: Keine Regex/Header/Query Matching
- **Tracing**: Keine Distributed Tracing Integration (Zipkin/Jaeger/OTel)

### Import-Beispiel (Envoy → GAL)

**Input (envoy.yaml):**
```yaml
static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 10000
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
                  prefix: /api
                route:
                  cluster: api_cluster
                  timeout: 30s
  clusters:
  - name: api_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: api_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: backend.svc
                port_value: 8080
```

**Output (gal-config.yaml):**
```yaml
version: "1.0"
provider: envoy
global:
  host: 0.0.0.0
  port: 10000
services:
  - name: backend
    type: rest
    protocol: http
    upstream:
      host: backend.svc
      port: 8080
      load_balancer:
        algorithm: round_robin
    routes:
      - path_prefix: /api
        timeout:
          read: "30s"
          connect: "5s"
```

### Empfehlungen für zukünftige Erweiterungen

**Priorität 1 (High Impact):**
1. **TLS Termination** - Listener TLS Support (`transport_socket`)
2. **Upstream TLS** - Backend TLS Connections
3. **Regex Routing** - `match.safe_regex` für Advanced Routing
4. **Header-based Routing** - `match.headers` für A/B Testing
5. **Traffic Splitting** - `weighted_clusters` für Canary Deployments

**Priorität 2 (Medium Impact):**
6. **Tracing Integration** - Zipkin/Jaeger/OpenTelemetry
7. **gRPC Health Checks** - `health_checks` mit gRPC
8. **Fault Injection** - `envoy.filters.http.fault` für Chaos Testing
9. **Buffer Limits** - `per_connection_buffer_limit_bytes`
10. **Circuit Breaker Limits** - Vollständige `circuit_breakers` Config

**Priorität 3 (Nice to Have):**
11. **Wasm Filters** - WebAssembly Extensions
12. **xDS API** - Dynamic Configuration Support
13. **gRPC-JSON Transcoder** - gRPC → JSON Transformation
14. **Compression** - `gzip` Filter
15. **Adaptive Concurrency** - `adaptive_concurrency` Filter

### Test Coverage (Import)

**Envoy Import Tests:** 15 Tests (test_import_envoy.py)

| Test Kategorie | Tests | Status |
|----------------|-------|--------|
| Basic Import | 3 | ✅ Passing |
| Clusters & Load Balancing | 3 | ✅ Passing |
| Health Checks | 2 | ✅ Passing |
| Routes & Timeouts | 2 | ✅ Passing |
| Headers | 1 | ✅ Passing |
| CORS | 1 | ✅ Passing |
| WebSocket | 1 | ✅ Passing |
| Errors & Warnings | 2 | ✅ Passing |

**Coverage Verbesserung durch Import:** 8% → 45% (+37%)

### Roundtrip-Kompatibilität

| Szenario | Roundtrip | Bemerkung |
|----------|-----------|-----------|
| Basic Routing + LB | ✅ 100% | Perfekt |
| Health Checks (Active) | ✅ 100% | Perfekt |
| CORS + Headers | ✅ 100% | Perfekt |
| JWT Authentication | ✅ 100% | Perfekt |
| Timeout & Retry | ✅ 95% | Retry-Details verloren |
| WebSocket | ✅ 100% | Perfekt |
| Rate Limiting | ⚠️ 60% | Externe Service-Config verloren |
| Body Transformation (Lua) | ❌ 20% | Lua-Code nicht parsebar |

**Durchschnittliche Roundtrip-Kompatibilität:** ~85%

### Fazit

**Envoy Import Coverage:**
- ✅ **Core Features:** 85% Coverage (Routing, LB, Health Checks, CORS, JWT)
- ⚠️ **Advanced Features:** 25% Coverage (Tracing, TLS, Wasm, xDS)
- ❌ **Nicht unterstützt:** Lua Parsing, xDS Dynamic Config, Advanced Filters

**Envoy Export Coverage:**
- ✅ **Core Features:** 95% Coverage (alle GAL Features → Envoy)
- ✅ **Best Practices:** Eingebaut (Timeouts, Retries, Health Checks)
- ⚠️ **Einschränkungen:** Rate Limiting benötigt externen Service, kein TLS Auto-Config

**Empfehlung:**
- 🚀 Für Standard API Gateway Workloads: **Vollständig ausreichend**
- ⚠️ Für komplexe Envoy Setups (Lua, xDS, Tracing): **Manuelle Nachbearbeitung nötig**
- 📚 Für Envoy → GAL Migration: **85% automatisiert, 15% Review**

**Referenzen:**
- 📚 [Envoy Filter Reference](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/http_filters)
- 📚 [Envoy Cluster Configuration](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/cluster/v3/cluster.proto)
- 📚 [Envoy Route Configuration](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/route/v3/route.proto)
- 📚 [Envoy Network Filters](https://www.envoyproxy.io/docs/envoy/latest/configuration/listeners/network_filters/network_filters)

---

## Envoy-spezifische Details

### Configuration Structure

Envoy verwendet eine **hierarchische YAML-Struktur**:

```
envoy.yaml
├── admin (Admin Interface)
├── static_resources
│   ├── listeners (Ingress)
│   │   ├── filter_chains
│   │   │   ├── filters (HTTP Connection Manager)
│   │   │   │   ├── http_filters (JWT, Rate Limit, etc.)
│   │   │   │   └── route_config (Routing Rules)
│   │   │   │       └── virtual_hosts
│   │   │   │           └── routes (Path Matching)
│   │   │   │               └── route (Cluster Mapping)
│   ├── clusters (Upstreams)
│   │   ├── load_assignment (Endpoints)
│   │   ├── health_checks (Active HC)
│   │   └── outlier_detection (Passive HC)
```

### Filters Architecture

Envoy's Macht liegt in seiner **Filter-Chain**:

1. **Network Filters** (L3/L4):
   - `envoy.filters.network.http_connection_manager`
   - `envoy.filters.network.tcp_proxy`

2. **HTTP Filters** (L7):
   - `envoy.filters.http.router` (Routing)
   - `envoy.filters.http.jwt_authn` (JWT)
   - `envoy.filters.http.ratelimit` (Rate Limiting)
   - `envoy.filters.http.cors` (CORS)
   - `envoy.filters.http.lua` (Custom Logic)
   - `envoy.filters.http.ext_authz` (External Auth)

### Admin Interface

```bash
# Config Dump (aktuelle Config)
curl http://localhost:9901/config_dump

# Stats (Prometheus Format)
curl http://localhost:9901/stats/prometheus

# Clusters (Health Status)
curl http://localhost:9901/clusters

# Logging Level ändern (Runtime)
curl -X POST http://localhost:9901/logging?level=debug
```

### Hot Reload

Envoy unterstützt **Hot Reload** ohne Downtime:

```bash
# Config validieren
envoy --mode validate -c new-envoy.yaml

# Hot Restart (zero-downtime)
envoy --restart-epoch 1 -c new-envoy.yaml
```

---

## Advanced Features

### 1. xDS API (Dynamic Configuration)

Envoy unterstützt **Dynamic Configuration** via xDS (x Discovery Service):

- **LDS** (Listener Discovery Service)
- **RDS** (Route Discovery Service)
- **CDS** (Cluster Discovery Service)
- **EDS** (Endpoint Discovery Service)
- **SDS** (Secret Discovery Service)

GAL generiert **Static Config**, aber Envoy kann mit **Control Planes** wie Istio, Envoy Gateway, oder Gloo arbeiten.

### 2. Lua Scripting

Envoy unterstützt **Lua Filters** für Custom Logic:

```yaml
http_filters:
- name: envoy.filters.http.lua
  typed_config:
    inline_code: |
      function envoy_on_request(request_handle)
        request_handle:headers():add("x-custom", "value")
      end
```

GAL nutzt Lua für:
- Basic Authentication
- Body Transformation
- Custom Request/Response Manipulation

### 3. External Authorization

```yaml
http_filters:
- name: envoy.filters.http.ext_authz
  typed_config:
    grpc_service:
      envoy_grpc:
        cluster_name: ext_authz_cluster
    with_request_body:
      max_request_bytes: 8192
```

Externe Auth-Services (z.B. OPA, custom auth services) können Authorization Decisions treffen.

### 4. Metrics & Tracing

**Prometheus Metrics**:
```yaml
admin:
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 9901
```

```bash
curl http://localhost:9901/stats/prometheus
```

**Distributed Tracing**:
```yaml
tracing:
  http:
    name: envoy.tracers.zipkin
    typed_config:
      "@type": type.googleapis.com/envoy.config.trace.v3.ZipkinConfig
      collector_cluster: zipkin
      collector_endpoint: "/api/v2/spans"
```

---

## Request Mirroring/Shadowing

**Status:** ✅ Native Support (`request_mirror_policies`)

Request Mirroring (Shadow Traffic) ermöglicht es, Requests an Shadow-Backends zu duplizieren, ohne die primäre Response zu beeinflussen. Ideal für Production Testing ohne User Impact.

### Übersicht

Envoy unterstützt Request Mirroring nativ mit `request_mirror_policies`. GAL generiert automatisch die Mirror-Konfiguration mit Sample Percentage Support.

**Features:**
- ✅ Native `request_mirror_policies` support
- ✅ Sample percentage via `runtime_fraction`
- ✅ Multiple mirror targets
- ✅ Fire-and-forget (keine Response-Wartezeit)
- ⚠️ Custom headers via zusätzliche Filter Chains

### GAL-Konfiguration

```yaml
version: "1.0"
provider: envoy

services:
  - name: api_service
    protocol: http
    upstream:
      host: api-v1
      port: 8080
    routes:
      - path_prefix: /api/users
        methods: [GET, POST]

        # Request Mirroring Configuration
        mirroring:
          enabled: true
          mirror_request_body: true
          mirror_headers: true
          targets:
            - name: shadow-v2
              upstream:
                host: shadow-api-v2
                port: 8080
              sample_percentage: 50.0  # 50% of traffic
              timeout: "5s"
              headers:
                X-Mirror: "true"
                X-Shadow-Version: "v2"
```

### Generierte Envoy-Konfiguration

```yaml
# Envoy Config (generiert von GAL)
static_resources:
  clusters:
    - name: primary_cluster
      connect_timeout: 5s
      type: STRICT_DNS
      load_assignment:
        cluster_name: primary_cluster
        endpoints:
          - lb_endpoints:
            - endpoint:
                address:
                  socket_address:
                    address: api-v1
                    port_value: 8080

    - name: shadow_cluster
      connect_timeout: 5s
      type: STRICT_DNS
      load_assignment:
        cluster_name: shadow_cluster
        endpoints:
          - lb_endpoints:
            - endpoint:
                address:
                  socket_address:
                    address: shadow-api-v2
                    port_value: 8080

  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8080
      filter_chains:
        - filters:
          - name: envoy.filters.network.http_connection_manager
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
              stat_prefix: ingress_http
              route_config:
                name: local_route
                virtual_hosts:
                  - name: api_service
                    domains: ["*"]
                    routes:
                      - match:
                          prefix: "/api/users"
                        route:
                          cluster: primary_cluster
                          timeout: 30s
                          # Request Mirroring
                          request_mirror_policies:
                            - cluster: shadow_cluster
                              runtime_fraction:
                                default_value:
                                  numerator: 50    # 50% sampling
                                  denominator: HUNDRED
```

### Use Cases

**1. Canary Deployment Testing (10% Shadow Traffic)**
```yaml
mirroring:
  enabled: true
  targets:
    - name: canary-v2
      upstream:
        host: api-v2-canary
        port: 8080
      sample_percentage: 10.0  # Only 10% to detect issues
```

**2. Performance Testing (100% Shadow Traffic)**
```yaml
mirroring:
  enabled: true
  targets:
    - name: load-test
      upstream:
        host: api-loadtest
        port: 8080
      sample_percentage: 100.0  # All traffic for performance testing
      timeout: "3s"
```

**3. Multiple Shadow Targets (A/B/C Testing)**
```yaml
mirroring:
  enabled: true
  targets:
    - name: shadow-v2
      upstream:
        host: api-v2
        port: 8080
      sample_percentage: 50.0
    - name: shadow-v3
      upstream:
        host: api-v3
        port: 8080
      sample_percentage: 10.0
```

### Deployment

```bash
# 1. GAL → Envoy Config generieren
gal generate --config config.yaml --provider envoy --output envoy.yaml

# 2. Envoy deployen (Docker)
docker run --rm -v $(pwd)/envoy.yaml:/etc/envoy/envoy.yaml \
  -p 8080:8080 -p 9901:9901 \
  envoyproxy/envoy:v1.31-latest

# 3. Mirroring testen
for i in {1..100}; do
  curl -s http://localhost:8080/api/users
done

# 4. Shadow Backend Metrics prüfen
curl http://shadow-api-v2:8080/metrics | grep request_count
```

### Monitoring

**Admin API Stats:**
```bash
# Mirror Cluster Stats
curl http://localhost:9901/stats | grep shadow_cluster

# Expected Output:
# cluster.shadow_cluster.upstream_rq_total: 50  # ~50 requests (50%)
# cluster.shadow_cluster.upstream_rq_time: 15ms
# cluster.shadow_cluster.upstream_rq_success: 48
# cluster.shadow_cluster.upstream_rq_error: 2
```

**Envoy Logs:**
```bash
# Mirror requests in logs
docker logs envoy-container 2>&1 | grep shadow_cluster

# Example:
# [info] upstream_rq_total: cluster.shadow_cluster: 1
# [info] response_code: 200, cluster: shadow_cluster
```

### Limitierungen

- ⚠️ **Custom Headers:** Keine direkte Header-Injection für Mirror-Requests (nutze Lua Filter als Workaround)
- ⚠️ **Sample Percentage:** Runtime-basiert (nicht exakt, nutzt `runtime_fraction`)
- ⚠️ **Response Ignored:** Shadow-Backend-Response wird komplett ignoriert (fire-and-forget)
- ⚠️ **Timeouts:** Mirror-Request-Timeout unabhängig vom Primary Request

### Best Practices

1. **Start with Low Sample Percentage (5-10%)**
   - Verhindert Shadow-Backend-Überlastung
   - Findet Bugs mit minimalem Traffic

2. **Monitor Shadow Backend Metrics**
   - Separate Metrics-Erfassung für Shadow Traffic
   - Alert bei hoher Error-Rate im Shadow

3. **Set Appropriate Timeouts**
   - Shadow-Timeouts sollten kürzer sein als Primary (z.B. 3s vs 30s)
   - Verhindert lange Mirror-Request-Blockierung

4. **Use Headers to Identify Mirror Traffic**
   - `X-Mirror: true` Header für Shadow-Backend-Identifikation
   - Ermöglicht separate Log-Filtering

### Troubleshooting

**Problem:** Mirror Requests erreichen Shadow Backend nicht

**Diagnose:**
```bash
# Cluster Status prüfen
curl http://localhost:9901/clusters | grep shadow_cluster

# Expected:
# cluster.shadow_cluster.membership_healthy: 1
# cluster.shadow_cluster.membership_total: 1
```

**Lösung:**
- DNS-Auflösung prüfen: `nslookup shadow-api-v2`
- Shadow Backend Health: `curl http://shadow-api-v2:8080/health`
- Envoy Logs prüfen: `docker logs envoy-container`

**Problem:** Zu viele/zu wenige Mirror Requests

**Diagnose:**
```bash
# Ratio berechnen
PRIMARY=$(curl -s http://localhost:9901/stats | grep primary_cluster.upstream_rq_total | awk '{print $2}')
SHADOW=$(curl -s http://localhost:9901/stats | grep shadow_cluster.upstream_rq_total | awk '{print $2}')
echo "Mirror Ratio: $(echo "scale=2; $SHADOW / $PRIMARY * 100" | bc)%"
```

**Lösung:**
- `runtime_fraction.default_value.numerator` anpassen (50 = 50%)
- Bei 1000+ Requests: ±5% Toleranz ist normal

> **Vollständige Dokumentation:** Siehe [Request Mirroring Guide](REQUEST_MIRRORING.md#1-envoy-native)

---

