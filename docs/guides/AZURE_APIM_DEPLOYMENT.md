# Azure API Management Deployment & Migration

**Deployment-Strategien, Migration und Best Practices für Azure APIM Provider in GAL**

**Navigation:**
- [← Zurück zur Azure APIM Übersicht](AZURE_APIM.md)
- [← Feature-Implementierungen](AZURE_APIM_FEATURES.md)

## Inhaltsverzeichnis

1. [Deployment-Strategien](#deployment-strategien)
2. [Migration zu Azure APIM](#migration-zu-azure-apim)
3. [Best Practices](#best-practices)
4. [Troubleshooting](#troubleshooting)
5. [Beispiele](#beispiele)
6. [Weiterführende Ressourcen](#weiterführende-ressourcen)

---

## Deployment-Strategien

### 1. Azure CLI Deployment

**Vollständiger Workflow:**

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

**Deployment Status prüfen:**
```bash
# Deployment Status
az deployment group show \
  --resource-group gal-resource-group \
  --name <deployment-name>

# APIM Service Status
az apim show \
  --resource-group gal-resource-group \
  --name my-apim-service
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

output "apim_gateway_url" {
  value = azurerm_template_deployment.gal_apim.outputs["gatewayUrl"]
}
```

**Deployment:**
```bash
# 1. GAL Config → ARM Template
gal generate \
  --config azure-apim.yaml \
  --provider azure_apim \
  --output terraform/azure-apim-template.json

# 2. Terraform Deployment
cd terraform
terraform init
terraform plan
terraform apply

# 3. Gateway URL anzeigen
terraform output apim_gateway_url
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

      - name: Run Integration Tests
        run: |
          curl -f https://${{ secrets.APIM_SERVICE_NAME }}.azure-api.net/api/health
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
# 1. Revision erstellen
az apim api revision create \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --api-id user_api \
  --api-revision 2

# 2. Revision aktivieren
az apim api release create \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --api-id user_api \
  --api-revision 2 \
  --notes "New version with breaking changes"

# 3. Rollback (falls nötig)
az apim api release create \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --api-id user_api \
  --api-revision 1 \
  --notes "Rollback to v1"
```

### 6. Multi-Environment Deployment

**Strategie:**
```
Dev → Staging → Production
```

**GAL Configs:**
- `azure-apim-dev.yaml` → Dev APIM Service (Developer SKU)
- `azure-apim-staging.yaml` → Staging APIM Service (Basic SKU)
- `azure-apim-prod.yaml` → Production APIM Service (Premium SKU)

**Beispiel: Dev Config**
```yaml
global:
  azure_apim:
    resource_group: gal-dev-rg
    apim_service_name: gal-apim-dev
    location: westeurope
    sku: Developer  # Kostengünstig, kein SLA

services:
  - name: user_api
    upstream:
      targets:
        - host: backend-dev.example.com
          port: 443
    azure_apim:
      product_name: Dev-Product
      rate_limit_calls: 6000  # 100 req/sec
```

**Beispiel: Production Config**
```yaml
global:
  azure_apim:
    resource_group: gal-prod-rg
    apim_service_name: gal-apim-prod
    location: westeurope
    sku: Premium  # Multi-Region, 99.99% SLA

services:
  - name: user_api
    upstream:
      targets:
        - host: backend-prod.example.com
          port: 443
    azure_apim:
      product_name: Production-Product
      rate_limit_calls: 120000  # 2000 req/sec
```

---

## Migration zu Azure APIM

### Migration von anderen API Gateways

**Unterstützte Source Provider:**
- Kong
- Envoy
- Nginx
- HAProxy
- APISIX
- Traefik
- AWS API Gateway
- GCP API Gateway

### Migration Workflow

```bash
# 1. Existierende Config importieren (z.B. Kong)
gal import \
  --provider kong \
  --config kong.yml \
  --output gal-config.yaml

# 2. GAL Config → Azure APIM ARM Template
gal generate \
  --config gal-config.yaml \
  --provider azure_apim \
  --output azure-apim-template.json

# 3. ARM Template deployen
az deployment group create \
  --resource-group gal-resource-group \
  --template-file azure-apim-template.json
```

### Migration Checklist

**Vor der Migration:**
- [ ] Alle API Endpoints dokumentieren
- [ ] Rate Limits und Policies auflisten
- [ ] Authentication Mechanismen prüfen (JWT, API Keys)
- [ ] Backend URLs und Health Checks validieren
- [ ] Monitoring und Logging Setup planen

**Während der Migration:**
- [ ] GAL Config erstellen und testen
- [ ] ARM Template generieren und validieren
- [ ] Dev/Staging Environment deployen
- [ ] Integration Tests durchführen
- [ ] Performance Tests (Load Testing)
- [ ] Subscription Keys generieren und verteilen

**Nach der Migration:**
- [ ] DNS/Traffic auf Azure APIM umleiten
- [ ] Monitoring aktivieren (Application Insights)
- [ ] Alte Gateway parallel laufen lassen (Rollback)
- [ ] Alerts konfigurieren
- [ ] Developer Portal aktivieren

### Beispiel: Kong → Azure APIM

**Schritt 1: Kong Config analysieren**

```yaml
# Kong config (kong.yml)
services:
  - name: user-service
    url: https://backend.example.com
    routes:
      - name: users-route
        paths:
          - /api/users
        methods: [GET, POST]
    plugins:
      - name: rate-limiting
        config:
          minute: 100
      - name: jwt
        config:
          uri_param_names: ["jwt"]
```

**Schritt 2: GAL Config erstellen**

```yaml
# GAL config (gal-config.yaml)
version: "1.0"
provider: azure_apim

services:
  - name: user_service
    type: rest
    protocol: https

    upstream:
      targets:
        - host: backend.example.com
          port: 443

    routes:
      - path_prefix: /api/users
        methods: [GET, POST]

        rate_limit:
          enabled: true
          requests_per_second: 100

        authentication:
          type: jwt
          jwt_config:
            issuer: "https://login.microsoftonline.com/{tenant-id}/v2.0"
            audience: "api://user-service"

    azure_apim:
      product_name: UserService-Product
      product_subscription_required: false  # JWT statt Subscription Keys
      api_revision: "1"
```

**Schritt 3: ARM Template generieren**

```bash
gal generate \
  --config gal-config.yaml \
  --provider azure_apim \
  --output azure-apim-template.json
```

**Schritt 4: Deployment**

```bash
az deployment group create \
  --resource-group gal-resource-group \
  --template-file azure-apim-template.json
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

**SKU Features:**

| SKU | SLA | Max Units | VNet | Multi-Region | Preis/Monat |
|-----|-----|-----------|------|--------------|-------------|
| **Developer** | Kein SLA | 1 | ❌ | ❌ | ~40 EUR |
| **Consumption** | 99.95% | Auto-scale | ❌ | ❌ | Pay-per-Request |
| **Basic** | 99.95% | 2 | ❌ | ❌ | ~135 EUR |
| **Standard** | 99.95% | 4 | ✅ | ❌ | ~540 EUR |
| **Premium** | 99.99% | Unlimited | ✅ | ✅ | ~2,160 EUR |

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

**Subscription Key Rotation:**
```bash
# Primary Key regenerieren
az apim subscription regenerate-key \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --subscription-id <subscription-id> \
  --key-type primary

# Secondary Key regenerieren
az apim subscription regenerate-key \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --subscription-id <subscription-id> \
  --key-type secondary
```

### 3. Rate Limiting Strategy

**Empfohlene Werte:**

| API Tier | Requests/Second | APIM Calls | Renewal Period |
|----------|----------------|------------|----------------|
| Free | 10 | 600 | 60 |
| Starter | 100 | 6,000 | 60 |
| Professional | 500 | 30,000 | 60 |
| Enterprise | 2000 | 120,000 | 60 |

**Best Practice:**
- Niedrigere Limits in Dev/Staging (Cost Optimization)
- Höhere Limits in Production (Performance)
- Per-Subscription Rate Limiting verwenden
- Grace Period für Limit-Überschreitung (Burst)

### 4. Monitoring & Logging

**Azure Monitor Integration:**

```bash
# 1. Application Insights erstellen
az monitor app-insights component create \
  --app gal-apim-insights \
  --location westeurope \
  --resource-group gal-resource-group

# 2. APIM mit Application Insights verbinden
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

// Top 10 langsame Requests
ApiManagementGatewayLogs
| where TimeGenerated > ago(1h)
| extend Duration = ResponseTime
| top 10 by Duration desc
| project TimeGenerated, Method, Url, Duration, ResponseCode
```

**Alerts konfigurieren:**

```bash
# Alert für 5xx Errors
az monitor metrics alert create \
  --name "APIM-5xx-Errors" \
  --resource-group gal-resource-group \
  --scopes /subscriptions/.../apim-service \
  --condition "count HttpResponseCode where code >= 500 > 10" \
  --window-size 5m \
  --evaluation-frequency 1m
```

### 5. Security Hardening

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

**HTTPS Enforcement:**
```xml
<choose>
    <when condition="@(context.Request.Url.Scheme != "https")">
        <return-response>
            <set-status code="403" reason="HTTPS required" />
        </return-response>
    </when>
</choose>
```

### 6. Performance Optimization

**Caching aktivieren:**
```yaml
routes:
  - path_prefix: /api/users
    cache:
      enabled: true
      ttl: 300  # 5 Minuten
      vary_by_query_params:
        - id
```

**Connection Pooling:**
- Azure APIM nutzt automatisch Connection Pooling
- Keine manuelle Konfiguration erforderlich

**Backend Timeouts:**
```xml
<forward-request timeout="120" />
```

### 7. Cost Optimization

**Tipps:**
- Developer SKU für Dev/Test (keine Production Workloads)
- Consumption SKU für sporadische APIs (Pay-per-Request)
- Basic/Standard SKU für Production (fixe Kosten)
- Premium SKU nur für Multi-Region oder Enterprise

**Cost Estimation:**
```bash
# Azure Pricing Calculator
https://azure.microsoft.com/en-us/pricing/calculator/

# Consumption SKU Pricing
# - First 1M calls: Free
# - Next 1-10M calls: $3.50 per million
# - Over 10M calls: $0.70 per million
```

---

## Troubleshooting

### Problem: ARM Template Deployment schlägt fehl

**Diagnose:**
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
- Fehlende Permissions (RBAC)

**Lösung:**
```bash
# APIM Service Name verfügbar?
az apim check-name --name <your-apim-name>

# Quota Limits prüfen
az vm list-usage --location westeurope
```

### Problem: Subscription Keys funktionieren nicht

**Diagnose:**
```bash
# Subscription Keys anzeigen
az apim subscription show \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --subscription-id <subscription-id>

# Test mit cURL
curl -H "Ocp-Apim-Subscription-Key: <your-key>" \
  https://my-apim-service.azure-api.net/api/users
```

**Lösung:**
```bash
# Subscription Key regenerieren
az apim subscription regenerate-key \
  --resource-group gal-resource-group \
  --service-name my-apim-service \
  --subscription-id <subscription-id> \
  --key-type primary
```

### Problem: JWT Validation schlägt fehl

**Diagnose:**
```bash
# OIDC Discovery Document prüfen
curl https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration

# Token Claims anzeigen (mit jwt-cli)
jwt decode <your-token>
```

**Häufige Fehler:**
- Falscher Issuer (tenant-id)
- Falsche Audience
- Required Claims fehlen im Token
- Token abgelaufen (exp)

**Lösung:**
- Issuer und Audience in Policy XML prüfen
- Token mit korrekten Claims neu generieren
- Clock Skew prüfen (Token exp vs. Server Zeit)

### Problem: Rate Limiting greift nicht

**Diagnose:**
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
- Testen mit Rate Limit Test:

```bash
# 100 Requests in 10 Sekunden
for i in {1..100}; do
  curl -H "Ocp-Apim-Subscription-Key: <key>" \
    https://my-apim-service.azure-api.net/api/users &
done
wait

# Erwartete Response: 429 Too Many Requests
```

### Problem: Backend Connection Timeout

**Diagnose:**
```bash
# Backend Erreichbarkeit testen
curl -v https://backend.example.com:443/api/users

# APIM Logs prüfen (Application Insights)
az monitor app-insights query \
  --app gal-apim-insights \
  --analytics-query "traces | where message contains 'timeout'"
```

**Lösungen:**
- Backend URL prüfen (HTTP vs HTTPS)
- Firewall Rules für APIM IP-Range
- VNet Integration prüfen (Premium SKU)
- Backend Timeout erhöhen (Policy: `<forward-request timeout="120" />`)

**APIM Outbound IPs finden:**
```bash
az apim show \
  --resource-group gal-resource-group \
  --name my-apim-service \
  --query "publicIPAddresses" \
  --output table
```

### Problem: CORS Errors

**Diagnose:**
```bash
# Browser Console:
# "Access to XMLHttpRequest has been blocked by CORS policy"
```

**Lösung:**
```xml
<!-- APIM Policy (Inbound) -->
<cors allow-credentials="true">
    <allowed-origins>
        <origin>https://example.com</origin>
        <origin>https://app.example.com</origin>
    </allowed-origins>
    <allowed-methods>
        <method>GET</method>
        <method>POST</method>
        <method>PUT</method>
        <method>DELETE</method>
        <method>OPTIONS</method>
    </allowed-methods>
    <allowed-headers>
        <header>Content-Type</header>
        <header>Authorization</header>
        <header>Ocp-Apim-Subscription-Key</header>
    </allowed-headers>
</cors>
```

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
      product_subscription_required: true
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

## Weiterführende Ressourcen

### Offizielle Dokumentation

- **Azure APIM Docs**: https://docs.microsoft.com/en-us/azure/api-management/
- **ARM Template Reference**: https://docs.microsoft.com/en-us/azure/templates/microsoft.apimanagement/
- **Policy Reference**: https://docs.microsoft.com/en-us/azure/api-management/api-management-policies
- **Azure CLI Reference**: https://docs.microsoft.com/en-us/cli/azure/apim

### GAL Guides

- [← Zurück zur Azure APIM Übersicht](AZURE_APIM.md)
- [← Feature-Implementierungen](AZURE_APIM_FEATURES.md)
- [Quickstart Guide](QUICKSTART.md)
- [Authentication Guide](AUTHENTICATION.md)
- [Rate Limiting Guide](RATE_LIMITING.md)
- [Provider Comparison](PROVIDERS.md)

### Beispiele

- [Azure APIM Example Config](https://github.com/pt9912/x-gal/blob/develop/examples/azure-apim-example.yaml)
- [Multi-Service YAML](https://github.com/pt9912/x-gal/blob/develop/examples/multi-service-example.yaml)

---

**Version:** 1.4.0
**Status:** ✅ Vollständig implementiert
**Letzte Aktualisierung:** 2025-10-22
