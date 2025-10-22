# Azure API Management (APIM) Guide

**Version:** 1.4.0
**Status:** ✅ Vollständig implementiert
**Cloud Provider:** Microsoft Azure
**Deployment:** ARM Templates, Azure CLI, Terraform, Bicep

---

## Übersicht

Azure API Management (APIM) ist Microsofts vollständig verwalteter API Gateway Service für Cloud-Native Anwendungen. GAL generiert Azure APIM ARM Templates und Policy XML aus einheitlicher YAML-Konfiguration.

### Warum Azure API Management?

**Vorteile:**
- ✅ **Fully Managed**: Keine Server-Wartung erforderlich
- ✅ **Azure Integration**: Native Integration mit Azure AD, Key Vault, App Services, Application Insights
- ✅ **Developer Portal**: Automatisch generierte API-Dokumentation und Subscription Management
- ✅ **Subscription Keys**: Built-in API Key Management mit Produkten
- ✅ **OpenAPI Support**: Import/Export von OpenAPI/Swagger Specifications
- ✅ **Multi-Region**: Global Deployment mit Azure Traffic Manager
- ✅ **Enterprise Features**: Azure AD JWT Validation, Virtual Networks, Custom Domains
- ✅ **Monitoring**: Azure Monitor, Application Insights, Log Analytics Integration

**Use Cases:**
- Azure Cloud-Native Applications
- Enterprise API Gateways (Azure Stack)
- Hybrid Cloud (On-Premises + Azure)
- API Monetization (Subscription Management)
- Developer Portals mit Self-Service API Access
- Microservices Gateway in AKS (Azure Kubernetes Service)

### Hauptmerkmale

- ✅ **ARM Template Generation**: Infrastructure-as-Code für Azure Deployments
- ✅ **Policy XML**: Rate Limiting, JWT Validation, Caching, Header Manipulation
- ✅ **Subscription Keys**: API Key Management mit Produkten
- ✅ **Azure AD Integration**: OAuth2/OIDC JWT Validation
- ✅ **OpenAPI 3.0 Export**: Automatische OpenAPI Spec Generation
- ✅ **Multi-Service Support**: Mehrere APIs und Produkte pro APIM Service
- ✅ **Backend Management**: Upstream Target Configuration

---

## Azure APIM Hierarchie

```
Azure APIM Service
  ├── Products (z.B. "Starter", "Premium", "Enterprise")
  │   ├── APIs (Logische API-Gruppen)
  │   │   ├── Operations (HTTP Endpoints)
  │   │   │   ├── Policies (Inbound, Backend, Outbound, On-Error)
  │   │   │   └── Request/Response Schemas
  │   │   └── API-Level Policies
  │   └── Product-Level Policies
  ├── Backends (Upstream Targets)
  ├── Named Values (Configuration Variables)
  ├── Subscriptions (API Keys)
  └── Users & Groups (Developer Portal)
```

**Konzepte:**

- **Products**: Container für APIs mit eigenen Subscription Keys und Policies
- **APIs**: Logische API-Gruppierung (z.B. "User API", "Payment API")
- **Operations**: Einzelne HTTP Endpoints (GET /users, POST /orders, etc.)
- **Policies**: XML-basierte Transformation und Security Rules
- **Subscriptions**: API Keys für den API-Zugriff
- **Backends**: Upstream Services (App Services, AKS, External APIs)

---

## Schnellstart

### 1. Minimal-Konfiguration

Erstelle eine einfache Azure APIM Konfiguration:

```yaml
# azure-apim-minimal.yaml
version: "1.0"
provider: azure_apim

global:
  azure_apim:
    resource_group: my-resource-group
    apim_service_name: my-apim-service
    location: westeurope
    sku: Developer  # Developer, Consumption, Basic, Standard, Premium

services:
  - name: user_api
    type: rest
    protocol: http

    upstream:
      targets:
        - host: backend.example.com
          port: 443

    routes:
      - path_prefix: /api/users
        methods: [GET, POST]

    # Azure APIM Konfiguration
    azure_apim:
      product_name: UserAPI-Product
      product_description: "User Management API"
      product_published: true
      product_subscription_required: true
      api_revision: "1"
      api_version: "v1"
      openapi_export: true
```

### 2. ARM Template generieren

```bash
# GAL Config → ARM Template
gal generate \
  --config azure-apim-minimal.yaml \
  --provider azure_apim \
  --output azure-apim-template.json
```

### 3. Azure Deployment

```bash
# Resource Group erstellen
az group create \
  --name my-resource-group \
  --location westeurope

# ARM Template deployen
az deployment group create \
  --resource-group my-resource-group \
  --template-file azure-apim-template.json
```

