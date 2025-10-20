# AWS API Gateway Provider Guide

**Letzte Aktualisierung:** 2025-10-20
**Status:** ✅ Production Ready (v1.4.0)

---

## Übersicht

AWS API Gateway ist ein vollständig verwalteter Service von Amazon Web Services, der es Entwicklern ermöglicht, APIs in beliebigem Umfang zu erstellen, zu veröffentlichen, zu verwalten, zu überwachen und zu sichern.

GAL unterstützt AWS API Gateway als **Cloud-Provider** mit vollständiger Import/Export-Funktionalität über OpenAPI 3.0 mit `x-amazon-apigateway` Extensions.

### Motivation

**Warum AWS API Gateway mit GAL?**

- **Cloud-Native**: Perfekt für AWS-basierte Microservices-Architekturen
- **Serverless**: Nahtlose Integration mit AWS Lambda
- **Skalierbarkeit**: Automatische Skalierung ohne Infrastruktur-Management
- **AWS-Ökosystem**: Integration mit Cognito, IAM, CloudWatch, WAF
- **Pay-per-Use**: Nur bezahlen für tatsächliche API-Aufrufe
- **Multi-Region**: Globale Verfügbarkeit mit CloudFront (EDGE Endpoints)

---

## AWS API Gateway Architektur

### REST API Komponenten

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS API Gateway                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  REST API                                            │  │
│  │  ├─ Stage (prod, staging, dev)                       │  │
│  │  ├─ Resources (/users, /products)                    │  │
│  │  ├─ Methods (GET, POST, PUT, DELETE)                 │  │
│  │  └─ Integrations                                     │  │
│  │     ├─ HTTP_PROXY    → Backend HTTP Service          │  │
│  │     ├─ AWS_PROXY     → Lambda Function               │  │
│  │     └─ MOCK          → Mock Response                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Authorization                                       │  │
│  │  ├─ API Keys         → x-api-key Header              │  │
│  │  ├─ Lambda Authorizer → Custom JWT Validation        │  │
│  │  ├─ Cognito User Pool → OAuth2/OIDC                  │  │
│  │  └─ IAM             → AWS Signature v4               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Usage Plans & Throttling                            │  │
│  │  ├─ Rate Limiting    → Requests per second           │  │
│  │  ├─ Quotas          → Daily/Monthly limits           │  │
│  │  └─ API Keys        → Subscription Management        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Monitoring & Logging                                │  │
│  │  ├─ CloudWatch Logs  → Access & Execution Logs       │  │
│  │  ├─ CloudWatch Metrics → Latency, Errors, Count      │  │
│  │  └─ X-Ray Tracing   → Distributed Tracing            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Endpoint-Typen

| Typ | Beschreibung | Verwendung |
|-----|-------------|------------|
| **REGIONAL** | API in einer spezifischen AWS Region | Latenz-sensitiv, Single-Region |
| **EDGE** | API über CloudFront global verteilt | Globale APIs, niedrige Latenz weltweit |
| **PRIVATE** | API nur innerhalb VPC erreichbar | Interne APIs, höchste Sicherheit |

---

## Schnellstart

### 1. Voraussetzungen

- AWS Account mit API Gateway Zugriff
- AWS CLI installiert und konfiguriert
- GAL installiert (`pip install gal-gateway`)

### 2. Einfache HTTP Proxy API

**GAL Konfiguration** (`config.yaml`):

```yaml
version: "1.0"
provider: aws_apigateway

global_config:
  aws_apigateway:
    api_name: "PetStore-API"
    api_description: "Pet Store REST API"
    endpoint_type: "REGIONAL"
    stage_name: "prod"
    integration_type: "HTTP_PROXY"
    cors_enabled: true

services:
  - name: petstore
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

**OpenAPI generieren:**

```bash
gal generate -c config.yaml -p aws_apigateway -o api.json
```

**Zu AWS deployen:**

```bash
# API erstellen
aws apigateway import-rest-api --body file://api.json

# API ID aus Output merken
export API_ID="abc123xyz"

# Deployment erstellen
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod

