# GAL Schnellstart-Guide

## Was ist GAL?

Gateway Abstraction Layer (GAL) ist ein Tool, das es ermöglicht, API-Gateway-Konfigurationen einmal zu definieren und für verschiedene Gateway-Provider (Envoy, Kong, APISIX, Traefik) zu generieren.

**Vorteile:**
- ✅ Keine Vendor Lock-in
- ✅ Einheitliche Konfiguration
- ✅ Automatische Payload-Transformationen
- ✅ Unterstützung für REST und gRPC
- ✅ Docker-ready

## Installation

### Option 1: Mit Docker (empfohlen)

```bash
# Image bauen
docker build -t gal:latest .

# Testen
docker run --rm gal:latest list-providers
```

### Option 2: Mit Python

```bash
# Repository klonen
git clone https://github.com/pt9912/x-gal.git
cd x-gal

# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

## Erste Schritte

### 1. Konfiguration erstellen

Erstelle eine Datei `my-gateway.yaml`:

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 8080

services:
  - name: hello_service
    type: rest
    protocol: http
    upstream:
      host: hello-app
      port: 3000
    routes:
      - path_prefix: /hello
        methods: [GET, POST]
```

### 2. Konfiguration validieren

```bash
# Mit Docker
docker run --rm -v $(pwd):/app/config gal:latest \
  validate --config config/my-gateway.yaml

# Mit Python
python gal-cli.py validate -c my-gateway.yaml
```

**Erwartete Ausgabe:**

```
✓ Configuration is valid
  Provider: envoy
  Services: 1
  gRPC services: 0
  REST services: 1
```

### 3. Gateway-Konfiguration generieren

```bash
# Mit Docker
docker run --rm -v $(pwd):/app/config -v $(pwd)/output:/app/generated gal:latest \
  generate --config config/my-gateway.yaml --output generated/envoy.yaml

# Mit Python
python gal-cli.py generate -c my-gateway.yaml -o envoy.yaml
```

**Ergebnis:** Eine `envoy.yaml` Datei mit der vollständigen Envoy-Konfiguration.

### 4. Für andere Provider generieren

```bash
# Kong
python gal-cli.py generate -c my-gateway.yaml -p kong -o kong.yaml

# APISIX
python gal-cli.py generate -c my-gateway.yaml -p apisix -o apisix.json

# Traefik
python gal-cli.py generate -c my-gateway.yaml -p traefik -o traefik.yaml

# Alle gleichzeitig
python gal-cli.py generate-all -c my-gateway.yaml
```

## Erweiterte Funktionen

### Payload-Transformationen

```yaml
services:
  - name: user_service
    type: rest
    protocol: http
    upstream:
      host: users-api
      port: 8080
    routes:
      - path_prefix: /api/users
        methods: [POST]
    transformation:
      enabled: true
      defaults:
        role: "user"
        active: true
      computed_fields:
        - field: user_id
          generator: uuid
          prefix: "usr_"
        - field: created_at
          generator: timestamp
      validation:
        required_fields:
          - email
          - name
```

**Was passiert:**
1. Fehlende Felder werden mit Defaults gefüllt (`role: "user"`, `active: true`)
2. `user_id` wird automatisch generiert (z.B. `usr_550e8400...`)
3. `created_at` wird mit aktuellem Timestamp gesetzt
4. Request wird abgelehnt, wenn `email` oder `name` fehlt

### gRPC-Services

```yaml
services:
  - name: order_service
    type: grpc
    protocol: http2
    upstream:
      host: order-grpc
      port: 9090
    routes:
      - path_prefix: /myapp.OrderService
    transformation:
      enabled: true
      defaults:
        status: "pending"
      computed_fields:
        - field: order_id
          generator: uuid
          prefix: "ord_"
```

### Plugins

```yaml
plugins:
  - name: rate_limiting
    enabled: true
    config:
      requests_per_second: 100
      burst: 200

  - name: cors
    enabled: true
    config:
      origins: ["*"]
      methods: [GET, POST, PUT, DELETE]
```

## Praktische Beispiele

### Beispiel 1: E-Commerce API-Gateway

```yaml
version: "1.0"
provider: kong

global:
  port: 8000

services:
  # Produktkatalog
  - name: products
    type: rest
    protocol: http
    upstream:
      host: product-service
      port: 8080
    routes:
      - path_prefix: /api/products
        methods: [GET, POST, PUT, DELETE]
    transformation:
      enabled: true
      defaults:
        in_stock: true
        currency: "EUR"
      computed_fields:
        - field: product_id
          generator: uuid
          prefix: "prod_"

  # Warenkorb
  - name: cart
    type: rest
    protocol: http
    upstream:
      host: cart-service
      port: 8081
    routes:
      - path_prefix: /api/cart
        methods: [GET, POST, PUT, DELETE]
    transformation:
      enabled: true
      computed_fields:
        - field: cart_id
          generator: uuid
          prefix: "cart_"
        - field: created_at
          generator: timestamp

  # Bestellungen
  - name: orders
    type: rest
    protocol: http
    upstream:
      host: order-service
      port: 8082
    routes:
      - path_prefix: /api/orders
        methods: [GET, POST]
    transformation:
      enabled: true
      defaults:
        status: "pending"
        payment_status: "unpaid"
      computed_fields:
        - field: order_id
          generator: uuid
          prefix: "ord_"
        - field: order_date
          generator: timestamp
      validation:
        required_fields:
          - customer_id
          - items

plugins:
  - name: rate_limiting
    enabled: true
    config:
      requests_per_second: 100
```

