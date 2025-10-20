# Azure API Management Import

**Status:** ✅ Vollständig implementiert
**Format:** OpenAPI 3.0 JSON/YAML
**Provider:** Azure API Management (APIM)
**Parser:** `AzureAPIMParser`

---

## Übersicht

Der Azure APIM Import ermöglicht das Importieren von Azure API Management APIs in das GAL-Format über **OpenAPI 3.0 Exports**.

### Was wird importiert?

✅ **API-Struktur:**
- API Titel, Version, Beschreibung
- Alle Pfade (Endpoints)
- HTTP-Methoden (GET, POST, PUT, DELETE, etc.)
- Backend-Server URLs

✅ **Security Schemes:**
- API Key Authentication (Subscription Keys)
- OAuth2 (Azure AD)
- OpenID Connect (Azure AD)

❌ **Nicht importiert:**
- Rate Limiting Policies (nur in ARM/Policy XML)
- Caching Policies (nur in ARM/Policy XML)
- Custom Policies (nur in ARM/Policy XML)
- Named Values / Secrets
- Products & Subscriptions

---

## Schnellstart

### 1. API aus Azure APIM exportieren

Verwende die Azure CLI, um eine API als OpenAPI 3.0 zu exportieren:

```bash
# Exportiere API als OpenAPI JSON
az apim api export \
  --api-id petstore-api \
  --resource-group myResourceGroup \
  --service-name myAPIManagement \
  --export-format OpenApiJsonFile \
  --file-path ./petstore-api.json

# Alternative: Exportiere als YAML
az apim api export \
  --api-id petstore-api \
  --resource-group myResourceGroup \
  --service-name myAPIManagement \
  --export-format OpenApiYamlFile \
  --file-path ./petstore-api.yaml
```

**Wichtig:** Der `--export-format` Parameter unterstützt:
- `OpenApiJsonFile` - OpenAPI 3.0 JSON (empfohlen)
- `OpenApiYamlFile` - OpenAPI 3.0 YAML
- `OpenApi` - OpenAPI 3.0 (URL, 5min gültig)

### 2. Importiere OpenAPI nach GAL

```bash
gal import-config \
  --provider azure_apim \
  --input petstore-api.json \
  --output gal-config.yaml
```

### 3. Generiere Config für Ziel-Provider

```bash
# Generiere Envoy Config
gal generate \
  --config gal-config.yaml \
  --provider envoy \
  --output envoy.yaml

# Oder Kong
gal generate \
  --config gal-config.yaml \
  --provider kong \
  --output kong.yaml
```

---

## Azure CLI Setup

### Installation

```bash
# Ubuntu/Debian
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# macOS
brew install azure-cli

# Windows
winget install Microsoft.AzureCLI
```

### Login & Setup

```bash
# Login
az login

# Setze Subscription (falls mehrere)
az account set --subscription "My Subscription"

# Liste alle API Management Services
az apim list --output table

# Liste alle APIs in einem APIM Service
az apim api list \
  --resource-group myResourceGroup \
  --service-name myAPIManagement \
  --output table
```

---

## Import-Beispiele

### Beispiel 1: Einfache API (nur Pfade)

**petstore-api.json:**
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Pet Store API",
    "version": "1.0.0"
  },
  "servers": [
    {"url": "https://petstore-backend.example.com"}
  ],
  "paths": {
    "/pets": {
      "get": {"summary": "List pets"},
      "post": {"summary": "Create pet"}
    },
    "/pets/{id}": {
      "get": {"summary": "Get pet"},
      "delete": {"summary": "Delete pet"}
    }
  }
}
```

**Import:**
```bash
gal import-config \
  --provider azure_apim \
  --input petstore-api.json \
  --output gal-config.yaml
```

**Ergebnis (gal-config.yaml):**
```yaml
version: "1.0"
services:
  - name: imported-api
    protocol: http
    upstream:
      targets:
        - host: petstore-backend.example.com
          port: 443
    routes:
      - path_prefix: /pets
        http_methods:
          - GET
          - POST
      - path_prefix: /pets/{id}
        http_methods:
          - GET
          - DELETE
```

---

### Beispiel 2: API mit Subscription Keys

**user-api.json:**
```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "User API",
    "version": "v1"
  },
  "servers": [
    {"url": "https://backend.example.com:8080"}
  ],
  "paths": {
    "/api/users": {
      "get": {
        "summary": "Get users",
        "security": [{"apiKey": []}]
      }
    }
  },
  "components": {
    "securitySchemes": {
      "apiKey": {
        "type": "apiKey",
        "name": "Ocp-Apim-Subscription-Key",
        "in": "header"
      }
    }
  }
}
```

**Ergebnis:**
```yaml
version: "1.0"
services:
  - name: imported-api
    protocol: http
    upstream:
      targets:
        - host: backend.example.com
          port: 8080
    routes:
      - path_prefix: /api/users
        http_methods:
          - GET
        authentication:
          type: api_key
          api_key:
            key_name: Ocp-Apim-Subscription-Key
            in_location: header
