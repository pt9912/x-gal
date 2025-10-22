# GCP API Gateway Provider Guide

**Letzte Aktualisierung:** 2025-10-20
**Status:** ✅ Production Ready (v1.4.0)

---

## Übersicht

GCP API Gateway ist ein vollständig verwalteter Service von Google Cloud Platform, der es Entwicklern ermöglicht, sichere und skalierbare APIs für ihre Backend-Services zu erstellen, zu deployen und zu verwalten.

GAL unterstützt GCP API Gateway als **Cloud-Provider** mit vollständiger Import/Export-Funktionalität über OpenAPI 2.0 (Swagger) mit `x-google-*` Extensions.

### Motivation

**Warum GCP API Gateway mit GAL?**

- **Cloud-Native**: Perfekt für GCP-basierte Microservices-Architekturen
- **Serverless**: Nahtlose Integration mit Cloud Run und Cloud Functions
- **Skalierbarkeit**: Automatische Skalierung ohne Infrastruktur-Management
- **GCP-Ökosystem**: Integration mit Cloud IAM, Cloud Logging, Cloud Monitoring
- **Pay-per-Use**: Nur bezahlen für tatsächliche API-Aufrufe
- **Multi-Region**: Globale Verfügbarkeit mit Load Balancing

---

## GCP API Gateway Architektur

### API Gateway Komponenten

```mermaid
graph TB
    subgraph Client["Client Layer"]
        WebApp["Web App"]
        MobileApp["Mobile App"]
        ThirdParty["Third Party"]
    end

    subgraph GCP["GCP API Gateway"]
        Gateway["API Gateway<br/>(Public Endpoint)"]

        subgraph Auth["Authentication Layer"]
            JWT["JWT Validation<br/>(x-google-issuer)"]
            APIKey["API Key Validation"]
        end

        subgraph Traffic["Traffic Management"]
            CORS["CORS Handling<br/>(Preflight & Headers)"]
            PathTrans["Path Translation"]
            Timeout["Request Timeout<br/>(Deadline)"]
        end

        subgraph Config["API Configuration"]
            APIConfig["API Config<br/>(OpenAPI 2.0)"]
            BackendConfig["Backend Config<br/>(x-google-backend)"]
        end
    end

    subgraph Backend["Backend Services"]
        CloudRun["Cloud Run<br/>(Serverless Container)"]
        CloudFunc["Cloud Functions<br/>(Serverless Functions)"]
        AppEngine["App Engine<br/>(PaaS)"]
        HTTP["HTTP/HTTPS<br/>(External Backend)"]
    end

    subgraph Monitoring["Monitoring & Logging"]
        Logging["Cloud Logging<br/>(Access Logs)"]
        Metrics["Cloud Monitoring<br/>(Metrics & Alerts)"]
        Trace["Cloud Trace<br/>(Distributed Tracing)"]
    end

    %% Request Flow
    WebApp --> Gateway
    MobileApp --> Gateway
    ThirdParty --> Gateway

    Gateway --> JWT
    Gateway --> APIKey
    JWT --> CORS
    APIKey --> CORS
    CORS --> PathTrans
    PathTrans --> Timeout

    Timeout --> APIConfig
    APIConfig --> BackendConfig

    BackendConfig --> CloudRun
    BackendConfig --> CloudFunc
    BackendConfig --> AppEngine
    BackendConfig --> HTTP

    Gateway -.-> Logging
    Gateway -.-> Metrics
    Gateway -.-> Trace

    %% Styling
    classDef clientStyle fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000
    classDef gatewayStyle fill:#fff3e0,stroke:#e65100,stroke-width:3px,color:#000
    classDef authStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000
    classDef trafficStyle fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px,color:#000
    classDef configStyle fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef backendStyle fill:#e0f2f1,stroke:#004d40,stroke-width:2px,color:#000
    classDef monitorStyle fill:#fce4ec,stroke:#880e4f,stroke-width:2px,color:#000

    class WebApp,MobileApp,ThirdParty clientStyle
    class Gateway gatewayStyle
    class JWT,APIKey authStyle
    class CORS,PathTrans,Timeout trafficStyle
    class APIConfig,BackendConfig configStyle
    class CloudRun,CloudFunc,AppEngine,HTTP backendStyle
    class Logging,Metrics,Trace monitorStyle
```

### Request Flow

Das folgende Sequenzdiagramm zeigt den vollständigen Request-Ablauf durch GCP API Gateway:

```mermaid
sequenceDiagram
    autonumber
    participant Client as Client<br/>(Web/Mobile App)
    participant Gateway as GCP API Gateway
    participant JWT as JWT Validator<br/>(x-google-issuer)
    participant CORS as CORS Handler
    participant SA as Service Account<br/>Auth
    participant Backend as Backend Service<br/>(Cloud Run/Functions)
    participant Log as Cloud Logging

    %% CORS Preflight
    rect rgb(240, 240, 250)
        Note over Client,CORS: CORS Preflight Request
        Client->>Gateway: OPTIONS /api/users<br/>Origin: https://app.example.com
        Gateway->>CORS: Check CORS Config
        CORS-->>Gateway: CORS Headers
        Gateway-->>Client: 200 OK<br/>Access-Control-Allow-Origin: *<br/>Access-Control-Allow-Methods: GET,POST<br/>Access-Control-Max-Age: 3600
    end

    %% Actual Request
    rect rgb(250, 250, 240)
        Note over Client,Backend: Actual API Request
        Client->>Gateway: GET /api/users<br/>Authorization: Bearer <JWT_TOKEN><br/>Origin: https://app.example.com

        Gateway->>JWT: Validate JWT Token
        JWT->>JWT: Check Issuer<br/>(https://accounts.google.com)
        JWT->>JWT: Verify Signature<br/>(JWKS URI)
        JWT->>JWT: Check Audiences<br/>(my-project.example.com)
        JWT->>JWT: Check Expiration

        alt JWT Invalid
            JWT-->>Gateway: 401 Unauthorized
            Gateway-->>Client: 401 Unauthorized<br/>Invalid JWT Token
        else JWT Valid
            JWT-->>Gateway: JWT Valid ✓

            Gateway->>CORS: Add CORS Headers
            CORS-->>Gateway: CORS Headers Applied

            Gateway->>SA: Generate Service Account JWT<br/>Audience: Backend URL
            SA-->>Gateway: SA JWT Token

            Gateway->>Backend: GET /api/users<br/>Authorization: Bearer <SA_JWT><br/>X-Forwarded-Authorization: Bearer <CLIENT_JWT>

            alt Backend Timeout
                Backend-->>Gateway: Timeout (> deadline)
                Gateway-->>Client: 504 Gateway Timeout
            else Backend Success
                Backend-->>Gateway: 200 OK<br/>Content-Type: application/json<br/>[{"id":1,"name":"User"}]

                Gateway->>Gateway: Apply Path Translation
                Gateway->>CORS: Add CORS Response Headers

                Gateway-->>Client: 200 OK<br/>Access-Control-Allow-Origin: *<br/>[{"id":1,"name":"User"}]
            end
        end

        Gateway->>Log: Log Request<br/>(Status, Latency, Client IP)
    end

    Note over Client,Log: Request completed in ~100ms
```

