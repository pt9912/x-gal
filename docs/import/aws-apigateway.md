# AWS API Gateway Import Guide

**Letzte Aktualisierung:** 2025-10-20

---

## Übersicht

GAL kann bestehende AWS API Gateway REST APIs über **OpenAPI 3.0 Exports** importieren und in provider-agnostische GAL-Konfigurationen umwandeln.

### Was wird importiert

✅ **Vollständig unterstützt:**
- API Name, Description, Version
- Routes (Paths) und HTTP Methods
- Integration Types (HTTP_PROXY, AWS_PROXY, MOCK)
- Backend URLs (bei HTTP_PROXY)
- Lambda Function ARNs (bei AWS_PROXY)
- Authentication Konfiguration:
  - API Keys (x-api-key Header)
  - Lambda Authorizers
  - Cognito User Pools
- CORS Konfiguration

❌ **NICHT importiert** (OpenAPI-Limitierungen):
- Usage Plans & Rate Limiting
- Stage Variables
- WAF Rules
- Deployment Configurations
- API Key Values (nur Header-Name)
- VTL (Velocity Template Language) Templates
- CloudWatch Settings

---

## Schnellstart

### 1. AWS API Gateway exportieren

```bash
# Liste aller APIs
aws apigateway get-rest-apis

# Output zeigt API IDs:
# {
#   "items": [
#     {
#       "id": "abc123xyz",
#       "name": "PetStore-API",
#       "description": "Pet Store REST API"
#     }
#   ]
# }

# API als OpenAPI 3.0 exportieren
aws apigateway get-export \
  --rest-api-id abc123xyz \
  --stage-name prod \
  --export-type oas30 \
  --accepts application/json > petstore-api.json
```

**Alternativer Export (YAML):**

```bash
aws apigateway get-export \
  --rest-api-id abc123xyz \
  --stage-name prod \
  --export-type oas30 \
  --accepts application/x-yaml > petstore-api.yaml
```

---

### 2. Zu GAL importieren

```bash
# JSON Import
gal import \
  -i petstore-api.json \
  -p aws_apigateway \
  -o petstore-gal.yaml

# YAML Import
gal import \
  -i petstore-api.yaml \
  -p aws_apigateway \
  -o petstore-gal.yaml
```

---

### 3. Importierte Config prüfen

```bash
cat petstore-gal.yaml
```

**Beispiel-Output:**

```yaml
version: "1.0"
provider: gal

global_config:
  aws_apigateway:
    api_name: "PetStore-API"
    api_description: "Pet Store REST API"
    endpoint_type: "REGIONAL"
    stage_name: "prod"
    integration_type: "HTTP_PROXY"
    api_key_required: false
    cors_enabled: true
    cors_allow_origins:
      - "*"
    cors_allow_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS
    cors_allow_headers:
      - Content-Type
      - Authorization

services:
  - name: imported-api
    type: rest
    protocol: https
    upstream:
      host: petstore.example.com
      port: 443
    routes:
      - path_prefix: /pets
        methods:
          - GET
          - POST
      - path_prefix: /pets/{id}
        methods:
          - GET
          - PUT
          - DELETE
```

---

## Import-Szenarien

### Szenario 1: HTTP Proxy API

**AWS API Gateway Export:**

```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "Backend-Proxy",
    "version": "1.0.0"
  },
  "paths": {
    "/api/users": {
      "get": {
        "responses": {
          "200": {"description": "Success"}
        },
        "x-amazon-apigateway-integration": {
          "type": "http_proxy",
          "httpMethod": "GET",
          "uri": "https://backend.example.com/api/users",
          "connectionType": "INTERNET",
          "timeoutInMillis": 29000
        }
      }
    }
  }
}
```

**Importierte GAL Config:**

