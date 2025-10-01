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

## Dokumentation

- [Schnellstart-Anleitung](docs/QUICKSTART.md)
- [Architektur-Übersicht](docs/ARCHITECTURE.md)
- [Provider-Details](docs/PROVIDERS.md)
- [Transformations-Anleitung](docs/TRANSFORMATIONS.md)

## Lizenz

MIT
