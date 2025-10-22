# AWS API Gateway Feature-Implementierungen

**Detaillierte Implementierung aller Features für AWS API Gateway Provider in GAL**

**Navigation:**
- [← Zurück zur AWS API Gateway Übersicht](AWS_APIGATEWAY.md)
- [→ Deployment & Migration](AWS_APIGATEWAY_DEPLOYMENT.md)

## Inhaltsverzeichnis

1. [Integration-Typen](#integration-typen)
2. [Authentifizierung & Autorisierung](#authentifizierung--autorisierung)
3. [CORS-Konfiguration](#cors-konfiguration)
4. [Beispiele](#beispiele)

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

## Request Mirroring

⚠️ **Workaround: Lambda@Edge**

AWS API Gateway unterstützt Request Mirroring nicht nativ. GAL konfiguriert einen **Lambda@Edge Workaround**.

**GAL Config:**
```yaml
services:
  - name: user_api
    protocol: http
    upstream:
      targets:
        - host: backend.example.com
          port: 443
    routes:
      - path_prefix: /api/users
        mirroring:
          enabled: true
          mirroring_lambda_edge_arn: "arn:aws:lambda:us-east-1:123456789012:function:mirror-function:1"
          targets:
            - name: shadow-backend
              upstream:
                host: shadow.example.com
                port: 443
              sample_percentage: 50
              timeout: 5
              headers:
                X-Mirror: "true"
                X-Shadow-Version: "v2"
```

**Lambda@Edge Function (mirror-function):**
```javascript
// Lambda@Edge Viewer Request Handler
exports.handler = async (event) => {
  const request = event.Records[0].cf.request;
  const https = require('https');

  // Sample percentage logic (50%)
  const sampleRate = parseInt(process.env.SAMPLE_PERCENTAGE || '50');
  if (Math.random() * 100 < sampleRate) {
    // Mirror request to shadow backend (fire-and-forget)
    const mirrorRequest = {
      hostname: process.env.SHADOW_HOST,  // shadow.example.com
      port: 443,
      path: request.uri,
      method: request.method,
      headers: {
        ...request.headers,
        'x-mirror': [{ value: 'true' }],
        'x-shadow-version': [{ value: 'v2' }]
      }
    };

    https.request(mirrorRequest, (res) => {
      // Ignore response (fire-and-forget)
      res.on('data', () => {});
      res.on('end', () => {});
    }).on('error', (error) => {
      console.error('Mirror failed:', error);
    }).end();
  }

  // Return original request (continue to origin)
  return request;
};
```

**Deployment:**
```bash
# 1. Lambda@Edge Function erstellen
zip mirror-function.zip index.js

aws lambda create-function \
  --function-name mirror-function \
  --runtime nodejs18.x \
  --role arn:aws:iam::123456789012:role/lambda-edge-role \
  --handler index.handler \
  --zip-file fileb://mirror-function.zip \
  --region us-east-1

# 2. Version veröffentlichen (required für Lambda@Edge)
aws lambda publish-version \
  --function-name mirror-function \
  --region us-east-1

# 3. CloudFront Distribution mit Lambda@Edge verknüpfen
aws cloudfront update-distribution \
  --id E1234567890ABC \
  --distribution-config '{
    "LambdaFunctionAssociations": {
      "Items": [{
        "LambdaFunctionARN": "arn:aws:lambda:us-east-1:123456789012:function:mirror-function:1",
        "EventType": "viewer-request"
      }]
    }
  }'

# 4. Environment Variables setzen
aws lambda update-function-configuration \
  --function-name mirror-function \
  --environment Variables={SAMPLE_PERCENTAGE=50,SHADOW_HOST=shadow.example.com} \
  --region us-east-1
```

**Hinweise:**
- ⚠️ **Lambda@Edge erforderlich**: Kein natives Mirroring in AWS API Gateway
- ⚠️ **CloudFront Integration**: Lambda@Edge läuft nur mit CloudFront (EDGE Endpoints)
- ✅ **Sample Percentage**: Via Environment Variables konfigurierbar
- ✅ **Custom Headers**: Im Lambda-Code definierbar
- ⚠️ **Regional Endpoints**: Nicht unterstützt (nur EDGE mit CloudFront)

**Alternativen:**
- **API Gateway REST API → Lambda Proxy** mit Mirroring-Logik im Lambda
- **Application Load Balancer** (ALB) mit Target Groups statt API Gateway
- **AWS App Mesh** für Service-Mesh-basiertes Mirroring

> **Vollständige Dokumentation:** Siehe [Request Mirroring Guide](REQUEST_MIRRORING.md#aws-api-gateway-workaround-lambdaedge)

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