**Ergebnis:**
- APIM Service erstellt (my-apim-service.azure-api.net)
- User API registriert
- Product erstellt (UserAPI-Product)
- Subscription Keys generiert
- Backend konfiguriert (backend.example.com:443)

---

## Konfigurationsoptionen

### Global Config

```yaml
global:
  azure_apim:
    resource_group: string          # Azure Resource Group Name (erforderlich)
    apim_service_name: string       # APIM Service Name (erforderlich)
    location: string                # Azure Region (default: westeurope)
    sku: string                     # SKU: Developer, Consumption, Basic, Standard, Premium
```

**SKU-Optionen:**

| SKU | Use Case | SLA | Features |
|-----|----------|-----|----------|
| **Developer** | Development/Testing | No SLA | Kein Production Support, max 1 Unit |
| **Consumption** | Serverless APIs | 99.95% | Auto-scaling, Pay-per-Request |
| **Basic** | Small Production APIs | 99.95% | Max 2 Units, basic features |
| **Standard** | Production APIs | 99.95% | Max 4 Units, VNet support |
| **Premium** | Enterprise APIs | 99.99% | Multi-Region, Unlimited Units, VNet, Caching |

### Service Config

```yaml
services:
  - name: string                    # Service Name (wird zu API Name)
    type: rest                      # Service Type (rest, grpc)
    protocol: http                  # Protocol (http, https)

    upstream:
      targets:
        - host: string              # Backend Hostname
          port: int                 # Backend Port (80, 443, 8080, etc.)

      load_balancer:
        algorithm: string           # Load Balancing (round_robin, least_conn)

    routes:
      - path_prefix: string         # URL Path (z.B. /api/users)
        methods: [...]              # HTTP Methods (GET, POST, PUT, DELETE, PATCH)

        # Rate Limiting
        rate_limit:
          enabled: bool
          requests_per_second: int

        # Authentication
        authentication:
          type: string              # jwt, api_key
          jwt_config: {...}
          api_key: {...}

        # Headers
        headers:
          request_add: {...}
          response_add: {...}

        # Caching (Azure APIM)
        cache:
          enabled: bool
          ttl: int
          vary_by_query_params: [...]

    # Azure APIM Spezifisch
    azure_apim:
      product_name: string                    # Product Name (erforderlich)
      product_description: string
      product_published: bool                 # true = öffentlich im Developer Portal
      product_subscription_required: bool     # true = Subscription Keys erforderlich
      api_revision: string                    # API Revision (z.B. "1", "2")
      api_version: string                     # API Version (z.B. "v1", "v2")
      openapi_export: bool                    # OpenAPI Spec exportieren
      subscription_keys_required: bool
      rate_limit_calls: int                   # APIM Rate Limit (Calls pro renewal_period)
      rate_limit_renewal_period: int          # Period in Sekunden (default: 60)
```

---

## Policy-Generierung

Azure APIM verwendet XML-basierte Policies für Transformationen, Security und Traffic Management. GAL generiert diese Policies automatisch aus der YAML-Konfiguration.

### Policy-Struktur

```xml
<policies>
    <inbound>
        <!-- Policies für eingehende Requests -->
        <base />
        <rate-limit ... />
        <validate-jwt ... />
        <set-header ... />
        <cache-lookup ... />
        <set-backend-service ... />
    </inbound>

    <backend>
        <!-- Policies für Backend Calls -->
        <base />
    </backend>

    <outbound>
        <!-- Policies für ausgehende Responses -->
        <base />
        <set-header ... />
        <cache-store ... />
    </outbound>

    <on-error>
        <!-- Policies für Fehlerbehandlung -->
        <base />
    </on-error>
</policies>
```

### Rate Limiting Policy

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    rate_limit:
      enabled: true
      requests_per_second: 100  # 100 req/sec = 6000 calls/60 seconds
```

**Generierte Policy:**
```xml
<rate-limit calls="6000" renewal-period="60" />
```

**Optionen:**
- `calls`: Maximale Anzahl an Calls pro renewal-period
- `renewal-period`: Zeitfenster in Sekunden (default: 60)
- `increment-condition`: Bedingung für Rate Limit Increment (optional)

### JWT Validation Policy (Azure AD)

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/admin
    authentication:
      type: jwt
      jwt_config:
        issuer: "https://login.microsoftonline.com/{tenant-id}/v2.0"
        audience: "api://admin-api"
        required_claims:
          - name: "roles"
            value: "admin"
          - name: "scp"
            value: "user_impersonation"
```

