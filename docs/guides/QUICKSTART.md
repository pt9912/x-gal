# GAL Schnellstart-Guide

## Was ist GAL?

Gateway Abstraction Layer (GAL) ist ein Tool, das es ermöglicht, API-Gateway-Konfigurationen einmal zu definieren und für verschiedene Gateway-Provider (Envoy, Kong, APISIX, Traefik, Nginx, HAProxy, Azure APIM) zu generieren.

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

## Beispiel-Workflows

Diese Workflows zeigen typische Anwendungsfälle für GAL in verschiedenen Szenarien.

### Workflow 1: Lokale Entwicklung

Schneller Einstieg für lokale Entwicklung mit Docker:

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
gal validate -c my-config.yaml

# 3. Generieren
gal generate -c my-config.yaml -o envoy.yaml

# 4. Envoy starten
docker run -d -v $(pwd)/envoy.yaml:/etc/envoy/envoy.yaml \
  -p 10000:10000 envoyproxy/envoy:v1.28-latest

# 5. Testen
curl http://localhost:10000/api
```

### Workflow 2: Multi-Environment Deployment

Verschiedene Provider für verschiedene Umgebungen:

```bash
# Development (Envoy - schnelle Iteration)
gal generate -c config.yaml -p envoy -o dev/envoy.yaml

# Staging (Kong - Plugin-Testing)
gal generate -c config.yaml -p kong -o staging/kong.yaml

# Production (APISIX - High Performance)
gal generate -c config.yaml -p apisix -o prod/apisix.json
```

**Vorteile:**
- Gleiche GAL-Config für alle Umgebungen
- Provider-spezifische Optimierungen pro Umgebung
- Einfache Promotion: Dev → Staging → Prod

### Workflow 3: Gateway-Migration

Schrittweise Migration von einem Gateway-Provider zu einem anderen:

```bash
# Aktuell: Kong in Produktion
# Ziel: Migration zu Envoy

# 1. GAL-Config aus bestehender Kong-Config erstellen
gal import -i kong-config.yaml -p kong -o gal-config.yaml

# 2. Envoy-Config generieren
gal generate -c gal-config.yaml -p envoy -o envoy.yaml

# 3. Parallel-Deployment mit Traffic-Mirroring
# - Kong bekommt 100% Live-Traffic
# - Envoy bekommt gespiegelten Traffic (Shadow Mode)

# 4. Canary-Deployment
# Phase 1: 10% Traffic zu Envoy
# Phase 2: 50% Traffic zu Envoy
# Phase 3: 100% Traffic zu Envoy

# 5. Kong deaktivieren
```

**Migrations-Checkliste:**
- [ ] GAL-Config aus Quell-Provider importieren
- [ ] Ziel-Provider Config generieren
- [ ] Feature-Kompatibilität prüfen (`gal compatibility-check`)
- [ ] Shadow-Deployment testen
- [ ] Canary-Rollout mit Traffic-Splitting
- [ ] Monitoring vergleichen (Latenz, Error-Rate)
- [ ] Rollback-Plan bereit haben

### Workflow 4: CI/CD Integration

Integration in eine Deployment-Pipeline:

```bash
# .github/workflows/deploy.yml oder .gitlab-ci.yml

# 1. Config validieren
gal validate -c config/gateway.yaml

# 2. Provider-spezifische Configs generieren
gal generate -c config/gateway.yaml -p envoy -o deploy/envoy.yaml

# 3. Config in Kubernetes deployen
kubectl apply -f deploy/envoy.yaml

