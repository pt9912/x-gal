# GAL Best Practices

Diese Best Practices helfen Ihnen, GAL effektiv, sicher und wartbar in Production einzusetzen.

---

## 1. Naming Conventions

### Services

**✅ Gut:**
```yaml
services:
  - name: user_authentication_service
  - name: order_processing_service
  - name: payment_gateway_service
  - name: inventory_management_api
```

**❌ Schlecht:**
```yaml
services:
  - name: UserAuth123!
  - name: srv1
  - name: MyAPIService
  - name: test-svc
```

**Regeln:**
- Verwende `snake_case` (Kleinbuchstaben mit Unterstrichen)
- Beschreibende Namen (was macht der Service?)
- Vermeide Sonderzeichen außer `_` und `-`
- Keine generischen Namen wie `api`, `service`, `gateway`

### Routes

**✅ Gut:**
```yaml
routes:
  - path_prefix: /api/v1/users
  - path_prefix: /api/v1/orders
  - path_prefix: /api/v1/products
```

**❌ Schlecht:**
```yaml
routes:
  - path_prefix: /usr
  - path_prefix: /o
  - path_prefix: /p
```

**Regeln:**
- API-Versionierung einbauen (`/api/v1/`, `/api/v2/`)
- Plural für Collections (`/users`, nicht `/user`)
- REST-konforme Pfade

### Computed Fields

**✅ Gut:**
```yaml
computed_fields:
  - field: user_id
    generator: uuid
    prefix: "usr_"
  - field: order_id
    generator: uuid
    prefix: "ord_"
  - field: transaction_id
    generator: uuid
    prefix: "txn_"
```

**Regeln:**
- Sprechende Prefixes (`usr_`, `ord_`, `txn_`)
- Suffix `_id` für IDs
- Suffix `_at` für Timestamps (`created_at`, `updated_at`)

---

## 2. Transformationen sinnvoll einsetzen

### Defaults nur für optionale Felder

**✅ Gut:**
```yaml
transformation:
  enabled: true
  defaults:
    # Optionale Felder mit sinnvollen Defaults
    status: "draft"
    priority: 3
    visibility: "private"
    language: "en"
```

**❌ Schlecht:**
```yaml
transformation:
  enabled: true
  defaults:
    # Kritische Business-Felder nicht als Default!
    customer_id: "unknown"
    amount: 0
    payment_method: "none"
```

**Regeln:**
- Defaults nur für **optionale** Felder
- Keine kritischen Business-Felder als Default (nutze `required_fields`)
- Defaults sollten sinnvolle Standardwerte sein

### IDs immer generieren

**✅ Gut:**
```yaml
computed_fields:
  # IDs immer generieren lassen
  - field: id
    generator: uuid
  - field: order_id
    generator: uuid
    prefix: "ord_"
  - field: request_id
    generator: uuid
```

**Regeln:**
- Nie IDs vom Client generieren lassen (Sicherheitsrisiko)
- UUIDs für global eindeutige IDs
- Prefixes für Lesbarkeit (`ord_123abc`, `usr_456def`)

### Validation für kritische Felder

**✅ Gut:**
```yaml
validation:
  # Kritische Business-Felder validieren
  required_fields:
    - customer_id
    - amount
    - payment_method
    - order_items
```

**Regeln:**
- Alle kritischen Felder validieren
- Früh validieren (am Gateway, nicht erst im Backend)
- Klare Fehlermeldungen (400 Bad Request)

---

## 3. Security Best Practices

### Secrets nie hardcoden

**✅ Gut:**
```yaml
# config.yaml
authentication:
  enabled: true
  type: jwt
  jwt:
    secret: "${JWT_SECRET}"  # Aus Environment Variable
    api_key: "${API_KEY}"
```

```bash
# .env
export JWT_SECRET="your-secret-key-here"
export API_KEY="your-api-key-here"

# Generierung mit Secrets
gal generate -c config.yaml -p kong -o kong.yaml
```

**❌ Schlecht:**
```yaml
# NIEMALS Secrets in Config-Files!
authentication:
  enabled: true
  type: jwt
  jwt:
    secret: "hardcoded-secret-123"  # ❌ Security-Risiko!
```

**Regeln:**
- Secrets immer aus Environment Variables
- `.env`-Files nie committen (`.gitignore`)
- Secrets Management nutzen (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)
- Secrets rotieren (regelmäßig neue Secrets)

### API Keys schützen

**✅ Gut:**
```yaml
authentication:
  enabled: true
  type: api_key
  api_key:
    header: "X-API-Key"
    keys_from_env: true  # Keys aus Environment
```