**Generierte Policy:**
```xml
<validate-jwt header-name="Authorization"
              failed-validation-httpcode="401"
              failed-validation-error-message="Unauthorized">
    <openid-config url="https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration" />
    <audiences>
        <audience>api://admin-api</audience>
    </audiences>
    <required-claims>
        <claim name="roles" match="any">
            <value>admin</value>
        </claim>
        <claim name="scp" match="any">
            <value>user_impersonation</value>
        </claim>
    </required-claims>
</validate-jwt>
```

### Subscription Key Validation

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    authentication:
      type: api_key
      api_key:
        key_name: Ocp-Apim-Subscription-Key
        in_location: header
```

**Generierte Policy:**
```xml
<check-header name="Ocp-Apim-Subscription-Key"
              failed-check-httpcode="401"
              failed-check-error-message="Missing or invalid subscription key" />
```

### Header Manipulation

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    headers:
      request_add:
        X-Custom-Header: "value1"
        X-API-Version: "v1"
      response_add:
        X-Powered-By: "Azure APIM"
        X-Response-Time: "measured"
```

**Generierte Policy:**
```xml
<!-- Inbound -->
<set-header name="X-Custom-Header" exists-action="override">
    <value>value1</value>
</set-header>
<set-header name="X-API-Version" exists-action="override">
    <value>v1</value>
</set-header>

<!-- Outbound -->
<set-header name="X-Powered-By" exists-action="override">
    <value>Azure APIM</value>
</set-header>
<set-header name="X-Response-Time" exists-action="override">
    <value>measured</value>
</set-header>
```

### Backend Service URL

**GAL Config:**
```yaml
upstream:
  targets:
    - host: backend.example.com
      port: 443
```

**Generierte Policy:**
```xml
<set-backend-service base-url="https://backend.example.com:443" />
```

**Auto-Detection:**
- Port 443 oder 8443 → `https://`
- Andere Ports → `http://`

---

## OpenAPI Export

GAL kann OpenAPI 3.0 Specifications für Azure APIM generieren, die direkt in APIM importiert werden können.

### OpenAPI generieren

```bash
# OpenAPI Spec generieren
gal generate \
  --config azure-apim.yaml \
  --provider azure_apim \
  --format openapi \
  --output openapi.json
```

### Generierte OpenAPI Spec

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "GAL API",
    "version": "1.0.0",
    "description": "Generated by GAL - Gateway Abstraction Layer"
  },
  "servers": [
    {
      "url": "https://backend.example.com:443"
    }
  ],
  "paths": {
    "/api/users": {
      "get": {
        "summary": "GET /api/users",
        "operationId": "get_api_users",
        "security": [
          {
            "apiKey": []
          }
        ],
        "responses": {
          "200": {
            "description": "Successful response"
          },
          "401": {
            "description": "Unauthorized"
          }
        }
      },
      "post": {
        "summary": "POST /api/users",
        "operationId": "post_api_users",
        "security": [
          {
            "apiKey": []
          }
        ],
        "responses": {
          "200": {
            "description": "Successful response"
          },
          "401": {
            "description": "Unauthorized"
          }
        }
      }
    }
  },
  "components": {
    "securitySchemes": {
      "apiKey": {
        "type": "apiKey",
        "name": "Ocp-Apim-Subscription-Key",
        "in": "header"
      },
      "oauth2": {
        "type": "oauth2",
        "flows": {
          "implicit": {
            "authorizationUrl": "https://login.microsoftonline.com/{tenant-id}/v2.0",
            "scopes": {}
          }
        }
      }
    }
  }
}
```

### OpenAPI in APIM importieren

```bash
# Import in existierenden APIM Service
az apim api import \
  --resource-group my-resource-group \
  --service-name my-apim-service \
  --path /api \
  --specification-format OpenApi \
  --specification-path openapi.json \
  --api-id my-api
```

---

## Azure-spezifische Features

### 1. Products & Subscriptions

**Products** sind Container für APIs mit eigenen Subscription Keys und Policies.

**Beispiel:**
```yaml
services:
  - name: user_api
    azure_apim:
      product_name: "Starter-Product"
      product_description: "Starter tier with 1000 req/min"
      product_published: true
      product_subscription_required: true
      rate_limit_calls: 60000  # 1000 req/sec * 60 seconds
      rate_limit_renewal_period: 60
