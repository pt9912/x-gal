# Gateway Abstraction Layer (GAL) - Python Edition

**Gateway-Abstraktionsschicht** - Provider-agnostisches API-Gateway-Konfigurations- und Transformationssystem in Python.

Definiere deine API-Gateway-Konfiguration einmal und deploye sie auf Envoy, Kong, APISIX, Traefik oder anderen Gateways - ohne Vendor Lock-in.

## Features

- ✅ **Einheitliche YAML-Konfiguration** für mehrere API-Gateway-Provider
- ✅ **Unterstützung für Envoy, Kong, APISIX, Traefik**
- ✅ **Automatische Payload-Transformationsgenerierung**
- ✅ **REST- und gRPC-Service-Unterstützung** (3 gRPC + 2 REST Services)
- ✅ **Default-Wert-Injektion**
- ✅ **Berechnete Felder** (UUIDs, Zeitstempel)
- ✅ **Feldvalidierung**
- ✅ **Reines Python** - kein Go erforderlich!

## Installation

### 🐳 Docker (Empfohlen)

```bash
# Image bauen
docker build -t gal:latest .

# Direkt verwenden
docker run --rm gal:latest list-providers

# Mit Volume für Ausgabe
docker run --rm -v $(pwd)/generated:/app/generated gal:latest \
  generate --config examples/gateway-config.yaml --provider envoy --output generated/envoy.yaml
```

### 🐍 Python (Lokal)

```bash
# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# CLI ausführbar machen
chmod +x gal-cli.py
```

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
│   │   └── traefik.py
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
python gal-cli.py generate-all --config CONFIG

# Konfigurationsinformationen anzeigen
python gal-cli.py info --config CONFIG

# Verfügbare Provider auflisten
python gal-cli.py list-providers
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

- `PROVIDER`: Gateway-Provider (envoy, kong, apisix, traefik)
- `CONFIG_FILE`: Pfad zur Konfigurationsdatei
- `OUTPUT_DIR`: Ausgabeverzeichnis für generierte Configs

## Dokumentation

- [Schnellstart-Anleitung](docs/QUICKSTART.md)
- [Architektur-Übersicht](docs/ARCHITECTURE.md)
- [Provider-Details](docs/PROVIDERS.md)
- [Transformations-Anleitung](docs/TRANSFORMATIONS.md)

## Lizenz

MIT