**Flow-Erklärung:**

1. **CORS Preflight (OPTIONS):** Browser sendet Preflight-Request
2. **CORS Validation:** Gateway prüft Origin und gibt erlaubte Methods/Headers zurück
3. **Actual Request:** Client sendet echten Request mit JWT Token
4. **JWT Validation:** Gateway validiert Token gegen Issuer und JWKS URI
5. **Audience Check:** Gateway prüft ob Token-Audience in Config erlaubt ist
6. **Service Account Auth:** Gateway generiert SA JWT für Backend-Authentifizierung
7. **Backend Request:** Gateway forwarded Request mit SA Auth an Backend
8. **Response:** Backend antwortet, Gateway fügt CORS Headers hinzu
9. **Logging:** Request wird in Cloud Logging persistiert

### Backend-Typen

| Backend | Beschreibung | Verwendung |
|---------|-------------|------------|
| **Cloud Run** | Serverless Container | Microservices, REST APIs |
| **Cloud Functions** | Event-driven Functions | Webhooks, leichtgewichtige APIs |
| **App Engine** | PaaS Platform | Legacy Apps, komplexe Anwendungen |
| **HTTP/HTTPS** | Externes HTTP Backend | Bestehende Services, Hybrid Cloud |

---

## Schnellstart

### 1. Voraussetzungen

- GCP Account mit API Gateway API aktiviert
- `gcloud` CLI installiert und konfiguriert
- GAL installiert (`pip install gal-gateway`)
- Service Account mit API Gateway Berechtigungen

### 2. Einfache HTTP Backend API

**GAL Konfiguration** (`config.yaml`):

```yaml
version: "1.0"
provider: gcp_apigateway

global_config:
  gcp_apigateway:
    # GCP Project
    project_id: "my-gcp-project"
    api_id: "user-api"
    api_display_name: "User Management API"
    region: "us-central1"

    # Backend
    backend_address: "https://backend.example.com"
    backend_protocol: "https"
    backend_deadline: 30.0

    # CORS
    cors_enabled: true
    cors_allow_origins:
      - "*"

services:
  - name: user_service
    type: rest
    protocol: http

    upstream:
      targets:
        - host: backend.example.com
          port: 443

    routes:
      - path_prefix: /api/users
        methods:
          - GET
          - POST

      - path_prefix: /api/users/{id}
        methods:
          - GET
          - PUT
          - DELETE
```

**OpenAPI 2.0 generieren:**

```bash
gal generate -c config.yaml -p gcp_apigateway > openapi.yaml
```

**Deployment:**

```bash
# 1. API erstellen
gcloud api-gateway apis create user-api \
  --project=my-gcp-project

# 2. API Config deployen
gcloud api-gateway api-configs create user-api-config \
  --api=user-api \
  --openapi-spec=openapi.yaml \
  --project=my-gcp-project

# 3. Gateway erstellen
gcloud api-gateway gateways create user-api-gateway \
  --api=user-api \
  --api-config=user-api-config \
  --location=us-central1 \
  --project=my-gcp-project
```

**Gateway URL abrufen:**

```bash
gcloud api-gateway gateways describe user-api-gateway \
  --location=us-central1 \
  --project=my-gcp-project \
  --format="value(defaultHostname)"
```

**API testen:**

```bash
GATEWAY_URL=$(gcloud api-gateway gateways describe user-api-gateway \
  --location=us-central1 --project=my-gcp-project \
  --format="value(defaultHostname)")

curl "https://${GATEWAY_URL}/api/users"
```

---

## Konfigurationsoptionen

### GCP API Gateway Config (`GCPAPIGatewayConfig`)

#### API-Konfiguration

```yaml
global_config:
  gcp_apigateway:
    # API Identifikation
    api_id: "my-api"                    # API ID (eindeutig im Projekt)
    api_display_name: "My API"          # Display Name
    api_config_id: "my-api-config"      # API Config ID
    gateway_id: "my-api-gateway"        # Gateway ID

    # GCP Project & Region
    project_id: "my-gcp-project"        # GCP Project ID (REQUIRED)
    region: "us-central1"               # Gateway Region
```

**Verfügbare Regionen:**
- `us-central1`, `us-east1`, `us-west1`
- `europe-west1`, `europe-west2`, `europe-west3`
- `asia-northeast1`, `asia-southeast1`

#### Backend-Konfiguration

```yaml
global_config:
  gcp_apigateway:
    # Backend Service
    backend_address: "https://service.run.app"   # Backend URL (REQUIRED)
    backend_protocol: "https"                    # http | https

    # Path Translation
    backend_path_translation: "APPEND_PATH_TO_ADDRESS"
    # APPEND_PATH_TO_ADDRESS: Backend URL + Request Path
    # CONSTANT_ADDRESS:       Backend URL (ohne Request Path)

    # Timeout
    backend_deadline: 30.0                      # Request timeout (Sekunden)

    # Backend Authentication
    backend_disable_auth: false                 # Backend Auth deaktivieren
    backend_jwt_audience: ""                    # JWT Audience für Backend
```

**Path Translation Beispiele:**

| Translation | Backend URL | Request | Final URL |
|------------|-------------|---------|-----------|
| `APPEND_PATH_TO_ADDRESS` | `https://api.example.com` | `/users/123` | `https://api.example.com/users/123` |
| `CONSTANT_ADDRESS` | `https://api.example.com/v1` | `/users/123` | `https://api.example.com/v1` |

#### JWT Authentication

```yaml
global_config:
  gcp_apigateway:
    # JWT Validation (x-google-issuer, x-google-jwks_uri)
    jwt_issuer: "https://accounts.google.com"
    jwt_jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    jwt_audiences:
      - "https://my-project.example.com"
      - "my-mobile-app"
```

**Unterstützte JWT Issuer:**

1. **Google Sign-In:**
   - Issuer: `https://accounts.google.com`
   - JWKS URI: `https://www.googleapis.com/oauth2/v3/certs`

2. **Firebase Authentication:**
   - Issuer: `https://securetoken.google.com/PROJECT_ID`
   - JWKS URI: `https://www.googleapis.com/service_accounts/v1/metadata/x509/securetoken@system.gserviceaccount.com`

3. **Custom JWT Provider:**
   - Eigener Issuer und JWKS Endpoint

#### CORS Configuration

```yaml
global_config:
  gcp_apigateway:
    # CORS Settings
    cors_enabled: true
    cors_allow_origins:
      - "https://app.example.com"
      - "https://admin.example.com"
    cors_allow_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS
    cors_allow_headers:
      - Content-Type
      - Authorization
      - X-Custom-Header
    cors_expose_headers:
      - X-Request-Id
    cors_max_age: 3600  # Preflight Cache (Sekunden)
```

#### Service Account Authentication