**Regeln:**
- API Keys nie in Git committen
- API Keys in Header (nicht URL-Parameter)
- Rate Limiting für API-Key-basierte Auth

### HTTPS/TLS erzwingen

**✅ Gut:**
```yaml
global:
  port: 443
  tls:
    enabled: true
    cert: "${TLS_CERT_PATH}"
    key: "${TLS_KEY_PATH}"
  redirect_http_to_https: true
```

**Regeln:**
- TLS für Production (immer!)
- Automatisches HTTP→HTTPS Redirect
- Let's Encrypt für kostenlose Zertifikate
- TLS 1.2 oder höher

---

## 4. Performance Optimization

### Connection Pooling

**✅ Gut:**
```yaml
services:
  - name: high_traffic_api
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
      connection_pool:
        max_connections: 1000
        max_idle_connections: 100
        idle_timeout: 90s
```

**Regeln:**
- Connection Pooling für häufig genutzte Backends
- `max_connections` basierend auf Backend-Kapazität
- `idle_timeout` für Resource Cleanup

### Timeouts richtig konfigurieren

**✅ Gut:**
```yaml
services:
  - name: slow_backend_api
    type: rest
    protocol: http
    upstream:
      host: slow-backend
      port: 8080
    timeout:
      connect: 5s      # Connection Timeout
      send: 10s        # Request Timeout
      read: 30s        # Response Timeout
```

**Regeln:**
- Timeouts immer setzen (verhindert Hanging Requests)
- `connect_timeout`: 2-5s (schnelles Fail-Fast)
- `read_timeout`: Abhängig vom Backend (10-60s)
- Retries mit Backoff kombinieren

### Caching aktivieren

**✅ Gut:**
```yaml
services:
  - name: static_content_api
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api/products
        methods: [GET]
    caching:
      enabled: true
      ttl: 300  # 5 Minuten
      cache_key: "$request_uri"
```

**Regeln:**
- Caching für Read-Heavy Endpoints
- TTL basierend auf Daten-Freshness-Anforderungen
- Cache-Invalidierung bei Updates

---

## 5. Resilience Patterns

### Circuit Breaker

**✅ Gut:**
```yaml
services:
  - name: flaky_service
    type: rest
    protocol: http
    upstream:
      host: unreliable-backend
      port: 8080
    circuit_breaker:
      enabled: true
      consecutive_errors: 5       # Nach 5 Fehlern: Circuit OPEN
      interval: 30s               # Prüfung alle 30s
      base_ejection_time: 30s     # Mindestens 30s OPEN
      max_ejection_percent: 50    # Max. 50% der Instanzen ausschließen
```

**Regeln:**
- Circuit Breaker für instabile Backends
- `consecutive_errors`: 3-5 für schnelles Fail-Fast
- `base_ejection_time`: 30-60s für Recovery
- Monitoring für Circuit Breaker Events

### Retries mit Exponential Backoff

**✅ Gut:**
```yaml
services:
  - name: retry_enabled_api
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    retry:
      enabled: true
      max_attempts: 3
      backoff:
        initial_interval: 100ms
        max_interval: 5s
        multiplier: 2
      retry_on:
        - 5xx
        - connection_failure
        - timeout
```

**Regeln:**
- Retries nur für idempotente Requests (GET, PUT, DELETE)
- Nie Retries für POST (Risk of Duplicate Creates)
- Exponential Backoff (100ms → 200ms → 400ms → ...)
- Max. 3 Retries

### Health Checks

**✅ Gut:**
```yaml
services:
  - name: monitored_api
    type: rest
    protocol: http
    upstream:
      targets:
        - host: backend1
          port: 8080
        - host: backend2
          port: 8080
    routes:
      - path_prefix: /api
    health_check:
      enabled: true
      interval: 10s
      timeout: 5s
      unhealthy_threshold: 3
      healthy_threshold: 2
      path: /health
      expected_status: 200
```

**Regeln:**
- Health Checks für alle Multi-Instance Backends
- `interval`: 5-10s für schnelle Detection
- `unhealthy_threshold`: 2-3 für Fail-Fast
- Dedizierter `/health` Endpoint im Backend

---

## 6. Monitoring & Observability

### Logging aktivieren

**✅ Gut:**
```yaml
global:
  logging:
    enabled: true
    level: info
    format: json
    fields:
      - timestamp
      - request_id
      - method
      - path
      - status
      - duration
      - upstream_host
      - client_ip
```

