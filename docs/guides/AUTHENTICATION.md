# Authentication Anleitung

GAL v1.1.0 führt umfassende Authentication-Unterstützung für alle Gateway-Provider ein. Diese Anleitung erklärt, wie Sie Authentication für Ihre APIs mit Basic Auth, API Keys und JWT konfigurieren.

## Inhaltsverzeichnis

- [Übersicht](#übersicht)
- [Schnellstart](#schnellstart)
- [Authentication-Typen](#authentication-typen)
  - [Basic Authentication](#basic-authentication)
  - [API Key Authentication](#api-key-authentication)
  - [JWT Authentication](#jwt-authentication)
- [Konfigurationsoptionen](#konfigurationsoptionen)
- [Provider-spezifische Implementierungen](#provider-spezifische-implementierungen)
- [Best Practices](#best-practices)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Migrationsleitfaden](#migrationsleitfaden)

## Übersicht

Authentication stellt sicher, dass nur autorisierte Benutzer auf Ihre APIs zugreifen können. GAL unterstützt drei Authentication-Methoden:

| Typ | Anwendungsfall | Sicherheitslevel | Komplexität |
|-----|----------------|------------------|-------------|
| **Basic Auth** | Interne Tools, Admin-Panels | Mittel | Niedrig |
| **API Key** | Service-to-Service, Externe APIs | Mittel-Hoch | Niedrig |
| **JWT** | Moderne Web/Mobile Apps, Microservices | Hoch | Mittel |

## Schnellstart

### API Key Authentication (Am einfachsten)

```yaml
services:
  - name: my_api
    type: rest
    protocol: http
    upstream:
      host: api.local
      port: 8080
    routes:
      - path_prefix: /api/protected
        authentication:
          enabled: true
          type: api_key
          api_key:
            keys:
              - "your-secret-key-123"
            key_name: X-API-Key
            in_location: header
```

**Test mit curl:**
```bash
curl -H "X-API-Key: your-secret-key-123" http://localhost:10000/api/protected
```

### Basic Authentication

```yaml
services:
  - name: admin_api
    type: rest
    protocol: http
    upstream:
      host: admin.local
      port: 8080
    routes:
      - path_prefix: /api/admin
        authentication:
          enabled: true
          type: basic
          basic_auth:
            users:
              admin: "super_secret_password"
              operator: "operator_pass"
            realm: "Admin Area"
```

**Test mit curl:**
```bash
curl -u admin:super_secret_password http://localhost:10000/api/admin
```

### JWT Authentication

```yaml
services:
  - name: secure_api
    type: rest
    protocol: http
    upstream:
      host: secure.local
      port: 8080
    routes:
      - path_prefix: /api/user
        authentication:
          enabled: true
          type: jwt
          jwt:
            issuer: "https://auth.example.com"
            audience: "api.example.com"
            jwks_uri: "https://auth.example.com/.well-known/jwks.json"
            algorithms:
              - RS256
```

**Test mit curl:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:10000/api/user
```

## Authentication-Typen

### Basic Authentication

HTTP Basic Authentication verwendet Username/Password-Credentials, die in HTTP-Headern übertragen werden.

#### Konfiguration

```yaml
authentication:
  enabled: true
  type: basic
  basic_auth:
    users:
      username1: "password1"
      username2: "password2"
    realm: "Protected Area"
  fail_status: 401
  fail_message: "Unauthorized"
```

#### Parameter

- `users` (dict): Mapping von Benutzername zu Passwort
- `realm` (string): Authentication-Realm im Browser-Prompt angezeigt (Standard: "Protected")
- `fail_status` (int): HTTP-Statuscode bei Auth-Fehlern (Standard: 401)
- `fail_message` (string): Fehlermeldung bei Auth-Fehlern

#### Sicherheitsüberlegungen

⚠️ **Wichtige Sicherheitshinweise:**
- Passwörter sollten in Production gehasht sein (z.B. bcrypt, htpasswd-Format)
- Verwenden Sie immer HTTPS, um Credentials während der Übertragung zu schützen
- Speichern Sie niemals Klartext-Passwörter in Konfigurationsdateien
- Erwägen Sie die Verwendung von Umgebungsvariablen oder Secrets Management

**Production-Beispiel mit htpasswd:**

```bash
# Generiere htpasswd-Hash
htpasswd -nb admin secret_password

# Ausgabe: admin:$apr1$XYZ123$HASH...
```

```yaml
basic_auth:
  users:
    admin: "$apr1$XYZ123$HASH..."  # htpasswd-Format
```

### API Key Authentication

API Key Authentication verwendet statische Keys, die in Headern oder Query-Parametern übergeben werden.

#### Konfiguration - Header-basiert

```yaml
authentication:
  enabled: true
  type: api_key
  api_key:
    keys:
      - "key_123abc"
      - "key_456def"
      - "key_789ghi"
    key_name: X-API-Key
    in_location: header
```

#### Konfiguration - Query Parameter

```yaml
authentication:
  enabled: true
  type: api_key
  api_key:
    keys:
      - "key_123abc"
    key_name: api_key
    in_location: query
```

**Verwendung:**
```bash
# Header-basiert
curl -H "X-API-Key: key_123abc" http://localhost:10000/api

# Query Parameter
curl "http://localhost:10000/api?api_key=key_123abc"
```

#### Parameter

- `keys` (list): Gültige API Keys
- `key_name` (string): Header- oder Query-Parameter-Name (Standard: "X-API-Key")
- `in_location` (string): "header" oder "query" (Standard: "header")

#### Best Practices

✅ **Empfohlen:**
- Verwenden Sie lange, zufällige Keys (mindestens 32 Zeichen)
- Rotieren Sie Keys regelmäßig
- Verwenden Sie unterschiedliche Keys für verschiedene Clients
- Loggen Sie Key-Nutzung für Auditing
- Verwenden Sie header-basierte Auth statt Query-Parameter (sicherer)

❌ **Vermeiden:**
- Keys über mehrere Services hinweg teilen
- Keys in Client-seitigem Code speichern (Mobile Apps, JavaScript)
- Vorhersagbare Key-Muster verwenden
- Keys in Anwendungslogs loggen

**Key-Generierungs-Beispiel:**
```bash
# Generiere sicheren Zufalls-Key
openssl rand -hex 32
# Ausgabe: 64-Zeichen Hexadezimal-String
```

### JWT Authentication

JSON Web Tokens (JWT) bieten zustandslose, claims-basierte Authentication.

#### Konfiguration

```yaml
authentication:
  enabled: true
  type: jwt
  jwt:
    issuer: "https://auth.example.com"
    audience: "api.example.com"
    jwks_uri: "https://auth.example.com/.well-known/jwks.json"
    algorithms:
      - RS256
      - ES256
    required_claims:
      - sub
      - email
  fail_status: 401
  fail_message: "Invalid or missing JWT token"
```

#### Parameter

- `issuer` (string): Erwarteter JWT-Aussteller (iss Claim)
- `audience` (string): Erwartete JWT-Audience (aud Claim)
- `jwks_uri` (string): JSON Web Key Set Endpoint-URL
- `algorithms` (list): Erlaubte Signatur-Algorithmen (Standard: ["RS256"])
- `required_claims` (list): Claims, die im Token vorhanden sein müssen

#### Gängige JWT-Algorithmen

| Algorithmus | Typ | Anwendungsfall |
|-------------|-----|----------------|
| **RS256** | RSA | Am häufigsten, Public Key Verification |
| **ES256** | ECDSA | Kleinere Signaturen, moderne Wahl |
| **HS256** | HMAC | Symmetrisch, nur für interne Services |

#### JWKS (JSON Web Key Set)

GAL holt und cached automatisch Public Keys vom JWKS-Endpoint.

**Beispiel JWKS-Endpoint:**
```
https://auth.example.com/.well-known/jwks.json
```

**JWKS-Struktur:**
```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "key-1",
      "n": "...",
      "e": "AQAB"
    }
  ]
}
```

#### JWT Claims

**Standard-Claims:**
- `iss` (issuer): Token-Aussteller-URL
- `sub` (subject): Benutzer-ID oder Identifikator
- `aud` (audience): Vorgesehener Empfänger
- `exp` (expiration): Token-Ablaufzeit
- `iat` (issued at): Token-Erstellungszeit
- `nbf` (not before): Token nicht gültig vor dieser Zeit

**Custom Claims:**
Sie können Custom Claims hinzufügen (z.B. `email`, `roles`, `permissions`) und diese in Ihrem Backend validieren.

#### JWT Beispiel

**JWT Header:**
```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "key-1"
}
```

**JWT Payload:**
```json
{
  "iss": "https://auth.example.com",
  "sub": "user123",
  "aud": "api.example.com",
  "exp": 1735689600,
  "iat": 1735686000,
  "email": "user@example.com",
  "roles": ["user", "admin"]
}
```

## Konfigurationsoptionen

### Gemeinsame Optionen

Alle Authentication-Typen teilen diese gemeinsamen Optionen:

```yaml
authentication:
  enabled: true              # Authentication aktivieren/deaktivieren
  type: "api_key"           # Authentication-Typ: "basic", "api_key", "jwt"
  fail_status: 401           # HTTP-Status bei Auth-Fehlern (Standard: 401)
  fail_message: "Unauthorized"  # Fehlermeldung bei Fehlern
```

### Typ-spezifische Optionen

#### Basic Auth
```yaml
basic_auth:
  users:                    # Username-Passwort-Mapping
    username: "password"
  realm: "Protected"        # Authentication-Realm
```

#### API Key
```yaml
api_key:
  keys:                     # Liste gültiger API Keys
    - "key1"
    - "key2"
  key_name: "X-API-Key"     # Header- oder Query-Param-Name
  in_location: "header"     # "header" oder "query"
```

#### JWT
```yaml
jwt:
  issuer: "https://auth.example.com"        # Token-Aussteller
  audience: "api.example.com"               # Token-Audience
  jwks_uri: "https://auth.example.com/..."  # JWKS-Endpoint
  algorithms:                               # Erlaubte Algorithmen
    - RS256
  required_claims:                          # Erforderliche JWT-Claims
    - sub
```

### Mehrere Routes mit unterschiedlicher Auth

```yaml
services:
  - name: multi_auth_service
    type: rest
    protocol: http
    upstream:
      host: service.local
      port: 8080
    routes:
      # Öffentlicher Endpoint - keine Auth
      - path_prefix: /api/public
        methods: [GET]

      # API Key geschützt
      - path_prefix: /api/protected
        methods: [GET, POST]
        authentication:
          type: api_key
          api_key:
            keys: ["key123"]

      # Admin - Basic Auth
      - path_prefix: /api/admin
        methods: [GET, POST, DELETE]
        authentication:
          type: basic
          basic_auth:
            users:
              admin: "secret"
```

## Provider-spezifische Implementierungen

### Kong

Kong implementiert Authentication mit nativen Plugins.

**Basic Auth:**
- Plugin: `basic-auth`
- Features: Consumer-basierte Authentication, Credential-Speicherung

**API Key:**
- Plugin: `key-auth`
- Features: Flexible Key-Location (Header/Query), Consumer-Zuordnung

**JWT:**
- Plugin: `jwt`
- Features: JWKS-Support, Claim-Verifizierung, RS256/ES256/HS256

**Generiertes Config-Beispiel:**
```yaml
services:
  - name: test_service
    routes:
      - name: test_service_route
        plugins:
          - name: key-auth
            config:
              key_names: [X-API-Key]
              key_in_header: true
              hide_credentials: true
```

### APISIX

APISIX implementiert Authentication mit Plugins und JSON-Konfiguration.

**Basic Auth:**
- Plugin: `basic-auth`
- Features: Consumer-basiert, flexible Konfiguration

**API Key:**
- Plugin: `key-auth`
- Features: Header- und Query-Parameter-Support

**JWT:**
- Plugin: `jwt-auth`
- Features: Algorithmus-Auswahl, Issuer/Audience-Validierung

**Generiertes Config-Beispiel:**
```json
{
  "routes": [
    {
      "uri": "/api/*",
      "plugins": {
        "key-auth": {
          "header": "X-API-Key"
        }
      }
    }
  ]
}
```

### Traefik

Traefik implementiert Authentication mit Middleware.

**Basic Auth:**
- Middleware: `basicAuth`
- Features: Benutzerliste, Realm-Konfiguration
- Hinweis: Verwenden Sie htpasswd-Format für Production

**API Key:**
- Middleware: `forwardAuth`
- Features: Externer Validierungsservice
- Hinweis: Benötigt externen API-Key-Validator

**JWT:**
- Middleware: `forwardAuth`
- Features: Externer JWT-Validierungsservice
- Hinweis: Benötigt externen JWT-Validator

**Generiertes Config-Beispiel:**
```yaml
http:
  middlewares:
    test_service_router_0_auth:
      basicAuth:
        users:
          - 'admin:$apr1$...'
        realm: 'Admin Area'
```

### Envoy

Envoy implementiert Authentication mit HTTP-Filtern.

**Basic Auth:**
- Filter: `envoy.filters.http.lua`
- Features: Inline Lua-Validierung
- Hinweis: Production benötigt externen Auth-Service

**API Key:**
- Filter: `envoy.filters.http.lua`
- Features: Header-Validierung via Lua
- Hinweis: Production benötigt externe Validierung

**JWT:**
- Filter: `envoy.filters.http.jwt_authn`
- Features: Vollständige JWT-Validierung, JWKS-Support, natives RS256/ES256
- Hinweis: Robusteste JWT-Implementierung

**Generiertes Config-Beispiel:**
```yaml
http_filters:
  - name: envoy.filters.http.jwt_authn
    typed_config:
      providers:
        jwt_provider:
          issuer: 'https://auth.example.com'
          audiences:
            - 'api.example.com'
          remote_jwks:
            http_uri:
              uri: 'https://auth.example.com/.well-known/jwks.json'
              cluster: jwks_cluster
```

## Best Practices

### Allgemeine Sicherheit

1. **Verwenden Sie immer HTTPS in Production**
   - Schützt Credentials und Tokens während der Übertragung
   - Erforderlich für Basic Auth und API Keys
   - Empfohlen für alle Authentication-Typen

2. **Verwenden Sie starke Credentials**
   - Passwörter: Mindestens 12 Zeichen, gemischte Groß-/Kleinschreibung, Sonderzeichen
   - API Keys: Mindestens 32 Zeichen, kryptographisch zufällig
   - JWT-Secrets: Mindestens 256 Bits für HS256

3. **Rotieren Sie Credentials regelmäßig**
   - API Keys: Alle 90 Tage
   - JWT-Signatur-Keys: Alle 6-12 Monate
   - Passwörter: Alle 90 Tage oder bei Kompromittierung

4. **Implementieren Sie Rate Limiting**
   - Kombinieren Sie Authentication mit Rate Limiting
   - Schutz vor Brute-Force-Angriffen
   - Verwenden Sie per-User- oder per-Key-Limits

### Authentication-Typ-Auswahl

**Verwenden Sie Basic Auth wenn:**
- Interne Tools und Admin-Interfaces
- Kleine Anzahl bekannter Benutzer
- Einfachheit wichtiger als erweiterte Features

**Verwenden Sie API Key wenn:**
- Service-to-Service-Kommunikation
- Externer API-Zugriff für Partner
- Einfaches Credential-Management benötigt

**Verwenden Sie JWT wenn:**
- Moderne Web- oder Mobile-Anwendungen
- Microservices-Architektur
- Zustandslose Authentication erforderlich
- Kurzlebige Tokens benötigt
- Claims-basierte Authorization erforderlich

### Production-Überlegungen

1. **Niemals Credentials hardcoden**
   ```yaml
   # Schlecht - hardcoded in Config
   users:
     admin: "password123"

   # Gut - Umgebungsvariablen verwenden
   users:
     admin: "${ADMIN_PASSWORD}"
   ```

2. **Verwenden Sie Secrets Management**
   - HashiCorp Vault
   - AWS Secrets Manager
   - Kubernetes Secrets
   - Azure Key Vault

3. **Implementieren Sie korrektes Logging**
   - Loggen Sie Authentication-Versuche (Erfolg und Fehler)
   - Loggen Sie keine Credentials oder Tokens
   - Überwachen Sie verdächtige Muster

4. **Fügen Sie Monitoring und Alerting hinzu**
   - Tracken Sie Authentication-Fehlerquoten
   - Alarmieren bei ungewöhnlichen Mustern
   - Überwachen Sie Token-Ablauf und Rotation

## Testing

### Testing Basic Auth

```bash
# Gültige Credentials
curl -u admin:secret http://localhost:10000/api/admin
# Erwartet: 200 OK

# Ungültige Credentials
curl -u admin:wrong http://localhost:10000/api/admin
# Erwartet: 401 Unauthorized

# Fehlende Credentials
curl http://localhost:10000/api/admin
# Erwartet: 401 Unauthorized
```

### Testing API Key Auth

```bash
# Gültiger API Key im Header
curl -H "X-API-Key: key_123abc" http://localhost:10000/api/protected
# Erwartet: 200 OK

# Gültiger API Key im Query-Parameter
curl "http://localhost:10000/api/protected?api_key=key_123abc"
# Erwartet: 200 OK

# Ungültiger API Key
curl -H "X-API-Key: invalid_key" http://localhost:10000/api/protected
# Erwartet: 401 Unauthorized

# Fehlender API Key
curl http://localhost:10000/api/protected
# Erwartet: 401 Unauthorized
```

### Testing JWT Auth

Generieren Sie zuerst einen Test-JWT-Token auf https://jwt.io oder mit einer Bibliothek:

```python
import jwt
import time

# Generiere JWT
payload = {
    "iss": "https://auth.example.com",
    "sub": "user123",
    "aud": "api.example.com",
    "exp": int(time.time()) + 3600,
    "iat": int(time.time())
}

# Verwenden Sie Ihren Private Key
token = jwt.encode(payload, private_key, algorithm="RS256")
```

```bash
# Gültiger JWT Token
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:10000/api/user
# Erwartet: 200 OK

# Ungültiger JWT Token
curl -H "Authorization: Bearer invalid.token.here" http://localhost:10000/api/user
# Erwartet: 401 Unauthorized

# Fehlender Authorization-Header
curl http://localhost:10000/api/user
# Erwartet: 401 Unauthorized

# Abgelaufener Token
curl -H "Authorization: Bearer EXPIRED_TOKEN" http://localhost:10000/api/user
# Erwartet: 401 Unauthorized
```

### Load Testing mit Authentication

```bash
# Apache Bench mit API Key
ab -n 1000 -c 10 -H "X-API-Key: key_123abc" http://localhost:10000/api/protected

# wrk mit JWT
wrk -t4 -c100 -d30s -H "Authorization: Bearer YOUR_JWT" http://localhost:10000/api/user
```

## Troubleshooting

### Häufige Probleme

#### 1. 401 Unauthorized trotz korrekter Credentials

**Symptom:** Authentication schlägt fehl trotz korrekter Credentials

**Mögliche Ursachen:**
- Credentials nicht korrekt im Gateway konfiguriert
- Tippfehler in Username/Passwort/Key
- Falscher Authentication-Typ konfiguriert
- Groß-/Kleinschreibungsprobleme

**Lösung:**
```bash
# Prüfe generierte Config
python gal-cli.py generate -f examples/authentication-test.yaml

# Verifiziere Credentials in Ausgabe
# Für Basic Auth, prüfe users-Sektion
# Für API Key, prüfe keys-Liste
# Für JWT, verifiziere issuer/audience
```

#### 2. JWT-Validierung schlägt fehl

**Symptom:** Gültige JWT-Tokens werden abgelehnt

**Mögliche Ursachen:**
- Falscher Issuer oder Audience
- JWKS-Endpoint nicht erreichbar
- Token abgelaufen
- Algorithmus-Mismatch
- Erforderliche Claims fehlen

**Lösung:**
```bash
# Verifiziere JWT auf jwt.io
# Prüfe ob Issuer mit Konfiguration übereinstimmt
# Verifiziere JWKS-Endpoint ist erreichbar
curl https://auth.example.com/.well-known/jwks.json

# Prüfe Token-Ablauf
# Verifiziere Algorithmus im JWT-Header stimmt mit Config überein
```

#### 3. API Key wird nicht erkannt

**Symptom:** API Key im Header/Query wird nicht validiert

**Mögliche Ursachen:**
- Key-Name-Mismatch (case-sensitive)
- Location-Mismatch (header vs query)
- Key nicht in konfigurierter Keys-Liste
- Sonderzeichen im Key verursachen Parsing-Probleme

**Lösung:**
```yaml
# Verifiziere Konfiguration
authentication:
  type: api_key
  api_key:
    key_name: X-API-Key  # Muss exakt übereinstimmen (case-sensitive)
    in_location: header   # Muss mit Request-Location übereinstimmen
    keys:
      - "your_actual_key"  # Muss exakt übereinstimmen
```

#### 4. Basic Auth Prompts erscheinen nicht

**Symptom:** Browser zeigt keinen Authentication-Prompt

**Mögliche Ursachen:**
- Falsche Realm-Konfiguration
- Vorher gecachte Credentials
- Browser-Sicherheitseinstellungen

**Lösung:**
- Browser-Cache und Cookies löschen
- Zuerst mit curl testen
- Verifizieren, dass Realm korrekt konfiguriert ist

#### 5. JWKS Fetch-Fehler (Envoy)

**Symptom:** Envoy kann JWKS nicht abrufen

**Mögliche Ursachen:**
- JWKS-Cluster nicht konfiguriert
- DNS-Auflösungsfehler
- HTTPS-Zertifikat-Validierungsfehler
- Netzwerkverbindungsprobleme

**Lösung:**
- Verifizieren Sie, dass JWKS-URL erreichbar ist
- Prüfen Sie, dass Cluster-Konfiguration TLS-Einstellungen enthält
- Testen Sie JWKS-Endpoint manuell:
```bash
curl https://auth.example.com/.well-known/jwks.json
```

### Debug-Modus

Aktivieren Sie Debug-Logging für Troubleshooting:

```bash
# Generiere Config mit ausführlicher Ausgabe
python gal-cli.py generate -f config.yaml --verbose

# Prüfe Gateway-Logs
# Kong
docker logs <kong-container>

# APISIX
docker logs <apisix-container>

# Traefik
docker logs <traefik-container>

# Envoy
docker logs <envoy-container>
```

## Migrationsleitfaden

### Von v1.0.0 zu v1.1.0

Authentication ist ein neues Feature in v1.1.0. Bestehende Konfigurationen ohne Authentication funktionieren weiterhin.

**Authentication zu bestehenden Routes hinzufügen:**

```yaml
# Vorher (v1.0.0)
routes:
  - path_prefix: /api/users
    methods: [GET, POST]

# Nachher (v1.1.0)
routes:
  - path_prefix: /api/users
    methods: [GET, POST]
    authentication:  # Neues Feld
      enabled: true
      type: api_key
      api_key:
        keys: ["your_key"]
```

### Kombination mit Rate Limiting

Authentication und Rate Limiting funktionieren nahtlos zusammen:

```yaml
routes:
  - path_prefix: /api/premium
    authentication:
      type: jwt
      jwt:
        issuer: "https://auth.example.com"
    rate_limit:
      enabled: true
      requests_per_second: 1000
      key_type: jwt_claim
      key_claim: sub  # Rate Limit pro JWT-Subject
```

## Erweiterte Themen

### Multi-Tenancy mit JWT Claims

Verwenden Sie JWT Claims für Multi-Tenant Rate Limiting:

```yaml
rate_limit:
  enabled: true
  key_type: jwt_claim
  key_claim: tenant_id  # Custom Claim
  requests_per_second: 100
```

### OAuth 2.0 Integration

GAL JWT-Support funktioniert mit jedem OAuth 2.0 / OIDC-Provider:

- Auth0
- Okta
- Keycloak
- AWS Cognito
- Azure AD
- Google Cloud Identity

Konfigurieren Sie den JWKS-Endpoint von Ihrem OAuth-Provider:

```yaml
jwt:
  issuer: "https://your-tenant.auth0.com/"
  audience: "https://your-api.example.com"
  jwks_uri: "https://your-tenant.auth0.com/.well-known/jwks.json"
```

### Custom Authentication

Für Custom-Authentication-Anforderungen, die nicht von eingebauten Typen abgedeckt werden:

1. **Traefik**: Verwenden Sie forwardAuth Middleware mit Custom-Validierungsservice
2. **Envoy**: Verwenden Sie ext_authz Filter mit Custom gRPC/HTTP-Service
3. **Kong**: Entwickeln Sie Custom Plugin
4. **APISIX**: Verwenden Sie Serverless Plugin mit Lua-Code

## Zusammenfassung

GAL v1.1.0 bietet umfassende Authentication-Unterstützung:

✅ Drei Authentication-Typen: Basic, API Key, JWT
✅ Alle vier Gateway-Provider unterstützt
✅ Per-Route Authentication-Konfiguration
✅ Kombination mit Rate Limiting
✅ Production-ready JWT mit JWKS-Support
✅ Flexibles Credential-Management

Für Fragen oder Probleme, besuchen Sie: https://github.com/pt9912/x-gal/issues
