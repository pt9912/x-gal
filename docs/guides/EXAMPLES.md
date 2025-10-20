# GAL Konfigurationsbeispiele

Diese Seite enthält vollständige, ausführbare Konfigurationsbeispiele für häufige Anwendungsfälle.

---

## Grundlegende Beispiele

### 1. Einfache REST-API

Minimales Beispiel für einen HTTP-basierten API-Service:

```yaml
version: "1.0"
provider: kong

services:
  - name: users_api
    type: rest
    protocol: http
    upstream:
      host: users-service
      port: 8080
    routes:
      - path_prefix: /api/users
        methods: [GET, POST, PUT, DELETE]
```

**Use Case:**
- Einfacher CRUD-Service
- Backend: users-service:8080
- Alle HTTP-Methoden erlaubt

**Deployment:**
```bash
gal generate -c users-api.yaml -p kong -o kong.yaml
```

---

### 2. API mit mehreren Routen

Service mit verschiedenen Endpunkten und HTTP-Methoden:

```yaml
version: "1.0"
provider: envoy

services:
  - name: blog_api
    type: rest
    protocol: http
    upstream:
      host: blog-backend
      port: 3000
    routes:
      - path_prefix: /api/posts
        methods: [GET, POST]
      - path_prefix: /api/posts/
        path_regex: "^/api/posts/[0-9]+$"
        methods: [GET, PUT, DELETE]
      - path_prefix: /api/comments
        methods: [GET, POST]
```

**Use Case:**
- Blog-API mit Posts und Comments
- Verschiedene Endpunkte mit spezifischen Methoden
- Regex für parametrisierte Routen (`/api/posts/123`)

---

## Transformationen

### 3. Automatische Defaults

Request-Transformationen mit Default-Werten:

```yaml
version: "1.0"
provider: apisix

services:
  - name: orders_api
    type: rest
    protocol: http
    upstream:
      host: orders-service
      port: 8080
    routes:
      - path_prefix: /api/orders
        methods: [POST]
    transformation:
      enabled: true
      defaults:
        status: "pending"
        currency: "USD"
        payment_method: "credit_card"
        priority: 3
```

**Use Case:**
- Order-Creation mit sinnvollen Defaults
- Wenn Client `status` nicht sendet → automatisch `"pending"`
- Wenn Client `currency` nicht sendet → automatisch `"USD"`

**Request:**
```json
POST /api/orders
{
  "customer_id": "cust_123",
  "items": [{"product_id": "prod_456", "quantity": 2}]
}
```

**Transformierter Request an Backend:**
```json
{
  "customer_id": "cust_123",
  "items": [{"product_id": "prod_456", "quantity": 2}],
  "status": "pending",
  "currency": "USD",
  "payment_method": "credit_card",
  "priority": 3
}
```

---

### 4. UUID-Generierung

Automatische ID-Generierung für neue Entities:

```yaml
version: "1.0"
provider: kong

services:
  - name: products_api
    type: rest
    protocol: http
    upstream:
      host: products-service
      port: 8080
    routes:
      - path_prefix: /api/products
        methods: [POST]
    transformation:
      enabled: true
      computed_fields:
        - field: product_id
          generator: uuid
          prefix: "prod_"
        - field: created_at
          generator: timestamp
        - field: updated_at
          generator: timestamp
```

**Use Case:**
- Automatische Product-ID Generierung
- Timestamps für Audit-Trail

**Request:**
```json
POST /api/products
{
  "name": "Laptop",
  "price": 999.99
}
```

**Transformierter Request:**
```json
{
  "name": "Laptop",
  "price": 999.99,
  "product_id": "prod_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "created_at": "2025-01-20T14:30:00Z",
  "updated_at": "2025-01-20T14:30:00Z"
}
```

---

### 5. Validierung mit Required Fields

Request-Validierung für kritische Business-Felder:

