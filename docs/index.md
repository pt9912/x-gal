# Gateway Abstraction Layer (GAL)

**Provider-agnostisches Konfigurationssystem für API-Gateways**

GAL ermöglicht es Ihnen, API-Gateway-Konfigurationen einmal zu definieren und für verschiedene Provider (Nginx, Envoy, Kong, APISIX, Traefik, HAProxy, Azure APIM, GCP API Gateway, AWS API Gateway) zu generieren.

---

## Schnelleinstieg

```yaml title="config.yaml"
version: "1.0"
provider: envoy

services:
  - name: my_service
    type: rest
    protocol: http
    upstream:
      host: my-app
      port: 8080
    routes:
      - path_prefix: /api
```

```bash
# Für beliebigen Provider generieren
gal generate -c config.yaml -p nginx
gal generate -c config.yaml -p envoy
gal generate -c config.yaml -p kong
gal generate -c config.yaml -p apisix
gal generate -c config.yaml -p traefik
gal generate -c config.yaml -p haproxy
gal generate -c config.yaml -p azure_apim
gal generate -c config.yaml -p gcp_apigateway
gal generate -c config.yaml -p aws_apigateway
```

[Zur Schnellstart-Anleitung →](guides/QUICKSTART.md){ .md-button .md-button--primary }

---

## Hauptfeatures

<div class="grid cards" markdown>

- :material-swap-horizontal: **Provider-agnostisch**

    ---

    Keine Vendor Lock-in. Wechseln Sie zwischen Gateways ohne Config-Neuschreibung.

- :material-shield-check: **Umfangreiche Features**

    ---

    Authentication, Rate Limiting, CORS, Circuit Breaker, Health Checks und mehr.

- :material-code-braces: **Automatische Transformationen**

    ---

    Defaults, UUID-Generierung, Timestamps - alles automatisch.

- :material-docker: **Docker-Ready**

    ---

    Container-basierte Workflows mit docker-compose Integration.

- :material-robot: **CI/CD-freundlich**

    ---

    Einfache Integration in Ihre Deployment-Pipeline.

- :material-import: **Import/Export**

    ---

    Importieren Sie bestehende Provider-Configs und exportieren Sie zu GAL.

- :material-ab-testing: **A/B Testing & Traffic Splitting**

    ---

    Canary Deployments, Blue/Green, Header/Cookie-Routing - alle Provider.

- :material-content-copy: **Request Mirroring**

    ---

    Shadow Traffic für Production Testing. Sample Percentage, Custom Headers, alle Provider.

- :material-test-tube: **E2E Docker Tests**

    ---

    Runtime-Tests mit echten Gateway-Containern. 1000 Requests, ±5% Toleranz.

</div>

---

## Unterstützte Provider

| Provider | Status | Output-Format | Transformations | Import/Export | Deployment |
|----------|--------|---------------|-----------------|---------------|------------|
| [Nginx](guides/NGINX.md) | :white_check_mark: | nginx.conf | Lua/njs | :white_check_mark: / :white_check_mark: | Self-Hosted |
| [Envoy](guides/ENVOY.md) | :white_check_mark: | YAML | Lua Filters | :white_check_mark: / :white_check_mark: | Self-Hosted |
| [Kong](guides/KONG.md) | :white_check_mark: | YAML | Plugins | :white_check_mark: / :white_check_mark: | Self-Hosted |
| [APISIX](guides/APISIX.md) | :white_check_mark: | JSON/YAML | Lua Serverless | :white_check_mark: / :white_check_mark: | Self-Hosted |
| [Traefik](guides/TRAEFIK.md) | :white_check_mark: | YAML/TOML | Middleware | :white_check_mark: / :white_check_mark: | Self-Hosted |
| [HAProxy](guides/HAPROXY.md) | :white_check_mark: | haproxy.cfg | Lua | :warning: / :white_check_mark: | Self-Hosted |
| **[Azure APIM](guides/AZURE_APIM.md)** | :white_check_mark: | **ARM/JSON** | **Policy XML** | :white_check_mark: / :white_check_mark: | **Azure Cloud** |
| **[GCP API Gateway](guides/GCP_APIGATEWAY.md)** | :white_check_mark: | **OpenAPI 2.0** | **Backend** | :white_check_mark: / :white_check_mark: | **Google Cloud** |
| **[AWS API Gateway](guides/AWS_APIGATEWAY.md)** | :white_check_mark: | **OpenAPI 3.0** | **VTL** | :white_check_mark: / :white_check_mark: | **AWS Cloud** |