```

**Generiertes Product:**
```json
{
  "type": "Microsoft.ApiManagement/service/products",
  "name": "[concat(parameters('apimServiceName'), '/Starter-Product')]",
  "properties": {
    "displayName": "Starter-Product",
    "description": "Starter tier with 1000 req/min",
    "subscriptionRequired": true,
    "approvalRequired": false,
    "state": "published"
  }
}
```

**Subscription Keys:**
- Primary Key: Automatisch generiert
- Secondary Key: Automatisch generiert (für Key Rotation)
- Developer Portal: Self-Service Subscription Management

### 2. Developer Portal

Der Developer Portal ist automatisch verfügbar unter:
```
https://<apim-service-name>.developer.azure-api.net
```

**Features:**
- API-Dokumentation (automatisch aus OpenAPI)
- Interactive API Testing
- Subscription Management (Self-Service)
- Code Samples (cURL, C#, Python, JavaScript, etc.)
- User Management

### 3. Azure AD Integration

**Azure AD App Registration:**

1. Azure AD App erstellen:
```bash
az ad app create \
  --display-name "My API" \
  --identifier-uris "api://my-api"
```

2. App Roles definieren (optional):
```json
{
  "appRoles": [
    {
      "allowedMemberTypes": ["User"],
      "displayName": "Admin",
      "id": "unique-guid",
      "isEnabled": true,
      "description": "Administrators",
      "value": "admin"
    }
  ]
}
```

3. GAL Config mit Azure AD JWT:
```yaml
authentication:
  type: jwt
  jwt_config:
    issuer: "https://login.microsoftonline.com/{tenant-id}/v2.0"
    audience: "api://my-api"
    required_claims:
      - name: "roles"
        value: "admin"
```

### 4. Named Values (Configuration Variables)

Named Values sind wiederverwendbare Konfigurationsvariablen (ähnlich zu Environment Variables).

**Verwendung in Policies:**
```xml
<set-header name="X-Backend-URL" exists-action="override">
    <value>@(context.Api.ServiceUrl.Host)</value>
</set-header>
```

**GAL Support:**
- Aktuell nicht direkt unterstützt
- Workaround: Manuelle Named Values nach Deployment

### 5. Virtual Networks (VNet Integration)

**Premium SKU Feature:**
- APIM in Azure VNet deployen
- Private Backend Endpoints
- ExpressRoute / VPN Connectivity

**GAL Config:**
```yaml
global:
  azure_apim:
    sku: Premium
    # VNet config via Azure Portal oder Terraform
```

### 5. Traffic Splitting & Canary Deployments

**Feature:** Gewichtsbasierte Traffic-Verteilung für A/B Testing, Canary Deployments und Blue/Green Deployments.

**Status:** ⚠️ **Eingeschränkt unterstützt** (Azure APIM native Limitierungen)

Azure API Management unterstützt Traffic Splitting **nicht nativ**, aber es gibt Workarounds:

#### Workaround 1: Multiple Backend Services mit Weighted Round Robin

Azure APIM kann über **Policy XML** mehrere Backends mit Gewichtung ansteuern.

**GAL Config (simuliert Traffic Split):**
```yaml
services:
  - name: canary_api
    type: rest
    routes:
      - path_prefix: /api/v1
        # Traffic Split via custom policy (siehe unten)
        upstream:
          targets:
            - host: backend-stable.azurewebsites.net
              port: 443
              weight: 90
            - host: backend-canary.azurewebsites.net
              port: 443
              weight: 10
```

**Azure APIM Policy (Inbound):**
```xml
<policies>
  <inbound>
    <base />
    <!-- Weighted Random Selection -->
    <set-variable name="random" value="@(new Random().Next(1, 101))" />
    <choose>
      <!-- 90% to Stable -->
      <when condition="@(context.Variables.GetValueOrDefault<int>("random") <= 90)">
        <set-backend-service base-url="https://backend-stable.azurewebsites.net" />
      </when>
      <!-- 10% to Canary -->
      <otherwise>
        <set-backend-service base-url="https://backend-canary.azurewebsites.net" />
      </otherwise>
    </choose>
  </inbound>
</policies>
```

**Erklärung:**
- `set-variable`: Generiert Zufallszahl 1-100
- `choose/when`: 1-90 → Stable Backend (90%)
- `otherwise`: 91-100 → Canary Backend (10%)
- `set-backend-service`: Dynamisches Backend-Routing

#### Workaround 2: Azure API Management Revisions

Azure APIM unterstützt **API Revisions** für Canary Deployments:

**Strategie:**
1. **Revision 1** (Current): Stable Backend
2. **Revision 2** (Non-Current): Canary Backend
3. **Traffic Split**: Via Revision Routing (10% → Revision 2)

**Azure CLI:**
```bash
# 1. Neue Revision erstellen
az apim api revision create \
  --resource-group gal-rg \
  --service-name gal-apim \
  --api-id my-api \
  --api-revision 2

