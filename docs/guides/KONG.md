# Kong Gateway Provider Anleitung

**Umfassende Anleitung für Kong Gateway Provider in GAL (Gateway Abstraction Layer)**

## Inhaltsverzeichnis

1. [Übersicht](#ubersicht)
2. [Schnellstart](#schnellstart)
3. [Installation und Setup](#installation-und-setup)
4. [Deployment-Strategien](#deployment-strategien)
5. [Konfigurationsoptionen](#konfigurationsoptionen)
6. [Provider-Vergleich](#provider-vergleich)

**Weitere Dokumentation:**
- [Feature-Implementierungen](KONG_FEATURES.md) - Details zu Plugins, Auth, Rate Limiting, Circuit Breaker
- [Migration & Best Practices](KONG_DEPLOYMENT.md) - Migration, Best Practices, Troubleshooting

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

### Kong Gateway Komponenten

```mermaid
graph TB
    subgraph Client["Client Layer"]
        WebApp["Web App"]
        MobileApp["Mobile App"]
        ThirdParty["Third Party API"]
    end

    subgraph Kong["Kong Gateway"]
        AdminAPI["Admin API<br/>(Port 8001)"]

        subgraph Proxy["Proxy Layer (Port 8000)"]
            Router["Router<br/>(Path/Host Matching)"]
            PluginChain["Plugin Chain"]
        end

        subgraph Plugins["Kong Plugins"]
            Auth["Authentication<br/>(JWT, Basic, API Key)"]
            RateLimit["Rate Limiting<br/>(Local/Redis)"]
            CORS["CORS<br/>(Preflight & Headers)"]
            Transform["Request/Response<br/>Transformation"]
        end

        subgraph Storage["Configuration Storage"]
            DBless["DB-less Mode<br/>(YAML Config)"]
            Database["Database Mode<br/>(PostgreSQL)"]
        end
    end

    subgraph Backend["Backend Services"]
        Upstream["Upstream<br/>(Load Balancer)"]
        Target1["Backend Server 1<br/>(api-1:8080)"]
        Target2["Backend Server 2<br/>(api-2:8080)"]
        Target3["Backend Server 3<br/>(api-3:8080)"]
    end

    subgraph Monitoring["Monitoring & Logging"]
        Prometheus["Prometheus Metrics<br/>(/metrics)"]
        Logs["Access Logs<br/>(JSON/Text)"]
        HealthCheck["Health Checks<br/>(Active + Passive)"]
    end

    %% Request Flow
    WebApp --> Router
    MobileApp --> Router
    ThirdParty --> Router

    Router --> PluginChain
    PluginChain --> Auth
    Auth --> RateLimit
    RateLimit --> CORS
    CORS --> Transform
    Transform --> Upstream

    Upstream --> Target1
    Upstream --> Target2
    Upstream --> Target3

    %% Admin & Config
    AdminAPI -.->|Manage| Plugins
    AdminAPI -.->|Configure| Upstream
    DBless -.->|Declarative Config| Router
    Database -.->|Dynamic Config| Router

    %% Monitoring
    Router -.-> Logs
    Router -.-> Prometheus
    Upstream -.-> HealthCheck

    %% Styling
    classDef clientStyle fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000
    classDef gatewayStyle fill:#fff3e0,stroke:#e65100,stroke-width:3px,color:#000
    classDef pluginStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000
    classDef storageStyle fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef backendStyle fill:#e0f2f1,stroke:#004d40,stroke-width:2px,color:#000
    classDef monitorStyle fill:#fce4ec,stroke:#880e4f,stroke-width:2px,color:#000

    class WebApp,MobileApp,ThirdParty clientStyle
    class AdminAPI,Router,PluginChain gatewayStyle
    class Auth,RateLimit,CORS,Transform pluginStyle
    class DBless,Database storageStyle
    class Upstream,Target1,Target2,Target3 backendStyle
    class Prometheus,Logs,HealthCheck monitorStyle
```

**Diagramm-Erklärung:**

- **Client Layer**: Verschiedene Client-Typen (Web, Mobile, APIs)
- **Kong Gateway**: Zentrale Komponenten
  - **Admin API** (Port 8001): Verwaltung und Konfiguration
  - **Proxy Layer** (Port 8000): Request-Handling und Routing
  - **Plugin Chain**: Kong's Plugin-Architektur für Features
- **Backend Services**: Load Balanced Upstream Targets
- **Monitoring**: Observability via Prometheus, Logs, Health Checks
- **DB-less vs. Database Mode**: Zwei Deployment-Optionen

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

### Request Flow

Das folgende Sequenzdiagramm zeigt den vollständigen Request-Ablauf durch Kong Gateway:

```mermaid
sequenceDiagram
    autonumber
    participant Client as Client<br/>(Browser/App)
    participant Kong as Kong Gateway<br/>(Port 8000)
    participant JWT as JWT Plugin
    participant RateLimit as Rate Limiting Plugin
    participant CORS as CORS Plugin
    participant Consumer as Consumer Lookup
    participant Backend as Backend Service<br/>(Upstream)
    participant Logs as Access Logs

    %% CORS Preflight
    rect rgb(240, 240, 250)
        Note over Client,CORS: CORS Preflight Request
        Client->>Kong: OPTIONS /api/users<br/>Origin: https://app.example.com
        Kong->>CORS: Process CORS Preflight
        CORS-->>Kong: CORS Headers
        Kong-->>Client: 200 OK<br/>Access-Control-Allow-Origin: *<br/>Access-Control-Allow-Methods: GET,POST<br/>Access-Control-Max-Age: 86400
    end

    %% Actual Request
    rect rgb(250, 250, 240)
        Note over Client,Backend: Authenticated API Request
        Client->>Kong: POST /api/users<br/>Authorization: Bearer <JWT_TOKEN><br/>Origin: https://app.example.com

        Kong->>JWT: Validate JWT Token
        JWT->>JWT: Extract Token from Header
        JWT->>JWT: Verify Signature<br/>(Public Key / JWKS)
        JWT->>JWT: Check Claims<br/>(iss, aud, exp)

        alt JWT Invalid
            JWT-->>Kong: 401 Unauthorized
            Kong-->>Client: 401 Unauthorized<br/>{"message": "Invalid JWT"}
        else JWT Valid
            JWT-->>Kong: JWT Valid ✓<br/>Claims: {sub: user123}

            Kong->>Consumer: Lookup Consumer<br/>(JWT Key Claim)
            Consumer-->>Kong: Consumer: user123<br/>Groups: [users, premium]

            Kong->>RateLimit: Check Rate Limit<br/>Consumer: user123
            RateLimit->>RateLimit: Count: 45/100 req/s

            alt Rate Limit Exceeded
                RateLimit-->>Kong: 429 Too Many Requests
                Kong-->>Client: 429 Too Many Requests<br/>X-RateLimit-Remaining: 0
            else Within Limit
                RateLimit-->>Kong: Rate Limit OK<br/>Remaining: 55/100

                Kong->>CORS: Add CORS Response Headers
                CORS-->>Kong: CORS Headers Applied

                Kong->>Backend: POST /api/users<br/>X-Consumer-ID: user123<br/>X-Consumer-Groups: users,premium<br/>X-Request-ID: abc-123

                alt Backend Timeout
                    Backend-->>Kong: Timeout (> 60s)
                    Kong-->>Client: 504 Gateway Timeout
                else Backend Error
                    Backend-->>Kong: 500 Internal Server Error
                    Kong-->>Client: 500 Internal Server Error
                else Backend Success
                    Backend-->>Kong: 201 Created<br/>{"id": 456, "name": "New User"}

                    Kong->>CORS: Add CORS Headers to Response
                    Kong-->>Client: 201 Created<br/>Access-Control-Allow-Origin: *<br/>X-RateLimit-Remaining: 55<br/>{"id": 456, "name": "New User"}
                end
            end
        end

        Kong->>Logs: Log Request<br/>(Status: 201, Latency: 120ms, Consumer: user123)
    end

    Note over Client,Logs: Request completed in ~120ms
```

**Flow-Erklärung:**

1. **CORS Preflight (OPTIONS):** Browser sendet Preflight-Request für Cross-Origin Requests
2. **CORS Plugin:** Kong validiert Origin und gibt erlaubte Methods/Headers zurück
3. **Actual Request:** Client sendet echten Request mit JWT Token
4. **JWT Plugin:** Validiert Token-Signatur, Issuer, Audience, Expiration
5. **Consumer Lookup:** Kong identifiziert Consumer basierend auf JWT Key Claim
6. **Rate Limiting Plugin:** Prüft ob Consumer innerhalb des Rate Limits ist (z.B. 100 req/s)
7. **Backend Request:** Kong forwarded Request mit zusätzlichen Headers (Consumer-ID, Groups)
8. **Response:** Backend antwortet, Kong fügt CORS Headers und Rate Limit Info hinzu
9. **Access Logs:** Request wird mit Status, Latency, Consumer-Info geloggt

**Kong Plugin Chain Vorteile:**
- ✅ Modulare Architektur - Plugins können einzeln aktiviert/deaktiviert werden
- ✅ Consumer-basiertes Rate Limiting - Pro User/API Key unterschiedliche Limits
- ✅ Context-Weitergabe - Consumer-Informationen werden an Backend weitergegeben
- ✅ Performance - Plugin Chain läuft in Nginx Worker Threads (Lua)

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

## Deployment-Strategien

### Deployment-Entscheidungsbaum

Der folgende Entscheidungsbaum hilft bei der Auswahl der richtigen Kong-Deployment-Strategie:

```mermaid
flowchart TD
    Start([Kong Deployment planen]) --> Q1{Backend-Typ?}

    Q1 -->|HTTP/HTTPS<br/>RESTful API| Q2{Authentication<br/>benötigt?}
    Q1 -->|gRPC Service| Q3{Kubernetes<br/>Deployment?}
    Q1 -->|WebSocket| Q4{Load Balancing<br/>nötig?}

    Q2 -->|Ja, JWT Auth| Scenario1[Szenario 1:<br/>JWT + Rate Limiting]
    Q2 -->|Nein, API Key| Scenario2[Szenario 2:<br/>API Key Auth]
    Q2 -->|Basic Auth| Scenario3[Szenario 3:<br/>Basic Auth + CORS]

    Q3 -->|Ja, Kubernetes| Scenario4[Szenario 4:<br/>Kong Ingress Controller]
    Q3 -->|Nein, Docker| Scenario1

    Q4 -->|Ja, Multi-Backend| Scenario5[Szenario 5:<br/>Load Balanced Upstream]
    Q4 -->|Nein, Single Backend| Scenario2

    %% Scenario 1 Details
    Scenario1 --> S1A[1. DB-less Mode wählen]
    S1A --> S1B[2. JWT Plugin konfigurieren<br/>mit Issuer + JWKS URI]
    S1B --> S1C[3. Rate Limiting Plugin<br/>100 req/s, Local Policy]
    S1C --> S1D[4. Consumer erstellen<br/>für Subscription]
    S1D --> S1E[5. GAL Config generieren]
    S1E --> S1F[6. Kong deployen<br/>mit Declarative Config]
    S1F --> S1G[Production API<br/>mit JWT + Rate Limit]

    %% Scenario 2 Details
    Scenario2 --> S2A[1. API Key Plugin aktivieren]
    S2A --> S2B[2. Consumer + Credential<br/>erstellen]
    S2B --> S2C[3. Usage Plan definieren<br/>Rate Limits pro Key]
    S2C --> S2D[4. GAL Config generieren]
    S2D --> S2E[5. Kong deployen]
    S2E --> S2F[API Key basierte API<br/>bereit]

    %% Scenario 3 Details
    Scenario3 --> S3A[1. Basic Auth Plugin<br/>aktivieren]
    S3A --> S3B[2. CORS Plugin<br/>konfigurieren]
    S3B --> S3C[3. Credentials für User<br/>erstellen]
    S3C --> S3D[4. GAL Config mit CORS]
    S3D --> S3E[5. Kong deployen]
    S3E --> S3F[Browser-kompatible API<br/>mit Basic Auth]

    %% Scenario 4 Details
    Scenario4 --> S4A[1. Kong Ingress Controller<br/>via Helm installieren]
    S4A --> S4B[2. KongPlugin CRDs<br/>definieren]
    S4B --> S4C[3. Ingress Resources<br/>erstellen]
    S4C --> S4D[4. GAL Config als<br/>ConfigMap mounten]
    S4D --> S4E[5. kubectl apply]
    S4E --> S4F[Kubernetes-native<br/>API Gateway]

    %% Scenario 5 Details
    Scenario5 --> S5A[1. Upstream mit<br/>Multiple Targets]
    S5A --> S5B[2. Load Balancing<br/>Algorithm wählen]
    S5B --> S5C[3. Active Health Checks<br/>konfigurieren]
    S5C --> S5D[4. Circuit Breaker via<br/>Passive Health Checks]
    S5D --> S5E[5. GAL Config mit<br/>Upstream generieren]
    S5E --> S5F[High-Availability API<br/>mit Auto-Failover]

    %% Styling
    classDef questionStyle fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000
    classDef scenarioStyle fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px,color:#000
    classDef stepStyle fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000
    classDef finalStyle fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000

    class Q1,Q2,Q3,Q4 questionStyle
    class Scenario1,Scenario2,Scenario3,Scenario4,Scenario5 scenarioStyle
    class S1A,S1B,S1C,S1D,S1E,S1F,S2A,S2B,S2C,S2D,S2E,S3A,S3B,S3C,S3D,S3E,S4A,S4B,S4C,S4D,S4E,S5A,S5B,S5C,S5D,S5E stepStyle
    class S1G,S2F,S3F,S4F,S5F finalStyle
```

**Deployment-Strategien im Überblick:**

| Szenario | Use Case | Hauptmerkmale | Mode |
|----------|----------|---------------|------|
| **1. JWT + Rate Limiting** | Production APIs mit User Auth | JWT Validation, Consumer-based Rate Limiting | DB-less oder Database |
| **2. API Key Auth** | Public APIs, Subscription Management | API Keys, Usage Plans, Rate Limits | DB-less empfohlen |
| **3. Basic Auth + CORS** | Internal APIs, Browser Apps | Basic Auth, CORS für SPAs | DB-less |
| **4. Kubernetes Ingress** | Cloud-native Microservices | KongPlugin CRDs, Ingress Resources | Kubernetes |
| **5. Load Balanced Upstream** | High-Availability APIs | Multiple Targets, Health Checks, Failover | DB-less oder Database |

**DB-less vs. Database Mode:**

| Feature | DB-less Mode | Database Mode |
|---------|-------------|---------------|
| **Config** | Declarative YAML | Admin API (Dynamic) |
| **Performance** | Schneller (kein DB Overhead) | Etwas langsamer |
| **Deployment** | Einfacher (keine DB nötig) | Komplexer (PostgreSQL) |
| **Runtime Changes** | Reload nötig | Sofort via Admin API |
| **Use Case** | Production, GitOps | Dynamic Subscriptions, Kong Manager |
| **GAL Empfehlung** | ✅ Bevorzugt | ⚠️ Für spezielle Use Cases |

**Entscheidungshilfe:**
- 🚀 **DB-less Mode** für statische Konfigurationen, GitOps, Container-Deployments
- 🔄 **Database Mode** für dynamische Consumer-Verwaltung, Kong Manager UI
- ☸️ **Kubernetes** für Cloud-native Microservices mit Ingress Controller
- 🌐 **Load Balancing** für High-Availability Production APIs

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