**Import-Hinweise:**
- **Azure APIM:** Import erfolgt über OpenAPI 3.0 Export (`az apim api export`). ARM Templates werden nicht geparst. Policies müssen manuell in GAL konfiguriert werden. Siehe [Azure APIM Import Guide](import/azure-apim.md).
- **GCP API Gateway:** Import erfolgt über OpenAPI 2.0 Export (`gcloud api-gateway api-configs describe`). Siehe [GCP Import Guide](import/gcp-apigateway.md).
- **AWS API Gateway:** Import erfolgt über OpenAPI 3.0 Export (`aws apigateway get-export`). Usage Plans müssen separat konfiguriert werden. Siehe [AWS Import Guide](import/aws-apigateway.md).

---

## Dokumentations-Navigation

### :books: Guides

Praktische Anleitungen für häufige Aufgaben:

- **[Schnellstart](guides/QUICKSTART.md)** - Installation und erste Schritte in 5 Minuten
- **[Provider-Übersicht](guides/PROVIDERS.md)** - Vergleich aller Gateway-Provider
- **Provider-spezifisch**: [Nginx](guides/NGINX.md) | [Envoy](guides/ENVOY.md) | [Kong](guides/KONG.md) | [APISIX](guides/APISIX.md) | [Traefik](guides/TRAEFIK.md) | [HAProxy](guides/HAPROXY.md) | [Azure APIM](guides/AZURE_APIM.md) | [GCP API Gateway](guides/GCP_APIGATEWAY.md) | [AWS API Gateway](guides/AWS_APIGATEWAY.md)
- **[Transformationen](guides/TRANSFORMATIONS.md)** - Request-Transformationen und Best Practices
- **[Entwicklung](guides/DEVELOPMENT.md)** - Zum Projekt beitragen

### :gear: Features

Detaillierte Feature-Dokumentation:

- **[Authentication](guides/AUTHENTICATION.md)** - JWT, API Keys, Basic Auth
- **[Rate Limiting](guides/RATE_LIMITING.md)** - Request-Limitierung
- **[CORS](guides/CORS.md)** - Cross-Origin Resource Sharing
- **[Circuit Breaker](guides/CIRCUIT_BREAKER.md)** - Fehlerbehandlung
- **[Health Checks](guides/HEALTH_CHECKS.md)** - Upstream-Monitoring
- **[Headers](guides/HEADERS.md)** - Header-Manipulation
- **[Logging & Observability](guides/LOGGING_OBSERVABILITY.md)** - Monitoring & Logging
- **[Body Transformation](guides/BODY_TRANSFORMATION.md)** - Request/Response Transformation
- **[gRPC Transformations](guides/GRPC_TRANSFORMATIONS.md)** - Protobuf-basierte gRPC Transformationen
- **[Azure API Management](guides/AZURE_APIM.md)** - Cloud-Native API Gateway für Azure
- **[Traffic Splitting](guides/TRAFFIC_SPLITTING.md)** - A/B Testing, Canary Deployments, Blue/Green
- **[Request Mirroring](guides/REQUEST_MIRRORING.md)** - Shadow Traffic, Production Testing, Sample Percentage
- **[WebSocket](guides/WEBSOCKET.md)** - WebSocket-Unterstützung
- **[Timeout & Retry](guides/TIMEOUT_RETRY.md)** - Timeout- & Retry-Strategien

