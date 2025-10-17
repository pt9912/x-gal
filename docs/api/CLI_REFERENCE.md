# GAL CLI Referenz

## Übersicht

Das GAL Command-Line Interface (CLI) bietet einen einfachen Zugang zur Gateway Abstraction Layer-Funktionalität für die Generierung, Validierung und Verwaltung von API-Gateway-Konfigurationen.

## Installation

```bash
# Mit pip
pip install gal

# Aus dem Quellcode
git clone https://github.com/pt9912/x-gal.git
cd x-gal
pip install -e .
```

## Globale Optionen

Alle Befehle unterstützen folgende globale Optionen:

- `--help` - Zeigt Hilfetext an

## Befehle

### `generate`

Generiert Gateway-Konfigurationen für einen spezifischen Provider.

**Syntax:**
```bash
gal-cli.py generate --config <datei> [--provider <provider>] [--output <datei>]
```

**Optionen:**

| Option | Kurzform | Beschreibung | Erforderlich |
|--------|----------|--------------|--------------|
| `--config` | `-c` | Pfad zur YAML-Konfigurationsdatei | Ja |
| `--provider` | `-p` | Provider-Name (überschreibt Config) | Nein |
| `--output` | `-o` | Ausgabedatei (Standard: stdout) | Nein |

**Unterstützte Provider:**
- `envoy` - Envoy Proxy
- `kong` - Kong API Gateway
- `apisix` - Apache APISIX
- `traefik` - Traefik

**Beispiele:**

```bash
# Konfiguration für Envoy generieren
gal-cli.py generate -c examples/gateway-config.yaml -o generated/envoy.yaml

# Provider überschreiben und nach stdout ausgeben
gal-cli.py generate -c examples/gateway-config.yaml -p kong

# Kong-Konfiguration in Datei schreiben
gal-cli.py generate -c examples/gateway-config.yaml -p kong -o kong-config.yaml
```

**Ausgabe:**

```
Generating configuration for: envoy
Services: 5 (3 gRPC, 2 REST)
✓ Configuration written to: generated/envoy.yaml
```

### `validate`

Validiert eine GAL-Konfigurationsdatei.

**Syntax:**
```bash
gal-cli.py validate --config <datei>
```

**Optionen:**

| Option | Kurzform | Beschreibung | Erforderlich |
|--------|----------|--------------|--------------|
| `--config` | `-c` | Pfad zur YAML-Konfigurationsdatei | Ja |

**Beispiele:**

```bash
# Konfiguration validieren
gal-cli.py validate -c examples/gateway-config.yaml
```

**Ausgabe (Erfolg):**

```
✓ Configuration is valid
  Provider: envoy
  Services: 5
  gRPC services: 3
  REST services: 2
```

**Ausgabe (Fehler):**

```
✗ Configuration is invalid: Port must be specified
```

### `generate-all`

Generiert Konfigurationen für alle unterstützten Provider gleichzeitig.

**Syntax:**
```bash
gal-cli.py generate-all --config <datei> [--output-dir <verzeichnis>]
```

**Optionen:**

| Option | Kurzform | Beschreibung | Erforderlich | Standard |
|--------|----------|--------------|--------------|----------|
| `--config` | `-c` | Pfad zur YAML-Konfigurationsdatei | Ja | - |
| `--output-dir` | `-o` | Ausgabeverzeichnis | Nein | `generated` |

**Beispiele:**

```bash
# Alle Provider generieren
gal-cli.py generate-all -c examples/gateway-config.yaml

# Mit benutzerdefiniertem Ausgabeverzeichnis
gal-cli.py generate-all -c examples/gateway-config.yaml -o output/configs
```

**Ausgabe:**

```
Generating configurations for all providers...
Output directory: /path/to/generated

  ✓ envoy: /path/to/generated/envoy.yaml
  ✓ kong: /path/to/generated/kong.yaml
  ✓ apisix: /path/to/generated/apisix.json
  ✓ traefik: /path/to/generated/traefik.yaml

✓ All configurations generated successfully
```

**Generierte Dateien:**

- `envoy.yaml` - Envoy-Konfiguration im YAML-Format
- `kong.yaml` - Kong deklarative Konfiguration
- `apisix.json` - APISIX-Konfiguration im JSON-Format
- `traefik.yaml` - Traefik-Konfiguration

### `info`

Zeigt detaillierte Informationen über eine Konfigurationsdatei an.

**Syntax:**
```bash
gal-cli.py info --config <datei>
```

**Optionen:**

| Option | Kurzform | Beschreibung | Erforderlich |
|--------|----------|--------------|--------------|
| `--config` | `-c` | Pfad zur YAML-Konfigurationsdatei | Ja |

**Beispiele:**

```bash
# Konfigurationsinformationen anzeigen
gal-cli.py info -c examples/gateway-config.yaml
```

