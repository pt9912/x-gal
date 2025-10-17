# Transformations-Guide

## Übersicht

Transformationen in GAL ermöglichen die automatische Manipulation von Request-Payloads, bevor diese an Backend-Services weitergeleitet werden. Dies ist besonders nützlich für:

- **Default-Werte**: Fehlende Felder mit Standardwerten auffüllen
- **Computed Fields**: Automatische Generierung von IDs, Timestamps, etc.
- **Validierung**: Sicherstellen, dass erforderliche Felder vorhanden sind
- **Normalisierung**: Einheitliche Datenformate über verschiedene Services

## Konfiguration

### Basis-Struktur

```yaml
services:
  - name: my_service
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api/users
        methods: [POST, PUT]
    transformation:
      enabled: true
      defaults:
        # Default-Werte
        status: "active"
        role: "user"
      computed_fields:
        # Automatisch generierte Felder
        - field: user_id
          generator: uuid
          prefix: "usr_"
        - field: created_at
          generator: timestamp
      validation:
        # Pflichtfelder
        required_fields:
          - email
          - username
```

## Default-Werte

Default-Werte werden gesetzt, wenn ein Feld im Request fehlt oder `null` ist.

### Syntax

```yaml
transformation:
  enabled: true
  defaults:
    field_name: "default_value"
    status: "pending"
    priority: 3
    active: true
```

### Beispiel: E-Commerce Order

**Konfiguration:**

```yaml
services:
  - name: orders_api
    transformation:
      enabled: true
      defaults:
        status: "pending"
        currency: "EUR"
        payment_method: "credit_card"
        shipping_method: "standard"
```

**Eingehender Request:**

```json
{
  "customer_id": "12345",
  "items": [
    {"product_id": "A1", "quantity": 2}
  ]
}
```

**Transformierter Request:**

```json
{
  "customer_id": "12345",
  "items": [
    {"product_id": "A1", "quantity": 2}
  ],
  "status": "pending",
  "currency": "EUR",
  "payment_method": "credit_card",
  "shipping_method": "standard"
}
```

## Computed Fields

Computed Fields werden automatisch generiert, wenn sie nicht im Request vorhanden sind.

### UUID-Generierung

Generiert eine eindeutige UUID für das Feld.

```yaml
computed_fields:
  - field: user_id
    generator: uuid
    prefix: "usr_"  # Optional: Präfix
```

**Generierter Wert:** `usr_550e8400-e29b-41d4-a716-446655440000`

### Ohne Präfix:

```yaml
computed_fields:
  - field: request_id
    generator: uuid
```

**Generierter Wert:** `550e8400-e29b-41d4-a716-446655440000`

### Timestamp-Generierung

Generiert einen Unix-Timestamp (Sekunden seit 1970-01-01).

```yaml
computed_fields:
  - field: created_at
    generator: timestamp
```

**Generierter Wert:** `1698765432`

### Kombination

```yaml
computed_fields:
  - field: order_id
    generator: uuid
    prefix: "ord_"
  - field: created_at
    generator: timestamp
  - field: updated_at
    generator: timestamp
```

## Validierung

Validierung stellt sicher, dass erforderliche Felder im Request vorhanden sind.

### Syntax

```yaml
validation:
  required_fields:
    - field1
    - field2
    - nested.field
```

### Beispiel: User Registration

```yaml
services:
  - name: user_registration
    transformation:
      enabled: true
      defaults:
        role: "user"
        active: false
      computed_fields:
        - field: user_id
          generator: uuid
          prefix: "usr_"
        - field: created_at
          generator: timestamp
      validation:
        required_fields:
          - email
          - username
          - password
```

**Gültiger Request:**

```json
{
  "email": "user@example.com",
  "username": "john_doe",
  "password": "secure_password"
}
```

**Ungültiger Request (fehlt `email`):**

```json
{
  "username": "john_doe",
  "password": "secure_password"
}
```

→ Wird abgelehnt, da `email` fehlt.

## Provider-spezifische Implementierung

### Envoy Proxy

Envoy nutzt **Lua Filters** für Transformationen.

**Generierter Code:**

```lua
function envoy_on_request(request_handle)
  local path = request_handle:headers():get(':path')
  if string.find(path, '/api/users') then
    local body = request_handle:body()
    if body then
      -- Parse JSON
      -- Apply defaults
      -- Generate computed fields
      -- Validate required fields
    end
  end
end
```

