# Envoy Provider Anleitung

**Umfassende Anleitung für den Envoy Proxy Provider in GAL (Gateway Abstraction Layer)**

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Schnellstart](#schnellstart)
3. [Installation und Setup](#installation-und-setup)
4. [Konfigurationsoptionen](#konfigurationsoptionen)
5. [Feature-Implementierungen](#feature-implementierungen)
6. [Provider-Vergleich](#provider-vergleich)
7. [Envoy-spezifische Details](#envoy-spezifische-details)
8. [Advanced Features](#advanced-features)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Übersicht

**Envoy Proxy** ist ein moderner, hochperformanter **Cloud-Native Proxy** und **Service Mesh Sidecar**, entwickelt von Lyft und jetzt Teil der **Cloud Native Computing Foundation (CNCF)**. Envoy ist die Grundlage für viele Service Mesh Lösungen wie **Istio**, **Consul Connect** und **AWS App Mesh**.

### Warum Envoy?

- ✅ **Modern & Cloud-Native** - Gebaut für Kubernetes und Microservices
- ✅ **Feature-reich** - Umfassendste Feature-Set aller Provider
- ✅ **Observability** - Eingebaute Metrics, Tracing, Logging
- ✅ **Performance** - C++ implementiert, extrem schnell
- ✅ **Extensibility** - Filter-basierte Architektur, Lua Support
- ✅ **Service Mesh Ready** - Perfekt für Istio, Envoy Gateway
- ✅ **Hot Reload** - Configuration Changes ohne Downtime

### GAL + Envoy = Perfekte Kombination

GAL vereinfacht Envoy's komplexe YAML-Konfiguration drastisch:

| Feature | Envoy (nativ) | GAL für Envoy |
|---------|---------------|---------------|
| Konfigurationsgröße | 200+ Zeilen | 30 Zeilen |
| Lernkurve | Steil (Wochen) | Flach (Stunden) |
| Fehleranfälligkeit | Hoch | Niedrig |
| Wartbarkeit | Schwierig | Einfach |
| Provider-Wechsel | Unmöglich | 1 Command |

### Envoy Feature-Matrix

| Feature | Envoy Support | GAL Implementation |
|---------|---------------|-------------------|
| **Traffic Management** | | |
| Rate Limiting | ✅ Native (envoy.filters.http.ratelimit) | ✅ Vollständig |
| Circuit Breaker | ✅ Native (outlier_detection) | ✅ Vollständig |
| Health Checks | ✅ Active + Passive | ✅ Vollständig |
| Load Balancing | ✅ Round Robin, Least Request, Ring Hash, etc. | ✅ Vollständig |
| Timeout & Retry | ✅ Umfassend (per-try timeout, retry policy) | ✅ Vollständig |
| **Security** | | |
| Basic Auth | ⚠️ Via Lua/External | ⚠️ Lua Filter |
| JWT Validation | ✅ Native (envoy.filters.http.jwt_authn) | ✅ Vollständig |
| API Key Auth | ⚠️ Via External Auth | ⚠️ External Service |
| CORS | ✅ Native (cors policy) | ✅ Vollständig |
| **Advanced** | | |
| WebSocket | ✅ Native (HTTP/1.1 Upgrade) | ✅ Vollständig |
| gRPC | ✅ Native (HTTP/2) | ✅ Vollständig |
| Body Transformation | ✅ Via Lua Filter | ✅ Lua Implementation |
| Request/Response Headers | ✅ Native | ✅ Vollständig |
| **Observability** | | |
| Access Logs | ✅ Structured (JSON, text) | ✅ Vollständig |
| Metrics (Prometheus) | ✅ Native | ✅ Vollständig |
| Distributed Tracing | ✅ Zipkin, Jaeger, OpenTelemetry | ✅ Vollständig |

---

## Schnellstart

### Beispiel 1: Einfacher Reverse Proxy

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend.default.svc.cluster.local
      port: 8080
    routes:
      - path_prefix: /api
```

**Generierte Envoy-Konfiguration** (~150 Zeilen):
```bash
gal generate --config config.yaml --provider envoy > envoy.yaml
```

Enthält:
- Static Resources (clusters, listeners)
- HTTP Connection Manager
- Route Configuration
- Cluster mit Health Checks

### Beispiel 2: Load Balancing mit Health Checks

```yaml
services:
  - name: api_service
    upstream:
      targets:
        - host: api-1.default.svc.cluster.local
          port: 8080
        - host: api-2.default.svc.cluster.local
          port: 8080
        - host: api-3.default.svc.cluster.local
          port: 8080
      health_check:
        active:
          enabled: true
          interval: "10s"
          timeout: "5s"
          http_path: "/health"
          healthy_threshold: 2
          unhealthy_threshold: 3
      load_balancer:
        algorithm: round_robin
    routes:
      - path_prefix: /api
```

**Generiert**:
- Cluster mit 3 Endpoints
- Active Health Checks (HTTP GET /health)
- Round Robin Load Balancing

### Beispiel 3: Complete Production Setup

```yaml
services:
  - name: api_service
    upstream:
      targets:
        - host: api-1.svc
          port: 8080
      health_check:
        active:
          enabled: true
          interval: "10s"
          http_path: "/health"
      load_balancer:
        algorithm: least_request
    routes:
      - path_prefix: /api
        rate_limit:
          enabled: true
          requests_per_second: 100
          burst: 200
        authentication:
          enabled: true
          type: jwt
          jwt:
            issuer: "https://auth.example.com"
            audiences: ["api"]
        cors:
          enabled: true
          allowed_origins: ["https://app.example.com"]
          allowed_methods: ["GET", "POST", "PUT", "DELETE"]
        timeout:
          connect: "5s"
          read: "60s"
        retry:
          enabled: true
          attempts: 3
          retry_on:
            - connect_timeout
            - http_5xx
```

---

## Installation und Setup

### 1. Envoy Binary Installation

#### Option A: Docker (Empfohlen)

```bash
# Official Envoy Image
docker pull envoyproxy/envoy:v1.28-latest

# Envoy starten mit GAL-generierter Config
docker run -d \
  --name envoy \
  -p 10000:10000 \
  -p 9901:9901 \
  -v $(pwd)/envoy.yaml:/etc/envoy/envoy.yaml \
  envoyproxy/envoy:v1.28-latest
```

#### Option B: Binary Download

```bash
# Linux (Ubuntu/Debian)
curl -L https://github.com/envoyproxy/envoy/releases/download/v1.28.0/envoy-1.28.0-linux-x86_64 \
  -o /usr/local/bin/envoy
chmod +x /usr/local/bin/envoy

# macOS (via Homebrew)
brew install envoy
```

#### Option C: Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: envoy-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: envoy
  template:
    metadata:
      labels:
        app: envoy
    spec:
      containers:
      - name: envoy
        image: envoyproxy/envoy:v1.28-latest
        ports:
        - containerPort: 10000
          name: http
        - containerPort: 9901
          name: admin
        volumeMounts:
        - name: config
          mountPath: /etc/envoy
      volumes:
      - name: config
        configMap:
          name: envoy-config
---
apiVersion: v1
kind: Service
metadata:
  name: envoy-gateway
spec:
  type: LoadBalancer
  selector:
    app: envoy
  ports:
  - port: 80
    targetPort: 10000
    name: http
  - port: 9901
    targetPort: 9901
    name: admin
```

### 2. GAL Config generieren

```bash
# GAL installieren
pip install gal-gateway

# Config generieren
gal generate --config gateway.yaml --provider envoy > envoy.yaml

# Validieren
envoy --mode validate -c envoy.yaml

# Starten
envoy -c envoy.yaml
```

### 3. Admin Interface prüfen

```bash
# Stats
curl http://localhost:9901/stats

# Config Dump
curl http://localhost:9901/config_dump

# Clusters Status
curl http://localhost:9901/clusters
```

---

## Konfigurationsoptionen

### Global Configuration

```yaml
global:
  host: 0.0.0.0           # Listener Address
  port: 10000             # HTTP Port
  admin_port: 9901        # Admin Interface Port
```

**Generiert**:
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
        port_value: 10000
```

### Upstream Configuration

```yaml
upstream:
  host: backend.svc        # Single host
  port: 8080
  # ODER
  targets:                 # Multiple targets
    - host: backend-1.svc
      port: 8080
      weight: 1
    - host: backend-2.svc
      port: 8080
      weight: 2
```

**Generiert Cluster**:
```yaml
clusters:
- name: api_service_cluster
  connect_timeout: 5s
  type: STRICT_DNS
  lb_policy: ROUND_ROBIN
  load_assignment:
    cluster_name: api_service_cluster
    endpoints:
    - lb_endpoints:
      - endpoint:
          address:
            socket_address:
              address: backend-1.svc
              port_value: 8080
        load_balancing_weight: 1
      - endpoint:
          address:
            socket_address:
              address: backend-2.svc
              port_value: 8080
        load_balancing_weight: 2
```

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

## Best Practices

### 1. Verwende Admin Interface für Debugging

```bash
# Live Config anzeigen
curl -s http://localhost:9901/config_dump | jq .

# Cluster Health prüfen
curl -s http://localhost:9901/clusters | grep health_flags
```

### 2. Enable Access Logs

```yaml
access_log:
- name: envoy.access_loggers.file
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.access_loggers.file.v3.FileAccessLog
    path: /dev/stdout
    log_format:
      json_format:
        start_time: "%START_TIME%"
        method: "%REQ(:METHOD)%"
        path: "%REQ(X-ENVOY-ORIGINAL-PATH?:PATH)%"
        response_code: "%RESPONSE_CODE%"
        duration: "%DURATION%"
```

### 3. Configure Resource Limits

```yaml
circuit_breakers:
  thresholds:
  - priority: DEFAULT
    max_connections: 1024
    max_pending_requests: 1024
    max_requests: 1024
    max_retries: 3
```

### 4. Use Health Checks

Immer Active + Passive Health Checks kombinieren:
```yaml
health_check:
  active:
    enabled: true
    interval: "10s"
  passive:
    enabled: true
    max_failures: 5
```

### 5. Tune Timeouts

```yaml
timeout:
  connect: "5s"       # Kurz für schnelles Failover
  read: "60s"         # Lang genug für normale Requests
  idle: "300s"        # 5 Minuten Keep-Alive
```

### 6. Enable Retry mit Exponential Backoff

```yaml
retry:
  enabled: true
  attempts: 3
  backoff: exponential
  base_interval: "25ms"
  max_interval: "250ms"
```

### 7. Monitoring & Alerting

- ✅ **Prometheus Metrics** scrapen
- ✅ **Grafana Dashboards** für Envoy
- ✅ **Alerting** auf 5xx Errors, Timeout Rates
- ✅ **Distributed Tracing** (Jaeger/Zipkin)

---

## Troubleshooting

### Problem 1: Config Validation Errors

**Symptom**: `envoy --mode validate` schlägt fehl

**Lösung**:
```bash
# Detaillierte Fehlermeldung
envoy --mode validate -c envoy.yaml --log-level debug

# GAL Config erneut generieren
gal generate --config gateway.yaml --provider envoy > envoy.yaml
```

### Problem 2: Upstream Connection Failed

**Symptom**: `503 Service Unavailable`, Logs zeigen "upstream connect error"

**Diagnose**:
```bash
# Cluster Status prüfen
curl http://localhost:9901/clusters | grep api_service

# Health Check Status
curl http://localhost:9901/clusters | grep health_flags
```

**Lösung**:
- Prüfe DNS-Auflösung: `nslookup backend.svc`
- Prüfe Backend-Health: `curl http://backend.svc:8080/health`
- Erhöhe Connection Timeout: `timeout.connect: "10s"`

### Problem 3: Rate Limiting funktioniert nicht

**Symptom**: Requests werden nicht gedrosselt

**Lösung**:
Envoy benötigt einen **External Rate Limit Service**:

```bash
# lyft/ratelimit deployen
kubectl apply -f https://github.com/envoyproxy/ratelimit/releases/latest/download/ratelimit.yaml
```

Oder verwende **Local Rate Limiting**:
```yaml
http_filters:
- name: envoy.filters.http.local_ratelimit
  typed_config:
    stat_prefix: http_local_rate_limiter
    token_bucket:
      max_tokens: 200
      tokens_per_fill: 100
      fill_interval: 1s
```

### Problem 4: JWT Validation schlägt fehl

**Symptom**: `401 Unauthorized`, JWT ist gültig

**Diagnose**:
```bash
# JWT Token dekodieren
echo "eyJhbGc..." | base64 -d | jq .

# JWKS URI prüfen
curl https://auth.example.com/.well-known/jwks.json
```

**Lösung**:
- Prüfe `issuer` stimmt überein
- Prüfe `audiences` ist korrekt
- Prüfe JWKS URI ist erreichbar

### Problem 5: High Latency

**Symptom**: Langsame Response Times

**Diagnose**:
```bash
# Stats prüfen
curl http://localhost:9901/stats | grep duration

# Tracing aktivieren (Jaeger)
curl http://localhost:9901/stats | grep tracing
```

**Lösung**:
- Reduziere Retry-Versuche
- Erhöhe Connection Pool Size
- Enable HTTP/2 für Backend
- Tune Timeout-Werte

### Problem 6: Memory/CPU Usage hoch

**Symptom**: Hoher Resource-Verbrauch

**Lösung**:
```yaml
# Resource Limits setzen
circuit_breakers:
  thresholds:
  - max_connections: 512
    max_requests: 512

# Buffer Limits
per_connection_buffer_limit_bytes: 32768
```

---

## Zusammenfassung

**Envoy Proxy** ist der **feature-reichste und modernste** API Gateway Provider in GAL:

✅ **Stärken**:
- Umfassendstes Feature-Set
- Native Observability
- Service Mesh Ready
- Hot Reload
- gRPC Native

⚠️ **Herausforderungen**:
- Steile Lernkurve (GAL löst dies!)
- Verbose Configuration (GAL vereinfacht)
- Rate Limiting benötigt External Service
- Basic Auth nicht nativ

**GAL macht Envoy zugänglich** - von 200+ Zeilen Envoy-YAML zu 30 Zeilen GAL-YAML!

**Nächste Schritte**:
- Vergleiche [Kong](KONG.md), [APISIX](APISIX.md), [Traefik](TRAEFIK.md)
- Probiere [WebSocket Support](WEBSOCKET.md) aus
- Implementiere [Circuit Breaker](CIRCUIT_BREAKER.md)

**Siehe auch**:
- [Official Envoy Docs](https://www.envoyproxy.io/docs)
- [Envoy GitHub](https://github.com/envoyproxy/envoy)
- [Envoy Slack](https://envoyproxy.slack.com)