```yaml
version: "1.0"
provider: envoy

services:
  - name: payments_api
    type: rest
    protocol: http
    upstream:
      host: payments-service
      port: 8080
    routes:
      - path_prefix: /api/payments
        methods: [POST]
    transformation:
      enabled: true
      defaults:
        currency: "USD"
      computed_fields:
        - field: transaction_id
          generator: uuid
          prefix: "txn_"
        - field: created_at
          generator: timestamp
      validation:
        required_fields:
          - customer_id
          - amount
          - payment_method
```

**Use Case:**
- Payment-API mit strikter Validierung
- Requests ohne `customer_id`, `amount` oder `payment_method` werden abgelehnt (400 Bad Request)

**Valid Request:**
```json
POST /api/payments
{
  "customer_id": "cust_123",
  "amount": 49.99,
  "payment_method": "visa"
}
```

**Invalid Request (fehlt `amount`):**
```json
POST /api/payments
{
  "customer_id": "cust_123",
  "payment_method": "visa"
}
```
**Response:** `400 Bad Request - Missing required field: amount`

---

## gRPC-Services

### 6. Einfacher gRPC-Service

gRPC-Service mit HTTP/2:

```yaml
version: "1.0"
provider: envoy

services:
  - name: user_service
    type: grpc
    protocol: http2
    upstream:
      host: user-grpc
      port: 9090
    routes:
      - path_prefix: /myapp.UserService
    transformation:
      enabled: true
      computed_fields:
        - field: user_id
          generator: uuid
```

**Use Case:**
- gRPC-Service für User-Management
- Protobuf-basierte Communication
- Automatische User-ID Generierung

**Supported Methods:**
- `/myapp.UserService/CreateUser`
- `/myapp.UserService/GetUser`
- `/myapp.UserService/UpdateUser`
- `/myapp.UserService/DeleteUser`

---

### 7. gRPC mit Transcoding (REST → gRPC)

gRPC-Service mit HTTP/JSON → gRPC-Transformation:

```yaml
version: "1.0"
provider: envoy

services:
  - name: inventory_service
    type: grpc
    protocol: http2
    upstream:
      host: inventory-grpc
      port: 9090
    routes:
      - path_prefix: /inventory.InventoryService
    grpc_transcoding:
      enabled: true
      proto_descriptor: "inventory.pb"
      services:
        - "inventory.InventoryService"
```

**Use Case:**
- REST-Clients können gRPC-Services nutzen
- Automatische JSON ↔ Protobuf Konvertierung
- Keine Code-Änderungen im Backend

**REST Request:**
```bash
curl -X POST http://gateway/inventory.InventoryService/CheckStock \
  -H "Content-Type: application/json" \
  -d '{"product_id": "prod_123", "warehouse_id": "wh_456"}'
```

**Gateway konvertiert zu gRPC Call:**
```
inventory.InventoryService/CheckStock(product_id="prod_123", warehouse_id="wh_456")
```

---

## Multi-Service Konfiguration

### 8. Microservices-Gateway

Mehrere Services mit einem Gateway:

```yaml
version: "1.0"
provider: kong

global:
  port: 8080

services:
  # REST: User Service
  - name: users_api
    type: rest
    protocol: http
    upstream:
      host: users-service
      port: 8080
    routes:
      - path_prefix: /api/users
        methods: [GET, POST, PUT, DELETE]

  # REST: Products Service
  - name: products_api
    type: rest
    protocol: http
    upstream:
      host: products-service
      port: 8081
    routes:
      - path_prefix: /api/products
        methods: [GET, POST, PUT, DELETE]

  # gRPC: Inventory Service
  - name: inventory_service
    type: grpc
    protocol: http2
    upstream:
      host: inventory-grpc
      port: 9090
    routes:
      - path_prefix: /inventory.InventoryService

  # REST: Orders Service
  - name: orders_api
    type: rest
    protocol: http
    upstream:
      host: orders-service
      port: 8082
    routes:
      - path_prefix: /api/orders
        methods: [GET, POST]
    transformation:
      enabled: true
      defaults:
        status: "pending"
      computed_fields:
        - field: order_id
          generator: uuid
          prefix: "ord_"
        - field: created_at
          generator: timestamp
      validation:
        required_fields:
          - customer_id
          - items
```