# API URL anzeigen
echo "https://${API_ID}.execute-api.us-east-1.amazonaws.com/prod"
```

---

## Konfigurationsoptionen

### Global Config

```yaml
global_config:
  aws_apigateway:
    # API Configuration
    api_name: "My-API"                    # API Name
    api_description: "My API Description" # Beschreibung
    endpoint_type: "REGIONAL"             # REGIONAL, EDGE, PRIVATE

    # Stage Configuration
    stage_name: "prod"                    # Stage Name (prod, dev, staging)
    stage_description: "Production Stage" # Stage Beschreibung

    # Integration Configuration
    integration_type: "HTTP_PROXY"        # HTTP_PROXY, AWS_PROXY, MOCK
    integration_timeout_ms: 29000         # Max: 29000ms

    # Lambda Integration (nur bei AWS_PROXY)
    lambda_function_arn: "arn:aws:lambda:..."
    lambda_invoke_role_arn: "arn:aws:iam:..."  # Optional

    # Authorization
    authorizer_type: null                 # lambda, cognito, iam
    lambda_authorizer_arn: null           # Lambda Authorizer ARN
    lambda_authorizer_ttl: 300            # Cache TTL (Sekunden)
    cognito_user_pool_arns: []            # Cognito User Pool ARNs

    # API Keys
    api_key_required: false               # API Key erforderlich
    api_key_source: "HEADER"              # HEADER oder AUTHORIZER

    # CORS
    cors_enabled: true
    cors_allow_origins: ["*"]
    cors_allow_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: ["Content-Type", "Authorization", "X-Api-Key"]
```

### Service Config

```yaml
services:
  - name: my_service
    type: rest                     # Immer "rest" für API Gateway
    protocol: https                # http oder https
    upstream:
      host: backend.example.com    # Backend Host
      port: 443                    # Backend Port

    routes:
      - path_prefix: /api/users
        methods:
          - GET
          - POST
        authentication:            # Optional: Route-Level Auth
          type: jwt
          jwt:
            issuer: "https://cognito-idp.us-east-1.amazonaws.com/..."
            audience: "my-app-client-id"
```

---

## Integration-Typen

### 1. HTTP_PROXY (HTTP Backend)

**Verwendung:** Proxy zu bestehenden HTTP/HTTPS Backends

```yaml
global_config:
  aws_apigateway:
    integration_type: "HTTP_PROXY"
    integration_timeout_ms: 29000

services:
  - name: backend_service
    protocol: https
    upstream:
      host: api.backend.com
      port: 443
    routes:
      - path_prefix: /api
        methods: [GET, POST]
```

**Generierte OpenAPI Extension:**

```json
{
  "x-amazon-apigateway-integration": {
    "type": "http_proxy",
    "httpMethod": "GET",
    "uri": "https://api.backend.com/api",
    "connectionType": "INTERNET",
    "timeoutInMillis": 29000,
    "passthroughBehavior": "when_no_match"
  }
}
```

**Vorteile:**
- ✅ Einfach zu konfigurieren
- ✅ Direkte Verbindung zu Backend
- ✅ Unterstützt alle HTTP-Methoden
- ✅ Keine zusätzlichen AWS-Services nötig

**Nachteile:**
- ❌ Kein automatisches Request/Response Mapping
- ❌ Backend muss öffentlich erreichbar sein (oder VPC Link)

---

### 2. AWS_PROXY (Lambda Integration)

**Verwendung:** Serverless APIs mit AWS Lambda

```yaml
global_config:
  aws_apigateway:
    integration_type: "AWS_PROXY"
    lambda_function_arn: "arn:aws:lambda:us-east-1:123456789012:function:my-function"
    lambda_invoke_role_arn: "arn:aws:iam::123456789012:role/api-gateway-invoke-lambda"

services:
  - name: lambda_service
    protocol: https
    upstream:
      host: lambda     # Placeholder
      port: 443
    routes:
      - path_prefix: /lambda
        methods: [POST]
```

**Generierte OpenAPI Extension:**

```json
{
  "x-amazon-apigateway-integration": {
    "type": "aws_proxy",
    "httpMethod": "POST",
    "uri": "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:my-function/invocations",
    "passthroughBehavior": "when_no_match",
    "timeoutInMillis": 29000
  }
}
```

**Lambda Event Format:**

```json
{
  "resource": "/lambda",
  "path": "/lambda",
  "httpMethod": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"key\":\"value\"}",
  "isBase64Encoded": false
}
```

**Lambda Response Format:**

```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"message\":\"Success\"}"
}
```

**Vorteile:**
- ✅ Serverless, keine Infrastruktur
- ✅ Automatische Skalierung
- ✅ Pay-per-Invocation
- ✅ Integration mit AWS Services

**Nachteile:**
- ❌ Cold Start Latenz
- ❌ 29 Sekunden Timeout-Limit
- ❌ Spezifisches Event/Response Format

---

### 3. MOCK (Mock Integration)

**Verwendung:** Mock-Responses für Testing/Development

```yaml
global_config:
  aws_apigateway:
    integration_type: "MOCK"