```yaml
version: "1.0"
provider: gal

global_config:
  aws_apigateway:
    api_name: "Backend-Proxy"
    integration_type: "HTTP_PROXY"
    integration_timeout_ms: 29000

services:
  - name: imported-api
    type: rest
    protocol: https
    upstream:
      host: backend.example.com
      port: 443
    routes:
      - path_prefix: /api/users
        methods:
          - GET
```

---

### Szenario 2: Lambda Integration (AWS_PROXY)

**AWS API Gateway Export:**

```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "Lambda-API",
    "version": "1.0.0"
  },
  "paths": {
    "/lambda": {
      "post": {
        "responses": {
          "200": {"description": "Success"}
        },
        "x-amazon-apigateway-integration": {
          "type": "aws_proxy",
          "httpMethod": "POST",
          "uri": "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:my-function/invocations"
        }
      }
    }
  }
}
```

**Importierte GAL Config:**

```yaml
version: "1.0"
provider: gal

global_config:
  aws_apigateway:
    api_name: "Lambda-API"
    integration_type: "AWS_PROXY"
    lambda_function_arn: "arn:aws:lambda:us-east-1:123456789012:function:my-function"

services:
  - name: imported-api
    type: rest
    protocol: https
    upstream:
      host: lambda
      port: 443
    routes:
      - path_prefix: /lambda
        methods:
          - POST
```

---

### Szenario 3: API Key Authentication

**AWS API Gateway Export:**

```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "Secured-API",
    "version": "1.0.0"
  },
  "x-amazon-apigateway-api-key-source": "HEADER",
  "components": {
    "securitySchemes": {
      "api_key": {
        "type": "apiKey",
        "name": "x-api-key",
        "in": "header"
      }
    }
  },
  "paths": {
    "/secure": {
      "get": {
        "security": [{"api_key": []}],
        "responses": {
          "200": {"description": "Success"}
        },
        "x-amazon-apigateway-integration": {
          "type": "http_proxy",
          "uri": "https://api.example.com/secure"
        }
      }
    }
  }
}
```

**Importierte GAL Config:**

```yaml
version: "1.0"
provider: gal

global_config:
  aws_apigateway:
    api_name: "Secured-API"
    api_key_required: true
    api_key_source: "HEADER"

services:
  - name: imported-api
    type: rest
    protocol: https
    upstream:
      host: api.example.com
      port: 443
    routes:
      - path_prefix: /secure
        methods:
          - GET
        authentication:
          type: api_key
          api_key:
            key_name: "x-api-key"
            keys: []  # Keys müssen manuell hinzugefügt werden
```

---

### Szenario 4: Cognito User Pool Authentication

**AWS API Gateway Export:**

```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "User-API",
    "version": "1.0.0"
  },
  "components": {
    "securitySchemes": {
      "cognito_authorizer": {
        "type": "apiKey",
        "name": "Authorization",
        "in": "header",
        "x-amazon-apigateway-authtype": "cognito_user_pools",
        "x-amazon-apigateway-authorizer": {
          "type": "cognito_user_pools",
          "providerARNs": [
            "arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_AbCdEfGhI"
          ]
        }
      }
    }
  },
  "paths": {
    "/profile": {
      "get": {
        "security": [{"cognito_authorizer": []}],
        "responses": {
          "200": {"description": "Success"}
        },
        "x-amazon-apigateway-integration": {
          "type": "http_proxy",
          "uri": "https://api.example.com/profile"
        }
      }
    }
  }
}
```

**Importierte GAL Config:**

```yaml
version: "1.0"
provider: gal

global_config:
  aws_apigateway:
    api_name: "User-API"
    authorizer_type: "cognito"
    cognito_user_pool_arns:
      - "arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_AbCdEfGhI"

services:
  - name: imported-api
    type: rest
    protocol: https
    upstream:
      host: api.example.com
      port: 443
    routes:
      - path_prefix: /profile
        methods:
          - GET
        authentication:
          type: jwt
          jwt:
            issuer: "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEfGhI"
            audience: ""  # Wird beim Export nicht bereitgestellt
```