```yaml
global_config:
  gcp_apigateway:
    # Service Account für Backend Auth
    service_account_email: "api-gateway@my-project.iam.gserviceaccount.com"
```

**Service Account Setup:**

```bash
# 1. Service Account erstellen
gcloud iam service-accounts create api-gateway \
  --display-name="API Gateway Service Account" \
  --project=my-project

# 2. Backend Berechtigung erteilen (z.B. Cloud Run)
gcloud run services add-iam-policy-binding my-service \
  --member="serviceAccount:api-gateway@my-project.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=us-central1

# 3. Bei API Config Deployment angeben
gcloud api-gateway api-configs create my-config \
  --api=my-api \
  --openapi-spec=openapi.yaml \
  --backend-auth-service-account=api-gateway@my-project.iam.gserviceaccount.com \
  --project=my-project
```

---

## Provider-Spezifische Features

### 1. OpenAPI 2.0 (Swagger) Only

**Wichtig:** GCP API Gateway unterstützt **nur OpenAPI 2.0 (Swagger)**, nicht OpenAPI 3.0.

GAL generiert automatisch OpenAPI 2.0 für GCP:

```yaml
swagger: "2.0"
info:
  title: "User API"
  version: "1.0.0"
schemes:
  - https
x-google-backend:
  address: "https://backend.example.com"
  deadline: 30.0
```

### 2. x-google-backend Extension

Die `x-google-backend` Extension definiert Backend-Konfiguration:

```yaml
x-google-backend:
  address: "https://service-abc123-uc.a.run.app"
  path_translation: "APPEND_PATH_TO_ADDRESS"
  deadline: 60.0
  disable_auth: false
  jwt_audience: "https://service-abc123-uc.a.run.app"
```

**Per-Operation Backend:**

```yaml
paths:
  /api/users:
    get:
      x-google-backend:
        address: "https://read-service.run.app"
        deadline: 10.0
    post:
      x-google-backend:
        address: "https://write-service.run.app"
        deadline: 30.0
```

### 3. JWT Authentication (x-google-issuer)

GCP API Gateway validiert JWT Tokens automatisch:

```yaml
securityDefinitions:
  google_jwt:
    authorizationUrl: ""
    flow: "implicit"
    type: "oauth2"
    x-google-issuer: "https://accounts.google.com"
    x-google-jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    x-google-audiences: "https://my-project.example.com"

security:
  - google_jwt: []
```

**JWT Token Format:**

```bash
# Google Sign-In Token
curl "https://GATEWAY_URL/api/users" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 4. Service Account Backend Auth

Für Cloud Run / Cloud Functions Backends:

```yaml
x-google-backend:
  address: "https://my-service-abc123-uc.a.run.app"
  jwt_audience: "https://my-service-abc123-uc.a.run.app"
```

API Gateway fügt automatisch Service Account JWT Token hinzu.

### 4. Traffic Splitting & Canary Deployments

**Feature:** Gewichtsbasierte Traffic-Verteilung für A/B Testing, Canary Deployments und Blue/Green Deployments.

**Status:** ⚠️ **Eingeschränkt unterstützt** (GCP API Gateway native Limitierungen)

GCP API Gateway unterstützt Traffic Splitting **nicht nativ** in der OpenAPI Spec. Workarounds:

#### Workaround 1: Cloud Load Balancer mit Traffic Splitting

GCP Cloud Load Balancer unterstützt **gewichtsbasiertes Traffic Splitting** vor API Gateway:

**Architektur:**
```
Client
  ↓
Cloud Load Balancer (Traffic Split)
  ├─ 90% → API Gateway 1 (Stable) → Cloud Run Revision 1
  └─ 10% → API Gateway 2 (Canary) → Cloud Run Revision 2
```

**Terraform Config:**
```hcl
resource "google_compute_url_map" "api_urlmap" {
  name = "api-urlmap"

  default_url_redirect {
    path_redirect = "/api"
  }

  # Weighted Backend Services
  path_matcher {
    name            = "api-path-matcher"
    default_service = google_compute_backend_service.api_backends.id

    route_rules {
      priority = 1
      route_action {
        weighted_backend_services {
          backend_service = google_compute_backend_service.stable_backend.id
          weight          = 90  # 90% Stable
        }
        weighted_backend_services {
          backend_service = google_compute_backend_service.canary_backend.id
          weight          = 10  # 10% Canary
        }
      }
    }
  }
}
```

**Deployment:**
```bash
# 1. Create Load Balancer
gcloud compute url-maps create api-lb \
  --default-service=stable-backend

# 2. Add Canary Backend mit 10% Traffic
gcloud compute url-maps add-path-matcher api-lb \
  --path-matcher-name=api-matcher \
  --default-service=stable-backend \
  --backend-service-path-rules="/api/*=stable-backend:90,canary-backend:10"
```

#### Workaround 2: Cloud Run Traffic Splitting (Backend)

Nutze **Cloud Run** als Backend mit nativem Traffic Splitting:

**Strategie:**
1. Deploy neue Version als **Cloud Run Revision**
2. Konfiguriere Traffic Split zwischen Revisions
3. API Gateway routet zu Cloud Run (unverändert)

**Cloud Run Traffic Split:**
```bash
# 1. Deploy neue Revision (Canary)
gcloud run deploy api-service \
  --image gcr.io/project/api:canary \
  --no-traffic  # Kein Traffic initial

# 2. Traffic Split: 90% stable, 10% canary
gcloud run services update-traffic api-service \
  --to-revisions api-service-001=90,api-service-002=10
```

**GAL Config (Backend Traffic Split):**
```yaml
services:
  - name: api_service
    type: rest
    upstream:
      host: api-service-abc123-uc.a.run.app  # Cloud Run URL
      port: 443
      # Traffic Split erfolgt auf Cloud Run Ebene
```

#### Workaround 3: Multiple API Gateway Configs

Deploye **2 API Gateway Configs** mit unterschiedlichen Backends:

**Architektur:**
```
Client
  ↓
DNS Weighted Routing (90/10)
  ├─ 90% → api-gateway-stable.endpoints.project.cloud.goog
  └─ 10% → api-gateway-canary.endpoints.project.cloud.goog
```

**Deployment:**
```bash
# 1. Stable API Gateway
gcloud api-gateway apis create stable-api --project=PROJECT_ID

gcloud api-gateway api-configs create stable-config \
  --api=stable-api \
  --openapi-spec=stable-openapi.yaml \
  --backend-auth-service-account=sa@project.iam.gserviceaccount.com

gcloud api-gateway gateways create stable-gateway \
  --api=stable-api \
  --api-config=stable-config \
  --location=us-central1

# 2. Canary API Gateway
gcloud api-gateway apis create canary-api --project=PROJECT_ID

gcloud api-gateway api-configs create canary-config \
  --api=canary-api \
  --openapi-spec=canary-openapi.yaml \
  --backend-auth-service-account=sa@project.iam.gserviceaccount.com

gcloud api-gateway gateways create canary-gateway \
  --api=canary-api \
  --api-config=canary-config \
  --location=us-central1

