# GAL Dokumentation

Willkommen zur umfassenden Dokumentation des Gateway Abstraction Layer (GAL).

## Schnelleinstieg

Neu bei GAL? Starten Sie hier:

- **[Schnellstart-Guide](guides/QUICKSTART.md)** - Installation und erste Schritte in 5 Minuten
- **[CLI-Referenz](api/CLI_REFERENCE.md)** - Übersicht aller verfügbaren Befehle
- **[Beispiel-Konfigurationen](../examples/)** - Vollständige Beispiele zum Ausprobieren

## Dokumentations-Übersicht

### 📚 Guides

Praktische Anleitungen für häufige Aufgaben und Use Cases:

| Guide | Beschreibung | Für wen |
|-------|--------------|---------|
| [Schnellstart](guides/QUICKSTART.md) | Installation und erste Schritte | Alle Nutzer |
| [Provider-Dokumentation](guides/PROVIDERS.md) | Details zu jedem Gateway-Provider | DevOps, Architects |
| [Transformations-Guide](guides/TRANSFORMATIONS.md) | Request-Transformationen und Best Practices | Developers, Architects |
| [Entwickler-Guide](guides/DEVELOPMENT.md) | Beitragen zum Projekt | Contributors |

### 🔧 API-Referenz

Vollständige technische Referenzdokumentation:

