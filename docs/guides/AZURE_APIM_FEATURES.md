# Azure API Management Feature-Implementierungen

**Detaillierte Implementierung aller Features für Azure APIM Provider in GAL**

**Navigation:**
- [← Zurück zur Azure APIM Übersicht](AZURE_APIM.md)
- [→ Deployment & Migration](AZURE_APIM_DEPLOYMENT.md)

## Inhaltsverzeichnis

1. [Policy-Generierung](#policy-generierung)
2. [Rate Limiting](#rate-limiting)
3. [Authentication Features](#authentication-features)
4. [Header Manipulation](#header-manipulation)
5. [Caching](#caching)
6. [OpenAPI Export](#openapi-export)
7. [Traffic Splitting & Canary](#traffic-splitting--canary)
8. [Request Mirroring](#request-mirroring)
9. [Azure-spezifische Features](#azure-spezifische-features)

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

---

## Rate Limiting

### Basic Rate Limiting Policy

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

### Product-Level Rate Limiting

Azure APIM unterstützt Rate Limiting auf Product-Ebene:

**GAL Config:**
```yaml
services:
  - name: user_api
    azure_apim:
      product_name: "Starter-Product"
      rate_limit_calls: 60000  # 1000 req/sec * 60 seconds
      rate_limit_renewal_period: 60
```

**Ergebnis:**
- Alle APIs im Product "Starter-Product" haben 1000 req/sec Limit
- Geteiltes Limit über alle APIs im Product

### Advanced Rate Limiting (Per-User)

**Policy XML:**
```xml
<rate-limit-by-key calls="1000"
                    renewal-period="60"
                    counter-key="@(context.Subscription.Id)" />
```

**Erklärung:**
- Rate Limit pro Subscription ID
- Jeder Subscriber hat eigenes Limit
- Ideal für Multi-Tenant APIs

---

## Authentication Features

### 1. JWT Validation (Azure AD)

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

### 2. Subscription Key Validation

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

### 3. Azure Managed Identity

**Policy XML (Advanced):**
```xml
<authentication-managed-identity resource="https://vault.azure.net" />
```

**Use Case:**
- Backend-Services in Azure (Key Vault, Storage, etc.)
- Kein API Key Management erforderlich
- IAM-basierte Authentifizierung

---

## Header Manipulation

### Request Headers

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    headers:
      request_add:
        X-Custom-Header: "value1"
        X-API-Version: "v1"
        X-Request-ID: "@{context.RequestId}"
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
<set-header name="X-Request-ID" exists-action="override">
    <value>@{context.RequestId}</value>
</set-header>
```

### Response Headers

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    headers:
      response_add:
        X-Powered-By: "Azure APIM"
        X-Response-Time: "@{context.Elapsed.TotalMilliseconds}ms"
```

**Generierte Policy:**
```xml
<!-- Outbound -->
<set-header name="X-Powered-By" exists-action="override">
    <value>Azure APIM</value>
</set-header>
<set-header name="X-Response-Time" exists-action="override">
    <value>@{context.Elapsed.TotalMilliseconds}ms</value>
</set-header>
```

### CORS Headers

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    cors:
      enabled: true
      allowed_origins:
        - "https://example.com"
        - "https://app.example.com"
      allowed_methods:
        - GET
        - POST
        - PUT
      allowed_headers:
        - Content-Type
        - Authorization
```

**Generierte Policy:**
```xml
<cors allow-credentials="false">
    <allowed-origins>
        <origin>https://example.com</origin>
        <origin>https://app.example.com</origin>
    </allowed-origins>
    <allowed-methods>
        <method>GET</method>
        <method>POST</method>
        <method>PUT</method>
    </allowed-methods>
    <allowed-headers>
        <header>Content-Type</header>
        <header>Authorization</header>
    </allowed-headers>
</cors>
```

---

## Caching

Azure APIM bietet Built-in Caching (Premium SKU).

### Basic Caching

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    cache:
      enabled: true
      ttl: 300  # 5 Minuten
```

**Generierte Policy:**
```xml
<!-- Inbound -->
<cache-lookup vary-by-developer="false" vary-by-developer-groups="false" />

<!-- Outbound -->
<cache-store duration="300" />
```

### Advanced Caching (Vary by Query Params)

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    cache:
      enabled: true
      ttl: 300
      vary_by_query_params:
        - id
        - page
        - limit
```

**Generierte Policy:**
```xml
<!-- Inbound -->
<cache-lookup vary-by-developer="false" vary-by-developer-groups="false">
    <vary-by-query-parameter>id</vary-by-query-parameter>
    <vary-by-query-parameter>page</vary-by-query-parameter>
    <vary-by-query-parameter>limit</vary-by-query-parameter>
</cache-lookup>

<!-- Outbound -->
<cache-store duration="300" />
```

### Cache Invalidation

**Policy XML (Advanced):**
```xml
<cache-remove-value key="@("users-" + context.Request.MatchedParameters["id"])" />
```

---

## OpenAPI Export

GAL kann OpenAPI 3.0 Specifications für Azure APIM generieren.

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

## Traffic Splitting & Canary {#traffic-splitting--canary}

**Feature:** Gewichtsbasierte Traffic-Verteilung für A/B Testing, Canary Deployments und Blue/Green Deployments.

**Status:** ⚠️ **Eingeschränkt unterstützt** (Azure APIM native Limitierungen)

Azure API Management unterstützt Traffic Splitting **nicht nativ**, aber es gibt Workarounds:

### Workaround 1: Weighted Backend Selection (Policy XML)

**GAL Config (simuliert Traffic Split):**
```yaml
services:
  - name: canary_api
    type: rest
    routes:
      - path_prefix: /api/v1
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

### Workaround 2: API Revisions (Canary)

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

# 2. Traffic Split konfigurieren (Azure Portal)
# Portal → API → Revisions → Set 10% traffic to Revision 2
```

**Limitation:**
- ⚠️ Revision-basiertes Traffic Splitting ist **manuell** (Azure Portal)
- ⚠️ GAL kann Revisions **nicht automatisch** über ARM Templates steuern

### Workaround 3: Azure Traffic Manager

Für echtes Traffic Splitting nutze **Azure Traffic Manager** vor APIM:

**Architektur:**
```
Client → Traffic Manager (90/10) → APIM Instance 1 (Stable)
                                 → APIM Instance 2 (Canary)
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

### Feature Comparison

| Feature | Azure APIM Support | Workaround |
|---------|-------------------|------------|
| **Weight-based Splitting** | ❌ Native | ✅ Policy XML Random Selection |
| **Header-based Routing** | ✅ Native | Policy XML `choose/when` |
| **Revision-based Canary** | ⚠️ Manual | Azure Portal (10-90% Split) |
| **Traffic Manager** | ✅ External | Azure Traffic Manager Weighted Routing |

**Empfehlung:**
- Für native Traffic Splitting Support nutze **Envoy**, **Nginx**, **Kong**, **APISIX**, **Traefik** oder **HAProxy**
- Für Azure APIM: Policy XML Workaround oder Azure Traffic Manager

**Siehe auch:**
- [Traffic Splitting Guide](TRAFFIC_SPLITTING.md) - Vollständige Dokumentation

---

## Request Mirroring

**Feature:** Request Mirroring (Shadowing) für Testing neuer Backends ohne Produktions-Impact.

**Status:** ⚠️ **Eingeschränkt unterstützt** (Azure APIM native Limitierungen)

Azure API Management unterstützt Request Mirroring **nicht nativ**, aber Workarounds existieren.

### Workaround 1: send-request Policy (Fire-and-Forget)

**Policy XML:**
```xml
<policies>
  <inbound>
    <base />
    <!-- Primary Backend -->
    <set-backend-service base-url="https://backend-stable.azurewebsites.net" />

    <!-- Mirror Request to Canary (Fire-and-Forget) -->
    <send-request mode="new" response-variable-name="mirror-response" timeout="10" ignore-error="true">
      <set-url>https://backend-canary.azurewebsites.net@{context.Request.Url.Path}</set-url>
      <set-method>@{context.Request.Method}</set-method>
      <set-header name="X-Mirrored-Request" exists-action="override">
        <value>true</value>
      </set-header>
      <set-body>@{context.Request.Body.As<string>(preserveContent: true)}</set-body>
    </send-request>
  </inbound>
</policies>
```

**Erklärung:**
- `send-request`: Sendet Request an Canary Backend
- `mode="new"`: Unabhängiger Request (nicht blockierend)
- `ignore-error="true"`: Fehler im Mirror Backend werden ignoriert
- `response-variable-name`: Response wird in Variable gespeichert (optional für Logging)

**Limitation:**
- ⚠️ **Kein GAL Support** (manuelles Policy XML erforderlich)
- ⚠️ **Keine Response-Validierung** (Fire-and-Forget)
- ⚠️ **Erhöhte Latenz** (zweiter HTTP Request)

### Workaround 2: Application Insights (Logging Only)

**Alternative:** Nutze Application Insights für Request Logging statt echtem Mirroring:

**Policy XML:**
```xml
<trace source="apim" severity="information">
    <message>@{
        return new {
            method = context.Request.Method,
            url = context.Request.Url.ToString(),
            headers = context.Request.Headers.Select(h => h.Key + ": " + String.Join(", ", h.Value)),
            body = context.Request.Body?.As<string>(preserveContent: true)
        }.ToString();
    }</message>
</trace>
```

### Feature Comparison

| Feature | Azure APIM Support | Workaround |
|---------|-------------------|------------|
| **Request Mirroring** | ❌ Native | ✅ send-request Policy (Fire-and-Forget) |
| **Percentage-based Mirroring** | ❌ | ⚠️ Policy XML + Random Selection |
| **Response Validation** | ❌ | ❌ Nicht möglich |

**Empfehlung:**
- Für native Request Mirroring Support nutze **Envoy**, **Nginx**, **Kong**, **APISIX** oder **Traefik**
- Für Azure APIM: `send-request` Policy (Fire-and-Forget)

**Siehe auch:**
- [Request Mirroring Guide](REQUEST_MIRRORING.md) - Vollständige Dokumentation

---

## Azure-spezifische Features

### 1. Products & Subscriptions

**Products** sind Container für APIs mit eigenen Subscription Keys und Policies.

**GAL Config:**
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

**Generiertes Product (ARM Template):**
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
    <value>{{backend-url}}</value>
</set-header>
```

**Azure CLI:**
```bash
az apim nv create \
  --resource-group gal-rg \
  --service-name gal-apim \
  --named-value-id backend-url \
  --display-name "Backend URL" \
  --value "https://backend.example.com"
```

**GAL Support:**
- ⚠️ Aktuell nicht direkt unterstützt
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

### 6. Backend Service URL

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

## Weiterführende Ressourcen

**Navigation:**
- [← Zurück zur Azure APIM Übersicht](AZURE_APIM.md)
- [→ Deployment & Migration](AZURE_APIM_DEPLOYMENT.md)

**Weitere Guides:**
- [Traffic Splitting Guide](TRAFFIC_SPLITTING.md)
- [Request Mirroring Guide](REQUEST_MIRRORING.md)
- [Authentication Guide](AUTHENTICATION.md)
- [Rate Limiting Guide](RATE_LIMITING.md)
- [Provider Comparison](PROVIDERS.md)

**Offizielle Dokumentation:**
- [Azure APIM Policy Reference](https://docs.microsoft.com/en-us/azure/api-management/api-management-policies)
- [Azure APIM ARM Templates](https://docs.microsoft.com/en-us/azure/templates/microsoft.apimanagement/)