**Regeln:**
- JSON-Format für strukturiertes Logging
- `request_id` für Request Tracing
- Log Level: `info` für Production, `debug` für Dev
- Sensitive Daten filtern (Passwords, API Keys, Tokens)

### Metrics exportieren

**✅ Gut:**
```yaml
global:
  metrics:
    enabled: true
    endpoint: /metrics
    format: prometheus
```

**Regeln:**
- Prometheus-Format für Monitoring
- Metriken: Request Rate, Error Rate, Latency (P50, P95, P99)
- Grafana Dashboards für Visualisierung
- Alerts für Critical Metrics (Error Rate > 5%, Latency > 1s)

### Distributed Tracing

**✅ Gut:**
```yaml
services:
  - name: traced_api
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    tracing:
      enabled: true
      provider: jaeger
      endpoint: "http://jaeger:14268/api/traces"
      sample_rate: 0.1  # 10% Sampling
```

**Regeln:**
- Tracing für Microservices-Architekturen
- Sampling für Production (1-10%)
- Trace IDs in Logs für Korrelation

---

## 7. Multi-Environment Configuration

### Environment-spezifische Configs

**✅ Gut:**
```bash
# Basis-Config (shared)
config/base.yaml

# Environment-Overrides
config/dev.yaml
config/staging.yaml
config/prod.yaml
```

**base.yaml:**
```yaml
version: "1.0"

services:
  - name: users_api
    type: rest
    protocol: http
    upstream:
      host: "${USERS_SERVICE_HOST}"
      port: "${USERS_SERVICE_PORT}"
    routes:
      - path_prefix: /api/users
```

**dev.yaml (Override):**
```bash
export USERS_SERVICE_HOST=localhost
export USERS_SERVICE_PORT=3000
```

**prod.yaml (Override):**
```bash
export USERS_SERVICE_HOST=users-service.prod.svc.cluster.local
export USERS_SERVICE_PORT=8080
```

**Generierung:**
```bash
# Dev
source config/dev.yaml && gal generate -c config/base.yaml -p envoy -o dev/envoy.yaml

# Prod
source config/prod.yaml && gal generate -c config/base.yaml -p envoy -o prod/envoy.yaml
```

**Regeln:**
- Basis-Config Environment-agnostisch
- Environment-Variablen für Unterschiede
- Keine Secrets in Config-Files

---

## 8. Version Control & CI/CD

### Git Best Practices

**✅ Gut:**
```bash
# .gitignore
.env
*.secret
generated/
migration/
```

```bash
# Struktur
.
├── config/
│   ├── base.yaml
│   ├── dev.env.example
│   ├── staging.env.example
│   └── prod.env.example
├── examples/
│   ├── simple-rest-api.yaml
│   └── grpc-service.yaml
└── README.md
```

**Regeln:**
- Nie Secrets committen
- `.env.example` mit Platzhaltern
- `generated/` Ordner nicht committen

### CI/CD Integration

**✅ Gut:**
```yaml
# .github/workflows/gateway-deploy.yml
name: Deploy Gateway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install GAL
        run: pip install gal

      - name: Validate Config
        run: gal validate -c config/gateway.yaml

      - name: Generate Envoy Config
        run: gal generate -c config/gateway.yaml -p envoy -o envoy.yaml

      - name: Deploy to Kubernetes
        run: kubectl apply -f envoy.yaml

      - name: Health Check
        run: |
          sleep 10
          curl --retry 5 --retry-delay 2 http://gateway.example.com/health
```

**Regeln:**
- Config-Validierung in CI/CD
- Automated Deployment
- Health Checks nach Deployment
- Rollback-Strategie

---

## 9. Testing & Validation

### Lokales Testen

**✅ Gut:**
```bash
# 1. Config validieren
gal validate -c config.yaml

# 2. Config generieren
gal generate -c config.yaml -p envoy -o envoy.yaml

# 3. Envoy mit generierter Config starten
docker run -d --name envoy \
  -v $(pwd)/envoy.yaml:/etc/envoy/envoy.yaml \
  -p 10000:10000 \
  envoyproxy/envoy:v1.28-latest

# 4. Testen
curl http://localhost:10000/api/users

# 5. Logs prüfen
docker logs envoy

# 6. Cleanup
docker stop envoy && docker rm envoy
```

### Integration Tests