| Dokument | Inhalt |
|----------|--------|
| [CLI-Referenz](api/CLI_REFERENCE.md) | Alle Befehle, Optionen und Beispiele |
| [Konfigurationsreferenz](api/CONFIGURATION.md) | YAML-Schema und alle Optionen |
| [Python-API](guides/PROVIDERS.md#python-api-referenz) | Docstrings, Klassen, Methoden |

### 🏗️ Architektur

Technische Details und Design-Entscheidungen:

| Dokument | Inhalt |
|----------|--------|
| [Architektur-Übersicht](architecture/ARCHITECTURE.md) | System-Design, Komponenten, Datenfluss |

## Was ist GAL?

Gateway Abstraction Layer (GAL) ist ein provider-agnostisches Konfigurationssystem für API-Gateways:

```yaml
# Einmal definieren
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
gal-cli.py generate -c config.yaml -p envoy
gal-cli.py generate -c config.yaml -p kong
gal-cli.py generate -c config.yaml -p apisix
gal-cli.py generate -c config.yaml -p traefik
```

### Hauptfeatures

- ✅ **Provider-agnostisch** - Keine Vendor Lock-in
- ✅ **Automatische Transformationen** - Defaults, UUID, Timestamps
- ✅ **gRPC & REST** - Beide Protokolle unterstützt
- ✅ **Docker-Ready** - Container-basierte Workflows
- ✅ **CI/CD-freundlich** - Einfache Integration

## Unterstützte Provider

| Provider | Status | Output-Format | Transformations |
|----------|--------|---------------|-----------------|
| [Envoy](guides/PROVIDERS.md#envoy-proxy) | ✅ | YAML | Lua Filters |
| [Kong](guides/PROVIDERS.md#kong-api-gateway) | ✅ | YAML | Plugins |
| [APISIX](guides/PROVIDERS.md#apache-apisix) | ✅ | JSON | Lua Serverless |
| [Traefik](guides/PROVIDERS.md#traefik) | ✅ | YAML | Middleware |

## Häufig verwendete Ressourcen

### Für Einsteiger

1. [Schnellstart-Guide](guides/QUICKSTART.md) - Erste Schritte
2. [Konfigurationsbeispiele](../examples/gateway-config.yaml) - Vollständige Beispiele
3. [CLI-Referenz](api/CLI_REFERENCE.md) - Befehlsübersicht

### Für Entwickler

1. [Entwickler-Guide](guides/DEVELOPMENT.md) - Setup und Contribution
2. [Architektur](architecture/ARCHITECTURE.md) - System-Design
3. [Python-API-Referenz](guides/PROVIDERS.md#python-api-referenz) - Klassen und Docstrings
4. [Tests schreiben](guides/DEVELOPMENT.md#testing) - Test-Best-Practices

### Für DevOps

1. [Provider-Vergleich](guides/PROVIDERS.md#provider-vergleich) - Welcher Provider passt?
2. [Docker-Integration](guides/QUICKSTART.md#docker-compose-integration) - Container-Deployment
3. [CI/CD-Integration](guides/QUICKSTART.md#use-case-3-cicd-integration) - Automation

## Beispiel-Workflows

### Workflow 1: Lokale Entwicklung

```bash
# 1. Config erstellen
cat > my-config.yaml << EOF
version: "1.0"
provider: envoy
services:
  - name: api
    type: rest
    protocol: http
    upstream:
      host: localhost
      port: 3000
    routes:
      - path_prefix: /api
EOF

# 2. Validieren
gal-cli.py validate -c my-config.yaml

# 3. Generieren
gal-cli.py generate -c my-config.yaml -o envoy.yaml

# 4. Envoy starten
docker run -d -v $(pwd)/envoy.yaml:/etc/envoy/envoy.yaml \
  -p 10000:10000 envoyproxy/envoy:v1.28-latest
```

### Workflow 2: Multi-Environment

```bash
# Dev (Envoy)
gal-cli.py generate -c config.yaml -p envoy -o dev/envoy.yaml

# Staging (Kong)
gal-cli.py generate -c config.yaml -p kong -o staging/kong.yaml

# Prod (APISIX)
gal-cli.py generate -c config.yaml -p apisix -o prod/apisix.json
```

### Workflow 3: Gateway-Migration

```bash
# Aktuell: Kong
# Ziel: Envoy

# 1. GAL-Config erstellen (von Kong-Doku)
vim config.yaml

# 2. Envoy-Config generieren
gal-cli.py generate -c config.yaml -p envoy -o envoy.yaml

# 3. Parallel testen
# Kong & Envoy mit Traffic-Mirroring

# 4. Schrittweise migrieren
# 10% -> 50% -> 100% Traffic
```

## Konfigurationsbeispiele

### Einfache REST-API

```yaml
version: "1.0"
provider: kong

services:
  - name: users_api
    type: rest
    protocol: http
    upstream:
      host: users-service
      port: 8080
    routes:
      - path_prefix: /api/users
        methods: [GET, POST, PUT, DELETE]
```

### Mit Transformationen

```yaml
services:
  - name: orders_api
    type: rest
    protocol: http
    upstream:
      host: orders-service
      port: 8080
    routes:
      - path_prefix: /api/orders
        methods: [POST]
    transformation:
      enabled: true
      defaults:
        status: "pending"
        currency: "USD"
      computed_fields:
        - field: order_id
          generator: uuid
          prefix: "ord_"
        - field: created_at
          generator: timestamp
      validation:
        required_fields:
          - customer_id
          - items
```

### gRPC-Service

```yaml
services:
  - name: user_service
    type: grpc
    protocol: http2
    upstream:
      host: user-grpc
      port: 9090
    routes:
      - path_prefix: /myapp.UserService
    transformation:
      enabled: true
      computed_fields:
        - field: user_id
          generator: uuid
```

## Troubleshooting

### Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| "Provider not registered" | Unbekannter Provider | Nutze: envoy, kong, apisix, traefik |
| "Port must be specified" | port: 0 in global | Setze gültigen Port (z.B. 8080) |
| "No such file" | Config-Datei fehlt | Prüfe Pfad zur Config-Datei |
| "Invalid YAML" | Syntax-Fehler | Validiere YAML-Syntax |

Siehe [Troubleshooting-Sektion](guides/QUICKSTART.md#troubleshooting) für Details.

## Best Practices

### 1. Naming Conventions

```yaml
# Gut
services:
  - name: user_authentication_service
  - name: order_processing_service

# Schlecht
services:
  - name: UserAuth123!
  - name: srv1
```

### 2. Transformationen sinnvoll einsetzen

```yaml
transformation:
  enabled: true
  defaults:
    # Optionale Felder mit sinnvollen Defaults
    status: "draft"
    priority: 3

  computed_fields:
    # IDs immer generieren
    - field: id
      generator: uuid

  validation:
    # Kritische Business-Felder
    required_fields:
      - customer_id
      - amount
```

### 3. Environment Variables für Secrets

```yaml
# Nie Secrets hardcoden!
plugins:
  - name: auth
    config:
      secret: ${JWT_SECRET}  # Aus Environment
      api_key: ${API_KEY}
```

## Community & Contribution

### Hilfe bekommen

- **GitHub Issues:** [github.com/pt9912/x-gal/issues](https://github.com/pt9912/x-gal/issues)
- **Discussions:** [github.com/pt9912/x-gal/discussions](https://github.com/pt9912/x-gal/discussions)

### Beitragen

Interessiert daran beizutragen? Siehe:

- [Entwickler-Guide](guides/DEVELOPMENT.md)
- [Contribution-Checklist](guides/DEVELOPMENT.md#contribution-checklist)

### Lizenz

MIT License - siehe [LICENSE](../LICENSE)

## Versionshinweise

**Aktuelle Version:** 1.0.0

Siehe [CHANGELOG.md](../CHANGELOG.md) für vollständige Release-Notes.

## Weitere Ressourcen

### Externe Dokumentation

- [Envoy Dokumentation](https://www.envoyproxy.io/docs)
- [Kong Dokumentation](https://docs.konghq.com/)
- [APISIX Dokumentation](https://apisix.apache.org/docs/)
- [Traefik Dokumentation](https://doc.traefik.io/traefik/)

### Verwandte Projekte

- [Istio](https://istio.io/) - Service Mesh mit Envoy
- [KrakenD](https://www.krakend.io/) - API Gateway
- [Tyk](https://tyk.io/) - Open Source API Gateway

---

**Dokumentations-Version:** 1.0.0
**Letzte Aktualisierung:** Oktober 2025
**Sprache:** Deutsch
