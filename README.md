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
- ✅ **REST- und gRPC-Service-Unterstützung** (3 gRPC + 2 REST Services)
- ✅ **Default-Wert-Injektion**
- ✅ **Berechnete Felder** (UUIDs, Zeitstempel)
- ✅ **Feldvalidierung**
- ✅ **Strukturiertes Logging** mit konfigurierbaren Log-Levels
- ✅ **Reines Python** - kein Go erforderlich!
- ✅ **CI/CD Ready** - GitHub Actions Workflows integriert
- ✅ **Umfassende Tests** - 345 Tests mit 89% Coverage
- 🆕 **Traffic Management** - Rate Limiting, Circuit Breaker, Health Checks & Load Balancing
- 🆕 **Security** - Authentication (Basic, API Key, JWT), Header Manipulation, CORS
- 🆕 **WebSocket Support** - Real-time bidirectional communication (all 6 providers)
- 🆕 **Body Transformation** - Request/Response body manipulation with dynamic fields
- 🆕 **Timeout & Retry** - Connection/read/send timeouts, automatic retries with exponential backoff

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
pip install -e .         # Runtime dependencies
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

# Mit Development Tools
pip install gal-gateway[dev]

# Spezifische Version
pip install gal-gateway==1.0.0

# Pre-Release von TestPyPI (optional)
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            gal-gateway
```

**PyPI Links:**
- **Stable Releases:** https://pypi.org/project/gal-gateway/
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
| Nginx | ✅ | Open Source (ngx_http modules) |
| HAProxy | ✅ | Advanced Load Balancing & ACLs |

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

### Environment Variables

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
- [**WebSocket Support**](docs/guides/WEBSOCKET.md) - Real-time bidirectional communication
- [**Body Transformation**](docs/guides/BODY_TRANSFORMATION.md) - Request/Response body manipulation (add/remove/rename fields, PII filtering)
- [**Timeout & Retry Policies**](docs/guides/TIMEOUT_RETRY.md) - Connection/read/send timeouts, automatic retries with exponential backoff

### Provider-Guides
- [**Envoy Provider**](docs/guides/ENVOY.md) - CNCF cloud-native proxy, Filter-Architektur, xDS API
- [**Kong Provider**](docs/guides/KONG.md) - Plugin-Ökosystem, Admin API, DB-less mode
- [**APISIX Provider**](docs/guides/APISIX.md) - Ultra-high performance, etcd integration, Lua scripting
- [**Traefik Provider**](docs/guides/TRAEFIK.md) - Auto-discovery, Let's Encrypt, Cloud-native
- [**Nginx Provider**](docs/guides/NGINX.md) - Open Source, ngx_http modules, OpenResty
- [**HAProxy Provider**](docs/guides/HAPROXY.md) - Advanced Load Balancing, ACLs, High performance

### Roadmap & Changelog
- [**Roadmap**](ROADMAP.md) - Geplante Features und Releases
- [**v1.1.0 Plan**](docs/v1.1.0-PLAN.md) - v1.1.0 Implementierungsplan (100% abgeschlossen)
- [**v1.2.0 Plan**](docs/v1.2.0-PLAN.md) - v1.2.0 Implementierungsplan (83.3% abgeschlossen - 5/6 Features)
- [Changelog](CHANGELOG.md)

## Testing & Development

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

- **323 Tests** mit **89% Code Coverage**
- Unit Tests für alle Module
- Provider-spezifische Tests (Envoy, Kong, APISIX, Traefik, Nginx, HAProxy)
- CLI Tests mit Click CliRunner
- End-to-End Workflow Tests
- Deployment Tests (mit Mocking)
- Real-World Szenario Tests
- Feature Tests (Rate Limiting, Auth, Headers, CORS, Circuit Breaker, Health Checks, WebSocket, Body Transformation)

### Code Quality

```bash
# Formatting mit black
black .

# Import sorting mit isort
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
   - Code Quality Checks
   - Coverage Reporting

2. **Docker Build** (`.github/workflows/docker-build.yml`)
   - Automatischer Build und Push zu ghcr.io
   - Multi-Platform Support (amd64, arm64)
   - Intelligentes Tagging (semver, branch, sha)

3. **Release** (`.github/workflows/release.yml`)
   - Automatische Releases bei Git Tags
   - Changelog-Generierung
   - Package Building
   - GitHub Release Creation

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

## Contributing

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
