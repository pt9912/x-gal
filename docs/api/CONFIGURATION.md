# GAL Konfigurationsreferenz

## Übersicht

GAL verwendet YAML-Dateien zur Definition von Gateway-Konfigurationen. Diese Konfigurationen sind provider-agnostisch und können für jeden unterstützten Gateway-Provider (Envoy, Kong, APISIX, Traefik) generiert werden.

## Konfigurationsschema

### Root-Level-Struktur

```yaml
version: string          # Konfigurationsversion (erforderlich)
provider: string         # Ziel-Provider (erforderlich)
global: object          # Globale Gateway-Einstellungen (optional)
services: array         # Liste der Services (erforderlich)
plugins: array          # Liste der Plugins (optional)
```

### Global Configuration

Globale Einstellungen, die auf das gesamte Gateway angewendet werden.

```yaml
global:
  host: string          # Listen-Host (Standard: "0.0.0.0")
  port: integer         # Listen-Port (Standard: 10000)
  admin_port: integer   # Admin-Port (Standard: 9901)
  timeout: string       # Request-Timeout (Standard: "30s")
```

**Beispiel:**

```yaml
global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901
  timeout: 30s
```

### Services

Liste der Backend-Services, die über das Gateway geroutet werden.

```yaml
services:
  - name: string                # Service-Name (erforderlich, einzigartig)
    type: string                # Service-Typ: "grpc" oder "rest" (erforderlich)
    protocol: string            # Protokoll: "http", "http2", "grpc" (erforderlich)
    upstream: object            # Upstream-Konfiguration (erforderlich)
    routes: array              # Route-Definitionen (erforderlich)
    transformation: object     # Transformationsregeln (optional)
```

#### Upstream

Definiert den Backend-Service-Endpunkt.

```yaml
upstream:
  host: string    # Hostname oder IP-Adresse (erforderlich)
  port: integer   # Port-Nummer (erforderlich)
```

**Beispiel:**

```yaml
upstream:
  host: user-service
  port: 9090
```

#### Routes

Definiert, wie Requests zum Service geroutet werden.

```yaml
routes:
  - path_prefix: string    # URL-Path-Präfix (erforderlich)
    methods: array         # HTTP-Methoden (optional, nur für REST)
```

**Beispiele:**

```yaml
# gRPC-Route
routes:
  - path_prefix: /myapp.UserService

# REST-Route mit Methoden
routes:
  - path_prefix: /api/products
    methods: [GET, POST, PUT, DELETE]

# Mehrere Routes
routes:
  - path_prefix: /api/v1/users
    methods: [GET, POST]
  - path_prefix: /api/v1/users/{id}
    methods: [GET, PUT, DELETE]
```

#### Transformation

Definiert Payload-Transformationen, die auf Requests angewendet werden.

```yaml
transformation:
  enabled: boolean              # Transformationen aktivieren (Standard: true)
  defaults: object             # Default-Werte für Felder
  computed_fields: array       # Berechnete/generierte Felder
  metadata: object             # Zusätzliche Metadaten
  validation: object           # Validierungsregeln
```

**defaults:**

Setzt Standard-Werte für fehlende Felder im Request-Body.

```yaml
defaults:
  field_name: value
```

**Beispiel:**

```yaml
defaults:
  status: "pending"
  currency: "USD"
  active: true
  priority: 5
```

**computed_fields:**

Generiert Felder automatisch basierend auf vordefinierten Generatoren.

```yaml
computed_fields:
  - field: string        # Feldname (erforderlich)
    generator: string    # Generator-Typ (erforderlich)
    prefix: string       # Präfix für generierten Wert (optional)
    suffix: string       # Suffix für generierten Wert (optional)
    expression: string   # Custom-Expression (optional, derzeit nicht verwendet)
```

**Verfügbare Generatoren:**

| Generator | Beschreibung | Beispiel-Ausgabe |
|-----------|--------------|------------------|
| `uuid` | Generiert UUID v4 | `550e8400-e29b-41d4-a716-446655440000` |
| `timestamp` | Unix-Timestamp | `1698765432` |
| `random` | Zufallszahl | `42` |

**Beispiel:**

```yaml
computed_fields:
  - field: user_id
    generator: uuid
    prefix: "user_"
    # Ergebnis: user_550e8400-e29b-41d4-a716-446655440000

  - field: created_at
    generator: timestamp
    # Ergebnis: 1698765432

  - field: order_id
    generator: uuid
    prefix: "order_"
    suffix: "_v1"
    # Ergebnis: order_550e8400-e29b-41d4-a716-446655440000_v1
```

**metadata:**

Fügt zusätzliche Metadaten zum Request hinzu.

```yaml
metadata:
  key: value
```

**Beispiel:**

```yaml
metadata:
  enriched_by: "gateway"
  service_name: "product_service"
  version: "1.0"
```

**validation:**

Definiert Validierungsregeln für Request-Payloads.

```yaml
validation:
  required_fields: array    # Liste erforderlicher Felder
```

**Beispiel:**

```yaml
validation:
  required_fields:
    - order_id
    - amount
    - method
```

### Plugins

