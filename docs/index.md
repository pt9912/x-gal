# Gateway Abstraction Layer (GAL)

**Provider-agnostisches Konfigurationssystem für API-Gateways**

GAL ermöglicht es Ihnen, API-Gateway-Konfigurationen einmal zu definieren und für verschiedene Provider (Nginx, Envoy, Kong, APISIX, Traefik, HAProxy, Azure APIM) zu generieren.

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
| **[Azure APIM](guides/AZURE_APIM.md)** | :white_check_mark: | **ARM/JSON** | **Policy XML** | :x: / :white_check_mark: | **Azure Cloud** |

---

## Dokumentations-Navigation

### :books: Guides

Praktische Anleitungen für häufige Aufgaben:

- **[Schnellstart](guides/QUICKSTART.md)** - Installation und erste Schritte in 5 Minuten
- **[Provider-Übersicht](guides/PROVIDERS.md)** - Vergleich aller Gateway-Provider
- **Provider-spezifisch**: [Nginx](guides/NGINX.md) | [Envoy](guides/ENVOY.md) | [Kong](guides/KONG.md) | [APISIX](guides/APISIX.md) | [Traefik](guides/TRAEFIK.md) | [HAProxy](guides/HAPROXY.md) | [Azure APIM](guides/AZURE_APIM.md)
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
- :white_check_mark: **Azure API Management** - Cloud Provider Support mit ARM Templates
- :white_check_mark: Proto Descriptor Management (file/inline/url)
- :white_check_mark: Azure AD JWT Validation & Subscription Keys
- :white_check_mark: OpenAPI 3.0 Export für APIM
- :white_check_mark: 71 neue Tests für gRPC, 29 neue Tests für Azure APIM
- :white_check_mark: 3000+ Zeilen neue Dokumentation

[Zum Changelog →](https://github.com/pt9912/x-gal/blob/main/CHANGELOG.md)

### Version 1.3.0

**Features aus v1.3.0:**

- Config Import für alle 6 Provider (Nginx, Envoy, Kong, APISIX, Traefik, HAProxy)
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