**Features:**
- ✅ Defaults
- ✅ Computed Fields (UUID, Timestamp)
- ⚠️ Validierung (begrenzt)

### Kong API Gateway

Kong nutzt das **request-transformer Plugin**.

**Generierte Konfiguration:**

```yaml
plugins:
  - name: request-transformer
    config:
      add:
        headers:
          - x-default-status: 'active'
          - x-default-role: 'user'
```

**Limitationen:**
- ✅ Defaults (als Headers)
- ❌ Computed Fields (benötigt Custom Plugins)
- ❌ Native Body-Transformation

**Hinweis:** Für volle Transformation-Unterstützung müssen Custom Lua Plugins entwickelt werden.

### Apache APISIX

APISIX nutzt **Serverless Pre-Function Plugin** mit Lua.

**Generierter Code:**

```lua
return function(conf, ctx)
  local core = require('apisix.core')
  local cjson = require('cjson.safe')
  local body = core.request.get_body()

  if body then
    local json_body = cjson.decode(body)
    if json_body then
      -- Apply defaults
      json_body.status = json_body.status or 'active'

      -- Generate UUID
      if not json_body.user_id then
        json_body.user_id = 'usr_' .. core.utils.uuid()
      end

      -- Generate timestamp
      if not json_body.created_at then
        json_body.created_at = os.time()
      end

      ngx.req.set_body_data(cjson.encode(json_body))
    end
  end
end
```

**Features:**
- ✅ Defaults
- ✅ Computed Fields (UUID, Timestamp)
- ✅ Volle Body-Manipulation
- ✅ Validierung

### Traefik

Traefik nutzt **Middleware Plugins** (benötigt Go-Entwicklung).

**Generierte Konfiguration:**

```yaml
middlewares:
  my_service_transform:
    plugin:
      my_service_transformer:
        defaults:
          status: 'active'
          role: 'user'
```

**Limitationen:**
- ⚠️ Middleware benötigt Go-Entwicklung
- ❌ Keine nativen Transformationen
- ❌ Computed Fields nicht unterstützt

**Hinweis:** Traefik ist primär für Routing/Load Balancing optimiert, nicht für Payload-Manipulation.

## Anwendungsfälle

### Use Case 1: User Onboarding

**Ziel:** Neue User automatisch mit Defaults versehen.

```yaml
services:
  - name: user_service
    transformation:
      enabled: true
      defaults:
        role: "user"
        status: "pending_verification"
        notifications_enabled: true
        theme: "light"
      computed_fields:
        - field: user_id
          generator: uuid
          prefix: "usr_"
        - field: created_at
          generator: timestamp
      validation:
        required_fields:
          - email
          - username
```

### Use Case 2: Order Processing

**Ziel:** Orders mit Tracking-Informationen versehen.

```yaml
services:
  - name: orders_api
    transformation:
      enabled: true
      defaults:
        status: "pending"
        currency: "EUR"
        payment_status: "awaiting_payment"
      computed_fields:
        - field: order_id
          generator: uuid
          prefix: "ord_"
        - field: created_at
          generator: timestamp
        - field: tracking_id
          generator: uuid
          prefix: "trk_"
      validation:
        required_fields:
          - customer_id
          - items
          - total_amount
```

### Use Case 3: API Logging

**Ziel:** Alle Requests mit Tracking-IDs versehen.

```yaml
services:
  - name: logging_api
    transformation:
      enabled: true
      computed_fields:
        - field: request_id
          generator: uuid
        - field: timestamp
          generator: timestamp
```

## Best Practices

### 1. Minimale Transformationen

Transformiere nur das Notwendigste. Zu viele Transformationen können Performance beeinträchtigen.

```yaml
# Gut
defaults:
  status: "active"

# Übertrieben
defaults:
  status: "active"
  field1: "value1"
  field2: "value2"
  # ... 20 weitere Felder
```

### 2. Sinnvolle Defaults

Wähle Defaults, die für die Mehrheit der Requests sinnvoll sind.

```yaml
# Gut
defaults:
  currency: "EUR"  # Standard-Währung für EU-Region
  language: "de"   # Standard-Sprache

# Schlecht
defaults:
  admin: true  # Nicht jeder User sollte Admin sein!
```

### 3. UUID-Präfixe für Debugging

Nutze Präfixe, um IDs leichter identifizieren zu können.