**Konfiguration generieren:**

```bash
python gal-cli.py generate -c ecommerce.yaml -o kong.yaml
```

### Beispiel 2: Microservices mit gRPC

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

services:
  # Authentifizierung
  - name: auth_service
    type: grpc
    protocol: http2
    upstream:
      host: auth-grpc
      port: 9090
    routes:
      - path_prefix: /auth.AuthService

  # Benutzerverwaltung
  - name: user_service
    type: grpc
    protocol: http2
    upstream:
      host: user-grpc
      port: 9091
    routes:
      - path_prefix: /users.UserService
    transformation:
      enabled: true
      computed_fields:
        - field: user_id
          generator: uuid
        - field: created_at
          generator: timestamp

  # Benachrichtigungen
  - name: notification_service
    type: grpc
    protocol: http2
    upstream:
      host: notify-grpc
      port: 9092
    routes:
      - path_prefix: /notifications.NotificationService
    transformation:
      enabled: true
      defaults:
        priority: "normal"
        channel: "email"
```

## Docker Compose Integration

Erstelle `docker-compose.yml`:

```yaml
version: '3.8'

services:
  gateway:
    image: envoyproxy/envoy:v1.28-latest
    volumes:
      - ./generated/envoy.yaml:/etc/envoy/envoy.yaml
    ports:
      - "10000:10000"
      - "9901:9901"
    command: envoy -c /etc/envoy/envoy.yaml

  hello-app:
    image: hashicorp/http-echo
    command: ["-text=Hello from backend!"]
    ports:
      - "3000:5678"
```

**Workflow:**

```bash
# 1. GAL-Konfiguration generieren
python gal-cli.py generate -c my-gateway.yaml -o generated/envoy.yaml

# 2. Services starten
docker-compose up -d

# 3. Testen
curl http://localhost:10000/hello
```

## Häufige Use Cases

### Use Case 1: Multi-Environment Setup

```bash
# Entwicklung (Envoy)
python gal-cli.py generate -c config.yaml -p envoy -o dev/envoy.yaml

# Staging (Kong)
python gal-cli.py generate -c config.yaml -p kong -o staging/kong.yaml

# Produktion (APISIX)
python gal-cli.py generate -c config.yaml -p apisix -o prod/apisix.json
```

### Use Case 2: Gateway-Migration

```bash
# Aktuelle Kong-Konfiguration
# Erstelle GAL-Config basierend auf Kong-Setup

# Generiere für neuen Provider
python gal-cli.py generate -c config.yaml -p envoy -o envoy.yaml

# Test parallel
# Beide Gateways mit gleichem Traffic

# Migration
# Schrittweise Traffic verschieben
```

### Use Case 3: CI/CD Integration

```bash
#!/bin/bash
# deploy-gateway.sh

CONFIG="config/gateway.yaml"
PROVIDER="envoy"
OUTPUT="deploy/envoy.yaml"

# Validieren
python gal-cli.py validate -c $CONFIG || exit 1

# Generieren
python gal-cli.py generate -c $CONFIG -p $PROVIDER -o $OUTPUT

# Deployen
kubectl apply -f $OUTPUT --namespace=production
```

## Troubleshooting

### Problem: "Provider not registered"

```bash
Error: Provider 'xyz' not registered
```

**Lösung:** Nutze einen unterstützten Provider:
- envoy
- kong
- apisix
- traefik

### Problem: "Port must be specified"

```yaml
# Falsch
global:
  port: 0

# Richtig
global:
  port: 8080
```

### Problem: Docker Volume Permissions

```bash
# Linux: Verwende aktuelle UID/GID
docker run --rm --user $(id -u):$(id -g) -v $(pwd):/app/config gal:latest ...
```

## Nächste Schritte

- 📖 [Vollständige Konfigurationsreferenz](../api/CONFIGURATION.md)
- 🔧 [CLI-Befehlsreferenz](../api/CLI_REFERENCE.md)
- 🏗️ [Architektur-Dokumentation](../architecture/ARCHITECTURE.md)
- 💻 [Entwickler-Guide](DEVELOPMENT.md)
- 🌐 [Provider-Details](PROVIDERS.md)

## Community & Support

- **Issues:** https://github.com/pt9912/x-gal/issues
- **Discussions:** https://github.com/pt9912/x-gal/discussions
- **Examples:** `examples/` Verzeichnis im Repository

## Lizenz

MIT License - siehe [LICENSE](../../LICENSE) für Details.