services:
  - name: mock_service
    protocol: https
    upstream:
      host: mock
      port: 443
    routes:
      - path_prefix: /mock
        methods: [GET]
```

**Generierte OpenAPI Extension:**

```json
{
  "x-amazon-apigateway-integration": {
    "type": "mock",
    "requestTemplates": {
      "application/json": "{\"statusCode\": 200}"
    },
    "responses": {
      "default": {
        "statusCode": "200",
        "responseTemplates": {
          "application/json": "{\"message\": \"Mock response\"}"
        }
      }
    }
  }
}
```

**Vorteile:**
- ✅ Kein Backend nötig
- ✅ Instant Responses
- ✅ Ideal für Frontend-Entwicklung

**Nachteile:**
- ❌ Statische Responses
- ❌ Keine Business-Logik

---

## Authentifizierung & Autorisierung

### 1. API Keys

**Verwendung:** Einfache API-Schlüssel für Subscriptions

```yaml
global_config:
  aws_apigateway:
    api_key_required: true
    api_key_source: "HEADER"

  authentication:
    type: api_key
    api_key:
      key_name: "x-api-key"
      keys: []  # Keys werden in AWS Console erstellt

services:
  - name: secured_api
    routes:
      - path_prefix: /secure
        methods: [GET]
        authentication:
          type: api_key
          api_key:
            key_name: "x-api-key"
```

**Request Example:**

```bash
curl -H "x-api-key: your-api-key-here" \
  https://api-id.execute-api.us-east-1.amazonaws.com/prod/secure
```

**API Keys erstellen:**

```bash
# API Key erstellen
aws apigateway create-api-key \
  --name "MyAppKey" \
  --enabled

# Usage Plan erstellen
aws apigateway create-usage-plan \
  --name "BasicPlan" \
  --throttle burstLimit=1000,rateLimit=500

# API Key zu Usage Plan hinzufügen
aws apigateway create-usage-plan-key \
  --usage-plan-id <plan-id> \
  --key-id <key-id> \
  --key-type API_KEY
```

**Vorteile:**
- ✅ Einfach zu implementieren
- ✅ Built-in Usage Plans
- ✅ Rate Limiting pro API Key

**Nachteile:**
- ❌ Keine User-Identität
- ❌ Keys müssen sicher gespeichert werden

---

### 2. Lambda Authorizer (Custom JWT)

**Verwendung:** Custom Authorization Logic mit Lambda

```yaml
global_config:
  aws_apigateway:
    authorizer_type: "lambda"
    lambda_authorizer_arn: "arn:aws:lambda:us-east-1:123456789012:function:my-authorizer"
    lambda_authorizer_ttl: 300

services:
  - name: protected_api
    routes:
      - path_prefix: /protected
        methods: [GET]
        authentication:
          type: jwt
          jwt:
            issuer: "https://auth.example.com"
            audience: "my-api"
```

**Lambda Authorizer Function (Python):**

```python
import json

def lambda_handler(event, context):
    token = event['authorizationToken']  # "Bearer <token>"

    # Validate JWT token (simplified)
    if is_valid_token(token):
        return generate_policy('user123', 'Allow', event['methodArn'])
    else:
        raise Exception('Unauthorized')

def generate_policy(principal_id, effect, resource):
    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource
            }]
        },
        'context': {
            'userId': principal_id,
            'role': 'user'
        }
    }

def is_valid_token(token):
    # Implement JWT validation logic
    # Verify signature, expiration, issuer, audience
    return True
```

**Request Example:**

```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  https://api-id.execute-api.us-east-1.amazonaws.com/prod/protected
```

**Vorteile:**
- ✅ Vollständige Kontrolle über Authorization
- ✅ Custom Claims-Validierung
- ✅ Cached Responses (TTL)
- ✅ Context-Weitergabe zu Backend

**Nachteile:**
- ❌ Zusätzliche Lambda-Funktion nötig
- ❌ Cold Start bei erstem Request
- ❌ Implementierung muss selbst erfolgen

---

### 3. Cognito User Pools (OAuth2/OIDC)

**Verwendung:** AWS-managed User Authentication

```yaml
global_config:
  aws_apigateway:
    authorizer_type: "cognito"
    cognito_user_pool_arns:
      - "arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_AbCdEfGhI"

