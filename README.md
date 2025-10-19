# Gateway Abstraction Layer (GAL) - Python Edition

[![Tests](https://github.com/pt9912/x-gal/actions/workflows/test.yml/badge.svg)](https://github.com/pt9912/x-gal/actions/workflows/test.yml)
[![Docker Build](https://github.com/pt9912/x-gal/actions/workflows/docker-build.yml/badge.svg)](https://github.com/pt9912/x-gal/actions/workflows/docker-build.yml)
[![PyPI version](https://img.shields.io/pypi/v/gal-gateway.svg)](https://pypi.org/project/gal-gateway/)
[![Python Version](https://img.shields.io/pypi/pyversions/gal-gateway.svg)](https://pypi.org/project/gal-gateway/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/gal-gateway.svg)](https://pypi.org/project/gal-gateway/)

**Gateway-Abstraktionsschicht** - Provider-agnostisches API-Gateway-Konfigurations- und Transformationssystem in Python.

Definiere deine API-Gateway-Konfiguration einmal und deploye sie auf Envoy, Kong, APISIX, Traefik, Nginx, HAProxy oder anderen Gateways - ohne Vendor Lock-in.

## Features

- ✅ **Einheitliche YAML-Konfiguration** für mehrere API-Gateway-Provider
- ✅ **Unterstützung für 6 Provider:** Envoy, Kong, APISIX, Traefik, Nginx, HAProxy
- ✅ **Automatische Payload-Transformationsgenerierung**
- ✅ **REST- und gRPC-Service-Unterstützung**
- ✅ **Default-Wert-Injektion**
- ✅ **Berechnete Felder** (UUIDs, Zeitstempel)
- ✅ **Feldvalidierung**
- ✅ **Strukturiertes Logging** mit konfigurierbaren Log-Levels
- ✅ **Reines Python** - kein Go erforderlich!
- ✅ **CI/CD Ready** - GitHub Actions Workflows integriert
- ✅ **Umfassende Tests** - 464 Tests mit 89% Coverage
- ✅ **Traffic Management** - Rate Limiting, Circuit Breaker, Health Checks & Load Balancing
- ✅ **Sicherheit** - Authentication (Basic, API Key, JWT), Header-Manipulation, CORS
- ✅ **WebSocket-Unterstützung** - Echtzeit bidirektionale Kommunikation (alle 6 Provider)
- ✅ **Body-Transformation** - Request/Response Body-Manipulation mit dynamischen Feldern
- ✅ **Timeout & Retry** - Verbindungs-/Lese-/Sende-Timeouts, automatische Wiederholungen mit exponentiellem Backoff
- ✅ **Logging & Observability** - Strukturiertes Logging (JSON), Prometheus/OpenTelemetry-Metriken, Log-Sampling, benutzerdefinierte Felder
- ✅ **Config-Import** (v1.3.0) - Importiere bestehende Envoy, Kong, APISIX, Traefik, Nginx, HAProxy Configs ins GAL-Format (`gal import-config`)
- ✅ **Compatibility Checker** (v1.3.0) - Prüfe Provider-Kompatibilität und vergleiche Feature-Unterstützung (`gal check-compatibility`, `gal compare-providers`)
- ✅ **Migration Assistant** (v1.3.0) - Interaktiver Migrations-Workflow mit Compatibility-Validierung und Migration Reports (`gal migrate`)

## Installation

### 🐳 Docker (Empfohlen)

#### Von GitHub Container Registry (Fertig)

```bash
# Latest Version ziehen
docker pull ghcr.io/pt9912/x-gal:latest

# Direkt verwenden
docker run --rm ghcr.io/pt9912/x-gal:latest list-providers

# Mit Volume für Ausgabe
docker run --rm -v $(pwd)/generated:/app/generated \
  ghcr.io/pt9912/x-gal:latest \
  generate --config examples/gateway-config.yaml --provider envoy --output generated/envoy.yaml

# Spezifische Version
docker pull ghcr.io/pt9912/x-gal:v1.0.0
```

#### Lokal bauen

```bash
# Image bauen
docker build -t gal:latest .

# Verwenden
docker run --rm gal:latest list-providers
```

### 🐍 Python (Lokal)

```bash
# Repository klonen
git clone https://github.com/pt9912/x-gal.git
cd x-gal

# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate

# Abhängigkeiten installieren
pip install -e .         # Laufzeit-Abhängigkeiten
pip install -e .[dev]    # Mit Dev-Tools (pytest, black, flake8, isort)

# CLI ausführbar machen
chmod +x gal-cli.py
```

### 📦 PyPI (Empfohlen für Produktion)

```bash
# Stabile Version von PyPI installieren
pip install gal-gateway

# CLI verwenden
gal --help
gal --version

# Mit Entwicklungs-Tools
pip install gal-gateway[dev]

# Spezifische Version
pip install gal-gateway==1.0.0

# Pre-Release von TestPyPI (optional)
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            gal-gateway
```

**PyPI-Links:**
- **Stabile Releases:** https://pypi.org/project/gal-gateway/
- **Pre-Releases (TestPyPI):** https://test.pypi.org/project/gal-gateway/
- **Dokumentation:** [PyPI Publishing Guide](docs/PYPI_PUBLISHING.md)

## Schnellstart

### 🐳 Mit Docker

```bash
# Alle Provider generieren
docker run --rm -v $(pwd)/generated:/app/generated gal:latest \
  generate-all --config examples/gateway-config.yaml --output-dir generated

# Einzelnen Provider generieren
docker run --rm -v $(pwd)/generated:/app/generated gal:latest \
  generate --config examples/gateway-config.yaml --provider kong --output generated/kong.yaml

# Mit Docker Compose
docker-compose up gal-generate  # Generiert Envoy-Konfiguration
PROVIDER=kong docker-compose up gal-generate  # Generiert Kong-Konfiguration
```

### 🐍 Mit Python

```bash
# Envoy-Konfiguration generieren
python gal-cli.py generate --config examples/gateway-config.yaml --provider envoy --output generated/envoy.yaml

# Oder das Convenience-Script verwenden
./generate-envoy.sh

# Für alle Provider generieren
python gal-cli.py generate-all --config examples/gateway-config.yaml
```

## Konfigurationsbeispiel

Das Beispiel enthält:
- **3 gRPC Services**: user_service, order_service, notification_service
- **2 REST Services**: product_service, payment_service

Jeder mit Transformationsregeln für:
- Standard-Werte
- Berechnete Felder (UUID, Zeitstempel-Generierung)
- Feldvalidierung

## Unterstützte Provider

| Provider | Status | Features |
|----------|--------|----------|
| Envoy | ✅ | Vollständige Unterstützung mit Wasm/Lua |
| Kong | ✅ | Lua Plugins |
| APISIX | ✅ | Lua Scripts |
| Traefik | ✅ | Middleware |
| Nginx | ✅ | Open Source (ngx_http-Module) |
| HAProxy | ✅ | Erweiterte Load Balancing & ACLs |

## Projektstruktur

```
x-gal/
├── gal/
│   ├── __init__.py
│   ├── config.py              # Konfigurationsmodelle
│   ├── manager.py             # Haupt-Orchestrator
│   ├── provider.py            # Provider-Interface
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── envoy.py
│   │   ├── kong.py
│   │   ├── apisix.py
│   │   ├── traefik.py
│   │   ├── nginx.py
│   │   └── haproxy.py
│   └── transformation/
│       ├── __init__.py
│       ├── engine.py
│       └── generators.py
├── gal-cli.py                 # CLI-Tool
├── examples/
│   └── gateway-config.yaml
├── tests/
└── docs/
```

## CLI-Befehle

```bash
# Konfiguration generieren
python gal-cli.py generate --config CONFIG --provider PROVIDER --output FILE

# Konfiguration validieren
python gal-cli.py validate --config CONFIG

# Für alle Provider generieren
python gal-cli.py generate-all --config CONFIG --output-dir OUTPUT

# 🚀 Provider-Config zu GAL importieren (v1.3.0)
python gal-cli.py import-config --provider envoy --input envoy.yaml --output gal-config.yaml
python gal-cli.py import-config --provider kong --input kong.yaml --output gal-config.yaml
python gal-cli.py import-config --provider apisix --input apisix.yaml --output gal-config.yaml
python gal-cli.py import-config --provider traefik --input traefik.yaml --output gal-config.yaml
python gal-cli.py import-config --provider nginx --input nginx.conf --output gal-config.yaml
python gal-cli.py import-config --provider haproxy --input haproxy.cfg --output gal-config.yaml

# 🔍 Provider-Kompatibilität prüfen (v1.3.0)
# Einzelnen Provider prüfen
python gal-cli.py check-compatibility --config gal-config.yaml --target-provider envoy

# Alle Provider vergleichen
python gal-cli.py compare-providers --config gal-config.yaml

# Mit detaillierter Ausgabe
python gal-cli.py check-compatibility --config gal-config.yaml --target-provider traefik --verbose

# 🔀 Zwischen Providern migrieren (v1.3.0)
# Interaktiver Modus (Prompts für alle Parameter)
python gal-cli.py migrate

# Nicht-interaktiver Modus
python gal-cli.py migrate \
  --source-provider kong \
  --source-config kong.yaml \
  --target-provider envoy \
  --output-dir ./migration \
  --yes

# Konfigurationsinformationen anzeigen
python gal-cli.py info --config CONFIG

# Verfügbare Provider auflisten
python gal-cli.py list-providers

# Mit Logging (für Debugging)
python gal-cli.py --log-level debug generate --config CONFIG --provider envoy

# Log Levels: debug, info, warning (default), error
python gal-cli.py --log-level info generate-all --config CONFIG
```

### Logging-Optionen

GAL unterstützt strukturiertes Logging mit verschiedenen Verbosity-Levels:

- `--log-level debug`: Detaillierte Debug-Informationen (Parsing, Validierung, Generation)
- `--log-level info`: Haupt-Operationen und Zusammenfassungen
- `--log-level warning`: Warnungen und nicht-kritische Probleme (Standard)
- `--log-level error`: Nur kritische Fehler

Beispiel:
```bash
# Debugging aktivieren
docker run --rm ghcr.io/pt9912/x-gal:latest \
  --log-level debug \
  generate --config examples/gateway-config.yaml --provider envoy
```

## 🐳 Docker Deployment

### Image bauen

```bash
# Standard-Build
docker build -t gal:latest .

# Mit spezifischer Version
docker build -t gal:1.0.0 .
```

### Docker Compose Services

```bash
# Standard CLI (interaktiv)
docker-compose up gal

# Development mit Live-Reload
docker-compose --profile dev up gal-dev

# Konfiguration generieren
docker-compose --profile generate up gal-generate

# Konfiguration validieren
CONFIG_FILE=examples/gateway-config.yaml docker-compose --profile validate up gal-validate
```

### Umgebungsvariablen

- `PROVIDER`: Gateway-Provider (envoy, kong, apisix, traefik, nginx, haproxy)
- `CONFIG_FILE`: Pfad zur Konfigurationsdatei
- `OUTPUT_DIR`: Ausgabeverzeichnis für generierte Configs

## Dokumentation

### Grundlagen
- [Schnellstart-Anleitung](docs/guides/QUICKSTART.md)
- [Architektur-Übersicht](docs/architecture/ARCHITECTURE.md)
- [Provider-Details](docs/guides/PROVIDERS.md)
- [Transformations-Anleitung](docs/guides/TRANSFORMATIONS.md)
- [Docker-Anleitung](docs/guides/DOCKER.md)

### Feature-Guides
- [Rate Limiting](docs/guides/RATE_LIMITING.md) - API-Schutz vor Überlastung
- [Authentication](docs/guides/AUTHENTICATION.md) - Basic, API Key, JWT
- [Headers](docs/guides/HEADERS.md) - Request/Response Header Manipulation
- [CORS](docs/guides/CORS.md) - Cross-Origin Resource Sharing
- [Circuit Breaker](docs/guides/CIRCUIT_BREAKER.md) - Fehlertoleranz & Resilienz
- [Health Checks & Load Balancing](docs/guides/HEALTH_CHECKS.md) - Hochverfügbarkeit
- [**WebSocket-Unterstützung**](docs/guides/WEBSOCKET.md) - Echtzeit bidirektionale Kommunikation
- [**Body-Transformation**](docs/guides/BODY_TRANSFORMATION.md) - Request/Response Body-Manipulation (Felder hinzufügen/entfernen/umbenennen, PII-Filterung)
- [**Timeout & Retry Policies**](docs/guides/TIMEOUT_RETRY.md) - Verbindungs-/Lese-/Sende-Timeouts, automatische Wiederholungen mit exponentiellem Backoff
- [**Logging & Observability**](docs/guides/LOGGING_OBSERVABILITY.md) - Strukturiertes Logging (JSON/Text), Prometheus/OpenTelemetry-Metriken, Log-Sampling, benutzerdefinierte Felder

### Provider-Guides
- [**Envoy Provider**](docs/guides/ENVOY.md) - CNCF cloud-native Proxy, Filter-Architektur, xDS API
- [**Kong Provider**](docs/guides/KONG.md) - Plugin-Ökosystem, Admin API, DB-less Modus
- [**APISIX Provider**](docs/guides/APISIX.md) - Ultra-hohe Performance, etcd-Integration, Lua-Scripting
- [**Traefik Provider**](docs/guides/TRAEFIK.md) - Auto-Discovery, Let's Encrypt, Cloud-native
- [**Nginx Provider**](docs/guides/NGINX.md) - Open Source, ngx_http-Module, OpenResty
- [**HAProxy Provider**](docs/guides/HAPROXY.md) - Erweiterte Load Balancing, ACLs, Hohe Performance

### Roadmap & Changelog
- [**Roadmap**](ROADMAP.md) - Geplante Features und Releases
- [**v1.1.0 Plan**](docs/v1.1.0-PLAN.md) - v1.1.0 Implementierungsplan (100% abgeschlossen)
- [**v1.2.0 Plan**](docs/v1.2.0-PLAN.md) - v1.2.0 Implementierungsplan (✅ 100% abgeschlossen - 6/6 Features)
- [Changelog](CHANGELOG.md)

## Tests & Entwicklung

### Tests ausführen

```bash
# Alle Tests
pytest

# Mit Coverage
pytest --cov=gal --cov-report=term-missing

# Spezifische Test-Datei
pytest tests/test_providers.py -v

# Mit Logging
pytest -v --log-cli-level=DEBUG
```

### Test-Suite

- **385 Tests** mit **89% Code-Coverage**
- Unit-Tests für alle Module
- Provider-spezifische Tests (Envoy, Kong, APISIX, Traefik, Nginx, HAProxy)
- CLI-Tests mit Click CliRunner
- End-to-End-Workflow-Tests
- Deployment-Tests (mit Mocking)
- Praxisnahe Szenario-Tests
- Feature-Tests (Rate Limiting, Auth, Headers, CORS, Circuit Breaker, Health Checks, WebSocket, Body-Transformation, Timeout & Retry, Logging & Observability)

### Code-Qualität

```bash
# Formatierung mit black
black .

# Import-Sortierung mit isort
isort .

# Linting mit flake8
flake8 .
```

## CI/CD

Das Projekt verwendet GitHub Actions für kontinuierliche Integration:

### Workflows

1. **Tests** (`.github/workflows/test.yml`)
   - Läuft auf Python 3.10, 3.11, 3.12
   - Automatische Tests bei jedem Push/PR
   - Code-Qualitätsprüfungen
   - Coverage-Berichte

2. **Docker Build** (`.github/workflows/docker-build.yml`)
   - Automatischer Build und Push zu ghcr.io
   - Multi-Plattform-Unterstützung (amd64, arm64)
   - Intelligentes Tagging (semver, branch, sha)

3. **Release** (`.github/workflows/release.yml`)
   - Automatische Releases bei Git Tags
   - Changelog-Generierung
   - Package-Erstellung
   - GitHub Release-Erstellung

### Release erstellen

```bash
# Version Tag erstellen
git tag v1.0.1
git push origin v1.0.1

# GitHub Actions erstellt automatisch:
# - GitHub Release mit Changelog
# - Docker Images auf ghcr.io
# - Distribution Packages
```

## Mitwirken

Beiträge sind willkommen! Bitte:

1. Fork das Repository
2. Erstelle einen Feature Branch (`git checkout -b feature/amazing-feature`)
3. Committe deine Änderungen (`git commit -m 'Add amazing feature'`)
4. Pushe zum Branch (`git push origin feature/amazing-feature`)
5. Öffne einen Pull Request

### Richtlinien

- Schreibe Tests für neue Features
- Befolge den bestehenden Code-Stil
- Aktualisiere die Dokumentation
- Füge Eintrag im CHANGELOG.md hinzu

## Lizenz

MIT - siehe [LICENSE](LICENSE) für Details.

## Links

- [GitHub Repository](https://github.com/pt9912/x-gal)
- [GitHub Container Registry](https://github.com/pt9912/x-gal/pkgs/container/x-gal)
- [Issues](https://github.com/pt9912/x-gal/issues)
- [Releases](https://github.com/pt9912/x-gal/releases)

## Autor

**Dietmar Burkard** - Gateway Abstraction Layer

---

⭐ Wenn dir dieses Projekt gefällt, gib ihm einen Stern auf GitHub!