Gateway-Plugins für erweiterte Funktionalität.

```yaml
plugins:
  - name: string        # Plugin-Name (erforderlich)
    enabled: boolean    # Plugin aktiviert (Standard: true)
    config: object      # Plugin-Konfiguration (optional)
```

**Beispiel:**

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
      headers: [Content-Type, Authorization]
```

## Vollständiges Beispiel

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901
  timeout: 30s

services:
  # gRPC Service mit Transformationen
  - name: user_service
    type: grpc
    protocol: http2
    upstream:
      host: user-service
      port: 9090
    routes:
      - path_prefix: /myapp.UserService
    transformation:
      enabled: true
      defaults:
        role: "user"
        age: 0
        active: true
      computed_fields:
        - field: user_id
          generator: uuid
          prefix: "user_"
        - field: created_at
          generator: timestamp
      metadata:
        service: "user_service"
        version: "1.0"

  # REST Service mit Validierung
  - name: payment_service
    type: rest
    protocol: http
    upstream:
      host: payment-service
      port: 8081
    routes:
      - path_prefix: /api/payments
        methods: [POST]
    transformation:
      enabled: true
      defaults:
        status: "pending"
        currency: "USD"
        provider: "stripe"
      computed_fields:
        - field: payment_id
          generator: uuid
          prefix: "pay_"
        - field: timestamp
          generator: timestamp
      validation:
        required_fields:
          - order_id
          - amount
          - method

  # REST Service ohne Transformationen
  - name: health_check
    type: rest
    protocol: http
    upstream:
      host: health-service
      port: 8082
    routes:
      - path_prefix: /health
        methods: [GET]

plugins:
  - name: rate_limiting
    enabled: true
    config:
      requests_per_second: 100
      burst: 200

  - name: authentication
    enabled: true
    config:
      jwt_secret: ${JWT_SECRET}
      token_header: Authorization
```

## Provider-spezifische Hinweise

### Envoy

- gRPC-Services erhalten automatisch `http2_protocol_options`
- Transformationen werden als Lua-Filter implementiert
- Admin-Interface läuft auf konfiguriertem `admin_port`

### Kong

- Output ist Kong Declarative Configuration (v3.0)
- Transformationen nutzen `request-transformer` Plugin
- gRPC-Services verwenden `protocol: grpc`

### APISIX

- Output ist JSON-Format
- Transformationen werden als Lua-Serverless-Functions implementiert
- Automatische Upstream-Generierung mit Round-Robin Load Balancing

### Traefik

- Routes verwenden PathPrefix-Regel
- Transformationen werden als Middleware-Plugins implementiert
- Services erhalten automatische LoadBalancer-Konfiguration

## Validierung

Nutzen Sie den `validate`-Befehl, um Ihre Konfiguration zu prüfen:

```bash
gal-cli.py validate -c config.yaml
```

## Best Practices

### 1. Naming Conventions

- Verwenden Sie snake_case für Service-Namen
- Nutzen Sie aussagekräftige Namen, die die Funktion beschreiben
- Vermeiden Sie Sonderzeichen außer Unterstrichen

```yaml
# Gut
name: user_authentication_service

# Schlecht
name: UserAuth123!
```

### 2. Transformationen

- Nutzen Sie Defaults für optionale Felder
- Computed Fields für eindeutige IDs und Timestamps
- Validation für kritische Business-Felder

```yaml
transformation:
  enabled: true
  defaults:
    status: "draft"  # Optionales Feld mit sinnvollem Default
  computed_fields:
    - field: id
      generator: uuid  # Eindeutige ID garantiert
  validation:
    required_fields:
      - customer_id  # Kritisches Business-Feld
```

### 3. Environment Variables

Nutzen Sie Environment Variables für Secrets:

```yaml
plugins:
  - name: auth
    config:
      secret: ${JWT_SECRET}  # Nie hardcoden!
      api_key: ${API_KEY}
```

### 4. Service-Organisation

Gruppieren Sie Services logisch:

```yaml
services:
  # Authentication Services
  - name: auth_service
    ...

  - name: user_service
    ...

  # Business Logic Services
  - name: order_service
    ...

  - name: payment_service
    ...

  # Infrastructure Services
  - name: health_check
    ...
```

## Fehlerbehandlung

### Häufige Fehler

**Fehlende erforderliche Felder:**

```yaml
# Fehler: upstream fehlt
services:
  - name: my_service
    type: rest
    protocol: http
    # upstream: FEHLT!
    routes:
      - path_prefix: /api
```

**Ungültiger Service-Typ:**

```yaml
# Fehler: type muss "grpc" oder "rest" sein
services:
  - name: my_service
    type: http  # FALSCH!
    ...
```

**Duplikat Service-Namen:**

```yaml
# Fehler: Service-Namen müssen eindeutig sein
services:
  - name: user_service
    ...
  - name: user_service  # DUPLIKAT!
    ...
```

## Siehe auch

- [CLI-Referenz](CLI_REFERENCE.md)
- [Transformations-Guide](../guides/TRANSFORMATIONS.md)
- [Provider-Dokumentation](../guides/PROVIDERS.md)