**Use Case:**
- E-Commerce-Backend mit 4 Microservices
- Verschiedene Protokolle (REST + gRPC)
- Order-Service mit Transformationen

**Routing:**
- `GET /api/users` → users-service:8080
- `GET /api/products` → products-service:8081
- `POST /api/orders` → orders-service:8082 (mit Transformationen)
- gRPC `/inventory.InventoryService` → inventory-grpc:9090

---

## Provider-spezifische Beispiele

### 9. Nginx mit OpenResty Lua

Nginx-Config mit Lua-basierten Transformationen:

```yaml
version: "1.0"
provider: nginx

services:
  - name: api_gateway
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api
    transformation:
      enabled: true
      defaults:
        api_version: "v1"
      computed_fields:
        - field: request_id
          generator: uuid
```

**Generierte nginx.conf nutzt OpenResty Lua:**
```nginx
location /api {
    access_by_lua_block {
        -- UUID-Generierung
        local uuid = require("resty.jit-uuid")
        ngx.req.set_header("X-Request-ID", uuid())

        -- Default-Werte
        ngx.req.set_header("X-API-Version", "v1")
    }

    proxy_pass http://backend:8080;
}
```

---

### 10. Envoy mit Lua Filters

Envoy-Config mit Lua HTTP Filters:

```yaml
version: "1.0"
provider: envoy

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api
    transformation:
      enabled: true
      computed_fields:
        - field: trace_id
          generator: uuid
```

**Generierte envoy.yaml nutzt Lua Filter:**
```yaml
http_filters:
  - name: envoy.filters.http.lua
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
      inline_code: |
        function envoy_on_request(request_handle)
          -- UUID-Generierung für Tracing
          local trace_id = generate_uuid()
          request_handle:headers():add("X-Trace-ID", trace_id)
        end
```

---

## Advanced Use Cases

### 11. API mit JWT Authentication

Service mit JWT-basierter Authentifizierung:

```yaml
version: "1.0"
provider: kong

services:
  - name: protected_api
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api/protected
        methods: [GET, POST]
    authentication:
      enabled: true
      type: jwt
      jwt:
        secret: "${JWT_SECRET}"
        algorithm: HS256
        header: "Authorization"
        claims_to_verify:
          - exp
          - iss
```

**Use Case:**
- API-Endpunkte erfordern gültiges JWT
- Ungültige/fehlende JWTs → 401 Unauthorized

**Request mit JWT:**
```bash
curl -H "Authorization: Bearer eyJhbGc..." http://gateway/api/protected/users
```

---

### 12. Rate Limiting

Service mit Request-Limitierung:

```yaml
version: "1.0"
provider: apisix

services:
  - name: public_api
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api/public
    rate_limiting:
      enabled: true
      requests_per_second: 10
      burst: 20
      key: "$remote_addr"  # IP-basiert
```

**Use Case:**
- Public API mit Rate Limiting
- Max. 10 Requests/Sekunde pro IP
- Burst bis zu 20 Requests

---

### 13. CORS-enabled API

Service mit Cross-Origin Resource Sharing:

```yaml
version: "1.0"
provider: envoy

services:
  - name: frontend_api
    type: rest
    protocol: http
    upstream:
      host: backend
      port: 8080
    routes:
      - path_prefix: /api
    cors:
      enabled: true
      allow_origins:
        - "https://app.example.com"
        - "https://admin.example.com"
      allow_methods: [GET, POST, PUT, DELETE, OPTIONS]
      allow_headers: [Content-Type, Authorization, X-API-Key]
      allow_credentials: true
      max_age: 86400
```

**Use Case:**
- Frontend-API für Web-Apps
- Erlaubt CORS-Requests von bestimmten Domains

---

### 14. Circuit Breaker

Service mit Circuit Breaker Pattern:

```yaml
version: "1.0"
provider: envoy

services:
  - name: unstable_api
    type: rest
    protocol: http
    upstream:
      host: flaky-backend
      port: 8080
    routes:
      - path_prefix: /api
    circuit_breaker:
      enabled: true
      max_connections: 100
      max_pending_requests: 50
      max_requests: 200
      max_retries: 3
      consecutive_errors: 5
      interval: 30s
      base_ejection_time: 30s
```