services:
  - name: user_api
    routes:
      - path_prefix: /profile
        methods: [GET, PUT]
        authentication:
          type: jwt
          jwt:
            issuer: "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEfGhI"
            audience: "my-app-client-id"
```

**Cognito Token erhalten:**

```bash
# User Login
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <client-id> \
  --auth-parameters USERNAME=user@example.com,PASSWORD=SecurePass123
```

**Request Example:**

```bash
curl -H "Authorization: Bearer <id-token>" \
  https://api-id.execute-api.us-east-1.amazonaws.com/prod/profile
```

**Vorteile:**
- ✅ Vollständig verwaltete User Pools
- ✅ OAuth2/OIDC Standard
- ✅ Multi-Factor Authentication (MFA)
- ✅ Social Identity Providers (Google, Facebook)
- ✅ Keine Lambda-Funktion nötig

**Nachteile:**
- ❌ AWS Cognito Lock-in
- ❌ Komplexe Konfiguration
- ❌ Kosten pro Monthly Active User

---

## CORS-Konfiguration

### Automatisches CORS Setup

```yaml
global_config:
  aws_apigateway:
    cors_enabled: true
    cors_allow_origins:
      - "https://app.example.com"
      - "https://admin.example.com"
    cors_allow_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS
    cors_allow_headers:
      - Content-Type
      - Authorization
      - X-Api-Key
```

**Generierte OPTIONS Method:**

```json
{
  "options": {
    "responses": {
      "200": {
        "description": "CORS preflight response",
        "headers": {
          "Access-Control-Allow-Origin": {"schema": {"type": "string"}},
          "Access-Control-Allow-Methods": {"schema": {"type": "string"}},
          "Access-Control-Allow-Headers": {"schema": {"type": "string"}}
        }
      }
    },
    "x-amazon-apigateway-integration": {
      "type": "mock",
      "requestTemplates": {
        "application/json": "{\"statusCode\": 200}"
      },
      "responses": {
        "default": {
          "statusCode": "200",
          "responseParameters": {
            "method.response.header.Access-Control-Allow-Origin": "'https://app.example.com,https://admin.example.com'",
            "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'",
            "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization,X-Api-Key'"
          }
        }
      }
    }
  }
}
```

**Browser Preflight Request:**

```http
OPTIONS /api/users HTTP/1.1
Host: api-id.execute-api.us-east-1.amazonaws.com
Origin: https://app.example.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type, Authorization
```

**Server Response:**

```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization, X-Api-Key
Access-Control-Max-Age: 86400
```

---

## Deployment-Strategien

### 1. AWS CLI Deployment

```bash
# 1. OpenAPI generieren
gal generate -c config.yaml -p aws_apigateway -o api.json

# 2. API erstellen
API_ID=$(aws apigateway import-rest-api \
  --body file://api.json \
  --query 'id' --output text)

echo "API ID: $API_ID"

# 3. Deployment erstellen
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --description "Initial deployment"

# 4. API URL
echo "API URL: https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
```

---

### 2. Terraform Deployment

**terraform/main.tf:**

```hcl
resource "aws_api_gateway_rest_api" "api" {
  name        = "PetStore-API"
  description = "Pet Store REST API managed by GAL"
  body        = file("${path.module}/api.json")

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_deployment" "prod" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = "prod"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.prod.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "prod"

  xray_tracing_enabled = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format          = "$context.requestId"
  }
}

resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/petstore"
  retention_in_days = 7
}

output "api_url" {
  value = "${aws_api_gateway_stage.prod.invoke_url}"
}
```

**Deployment:**

```bash
# OpenAPI generieren
gal generate -c config.yaml -p aws_apigateway -o terraform/api.json

# Terraform apply
cd terraform
terraform init
terraform plan
terraform apply

# API URL ausgeben
terraform output api_url
```

---

### 3. CI/CD mit GitHub Actions

**.github/workflows/deploy-api.yml:**

```yaml
name: Deploy AWS API Gateway