# 2. Traffic Split konfigurieren (über Azure Portal)
# Portal → API → Revisions → Set 10% traffic to Revision 2
```

**Limitation:**
- ⚠️ Revision-basiertes Traffic Splitting ist **manuell** (Azure Portal)
- ⚠️ GAL kann Revisions **nicht automatisch** über ARM Templates steuern

#### Workaround 3: Azure Traffic Manager (External)

Für echtes Traffic Splitting nutze **Azure Traffic Manager** vor APIM:

**Architektur:**
```
Client
  ↓
Azure Traffic Manager (Weighted Routing)
  ├─ 90% → APIM Instance 1 (Stable Backend)
  └─ 10% → APIM Instance 2 (Canary Backend)
```

**Azure Traffic Manager Config:**
```bash
az network traffic-manager endpoint create \
  --resource-group gal-rg \
  --profile-name gal-tm-profile \
  --name stable-endpoint \
  --type azureEndpoints \
  --target-resource-id /subscriptions/.../apim-stable \
  --weight 90

az network traffic-manager endpoint create \
  --resource-group gal-rg \
  --profile-name gal-tm-profile \
  --name canary-endpoint \
  --type azureEndpoints \
  --target-resource-id /subscriptions/.../apim-canary \
  --weight 10
```

**Pros:**
- ✅ Echte gewichtsbasierte Verteilung
- ✅ DNS-basiertes Routing
- ✅ Automatisches Failover

**Cons:**
- ❌ Zusätzliche Kosten (Traffic Manager)
- ❌ Komplexere Architektur (2 APIM Instanzen)

#### Azure APIM Traffic Splitting Features

| Feature | Azure APIM Support | Workaround |
|---------|-------------------|------------|
| **Weight-based Splitting** | ❌ Native | ✅ Policy XML Random Selection |
| **Header-based Routing** | ✅ Native | Policy XML `choose/when` |
| **Revision-based Canary** | ⚠️ Manual | Azure Portal (10-90% Split) |
| **Traffic Manager** | ✅ External | Azure Traffic Manager Weighted Routing |
| **A/B Testing** | ⚠️ Limited | Policy XML + Named Values |
| **Blue/Green** | ✅ Native | Backend URL Switch in Policy |

#### Best Practices für Azure APIM:

**Empfohlene Strategie:**
1. **Klein starten:** Policy XML mit 5-10% Canary (Random Selection)
2. **Named Values:** Backend URLs als Named Values speichern
3. **Monitoring:** Application Insights für beide Backends aktivieren
4. **Gradual Rollout:** Policy XML manuell anpassen (5% → 25% → 50% → 100%)
5. **Production:** Azure Traffic Manager für echte Enterprise-Deployments

**GAL Limitation:**
⚠️ GAL kann Azure APIM Traffic Splitting **nicht automatisch generieren**, da:
- Azure APIM hat kein natives Traffic Splitting Feature
- Policy XML Random Selection muss **manuell** geschrieben werden
- Revisions sind nur über Azure Portal steuerbar

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
- [Azure Traffic Manager](https://learn.microsoft.com/en-us/azure/traffic-manager/traffic-manager-routing-methods)
- [Azure APIM Revisions](https://learn.microsoft.com/en-us/azure/api-management/api-management-revisions)

---

## Deployment-Strategien

### 1. Azure CLI Deployment

```bash
# 1. Resource Group erstellen
az group create \
  --name gal-resource-group \
  --location westeurope

# 2. GAL Config → ARM Template
gal generate \
  --config azure-apim.yaml \
  --provider azure_apim \
  --output azure-apim-template.json

# 3. ARM Template deployen
az deployment group create \
  --resource-group gal-resource-group \
  --template-file azure-apim-template.json \
  --parameters apimServiceName=my-apim-service
```

### 2. Terraform Deployment

**terraform/main.tf:**
```hcl
resource "azurerm_resource_group" "gal" {
  name     = "gal-resource-group"
  location = "West Europe"
}

resource "azurerm_template_deployment" "gal_apim" {
  name                = "gal-apim-deployment"
  resource_group_name = azurerm_resource_group.gal.name

  template_body = file("azure-apim-template.json")

  parameters = {
    apimServiceName = "my-apim-service"
  }

  deployment_mode = "Incremental"
}
```

**Deployment:**
```bash
# GAL Config → ARM Template
gal generate \
  --config azure-apim.yaml \
  --provider azure_apim \
  --output terraform/azure-apim-template.json