**Hinweis:** Die `audience` (App Client ID) ist im OpenAPI Export nicht enthalten und muss manuell ergänzt werden.

---

### Szenario 5: CORS Configuration

**AWS API Gateway Export:**

```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "CORS-API",
    "version": "1.0.0"
  },
  "paths": {
    "/api": {
      "get": {
        "responses": {
          "200": {"description": "Success"}
        },
        "x-amazon-apigateway-integration": {
          "type": "http_proxy",
          "uri": "https://api.example.com/api"
        }
      },
      "options": {
        "responses": {
          "200": {
            "description": "CORS preflight",
            "headers": {
              "Access-Control-Allow-Origin": {"schema": {"type": "string"}},
              "Access-Control-Allow-Methods": {"schema": {"type": "string"}},
              "Access-Control-Allow-Headers": {"schema": {"type": "string"}}
            }
          }
        },
        "x-amazon-apigateway-integration": {
          "type": "mock",
          "responses": {
            "default": {
              "statusCode": "200",
              "responseParameters": {
                "method.response.header.Access-Control-Allow-Origin": "'https://app.example.com'",
                "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'",
                "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization'"
              }
            }
          }
        }
      }
    }
  }
}
```

**Importierte GAL Config:**

```yaml
version: "1.0"
provider: gal

global_config:
  aws_apigateway:
    api_name: "CORS-API"
    cors_enabled: true
    cors_allow_origins:
      - "https://app.example.com"
    cors_allow_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS
    cors_allow_headers:
      - Content-Type
      - Authorization

services:
  - name: imported-api
    type: rest
    protocol: https
    upstream:
      host: api.example.com
      port: 443
    routes:
      - path_prefix: /api
        methods:
          - GET
```

---

## Post-Import Anpassungen

### 1. Backend URL anpassen

```yaml
# Original Import
services:
  - name: imported-api
    upstream:
      host: old-backend.example.com
      port: 443

# Angepasst
services:
  - name: imported-api
    upstream:
      host: new-backend.example.com
      port: 8080
```

---

### 2. Rate Limiting hinzufügen

**Hinweis:** Usage Plans werden NICHT exportiert. Manuell hinzufügen:

```yaml
global_config:
  rate_limiting:
    requests_per_second: 100
    burst: 200
```

---

### 3. Authentication erweitern

```yaml
# Cognito Audience ergänzen
routes:
  - path_prefix: /profile
    authentication:
      type: jwt
      jwt:
        issuer: "https://cognito-idp.us-east-1.amazonaws.com/pool-id"
        audience: "my-app-client-id"  # Manuell hinzufügen
```

---

### 4. Zu anderem Provider migrieren

```bash
# Import von AWS API Gateway
gal import -i api.json -p aws_apigateway -o gal-config.yaml

# Provider ändern
sed -i 's/provider: gal/provider: kong/' gal-config.yaml

# Für Kong generieren
gal generate -c gal-config.yaml -p kong -o kong-config.yaml
```

---

## Troubleshooting

### Problem: "Invalid OpenAPI format"

**Ursache:** Ungültiges JSON/YAML oder falsche OpenAPI-Version

**Lösung:**

```bash
# Prüfe OpenAPI-Version
cat api.json | grep "openapi"
# Sollte sein: "openapi": "3.0.1"

# Validiere JSON
cat api.json | jq .

# Validiere YAML
python -c "import yaml; yaml.safe_load(open('api.yaml'))"
```

---

### Problem: "No backend URL found"

**Ursache:** Keine HTTP_PROXY Integration gefunden

**Lösung:**

Die importierte Config verwendet einen Fallback:

```yaml
services:
  - upstream:
      host: backend.example.com  # Fallback
      port: 443
```

**Manuell korrigieren:**

```yaml
services:
  - upstream:
      host: actual-backend.com
      port: 8080
```

---

### Problem: Lambda ARN nicht extrahiert

**Ursache:** Ungültiges URI-Format in x-amazon-apigateway-integration