### :wrench: API-Referenz

Vollständige technische Referenz:

- **[CLI-Referenz](api/CLI_REFERENCE.md)** - Alle Befehle und Optionen
- **[Konfigurationsreferenz](api/CONFIGURATION.md)** - YAML-Schema und alle Optionen

### :building_construction: Architektur

Technische Details und Design:

- **[Architektur-Übersicht](architecture/ARCHITECTURE.md)** - System-Design, Komponenten, Datenfluss

---

## Schnell-Links für verschiedene Zielgruppen

=== "Einsteiger"

    1. [Schnellstart-Guide](guides/QUICKSTART.md) - Erste Schritte
    2. [Konfigurationsbeispiele](https://github.com/pt9912/x-gal/tree/main/examples) - Vollständige Beispiele
    3. [CLI-Referenz](api/CLI_REFERENCE.md) - Befehlsübersicht

=== "Entwickler"

    1. [Entwickler-Guide](guides/DEVELOPMENT.md) - Setup und Contribution
    2. [Architektur](architecture/ARCHITECTURE.md) - System-Design
    3. [Python-API-Referenz](guides/PROVIDERS.md#python-api-referenz) - Klassen und Docstrings
    4. [Tests schreiben](guides/DEVELOPMENT.md#testing) - Test-Best-Practices

=== "DevOps"

    1. [Provider-Vergleich](guides/PROVIDERS.md#provider-vergleich) - Welcher Provider passt?
    2. [Docker-Integration](guides/QUICKSTART.md#docker-compose-integration) - Container-Deployment
    3. [CI/CD-Integration](guides/QUICKSTART.md#use-case-3-cicd-integration) - Automation

---

## Neuigkeiten

### Version 1.4.0

**Neu in v1.4.0:**

- :white_check_mark: **gRPC Transformations** - Protobuf-basierte Request/Response Transformationen
- :white_check_mark: **Cloud Provider Support** - Azure APIM, AWS API Gateway, GCP API Gateway
- :white_check_mark: **A/B Testing & Traffic Splitting** - Canary Deployments, Header/Cookie-Routing
- :white_check_mark: **Request Mirroring** - Shadow Traffic für Production Testing (9/9 Provider)
- :white_check_mark: Proto Descriptor Management (file/inline/url)
- :white_check_mark: Azure AD/AWS Cognito/GCP JWT Validation
- :white_check_mark: OpenAPI 3.0/2.0 Export für Cloud Provider
- :white_check_mark: 549+ Tests (89% Coverage)
- :white_check_mark: 5000+ Zeilen neue Dokumentation

[Zum Changelog →](https://github.com/pt9912/x-gal/blob/main/CHANGELOG.md)

### Version 1.3.0

**Features aus v1.3.0:**

- Config Import für alle 7 Provider (Nginx, Envoy, Kong, APISIX, Traefik, HAProxy, Azure APIM)
- Compatibility Checker für Provider-Migration
- Migration Assistant für automatische Provider-Wechsel
- HAProxy Config Parser

[Vollständiger Changelog →](https://github.com/pt9912/x-gal/blob/main/CHANGELOG.md)

---

## Community & Support

### Hilfe bekommen

- **GitHub Issues:** [Bug Reports & Feature Requests](https://github.com/pt9912/x-gal/issues)
- **GitHub Discussions:** [Fragen & Diskussionen](https://github.com/pt9912/x-gal/discussions)

### Beitragen

Interessiert daran beizutragen? Siehe:

- [Entwickler-Guide](guides/DEVELOPMENT.md)
- [Contribution-Checklist](guides/DEVELOPMENT.md#contribution-checklist)

### Lizenz

MIT License - siehe [LICENSE](https://github.com/pt9912/x-gal/blob/main/LICENSE)

---

**Viel Erfolg mit GAL!**