# Terraform Deployment
cd terraform
terraform init
terraform plan
terraform apply
```

### 3. Bicep Deployment

**Bicep** ist Microsofts DSL für ARM Templates (alternative Syntax).

**Konvertierung:**
```bash
# ARM Template → Bicep
az bicep decompile \
  --file azure-apim-template.json \
  --outfile azure-apim.bicep

# Bicep → ARM Template (optional)
az bicep build \
  --file azure-apim.bicep \
  --outfile azure-apim-template.json
```

**Deployment:**
```bash
az deployment group create \
  --resource-group gal-resource-group \
  --template-file azure-apim.bicep
```

### 4. CI/CD Integration (GitHub Actions)

**.github/workflows/deploy-apim.yml:**
```yaml
name: Deploy Azure APIM

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

      - name: Generate ARM Template
        run: |
          gal generate \
            --config azure-apim.yaml \
            --provider azure_apim \
            --output azure-apim-template.json

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy to Azure
        run: |
          az deployment group create \
            --resource-group ${{ secrets.RESOURCE_GROUP }} \
            --template-file azure-apim-template.json \
            --parameters apimServiceName=${{ secrets.APIM_SERVICE_NAME }}
```

### 5. Blue-Green Deployment

**Strategie:**
1. Neue APIM Revision erstellen
2. Traffic auf neue Revision umleiten
3. Alte Revision beibehalten (Rollback-Option)

**GAL Config:**
```yaml
services:
  - name: user_api_v2
    azure_apim:
      api_revision: "2"  # Neue Revision
      api_version: "v2"
```

**Azure CLI:**
```bash
# Revision aktivieren
az apim api release create \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --api-id user_api \
  --api-revision 2 \
  --notes "New version with breaking changes"
```

---

## Best Practices

### 1. SKU-Auswahl

| Umgebung | Empfohlene SKU | Begründung |
|----------|----------------|------------|
| Development | Developer | Kostengünstig, kein SLA, Feature-complete |
| Testing/Staging | Basic oder Consumption | SLA 99.95%, Production-like |
| Production (kleine APIs) | Standard | VNet Support, 99.95% SLA |
| Production (Enterprise) | Premium | Multi-Region, 99.99% SLA, unbegrenzte Units |

### 2. Subscription Management

**Best Practice:**
- Ein Product pro API Tier (Starter, Professional, Enterprise)
- Subscription Keys pro Environment (Dev, Staging, Production)
- Secondary Keys für Key Rotation verwenden
- Subscription Expiration Dates setzen

**Beispiel:**
```yaml
services:
  - name: user_api
    azure_apim:
      product_name: "Professional-Tier"
      product_subscription_required: true
      rate_limit_calls: 120000  # 2000 req/min
```

### 3. Rate Limiting Strategy

**Empfohlene Werte:**

| API Tier | Requests/Second | APIM Calls | Renewal Period |
|----------|----------------|------------|----------------|
| Free | 10 | 600 | 60 |
| Starter | 100 | 6,000 | 60 |
| Professional | 500 | 30,000 | 60 |
| Enterprise | 2000 | 120,000 | 60 |

### 4. Caching

Azure APIM bietet Built-in Caching (Premium SKU).

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    cache:
      enabled: true
      ttl: 300  # 5 Minuten
      vary_by_query_params:
        - id
        - page
```

**Generierte Policy:**
```xml
<!-- Inbound -->
<cache-lookup vary-by-developer="false" vary-by-developer-groups="false">
    <vary-by-query-parameter>id,page</vary-by-query-parameter>
</cache-lookup>

<!-- Outbound -->
<cache-store duration="300" />
```

### 5. Monitoring & Logging

**Azure Monitor Integration:**
```bash
# Application Insights erstellen
az monitor app-insights component create \
  --app gal-apim-insights \
  --location westeurope \
  --resource-group gal-resource-group

# APIM mit Application Insights verbinden
az apim api diagnostic create \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --api-id user_api \
  --diagnostic-id applicationinsights \
  --logger-id app-insights-logger
```

**Log Analytics Queries:**
```kusto
// Requests pro Minute
ApiManagementGatewayLogs
| where TimeGenerated > ago(1h)
| summarize RequestCount = count() by bin(TimeGenerated, 1m)
| render timechart

// 4xx/5xx Error Rate
ApiManagementGatewayLogs
| where ResponseCode >= 400
| summarize ErrorCount = count() by ResponseCode
| order by ErrorCount desc
```

### 6. Security Hardening

**Empfehlungen:**
- ✅ HTTPS only (enforce HTTPS in policies)
- ✅ Azure AD JWT Validation für interne APIs
- ✅ Subscription Keys für externe APIs
- ✅ Rate Limiting auf allen Endpoints
- ✅ IP Whitelisting (via APIM Policies)
- ✅ CORS Policies konfigurieren
- ✅ Custom Domains mit TLS 1.2+ verwenden

