# Header Manipulation Guide

**Complete guide to HTTP header manipulation in GAL (Gateway Abstraction Layer)**

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Header Operations](#header-operations)
4. [Configuration Levels](#configuration-levels)
5. [Provider Implementation](#provider-implementation)
6. [Common Use Cases](#common-use-cases)
7. [Security Best Practices](#security-best-practices)
8. [Testing Header Manipulation](#testing-header-manipulation)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Header manipulation allows you to modify HTTP request and response headers as they pass through the gateway. This is essential for:

- **Security**: Adding security headers, removing sensitive information
- **CORS**: Enabling cross-origin resource sharing
- **Request Identification**: Adding correlation/request IDs
- **Backend Communication**: Adding internal headers for backend services
- **Response Modification**: Customizing headers returned to clients

### Supported Operations

| Operation | Request | Response | Description |
|-----------|---------|----------|-------------|
| **Add** | ✅ | ✅ | Add header (keeps existing values) |
| **Set** | ✅ | ✅ | Set/replace header (overwrites existing) |
| **Remove** | ✅ | ✅ | Delete header completely |

### Provider Support

All GAL providers support header manipulation:

| Provider | Request Headers | Response Headers | Notes |
|----------|----------------|------------------|-------|
| **Envoy** | ✅ | ✅ | Native route-level header manipulation |
| **Kong** | ✅ | ✅ | request-transformer, response-transformer plugins |
| **APISIX** | ✅ | ✅ | proxy-rewrite, response-rewrite plugins |
| **Traefik** | ✅ | ✅ | headers middleware |
| **Nginx** | ✅ | ✅ | proxy_set_header, add_header directives |
| **HAProxy** | ✅ | ✅ | http-request/http-response set-header |
| **Azure APIM** | ✅ | ✅ | set-header Policy XML (inbound/outbound) |

---

## Quick Start

### Basic Example: Adding Request Headers

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
        headers:
          request_add:
            X-Request-ID: "{{uuid}}"
            X-API-Version: "v1"
```

### Basic Example: Security Headers

```yaml
routes:
  - path_prefix: /api
    headers:
      response_add:
        X-Frame-Options: DENY
        X-Content-Type-Options: nosniff
        Strict-Transport-Security: "max-age=31536000"
      response_remove:
        - Server
        - X-Powered-By
```

---

## Header Operations

### 1. Adding Headers (request_add / response_add)

**Adds** headers while preserving existing values. If the header already exists, the new value is appended.

```yaml
headers:
  request_add:
    X-Custom-Header: "custom-value"
    X-Correlation-ID: "{{uuid}}"
    X-Forwarded-For: "client-ip"

  response_add:
    X-Response-Time: "100ms"
    X-Cache-Status: "HIT"
    X-Server-ID: "gateway-01"
```

**Use Cases**:
- Adding custom headers for backend services
- Injecting correlation/trace IDs
- Adding caching information
- Appending proxy chain information

### 2. Setting Headers (request_set / response_set)

**Sets or replaces** headers. If the header exists, it's overwritten with the new value.

```yaml
headers:
  request_set:
    User-Agent: "GAL-Gateway/1.0"
    Host: "backend.internal.com"
    Authorization: "Bearer {{token}}"

  response_set:
    Server: "GAL-Gateway"
    Content-Type: "application/json"
```

**Use Cases**:
- Overwriting existing headers
- Standardizing header values
- Modifying upstream-generated headers
- Setting security headers

### 3. Removing Headers (request_remove / response_remove)

**Removes** headers completely from the request or response.

```yaml
headers:
  request_remove:
    - X-Internal-Token
    - X-Debug-Mode
    - Cookie

  response_remove:
    - Server
    - X-Powered-By
    - X-AspNet-Version
```

**Use Cases**:
- Removing sensitive information
- Hiding backend details
- Stripping debug headers in production
- Removing unnecessary headers

---

## Configuration Levels

GAL supports header manipulation at two levels:

### 1. Route-Level (Per-Route)

Configure headers for specific routes. **Takes precedence** over service-level configuration.

```yaml
services:
  - name: api_service
    upstream:
      host: api.local
      port: 8080
    routes:
      - path_prefix: /api/public
        headers:
          request_add:
            X-API-Type: "public"
          response_add:
            Cache-Control: "public, max-age=3600"

      - path_prefix: /api/private
        headers:
          request_add:
            X-API-Type: "private"
          response_add:
            Cache-Control: "private, no-cache"
```

**Advantages**:
- Fine-grained control per endpoint
- Different headers for different paths
- Override service defaults

### 2. Service-Level (Transformation)

Configure headers for all routes in a service.

```yaml
services:
  - name: backend_service
    upstream:
      host: backend.local
      port: 8080
    routes:
      - path_prefix: /api
    transformation:
      enabled: true
      headers:
        request_add:
          X-Service-Name: "backend_service"
          X-Environment: "production"
        response_add:
          X-API-Version: "2.0"
```

**Advantages**:
- Apply headers to all routes
- Centralized header configuration
- DRY (Don't Repeat Yourself)

---

## Provider Implementation

### Kong (request-transformer & response-transformer)

Kong uses two plugins for header manipulation:

**Request Headers**:
```yaml
plugins:
  - name: request-transformer
    config:
      add:
        headers:
          - "X-Custom:value"
      replace:
        headers:
          - "User-Agent:GAL"
      remove:
        headers:
          - X-Internal
```

**Response Headers**:
```yaml
plugins:
  - name: response-transformer
    config:
      add:
        headers:
          - "X-Response:ok"
      remove:
        headers:
          - Server
```

### APISIX (proxy-rewrite & response-rewrite)

APISIX uses rewrite plugins:

**Request Headers**:
```json
{
  "proxy-rewrite": {
    "headers": {
      "add": {"X-Custom": "value"},
      "set": {"User-Agent": "GAL"},
      "remove": ["X-Internal"]
    }
  }
}
```

**Response Headers**:
```json
{
  "response-rewrite": {
    "headers": {
      "add": {"X-Response": "ok"},
      "remove": ["Server"]
    }
  }
}
```

### Traefik (headers middleware)

Traefik uses the headers middleware:

```yaml
middlewares:
  api_headers:
    headers:
      customRequestHeaders:
        X-Custom: "value"
        X-Internal: ""  # Empty value removes header
      customResponseHeaders:
        X-Response: "ok"
        Server: ""  # Empty value removes header
```

### Envoy (Native Route Configuration)

Envoy has native header manipulation:

```yaml
routes:
  - match:
      prefix: /api
    route:
      cluster: backend
    request_headers_to_add:
      - header:
          key: X-Custom
          value: value
        append: true  # true=add, false=set
    request_headers_to_remove:
      - X-Internal
    response_headers_to_add:
      - header:
          key: X-Response
          value: ok
    response_headers_to_remove:
      - Server
```

---

### Nginx (proxy_set_header / add_header)

Nginx implementiert Header Manipulation mit `proxy_set_header` für Request Headers und `add_header` für Response Headers.

**Config-Beispiel (Request Headers):**
```nginx
# GAL generiert Nginx-Config
http {
    upstream backend {
        server api.internal:8080;
    }

    server {
        listen 80;
        server_name api.example.com;

        location /api {
            # Request Headers (an Upstream)
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Request-ID $request_id;
            proxy_set_header X-API-Version "v1";

            # Response Headers (an Client)
            add_header X-Frame-Options "DENY" always;
            add_header X-Content-Type-Options "nosniff" always;
            add_header X-Request-ID $request_id always;

            # Headers entfernen (durch leeren Wert)
            proxy_set_header X-Internal-Token "";
            more_clear_headers 'Server';  # Benötigt ngx_headers_more module

            proxy_pass http://backend;
        }
    }
}
```

**Mit OpenResty (Lua für komplexe Logik):**
```nginx
location /api {
    access_by_lua_block {
        -- Request Headers setzen
        ngx.req.set_header("X-Request-ID", ngx.var.request_id)
        ngx.req.set_header("X-Forwarded-For", ngx.var.remote_addr)
        ngx.req.set_header("X-API-Version", "v1")

        -- Conditional Header Logic
        local user_agent = ngx.req.get_headers()["User-Agent"]
        if user_agent and string.match(user_agent, "Mobile") then
            ngx.req.set_header("X-Device-Type", "mobile")
        else
            ngx.req.set_header("X-Device-Type", "desktop")
        end

        -- Header entfernen
        ngx.req.clear_header("X-Internal-Token")
    }

    header_filter_by_lua_block {
        -- Response Headers setzen
        ngx.header["X-Request-ID"] = ngx.var.request_id
        ngx.header["X-Response-Time"] = ngx.var.request_time
        ngx.header["X-Frame-Options"] = "DENY"

        -- Response Headers entfernen
        ngx.header["Server"] = nil
        ngx.header["X-Powered-By"] = nil
    }

    proxy_pass http://backend;
}
```

**X-Forwarded-* Headers:**
```nginx
location /api {
    # Standard Forwarded Headers
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;

    # Custom Headers
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Original-URI $request_uri;

    proxy_pass http://backend;
}
```

**Nginx Besonderheiten**:
- ✅ `proxy_set_header` für Request Headers an Upstream
- ✅ `add_header` für Response Headers an Client
- ✅ `always` Flag wichtig für add_header (auch bei Errors)
- ✅ OpenResty/Lua für komplexe Header-Logik
- ✅ `$request_id` Variable für Request Tracking
- ⚠️ Header Removal: `proxy_set_header X-Header ""` (leerer Wert)
- ⚠️ Response Header Removal: Benötigt `ngx_headers_more` Module (`more_clear_headers`)
- ⚠️ `add_header` wird nicht vererbt (muss in jeder Location definiert werden)

**Testing:**
```bash
# Request Headers testen
curl -v http://nginx-host/api \
  -H "User-Agent: TestClient/1.0" \
  2>&1 | grep ">"

# Response Headers prüfen
curl -I http://nginx-host/api

# Erwartete Response Headers:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-Request-ID: <uuid>

# Header entfernt prüfen
curl -I http://nginx-host/api | grep -i "Server:"
# Sollte leer sein wenn more_clear_headers verwendet wird
```

**Nginx Config für GAL Header Manipulation:**
```nginx
# Vollständiges Beispiel für GAL-generierte Config
http {
    # Custom Log Format mit Request ID
    log_format main_with_headers '$remote_addr - $remote_user [$time_local] '
                                 '"$request" $status $body_bytes_sent '
                                 '"$http_referer" "$http_user_agent" '
                                 'request_id="$request_id"';

    access_log /var/log/nginx/access.log main_with_headers;

    upstream api_backend {
        server api-1.internal:8080;
        server api-2.internal:8080;
    }

    server {
        listen 80;
        server_name api.example.com;

        # Security Headers (für alle Locations)
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000" always;

        location /api/public {
            # Request Headers
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-API-Type "public";
            proxy_set_header X-Request-ID $request_id;

            # Response Headers
            add_header X-API-Version "v1" always;
            add_header Cache-Control "public, max-age=3600" always;

            proxy_pass http://api_backend;
        }

        location /api/private {
            # Request Headers
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-API-Type "private";
            proxy_set_header X-Request-ID $request_id;

            # Response Headers
            add_header X-API-Version "v1" always;
            add_header Cache-Control "private, no-cache" always;

            proxy_pass http://api_backend;
        }
    }
}
```

---

### HAProxy (http-request / http-response)

HAProxy implementiert Header Manipulation mit `http-request` für Request Headers und `http-response` für Response Headers.

**Config-Beispiel:**
```haproxy
# GAL generiert HAProxy-Config
global
    log stdout format raw local0
    maxconn 4096

defaults
    log global
    mode http
    option httplog
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend api_front
    bind *:80

    # Request Headers setzen (an Backend)
    http-request set-header X-Forwarded-For %[src]
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Request-ID %[uuid()]
    http-request add-header X-API-Version v1
    http-request set-header X-Real-IP %[src]

    # Request Headers entfernen
    http-request del-header X-Internal-Token
    http-request del-header X-Debug-Mode

    # Response Headers setzen (an Client)
    http-response set-header X-Frame-Options "DENY"
    http-response set-header X-Content-Type-Options "nosniff"
    http-response set-header X-XSS-Protection "1; mode=block"
    http-response set-header X-Request-ID %[req.hdr(X-Request-ID)]

    # Response Headers entfernen
    http-response del-header Server
    http-response del-header X-Powered-By

    default_backend api_backend

backend api_backend
    balance roundrobin
    server api1 api-1.internal:8080 check
    server api2 api-2.internal:8080 check
```

**Conditional Headers mit ACLs:**
```haproxy
frontend api_front
    bind *:80

    # ACL für verschiedene API Typen
    acl is_public_api path_beg /api/public
    acl is_private_api path_beg /api/private
    acl is_admin_api path_beg /api/admin

    # Conditional Request Headers
    http-request set-header X-API-Type "public" if is_public_api
    http-request set-header X-API-Type "private" if is_private_api
    http-request set-header X-API-Type "admin" if is_admin_api

    # Device Type Detection
    acl is_mobile hdr_sub(User-Agent) -i mobile
    acl is_mobile hdr_sub(User-Agent) -i android
    acl is_mobile hdr_sub(User-Agent) -i iphone
    http-request set-header X-Device-Type "mobile" if is_mobile
    http-request set-header X-Device-Type "desktop" if !is_mobile

    # Response Headers mit Conditions
    http-response set-header Cache-Control "public, max-age=3600" if is_public_api
    http-response set-header Cache-Control "private, no-cache" if is_private_api

    default_backend api_backend
```

**HAProxy Variables für Dynamic Headers:**
```haproxy
frontend api_front
    bind *:80

    # HAProxy Sample Fetch Methods
    http-request set-header X-Client-IP %[src]
    http-request set-header X-Client-Port %[src_port]
    http-request set-header X-Server-Name %[env(HOSTNAME)]
    http-request set-header X-Request-Time %[date()]
    http-request set-header X-Request-ID %[uuid()]

    # Forwarded Headers
    http-request set-header X-Forwarded-For %[src]
    http-request set-header X-Forwarded-Proto %[ssl_fc,iif(https,http)]
    http-request set-header X-Forwarded-Host %[req.hdr(Host)]

    # Response Headers mit Backend-Daten
    http-response set-header X-Backend-Server %[res.hdr(X-Server-ID)]
    http-response set-header X-Response-Time %[res.hdr(X-Processing-Time)]

    default_backend api_backend
```

**Multi-Tenant Headers:**
```haproxy
frontend api_front
    bind *:80

    # Extract Tenant from Subdomain
    acl tenant_acme hdr_beg(Host) -i acme.
    acl tenant_widgets hdr_beg(Host) -i widgets.

    # Set Tenant Headers
    http-request set-header X-Tenant-ID "acme" if tenant_acme
    http-request set-header X-Tenant-ID "widgets" if tenant_widgets

    # Tenant-specific Backend Headers
    http-request set-header X-Tenant-Region "us-west" if tenant_acme
    http-request set-header X-Tenant-Region "eu-central" if tenant_widgets

    default_backend api_backend
```

**HAProxy Besonderheiten**:
- ✅ `http-request set-header` / `http-request add-header` für Request Headers
- ✅ `http-response set-header` / `http-response add-header` für Response Headers
- ✅ `http-request del-header` / `http-response del-header` für Header Removal
- ✅ ACL-basierte Conditional Logic (sehr performant)
- ✅ Sample Fetch Methods: `%[src]`, `%[uuid()]`, `%[req.hdr(Name)]`
- ✅ `set-header` = replace, `add-header` = append
- ✅ `%[req.hdr(Header)]` für Request Header Werte
- ✅ `%[res.hdr(Header)]` für Response Header Werte
- ⚠️ UUID generiert via `%[uuid()]` (HAProxy 1.9+)

**Testing:**
```bash
# Request Headers testen
curl -v http://haproxy-host/api \
  -H "User-Agent: Mobile/1.0" \
  2>&1 | grep ">"

# Response Headers prüfen
curl -I http://haproxy-host/api

# Erwartete Response Headers:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-Request-ID: <uuid>

# Multi-Tenant Testing
curl -I http://acme.example.com/api
# Sollte X-Tenant-ID: acme setzen

# Device Detection Testing
curl -I http://haproxy-host/api -A "Mozilla/5.0 (iPhone)"
# Sollte X-Device-Type: mobile setzen
```

**HAProxy Config für GAL Header Manipulation:**
```haproxy
# Vollständiges Beispiel für GAL-generierte Config
global
    log stdout format raw local0
    maxconn 4096

defaults
    log global
    mode http
    option httplog
    option http-server-close
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend api_front
    bind *:80

    # Standard Security Headers
    http-response set-header X-Frame-Options "DENY"
    http-response set-header X-Content-Type-Options "nosniff"
    http-response set-header X-XSS-Protection "1; mode=block"
    http-response set-header Strict-Transport-Security "max-age=31536000"

    # Remove Backend Disclosure Headers
    http-response del-header Server
    http-response del-header X-Powered-By
    http-response del-header X-AspNet-Version

    # Request Identification
    http-request set-header X-Request-ID %[uuid()]
    http-request set-header X-Forwarded-For %[src]
    http-request set-header X-Real-IP %[src]

    # Route-specific Headers
    acl is_public path_beg /api/public
    acl is_private path_beg /api/private

    http-request set-header X-API-Type "public" if is_public
    http-request set-header X-API-Type "private" if is_private

    http-response set-header X-API-Version "v1"
    http-response set-header Cache-Control "public, max-age=3600" if is_public
    http-response set-header Cache-Control "private, no-cache" if is_private

    default_backend api_backend

backend api_backend
    balance roundrobin
    option httpchk GET /health
    server api1 api-1.internal:8080 check inter 5s
    server api2 api-2.internal:8080 check inter 5s
```

---

### Azure APIM (set-header Policy)

Azure API Management uses Policy XML for header manipulation:

**Request Headers (Inbound)**:
```xml
<policies>
    <inbound>
        <base />
        <set-header name="X-Custom" exists-action="override">
            <value>value</value>
        </set-header>
        <set-header name="X-Internal" exists-action="delete" />
    </inbound>
</policies>
```

**Response Headers (Outbound)**:
```xml
<policies>
    <outbound>
        <base />
        <set-header name="X-Response" exists-action="override">
            <value>ok</value>
        </set-header>
        <set-header name="Server" exists-action="delete" />
    </outbound>
</policies>
```

**exists-action Options**:
- `override`: Replace header if exists, add if not (default for set)
- `append`: Add to existing header value
- `skip`: Only add if doesn't exist
- `delete`: Remove header

**GAL Mapping**:
- `request_add` → `<inbound>` `exists-action="override"`
- `response_add` → `<outbound>` `exists-action="override"`
- `request_remove` → `<inbound>` `exists-action="delete"`
- `response_remove` → `<outbound>` `exists-action="delete"`

### GCP API Gateway

GCP API Gateway unterstützt Header Manipulation über OpenAPI 2.0 und x-google-backend Extensions.

**Header-Features:**
- Mechanismus: OpenAPI 2.0 `parameters` und `x-google-backend`
- Forwarded Headers: X-Forwarded-For, X-Forwarded-Proto automatisch gesetzt
- Custom Headers: Via Backend Service konfigurierbar
- Hinweis: Keine native Response Header Manipulation

**Standard Forwarded Headers:**
GCP API Gateway fügt automatisch folgende Headers hinzu:

```yaml
# Automatisch gesetzte Headers (nicht konfigurierbar)
X-Forwarded-For: <client-ip>
X-Forwarded-Proto: https
X-Forwarded-Host: <gateway-hostname>
X-Cloud-Trace-Context: <trace-id>/<span-id>;<trace-options>
```

**Request Header Injection via OpenAPI:**
```yaml
swagger: "2.0"
info:
  title: "API with Custom Headers"
  version: "1.0.0"

x-google-backend:
  address: https://backend.example.com
  deadline: 30.0

paths:
  /api/users:
    get:
      parameters:
        - name: X-API-Version
          in: header
          required: true
          type: string
          default: "v1"
        - name: X-Request-ID
          in: header
          required: false
          type: string
      x-google-backend:
        address: https://backend.example.com
        jwt_audience: backend-service
```

**Backend Header Transformation:**
```python
# Backend Service (Cloud Run/Cloud Functions/GKE)
# Empfang der Gateway-Headers

from flask import Flask, request

app = Flask(__name__)

@app.route('/api/users')
def users():
    # Gateway-Headers empfangen
    client_ip = request.headers.get('X-Forwarded-For')
    trace_context = request.headers.get('X-Cloud-Trace-Context')
    api_version = request.headers.get('X-API-Version', 'v1')

    # Custom Response Headers setzen
    response = {'users': [...]}
    headers = {
        'X-API-Version': api_version,
        'X-Response-Time': '45ms',
        'X-Trace-ID': trace_context
    }

    return response, 200, headers
```

**Cloud Logging für Header Debugging:**
```bash
# Header-Logs anzeigen
gcloud logging read "resource.type=api AND httpRequest.requestUrl=~\"/api\"" \
  --project=my-project \
  --format=json \
  --limit=10 | jq '.[] | {url: .httpRequest.requestUrl, headers: .httpRequest.requestHeaders}'
```

**Deployment:**
```bash
# API Gateway Config mit Header-Konfiguration deployen
gcloud api-gateway api-configs create config-v1 \
  --api=my-api \
  --openapi-spec=openapi.yaml \
  --project=my-project

# Gateway erstellen
gcloud api-gateway gateways create my-gateway \
  --api=my-api \
  --api-config=config-v1 \
  --location=us-central1 \
  --project=my-project
```

**GCP API Gateway Besonderheiten:**
- ✅ Automatische X-Forwarded-* Headers
- ✅ X-Cloud-Trace-Context für Distributed Tracing
- ✅ Request Header Validation via OpenAPI Schema
- ⚠️ Response Header Manipulation nur via Backend
- ⚠️ Keine native Header Removal auf Gateway-Ebene
- ✅ Integration mit Cloud Trace und Cloud Logging

**Beispiel: CORS Headers (Backend-seitig):**
Da GCP API Gateway keine nativen Response Headers manipulieren kann, müssen CORS-Headers vom Backend gesetzt werden:

```python
# Cloud Run Backend mit CORS
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app,
     origins=['https://example.com'],
     allow_headers=['Content-Type', 'Authorization'],
     expose_headers=['X-Request-ID', 'X-API-Version'],
     max_age=3600)

@app.route('/api/users')
def users():
    # CORS Headers werden automatisch von flask_cors gesetzt
    return {'users': [...]}
```

**Hinweis:** Für umfassende Header Manipulation empfiehlt Google:
1. **Backend-seitige Header-Logik** (empfohlen)
2. **Cloud Endpoints** (erweiterte API Management Features)
3. **Apigee** (Enterprise API Gateway mit vollständiger Header-Kontrolle)

### AWS API Gateway

AWS API Gateway implementiert Header Manipulation über `x-amazon-apigateway-integration` Extensions in OpenAPI 3.0.

**Request Headers (Integration Request):**
- Mechanismus: `requestParameters` im `x-amazon-apigateway-integration` Block
- Mapping: `integration.request.header.X-Custom` ← `method.request.header.User-Agent`
- Static Values: Direkte String-Werte mit einfachen Quotes
- Hinweis: Header-Mapping erfolgt während Integration Request Phase

**Response Headers (Integration Response):**
- Mechanismus: `responseParameters` im `x-amazon-apigateway-integration` Block
- Mapping: `method.response.header.X-Custom` ← `integration.response.header.X-Backend`
- CORS Headers: Automatisch via `cors_enabled: true` oder manuell konfiguriert
- Gateway Response Headers: DEFAULT_4XX, DEFAULT_5XX für Error Responses

**Generiertes OpenAPI Config-Beispiel:**
```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "API with Headers",
    "version": "1.0.0"
  },
  "paths": {
    "/api/users": {
      "get": {
        "responses": {
          "200": {
            "description": "Success",
            "headers": {
              "X-API-Version": {
                "schema": {"type": "string"}
              },
              "X-Request-ID": {
                "schema": {"type": "string"}
              }
            }
          }
        },
        "x-amazon-apigateway-integration": {
          "type": "http_proxy",
          "httpMethod": "GET",
          "uri": "https://backend.example.com/api/users",
          "requestParameters": {
            "integration.request.header.X-API-Version": "'v1'",
            "integration.request.header.X-Gateway": "'AWS-API-Gateway'",
            "integration.request.header.X-Request-ID": "context.requestId"
          },
          "responses": {
            "default": {
              "statusCode": "200",
              "responseParameters": {
                "method.response.header.X-API-Version": "'v1'",
                "method.response.header.X-Request-ID": "context.requestId",
                "method.response.header.Access-Control-Allow-Origin": "'*'"
              }
            }
          }
        }
      }
    }
  }
}
```

**Context Variables:**
AWS API Gateway bietet `$context` Variablen für dynamische Headers:

```json
{
  "requestParameters": {
    "integration.request.header.X-Request-ID": "context.requestId",
    "integration.request.header.X-Request-Time": "context.requestTime",
    "integration.request.header.X-Source-IP": "context.identity.sourceIp",
    "integration.request.header.X-User-Agent": "context.identity.userAgent"
  }
}
```

**Deployment:**
```bash
# 1. OpenAPI mit Header-Konfiguration generieren
gal generate -c config.yaml -p aws_apigateway -o api.json

# 2. API erstellen/updaten
aws apigateway import-rest-api --body file://api.json

# 3. Deployment
aws apigateway create-deployment \
  --rest-api-id abc123xyz \
  --stage-name prod

# 4. Gateway Response Headers (für Errors)
aws apigateway put-gateway-response \
  --rest-api-id abc123xyz \
  --response-type DEFAULT_4XX \
  --response-parameters \
    gatewayresponse.header.Access-Control-Allow-Origin="'*'" \
    gatewayresponse.header.X-Error-Type="'Client-Error'"

aws apigateway put-gateway-response \
  --rest-api-id abc123xyz \
  --response-type DEFAULT_5XX \
  --response-parameters \
    gatewayresponse.header.Access-Control-Allow-Origin="'*'" \
    gatewayresponse.header.X-Error-Type="'Server-Error'"
```

**Testing:**
```bash
# Request Headers testen
curl -v https://abc123.execute-api.us-east-1.amazonaws.com/prod/api/users \
  -H "User-Agent: TestClient/1.0" \
  2>&1 | grep ">"

# Response Headers prüfen
curl -I https://abc123.execute-api.us-east-1.amazonaws.com/prod/api/users

# Erwartete Response Headers:
# X-API-Version: v1
# X-Request-ID: abc123-def456-...
# Access-Control-Allow-Origin: *
```

**CORS Headers (automatisch):**
```yaml
# GAL Config
global_config:
  aws_apigateway:
    cors_enabled: true
    cors_allow_origins: ["https://app.example.com"]
    cors_allow_methods: ["GET", "POST", "PUT", "DELETE"]
    cors_allow_headers: ["Content-Type", "Authorization"]
```

**Generierte CORS Headers:**
```json
{
  "options": {
    "x-amazon-apigateway-integration": {
      "type": "mock",
      "responses": {
        "default": {
          "statusCode": "200",
          "responseParameters": {
            "method.response.header.Access-Control-Allow-Origin": "'https://app.example.com'",
            "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE'",
            "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization'",
            "method.response.header.Access-Control-Max-Age": "'86400'"
          }
        }
      }
    }
  }
}
```

**AWS API Gateway-spezifische Features:**
- ✅ Request Parameter Mapping (Header, Query, Path)
- ✅ Response Parameter Mapping
- ✅ Context Variables ($context.requestId, $context.identity.sourceIp)
- ✅ Gateway Response Headers (DEFAULT_4XX, DEFAULT_5XX)
- ✅ CORS Headers (automatisch via cors_enabled)
- ✅ Static + Dynamic Headers
- ⚠️ Keine Header Removal (nur Mapping)

**Limitierungen:**
- ⚠️ Keine native "Remove Header" Operation (nur Nicht-Mappen)
- ⚠️ Header-Mapping ist deklarativ (kein Scripting wie bei Kong/APISIX)
- ⚠️ Komplexe Transformationen benötigen Lambda Integration
- ❌ Keine Conditional Header Logic (benötigt Lambda Authorizer)

**Advanced: Lambda Integration für komplexe Header-Logik:**
```python
# Lambda Function für Custom Header-Logik
def lambda_handler(event, context):
    headers = event['headers']

    # Custom Header Logic
    custom_headers = {
        'X-Processed-By': 'Lambda',
        'X-Request-ID': event['requestContext']['requestId'],
        'X-User-Tier': 'Premium' if 'x-api-key' in headers else 'Free',
        'X-Rate-Limit-Remaining': '1000'
    }

    # Backend Request (optional)
    # response = requests.get(backend_url, headers=headers)

    return {
        'statusCode': 200,
        'headers': custom_headers,
        'body': json.dumps({'message': 'Success'})
    }
```

**Hinweis:** Für komplexe Header-Manipulationen (Conditional Logic, Regex, etc.) empfiehlt sich die Verwendung von **AWS_PROXY Integration mit Lambda** statt HTTP_PROXY.

---

## Common Use Cases

### 1. Security Headers

Add standard security headers to all responses:

```yaml
headers:
  response_add:
    # Prevent clickjacking
    X-Frame-Options: "DENY"

    # Prevent MIME type sniffing
    X-Content-Type-Options: "nosniff"

    # Enable XSS protection
    X-XSS-Protection: "1; mode=block"

    # HSTS for HTTPS
    Strict-Transport-Security: "max-age=31536000; includeSubDomains"

    # Content Security Policy
    Content-Security-Policy: "default-src 'self'"

  response_remove:
    # Hide backend details
    - Server
    - X-Powered-By
    - X-AspNet-Version
```

### 2. CORS Headers

Enable Cross-Origin Resource Sharing:

```yaml
headers:
  response_add:
    Access-Control-Allow-Origin: "*"
    Access-Control-Allow-Methods: "GET, POST, PUT, DELETE, OPTIONS"
    Access-Control-Allow-Headers: "Content-Type, Authorization"
    Access-Control-Max-Age: "86400"
```

### 3. Request Identification

Add correlation/trace IDs for distributed tracing:

```yaml
headers:
  request_add:
    X-Request-ID: "{{uuid}}"
    X-Correlation-ID: "{{uuid}}"
    X-Trace-ID: "{{uuid}}"

  response_add:
    X-Request-ID: "{{uuid}}"  # Echo request ID in response
```

### 4. Backend Communication

Add internal headers for backend services:

```yaml
headers:
  request_add:
    X-Gateway-Version: "1.0"
    X-Client-IP: "{{client_ip}}"
    X-Forwarded-Proto: "https"
    X-Real-IP: "{{client_ip}}"
```

### 5. Caching Control

Configure caching behavior:

```yaml
# Public API - cacheable
routes:
  - path_prefix: /api/public
    headers:
      response_add:
        Cache-Control: "public, max-age=3600"
        Vary: "Accept-Encoding"

# Private API - no caching
routes:
  - path_prefix: /api/private
    headers:
      response_add:
        Cache-Control: "private, no-cache, no-store, must-revalidate"
        Pragma: "no-cache"
        Expires: "0"
```

### 6. API Versioning

Indicate API version in headers:

```yaml
headers:
  request_add:
    X-API-Version: "v2"

  response_add:
    X-API-Version: "v2"
    X-Deprecated: "false"
```

### 7. Removing Sensitive Information

Strip internal/debug headers:

```yaml
headers:
  request_remove:
    - X-Internal-Token
    - X-Debug-Mode
    - X-Admin-Secret

  response_remove:
    - X-Database-Host
    - X-Internal-Service
    - X-Debug-Info
```

---

## Security Best Practices

### 1. Always Remove Backend Disclosure Headers

```yaml
response_remove:
  - Server           # "Apache/2.4.41", "nginx/1.18.0"
  - X-Powered-By     # "PHP/7.4.3", "Express"
  - X-AspNet-Version # "4.0.30319"
  - X-AspNetMvc-Version
```

### 2. Add Security Headers to All Responses

```yaml
response_add:
  X-Frame-Options: "DENY"
  X-Content-Type-Options: "nosniff"
  X-XSS-Protection: "1; mode=block"
  Strict-Transport-Security: "max-age=31536000; includeSubDomains; preload"
```

### 3. Implement Content Security Policy

```yaml
response_add:
  Content-Security-Policy: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
```

### 4. Remove Debug Headers in Production

```yaml
request_remove:
  - X-Debug
  - X-Trace
  - X-Internal-Request
```

### 5. Sanitize Forwarded Headers

```yaml
# Remove client-provided proxy headers
request_remove:
  - X-Forwarded-For
  - X-Real-IP
  - X-Forwarded-Proto

# Add gateway-verified headers
request_add:
  X-Forwarded-For: "{{client_ip}}"
  X-Real-IP: "{{client_ip}}"
  X-Forwarded-Proto: "https"
```

---

## Testing Header Manipulation

### Using cURL

**Test Request Headers**:
```bash
# Check if header is added to backend
curl -v http://gateway/api \
  -H "X-Test: original" \
  2>&1 | grep "X-Custom"
```

**Test Response Headers**:
```bash
# Check response headers
curl -I http://gateway/api

# Should see added headers
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
```

### Using HTTPie

```bash
# Request headers
http GET http://gateway/api X-Test:original

# Response headers
http HEAD http://gateway/api
```

### Automated Testing

```python
import requests

def test_security_headers():
    response = requests.get('http://gateway/api')

    # Check added headers
    assert 'X-Frame-Options' in response.headers
    assert response.headers['X-Frame-Options'] == 'DENY'

    # Check removed headers
    assert 'Server' not in response.headers
    assert 'X-Powered-By' not in response.headers
```

---

## Troubleshooting

### Headers Not Being Added

**Problem**: Headers configured but not appearing in requests/responses

**Solutions**:
1. **Check provider logs**: Ensure plugins/middlewares are loaded
2. **Verify configuration**: Check YAML syntax for headers section
3. **Test with curl -v**: See exact headers being sent/received
4. **Check middleware order**: Some providers require specific plugin order

**Kong**:
```bash
# Check if plugins are loaded
curl http://localhost:8001/plugins

# Check specific route plugins
curl http://localhost:8001/routes/{route_id}/plugins
```

**APISIX**:
```bash
# Check route configuration
curl http://localhost:9180/apisix/admin/routes/1 \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1"
```

### Headers Being Duplicated

**Problem**: Headers appear multiple times

**Solution**: Use **`request_set`/`response_set`** instead of **`request_add`/`response_add`**

```yaml
# Wrong - causes duplication
headers:
  request_add:
    X-Correlation-ID: "{{uuid}}"  # May add multiple times

# Correct - ensures single value
headers:
  request_set:
    X-Correlation-ID: "{{uuid}}"  # Replaces existing
```

### Headers Not Removed

**Problem**: Headers still appearing despite remove configuration

**Solutions**:
1. **Check header name**: Header names are case-insensitive but must match
2. **Provider-specific**: Some headers may be protected
3. **Order matters**: Remove operations happen at specific phases

```yaml
# Ensure exact header name
response_remove:
  - Server            # Correct
  - server            # Also works (case-insensitive)
  - X-Powered-By      # Exact name required
```

### CORS Issues

**Problem**: CORS errors despite adding CORS headers

**Solution**: Ensure OPTIONS requests are handled correctly

```yaml
routes:
  - path_prefix: /api
    methods: [GET, POST, PUT, DELETE, OPTIONS]  # Include OPTIONS!
    headers:
      response_add:
        Access-Control-Allow-Origin: "*"
        Access-Control-Allow-Methods: "GET, POST, PUT, DELETE, OPTIONS"
        Access-Control-Allow-Headers: "Content-Type, Authorization"
        Access-Control-Max-Age: "86400"
```

### Provider-Specific Issues

**Kong**: Plugin conflicts
```yaml
# Ensure plugins don't conflict
# request-transformer must come before authentication
```

**APISIX**: Plugin priority
```json
{
  "plugins": {
    "proxy-rewrite": { "_meta": {"priority": 1008} },
    "response-rewrite": { "_meta": {"priority": 899} }
  }
}
```

**Traefik**: Middleware order
```yaml
# Middlewares are applied in order listed
routers:
  api:
    middlewares:
      - headers-middleware  # Applied first
      - auth-middleware     # Applied second
```

**Envoy**: Filter chain order
```yaml
# HTTP filters are applied in order
http_filters:
  - name: jwt_authn      # Applied first
  - name: header_manipulation  # Applied second
  - name: router         # Must be last
```

---

## Advanced Patterns

### Conditional Headers

Add headers based on route path:

```yaml
services:
  - name: api
    routes:
      - path_prefix: /api/v1
        headers:
          request_add:
            X-API-Version: "v1"

      - path_prefix: /api/v2
        headers:
          request_add:
            X-API-Version: "v2"
```

### Environment-Specific Headers

```yaml
# Production
headers:
  request_add:
    X-Environment: "production"
  response_remove:
    - X-Debug

# Development
headers:
  request_add:
    X-Environment: "development"
    X-Debug-Mode: "enabled"
```

### Multi-Tenant Headers

```yaml
routes:
  - path_prefix: /tenant/acme
    headers:
      request_add:
        X-Tenant-ID: "acme"
        X-Tenant-Region: "us-west"

  - path_prefix: /tenant/widgets
    headers:
      request_add:
        X-Tenant-ID: "widgets"
        X-Tenant-Region: "eu-central"
```

---

## Conclusion

Header manipulation is a powerful feature that enables:

✅ **Security hardening** through security headers
✅ **CORS support** for cross-origin requests
✅ **Request tracing** with correlation IDs
✅ **Backend communication** via internal headers
✅ **Information hiding** by removing server headers

**Next Steps**:
- Review [AUTHENTICATION.md](AUTHENTICATION.md) for combining headers with auth
- Check [RATE_LIMITING.md](RATE_LIMITING.md) for rate limiting integration
- Explore [examples/headers-test.yaml](https://github.com/pt9912/x-gal/blob/main/examples/headers-test.yaml) for complete examples

**Need Help?**
- Report issues: https://github.com/anthropics/gal/issues
- Documentation: https://docs.gal.dev
- Examples: [examples/](../../examples/)