# 3. Cloud DNS Weighted Routing
gcloud dns record-sets create api.example.com --type=A --ttl=300 \
  --rrdatas="STABLE_IP:90,CANARY_IP:10"
```

#### GCP API Gateway Traffic Splitting Features

| Feature | GCP API Gateway | Workaround |
|---------|----------------|------------|
| **Weight-based Splitting** | ❌ Native | ✅ Cloud Load Balancer |
| **Cloud Run Revisions** | ✅ Backend | Cloud Run Traffic Split (native) |
| **Multiple Gateways** | ⚠️ Complex | DNS Weighted Routing |
| **Header-based Routing** | ⚠️ Limited | OpenAPI `x-google-backend` per path |
| **A/B Testing** | ❌ Native | Cloud Load Balancer + Cloud Run |
| **Blue/Green** | ✅ Gateway Swap | Switch API Config (instant) |

#### Best Practices für GCP API Gateway:

**Empfohlene Strategie:**

1. **Cloud Run als Backend:**
   - ✅ Nutze Cloud Run Traffic Splitting (native, einfach)
   - ✅ API Gateway bleibt unverändert
   - ✅ Gradual Rollout: 5% → 25% → 50% → 100%
   - ✅ Instant Rollback via `gcloud run services update-traffic`

2. **Cloud Load Balancer (Enterprise):**
   - ✅ Für komplexe Traffic Routing Szenarien
   - ✅ Gewichtsbasiertes Splitting auf Gateway-Ebene
   - ❌ Höhere Kosten (zusätzlicher Load Balancer)

3. **Blue/Green via API Config:**
   - ✅ Deploye neue API Config (Blue/Green)
   - ✅ Instant Switch via `gcloud api-gateway gateways update`
   - ✅ Rollback durch vorherige Config

**Cloud Run Gradual Rollout Beispiel:**
```bash
# Phase 1: 5% Canary
gcloud run services update-traffic api-service \
  --to-revisions stable=95,canary=5

# Phase 2: 25% Canary (nach Monitoring)
gcloud run services update-traffic api-service \
  --to-revisions stable=75,canary=25

# Phase 3: 50% Canary
gcloud run services update-traffic api-service \
  --to-revisions stable=50,canary=50

# Phase 4: 100% Canary (Full Migration)
gcloud run services update-traffic api-service \
  --to-revisions canary=100

# Rollback (instant)
gcloud run services update-traffic api-service \
  --to-revisions stable=100
```

**GAL Limitation:**
⚠️ GAL kann GCP API Gateway Traffic Splitting **nicht automatisch generieren**, da:
- GCP API Gateway hat kein natives Traffic Splitting in OpenAPI 2.0
- Traffic Split muss über **Cloud Run** oder **Cloud Load Balancer** erfolgen
- Multi-Gateway Setup ist komplex und kostspielig

**Alternative:**
Für native Traffic Splitting Support nutze:
- ✅ **Envoy** (weighted_clusters)
- ✅ **Nginx** (split_clients)
- ✅ **Kong** (upstream targets with weights)
- ✅ **HAProxy** (server weights)
- ✅ **Traefik** (weighted services)
- ✅ **APISIX** (traffic-split plugin)

**Siehe auch:**
- [Traffic Splitting Guide](TRAFFIC_SPLITTING.md) - Vollständige Dokumentation
- [Cloud Run Traffic Splitting](https://cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration)
- [Cloud Load Balancing](https://cloud.google.com/load-balancing/docs/https/weighted-load-balancing)

---

## Deployment-Strategien

### Deployment-Entscheidungsbaum

Der folgende Entscheidungsbaum hilft bei der Auswahl der richtigen Deployment-Strategie:

```mermaid
flowchart TD
    Start([API Deployment Planen]) --> Q1{Backend Typ?}

    Q1 -->|Cloud Run/<br/>Cloud Functions| Q2{Authentifizierung<br/>benötigt?}
    Q1 -->|App Engine| Q3{JWT Auth<br/>nötig?}
    Q1 -->|Externes HTTP<br/>Backend| Q4{On-Premises oder<br/>Hybrid Cloud?}

    Q2 -->|Ja, JWT Client Auth| Scenario1[Szenario 1:<br/>Cloud Run + JWT Auth]
    Q2 -->|Nein| Scenario2[Szenario 2:<br/>Basic Cloud Run]

    Q3 -->|Ja, Firebase Auth| Scenario3[Szenario 3:<br/>Firebase Auth]
    Q3 -->|Nein| Scenario2

    Q4 -->|Ja| Scenario4[Szenario 4:<br/>Hybrid Cloud HTTP]
    Q4 -->|Nein| Q5{Multi-Region<br/>benötigt?}

    Q5 -->|Ja| Scenario5[Szenario 5:<br/>Multi-Region Deployment]
    Q5 -->|Nein| Scenario2

    %% Scenario 1 Details
    Scenario1 --> S1A[1. Service Account erstellen]
    S1A --> S1B[2. Cloud Run IAM Policy]
    S1B --> S1C[3. JWT Config in GAL]
    S1C --> S1D[4. API Gateway deployen<br/>mit Backend Auth]
    S1D --> S1E[Client mit JWT Token<br/>API aufrufen]

    %% Scenario 2 Details
    Scenario2 --> S2A[1. Backend deployen]
    S2A --> S2B[2. Basic GAL Config]
    S2B --> S2C[3. OpenAPI generieren]
    S2C --> S2D[4. API Gateway deployen]
    S2D --> S2E[Public API verfügbar]

    %% Scenario 3 Details
    Scenario3 --> S3A[1. Firebase Project Setup]
    S3A --> S3B[2. Firebase Auth Config]
    S3B --> S3C[3. GAL Config mit<br/>securetoken.google.com]
    S3C --> S3D[4. CORS für Web Apps]
    S3D --> S3E[Firebase Client SDK<br/>Integration]

    %% Scenario 4 Details
    Scenario4 --> S4A[1. VPN/Interconnect Setup]
    S4A --> S4B[2. Private Backend URL]
    S4B --> S4C[3. GAL Config mit<br/>HTTP Backend]
    S4C --> S4D[4. Extended Timeout<br/>konfigurieren]
    S4D --> S4E[Hybrid Cloud Bridge<br/>aktiv]

    %% Scenario 5 Details
    Scenario5 --> S5A[1. Global Load Balancer]
    S5A --> S5B[2. Multi-Region Backends]
    S5B --> S5C[3. Gateway in jeder Region<br/>deployen]
    S5C --> S5D[4. DNS-basiertes<br/>Geo-Routing]
    S5D --> S5E[Globale API<br/>verfügbar]

    %% Styling
    classDef questionStyle fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000
    classDef scenarioStyle fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px,color:#000
    classDef stepStyle fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000
    classDef finalStyle fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000

    class Q1,Q2,Q3,Q4,Q5 questionStyle
    class Scenario1,Scenario2,Scenario3,Scenario4,Scenario5 scenarioStyle
    class S1A,S1B,S1C,S1D,S2A,S2B,S2C,S2D,S3A,S3B,S3C,S3D,S4A,S4B,S4C,S4D,S5A,S5B,S5C,S5D stepStyle
    class S1E,S2E,S3E,S4E,S5E finalStyle