on:
  push:
    branches:
      - main
    paths:
      - 'api-config.yaml'
      - '.github/workflows/deploy-api.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install GAL
        run: pip install gal-gateway

      - name: Generate OpenAPI
        run: |
          gal generate \
            -c api-config.yaml \
            -p aws_apigateway \
            -o api.json

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Deploy to AWS
        run: |
          # API erstellen oder updaten
          if aws apigateway get-rest-api --rest-api-id ${{ secrets.API_ID }} 2>/dev/null; then
            # Update existing API
            aws apigateway put-rest-api \
              --rest-api-id ${{ secrets.API_ID }} \
              --mode overwrite \
              --body file://api.json
          else
            # Create new API
            API_ID=$(aws apigateway import-rest-api \
              --body file://api.json \
              --query 'id' --output text)
            echo "API_ID=$API_ID" >> $GITHUB_ENV
          fi

          # Create deployment
          aws apigateway create-deployment \
            --rest-api-id ${{ secrets.API_ID }} \
            --stage-name prod \
            --description "Deployed from GitHub Actions"

      - name: Output API URL
        run: |
          echo "API deployed to:"
          echo "https://${{ secrets.API_ID }}.execute-api.us-east-1.amazonaws.com/prod"
```

---

### 4. Blue-Green Deployment

**Konzept:** Zero-Downtime Updates mit Stage-Wechsel

```bash
# 1. Aktuellen Stand sichern
OLD_STAGE="prod"
NEW_STAGE="prod-v2"

# 2. Neue Version deployen
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name $NEW_STAGE \
  --description "Blue-Green deployment v2"

# 3. Neue Version testen
curl https://${API_ID}.execute-api.us-east-1.amazonaws.com/${NEW_STAGE}/health

# 4. Traffic umleiten (Custom Domain)
aws apigateway update-base-path-mapping \
  --domain-name api.example.com \
  --base-path "" \
  --patch-operations op=replace,path=/stage,value=$NEW_STAGE

# 5. Alte Version löschen (nach Bestätigung)
aws apigateway delete-stage \
  --rest-api-id $API_ID \
  --stage-name $OLD_STAGE
```

---

## Import von bestehenden AWS APIs

### Export aus AWS API Gateway

```bash
# Liste aller APIs
aws apigateway get-rest-apis

# API exportieren (OpenAPI 3.0)
aws apigateway get-export \
  --rest-api-id <api-id> \
  --stage-name prod \
  --export-type oas30 \
  --accepts application/json > api-export.json
```

### Import zu GAL

```bash
# OpenAPI zu GAL Config konvertieren
gal import \
  -i api-export.json \
  -p aws_apigateway \
  -o gal-config.yaml

# Konvertierte Config prüfen
cat gal-config.yaml
```

**Beispiel Export:**

```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "PetStore API",
    "version": "1.0.0"
  },
  "paths": {
    "/pets": {
      "get": {
        "x-amazon-apigateway-integration": {
          "type": "http_proxy",
          "httpMethod": "GET",
          "uri": "https://petstore.example.com/pets"
        }
      }
    }
  }
}
```

**Konvertierte GAL Config:**

```yaml
version: "1.0"
provider: gal