**Use Case:**
- Backend ist manchmal instabil
- Nach 5 aufeinanderfolgenden Fehlern: Circuit OPEN
- Backend wird für 30s ausgeschlossen
- Verhindert Cascading Failures

---

### 15. Health Checks

Service mit aktiven Health Checks:

```yaml
version: "1.0"
provider: envoy

services:
  - name: monitored_api
    type: rest
    protocol: http
    upstream:
      targets:
        - host: backend1.example.com
          port: 8080
        - host: backend2.example.com
          port: 8080
        - host: backend3.example.com
          port: 8080
    routes:
      - path_prefix: /api
    health_check:
      enabled: true
      interval: 10s
      timeout: 5s
      unhealthy_threshold: 3
      healthy_threshold: 2
      path: /health
      expected_status: 200
```

**Use Case:**
- Multi-Instance Backend (3 Pods/VMs)
- Health Check alle 10s auf `/health`
- Unhealthy Instances werden aus Load-Balancing entfernt

---

## Cloud Provider Beispiele

### 16. Azure API Management

Azure APIM mit Policies:

```yaml
version: "1.0"
provider: azure_apim

services:
  - name: azure_api
    type: rest
    protocol: http
    upstream:
      host: backend.azurewebsites.net
      port: 443
    routes:
      - path_prefix: /api
    authentication:
      enabled: true
      type: jwt
      jwt:
        issuer: "https://login.microsoftonline.com/{tenant-id}/v2.0"
        audience: "api://my-app"
    rate_limiting:
      enabled: true
      requests_per_second: 100
      quota_per_month: 1000000
```

**Deployment:**
```bash
gal generate -c azure-config.yaml -p azure_apim -o apim.json
az apim api import --path /api --api-id my-api --specification-format OpenApiJson --specification-path apim.json
```

---

### 17. AWS API Gateway

AWS API Gateway mit Lambda-Integration:

```yaml
version: "1.0"
provider: aws_apigateway

services:
  - name: serverless_api
    type: rest
    protocol: http
    upstream:
      lambda_function: "arn:aws:lambda:us-east-1:123456789012:function:my-function"
    routes:
      - path_prefix: /api
        methods: [GET, POST]
    authentication:
      enabled: true
      type: cognito
      cognito:
        user_pool_arn: "arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_ABC123"
    rate_limiting:
      enabled: true
      throttle_burst_limit: 5000
      throttle_rate_limit: 2000
```

**Deployment:**
```bash
gal generate -c aws-config.yaml -p aws_apigateway -o api.json
aws apigateway import-rest-api --body file://api.json
```

---

### 18. GCP API Gateway

GCP API Gateway mit Cloud Run Backend:

```yaml
version: "1.0"
provider: gcp_apigateway

services:
  - name: cloud_run_api
    type: rest
    protocol: http
    upstream:
      host: "my-service-abc123-uc.a.run.app"
      port: 443
    routes:
      - path_prefix: /api
    authentication:
      enabled: true
      type: jwt
      jwt:
        issuer: "https://accounts.google.com"
        jwks_uri: "https://www.googleapis.com/oauth2/v3/certs"
        audiences: ["my-cloud-run-service"]
```

**Deployment:**
```bash
gal generate -c gcp-config.yaml -p gcp_apigateway -o openapi.yaml
gcloud api-gateway apis create my-api --project=my-project
gcloud api-gateway api-configs create config-v1 --api=my-api --openapi-spec=openapi.yaml
gcloud api-gateway gateways create my-gateway --api=my-api --api-config=config-v1 --location=us-central1
```

---

## Nächste Schritte

- 📖 [Konfigurationsreferenz](../api/CONFIGURATION.md) - Alle verfügbaren Optionen
- 🔧 [CLI-Referenz](../api/CLI_REFERENCE.md) - Alle Befehle im Detail
- 🏗️ [Best Practices](BEST_PRACTICES.md) - Empfehlungen für Production
- 🌐 [Provider-Guides](PROVIDERS.md) - Provider-spezifische Details
