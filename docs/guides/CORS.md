# CORS (Cross-Origin Resource Sharing) Anleitung

**Umfassende Anleitung für CORS-Policies in GAL (Gateway Abstraction Layer)**

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Schnellstart](#schnellstart)
3. [Konfigurationsoptionen](#konfigurationsoptionen)
4. [Provider-Implementierung](#provider-implementierung)
5. [Häufige Anwendungsfälle](#häufige-anwendungsfälle)
6. [Sicherheits-Best-Practices](#sicherheits-best-practices)
7. [CORS Testen](#cors-testen)
8. [Troubleshooting](#troubleshooting)

---

## Übersicht

CORS (Cross-Origin Resource Sharing) ist ein Sicherheitsmechanismus, der es Webanwendungen ermöglicht, Ressourcen von verschiedenen Ursprüngen (Origins) anzufordern. GAL bietet eine einheitliche CORS-Konfiguration für alle unterstützten Gateway-Provider.

### Was ist CORS?

CORS ermöglicht es Browsern, Cross-Origin-Requests durchzuführen, die normalerweise durch die Same-Origin-Policy blockiert würden. Beispiel:

- **Frontend:** `https://app.example.com`
- **API:** `https://api.example.com`

Ohne CORS würde der Browser die Requests vom Frontend zur API blockieren, da sie unterschiedliche Origins haben.

### Warum ist CORS wichtig?

- ✅ **Sicherheit**: Kontrolliert, welche Domains auf deine API zugreifen dürfen
- ✅ **Flexibilität**: Ermöglicht moderne Frontend-Architekturen (SPA, PWA)
- ✅ **Browser-Kompatibilität**: Funktioniert mit allen modernen Browsern
- ✅ **Credentials-Support**: Ermöglicht Cookies und Authentication headers

### Unterstützte Features

| Feature | Kong | APISIX | Traefik | Envoy | Beschreibung |
|---------|------|--------|---------|-------|--------------|
| **Allowed Origins** | ✅ | ✅ | ✅ | ✅ | Welche Origins dürfen zugreifen |
| **Allowed Methods** | ✅ | ✅ | ✅ | ✅ | Erlaubte HTTP-Methoden |
| **Allowed Headers** | ✅ | ✅ | ✅ | ✅ | Erlaubte Request-Headers |
| **Exposed Headers** | ✅ | ✅ | ✅ | ✅ | Headers die an Client zurückgegeben werden |
| **Credentials** | ✅ | ✅ | ✅ | ✅ | Cookies/Auth headers erlauben |
| **Max Age** | ✅ | ✅ | ✅ | ✅ | Preflight-Cache-Dauer |

---

## Schnellstart

### Einfache CORS-Konfiguration

Erlaube alle Origins (nur für Entwicklung!):

```yaml
version: "1.0"
provider: kong

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.example.com
      port: 8080
    routes:
      - path_prefix: /api
        methods: [GET, POST, OPTIONS]
        cors:
          enabled: true
          allowed_origins: ["*"]
          allowed_methods: [GET, POST, PUT, DELETE, OPTIONS]
          allowed_headers: [Content-Type, Authorization]
```

### Produktions-CORS-Konfiguration

Beschränke auf spezifische Origins:

```yaml
routes:
  - path_prefix: /api
    methods: [GET, POST, OPTIONS]
    cors:
      enabled: true
      allowed_origins:
        - "https://app.example.com"
        - "https://www.example.com"
      allowed_methods: [GET, POST, PUT, DELETE, OPTIONS]
      allowed_headers: [Content-Type, Authorization, X-API-Key]
      expose_headers: [X-Request-ID, X-RateLimit-Remaining]
      allow_credentials: true
      max_age: 86400  # 24 Stunden
```

### CORS mit Authentication

Kombiniere CORS mit JWT-Authentication:

```yaml
routes:
  - path_prefix: /api/protected
    methods: [GET, POST, OPTIONS]

    # CORS-Konfiguration
    cors:
      enabled: true
      allowed_origins: ["https://app.example.com"]
      allowed_methods: [GET, POST, OPTIONS]
      allowed_headers: [Content-Type, Authorization]
      allow_credentials: true

    # Authentication
    authentication:
      enabled: true
      type: jwt
      jwt:
        issuer: "https://auth.example.com"
        audience: "api.example.com"
        jwks_uri: "https://auth.example.com/.well-known/jwks.json"
```

---

## Konfigurationsoptionen

### CORSPolicy Felder

```yaml
cors:
  # Aktivierung
  enabled: true

  # Erlaubte Origins (Domains)
  allowed_origins:
    - "https://app.example.com"
    - "https://admin.example.com"
    # Oder Wildcard (NUR für Entwicklung!)
    # - "*"

  # Erlaubte HTTP-Methoden
  allowed_methods:
    - GET
    - POST
    - PUT
    - DELETE
    - OPTIONS  # Wichtig für Preflight!

  # Erlaubte Request-Headers
  allowed_headers:
    - Content-Type
    - Authorization
    - X-API-Key
    - X-Custom-Header

  # Headers die an Browser zurückgegeben werden
  expose_headers:
    - X-Request-ID
    - X-Response-Time
    - X-RateLimit-Remaining

  # Credentials erlauben (Cookies, Auth headers)
  allow_credentials: true

  # Preflight-Cache-Dauer (in Sekunden)
  max_age: 86400  # 24 Stunden
```

### Standard-Werte

Wenn Felder weggelassen werden, gelten folgende Defaults:

```yaml
cors:
  enabled: true
  allowed_origins: ["*"]
  allowed_methods: [GET, POST, PUT, DELETE, OPTIONS]
  allowed_headers: [Content-Type, Authorization]
  expose_headers: []
  allow_credentials: false
  max_age: 86400
```

### Wildcard Origins (`*`)

⚠️ **Warnung**: Wildcard Origins sind **unsicher** für Produktion!

```yaml
# ❌ NICHT in Produktion verwenden!
cors:
  allowed_origins: ["*"]
  allow_credentials: true  # Funktioniert nicht mit "*"!

# ✅ Stattdessen spezifische Origins:
cors:
  allowed_origins:
    - "https://app.example.com"
    - "https://admin.example.com"
  allow_credentials: true
```

**Wichtig**: Wenn `allow_credentials: true`, dann **darf NICHT** `*` als Origin verwendet werden!

---

## Provider-Implementierung

### Kong (cors plugin)

Kong verwendet das native `cors` Plugin:

```yaml
# GAL Konfiguration
cors:
  enabled: true
  allowed_origins: ["https://app.example.com"]
  allowed_methods: [GET, POST]
  allow_credentials: true

# Wird zu Kong-Config:
plugins:
  - name: cors
    config:
      origins:
        - "https://app.example.com"
      methods:
        - GET
        - POST
      headers:
        - Content-Type
        - Authorization
      credentials: true
      max_age: 86400
```

**Kong Besonderheiten**:
- ✅ Vollständige CORS-Unterstützung
- ✅ Native Plugin-Integration
- ✅ Regex-Support für Origins
- ⚠️ OPTIONS-Methode muss in Route-Methoden enthalten sein

### APISIX (cors plugin)

APISIX verwendet das `cors` Plugin mit komma-separiertem Format:

```yaml
# GAL Konfiguration
cors:
  enabled: true
  allowed_origins: ["https://app.example.com", "https://www.example.com"]
  allowed_methods: [GET, POST]

# Wird zu APISIX-Config:
{
  "plugins": {
    "cors": {
      "allow_origins": "https://app.example.com,https://www.example.com",
      "allow_methods": "GET,POST",
      "allow_headers": "Content-Type,Authorization",
      "allow_credential": true,
      "max_age": 86400
    }
  }
}
```

**APISIX Besonderheiten**:
- ✅ Native CORS-Plugin
- ⚠️ Komma-separierte Listen (automatisch konvertiert)
- ⚠️ `allow_credential` (singular, nicht plural!)

### Traefik (headers middleware)

Traefik implementiert CORS via Headers-Middleware:

```yaml
# GAL Konfiguration
cors:
  enabled: true
  allowed_origins: ["https://app.example.com"]
  allowed_methods: [GET, POST]

# Wird zu Traefik-Config:
middlewares:
  api_router_0_cors:
    headers:
      accessControlAllowMethods:
        - GET
        - POST
      accessControlAllowOriginList:
        - "https://app.example.com"
      accessControlAllowHeaders:
        - Content-Type
        - Authorization
      accessControlAllowCredentials: true
      accessControlMaxAge: 86400
```

**Traefik Besonderheiten**:
- ✅ Headers-Middleware für CORS
- ✅ `accessControl*` Konfiguration
- ⚠️ Middleware muss in Router referenziert werden

### Envoy (native CORS policy)

Envoy hat native CORS-Unterstützung auf Route-Level:

```yaml
# GAL Konfiguration
cors:
  enabled: true
  allowed_origins: ["https://app.example.com"]
  allowed_methods: [GET, POST]

# Wird zu Envoy-Config:
routes:
  - match:
      prefix: /api
    route:
      cluster: api_cluster
    cors:
      allow_origin_string_match:
        - exact: "https://app.example.com"
      allow_methods: "GET, POST"
      allow_headers: "Content-Type, Authorization"
      allow_credentials: true
      max_age: "86400"
```

**Envoy Besonderheiten**:
- ✅ Native CORS-Policy
- ✅ Regex-Support für Origins
- ⚠️ Wildcard `*` wird zu `safe_regex: '.*'` konvertiert

---

## Häufige Anwendungsfälle

### 1. Single-Page Application (SPA)

Frontend und Backend auf verschiedenen Domains:

```yaml
# Frontend: https://app.example.com
# Backend: https://api.example.com

services:
  - name: api
    routes:
      - path_prefix: /api
        methods: [GET, POST, PUT, DELETE, OPTIONS]
        cors:
          enabled: true
          allowed_origins:
            - "https://app.example.com"
          allowed_methods: [GET, POST, PUT, DELETE, OPTIONS]
          allowed_headers: [Content-Type, Authorization]
          allow_credentials: true
```

### 2. Mehrere Frontend-Domains

Erlaube mehrere Subdomains:

```yaml
cors:
  enabled: true
  allowed_origins:
    - "https://app.example.com"
    - "https://admin.example.com"
    - "https://mobile.example.com"
  allowed_methods: [GET, POST, PUT, DELETE, OPTIONS]
  allow_credentials: true
```

### 3. Public API (keine Credentials)

Öffentliche API ohne Authentication:

```yaml
cors:
  enabled: true
  allowed_origins: ["*"]  # OK für public APIs
  allowed_methods: [GET, POST, OPTIONS]
  allowed_headers: [Content-Type]
  allow_credentials: false  # Wichtig!
  max_age: 86400
```

### 4. API mit Custom Headers

Erlaube spezielle API-Keys im Header:

```yaml
cors:
  enabled: true
  allowed_origins: ["https://app.example.com"]
  allowed_methods: [GET, POST, OPTIONS]
  allowed_headers:
    - Content-Type
    - Authorization
    - X-API-Key        # Custom Header
    - X-Client-ID      # Custom Header
  expose_headers:
    - X-RateLimit-Limit
    - X-RateLimit-Remaining
    - X-RateLimit-Reset
```

### 5. Entwicklung vs. Produktion

Verschiedene CORS-Konfigurationen:

```yaml
# development.yaml
cors:
  enabled: true
  allowed_origins: ["*"]
  allowed_methods: [GET, POST, PUT, DELETE, OPTIONS]
  allow_credentials: false

# production.yaml
cors:
  enabled: true
  allowed_origins:
    - "https://app.example.com"
    - "https://www.example.com"
  allowed_methods: [GET, POST, PUT, DELETE, OPTIONS]
  allowed_headers: [Content-Type, Authorization]
  allow_credentials: true
```

### 6. Mobile Apps

Erlaube spezielle Origins für mobile Apps:

```yaml
cors:
  enabled: true
  allowed_origins:
    - "https://app.example.com"      # Web
    - "capacitor://localhost"        # Capacitor iOS
    - "http://localhost"             # Capacitor Android
  allowed_methods: [GET, POST, PUT, DELETE, OPTIONS]
  allow_credentials: true
```

### 7. GraphQL API

CORS für GraphQL-Endpoints:

```yaml
services:
  - name: graphql_api
    routes:
      - path_prefix: /graphql
        methods: [GET, POST, OPTIONS]
        cors:
          enabled: true
          allowed_origins: ["https://app.example.com"]
          allowed_methods: [GET, POST, OPTIONS]
          allowed_headers:
            - Content-Type
            - Authorization
            - X-Apollo-Tracing  # GraphQL-spezifisch
```

### 8. WebSocket-Verbindungen

CORS für WebSocket-Upgrades:

```yaml
services:
  - name: websocket_service
    routes:
      - path_prefix: /ws
        methods: [GET, OPTIONS]  # WebSocket uses GET for upgrade
        cors:
          enabled: true
          allowed_origins: ["https://app.example.com"]
          allowed_methods: [GET, OPTIONS]
          allowed_headers:
            - Sec-WebSocket-Protocol
            - Sec-WebSocket-Extensions
```

---

## Sicherheits-Best-Practices

### 1. ❌ Niemals Wildcard mit Credentials

**Falsch** (Sicherheitslücke!):
```yaml
cors:
  allowed_origins: ["*"]
  allow_credentials: true  # ❌ GEFÄHRLICH!
```

**Richtig**:
```yaml
cors:
  allowed_origins:
    - "https://app.example.com"
  allow_credentials: true  # ✅ Sicher
```

### 2. ✅ Spezifische Origins verwenden

**Falsch**:
```yaml
allowed_origins: ["*"]  # ❌ Zu permissiv
```

**Richtig**:
```yaml
allowed_origins:
  - "https://app.example.com"
  - "https://admin.example.com"
```

### 3. ✅ Minimale Header-Rechte

Erlaube nur benötigte Headers:

```yaml
# ❌ Zu permissiv
allowed_headers: ["*"]

# ✅ Nur benötigte Headers
allowed_headers:
  - Content-Type
  - Authorization
  - X-API-Key
```

### 4. ✅ OPTIONS-Methode nicht vergessen

Für Preflight-Requests:

```yaml
routes:
  - path_prefix: /api
    methods: [GET, POST, PUT, DELETE, OPTIONS]  # ✅ OPTIONS!
    cors:
      enabled: true
```

### 5. ✅ HTTPS für Produktion

Verwende immer HTTPS-Origins in Produktion:

```yaml
# ❌ HTTP in Produktion
allowed_origins:
  - "http://app.example.com"

# ✅ HTTPS in Produktion
allowed_origins:
  - "https://app.example.com"
```

### 6. ✅ Max Age begrenzen

Setze sinnvolle Preflight-Cache-Dauer:

```yaml
# ❌ Zu lang (1 Jahr)
max_age: 31536000

# ✅ Sinnvoll (24 Stunden)
max_age: 86400
```

### 7. ✅ Expose nur benötigte Headers

Exponiere nur Headers die der Client wirklich braucht:

```yaml
# ✅ Nur benötigte Headers
expose_headers:
  - X-Request-ID
  - X-RateLimit-Remaining

# ❌ Zu viele interne Headers
expose_headers:
  - X-Internal-Service
  - X-Database-Host  # Sensible Informationen!
```

---

## CORS Testen

### Mit cURL

#### Preflight-Request (OPTIONS) testen:

```bash
curl -X OPTIONS http://api.example.com/api/users \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

**Erwartete Response-Headers**:
```
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

#### Actual Request testen:

```bash
curl -X GET http://api.example.com/api/users \
  -H "Origin: https://app.example.com" \
  -v
```

**Erwartete Response-Headers**:
```
Access-Control-Allow-Origin: https://app.example.com
```

### Mit JavaScript (Browser)

```javascript
// Einfacher CORS-Test
fetch('https://api.example.com/api/users', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  },
  credentials: 'include'  // Wenn allow_credentials: true
})
.then(response => {
  console.log('CORS successful!');
  console.log('Response headers:', response.headers);
  return response.json();
})
.catch(error => {
  console.error('CORS error:', error);
});
```

### Mit Python Requests

```python
import requests

# Test Preflight
response = requests.options(
    'http://api.example.com/api/users',
    headers={
        'Origin': 'https://app.example.com',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type'
    }
)

print('Preflight Response Headers:')
print(response.headers)

# Check CORS headers
assert 'Access-Control-Allow-Origin' in response.headers
assert response.headers['Access-Control-Allow-Origin'] == 'https://app.example.com'
```

### Automatisierte Tests

```python
def test_cors_headers():
    """Test CORS configuration"""
    response = requests.get(
        'http://api.example.com/api/users',
        headers={'Origin': 'https://app.example.com'}
    )

    # Check allowed origin
    assert 'Access-Control-Allow-Origin' in response.headers
    assert response.headers['Access-Control-Allow-Origin'] == 'https://app.example.com'

    # Check credentials
    if 'Access-Control-Allow-Credentials' in response.headers:
        assert response.headers['Access-Control-Allow-Credentials'] == 'true'

def test_cors_preflight():
    """Test CORS preflight request"""
    response = requests.options(
        'http://api.example.com/api/users',
        headers={
            'Origin': 'https://app.example.com',
            'Access-Control-Request-Method': 'POST'
        }
    )

    assert response.status_code == 200
    assert 'Access-Control-Allow-Methods' in response.headers
```

---

## Troubleshooting

### Problem 1: CORS-Fehler trotz Konfiguration

**Symptom**: Browser zeigt CORS-Fehler, obwohl CORS konfiguriert ist.

**Lösung**:
1. ✅ OPTIONS-Methode erlauben:
```yaml
methods: [GET, POST, OPTIONS]  # OPTIONS nicht vergessen!
```

2. ✅ Origin exakt matchen:
```yaml
# ❌ Falsch
allowed_origins: ["https://app.example.com/"]

# ✅ Richtig (ohne trailing slash)
allowed_origins: ["https://app.example.com"]
```

3. ✅ CORS vor Authentication:
```yaml
# Stelle sicher, dass CORS-Plugin VOR Authentication läuft
```

### Problem 2: Credentials funktionieren nicht

**Symptom**: Cookies/Auth headers werden nicht gesendet.

**Lösung**:
```yaml
# ❌ Wildcard mit Credentials
cors:
  allowed_origins: ["*"]
  allow_credentials: true

# ✅ Spezifische Origin
cors:
  allowed_origins: ["https://app.example.com"]
  allow_credentials: true
```

**Client-Side**:
```javascript
// JavaScript: credentials einschließen
fetch('https://api.example.com/api', {
  credentials: 'include'  // Wichtig!
})
```

### Problem 3: Preflight-Request schlägt fehl

**Symptom**: OPTIONS-Request gibt 401/403 zurück.

**Lösung**:
```yaml
# Authentication für OPTIONS deaktivieren
routes:
  - path_prefix: /api
    methods: [GET, POST, OPTIONS]
    cors:
      enabled: true
    # CORS muss VOR Authentication kommen!
```

### Problem 4: Custom Headers werden blockiert

**Symptom**: Custom Headers wie `X-API-Key` funktionieren nicht.

**Lösung**:
```yaml
cors:
  allowed_headers:
    - Content-Type
    - Authorization
    - X-API-Key        # Custom Header explizit erlauben!
```

**Client-Side**:
```javascript
fetch('https://api.example.com/api', {
  headers: {
    'X-API-Key': 'key123'  // Muss in allowed_headers sein!
  }
})
```

### Problem 5: Expose-Headers nicht sichtbar

**Symptom**: Response-Header sind im Browser nicht verfügbar.

**Lösung**:
```yaml
cors:
  expose_headers:
    - X-Request-ID        # Exponiere Header explizit!
    - X-RateLimit-Remaining
```

**Client-Side**:
```javascript
response.headers.get('X-Request-ID')  // Jetzt verfügbar
```

### Problem 6: CORS funktioniert nur auf einem Provider

**Problem**: CORS funktioniert auf Kong, aber nicht auf Envoy.

**Lösung**: Provider-spezifische Besonderheiten prüfen:

**Kong**:
```yaml
# OPTIONS in Route-Methoden
methods: [GET, POST, OPTIONS]
```

**APISIX**:
```yaml
# allow_credential (singular!)
```

**Traefik**:
```yaml
# Middleware muss in Router referenziert sein
```

**Envoy**:
```yaml
# CORS ist route-level, nicht global
```

### Problem 7: Max-Age funktioniert nicht

**Symptom**: Preflight-Requests werden nicht gecacht.

**Lösung**:
```yaml
# Setze max_age explizit
cors:
  max_age: 86400  # 24 Stunden

# Browser-Cache prüfen (DevTools → Network → Disable Cache)
```

---

## Best Practice Checkliste

### Vor Deployment

- [ ] ✅ Wildcard `*` nur in Entwicklung verwenden
- [ ] ✅ Spezifische Origins für Produktion
- [ ] ✅ OPTIONS-Methode in allen Routes
- [ ] ✅ HTTPS-Origins in Produktion
- [ ] ✅ allow_credentials nur mit spezifischen Origins
- [ ] ✅ Minimale allowed_headers
- [ ] ✅ Nur benötigte expose_headers
- [ ] ✅ Sinnvolle max_age (24 Stunden)

### Security Review

- [ ] ❌ Keine Wildcard mit Credentials
- [ ] ❌ Keine sensitiven Headers exponiert
- [ ] ❌ Keine HTTP-Origins in Produktion
- [ ] ✅ CORS vor Authentication
- [ ] ✅ Rate Limiting für OPTIONS-Requests

### Testing

- [ ] ✅ Preflight-Request testen (OPTIONS)
- [ ] ✅ Actual Request testen (GET/POST)
- [ ] ✅ Mit Credentials testen
- [ ] ✅ Custom Headers testen
- [ ] ✅ Verschiedene Origins testen
- [ ] ✅ Browser DevTools prüfen

---

## Zusammenfassung

CORS in GAL ermöglicht:

✅ **Einheitliche Konfiguration** für alle Provider
✅ **Vollständige CORS-Unterstützung** (Origins, Methods, Headers, Credentials)
✅ **Einfache Integration** mit Authentication und Rate Limiting
✅ **Provider-Abstraktion** - schreibe einmal, deploye überall

**Nächste Schritte**:
- Siehe [AUTHENTICATION.md](AUTHENTICATION.md) für CORS + Auth
- Siehe [HEADERS.md](HEADERS.md) für zusätzliche Header-Manipulation
- Siehe [examples/cors-example.yaml](../../examples/cors-example.yaml) für vollständige Beispiele

**Hilfe benötigt?**
- Probleme melden: https://github.com/pt9912/x-gal/issues
- Dokumentation: https://docs.gal.dev
- Beispiele: [examples/](../../examples/)
