# GCP API Gateway Import

Import bestehender GCP API Gateway Konfigurationen nach GAL.

## Übersicht

GAL kann OpenAPI 2.0 (Swagger) Specs mit `x-google-*` Extensions importieren und in provider-agnostische GAL-Konfiguration konvertieren.

## Voraussetzungen

- `gcloud` CLI installiert
- GCP Project mit API Gateway Zugriff
- Bestehende API Gateway Deployment

## Import-Prozess

### 1. OpenAPI Spec exportieren

```bash
# API Config beschreiben
gcloud api-gateway api-configs describe CONFIG_ID \
  --api=API_ID \
  --project=PROJECT_ID \
  --format=yaml > api-config.yaml

# OpenAPI Spec extrahieren (aus gatewayConfig)
# Die OpenAPI 2.0 Spec ist im outputten YAML enthalten
```

**Alternative: OpenAPI Spec direkt verwenden**

Falls Sie die ursprüngliche OpenAPI 2.0 Datei haben:

```bash
# Nutze die originale openapi.yaml Datei
gal import -i openapi.yaml -p gcp_apigateway -o gal-config.yaml
```

### 2. GAL Import ausführen

```bash
gal import \
  --input openapi.yaml \
  --provider gcp_apigateway \
  --output gal-config.yaml
```

### 3. Importierte Config prüfen

```yaml
version: "1.0"
provider: gal

global_config:
  gcp_apigateway:
    api_id: "user-api"
    api_display_name: "User Management API"
    project_id: "my-gcp-project"
    region: "us-central1"
    backend_address: "https://backend.example.com"
    backend_path_translation: "APPEND_PATH_TO_ADDRESS"
    backend_deadline: 30.0
    jwt_issuer: "https://accounts.google.com"
    jwt_jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    jwt_audiences:
      - "https://my-project.example.com"
    cors_enabled: true
    cors_allow_origins:
      - "*"

services:
  - name: imported-api
    type: rest
    protocol: https
    upstream:
      targets:
        - host: backend.example.com
          port: 443
    routes:
      - path_prefix: /api/users
        methods:
          - GET
          - POST
```

## Unterstützte Features

| Feature | Import Support | Notizen |
|---------|----------------|---------|
| **x-google-backend** | ✅ Voll | Backend Address, Path Translation, Deadline |
| **JWT Auth** | ✅ Voll | x-google-issuer, x-google-jwks_uri, x-google-audiences |
| **CORS** | ✅ Voll | OPTIONS Methods mit Headers |
| **Routes** | ✅ Voll | Paths + HTTP Methods |
| **Service Account** | ⚠️ Teilweise | Nicht in OpenAPI Spec enthalten |

## Beispiele

### Basis Import

**Input:** `openapi.yaml` (OpenAPI 2.0)

```yaml
swagger: "2.0"
info:
  title: "Pet Store API"
  version: "1.0.0"

schemes:
  - https

x-google-backend:
  address: "https://pet store-backend.example.com"
  deadline: 30.0

paths:
  /pets:
    get:
      responses:
        200:
          description: "List pets"
```

**Command:**

```bash
gal import -i openapi.yaml -p gcp_apigateway -o gal-config.yaml
```

**Output:** `gal-config.yaml`

```yaml
version: "1.0"
provider: gal

global_config:
  gcp_apigateway:
    api_id: "imported-api"
    api_display_name: "Pet Store API"
    project_id: "gcp-project"  # Default
    backend_address: "https://petstore-backend.example.com"

services:
  - name: imported-api
    type: rest
    protocol: https
    upstream:
      targets:
        - host: petstore-backend.example.com
          port: 443
    routes:
      - path_prefix: /pets
        methods:
          - GET
```

### Import mit JWT

**Input:** OpenAPI mit JWT

```yaml
swagger: "2.0"
info:
  title: "Secure API"
  version: "1.0.0"

x-google-backend:
  address: "https://backend.example.com"

securityDefinitions:
  google_jwt:
    authorizationUrl: ""
    flow: "implicit"
    type: "oauth2"
    x-google-issuer: "https://accounts.google.com"
    x-google-jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    x-google-audiences: "https://my-project.example.com"

security:
  - google_jwt: []

paths:
  /api/data:
    get:
      responses:
        200:
          description: "Get data"
```

**Output:** GAL Config mit JWT

```yaml
global_config:
  gcp_apigateway:
    jwt_issuer: "https://accounts.google.com"
    jwt_jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
    jwt_audiences:
      - "https://my-project.example.com"

services:
  - name: imported-api
    routes:
      - path_prefix: /api/data
        methods:
          - GET
        authentication:
          type: jwt
          jwt:
            issuer: "https://accounts.google.com"
            jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
            audience: "https://my-project.example.com"
```

## Migration zu anderen Providern

### GCP → AWS API Gateway

```bash
# 1. GCP importieren
gal import -i gcp-openapi.yaml -p gcp_apigateway -o gal-config.yaml

# 2. Provider ändern
sed -i 's/provider: gal/provider: aws_apigateway/' gal-config.yaml

# 3. AWS-spezifische Config hinzufügen
# Editiere gal-config.yaml: Füge global_config.aws_apigateway hinzu

# 4. AWS OpenAPI generieren
gal generate -c gal-config.yaml -p aws_apigateway > aws-openapi.yaml
```

**Wichtig:** OpenAPI 2.0 → 3.0 Upgrade automatisch

### GCP → Nginx/Kong/Traefik

```bash
# 1. GCP importieren
gal import -i gcp-openapi.yaml -p gcp_apigateway -o gal-config.yaml

# 2. Zu Nginx/Kong/etc. deployen
gal generate -c gal-config.yaml -p nginx > nginx.conf
gal generate -c gal-config.yaml -p kong > kong.yaml
```

## Limitierungen

| Limitation | Workaround |
|-----------|------------|
| Service Account Email nicht importiert | Manuell in Config eintragen |
| Project ID Extraktion best-effort | Project ID manuell setzen |
| Region nicht in OpenAPI Spec | Region manuell setzen |
| Per-Operation Backend nicht voll unterstützt | Globale Backend Config nutzen |

## Troubleshooting

### Import schlägt fehl: "Invalid OpenAPI format"

```bash
# Prüfe OpenAPI Version
grep "swagger:" openapi.yaml
# Muss sein: swagger: "2.0"

# Falls OpenAPI 3.0: GCP unterstützt nur 2.0
# Konvertierung zu 2.0 nötig
```

### Import schlägt fehl: "No backend URL found"

```bash
# Prüfe x-google-backend
grep -A 5 "x-google-backend" openapi.yaml

# Füge backend hinzu falls fehlend
x-google-backend:
  address: "https://backend.example.com"
```

### CORS nicht importiert

```bash
# Prüfe OPTIONS Methods
grep -A 10 "options:" openapi.yaml

# CORS wird nur importiert wenn OPTIONS Methods vorhanden
```

## Weitere Ressourcen

- [GCP API Gateway Guide](../guides/GCP_APIGATEWAY.md)
- [Migration Overview](migration.md)
- [Provider Compatibility](compatibility.md)
