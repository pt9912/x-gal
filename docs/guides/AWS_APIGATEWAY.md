# AWS API Gateway Provider Anleitung

**Umfassende Anleitung für AWS API Gateway Provider in GAL (Gateway Abstraction Layer)**

## Inhaltsverzeichnis

1. [Übersicht](#ubersicht)
2. [AWS API Gateway Architektur](#aws-api-gateway-architektur)
3. [Schnellstart](#schnellstart)
4. [Konfigurationsoptionen](#konfigurationsoptionen)
5. [Request Flow durch AWS API Gateway](#request-flow-durch-aws-api-gateway)
6. [Provider-Vergleich](#provider-vergleich)

**Weitere Dokumentation:**
- [Feature-Implementierungen](AWS_APIGATEWAY_FEATURES.md) - Integration-Typen, Auth, CORS, Usage Plans
- [Deployment & Migration](AWS_APIGATEWAY_DEPLOYMENT.md) - Deployment, Import, Migration, Best Practices

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

```mermaid
graph TB
    subgraph Client["Client Layer"]
        WebBrowser["Web Browser"]
        MobileAppIOS["Mobile App (iOS)"]
        MobileAppAndroid["Mobile App (Android)"]
        APIClient["API Client"]
    end

    subgraph Gateway["AWS API Gateway Layer"]
        subgraph API["REST API / HTTP API"]
            Resources["Resources<br/>(/users, /products, /orders)"]
            Methods["Methods<br/>(GET, POST, PUT, DELETE)"]
            Stages["Stages<br/>(prod, dev, staging)"]
        end

        subgraph Auth["Authorization"]
            APIKeys["API Keys<br/>(x-api-key)"]
            LambdaAuth["Lambda Authorizer<br/>(Custom JWT)"]
            Cognito["Cognito User Pools<br/>(OAuth2/OIDC)"]
            IAM["IAM<br/>(SigV4)"]
        end

        subgraph Integration["Integration Types"]
            HTTPProxy["HTTP_PROXY<br/>(Backend HTTP)"]
            AWSProxy["AWS_PROXY<br/>(Lambda)"]
            Mock["MOCK<br/>(Testing)"]
        end

        subgraph UsagePlans["Usage Plans & Throttling"]
            RateLimit["Rate Limiting<br/>(Requests/sec)"]
            Quotas["Quotas<br/>(Daily/Monthly)"]
            APIKeyMgmt["API Key Management"]
        end
    end

    subgraph Backend["Backend Services Layer"]
        Lambda["Lambda Function<br/>(Serverless)"]
        HTTPBackend["HTTP Backend<br/>(ECS/EKS)"]
        MockResp["Mock Response"]
    end

    subgraph CrossCutting["Cross-Cutting Concerns"]
        subgraph Security["Security"]
            WAF["AWS WAF<br/>(DDoS, SQL Injection)"]
            VPCLink["VPC Link<br/>(Private APIs)"]
            CloudFront["CloudFront<br/>(EDGE Endpoints)"]
        end

        subgraph Observability["Observability"]
            CWLogs["CloudWatch Logs<br/>(Access/Execution)"]
            CWMetrics["CloudWatch Metrics<br/>(Count, 4XX, 5XX, Latency)"]
            XRay["X-Ray Tracing"]
        end

        subgraph CORS["CORS"]
            GatewayResp["Gateway Responses<br/>(DEFAULT_4XX, DEFAULT_5XX)"]
            OPTIONS["OPTIONS Methods<br/>(Preflight)"]
        end
    end

    %% Request Flow
    WebBrowser --> Resources
    MobileAppIOS --> Resources
    MobileAppAndroid --> Resources
    APIClient --> Resources

    Resources --> Methods
    Methods --> Stages
    Stages --> APIKeys
    Stages --> LambdaAuth
    Stages --> Cognito
    Stages --> IAM

    APIKeys --> RateLimit
    LambdaAuth --> RateLimit
    Cognito --> RateLimit
    IAM --> RateLimit

    RateLimit --> Quotas
    Quotas --> APIKeyMgmt
    APIKeyMgmt --> HTTPProxy
    APIKeyMgmt --> AWSProxy
    APIKeyMgmt --> Mock

    HTTPProxy --> HTTPBackend
    AWSProxy --> Lambda
    Mock --> MockResp

    %% Cross-Cutting
    Stages -.-> WAF
    Stages -.-> VPCLink
    Stages -.-> CloudFront
    Stages -.-> CWLogs
    Stages -.-> CWMetrics
    Stages -.-> XRay
    Methods -.-> GatewayResp
    Methods -.-> OPTIONS

    %% Styling
    classDef clientStyle fill:#E3F2FD,stroke:#01579B,stroke-width:2px,color:#000
    classDef gatewayStyle fill:#FFF3E0,stroke:#E65100,stroke-width:3px,color:#000
    classDef backendStyle fill:#F1F8E9,stroke:#558B2F,stroke-width:2px,color:#000
    classDef authStyle fill:#FCE4EC,stroke:#C2185B,stroke-width:2px,color:#000
    classDef trafficStyle fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#000
    classDef monitorStyle fill:#E0F2F1,stroke:#00695C,stroke-width:2px,color:#000
    classDef storageStyle fill:#FFF9C4,stroke:#F57F17,stroke-width:2px,color:#000
    classDef awsStyle fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff

    class WebBrowser,MobileAppIOS,MobileAppAndroid,APIClient clientStyle
    class Resources,Methods,Stages,HTTPProxy,AWSProxy,Mock gatewayStyle
    class Lambda,HTTPBackend,MockResp backendStyle
    class APIKeys,LambdaAuth,Cognito,IAM authStyle
    class RateLimit,Quotas,APIKeyMgmt trafficStyle
    class CWLogs,CWMetrics,XRay monitorStyle
    class WAF,VPCLink,CloudFront,GatewayResp,OPTIONS storageStyle
```

**Diagramm-Erklärung:**

- **Client Layer:** Verschiedene Client-Typen (Web Browser, Mobile Apps für iOS/Android, API Clients)
- **AWS API Gateway Layer:** Zentrale Komponenten
  - **REST API / HTTP API:** Resources, Methods, Stages für API-Organisation
  - **Authorization:** Vier Hauptmechanismen (API Keys, Lambda Authorizer, Cognito, IAM)
  - **Integration Types:** HTTP_PROXY für Backend HTTP, AWS_PROXY für Lambda, MOCK für Testing
  - **Usage Plans & Throttling:** Rate Limiting, Quotas, API Key Management
- **Backend Services:** Lambda Function (Serverless), HTTP Backend (ECS/EKS), Mock Response
- **Cross-Cutting Concerns:**
  - **Security:** AWS WAF (DDoS/SQL Injection), VPC Link (Private APIs), CloudFront (EDGE)
  - **Observability:** CloudWatch Logs, Metrics, X-Ray Tracing
  - **CORS:** Gateway Responses für Error Handling, OPTIONS Methods für Preflight

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

## Request Flow durch AWS API Gateway

Das folgende Sequenzdiagramm zeigt den vollständigen Request-Ablauf durch AWS API Gateway mit allen Security- und Traffic-Management-Features:

```mermaid
sequenceDiagram
    autonumber
    participant Client as Client<br/>(Browser/App)
    participant Gateway as API Gateway
    participant APIKey as API Key Validator<br/>(Usage Plan Check)
    participant LambdaAuth as Lambda Authorizer<br/>(JWT Validation)
    participant RateLimit as Rate Limiter<br/>(Usage Plan)
    participant Lambda as Lambda Function
    participant DynamoDB as DynamoDB
    participant CloudWatch as CloudWatch Logs

    %% Request Start
    rect rgb(250, 250, 240)
        Note over Client,CloudWatch: Authenticated POST Request with API Key
        Client->>Gateway: POST /api/users<br/>Authorization: Bearer JWT<br/>x-api-key: abc123xyz

        Gateway->>APIKey: Validate API Key
        APIKey->>APIKey: Check Usage Plan<br/>(API Key exists?)

        alt API Key Invalid
            APIKey-->>Gateway: 403 Forbidden
            Gateway-->>Client: 403 Forbidden<br/>MissingAuthenticationToken
        else API Key Valid
            APIKey-->>Gateway: API Key Valid ✓

            Gateway->>LambdaAuth: Invoke Lambda Authorizer<br/>(JWT Token)
            LambdaAuth->>LambdaAuth: JWT Validation<br/>(Extract Bearer Token)
            LambdaAuth->>LambdaAuth: Verify Signature<br/>(RS256/Public Key)
            LambdaAuth->>LambdaAuth: Check Issuer<br/>(iss claim)
            LambdaAuth->>LambdaAuth: Check Audience<br/>(aud claim)
            LambdaAuth->>LambdaAuth: Check Expiration<br/>(exp claim)

            alt JWT Invalid/Expired
                LambdaAuth-->>Gateway: 403 Forbidden<br/>(Deny Policy)
                Gateway-->>Client: 403 Unauthorized<br/>Invalid JWT Token
            else JWT Valid
                LambdaAuth-->>Gateway: Allow Policy + Context<br/>(user_id: user123, role: admin)

                Gateway->>RateLimit: Check Rate Limit<br/>(Usage Plan for API Key)
                RateLimit->>RateLimit: Count Requests<br/>(45/500 req/s, Burst: 800/1000)

                alt Rate Limit Exceeded
                    RateLimit-->>Gateway: 429 Too Many Requests
                    Gateway-->>Client: 429 Too Many Requests<br/>TooManyRequestsException<br/>Retry-After: 1
                else Within Limit
                    RateLimit-->>Gateway: Rate Limit OK<br/>(Remaining: 455/500 req/s)

                    Gateway->>Lambda: Invoke Lambda<br/>(AWS_PROXY Integration)<br/>Event: {body, headers, context}
                    Lambda->>Lambda: Parse Request Body
                    Lambda->>DynamoDB: PutItem (Save User)
                    DynamoDB-->>Lambda: Success (200 OK)
                    Lambda-->>Gateway: Lambda Response<br/>{statusCode: 201, body: JSON}

                    Gateway->>CloudWatch: Log Request<br/>(request_id, status: 201,<br/>latency: 120ms, api_key: abc123)

                    Gateway-->>Client: 201 Created<br/>Access-Control-Allow-Origin: *<br/>{"id": 456, "name": "John Doe"}
                end
            end
        end
    end

    Note over Client,CloudWatch: Request completed in ~120ms
```

**Alternative Flows:**

| Fehler | HTTP Status | Response | Ursache |
|--------|-------------|----------|---------|
| **API Key Invalid** | 403 Forbidden | `{"message":"Forbidden"}` | x-api-key fehlt oder ungültig |
| **Lambda Authorizer Deny** | 403 Forbidden | `{"message":"User is not authorized"}` | JWT ungültig/expired |
| **Rate Limit Exceeded** | 429 Too Many Requests | `{"message":"Too Many Requests"}` | Usage Plan Limit überschritten |
| **Lambda Timeout** | 504 Gateway Timeout | `{"message":"Endpoint request timed out"}` | Lambda > 29s (Hard Limit!) |
| **Lambda Error** | 502 Bad Gateway | `{"message":"Internal server error"}` | Lambda Exception |

**Flow-Erklärung:**

1. **Client Request:** Client sendet POST Request mit JWT Token (Authorization Header) und API Key (x-api-key Header)
2. **API Key Validation:** Gateway prüft ob API Key existiert und zu einem Usage Plan gehört
3. **Lambda Authorizer Invocation:** Gateway ruft Lambda Authorizer Function auf
4. **JWT Validation:** Lambda validiert JWT Token (Signature, Issuer, Audience, Expiration)
5. **IAM Policy Generation:** Lambda Authorizer generiert Allow/Deny IAM Policy + Context (user_id, role)
6. **Rate Limit Check:** Gateway prüft Usage Plan Rate Limits (500 req/s, Burst 1000)
7. **Lambda Integration:** Gateway invoked Backend Lambda Function (AWS_PROXY)
8. **DynamoDB Write:** Lambda speichert User Data in DynamoDB
9. **CloudWatch Logging:** Request wird mit allen Details geloggt (request_id, status, latency, api_key)
10. **Response:** Client erhält 201 Created mit CORS Headers

**AWS API Gateway Besonderheiten:**

- **29 Sekunden Hard Timeout:** Lambda Integration hat Maximum 29000ms Timeout
- **Usage Plans:** Rate Limiting erfolgt pro API Key über Usage Plans
- **Lambda Authorizer TTL:** Authorizer Responses werden gecached (default: 300s)
- **Gateway Responses:** DEFAULT_4XX und DEFAULT_5XX Responses für CORS Error Handling
- **CloudWatch Logs:** Access Logs (JSON Format) und Execution Logs (DEBUG)
- **X-Ray Tracing:** Distributed Tracing über Lambda und Backend Services

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

