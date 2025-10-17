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
| **Kong** | ✅ | ✅ | request-transformer, response-transformer plugins |
| **APISIX** | ✅ | ✅ | proxy-rewrite, response-rewrite plugins |
| **Traefik** | ✅ | ✅ | headers middleware |
| **Envoy** | ✅ | ✅ | Native route-level header manipulation |

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
- Explore [examples/headers-test.yaml](../../examples/headers-test.yaml) for complete examples

**Need Help?**
- Report issues: https://github.com/anthropics/gal/issues
- Documentation: https://docs.gal.dev
- Examples: [examples/](../../examples/)