```

---

### Beispiel 3: API mit Azure AD OAuth2

**admin-api.json:**
```json
{
  "openapi": "3.0.2",
  "info": {
    "title": "Admin API",
    "version": "2.0.0"
  },
  "servers": [
    {"url": "https://admin-backend.example.com"}
  ],
  "paths": {
    "/api/admin/users": {
      "delete": {
        "summary": "Delete user",
        "security": [{"oauth2": ["admin"]}]
      }
    }
  },
  "components": {
    "securitySchemes": {
      "oauth2": {
        "type": "oauth2",
        "flows": {
          "implicit": {
            "authorizationUrl": "https://login.microsoftonline.com/tenant-id/oauth2/authorize",
            "scopes": {"admin": "Admin access"}
          }
        }
      }
    }
  }
}
```

**Ergebnis:**
```yaml
version: "1.0"
services:
  - name: imported-api
    protocol: http
    upstream:
      targets:
        - host: admin-backend.example.com
          port: 443
    routes:
      - path_prefix: /api/admin/users
        http_methods:
          - DELETE
        authentication:
          type: jwt
          jwt_config:
            issuer: https://login.microsoftonline.com/tenant-id
            # audience muss manuell konfiguriert werden
```

---

## Python API

### Programmatischer Import

```python
from gal.providers.azure_apim import AzureAPIMProvider

# OpenAPI JSON lesen
with open("petstore-api.json") as f:
    openapi_content = f.read()

# Azure APIM Provider erstellen
provider = AzureAPIMProvider()

# OpenAPI zu GAL importieren
config = provider.parse(openapi_content)

# GAL Config speichern
from gal.config import save_config
save_config(config, "gal-config.yaml")

# Zu anderem Provider migrieren
from gal.providers.envoy import EnvoyProvider
envoy_provider = EnvoyProvider()
envoy_config = envoy_provider.generate(config)

with open("envoy.yaml", "w") as f:
    f.write(envoy_config)
```

### Parser direkt verwenden

```python
from gal.parsers.azure_apim_parser import AzureAPIMParser

# Parser erstellen
parser = AzureAPIMParser()

# OpenAPI parsen
api = parser.parse(openapi_content, api_id="my-api")

# API-Informationen extrahieren
print(f"API: {api.title} v{api.version}")
print(f"Backend: {parser.extract_backend_url(api)}")

# Routes extrahieren
routes = parser.extract_routes(api)
for route in routes:
    print(f"{route['path']}: {route['methods']}")

# Authentication extrahieren
auth = parser.extract_authentication(api)
if auth:
    print(f"Auth Type: {auth['type']}")
```

---

## Unterstützte Features

| Feature | Importiert | Hinweise |
|---------|-----------|----------|
| **API-Struktur** |
| Titel, Version, Beschreibung | ✅ | Aus `info` Objekt |
| Pfade (Endpoints) | ✅ | Alle Pfade aus `paths` |
| HTTP-Methoden | ✅ | GET, POST, PUT, DELETE, PATCH, etc. |
| Backend URL | ✅ | Aus `servers[0].url` |
| **Security** |
| API Key (Subscription Keys) | ✅ | → `api_key` Authentication |
| OAuth2 (Azure AD) | ✅ | → `jwt` Authentication (issuer extrahiert) |
| OpenID Connect | ✅ | → `jwt` Authentication |
| **Policies** |
| Rate Limiting | ❌ | Nur in ARM/Policy XML verfügbar |
| Caching | ❌ | Nur in ARM/Policy XML verfügbar |
| Transformations | ❌ | Nur in ARM/Policy XML verfügbar |
| Custom Policies | ❌ | Nur in ARM/Policy XML verfügbar |
| **Azure-Features** |
| Products & Subscriptions | ❌ | Nicht in OpenAPI enthalten |
| Named Values | ❌ | Nicht in OpenAPI enthalten |
| Developer Portal | ❌ | Nicht relevant für Import |

---

## Limitierungen

### 1. Policies nicht in OpenAPI

Azure APIM **Policies** (rate limiting, caching, transformations) sind **NICHT** in OpenAPI Exports enthalten. Sie werden nur in den folgenden Formaten gespeichert:

- **ARM Templates** (`Microsoft.ApiManagement/service/apis/operations/policies`)
- **Policy XML** (separate Policy-Dateien)

**Workaround:**
- Konfiguriere Rate Limiting manuell in GAL nach dem Import
- Oder: Exportiere ARM Template zusätzlich und parse Policy XML (Future Enhancement)

### 2. Audience für JWT fehlt

OpenAPI 3.0 enthält **keine** `audience` Informationen für OAuth2/OpenID Connect.

**Workaround:**
```yaml
# Nach Import manuell hinzufügen
authentication:
  type: jwt
  jwt_config:
    issuer: https://login.microsoftonline.com/tenant-id
    audience: api://my-api-id  # <-- Manuell hinzufügen