**Prüfung:**

```bash
cat api.json | jq '.paths[].*.["x-amazon-apigateway-integration"].uri'
```

**Erwartetes Format:**

```
arn:aws:apigateway:REGION:lambda:path/2015-03-31/functions/ARN/invocations
```

---

### Problem: CORS wird nicht erkannt

**Ursache:** OPTIONS-Methode fehlt oder hat keine CORS-Integration

**Lösung:** CORS manuell aktivieren:

```yaml
global_config:
  aws_apigateway:
    cors_enabled: true
    cors_allow_origins: ["*"]
    cors_allow_methods: [GET, POST, PUT, DELETE, OPTIONS]
    cors_allow_headers: [Content-Type, Authorization]
```

---

## Migration-Workflow

### AWS → GAL → Anderer Provider

```bash
# 1. Export von AWS
aws apigateway get-export \
  --rest-api-id abc123 \
  --stage-name prod \
  --export-type oas30 > aws-api.json

# 2. Import zu GAL
gal import -i aws-api.json -p aws_apigateway -o gal-config.yaml

# 3. Config anpassen
vim gal-config.yaml

# 4. Zu anderem Provider migrieren
gal generate -c gal-config.yaml -p kong -o kong-config.yaml
gal generate -c gal-config.yaml -p envoy -o envoy-config.yaml
gal generate -c gal-config.yaml -p azure_apim -o azure-config.json
```

---

## Best Practices

### 1. ✅ Version Control

```bash
# Import mit Git-Tracking
git checkout -b import/aws-api-gateway

gal import -i api.json -p aws_apigateway -o gal-config.yaml

git add gal-config.yaml
git commit -m "feat: Import AWS API Gateway configuration"

# Review und Merge
git diff main...import/aws-api-gateway
```

---

### 2. ✅ Backup vor Migration

```bash
# Backup der Original-Config
cp gal-config.yaml gal-config.yaml.backup

# Migration durchführen
gal generate -c gal-config.yaml -p kong -o kong-config.yaml

# Bei Problemen: Restore
cp gal-config.yaml.backup gal-config.yaml
```

---

### 3. ✅ Validierung nach Import

```bash
# Config validieren
gal validate -c gal-config.yaml

# Test-Generierung
gal generate -c gal-config.yaml -p aws_apigateway -o test-api.json

# JSON validieren
cat test-api.json | jq .
```

---

### 4. ✅ Inkrementelle Migration

```bash
# Route für Route migrieren
# 1. Importiere Original
gal import -i full-api.json -p aws_apigateway -o original.yaml

# 2. Erstelle Subset Config
# routes:
#   - path_prefix: /users  # Nur User-Routes

# 3. Teste Subset
gal generate -c subset.yaml -p kong

# 4. Erweitere schrittweise
```

---

## Python API

```python
from gal.providers import AWSAPIGatewayProvider

# Provider initialisieren
provider = AWSAPIGatewayProvider()

# OpenAPI Export laden
with open('api.json') as f:
    openapi_content = f.read()

# Zu GAL Config importieren
config = provider.parse(openapi_content)

# Config inspizieren
print(f"API Name: {config.global_config.aws_apigateway.api_name}")
print(f"Services: {len(config.services)}")
print(f"Routes: {len(config.services[0].routes)}")

# Zu YAML exportieren
import yaml
from dataclasses import asdict

with open('gal-config.yaml', 'w') as f:
    yaml.dump(asdict(config), f)
```

---

## Weiterführende Ressourcen

- [AWS API Gateway Export Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-export-api.html)
- [OpenAPI 3.0 Specification](https://spec.openapis.org/oas/v3.0.3)
- [x-amazon-apigateway Extensions](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions.html)
- [GAL AWS API Gateway Guide](../guides/AWS_APIGATEWAY.md)

---

**Version:** 1.4.0
**Status:** ✅ Production Ready
**Letztes Update:** 2025-10-20