```

**Deployment-Strategien im Überblick:**

| Szenario | Use Case | Hauptmerkmale |
|----------|----------|---------------|
| **1. Cloud Run + JWT** | Production APIs mit User Auth | JWT Validation, Service Account Backend Auth |
| **2. Basic Cloud Run** | Einfache APIs, interne Services | Minimal Config, schnelles Setup |
| **3. Firebase Auth** | Mobile/Web Apps | Firebase Integration, CORS Support |
| **4. Hybrid Cloud** | On-Premises Integration | VPN/Interconnect, Extended Timeouts |
| **5. Multi-Region** | Globale Services | Geo-Distribution, High Availability |

### 1. Cloud Run Backend

**Szenario:** Serverless Container als Backend

```yaml
version: "1.0"
provider: gcp_apigateway

global_config:
  gcp_apigateway:
    project_id: "my-project"
    api_id: "cloudrun-api"
    region: "us-central1"

    # Cloud Run Service
    backend_address: "https://my-service-abc123-uc.a.run.app"
    backend_deadline: 60.0

    # Service Account Auth
    service_account_email: "api-gateway@my-project.iam.gserviceaccount.com"
    backend_jwt_audience: "https://my-service-abc123-uc.a.run.app"

    # JWT für Client Auth
    jwt_issuer: "https://accounts.google.com"
    jwt_jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"

services:
  - name: api_service
    type: rest
    protocol: http

    upstream:
      targets:
        - host: my-service-abc123-uc.a.run.app
          port: 443

    routes:
      - path_prefix: /api/v1
        methods:
          - GET
          - POST
          - PUT
          - DELETE
```

**Deployment:**

```bash
# 1. Cloud Run Service deployen
gcloud run deploy my-service \
  --image=gcr.io/my-project/my-service:latest \
  --region=us-central1 \
  --platform=managed \
  --no-allow-unauthenticated

# 2. GAL Config generieren
gal generate -c config.yaml -p gcp_apigateway > openapi.yaml

# 3. API Gateway deployen
gcloud api-gateway apis create cloudrun-api --project=my-project

gcloud api-gateway api-configs create cloudrun-api-config \
  --api=cloudrun-api \
  --openapi-spec=openapi.yaml \
  --backend-auth-service-account=api-gateway@my-project.iam.gserviceaccount.com \
  --project=my-project

gcloud api-gateway gateways create cloudrun-api-gateway \
  --api=cloudrun-api \
  --api-config=cloudrun-api-config \
  --location=us-central1 \
  --project=my-project
```

### 2. Firebase Authentication

**Szenario:** Mobile/Web App mit Firebase Auth

```yaml
version: "1.0"
provider: gcp_apigateway

global_config:
  gcp_apigateway:
    project_id: "my-firebase-project"
    api_id: "firebase-api"
    region: "us-central1"

    backend_address: "https://backend.example.com"

    # Firebase Auth
    jwt_issuer: "https://securetoken.google.com/my-firebase-project"
    jwt_jwks_uri: "https://www.googleapis.com/service_accounts/v1/metadata/x509/securetoken@system.gserviceaccount.com"
    jwt_audiences:
      - "my-firebase-project"

    # CORS für Web Apps
    cors_enabled: true
    cors_allow_origins:
      - "https://app.example.com"
    cors_allow_headers:
      - Content-Type
      - Authorization
      - Firebase-Instance-ID-Token

services:
  - name: api
    type: rest
    protocol: http

    upstream:
      targets:
        - host: backend.example.com
          port: 443

    routes:
      - path_prefix: /api/users
        methods:
          - GET
          - POST
          - PUT
          - DELETE
```

**Client-Code (JavaScript):**

```javascript
// Firebase Auth Token holen
const user = firebase.auth().currentUser;
const token = await user.getIdToken();

