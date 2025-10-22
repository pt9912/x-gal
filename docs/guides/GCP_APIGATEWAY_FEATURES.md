# GCP API Gateway Feature-Implementierungen

**Detaillierte Implementierung aller Features für GCP API Gateway Provider in GAL**

**Navigation:**
- [← Zurück zur GCP API Gateway Übersicht](GCP_APIGATEWAY.md)
- [→ Deployment & Migration](GCP_APIGATEWAY_DEPLOYMENT.md)

## Inhaltsverzeichnis

1. [Provider-Spezifische Features](#provider-spezifische-features)
2. [Beispiele](#beispiele)

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