**IP Whitelisting Policy:**
```xml
<ip-filter action="allow">
    <address>13.66.201.169</address>
    <address-range from="13.66.140.128" to="13.66.140.143" />
</ip-filter>
```

### 7. Multi-Environment Deployment

**Strategie:**
```
Dev → Staging → Production
```

**GAL Configs:**
- `azure-apim-dev.yaml` → Dev APIM Service
- `azure-apim-staging.yaml` → Staging APIM Service
- `azure-apim-prod.yaml` → Production APIM Service (Premium SKU)

**Unterschiede:**
- Rate Limits (niedriger in Dev/Staging)
- Backend URLs (verschiedene Upstreams)
- Authentication (Test Tokens in Dev)

---

## Troubleshooting

### Problem: ARM Template Deployment schlägt fehl

**Lösung:**
```bash
# Deployment Status prüfen
az deployment group show \
  --resource-group gal-resource-group \
  --name <deployment-name>

# Deployment Logs anzeigen
az deployment operation group list \
  --resource-group gal-resource-group \
  --name <deployment-name>
```

**Häufige Fehler:**
- APIM Service Name bereits vergeben (global eindeutig)
- SKU nicht verfügbar in Region
- Quota-Limits erreicht

### Problem: Subscription Keys funktionieren nicht

**Lösung:**
```bash
# Subscription Keys anzeigen
az apim subscription show \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --subscription-id <subscription-id>

# Subscription Key regenerieren
az apim subscription regenerate-key \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --subscription-id <subscription-id> \
  --key-type primary
```

**Test:**
```bash
curl -H "Ocp-Apim-Subscription-Key: <your-key>" \
  https://my-apim-service.azure-api.net/api/users
```

### Problem: JWT Validation schlägt fehl

**Diagnose:**
```bash
# OIDC Discovery Document prüfen
curl https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration

# Token Claims anzeigen
jwt decode <your-token>
```

**Häufige Fehler:**
- Falscher Issuer (tenant-id)
- Falsche Audience
- Required Claims fehlen im Token

### Problem: Rate Limiting greift nicht

**Prüfung:**
```bash
# Policy XML anzeigen
az apim api operation policy show \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --api-id user_api \
  --operation-id get_users
```

**Lösung:**
- Policy XML validieren
- `calls` und `renewal-period` prüfen
- Eventuell Product-Level Policies prüfen

### Problem: Backend Connection Timeout

**Diagnose:**
```bash
# Backend Erreichbarkeit testen
curl -v https://backend.example.com:443/api/users

# APIM Logs prüfen
az apim api diagnostic get \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --api-id user_api \
  --diagnostic-id applicationinsights
```

**Lösungen:**
- Backend URL prüfen (HTTP vs HTTPS)
- Firewall Rules für APIM IP-Range
- VNet Integration prüfen (Premium SKU)
- Backend Timeout erhöhen (Policy: `<forward-request timeout="120" />`)

---

## Beispiele

### 1. Public API ohne Authentication

```yaml
services:
  - name: public_api
    upstream:
      targets:
        - host: public-backend.example.com
          port: 443
    routes:
      - path_prefix: /api/public
        methods: [GET]
    azure_apim:
      product_name: PublicAPI-Product
      product_subscription_required: false  # Keine Subscription Keys
      api_revision: "1"
```

### 2. API mit Subscription Keys

```yaml
services:
  - name: user_api
    upstream:
      targets:
        - host: user-backend.example.com
          port: 443
    routes:
      - path_prefix: /api/users
        methods: [GET, POST, PUT, DELETE]
        authentication:
          type: api_key
          api_key:
            key_name: Ocp-Apim-Subscription-Key
            in_location: header
        rate_limit:
          enabled: true
          requests_per_second: 100
    azure_apim:
      product_name: UserAPI-Product
      product_subscription_required: true  # Subscription Keys erforderlich
      api_revision: "1"
```

### 3. API mit Azure AD JWT

```yaml
services:
  - name: admin_api
    upstream:
      targets:
        - host: admin-backend.example.com
          port: 443
    routes:
      - path_prefix: /api/admin
        methods: [GET, POST, PUT, DELETE]
        authentication:
          type: jwt
          jwt_config:
            issuer: "https://login.microsoftonline.com/{tenant-id}/v2.0"
            audience: "api://admin-api"
            required_claims:
              - name: "roles"
                value: "admin"
    azure_apim:
      product_name: AdminAPI-Product
      product_subscription_required: false  # JWT statt Subscription Keys
      api_revision: "1"
```

