# Body Transformation - Request/Response Body Manipulation

**Request- und Response-Body-Transformation** ermöglicht die Manipulation von JSON-Payloads während der Verarbeitung durch das Gateway.

## Inhaltsverzeichnis

- [Übersicht](#ubersicht)
- [Schnellstart](#schnellstart)
- [Konfigurationsoptionen](#konfigurationsoptionen)
- [Provider-Implementierungen](#provider-implementierungen)
- [Häufige Anwendungsfälle](#haufige-anwendungsfalle)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Provider-Vergleich](#provider-vergleich)

---

## Übersicht

### Was ist Body Transformation?

Body Transformation erlaubt die Manipulation von Request- und Response-Bodys auf Gateway-Ebene:

**Request Transformation:**
- **Add Fields**: Felder hinzufügen (z.B. `trace_id`, `timestamp`)
- **Remove Fields**: Sensitive Felder entfernen (z.B. `internal_id`, `secret`)
- **Rename Fields**: Felder umbenennen (z.B. `user_id` → `id`)

**Response Transformation:**
- **Filter Fields**: Sensitive Felder filtern (z.B. `password`, `ssn`)
- **Add Fields**: Metadata hinzufügen (z.B. `server_time`, `api_version`)

### Template-Variablen

GAL unterstützt dynamische Werte:

| Variable | Beschreibung | Beispiel |
|----------|--------------|----------|
| `{{uuid}}` | Generiert UUID v4 | `550e8400-e29b-41d4-a716-446655440000` |
| `{{now}}` | Aktueller Timestamp (ISO 8601) | `2025-01-18T14:30:00Z` |
| `{{timestamp}}` | Alias für `{{now}}` | `2025-01-18T14:30:00Z` |

### Wann verwenden?

✅ **Verwenden bei:**
- Trace-IDs für Distributed Tracing hinzufügen
- Sensitive Daten aus Responses filtern
- API-Versionierung über Metadata
- Legacy-System-Integration (Field Mapping)
- Audit-Logging-Informationen hinzufügen

❌ **Nicht verwenden bei:**
- Komplexen Business-Logic-Transformationen
- Verschlüsselung/Entschlüsselung (nutze TLS)
- Großen Payloads (Performance-Impact)

---

## Schnellstart

### Beispiel 1: Trace-ID hinzufügen

```yaml
services:
  - name: api_service
    protocol: http
    upstream:
      host: api.internal
      port: 8080
    routes:
      - path_prefix: /api/users
        body_transformation:
          enabled: true
          request:
            add_fields:
              trace_id: "{{uuid}}"
              timestamp: "{{now}}"
```

**Ergebnis:**
```json
// Original Request
{"username": "alice", "email": "alice@example.com"}

// Transformed Request
{
  "username": "alice",
  "email": "alice@example.com",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-01-18T14:30:00Z"
}
```

### Beispiel 2: Sensitive Felder entfernen

```yaml
routes:
  - path_prefix: /api/users
    body_transformation:
      enabled: true
      request:
        remove_fields:
          - internal_id
          - secret_key
```

**Ergebnis:**
```json
// Original Request
{"username": "alice", "internal_id": "INT123", "secret_key": "abc"}

// Transformed Request
{"username": "alice"}
```

### Beispiel 3: Response-Felder filtern

```yaml
routes:
  - path_prefix: /api/users/{id}
    body_transformation:
      enabled: true
      response:
        filter_fields:
          - password
          - ssn
        add_fields:
          server_time: "{{timestamp}}"
```

**Ergebnis:**
```json
// Original Response
{"id": 1, "username": "alice", "password": "hashed", "ssn": "123-45-6789"}

// Transformed Response
{
  "id": 1,
  "username": "alice",
  "server_time": "2025-01-18T14:30:00Z"
}
```

---

## Konfigurationsoptionen

### BodyTransformationConfig

```yaml
body_transformation:
  enabled: true              # Body Transformation aktivieren
  request:                   # Request-Transformation (optional)
    add_fields:              # Felder hinzufügen
      field_name: "value"
      trace_id: "{{uuid}}"
    remove_fields:           # Felder entfernen
      - field_to_remove
    rename_fields:           # Felder umbenennen
      old_name: new_name
  response:                  # Response-Transformation (optional)
    filter_fields:           # Sensitive Felder filtern
      - password
      - ssn
    add_fields:              # Metadata hinzufügen
      server_time: "{{timestamp}}"
```

### Request Transformation

#### `add_fields` (Dict[str, Any])

Felder zum Request-Body hinzufügen. Unterstützt Template-Variablen.

```yaml
request:
  add_fields:
    trace_id: "{{uuid}}"           # Dynamisch: UUID
    timestamp: "{{now}}"           # Dynamisch: Timestamp
    api_version: "v1"              # Statisch: String
    priority: 1                    # Statisch: Integer
    enabled: true                  # Statisch: Boolean
```

#### `remove_fields` (List[str])

Felder aus dem Request-Body entfernen.

```yaml
request:
  remove_fields:
    - internal_id      # Interne IDs
    - secret_key       # Secrets
    - password         # Passwörter
    - debug_info       # Debug-Informationen
```

#### `rename_fields` (Dict[str, str])

Felder im Request-Body umbenennen (Field Mapping).

```yaml
request:
  rename_fields:
    user_id: id               # user_id → id
    user_name: name           # user_name → name
    user_email: email         # user_email → email
    created_at: timestamp     # created_at → timestamp
```

**Hinweis:** Nicht alle Provider unterstützen `rename_fields` nativ. Siehe [Provider-Vergleich](#provider-vergleich).

### Response Transformation

#### `filter_fields` (List[str])

Sensitive Felder aus dem Response-Body entfernen.

```yaml
response:
  filter_fields:
    - password             # Passwörter
    - ssn                  # Social Security Numbers
    - credit_card          # Kreditkarten-Nummern
    - api_key              # API Keys
    - internal_notes       # Interne Notizen
```

#### `add_fields` (Dict[str, Any])

Metadata-Felder zum Response-Body hinzufügen.

```yaml
response:
  add_fields:
    server_time: "{{timestamp}}"    # Server-Timestamp
    server_id: "gateway-1"          # Server-ID
    api_version: "v1.2.0"           # API-Version
    response_id: "{{uuid}}"         # Response-ID
```

---

## Provider-Implementierungen

### 1. Envoy - Lua Filter (100% Support)

**Implementierung:** envoy.filters.http.lua

**Konfiguration:**
```yaml
# GAL Config
body_transformation:
  enabled: true
  request:
    add_fields:
      trace_id: "{{uuid}}"
```

**Generierte Envoy Config:**
```yaml
http_filters:
  - name: envoy.filters.http.lua
    typed_config:
      '@type': type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
      inline_code: |
        local cjson = require('cjson')

        function generate_uuid()
          -- UUID v4 generation
        end

        function envoy_on_request(request_handle)
          local body = request_handle:body()
          if body and body:length() > 0 then
            local body_json = cjson.decode(body:getBytes(0, body:length()))
            body_json.trace_id = generate_uuid()
            request_handle:body():setBytes(cjson.encode(body_json))
          end
        end
```

**Features:**
- ✅ Add Fields (inkl. Template-Variablen)
- ✅ Remove Fields
- ✅ Rename Fields
- ✅ Filter Fields (Response)
- ✅ Add Fields (Response)

**Template-Variablen:**
- `{{uuid}}` → `generate_uuid()` (Lua-Funktion)
- `{{now}}` / `{{timestamp}}` → `os.date('%Y-%m-%dT%H:%M:%SZ')`

### 2. Kong - Transformer Plugins (95% Support)

**Implementierung:** request-transformer & response-transformer Plugins

**Konfiguration:**
```yaml
# GAL Config
body_transformation:
  enabled: true
  request:
    add_fields:
      trace_id: "{{uuid}}"
    remove_fields:
      - secret
```

**Generierte Kong Config:**
```yaml
plugins:
  - name: request-transformer
    config:
      add:
        json:
          - trace_id:$(uuid())
      remove:
        json:
          - secret
```

**Features:**
- ✅ Add Fields
- ✅ Remove Fields
- ⚠️ Rename Fields (benötigt custom Lua Plugin)
- ✅ Filter Fields (Response)
- ✅ Add Fields (Response)

**Template-Variablen:**
- `{{uuid}}` → `$(uuid())` (Kong-Funktion, falls verfügbar)
- `{{now}}` / `{{timestamp}}` → `$(date())`

**Limitation:** Kong's `request-transformer` Plugin unterstützt `rename_fields` nicht nativ. GAL loggt eine Warnung und empfiehlt ein custom Lua Plugin.

### 3. APISIX - Serverless Functions (100% Support)

**Implementierung:** serverless-pre-function & serverless-post-function

**Konfiguration:**
```yaml
# GAL Config
body_transformation:
  enabled: true
  request:
    add_fields:
      request_id: "{{uuid}}"
  response:
    filter_fields:
      - password
```

**Generierte APISIX Config:**
```json
{
  "plugins": {
    "serverless-pre-function": {
      "phase": "rewrite",
      "functions": [
        "return function(conf, ctx)\n  local core = require('apisix.core')\n  local cjson = require('cjson.safe')\n  local body = core.request.get_body()\n  if body then\n    local json_body = cjson.decode(body)\n    json_body.request_id = core.utils.uuid()\n    ngx.req.set_body_data(cjson.encode(json_body))\n  end\nend"
      ]
    },
    "serverless-post-function": {
      "phase": "body_filter",
      "functions": [
        "return function(conf, ctx)\n  local cjson = require('cjson.safe')\n  local chunk = ngx.arg[1]\n  if chunk then\n    local body_json = cjson.decode(chunk)\n    body_json.password = nil\n    ngx.arg[1] = cjson.encode(body_json)\n  end\nend"
      ]
    }
  }
}
```

**Features:**
- ✅ Add Fields
- ✅ Remove Fields
- ✅ Rename Fields
- ✅ Filter Fields (Response)
- ✅ Add Fields (Response)

**Template-Variablen:**
- `{{uuid}}` → `core.utils.uuid()`
- `{{now}}` / `{{timestamp}}` → `os.date('%Y-%m-%dT%H:%M:%SZ')`

### 4. Traefik - Nicht unterstützt (0% Support)

**Implementierung:** Keine native Unterstützung

Traefik unterstützt Body Transformation **nicht nativ**. GAL generiert eine **Warnung** mit Alternativen:

```
WARNING: Body transformation configured for api_service//api/users,
but Traefik does not natively support request/response body transformation.

Consider using:
  1. ForwardAuth middleware with external transformation service
  2. Custom Traefik plugin (requires Go development)
  3. Alternative provider (Envoy, Kong, APISIX, Nginx, HAProxy)
```

**Alternativen:**

**Option 1: ForwardAuth Middleware**
```yaml
middlewares:
  transformation:
    forwardAuth:
      address: "http://transform-service:8080"
      authRequestHeaders:
        - "Content-Type"
```

Externer Transformation-Service (Python/Go/Node.js) übernimmt Body Transformation.

**Option 2: Custom Traefik Plugin (Go)**

Entwickle ein Traefik Plugin in Go:
```go
// plugins-local/src/github.com/username/transform/transform.go
package transform

import (
    "context"
    "encoding/json"
    "io"
    "net/http"
)

type Config struct {
    AddFields map[string]interface{} `json:"addFields,omitempty"`
}

func (t *Transform) ServeHTTP(rw http.ResponseWriter, req *http.Request) {
    body, _ := io.ReadAll(req.Body)
    var jsonBody map[string]interface{}
    json.Unmarshal(body, &jsonBody)

    // Add fields
    for key, value := range t.config.AddFields {
        jsonBody[key] = value
    }

    newBody, _ := json.Marshal(jsonBody)
    req.Body = io.NopCloser(bytes.NewReader(newBody))
    t.next.ServeHTTP(rw, req)
}
```

### 5. Nginx - OpenResty Lua (100% Support)

**Implementierung:** access_by_lua_block & body_filter_by_lua_block

**Voraussetzung:** OpenResty (Nginx + Lua)

**Konfiguration:**
```yaml
# GAL Config
body_transformation:
  enabled: true
  request:
    add_fields:
      request_id: "{{uuid}}"
```

**Generierte Nginx Config:**
```nginx
location /api/users {
    # Request body transformation (requires OpenResty)
    access_by_lua_block {
        local cjson = require('cjson')
        ngx.req.read_body()
        local body_data = ngx.req.get_body_data()
        if body_data then
            local body_json = cjson.decode(body_data)
            body_json.request_id = ngx.var.request_id
            ngx.req.set_body_data(cjson.encode(body_json))
        end
    }

    # Response body transformation
    body_filter_by_lua_block {
        local cjson = require('cjson')
        local chunk = ngx.arg[1]
        if chunk then
            local body_json = cjson.decode(chunk)
            body_json.password = nil
            ngx.arg[1] = cjson.encode(body_json)
        end
    }

    proxy_pass http://upstream_api_service;
}
```

**Features:**
- ✅ Add Fields
- ✅ Remove Fields
- ✅ Rename Fields
- ✅ Filter Fields (Response)
- ✅ Add Fields (Response)

**Template-Variablen:**
- `{{uuid}}` → `ngx.var.request_id`
- `{{now}}` / `{{timestamp}}` → `ngx.utctime()`

**Installation:**
```bash
# Ubuntu/Debian
apt-get install openresty

# macOS
brew install openresty/brew/openresty
```

### 6. HAProxy - Lua Scripting (90% Support)

**Implementierung:** Lua-Funktionen (manuell implementiert)

**Konfiguration:**
```yaml
# GAL Config
body_transformation:
  enabled: true
  request:
    add_fields:
      trace_id: "{{uuid}}"
```

**Generierte HAProxy Config:**
```haproxy
frontend http_frontend
    # Body transformation for /api/users (requires Lua)
    http-request lua.transform_request_api_service_route0 if is_api_service_route0
    http-response lua.transform_response_api_service_route0 if is_api_service_route0
```

**Lua-Implementierung (manuell):**

GAL generiert **Funktionsreferenzen**, aber du musst die Lua-Funktionen selbst implementieren:

```lua
-- /etc/haproxy/transform.lua
core.register_action("transform_request_api_service_route0", {"http-req"}, function(txn)
    local json = require("json")
    local body = txn.req:dup():get_body()

    if body then
        local data = json.decode(body)
        data.trace_id = core.uuid()
        data.timestamp = os.date("!%Y-%m-%dT%H:%M:%SZ")
        txn.req:set_body_data(json.encode(data))
    end
end)

core.register_action("transform_response_api_service_route0", {"http-res"}, function(txn)
    local json = require("json")
    local body = txn.res:dup():get_body()

    if body then
        local data = json.decode(body)
        data.password = nil
        txn.res:set_body_data(json.encode(data))
    end
end)
```

**HAProxy Global Config:**
```haproxy
global
    lua-load /etc/haproxy/transform.lua
```

**Features:**
- ✅ Add Fields (manuell implementieren)
- ✅ Remove Fields (manuell implementieren)
- ✅ Rename Fields (manuell implementieren)
- ✅ Filter Fields (Response, manuell)
- ✅ Add Fields (Response, manuell)

**Warnung:** GAL loggt eine Warnung mit Implementierungshinweisen.

---

## Häufige Anwendungsfälle

### 1. Distributed Tracing - Trace-IDs hinzufügen

**Use Case:** Jeder Request bekommt eine eindeutige Trace-ID für End-to-End-Tracking.

```yaml
routes:
  - path_prefix: /api
    body_transformation:
      enabled: true
      request:
        add_fields:
          trace_id: "{{uuid}}"
          request_time: "{{timestamp}}"
      response:
        add_fields:
          response_time: "{{timestamp}}"
```

**Vorteile:**
- ✅ Einfaches Request-Tracking über Microservices
- ✅ Korrelation von Logs
- ✅ Performance-Monitoring

### 2. Legacy-System-Integration - Field Mapping

**Use Case:** Legacy-System erwartet alte Feldnamen.

```yaml
routes:
  - path_prefix: /legacy/users
    body_transformation:
      enabled: true
      request:
        rename_fields:
          id: userId
          name: userName
          email: userEmail
          created: createdAt
```

**Original Request:**
```json
{"id": 1, "name": "Alice", "email": "alice@example.com"}
```

**Transformed Request:**
```json
{"userId": 1, "userName": "Alice", "userEmail": "alice@example.com"}
```

### 3. Security - Sensitive Daten filtern

**Use Case:** PII (Personally Identifiable Information) aus Responses entfernen.

```yaml
routes:
  - path_prefix: /api/users
    body_transformation:
      enabled: true
      response:
        filter_fields:
          - password
          - ssn
          - credit_card
          - api_key
          - internal_notes
```

**Original Response:**
```json
{
  "id": 1,
  "username": "alice",
  "password": "hashed_password",
  "ssn": "123-45-6789",
  "email": "alice@example.com"
}
```

**Transformed Response:**
```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com"
}
```

### 4. API Versioning - Metadata hinzufügen

**Use Case:** API-Version und Server-Informationen zu Responses hinzufügen.

```yaml
routes:
  - path_prefix: /api/v1
    body_transformation:
      enabled: true
      response:
        add_fields:
          api_version: "v1.2.0"
          server: "gateway-1"
          timestamp: "{{timestamp}}"
```

### 5. Audit Logging - Audit-Informationen

**Use Case:** Audit-Trail-Informationen zu Requests hinzufügen.

```yaml
routes:
  - path_prefix: /api/admin
    body_transformation:
      enabled: true
      request:
        add_fields:
          audit_id: "{{uuid}}"
          audit_timestamp: "{{timestamp}}"
          gateway: "gal-gateway-1"
      response:
        add_fields:
          audit_response_time: "{{timestamp}}"
```

### 6. Canary Deployment - Version-Flag

**Use Case:** Requests für Canary-Deployment markieren.

```yaml
routes:
  - path_prefix: /api/v2-beta
    body_transformation:
      enabled: true
      request:
        add_fields:
          deployment: "canary"
          version: "v2-beta"
          canary_weight: 10
```

### 7. Multi-Tenant - Tenant-ID hinzufügen

**Use Case:** Tenant-ID basierend auf Header hinzufügen.

```yaml
routes:
  - path_prefix: /api/tenant
    body_transformation:
      enabled: true
      request:
        add_fields:
          tenant_id: "extracted-from-header"  # In Produktion: Lua/Custom Logic
          tenant_region: "eu-west-1"
```

---

## Best Practices

### 1. ✅ Minimale Transformation

**Regel:** Transformiere nur, was wirklich nötig ist.

❌ **Schlecht:**
```yaml
request:
  add_fields:
    field1: "value1"
    field2: "value2"
    field3: "value3"
    field4: "value4"
    field5: "value5"
```

✅ **Gut:**
```yaml
request:
  add_fields:
    trace_id: "{{uuid}}"  # Nur für Tracing
```

**Grund:** Jede Transformation hat Performance-Impact (JSON decode/encode).

### 2. ✅ Template-Variablen verwenden

**Regel:** Nutze `{{uuid}}` und `{{timestamp}}` für dynamische Werte.

❌ **Schlecht:**
```yaml
request:
  add_fields:
    trace_id: "static-value"  # Immer gleich!
```

✅ **Gut:**
```yaml
request:
  add_fields:
    trace_id: "{{uuid}}"  # Eindeutig pro Request
```

### 3. ✅ Provider-Kompatibilität prüfen

**Regel:** Verwende Features, die dein Provider unterstützt.

```yaml
# Kong unterstützt rename_fields NICHT nativ
request:
  rename_fields:  # ⚠️ Warnung bei Kong!
    old: new
```

**Lösung:** Nutze [Provider-Vergleich](#provider-vergleich) vor der Implementierung.

### 4. ✅ Response-Filterung für Security

**Regel:** Filtere IMMER sensitive Daten aus Responses.

```yaml
response:
  filter_fields:
    - password
    - ssn
    - credit_card
    - api_key
    - secret
    - internal_notes
```

### 5. ✅ Testing mit echten Payloads

**Regel:** Teste Transformationen mit realistischen Payloads.

```bash
# Test Request
curl -X POST http://gateway/api/users \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "internal_id": "INT123"}'

# Check transformed request im Backend
```

### 6. ✅ Monitoring & Logging

**Regel:** Überwache Transformation-Fehler.

```yaml
# Envoy: Lua-Fehler landen in Envoy-Logs
# Kong: Plugin-Errors in Kong-Logs
# APISIX: Serverless-Function-Errors in error.log
```

**Metric-Beispiele:**
- `body_transformation_errors_total`
- `body_transformation_duration_seconds`

### 7. ✅ Dokumentiere Custom Lua

**Regel:** Wenn du custom Lua verwendest (HAProxy, Nginx), dokumentiere es!

```lua
-- /etc/haproxy/transform.lua
-- Purpose: Transform request body for api_service
-- Author: DevOps Team
-- Date: 2025-01-18
-- Dependencies: lua-json

core.register_action("transform_request_api_service_route0", {"http-req"}, function(txn)
    -- Implementation...
end)
```

---

## Troubleshooting

### Problem 1: Transformation funktioniert nicht

**Symptom:** Body wird nicht transformiert.

**Debugging:**

1. **Check Provider-Logs:**
```bash
# Envoy
kubectl logs -f envoy-pod | grep lua

# Kong
tail -f /usr/local/kong/logs/error.log

# APISIX
tail -f /usr/local/apisix/logs/error.log

# Nginx (OpenResty)
tail -f /var/log/nginx/error.log
```

2. **Check Config-Syntax:**
```bash
# Envoy
envoy --mode validate -c envoy.yaml

# Kong
kong config parse kong.yaml

# Nginx
nginx -t -c nginx.conf
```

3. **Check JSON-Parsing:**
```bash
# Teste ob Request/Response valides JSON ist
echo '{"test": "value"}' | jq .
```

**Häufige Ursachen:**
- ❌ Request/Response ist kein JSON
- ❌ Lua-Module fehlen (cjson)
- ❌ Provider unterstützt Feature nicht

### Problem 2: Template-Variablen werden nicht ersetzt

**Symptom:** `{{uuid}}` bleibt als String im Body.

**Lösung:**

Check Provider-Implementation:

**Envoy:**
```lua
-- Muss generate_uuid() Funktion haben
function generate_uuid()
  -- Implementation
end
```

**APISIX:**
```lua
-- Muss core.utils.uuid() verwenden
body_json.trace_id = core.utils.uuid()
```

**Kong:**
```yaml
# Kong: $(uuid()) statt {{uuid}}
add:
  json:
    - trace_id:$(uuid())
```

### Problem 3: Performance-Degradation

**Symptom:** Gateway-Response-Zeit steigt signifikant.

**Debugging:**

1. **Measure Transformation-Overhead:**
```bash
# Ohne Transformation
ab -n 1000 -c 10 http://gateway/api/users

# Mit Transformation
ab -n 1000 -c 10 http://gateway/api/users-transformed
```

2. **Profile Lua-Code (Envoy):**
```lua
function envoy_on_request(request_handle)
    local start_time = os.clock()
    -- Transformation logic
    local duration = os.clock() - start_time
    request_handle:logInfo("Transformation took: " .. duration .. "s")
end
```

**Optimierungen:**
- ✅ Reduziere Anzahl der transformierten Felder
- ✅ Cache Lua-Module (cjson)
- ✅ Nutze lightweight JSON-Parser
- ✅ Erwäge Transformation im Backend

### Problem 4: rename_fields funktioniert nicht (Kong)

**Symptom:** Kong loggt Warnung über `rename_fields`.

**Lösung:**

Kong's `request-transformer` Plugin unterstützt `rename_fields` nicht nativ.

**Option 1: Custom Lua Plugin**
```lua
-- kong/plugins/rename-transformer/handler.lua
local kong = kong
local cjson = require("cjson")

local RenameTransformer = {}

function RenameTransformer:access(conf)
    local body = kong.request.get_raw_body()
    if body then
        local json_body = cjson.decode(body)

        for old_name, new_name in pairs(conf.rename_fields) do
            if json_body[old_name] ~= nil then
                json_body[new_name] = json_body[old_name]
                json_body[old_name] = nil
            end
        end

        kong.service.request.set_raw_body(cjson.encode(json_body))
    end
end

return RenameTransformer
```

**Option 2: Alternative Provider**

Nutze Envoy, APISIX oder Nginx statt Kong für `rename_fields`.

### Problem 5: Traefik-Warnung

**Symptom:** GAL loggt Warnung "Traefik does not natively support...".

**Lösung:**

Traefik unterstützt Body Transformation nicht nativ. Optionen:

1. **ForwardAuth + Externer Service**
2. **Custom Traefik Plugin (Go)**
3. **Alternative Provider (Envoy, Kong, etc.)**

Siehe [Traefik-Implementierung](#4-traefik-nicht-unterstutzt-0-support).

### Problem 6: HAProxy Lua-Script nicht gefunden

**Symptom:** HAProxy startet nicht: "lua-load /path/to/transform.lua: No such file".

**Lösung:**

1. **Create Lua-Script:**
```bash
mkdir -p /etc/haproxy
cat > /etc/haproxy/transform.lua << 'EOF'
-- Transformation functions
core.register_action("transform_request_api_service_route0", {"http-req"}, function(txn)
    -- Implementation
end)
EOF
```

2. **Update haproxy.cfg:**
```haproxy
global
    lua-load /etc/haproxy/transform.lua
```

3. **Restart HAProxy:**
```bash
systemctl restart haproxy
```

---

## Provider-Vergleich

### Feature-Matrix

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy |
|---------|-------|------|--------|---------|-------|---------|
| **Request Transformation** |
| Add Fields | ✅ Lua | ✅ Plugin | ✅ Lua | ❌ | ✅ Lua | ⚠️ Manual Lua |
| Remove Fields | ✅ Lua | ✅ Plugin | ✅ Lua | ❌ | ✅ Lua | ⚠️ Manual Lua |
| Rename Fields | ✅ Lua | ⚠️ Custom | ✅ Lua | ❌ | ✅ Lua | ⚠️ Manual Lua |
| **Response Transformation** |
| Filter Fields | ✅ Lua | ✅ Plugin | ✅ Lua | ❌ | ✅ Lua | ⚠️ Manual Lua |
| Add Fields | ✅ Lua | ✅ Plugin | ✅ Lua | ❌ | ✅ Lua | ⚠️ Manual Lua |
| **Template Variables** |
| {{uuid}} | ✅ | ⚠️ $(uuid()) | ✅ | ❌ | ✅ | ⚠️ Manual |
| {{timestamp}} | ✅ | ⚠️ $(date()) | ✅ | ❌ | ✅ | ⚠️ Manual |
| **Setup** |
| Configuration | ✅ Auto | ✅ Auto | ✅ Auto | ⚠️ Manual | ⚠️ OpenResty | ⚠️ Manual Lua |
| Performance | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | N/A | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Complexity | Medium | Low | Medium | High | Medium | High |

**Legende:**
- ✅ = Full native support
- ⚠️ = Partial support / requires setup
- ❌ = Not supported

### Empfehlungen

#### Bester Provider: **APISIX** 🏆
- ✅ 100% Feature-Support
- ✅ Beste Performance
- ✅ Einfache Konfiguration
- ✅ Native Template-Variablen

#### Für Kubernetes: **Envoy** 🚀
- ✅ 100% Feature-Support
- ✅ Best Practices mit Service Mesh (Istio)
- ✅ Robuste Lua-Implementation

#### Für Einfachheit: **Kong** 💡
- ✅ 95% Feature-Support (außer rename)
- ✅ Einfachste Konfiguration
- ✅ Großes Plugin-Ökosystem

#### Für Nginx-Nutzer: **Nginx + OpenResty** 🔧
- ✅ 100% Feature-Support
- ⚠️ Requires OpenResty Installation
- ✅ Gute Performance

#### **Nicht empfohlen:**
- ❌ **Traefik**: Keine native Unterstützung
- ⚠️ **HAProxy**: Manuelle Lua-Implementierung erforderlich

---

## Zusammenfassung

### ✅ Body Transformation ermöglicht:
- Request-Body-Manipulation (add/remove/rename fields)
- Response-Body-Filterung (sensitive data)
- Template-Variablen ({{uuid}}, {{timestamp}})
- Provider-agnostische Konfiguration

### 🎯 Best Practices:
1. Minimale Transformation für Performance
2. Template-Variablen für dynamische Werte
3. Provider-Kompatibilität prüfen
4. Response-Filterung für Security
5. Testing mit echten Payloads
6. Monitoring & Logging aktivieren
7. Custom Lua dokumentieren

### 📊 Provider-Empfehlungen:
- **APISIX**: Beste Wahl (100% Support, Top Performance)
- **Envoy**: Ideal für Kubernetes/Service Mesh
- **Kong**: Einfachste Setup (95% Support)
- **Nginx**: Gut mit OpenResty (100% Support)
- **Traefik**: ❌ Nicht empfohlen
- **HAProxy**: ⚠️ Nur mit Manual Lua

### 🔗 Weitere Ressourcen:
- [Body Transformation Examples](https://github.com/pt9912/x-gal/blob/main/examples/body-transformation-example.yaml)
- [Provider Documentation](PROVIDERS.md)
- [v1.2.0 Plan](../v1.2.0-PLAN.md)

---

**Version:** v1.2.0
**Zuletzt aktualisiert:** 2025-01-18
**Autor:** GAL Development Team
