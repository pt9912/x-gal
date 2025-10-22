# Azure API Management (APIM) Provider Anleitung

**Version:** 1.4.0
**Status:** ✅ Vollständig implementiert
**Cloud Provider:** Microsoft Azure
**Deployment:** ARM Templates, Azure CLI, Terraform, Bicep

---

## Navigation

- **[→ Features & Implementation](AZURE_APIM_FEATURES.md)** - Policy XML, Rate Limiting, JWT, Caching
- **[→ Deployment & Migration](AZURE_APIM_DEPLOYMENT.md)** - Azure CLI, Terraform, Best Practices

---

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Azure APIM Hierarchie](#azure-apim-hierarchie)
3. [Schnellstart](#schnellstart)
4. [Konfigurationsoptionen](#konfigurationsoptionen)
5. [Vergleich mit anderen Providern](#vergleich-azure-apim-vs-andere-provider)
6. [Weiterführende Ressourcen](#weiterführende-ressourcen)

---

## Übersicht

Azure API Management (APIM) ist Microsofts vollständig verwalteter API Gateway Service für Cloud-Native Anwendungen. GAL generiert Azure APIM ARM Templates und Policy XML aus einheitlicher YAML-Konfiguration.

### Warum Azure Management?

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

### Unterstützte Features

| Feature | Status | Implementierung |
|---------|--------|-----------------|
| **Load Balancing** | ✅ | Backend Pools |
| **Rate Limiting** | ✅ | Policy XML (`<rate-limit>`) |
| **Authentication** | ✅ | JWT (Azure AD), Subscription Keys, Managed Identity |
| **CORS** | ✅ | Policy XML (`<cors>`) |
| **Headers** | ✅ | Policy XML (`<set-header>`) |
| **Caching** | ✅ | Policy XML (`<cache-lookup>`, `<cache-store>`) |
| **Timeouts** | ✅ | Policy XML (`<forward-request timeout="">`) |
| **Circuit Breaker** | ⚠️ | Nicht nativ (Custom Policies) |
| **Health Checks** | ⚠️ | Indirekt via Azure Monitor |
| **gRPC** | ⚠️ | Limitiert (HTTP/2, kein Protobuf Transcoding) |
| **WebSocket** | ⚠️ | Limitiert (Premium SKU) |
| **Traffic Splitting** | ⚠️ | Policy XML Workarounds ([Details](AZURE_APIM_FEATURES.md#traffic-splitting--canary)) |
| **Request Mirroring** | ⚠️ | Policy XML `send-request` ([Details](AZURE_APIM_FEATURES.md#request-mirroring)) |

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

**Weitere Konfigurationsdetails:**
- **[Policy-Generierung](AZURE_APIM_FEATURES.md#policy-generierung)** - Rate Limiting, JWT, Headers, Caching
- **[OpenAPI Export](AZURE_APIM_FEATURES.md#openapi-export)** - OpenAPI 3.0 Spec Generation
- **[Azure-spezifische Features](AZURE_APIM_FEATURES.md#azure-spezifische-features)** - Products, Developer Portal, Named Values

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

### Weitere GAL Dokumentation

- **[→ Features & Implementation](AZURE_APIM_FEATURES.md)** - Policy XML, Rate Limiting, JWT, Caching, Traffic Splitting
- **[→ Deployment & Migration](AZURE_APIM_DEPLOYMENT.md)** - Azure CLI, Terraform, Best Practices, Troubleshooting

### Weitere Provider-Guides

- [Nginx Provider](NGINX.md) - Open-Source Reverse Proxy
- [Envoy Provider](ENVOY.md) - Cloud-Native Proxy
- [Kong Provider](KONG.md) - API Gateway Platform
- [APISIX Provider](APISIX.md) - Cloud-Native API Gateway
- [Traefik Provider](TRAEFIK.md) - Modern HTTP Reverse Proxy
- [HAProxy Provider](HAPROXY.md) - High Performance Load Balancer
- [AWS API Gateway Provider](AWS_APIGATEWAY.md) - AWS Managed Service
- [GCP API Gateway Provider](GCP_APIGATEWAY.md) - Google Cloud Managed Service

### Feature-spezifische Guides

- [Traffic Splitting Guide](TRAFFIC_SPLITTING.md) - A/B Testing, Canary Deployments
- [Request Mirroring Guide](REQUEST_MIRRORING.md) - Shadowing für Testing
- [Authentication Guide](AUTHENTICATION.md) - JWT, API Keys, OAuth2
- [Rate Limiting Guide](RATE_LIMITING.md) - Rate Limiting Strategien
- [gRPC Transformations Guide](GRPC_TRANSFORMATIONS.md) - gRPC Support
- [Provider Comparison](PROVIDERS.md) - Vollständiger Provider-Vergleich

### Offizielle Dokumentation

- **Azure APIM Docs**: https://docs.microsoft.com/en-us/azure/api-management/
- **ARM Template Reference**: https://docs.microsoft.com/en-us/azure/templates/microsoft.apimanagement/
- **Policy Reference**: https://docs.microsoft.com/en-us/azure/api-management/api-management-policies
- **Azure CLI Reference**: https://docs.microsoft.com/en-us/cli/azure/apim

### Beispiele

- [Azure APIM Example Config](https://github.com/pt9912/x-gal/blob/develop/examples/azure-apim-example.yaml)
- [Multi-Service YAML](https://github.com/pt9912/x-gal/blob/develop/examples/multi-service-example.yaml)

---

**Version:** 1.4.0
**Status:** ✅ Vollständig implementiert
**Letzte Aktualisierung:** 2025-10-22