```

### 3. Named Values nicht verfügbar

Azure APIM **Named Values** (früher "Properties") sind **nicht** in OpenAPI Exports enthalten.

**Workaround:**
- Ersetze Named Values nach Export manuell
- Oder: Verwende GAL Template-Variablen

### 4. Products nicht importiert

Azure APIM **Products** (Gruppierungen von APIs mit Subscription Keys) sind **nicht** in OpenAPI enthalten.

**Workaround:**
- Konfiguriere Products manuell in der Ziel-Gateway-Umgebung

---

## Troubleshooting

### Problem: "Unsupported OpenAPI version"

**Symptom:**
```
ValueError: Unsupported OpenAPI version: 2.0. Only OpenAPI 3.x is supported.
```

**Ursache:** Du hast ein **Swagger 2.0** Dokument statt OpenAPI 3.0.

**Lösung:** Exportiere als OpenAPI 3.0:
```bash
az apim api export \
  --export-format OpenApiJsonFile \  # NICHT Swagger20
  ...
```

---

### Problem: "No backend URL found"

**Symptom:**
```
WARNING: No backend URL found in OpenAPI spec
```

**Ursache:** Keine `servers` im OpenAPI Dokument.

**Lösung 1:** Füge `servers` manuell hinzu:
```json
{
  "openapi": "3.0.0",
  "servers": [
    {"url": "https://backend.example.com"}
  ],
  ...
}
```

**Lösung 2:** Ignoriere die Warnung - GAL verwendet `https://backend.example.com` als Default.

---

### Problem: "Rate limiting not imported"

**Symptom:** Rate Limiting Policies fehlen in der importierten Config.

**Ursache:** Policies sind **nicht** in OpenAPI Exports enthalten.

**Lösung:** Konfiguriere Rate Limiting manuell nach Import:
```yaml
services:
  - name: imported-api
    routes:
      - path_prefix: /api/users
        rate_limiting:
          requests_per_second: 100
          burst: 200
```

---

### Problem: "JWT audience missing"

**Symptom:** JWT `audience` ist `null` in der importierten Config.

**Ursache:** OpenAPI 3.0 enthält keine `audience` Informationen.

**Lösung:** Füge `audience` manuell hinzu:
```yaml
authentication:
  type: jwt
  jwt_config:
    issuer: https://login.microsoftonline.com/tenant-id
    audience: api://my-api-id  # <-- Hinzufügen
```

---

## Best Practices

### 1. ✅ Verifiziere Backend URL

Nach dem Import, prüfe ob Backend URL korrekt ist:

```bash
# Prüfe gal-config.yaml
grep -A 5 "upstream:" gal-config.yaml
```

Erwartete Ausgabe:
```yaml
upstream:
  targets:
    - host: backend.example.com
      port: 443
```

---

### 2. ✅ Konfiguriere Authentication Audience

Für JWT Authentication, **immer** `audience` hinzufügen:

```yaml
authentication:
  type: jwt
  jwt_config:
    issuer: https://login.microsoftonline.com/YOUR-TENANT-ID
    audience: api://YOUR-API-ID  # <-- Wichtig!
```

---

### 3. ✅ Füge Policies manuell hinzu

Nach Import, konfiguriere fehlende Policies:

```yaml
routes:
  - path_prefix: /api/users
    # Rate Limiting
    rate_limiting:
      requests_per_second: 100
      burst: 200
    # Caching
    # ... (falls benötigt)
```

---

### 4. ✅ Teste Import mit gal validate

```bash
# Nach Import validieren
gal validate --config gal-config.yaml
```

---

### 5. ✅ Migriere zu mehreren Providern

```bash
# Import from Azure APIM
gal import-config \
  --provider azure_apim \
  --input azure-api.json \
  --output gal-config.yaml

# Generate for multiple targets
gal generate-all \
  --config gal-config.yaml \
  --output ./configs/
```

---

## Zusammenfassung

### ✅ Was funktioniert:
- OpenAPI 3.0 Import (JSON/YAML)
- API-Struktur (Pfade, Methoden, Backend)
- Security Schemes (API Key, OAuth2, OpenID Connect)
- Multi-Path APIs
- Azure AD Integration

### ⚠️ Was manuell konfiguriert werden muss:
- Rate Limiting Policies
- Caching Policies
- JWT `audience`
- Named Values
- Products & Subscriptions

### 📊 Empfohlener Workflow:
1. Exportiere API mit `az apim api export --export-format OpenApiJsonFile`
2. Importiere nach GAL mit `gal import-config --provider azure_apim`
3. Füge fehlende Policies manuell hinzu (rate limiting, etc.)
4. Validiere Config mit `gal validate`
5. Generiere Config für Ziel-Provider mit `gal generate`

---

**Version:** 1.4.0
**Status:** ✅ Production Ready
**Letzte Aktualisierung:** 2025-10-20
