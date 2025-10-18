# Kong Gateway Provider Anleitung

**Umfassende Anleitung für den Kong Gateway Provider in GAL (Gateway Abstraction Layer)**

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Schnellstart](#schnellstart)
3. [Installation und Setup](#installation-und-setup)
4. [Konfigurationsoptionen](#konfigurationsoptionen)
5. [Feature-Implementierungen](#feature-implementierungen)
6. [Provider-Vergleich](#provider-vergleich)
7. [Kong-spezifische Details](#kong-spezifische-details)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Übersicht

**Kong Gateway** ist ein **Open-Source API Gateway** und **Service Mesh**, gebaut auf **Nginx** und **OpenResty (Lua)**. Kong ist bekannt für seine **Plugin-Architektur** und **einfache Verwaltung**.

### Warum Kong?

- ✅ **Plugin-Ökosystem** - 300+ Plugins (Community + Enterprise)
- ✅ **DB-less Mode** - Deklarative Konfiguration (YAML)
- ✅ **Developer-Friendly** - Einfache Admin API
- ✅ **Performance** - Basiert auf Nginx + OpenResty
- ✅ **Kong Manager** - Web UI für Verwaltung (Enterprise)
- ✅ **Cloud-Native** - Kubernetes-ready, Helm Charts
- ✅ **Service Mesh** - Kong Mesh (Kuma-basiert)

### Kong Feature-Matrix

| Feature | Kong Support | GAL Implementation |
|---------|--------------|-------------------|
| **Traffic Management** | | |
| Rate Limiting | ✅ Native Plugin | ✅ Vollständig |
| Circuit Breaker | ⚠️ Via Plugin | ⚠️ Plugin Config |
| Health Checks | ✅ Passive + Active | ✅ Vollständig |
| Load Balancing | ✅ Native | ✅ Vollständig |
| Timeout & Retry | ✅ Native | ✅ Vollständig |
| **Security** | | |
| Basic Auth | ✅ Native Plugin | ✅ Vollständig |
| JWT Validation | ✅ Native Plugin | ✅ Vollständig |
| API Key Auth | ✅ Native Plugin | ✅ Vollständig |
| CORS | ✅ Native Plugin | ✅ Vollständig |
| **Advanced** | | |
| WebSocket | ✅ Native | ✅ Vollständig |
| gRPC | ✅ Native | ✅ Vollständig |
| Body Transformation | ✅ Plugins | ✅ Vollständig |
| Request/Response Headers | ✅ Plugins | ✅ Vollständig |

---

## Schnellstart

### Beispiel 1: Einfacher API Gateway

```yaml
version: "1.0"
provider: kong

global:
  host: 0.0.0.0
  port: 8000
  admin_port: 8001

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
```

**Generiert** (Kong Declarative Config):
```yaml
_format_version: '3.0'
services:
- name: api_service
  protocol: http
  host: api-backend
  port: 8080
  routes:
  - name: api_service_route
    paths:
    - /api
```

### Beispiel 2: Mit Authentication + Rate Limiting

```yaml
services:
  - name: api_service
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        authentication:
          enabled: true
          type: jwt
          jwt:
            issuer: "https://auth.example.com"
        rate_limit:
          enabled: true
          requests_per_second: 100
```

**Generiert**:
```yaml
services:
- name: api_service
  plugins:
  - name: jwt
    config:
      claims_to_verify: [iss]
      key_claim_name: iss
      issuer: https://auth.example.com
  - name: rate-limiting
    config:
      second: 100
      policy: local
```

---

## Installation und Setup

### 1. Kong Installation

#### Option A: Docker (Empfohlen)

```bash
# Kong in DB-less Mode (Declarative Config)
docker run -d \
  --name kong \
  -e "KONG_DATABASE=off" \
  -e "KONG_DECLARATIVE_CONFIG=/kong.yaml" \
  -e "KONG_PROXY_ACCESS_LOG=/dev/stdout" \
  -e "KONG_ADMIN_ACCESS_LOG=/dev/stdout" \
  -e "KONG_PROXY_ERROR_LOG=/dev/stderr" \
  -e "KONG_ADMIN_ERROR_LOG=/dev/stderr" \
  -p 8000:8000 \
  -p 8443:8443 \
  -p 8001:8001 \
  -p 8444:8444 \
  -v $(pwd)/kong.yaml:/kong.yaml \
  kong:3.4

# Admin API prüfen
curl http://localhost:8001/
```

#### Option B: Kubernetes (Helm)

```bash
# Kong Helm Repo hinzufügen
helm repo add kong https://charts.konghq.com
helm repo update

# Kong installieren (DB-less)
helm install kong kong/kong \
  --set ingressController.enabled=true \
  --set env.database=off \
  --set env.declarative_config=/kong.yaml
```

### 2. GAL Config generieren

```bash
# Config generieren
gal generate --config gateway.yaml --provider kong > kong.yaml

# Kong mit Config starten
docker run -d --name kong \
  -e "KONG_DATABASE=off" \
  -e "KONG_DECLARATIVE_CONFIG=/kong.yaml" \
  -p 8000:8000 -p 8001:8001 \
  -v $(pwd)/kong.yaml:/kong.yaml \
  kong:3.4
```

### 3. Verify Setup

```bash
# Services prüfen
curl http://localhost:8001/services

# Routes prüfen
curl http://localhost:8001/routes

# Test Request
curl http://localhost:8000/api
```

---

## Konfigurationsoptionen

### Global Configuration

```yaml
global:
  host: 0.0.0.0      # Proxy Listen Address
  port: 8000         # HTTP Port
  admin_port: 8001   # Admin API Port
```

### Service Configuration

```yaml
services:
  - name: api_service
    protocol: http          # http, https, grpc, grpcs
    upstream:
      host: backend.svc
      port: 8080
      # Timeouts (in Milliseconds!)
      connect_timeout: 60000
      read_timeout: 60000
      write_timeout: 60000
```

**Kong Besonderheit**: Timeouts in **Millisekunden** (nicht Sekunden)!

---

## Feature-Implementierungen

### 1. Load Balancing

```yaml
upstream:
  targets:
    - host: backend-1
      port: 8080
      weight: 100
    - host: backend-2
      port: 8080
      weight: 200
  load_balancer:
    algorithm: round_robin  # round_robin, least_conn, ip_hash
```

**Generiert**:
```yaml
upstreams:
- name: api_service_upstream
  algorithm: round-robin
  targets:
  - target: backend-1:8080
    weight: 100
  - target: backend-2:8080
    weight: 200
```

### 2. Health Checks

```yaml
health_check:
  active:
    enabled: true
    interval: "10s"
    timeout: "5s"
    http_path: "/health"
    healthy_threshold: 2
    unhealthy_threshold: 3
```

**Generiert**:
```yaml
upstreams:
- name: api_service_upstream
  healthchecks:
    active:
      type: http
      http_path: /health
      timeout: 5
      interval: 10
      healthy:
        successes: 2
      unhealthy:
        http_failures: 3
```

### 3. Rate Limiting

```yaml
rate_limit:
  enabled: true
  requests_per_second: 100
  burst: 200
```

**Generiert**:
```yaml
plugins:
- name: rate-limiting
  config:
    second: 100
    policy: local
    hide_client_headers: false
```

### 4. Authentication

**JWT**:
```yaml
authentication:
  enabled: true
  type: jwt
  jwt:
    issuer: "https://auth.example.com"
    audiences: ["api"]
```

**Generiert**:
```yaml
plugins:
- name: jwt
  config:
    claims_to_verify: [iss, aud]
    key_claim_name: iss
```

**Basic Auth**:
```yaml
authentication:
  enabled: true
  type: basic
  basic_auth:
    users:
      admin: password123
```

**Generiert**:
```yaml
plugins:
- name: basic-auth
consumers:
- username: admin
  basicauth_credentials:
  - username: admin
    password: password123
```

**API Key**:
```yaml
authentication:
  enabled: true
  type: api_key
  api_key:
    key_name: X-API-Key
    in_location: header
```

**Generiert**:
```yaml
plugins:
- name: key-auth
  config:
    key_names: [X-API-Key]
```

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
plugins:
- name: cors
  config:
    origins: ["https://app.example.com"]
    methods: ["GET", "POST", "PUT", "DELETE"]
    headers: ["Content-Type", "Authorization"]
    credentials: true
    max_age: 86400
```

### 6. Timeout & Retry

```yaml
timeout:
  connect: "10s"
  send: "60s"
  read: "120s"
retry:
  enabled: true
  attempts: 3
```

**Generiert**:
```yaml
services:
- name: api_service
  connect_timeout: 10000    # Milliseconds!
  write_timeout: 60000
  read_timeout: 120000
  retries: 3
```

**Wichtig**: Kong verwendet **Millisekunden** für Timeouts!

### 7. Request/Response Headers

```yaml
headers:
  request_add:
    X-Request-ID: "{{uuid}}"
  request_remove:
    - X-Internal-Secret
  response_add:
    X-Gateway: "Kong"
  response_remove:
    - X-Powered-By
```

**Generiert**:
```yaml
plugins:
- name: request-transformer
  config:
    add:
      headers: ["X-Request-ID:{{uuid}}"]
    remove:
      headers: ["X-Internal-Secret"]
- name: response-transformer
  config:
    add:
      headers: ["X-Gateway:Kong"]
    remove:
      headers: ["X-Powered-By"]
```

### 8. Body Transformation

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

**Generiert**:
```yaml
plugins:
- name: request-transformer
  config:
    add:
      json: ["trace_id:{{uuid}}"]
    remove:
      json: ["secret_key"]
- name: response-transformer
  config:
    remove:
      json: ["password"]
```

---

## Provider-Vergleich

### Kong vs. Andere Provider

| Feature | Kong | Envoy | APISIX | Traefik | Nginx | HAProxy |
|---------|------|-------|--------|---------|-------|---------|
| **Ease of Use** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Plugin Ecosystem** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Admin API** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Documentation** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Enterprise Support** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

**Kong Stärken**:
- ✅ **Einfachste Konfiguration** aller Provider
- ✅ **300+ Plugins** (Community + Enterprise)
- ✅ **Admin API** für dynamische Verwaltung
- ✅ **Kong Manager** (Web UI - Enterprise)
- ✅ **DB-less Mode** (Declarative Config)
- ✅ **Beste Dokumentation**

**Kong Schwächen**:
- ❌ **Enterprise Features** kostenpflichtig
- ⚠️ **Performance** etwas niedriger als Nginx/HAProxy
- ⚠️ **Retry** keine konditionalen Bedingungen

---

## Kong-spezifische Details

### Plugin-Architektur

Kong's Macht liegt in seinen **Plugins**:

**Plugin Execution Order**:
1. **Pre-Function** (Custom Lua before request)
2. **Authentication** (JWT, Basic, API Key, etc.)
3. **Rate Limiting** (Rate limits enforcement)
4. **Request Transformer** (Modify request)
5. **Proxy** (Forward to upstream)
6. **Response Transformer** (Modify response)
7. **Post-Function** (Custom Lua after response)

### Admin API

Kong bietet eine **REST API** für Verwaltung:

```bash
# Services auflisten
curl http://localhost:8001/services

# Service erstellen
curl -X POST http://localhost:8001/services \
  -d "name=my-service" \
  -d "url=http://backend:8080"

# Route hinzufügen
curl -X POST http://localhost:8001/services/my-service/routes \
  -d "paths[]=/api"

# Plugin aktivieren
curl -X POST http://localhost:8001/services/my-service/plugins \
  -d "name=rate-limiting" \
  -d "config.second=100"
```

**Hinweis**: GAL generiert **Declarative Config** (DB-less Mode), nicht Admin API Calls.

### DB-less vs. DB Mode

**DB-less Mode** (Empfohlen für GAL):
- ✅ Keine Datenbank erforderlich
- ✅ Einfaches Deployment
- ✅ Git-freundlich (YAML-Config)
- ❌ Keine dynamischen Änderungen via Admin API

**DB Mode** (PostgreSQL):
- ✅ Dynamische Änderungen via Admin API
- ✅ Kong Manager UI
- ❌ Benötigt Datenbank
- ❌ Komplexeres Setup

### Kong Manager (Enterprise)

Kong Enterprise bietet eine **Web UI**:

```bash
# Kong Manager aktivieren (Enterprise)
docker run -d \
  --name kong-enterprise \
  -e "KONG_ADMIN_GUI_URL=http://localhost:8002" \
  kong/kong-gateway:3.4-enterprise
```

Zugriff: `http://localhost:8002`

---

## Best Practices

### 1. Verwende DB-less Mode für Production

```yaml
# DB-less ist einfacher und stabiler
KONG_DATABASE=off
KONG_DECLARATIVE_CONFIG=/kong.yaml
```

### 2. Enable Access Logs

```yaml
# JSON-Format für strukturierte Logs
KONG_PROXY_ACCESS_LOG=/dev/stdout
KONG_ADMIN_ACCESS_LOG=/dev/stdout
KONG_LOG_LEVEL=info
```

### 3. Configure Resource Limits

```yaml
# Nginx Worker Limits
KONG_NGINX_WORKER_PROCESSES=auto
KONG_NGINX_WORKER_CONNECTIONS=4096
```

### 4. Use Health Checks

Immer Active Health Checks konfigurieren:
```yaml
healthchecks:
  active:
    type: http
    http_path: /health
```

### 5. Tune Timeouts

```yaml
# In Milliseconds!
connect_timeout: 60000    # 60 Sekunden
read_timeout: 60000
write_timeout: 60000
```

### 6. Rate Limiting Strategy

```yaml
# Local Policy (einfach)
rate-limiting:
  policy: local

# Redis Policy (distributed)
rate-limiting:
  policy: redis
  redis_host: redis.svc
```

### 7. Security Headers

```yaml
plugins:
- name: response-transformer
  config:
    add:
      headers:
      - X-Frame-Options:DENY
      - X-Content-Type-Options:nosniff
```

---

## Troubleshooting

### Problem 1: Config Validation Errors

**Symptom**: Kong startet nicht, Config-Fehler

**Lösung**:
```bash
# Validate Config
kong config parse /path/to/kong.yaml

# GAL Config erneut generieren
gal generate --config gateway.yaml --provider kong > kong.yaml
```

### Problem 2: Upstream Connection Failed

**Symptom**: `502 Bad Gateway`

**Diagnose**:
```bash
# Services Status prüfen
curl http://localhost:8001/services/api_service

# Upstream Health prüfen
curl http://localhost:8001/upstreams/api_service_upstream/health
```

### Problem 3: Rate Limiting nicht aktiv

**Symptom**: Requests werden nicht gedrosselt

**Lösung**:
```yaml
# Prüfe Plugin Config
plugins:
- name: rate-limiting
  config:
    second: 100       # Requests pro Sekunde
    policy: local     # Muss gesetzt sein
```

### Problem 4: JWT Validation schlägt fehl

**Symptom**: `401 Unauthorized`

**Diagnose**:
```bash
# Consumer mit JWT Credential erstellen
curl -X POST http://localhost:8001/consumers/test-user
curl -X POST http://localhost:8001/consumers/test-user/jwt \
  -d "key=issuer-key"
```

### Problem 5: Timeout zu kurz

**Symptom**: `504 Gateway Timeout`

**Lösung**:
```yaml
# Timeouts erhöhen (in MS!)
services:
- name: api_service
  connect_timeout: 120000   # 120 Sekunden
  read_timeout: 120000
```

### Problem 6: Memory Usage hoch

**Symptom**: Hoher RAM-Verbrauch

**Lösung**:
```yaml
# Worker Processes reduzieren
KONG_NGINX_WORKER_PROCESSES=2
KONG_MEM_CACHE_SIZE=128m
```

---

## Zusammenfassung

**Kong Gateway** ist der **developer-freundlichste** API Gateway Provider:

✅ **Stärken**:
- Einfachste Konfiguration
- 300+ Plugins
- Beste Admin API
- DB-less Mode
- Beste Dokumentation

⚠️ **Herausforderungen**:
- Enterprise Features kostenpflichtig
- Etwas niedriger Performance als Nginx/HAProxy
- Retry ohne konditionale Bedingungen

**GAL macht Kong noch einfacher** - automatische Plugin-Konfiguration aus GAL-YAML!

**Nächste Schritte**:
- Vergleiche [Envoy](ENVOY.md), [APISIX](APISIX.md), [Traefik](TRAEFIK.md)
- Probiere [Kong Plugins](https://docs.konghq.com/hub/)
- Explore [Kong Enterprise](https://konghq.com/products/kong-enterprise)

**Siehe auch**:
- [Kong Docs](https://docs.konghq.com/)
- [Kong GitHub](https://github.com/Kong/kong)
- [Kong Community Forum](https://discuss.konghq.com/)