### 4. Multi-Region Deployment (Premium SKU)

```yaml
global:
  azure_apim:
    sku: Premium
    location: westeurope
    # Zusätzliche Regionen via Azure Portal

services:
  - name: global_api
    upstream:
      targets:
        - host: backend-westeurope.example.com
          port: 443
    routes:
      - path_prefix: /api/global
        methods: [GET, POST]
        rate_limit:
          enabled: true
          requests_per_second: 1000
    azure_apim:
      product_name: GlobalAPI-Product
      product_subscription_required: true
      api_revision: "1"
```

### 5. API mit Custom Headers

```yaml
services:
  - name: webhook_api
    upstream:
      targets:
        - host: webhook-backend.example.com
          port: 8080
    routes:
      - path_prefix: /webhooks
        methods: [POST]
        headers:
          request_add:
            X-Webhook-Source: "Azure-APIM"
            X-Webhook-Version: "1.0"
            X-Request-ID: "generated"
          response_add:
            X-Webhook-Processed: "true"
            X-Response-Time: "measured"
    azure_apim:
      product_name: WebhookAPI-Product
      api_revision: "1"
```

---

## Vergleich: Azure APIM vs. andere Provider

| Feature | Azure APIM | Kong | Envoy | APISIX | Traefik |
|---------|-----------|------|-------|--------|---------|
| **Deployment** | Fully Managed | Self-Hosted oder Cloud | Self-Hosted | Self-Hosted oder Cloud | Self-Hosted |
| **Subscription Keys** | ✅ Built-in | ⚠️ Plugin | ❌ | ⚠️ Plugin | ❌ |
| **Azure AD JWT** | ✅ Native | ⚠️ Custom | ⚠️ Lua | ⚠️ Custom | ⚠️ Middleware |
| **Developer Portal** | ✅ Built-in | ⚠️ Custom | ❌ | ⚠️ Custom | ❌ |
| **Rate Limiting** | ✅ Built-in | ✅ | ✅ | ✅ | ✅ |
| **Caching** | ✅ Built-in | ✅ | ✅ | ✅ | ✅ |
| **OpenAPI Import** | ✅ | ⚠️ | ❌ | ⚠️ | ❌ |
| **Multi-Region** | ✅ Premium | ⚠️ Custom | ⚠️ Custom | ⚠️ Custom | ⚠️ Custom |
| **Cost** | Pay-per-SKU | Free (OSS) | Free (OSS) | Free (OSS) | Free (OSS) |

**Wann Azure APIM verwenden?**
- ✅ Azure Cloud-Native Applications
- ✅ Subscription Key Management erforderlich
- ✅ Developer Portal erforderlich
- ✅ Enterprise Support erforderlich
- ✅ Multi-Region Deployment
- ✅ Fully Managed Service bevorzugt

**Wann andere Provider verwenden?**
- ❌ Multi-Cloud (AWS, GCP) → Kong, Envoy, APISIX
- ❌ Kubernetes-Native → Kong (Ingress), Envoy (Istio), Traefik
- ❌ Self-Hosted erforderlich → Kong, Envoy, APISIX, Traefik
- ❌ Cost-Optimierung → Open-Source Provider

---

## Weiterführende Ressourcen

### Offizielle Dokumentation

- **Azure APIM Docs**: https://docs.microsoft.com/en-us/azure/api-management/
- **ARM Template Reference**: https://docs.microsoft.com/en-us/azure/templates/microsoft.apimanagement/
- **Policy Reference**: https://docs.microsoft.com/en-us/azure/api-management/api-management-policies
- **Azure CLI Reference**: https://docs.microsoft.com/en-us/cli/azure/apim

### GAL Guides

- [Quickstart Guide](QUICKSTART.md)
- [Authentication Guide](AUTHENTICATION.md)
- [Rate Limiting Guide](RATE_LIMITING.md)
- [gRPC Transformations Guide](GRPC_TRANSFORMATIONS.md)
- [Provider Comparison](PROVIDERS.md)

### Beispiele

- [Azure APIM Example Config](https://github.com/pt9912/x-gal/blob/develop/examples/azure-apim-example.yaml)
- [Multi-Service YAML](https://github.com/pt9912/x-gal/blob/develop/examples/multi-service-example.yaml)

### Community

- **GitHub**: https://github.com/your-org/x-gal
- **Issues**: https://github.com/your-org/x-gal/issues
- **Discussions**: https://github.com/your-org/x-gal/discussions

---

**Version:** 1.4.0
**Status:** ✅ Vollständig implementiert
**Letzte Aktualisierung:** 2025-10-19