// API Gateway Request
const response = await fetch('https://GATEWAY_URL/api/users', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

### 3. Multi-Region Deployment

**Szenario:** Globale API mit Multi-Region Load Balancing

```yaml
version: "1.0"
provider: gcp_apigateway

global_config:
  gcp_apigateway:
    project_id: "global-project"
    api_id: "global-api"
    region: "us-central1"  # Primary Region

    # Global Load Balancer
    backend_address: "https://global-lb.example.com"

    jwt_issuer: "https://accounts.google.com"
    jwt_jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"

    cors_enabled: true
    cors_allow_origins:
      - "*"

services:
  - name: global_api
    type: rest
    protocol: http

    upstream:
      targets:
        - host: global-lb.example.com
          port: 443

    routes:
      - path_prefix: /api/v1
        methods:
          - GET
          - POST
          - PUT
          - DELETE
```

**Multi-Region Deployment:**

```bash
# Deploy in us-central1
gcloud api-gateway gateways create global-api-gateway-us \
  --api=global-api \
  --api-config=global-api-config \
  --location=us-central1 \
  --project=global-project

# Deploy in europe-west1
gcloud api-gateway gateways create global-api-gateway-eu \
  --api=global-api \
  --api-config=global-api-config \
  --location=europe-west1 \
  --project=global-project

# Deploy in asia-northeast1
gcloud api-gateway gateways create global-api-gateway-asia \
  --api=global-api \
  --api-config=global-api-config \
  --location=asia-northeast1 \
  --project=global-project
```

**DNS Load Balancing:**

```
global-api.example.com:
  - us.global-api.example.com → us-central1 Gateway
  - eu.global-api.example.com → europe-west1 Gateway
  - asia.global-api.example.com → asia-northeast1 Gateway
```

### 4. Hybrid Cloud (HTTP Backend)

**Szenario:** On-Premises Backend mit GCP API Gateway

```yaml
version: "1.0"
provider: gcp_apigateway

global_config:
  gcp_apigateway:
    project_id: "hybrid-project"
    api_id: "hybrid-api"
    region: "us-central1"

    # On-Prem Backend (via VPN/Interconnect)
    backend_address: "https://10.0.1.50:8080"
    backend_protocol: "https"
    backend_deadline: 60.0

    cors_enabled: true

services:
  - name: onprem_api
    type: rest
    protocol: http

    upstream:
      targets:
        - host: "10.0.1.50"
          port: 8080

    routes:
      - path_prefix: /api/legacy
        methods:
          - GET
          - POST
```

---

## Import/Export

### Export: GAL → GCP

**GAL Config in OpenAPI 2.0 exportieren:**

```bash
# Export to OpenAPI 2.0 (Swagger)
gal generate -c config.yaml -p gcp_apigateway > openapi.yaml

# Validate OpenAPI Spec
gcloud api-gateway api-configs validate \
  --openapi-spec=openapi.yaml \
  --project=my-project
```

**Generated OpenAPI 2.0:**

```yaml
swagger: "2.0"
info:
  title: "User API"
  version: "1.0.0"
  description: "User Management API"

schemes:
  - https

x-google-backend:
  address: "https://backend.example.com"
  path_translation: "APPEND_PATH_TO_ADDRESS"
  deadline: 30.0

securityDefinitions:
  google_jwt:
    authorizationUrl: ""
    flow: "implicit"
    type: "oauth2"
    x-google-issuer: "https://accounts.google.com"
    x-google-jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    x-google-audiences: "https://my-project.example.com"

paths:
  /api/users:
    get:
      summary: "Get users"
      operationId: "getUsers"
      security:
        - google_jwt: []
      responses:
        200:
          description: "Success"
    post:
      summary: "Create user"
      operationId: "createUser"
      security:
        - google_jwt: []
      responses:
        201:
          description: "Created"
    options:
      summary: "CORS preflight"
      operationId: "corsUsers"
      responses:
        200:
          description: "CORS response"
          headers:
            Access-Control-Allow-Origin:
              type: "string"
              description: "*"
            Access-Control-Allow-Methods:
              type: "string"
              description: "GET, POST, OPTIONS"
            Access-Control-Allow-Headers:
              type: "string"
              description: "Content-Type, Authorization"
            Access-Control-Max-Age:
              type: "string"
              description: "3600"
```

### Import: GCP → GAL

**Bestehende GCP API Gateway Konfiguration importieren:**

```bash
# 1. API Config exportieren (via gcloud)
gcloud api-gateway api-configs describe my-api-config \
  --api=my-api \
  --project=my-project \
  --format=json > api-config.json

# 2. OpenAPI Spec extrahieren
# (OpenAPI Spec ist in gatewayServiceAccount.openApiDocuments[0].document)

# 3. GAL Import
gal import -i openapi.yaml -p gcp_apigateway -o gal-config.yaml
```

**Importierte GAL Config:**

```yaml
version: "1.0"
provider: gal

global_config:
  gcp_apigateway:
    api_id: "my-api"
    api_display_name: "My API"
    project_id: "my-project"
    region: "us-central1"
    backend_address: "https://backend.example.com"
    backend_path_translation: "APPEND_PATH_TO_ADDRESS"
    backend_deadline: 30.0
    jwt_issuer: "https://accounts.google.com"
    jwt_jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    jwt_audiences:
      - "https://my-project.example.com"
    cors_enabled: true
    cors_allow_origins:
      - "*"

services:
  - name: imported-api
    type: rest
    protocol: https
    upstream:
      targets:
        - host: backend.example.com
          port: 443
    routes:
      - path_prefix: /api/users
        methods:
          - GET
          - POST
```

---

## Migration & Best Practices

### Migration von anderen Providern

Der folgende Ablauf zeigt den typischen Migrationsprozess von anderen Gateway-Providern zu GCP API Gateway:

```mermaid
flowchart LR
    subgraph Source["Quell-Provider"]
        AWS["AWS API Gateway<br/>(OpenAPI 3.0)"]
        Azure["Azure APIM<br/>(OpenAPI 3.0)"]
        Kong["Kong Gateway<br/>(Kong Config)"]
        Nginx["Nginx<br/>(nginx.conf)"]
    end

    subgraph GAL["GAL - Gateway Abstraction Layer"]
        Import["GAL Import<br/>gal import -i spec.yaml"]
        Config["GAL Config<br/>(Provider-agnostisch)"]
        Export["GAL Export<br/>gal generate -p gcp_apigateway"]
    end

    subgraph GCP["GCP API Gateway"]
        OpenAPI["OpenAPI 2.0<br/>(x-google-* Extensions)"]
        Validate["Validation<br/>gcloud api-configs validate"]
        Deploy["Deployment<br/>API + Config + Gateway"]
        Live["Live Gateway<br/>(Public Endpoint)"]
    end

    subgraph Migration["Migrations-Schritte"]
        M1["1. Export aus<br/>Quell-Provider"]
        M2["2. GAL Import<br/>(Auto-Conversion)"]
        M3["3. Config anpassen<br/>(GCP-spezifisch)"]
        M4["4. OpenAPI 2.0<br/>generieren"]
        M5["5. Validieren &<br/>Deployen"]
        M6["6. Testing &<br/>Cutover"]
    end

    %% Flow
    AWS --> M1
    Azure --> M1
    Kong --> M1
    Nginx --> M1

    M1 --> Import
    Import --> M2
    M2 --> Config
    Config --> M3
    M3 --> Export
    Export --> M4
    M4 --> OpenAPI
    OpenAPI --> M5
    M5 --> Validate
    Validate --> Deploy
    Deploy --> M6
    M6 --> Live

    %% Annotations
    Import -.->|Unterstützt:<br/>AWS, Azure, Kong,<br/>Nginx, OpenAPI| Config
    Config -.->|Provider-neutral:<br/>services, routes,<br/>upstream| Export
    Export -.->|Auto-generiert:<br/>x-google-backend,<br/>x-google-issuer| OpenAPI
    Validate -.->|Prüft:<br/>OpenAPI 2.0,<br/>Extensions| Deploy

    %% Styling
    classDef sourceStyle fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000
    classDef galStyle fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px,color:#000
    classDef gcpStyle fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000
    classDef stepStyle fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#000

    class AWS,Azure,Kong,Nginx sourceStyle
    class Import,Config,Export galStyle
    class OpenAPI,Validate,Deploy,Live gcpStyle
    class M1,M2,M3,M4,M5,M6 stepStyle
```

**Migrations-Checkliste:**

| Phase | Schritte | Tools | Validierung |
|-------|----------|-------|-------------|
| **1. Export** | Quell-Config extrahieren | `aws apigateway get-export`<br/>`az apim api export` | Syntax Check |
| **2. Import** | GAL Import durchführen | `gal import -i spec.yaml -p aws` | Schema Validation |
| **3. Anpassung** | GCP-spezifische Config | Edit `global_config.gcp_apigateway` | Manual Review |
| **4. Export** | OpenAPI 2.0 generieren | `gal generate -p gcp_apigateway` | OpenAPI 2.0 Syntax |
| **5. Deployment** | GCP Deployment | `gcloud api-gateway` | API Config Validation |
| **6. Testing** | Funktionstests | curl, Postman, CI/CD | Response Comparison |

#### Von AWS API Gateway

**AWS → GCP Mapping:**

| AWS | GCP | Notizen |
|-----|-----|---------|
| `x-amazon-apigateway-integration` | `x-google-backend` | Backend Config |
| Lambda Authorizer | `x-google-issuer` (JWT) | Custom Auth → JWT |
| Cognito User Pool | `x-google-issuer` (Firebase) | OAuth2 → Firebase Auth |
| API Key | API Key | Beide unterstützt |
| OpenAPI 3.0 | OpenAPI 2.0 | **Version downgrade nötig** |

**Migration Steps:**

```bash
# 1. AWS API exportieren
aws apigateway get-export \
  --rest-api-id abc123 \
  --stage-name prod \
  --export-type oas30 \
  --accepts application/yaml \
  aws-openapi.yaml

# 2. In GAL importieren
gal import -i aws-openapi.yaml -p aws_apigateway -o gal-config.yaml

# 3. Provider auf GCP ändern
# Editiere gal-config.yaml: provider: gcp_apigateway

# 4. GCP-spezifische Config hinzufügen
# Füge global_config.gcp_apigateway hinzu

# 5. GCP OpenAPI generieren
gal generate -c gal-config.yaml -p gcp_apigateway > gcp-openapi.yaml
```

#### Von Azure APIM

**Azure → GCP Mapping:**

| Azure APIM | GCP | Notizen |
|------------|-----|---------|
| Backend Service | `x-google-backend` | Backend URL |
| JWT Validation Policy | `x-google-issuer` | JWT Config |
| CORS Policy | CORS Headers | OPTIONS Methods |
| Rate Limiting | Nicht unterstützt | Use Cloud Armor |

### Best Practices

#### 1. Service Account Berechtigungen

**Minimale Berechtigungen:**

```bash
# API Gateway Service Account
gcloud projects add-iam-policy-binding my-project \
  --member="serviceAccount:api-gateway@my-project.iam.gserviceaccount.com" \
  --role="roles/apigateway.admin"

# Cloud Run Invoker (für Backend Auth)
gcloud run services add-iam-policy-binding my-service \
  --member="serviceAccount:api-gateway@my-project.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=us-central1
```

#### 2. Timeout-Konfiguration

```yaml
global_config:
  gcp_apigateway:
    # Kurze Timeouts für Read Operations
    backend_deadline: 10.0

    # Längere Timeouts für Write Operations (per-route)
    # Nutze x-google-backend auf Operation-Level
```

**Per-Operation Timeouts:**

```yaml
# In generiertem OpenAPI 2.0:
paths:
  /api/users:
    get:
      x-google-backend:
        deadline: 5.0   # Schnelle Read
    post:
      x-google-backend:
        deadline: 30.0  # Langsamere Write
```

#### 3. CORS für SPAs

```yaml
global_config:
  gcp_apigateway:
    cors_enabled: true
    cors_allow_origins:
      - "https://app.example.com"
      - "http://localhost:3000"  # Development
    cors_allow_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS
    cors_allow_headers:
      - Content-Type
      - Authorization
      - X-Requested-With
    cors_expose_headers:
      - X-Request-Id
      - X-RateLimit-Remaining
    cors_max_age: 7200  # 2 Stunden Cache
```

#### 4. JWT Audience Validation

```yaml
global_config:
  gcp_apigateway:
    jwt_issuer: "https://accounts.google.com"
    jwt_jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"

    # Spezifische Audiences
    jwt_audiences:
      - "https://my-project.example.com"      # Web App
      - "com.example.mobile.android"          # Android App
      - "com.example.mobile.ios"              # iOS App
```

#### 5. Cloud Run Backend Best Practices

```yaml
global_config:
  gcp_apigateway:
    backend_address: "https://my-service-abc123-uc.a.run.app"

    # Längerer Timeout für Cloud Run Cold Starts
    backend_deadline: 60.0

    # Service Account Auth aktivieren
    service_account_email: "api-gateway@my-project.iam.gserviceaccount.com"
    backend_jwt_audience: "https://my-service-abc123-uc.a.run.app"
```

**Cloud Run Service mit Min Instances:**

```bash
# Verhindere Cold Starts
gcloud run services update my-service \
  --min-instances=1 \
  --region=us-central1
```

#### 6. Monitoring & Logging

**Cloud Logging aktivieren:**

```bash
# API Gateway Logs anzeigen
gcloud logging read "resource.type=api AND resource.labels.service=GATEWAY_ID" \
  --limit=50 \
  --project=my-project
```

**Cloud Monitoring Metrics:**

- `apigateway.googleapis.com/request_count` - Request Count
- `apigateway.googleapis.com/request_latencies` - Latenz
- `apigateway.googleapis.com/error_count` - Error Count

**Alert erstellen:**

```bash
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="API Gateway High Error Rate" \
  --condition-display-name="Error Rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --metric-type="apigateway.googleapis.com/error_count"
```

---

## Troubleshooting

### Häufige Probleme

#### 1. 503 Service Unavailable

**Problem:** Gateway antwortet mit 503

**Ursachen:**
- Backend Service nicht erreichbar
- Backend Timeout überschritten
- Service Account hat keine Berechtigung

**Lösung:**

```bash
# Backend Erreichbarkeit prüfen
curl -I https://backend.example.com/api/health

# Timeout erhöhen
backend_deadline: 60.0

# Service Account Berechtigung prüfen
gcloud run services get-iam-policy my-service \
  --region=us-central1 \
  --project=my-project
```

#### 2. 401 Unauthorized (JWT)

**Problem:** JWT Token wird abgelehnt

**Ursachen:**
- Falscher Issuer
- JWKS URI nicht erreichbar
- Token expired
- Audience mismatch

**Lösung:**

```bash
# JWT Token dekodieren und prüfen
echo "TOKEN" | cut -d. -f2 | base64 -d | jq .

# Prüfe:
# - iss (Issuer) = jwt_issuer Config
# - aud (Audience) in jwt_audiences Config
# - exp (Expiration) noch gültig
```

**Config korrigieren:**

```yaml
global_config:
  gcp_apigateway:
    # Issuer muss exakt mit Token 'iss' übereinstimmen
    jwt_issuer: "https://accounts.google.com"

    # JWKS URI muss erreichbar sein
    jwt_jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"

    # Mindestens eine Audience muss mit Token 'aud' übereinstimmen
    jwt_audiences:
      - "https://my-project.example.com"
```

#### 3. CORS Preflight Failed

**Problem:** Browser blockiert Request wegen CORS

**Ursachen:**
- CORS nicht aktiviert
- Origin nicht in `cors_allow_origins`
- OPTIONS Method fehlt

**Lösung:**

```yaml
global_config:
  gcp_apigateway:
    cors_enabled: true
    cors_allow_origins:
      - "https://app.example.com"  # WICHTIG: Exakte Origin
      - "*"  # Oder Wildcard für Development
    cors_allow_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS  # WICHTIG: OPTIONS muss enthalten sein
    cors_allow_headers:
      - Content-Type
      - Authorization
```

**Browser Console prüfen:**

```
Access to fetch at 'https://GATEWAY_URL/api/users' from origin 'https://app.example.com'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
```

#### 4. Backend Timeout

**Problem:** Request timeout nach 30 Sekunden

**Lösung:**

```yaml
global_config:
  gcp_apigateway:
    # Globaler Timeout erhöhen
    backend_deadline: 120.0  # Maximum: 120 Sekunden
```

**Per-Operation Timeout:**

Editiere generiertes `openapi.yaml`:

```yaml
paths:
  /api/long-running:
    post:
      x-google-backend:
        address: "https://backend.example.com"
        deadline: 120.0
```

#### 5. API Config Deployment Failed

**Problem:** `gcloud api-gateway api-configs create` schlägt fehl

**Fehler:**

```
ERROR: (gcloud.api-gateway.api-configs.create) INVALID_ARGUMENT:
Invalid OpenAPI spec: swagger version must be 2.0
```

**Lösung:**

```bash
# GAL generiert automatisch OpenAPI 2.0 für GCP
gal generate -c config.yaml -p gcp_apigateway > openapi.yaml

# Prüfe Version im openapi.yaml
grep "swagger:" openapi.yaml
# Sollte sein: swagger: "2.0"
```

**Andere OpenAPI Fehler:**

```bash
# OpenAPI Spec validieren
gcloud api-gateway api-configs validate \
  --openapi-spec=openapi.yaml \
  --project=my-project

# Zeigt detaillierte Fehler mit Zeilennummern
```

---

## Performance & Limits

### GCP API Gateway Limits

| Limit | Wert | Notizen |
|-------|------|---------|
| Max Request Size | 10 MB | Request Body |
| Max Response Size | 10 MB | Response Body |
| Max Timeout | 120 Sekunden | Backend Deadline |
| Max APIs pro Project | 500 | Soft Limit |
| Max Gateways pro Region | 100 | Soft Limit |
| Max API Configs pro API | 500 | Soft Limit |

**Limits erhöhen:**

```bash
# Support kontaktieren für höhere Limits
gcloud support cases create \
  --summary="API Gateway Quota Increase Request" \
  --description="Need higher limits for production workload"
```

### Performance Optimierung

#### 1. Backend Latency reduzieren

```yaml
global_config:
  gcp_apigateway:
    # Cloud Run in gleicher Region deployen
    region: "us-central1"
    backend_address: "https://service-us-central1.run.app"
```

#### 2. CORS Preflight Cache

```yaml
global_config:
  gcp_apigateway:
    # Längerer CORS Cache reduziert Preflight Requests
    cors_max_age: 86400  # 24 Stunden
```

#### 3. Cloud Run Min Instances

```bash
# Verhindere Cold Starts
gcloud run services update my-service \
  --min-instances=1 \
  --max-instances=100 \
  --region=us-central1
```

#### 4. CDN für statische Responses

```bash
# Cloud CDN aktivieren (für cacheable Responses)
# Nutze Cloud Load Balancer + Cloud CDN vor API Gateway
```

---

## Kosten

### Preismodell

**GCP API Gateway Pricing (Stand 2025):**

| Komponente | Preis | Einheit |
|-----------|-------|---------|
| API Calls | $3.00 | pro 1M Calls |
| API Calls (ab 2B) | $1.50 | pro 1M Calls |
| Data Transfer (Egress) | $0.12 | pro GB (nach GCP Free Tier) |

**Beispiel-Rechnung (1M Requests/Monat):**

```
API Gateway:
- 1M API Calls: $3.00

Cloud Run Backend:
- 1M Requests: ~$0.40
- CPU: ~$2.00
- Memory: ~$1.00

Total: ~$6.40/Monat
```

### Kosten-Optimierung

1. **Request Batching:** Mehrere Requests zu einem kombinieren
2. **Caching:** Cloud CDN oder Backend Caching nutzen
3. **Minimal Responses:** Nur nötige Daten zurückgeben
4. **Compression:** gzip Compression aktivieren

---

## Security Best Practices

### 1. JWT Authentication

```yaml
global_config:
  gcp_apigateway:
    # IMMER JWT für Production APIs
    jwt_issuer: "https://accounts.google.com"
    jwt_jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    jwt_audiences:
      - "https://my-project.example.com"
```

### 2. Service Account Backend Auth

```yaml
global_config:
  gcp_apigateway:
    # Backend Auth für Cloud Run/Functions
    service_account_email: "api-gateway@my-project.iam.gserviceaccount.com"
    backend_jwt_audience: "https://backend.run.app"
```

### 3. Cloud Armor Integration

```bash
# DDoS Protection & WAF
gcloud compute security-policies create api-protection \
  --description="API Gateway Protection"

# Rate Limiting Rule
gcloud compute security-policies rules create 1000 \
  --security-policy=api-protection \
  --expression="true" \
  --action=rate-based-ban \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60
```

### 4. VPC Service Controls

```bash
# API Gateway in VPC Service Perimeter einschließen
gcloud access-context-manager perimeters create api-perimeter \
  --title="API Gateway Perimeter" \
  --resources=projects/PROJECT_NUMBER \
  --restricted-services=apigateway.googleapis.com
```

### 5. Audit Logging

```bash
# Admin Activity Logs (automatisch aktiviert)
# Data Access Logs aktivieren
gcloud logging sinks create api-audit-sink \
  bigquery.googleapis.com/projects/my-project/datasets/audit_logs \
  --log-filter='resource.type="api"'
```

---

## Beispiele

Vollständige Beispiele finden Sie in:

- `examples/gcp-apigateway-example.yaml` - 5 komplette Szenarien
- `tests/test_gcp_apigateway.py` - 9 Export-Tests
- `tests/test_import_gcp_apigateway.py` - 17 Import-Tests

### Schnell-Referenz

**Basis-Setup:**

```yaml
version: "1.0"
provider: gcp_apigateway
global_config:
  gcp_apigateway:
    project_id: "my-project"
    api_id: "my-api"
    backend_address: "https://backend.example.com"
services:
  - name: api
    type: rest
    protocol: http
    upstream:
      targets:
        - host: backend.example.com
          port: 443
    routes:
      - path_prefix: /api
        methods: [GET, POST]
```

**Mit JWT:**

```yaml
global_config:
  gcp_apigateway:
    jwt_issuer: "https://accounts.google.com"
    jwt_jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    jwt_audiences: ["https://my-project.example.com"]
```

**Mit CORS:**

```yaml
global_config:
  gcp_apigateway:
    cors_enabled: true
    cors_allow_origins: ["https://app.example.com"]
```

---

## Weiterführende Ressourcen

### GCP Dokumentation

- [API Gateway Overview](https://cloud.google.com/api-gateway/docs/overview)
- [OpenAPI Extensions](https://cloud.google.com/endpoints/docs/openapi/openapi-extensions)
- [Authentication](https://cloud.google.com/api-gateway/docs/authenticate-service-account)
- [Monitoring](https://cloud.google.com/api-gateway/docs/monitoring)

### GAL Dokumentation

- [Schnellstart](QUICKSTART.md)
- [Provider Übersicht](PROVIDERS.md)
- [Authentication Guide](AUTHENTICATION.md)
- [CORS Guide](CORS.md)

### Tools

- [gcloud CLI](https://cloud.google.com/sdk/gcloud)
- [OpenAPI Validator](https://validator.swagger.io/)
- [JWT Debugger](https://jwt.io/)

---

**Letzte Aktualisierung:** 2025-10-20
**GAL Version:** 1.4.0
**Feature Status:** ✅ Production Ready