global_config:
  aws_apigateway:
    api_name: "PetStore API"
    api_description: ""
    endpoint_type: "REGIONAL"
    stage_name: "prod"
    integration_type: "HTTP_PROXY"
    cors_enabled: false

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
```

**Was wird importiert:**
- ✅ API Name, Description, Version
- ✅ Routes (Paths) und HTTP Methods
- ✅ Integration Type (HTTP_PROXY, AWS_PROXY, MOCK)
- ✅ Lambda ARNs (bei AWS_PROXY)
- ✅ Cognito User Pool ARNs
- ✅ API Key Configuration
- ✅ CORS Configuration

**Was wird NICHT importiert:**
- ❌ Usage Plans (Rate Limiting)
- ❌ WAF Rules
- ❌ Stage Variables
- ❌ Deployment Configurations
- ❌ API Keys (nur Header-Name)
- ❌ VTL Mapping Templates

---

## Best Practices

### 1. API-Design

**✅ DO:**
- Verwende REST-konforme Resource-Namen (`/users`, `/products`)
- Versioniere deine API (`/v1/users`, `/v2/users`)
- Nutze HTTP-Methoden korrekt (GET, POST, PUT, DELETE)
- Implementiere Health Check Endpoints (`/health`, `/ready`)

**❌ DON'T:**
- Vermeide Verben in Pfaden (`/getUser`, `/createProduct`)
- Nutze keine inkonsistente Namenskonventionen
- Exposiere keine Backend-Implementierungsdetails

---

### 2. SKU-Auswahl

| SKU | Requests/Monat | Kosten | Verwendung |
|-----|---------------|--------|------------|
| **REST API** | Pay-per-Request | $3.50/Million | Standard-APIs, volle Features |
| **HTTP API** | Pay-per-Request | $1.00/Million | Einfache APIs, weniger Features |
| **WebSocket API** | Pay-per-Message | $1.00/Million | Real-time APIs |

**Empfehlung:** Nutze REST API für volle Feature-Unterstützung (Lambda Authorizer, Usage Plans, etc.)

---

### 3. Subscription Management (API Keys)

**Strategie:**
1. **Usage Plans** für verschiedene Tiers (Free, Basic, Premium)
2. **API Keys** pro Customer/Application
3. **Rate Limiting** pro Usage Plan
4. **Quotas** für monatliche Limits

**Beispiel:**

```bash
# Free Tier
aws apigateway create-usage-plan \
  --name "FreeTier" \
  --throttle burstLimit=100,rateLimit=10 \
  --quota limit=10000,period=MONTH

# Premium Tier
aws apigateway create-usage-plan \
  --name "PremiumTier" \
  --throttle burstLimit=5000,rateLimit=1000 \
  --quota limit=1000000,period=MONTH
```

---

### 4. Rate Limiting

**Empfehlungen:**

```yaml
# Konservativ (kleine APIs)
throttle:
  burst_limit: 100
  rate_limit: 50

# Standard (mittlere APIs)
throttle:
  burst_limit: 1000
  rate_limit: 500

# Aggressiv (große APIs)
throttle:
  burst_limit: 5000
  rate_limit: 2000
```

**Hinweis:** Rate Limiting wird in AWS API Gateway über **Usage Plans** konfiguriert, nicht über OpenAPI.

---

### 5. Security

**✅ Implementiere:**
- ✅ HTTPS Only (HTTP wird automatisch zu HTTPS umgeleitet)
- ✅ API Keys für öffentliche APIs
- ✅ Cognito/Lambda Authorizer für User-APIs
- ✅ IAM Authorization für Service-to-Service
- ✅ AWS WAF für DDoS-Schutz
- ✅ CloudWatch Logs für Audit Trail

**✅ Nutze AWS Services:**
- AWS WAF: DDoS Protection, SQL Injection, XSS
- AWS Shield: DDoS Protection
- AWS Secrets Manager: Sichere API Keys
- AWS Certificate Manager: SSL/TLS Zertifikate

---

### 6. Monitoring & Logging

**CloudWatch Metrics:**

```bash
# API Gateway Metrics anzeigen
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=PetStore-API \
  --start-time 2025-10-20T00:00:00Z \
  --end-time 2025-10-20T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

**Wichtige Metriken:**
- **Count**: Anzahl API-Requests
- **4XXError**: Client-Fehler
- **5XXError**: Server-Fehler
- **Latency**: Response-Zeit
- **IntegrationLatency**: Backend-Response-Zeit

**CloudWatch Logs aktivieren:**

```bash
aws apigateway update-stage \
  --rest-api-id $API_ID \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/accessLogSettings/destinationArn,value=arn:aws:logs:... \
    op=replace,path=/accessLogSettings/format,value='$context.requestId'
```

---

## Troubleshooting

### 1. "Missing Authentication Token"

**Problem:** API Request ohne Authentication

**Ursache:** Falscher Pfad oder fehlende Authorization

**Lösung:**

```bash
# Prüfe API URL
aws apigateway get-rest-api --rest-api-id $API_ID

# Prüfe Stage
aws apigateway get-stage --rest-api-id $API_ID --stage-name prod

# Korrekter Request
curl -H "Authorization: Bearer <token>" \
  https://${API_ID}.execute-api.us-east-1.amazonaws.com/prod/api/users
```

---

### 2. "Execution failed due to configuration error: Invalid permissions on Lambda function"

**Problem:** API Gateway kann Lambda nicht aufrufen

**Lösung:**