```yaml
computed_fields:
  - field: user_id
    generator: uuid
    prefix: "usr_"    # → usr_...
  - field: order_id
    generator: uuid
    prefix: "ord_"    # → ord_...
  - field: payment_id
    generator: uuid
    prefix: "pay_"    # → pay_...
```

### 4. Validierung vor Transformationen

Stelle sicher, dass kritische Felder vorhanden sind, bevor Defaults gesetzt werden.

```yaml
validation:
  required_fields:
    - customer_id  # Muss vorhanden sein
    - amount       # Muss vorhanden sein

defaults:
  status: "pending"  # Kann fehlen
```

### 5. Provider-Capabilities beachten

Wähle den Provider basierend auf Transformation-Anforderungen:

| Anforderung | Empfohlener Provider |
|-------------|---------------------|
| Einfache Defaults | Alle Provider |
| Computed Fields (UUID) | APISIX, Envoy |
| Timestamp-Generierung | APISIX, Envoy |
| Komplexe Validierung | APISIX |
| Keine Transformationen | Traefik |

## Debugging

### Problem: Defaults werden nicht angewendet

**Lösung:**

1. Prüfe, ob `transformation.enabled: true` gesetzt ist
2. Verifiziere Provider-Unterstützung
3. Prüfe Gateway-Logs

```bash
# Envoy
curl http://localhost:9901/stats | grep lua

# APISIX
curl http://localhost:9080/apisix/admin/routes -H "X-API-KEY: ..."
```

### Problem: UUID-Format nicht wie erwartet

**APISIX/Envoy:**
- Format: `prefix_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

**Kong:**
- Nicht unterstützt (Custom Plugin erforderlich)

### Problem: Validierung schlägt fehl

Prüfe, ob alle `required_fields` im Request vorhanden sind:

```bash
# Test mit curl
curl -X POST http://gateway:8080/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "test_user"
  }' -v
```

## Performance-Überlegungen

### Transformation-Overhead

| Provider | Overhead | Empfehlung |
|----------|----------|------------|
| Envoy | ~0.5-1ms | ✅ Production-ready |
| APISIX | ~0.5-2ms | ✅ Production-ready |
| Kong | ~2-5ms | ⚠️ Monitor bei High-Traffic |
| Traefik | N/A | Keine nativen Transformationen |

### Optimierung

1. **Minimale Defaults**: Nur notwendige Felder transformieren
2. **Caching**: Provider-interne Caches nutzen
3. **Selective Transformation**: Nur für spezifische Routes aktivieren

```yaml
# Gut: Nur für POST/PUT
routes:
  - path_prefix: /api/users
    methods: [POST, PUT]  # Transformation nur hier

# Vermeiden: Alle Methoden
routes:
  - path_prefix: /api/users
    # Transformation für GET/DELETE unnötig
```

## Migration zwischen Providern

### Von Kong zu APISIX

**Kong (limitiert):**
```yaml
plugins:
  - name: request-transformer
    config:
      add:
        headers:
          - x-default-status: 'active'
```

**APISIX (volle Unterstützung):**
```yaml
transformation:
  enabled: true
  defaults:
    status: "active"
  computed_fields:
    - field: user_id
      generator: uuid
```

### Von Traefik zu Envoy

**Traefik (keine native Unterstützung):**
```yaml
# Custom Middleware erforderlich
```

**Envoy (Lua Filter):**
```yaml
transformation:
  enabled: true
  defaults:
    status: "active"
  computed_fields:
    - field: request_id
      generator: uuid
```

## Python API-Referenz

Für Details zur Implementierung siehe:

- `gal/config.py` - Transformation, ComputedField, Validation Dataclasses
- `gal/providers/envoy.py:112-177` - Envoy Lua Filter Generierung
- `gal/providers/apisix.py:159-218` - APISIX Lua Script Generierung
- `gal/providers/kong.py:134-141` - Kong Plugin-Konfiguration
- `gal/providers/traefik.py:142-152` - Traefik Middleware-Konfiguration

## Siehe auch

- [Provider-Dokumentation](PROVIDERS.md) - Provider-spezifische Details
- [Konfigurationsreferenz](../api/CONFIGURATION.md) - Vollständige YAML-Optionen
- [Schnellstart-Guide](QUICKSTART.md) - Praktische Beispiele
- [Entwickler-Guide](DEVELOPMENT.md) - Custom Transformations entwickeln