**✅ Gut:**
```bash
# tests/integration_test.sh

#!/bin/bash
set -e

# 1. Backend starten (Mock)
docker run -d --name backend -p 8080:8080 mockserver

# 2. Gateway Config generieren
gal generate -c config.yaml -p envoy -o envoy.yaml

# 3. Gateway starten
docker run -d --name gateway \
  --link backend \
  -v $(pwd)/envoy.yaml:/etc/envoy/envoy.yaml \
  -p 10000:10000 \
  envoyproxy/envoy:v1.28-latest

# 4. Wait for startup
sleep 5

# 5. Tests
curl -f http://localhost:10000/api/users || exit 1
curl -f http://localhost:10000/api/orders || exit 1

# 6. Cleanup
docker stop gateway backend
docker rm gateway backend
```

**Regeln:**
- Integration Tests für CI/CD
- Mock-Backends für Tests
- Health Checks vor Tests

---

## 10. Documentation

### Config Documentation

**✅ Gut:**
```yaml
# users-api.yaml

# User Management API
# Owner: Platform Team
# Contact: platform@example.com
# Last Updated: 2025-01-20

version: "1.0"
provider: envoy

services:
  # REST API for CRUD operations on Users
  # Backend: users-service (Python Flask)
  # SLA: 99.9% uptime, < 200ms p95 latency
  - name: users_api
    type: rest
    protocol: http
    upstream:
      host: users-service
      port: 8080
    routes:
      - path_prefix: /api/v1/users
        methods: [GET, POST, PUT, DELETE]

    # Transformations:
    # - Auto-generate user_id (UUID with 'usr_' prefix)
    # - Set created_at timestamp
    # - Validate required fields (email, username)
    transformation:
      enabled: true
      computed_fields:
        - field: user_id
          generator: uuid
          prefix: "usr_"
        - field: created_at
          generator: timestamp
      validation:
        required_fields:
          - email
          - username
```

**Regeln:**
- Comments für komplexe Configs
- Owner & Contact Info
- SLA-Informationen
- Transformation-Logik dokumentieren

### README.md

**✅ Gut:**
```markdown
# User API Gateway

## Übersicht
Gateway-Konfiguration für User Management API.

## Deployment
```bash
# Dev
gal generate -c users-api.yaml -p envoy -o dev/envoy.yaml

# Prod
gal generate -c users-api.yaml -p kong -o prod/kong.yaml
```

## Endpoints
- `GET /api/v1/users` - List users
- `POST /api/v1/users` - Create user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

## Monitoring
- Grafana Dashboard: https://grafana.example.com/d/users-api
- Logs: Kibana → `service:users_api`
```

---

## 11. Provider-spezifische Best Practices

### Envoy

**✅ Gut:**
- Admin API aktivieren (`:9901/stats`, `:9901/clusters`)
- Hot-Reload nutzen (`envoy --restart-epoch`)
- YAML-Config validieren vor Deployment

### Kong

**✅ Gut:**
- Declarative Config nutzen (nicht DB-Mode)
- Kong Admin API für Debugging (`:8001/status`)
- Plugin-Prioritäten beachten

### APISIX

**✅ Gut:**
- etcd für Config Storage (Clustering)
- Dashboard für UI-Management
- Serverless Lua für Custom Logic

### Nginx

**✅ Gut:**
- OpenResty für Lua-Support
- `nginx -t` für Config-Validierung
- Access Logs in JSON-Format

### Cloud Providers (AWS, Azure, GCP)

**✅ Gut:**
- Nutze native Monitoring (CloudWatch, Azure Monitor, Cloud Monitoring)
- Infrastructure as Code (Terraform, CloudFormation, ARM)
- Managed TLS Certificates (ACM, Key Vault, Certificate Manager)

---

## Zusammenfassung: Die wichtigsten Regeln

1. ✅ **Secrets aus Environment Variables** (nie hardcoden)
2. ✅ **IDs immer generieren** (UUID mit Prefix)
3. ✅ **HTTPS/TLS für Production** (immer!)
4. ✅ **Rate Limiting aktivieren** (DDoS-Schutz)
5. ✅ **Health Checks konfigurieren** (Multi-Instance Backends)
6. ✅ **Circuit Breaker für instabile Backends**
7. ✅ **Logging & Metrics exportieren** (JSON + Prometheus)
8. ✅ **Timeouts setzen** (verhindert Hanging Requests)
9. ✅ **Config validieren in CI/CD**
10. ✅ **Dokumentation pflegen** (README, Comments)

---

## Nächste Schritte

- 📖 [Konfigurationsbeispiele](EXAMPLES.md) - Vollständige Beispiele
- 🔧 [CLI-Referenz](../api/CLI_REFERENCE.md) - Alle Befehle
- 🏗️ [Provider-Guides](PROVIDERS.md) - Provider-spezifische Details
- 🌐 [Schnellstart](QUICKSTART.md) - Getting Started