```bash
# Lambda Permission hinzufügen
aws lambda add-permission \
  --function-name my-function \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:123456789012:${API_ID}/*/*"
```

---

### 3. "Forbidden" bei Cognito Authorization

**Problem:** Cognito Token wird nicht akzeptiert

**Prüfung:**

```bash
# Token dekodieren (JWT)
echo "eyJhbGc..." | base64 -d

# Prüfe:
# - iss (Issuer) = Cognito User Pool URL
# - aud (Audience) = App Client ID
# - exp (Expiration) > current time
```

**Lösung:** Token neu anfordern mit korrekten Parametern

---

### 4. CORS Preflight Fehler

**Problem:** Browser blockiert Request wegen CORS

**Lösung:**

```yaml
global_config:
  aws_apigateway:
    cors_enabled: true
    cors_allow_origins:
      - "https://your-app.com"  # Nicht "*" in Production!
    cors_allow_methods: [GET, POST, PUT, DELETE, OPTIONS]
    cors_allow_headers: [Content-Type, Authorization]
```

**Deployment:**

```bash
gal generate -c config.yaml -p aws_apigateway -o api.json
aws apigateway put-rest-api --rest-api-id $API_ID --mode overwrite --body file://api.json
aws apigateway create-deployment --rest-api-id $API_ID --stage-name prod
```

---

### 5. Lambda Timeout (504 Gateway Timeout)

**Problem:** Lambda Function läuft länger als API Gateway Timeout (29s)

**Lösung:**

```yaml
# Reduziere Lambda Execution Time
global_config:
  aws_apigateway:
    integration_timeout_ms: 29000  # Max: 29000ms

# Oder verwende Asynchrone Patterns (SQS, Step Functions)
```

---

## Beispiele

Vollständige Beispiele finden Sie in `examples/aws-apigateway-example.yaml`:

1. ✅ **Basic HTTP Proxy** - Einfache Backend-Integration
2. ✅ **Lambda Integration** - Serverless API
3. ✅ **Cognito Authentication** - User-basierte APIs
4. ✅ **Lambda Authorizer** - Custom Authorization
5. ✅ **Multi-Backend** - Microservices Gateway
6. ✅ **EDGE Endpoint** - Global Distribution
7. ✅ **Mock Integration** - Development/Testing

---

## Provider-Vergleich

| Feature | AWS API Gateway | Azure APIM | Kong | Envoy |
|---------|----------------|------------|------|-------|
| **Deployment** | Cloud (AWS) | Cloud (Azure) | Self-Hosted | Self-Hosted |
| **Serverless** | ✅ Lambda | ✅ Functions | ❌ | ❌ |
| **Pricing** | Pay-per-Request | Pay-per-Request | Free/Enterprise | Free |
| **Auto-Scaling** | ✅ Automatic | ✅ Automatic | Manual | Manual |
| **Multi-Region** | ✅ EDGE | ✅ Multi-Region | Manual | Manual |
| **WAF Integration** | ✅ AWS WAF | ✅ Azure WAF | Plugins | Envoy WAF |
| **Vendor Lock-in** | ⚠️ AWS | ⚠️ Azure | ✅ Open | ✅ Open |

**Empfehlung:**
- **AWS API Gateway**: Wenn Sie bereits AWS nutzen und Serverless bevorzugen
- **Azure APIM**: Wenn Sie Azure-native sind
- **Kong/Envoy**: Wenn Sie Multi-Cloud oder On-Premise benötigen

---

## Weiterführende Ressourcen

### AWS Dokumentation

- [AWS API Gateway Developer Guide](https://docs.aws.amazon.com/apigateway/)
- [OpenAPI Extensions for API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions.html)
- [Lambda Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html)
- [Cognito User Pools](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html)

### GAL Dokumentation

- [Schnellstart-Guide](QUICKSTART.md)
- [Provider-Übersicht](PROVIDERS.md)
- [Authentication Guide](AUTHENTICATION.md)
- [Import/Export Guide](../import/aws-apigateway.md)

### Beispiele

- [AWS API Gateway Examples](https://github.com/pt9912/x-gal/blob/main/examples/aws-apigateway-example.yaml)
- [GitHub Actions Workflow](https://github.com/pt9912/x-gal/blob/main/.github/workflows/deploy-api.yml)

---

**Version:** 1.4.0
**Status:** ✅ Production Ready
**Letztes Update:** 2025-10-20