# 4. Health-Check
curl --retry 5 --retry-delay 2 http://gateway.example.com/health
```

## Troubleshooting

### Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| `Provider not registered` | Unbekannter Provider-Name | Nutze einen der unterstützten Provider: `nginx`, `envoy`, `kong`, `apisix`, `traefik`, `haproxy`, `azure_apim`, `gcp_apigateway`, `aws_apigateway` |
| `Port must be specified` | `port: 0` in Global-Config | Setze einen gültigen Port (z.B. `port: 8080`) in der Global-Sektion |
| `No such file or directory` | Config-Datei nicht gefunden | Prüfe den Pfad zur Config-Datei mit `ls -la config.yaml` |
| `Invalid YAML syntax` | YAML-Syntax-Fehler | Validiere YAML-Syntax mit einem Online-Tool oder `yamllint config.yaml` |
| `Field 'upstream' is required` | Pflichtfeld fehlt | Füge alle Pflichtfelder hinzu (siehe [Konfigurationsreferenz](../api/CONFIGURATION.md)) |
| `Docker permission denied` | Fehlende Docker-Berechtigungen | Führe `sudo usermod -aG docker $USER` aus und melde dich neu an |

### Detailliertes Debugging

```bash
# 1. Config-Validierung mit Details
gal validate -c config.yaml --verbose

# 2. Generierung mit Debug-Output
gal generate -c config.yaml -p envoy --debug

# 3. Provider-Kompatibilität prüfen
gal compatibility-check -c config.yaml -p envoy

# 4. Config-Diff zwischen Providern
diff <(gal generate -c config.yaml -p envoy) \
     <(gal generate -c config.yaml -p kong)
```

## Nächste Schritte

- 📖 [Vollständige Konfigurationsreferenz](../api/CONFIGURATION.md)
- 🔧 [CLI-Befehlsreferenz](../api/CLI_REFERENCE.md)
- 🏗️ [Architektur-Dokumentation](../architecture/ARCHITECTURE.md)
- 💻 [Entwickler-Guide](DEVELOPMENT.md)
- 🌐 [Provider-Details](PROVIDERS.md)
- 📝 [Konfigurationsbeispiele](EXAMPLES.md) - Vollständige Beispiele für alle Use Cases
- ✅ [Best Practices](BEST_PRACTICES.md) - Production-Ready Konfigurationen

## Externe Ressourcen

### Provider-Dokumentation

Offizielle Dokumentation der unterstützten Gateway-Provider:

- **[Nginx Dokumentation](https://nginx.org/en/docs/)** - Nginx Core + OpenResty
- **[Envoy Dokumentation](https://www.envoyproxy.io/docs)** - Envoy Proxy + xDS API
- **[Kong Dokumentation](https://docs.konghq.com/)** - Kong Gateway + Plugins
- **[APISIX Dokumentation](https://apisix.apache.org/docs/)** - Apache APISIX + Lua Serverless
- **[Traefik Dokumentation](https://doc.traefik.io/traefik/)** - Traefik Proxy + Middleware
- **[HAProxy Dokumentation](https://docs.haproxy.org/)** - HAProxy Configuration
- **[Azure APIM Dokumentation](https://learn.microsoft.com/en-us/azure/api-management/)** - Azure API Management
- **[AWS API Gateway Dokumentation](https://docs.aws.amazon.com/apigateway/)** - AWS API Gateway
- **[GCP API Gateway Dokumentation](https://cloud.google.com/api-gateway/docs)** - Google Cloud API Gateway

### Verwandte Projekte

- **[Istio](https://istio.io/)** - Service Mesh mit Envoy als Data Plane
- **[KrakenD](https://www.krakend.io/)** - High-Performance API Gateway
- **[Tyk](https://tyk.io/)** - Open Source API Gateway mit Analytics
- **[Apollo Router](https://www.apollographql.com/docs/router/)** - GraphQL Gateway
- **[Express Gateway](https://www.express-gateway.io/)** - Node.js API Gateway

### Tools & Utilities

- **[Postman](https://www.postman.com/)** - API Testing & Documentation
- **[HTTPie](https://httpie.io/)** - User-friendly HTTP Client
- **[k6](https://k6.io/)** - Load Testing für APIs
- **[Grafana](https://grafana.com/)** - Monitoring & Observability
- **[Prometheus](https://prometheus.io/)** - Metrics Collection
- **[Jaeger](https://www.jaegertracing.io/)** - Distributed Tracing

## Community & Support

- **GitHub Issues:** https://github.com/pt9912/x-gal/issues
- **Discussions:** https://github.com/pt9912/x-gal/discussions
- **Examples:** `examples/` Verzeichnis im Repository

## Lizenz

MIT License - siehe [LICENSE](../../LICENSE) für Details.