**Ausgabe:**

```
============================================================
GAL Configuration Information
============================================================
Provider: envoy
Version: 1.0

Global Settings:
  Host: 0.0.0.0
  Port: 10000
  Admin Port: 9901
  Timeout: 30s

Services (5 total):

  • user_service
    Type: grpc
    Upstream: user-service:9090
    Routes: 1
    Transformations: ✓ Enabled
      Defaults: 3 fields
      Computed: 2 fields

  • order_service
    Type: grpc
    Upstream: order-service:9091
    Routes: 1
    Transformations: ✓ Enabled
      Defaults: 3 fields
      Computed: 2 fields

  • product_service
    Type: rest
    Upstream: product-service:8080
    Routes: 1
    Transformations: ✓ Enabled
      Defaults: 4 fields
      Computed: 2 fields

  • payment_service
    Type: rest
    Upstream: payment-service:8081
    Routes: 1
    Transformations: ✓ Enabled
      Defaults: 3 fields
      Computed: 2 fields
      Required: order_id, amount, method

Plugins (1):
  ✓ rate_limiting
```

### `list-providers`

Listet alle verfügbaren Gateway-Provider auf.

**Syntax:**
```bash
gal-cli.py list-providers
```

**Keine Optionen erforderlich.**

**Beispiele:**

```bash
# Verfügbare Provider auflisten
gal-cli.py list-providers
```

**Ausgabe:**

```
Available providers:
  • envoy   - Envoy Proxy
  • kong    - Kong API Gateway
  • apisix  - Apache APISIX
  • traefik - Traefik
```

## Docker-Verwendung

### Grundlegende Verwendung

```bash
# Image bauen
docker build -t gal:latest .

# Befehl ausführen
docker run --rm gal:latest list-providers
```

### Mit Volume-Mounting

```bash
# Konfiguration generieren mit Volume
docker run --rm \
  -v $(pwd)/examples:/app/examples \
  -v $(pwd)/generated:/app/generated \
  gal:latest generate \
    --config examples/gateway-config.yaml \
    --output generated/envoy.yaml
```

### Mit Docker Compose

```bash
# Standard-Generierung (Envoy)
docker-compose up gal-generate

# Für spezifischen Provider
PROVIDER=kong docker-compose up gal-generate

# Alle Provider generieren
docker-compose up gal-generate-all
```

## Fehlerbehandlung

### Exit-Codes

| Code | Bedeutung |
|------|-----------|
| 0 | Erfolg |
| 1 | Fehler (Validierung fehlgeschlagen, Datei nicht gefunden, etc.) |

### Häufige Fehler

**Datei nicht gefunden:**
```
Error: [Errno 2] No such file or directory: 'config.yaml'
```
→ Prüfen Sie, ob die Konfigurationsdatei existiert und der Pfad korrekt ist.

**Ungültige YAML-Syntax:**
```
Error: while parsing a block mapping
```
→ Prüfen Sie die YAML-Syntax Ihrer Konfigurationsdatei.

**Provider nicht unterstützt:**
```
Error: Provider 'unknown' not registered
```
→ Verwenden Sie einen der unterstützten Provider: envoy, kong, apisix, traefik.

**Validierung fehlgeschlagen:**
```
Error: Port must be specified
```
→ Stellen Sie sicher, dass alle erforderlichen Felder in der Konfiguration gesetzt sind.

## Scripting-Beispiele

### Bash-Script für Continuous Deployment

```bash
#!/bin/bash
set -e

CONFIG_FILE="config/gateway.yaml"
OUTPUT_DIR="deploy/configs"

echo "Validating configuration..."
gal-cli.py validate -c "$CONFIG_FILE"

echo "Generating configurations..."
gal-cli.py generate-all -c "$CONFIG_FILE" -o "$OUTPUT_DIR"

echo "Deploying to environments..."
kubectl apply -f "$OUTPUT_DIR/envoy.yaml" --namespace=production

echo "✓ Deployment complete"
```

### Python-Integration

```python
import subprocess
import json

def generate_gateway_config(config_path, provider, output_path):
    """Generate gateway configuration using GAL CLI"""
    cmd = [
        'gal-cli.py', 'generate',
        '--config', config_path,
        '--provider', provider,
        '--output', output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to generate config: {result.stderr}")

    return output_path

# Verwendung
try:
    output = generate_gateway_config(
        'examples/gateway-config.yaml',
        'envoy',
        'generated/envoy.yaml'
    )
    print(f"Configuration generated: {output}")
except RuntimeError as e:
    print(f"Error: {e}")
```

## Siehe auch

- [Konfigurationsreferenz](CONFIGURATION.md)
- [Provider-Dokumentation](../guides/PROVIDERS.md)
- [Transformations-Guide](../guides/TRANSFORMATIONS.md)
