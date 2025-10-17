# Authentication Guide

GAL v1.1.0 introduces comprehensive authentication support across all gateway providers. This guide explains how to configure authentication for your APIs using Basic Auth, API Keys, and JWT.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Authentication Types](#authentication-types)
  - [Basic Authentication](#basic-authentication)
  - [API Key Authentication](#api-key-authentication)
  - [JWT Authentication](#jwt-authentication)
- [Configuration Options](#configuration-options)
- [Provider-Specific Implementations](#provider-specific-implementations)
- [Best Practices](#best-practices)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Migration Guide](#migration-guide)

## Overview

Authentication ensures that only authorized users can access your APIs. GAL supports three authentication methods:

| Type | Use Case | Security Level | Complexity |
|------|----------|----------------|------------|
| **Basic Auth** | Internal tools, admin panels | Medium | Low |
| **API Key** | Service-to-service, external APIs | Medium-High | Low |
| **JWT** | Modern web/mobile apps, microservices | High | Medium |

## Quick Start

### API Key Authentication (Simplest)

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

**Test with curl:**
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

**Test with curl:**
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

**Test with curl:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:10000/api/user
```

## Authentication Types

### Basic Authentication

HTTP Basic Authentication uses username/password credentials transmitted in HTTP headers.

#### Configuration

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

#### Parameters

- `users` (dict): Username to password mapping
- `realm` (string): Authentication realm displayed in browser prompt (default: "Protected")
- `fail_status` (int): HTTP status code for auth failures (default: 401)
- `fail_message` (string): Error message for auth failures

#### Security Considerations

⚠️ **Important Security Notes:**
- Passwords should be hashed (e.g., bcrypt, htpasswd format) in production
- Always use HTTPS to protect credentials in transit
- Avoid storing plaintext passwords in configuration files
- Consider using environment variables or secrets management

**Production Example with htpasswd:**

```bash
# Generate htpasswd hash
htpasswd -nb admin secret_password

# Output: admin:$apr1$XYZ123$HASH...
```

```yaml
basic_auth:
  users:
    admin: "$apr1$XYZ123$HASH..."  # htpasswd format
```

### API Key Authentication

API Key authentication uses static keys passed in headers or query parameters.

#### Configuration - Header-based

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

#### Configuration - Query Parameter

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

**Usage:**
```bash
# Header-based
curl -H "X-API-Key: key_123abc" http://localhost:10000/api

# Query parameter
curl "http://localhost:10000/api?api_key=key_123abc"
```

#### Parameters

- `keys` (list): Valid API keys
- `key_name` (string): Header or query parameter name (default: "X-API-Key")
- `in_location` (string): "header" or "query" (default: "header")

#### Best Practices

✅ **Do:**
- Use long, random keys (minimum 32 characters)
- Rotate keys regularly
- Use different keys for different clients
- Log key usage for auditing
- Use header-based auth over query parameters (more secure)

❌ **Don't:**
- Share keys across multiple services
- Store keys in client-side code (mobile apps, JavaScript)
- Use predictable key patterns
- Log keys in application logs

**Key Generation Example:**
```bash
# Generate secure random key
openssl rand -hex 32
# Output: 64-character hexadecimal string
```

### JWT Authentication

JSON Web Tokens (JWT) provide stateless, claims-based authentication.

#### Configuration

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

#### Parameters

- `issuer` (string): Expected JWT issuer (iss claim)
- `audience` (string): Expected JWT audience (aud claim)
- `jwks_uri` (string): JSON Web Key Set endpoint URL
- `algorithms` (list): Allowed signing algorithms (default: ["RS256"])
- `required_claims` (list): Claims that must be present in the token

#### Common JWT Algorithms

| Algorithm | Type | Use Case |
|-----------|------|----------|
| **RS256** | RSA | Most common, public key verification |
| **ES256** | ECDSA | Smaller signatures, modern choice |
| **HS256** | HMAC | Symmetric, use only for internal services |

#### JWKS (JSON Web Key Set)

GAL automatically fetches and caches public keys from the JWKS endpoint.

**Example JWKS endpoint:**
```
https://auth.example.com/.well-known/jwks.json
```

**JWKS structure:**
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

**Standard Claims:**
- `iss` (issuer): Token issuer URL
- `sub` (subject): User ID or identifier
- `aud` (audience): Intended recipient
- `exp` (expiration): Token expiration time
- `iat` (issued at): Token creation time
- `nbf` (not before): Token not valid before this time

**Custom Claims:**
You can add custom claims (e.g., `email`, `roles`, `permissions`) and validate them in your backend.

#### JWT Example

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

## Configuration Options

### Common Options

All authentication types share these common options:

```yaml
authentication:
  enabled: true              # Enable/disable authentication
  type: "api_key"           # Authentication type: "basic", "api_key", "jwt"
  fail_status: 401           # HTTP status for auth failures (default: 401)
  fail_message: "Unauthorized"  # Error message for failures
```

### Type-Specific Options

#### Basic Auth
```yaml
basic_auth:
  users:                    # Username-password mapping
    username: "password"
  realm: "Protected"        # Authentication realm
```

#### API Key
```yaml
api_key:
  keys:                     # List of valid API keys
    - "key1"
    - "key2"
  key_name: "X-API-Key"     # Header or query param name
  in_location: "header"     # "header" or "query"
```

#### JWT
```yaml
jwt:
  issuer: "https://auth.example.com"        # Token issuer
  audience: "api.example.com"               # Token audience
  jwks_uri: "https://auth.example.com/..."  # JWKS endpoint
  algorithms:                               # Allowed algorithms
    - RS256
  required_claims:                          # Required JWT claims
    - sub
```

### Multiple Routes with Different Auth

```yaml
services:
  - name: multi_auth_service
    type: rest
    protocol: http
    upstream:
      host: service.local
      port: 8080
    routes:
      # Public endpoint - no auth
      - path_prefix: /api/public
        methods: [GET]

      # API key protected
      - path_prefix: /api/protected
        methods: [GET, POST]
        authentication:
          type: api_key
          api_key:
            keys: ["key123"]

      # Admin - basic auth
      - path_prefix: /api/admin
        methods: [GET, POST, DELETE]
        authentication:
          type: basic
          basic_auth:
            users:
              admin: "secret"
```

## Provider-Specific Implementations

### Kong

Kong implements authentication using native plugins.

**Basic Auth:**
- Plugin: `basic-auth`
- Features: Consumer-based authentication, credential storage

**API Key:**
- Plugin: `key-auth`
- Features: Flexible key location (header/query), consumer association

**JWT:**
- Plugin: `jwt`
- Features: JWKS support, claim verification, RS256/ES256/HS256

**Generated Config Example:**
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

APISIX implements authentication using plugins with JSON configuration.

**Basic Auth:**
- Plugin: `basic-auth`
- Features: Consumer-based, flexible configuration

**API Key:**
- Plugin: `key-auth`
- Features: Header and query parameter support

**JWT:**
- Plugin: `jwt-auth`
- Features: Algorithm selection, issuer/audience validation

**Generated Config Example:**
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

Traefik implements authentication using middleware.

**Basic Auth:**
- Middleware: `basicAuth`
- Features: Users list, realm configuration
- Note: Use htpasswd format for production

**API Key:**
- Middleware: `forwardAuth`
- Features: External validation service
- Note: Requires external API key validator

**JWT:**
- Middleware: `forwardAuth`
- Features: External JWT validation service
- Note: Requires external JWT validator

**Generated Config Example:**
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

Envoy implements authentication using HTTP filters.

**Basic Auth:**
- Filter: `envoy.filters.http.lua`
- Features: Inline Lua validation
- Note: Production requires external auth service

**API Key:**
- Filter: `envoy.filters.http.lua`
- Features: Header validation via Lua
- Note: Production requires external validation

**JWT:**
- Filter: `envoy.filters.http.jwt_authn`
- Features: Full JWT validation, JWKS support, native RS256/ES256
- Note: Most robust JWT implementation

**Generated Config Example:**
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

### General Security

1. **Always use HTTPS in production**
   - Protects credentials and tokens in transit
   - Required for Basic Auth and API Keys
   - Recommended for all authentication types

2. **Use strong credentials**
   - Passwords: Minimum 12 characters, mixed case, special characters
   - API Keys: Minimum 32 characters, cryptographically random
   - JWT secrets: Minimum 256 bits for HS256

3. **Rotate credentials regularly**
   - API Keys: Every 90 days
   - JWT signing keys: Every 6-12 months
   - Passwords: Every 90 days or on compromise

4. **Implement rate limiting**
   - Combine authentication with rate limiting
   - Protect against brute force attacks
   - Use per-user or per-key limits

### Authentication Type Selection

**Use Basic Auth when:**
- Internal tools and admin interfaces
- Small number of known users
- Simplicity is more important than advanced features

**Use API Key when:**
- Service-to-service communication
- External API access for partners
- Simple credential management needed

**Use JWT when:**
- Modern web or mobile applications
- Microservices architecture
- Stateless authentication required
- Short-lived tokens needed
- Claims-based authorization required

### Production Considerations

1. **Never hardcode credentials**
   ```yaml
   # Bad - hardcoded in config
   users:
     admin: "password123"

   # Good - use environment variables
   users:
     admin: "${ADMIN_PASSWORD}"
   ```

2. **Use secrets management**
   - HashiCorp Vault
   - AWS Secrets Manager
   - Kubernetes Secrets
   - Azure Key Vault

3. **Implement proper logging**
   - Log authentication attempts (success and failure)
   - Don't log credentials or tokens
   - Monitor for suspicious patterns

4. **Add monitoring and alerting**
   - Track authentication failure rates
   - Alert on unusual patterns
   - Monitor token expiration and rotation

## Testing

### Testing Basic Auth

```bash
# Valid credentials
curl -u admin:secret http://localhost:10000/api/admin
# Expected: 200 OK

# Invalid credentials
curl -u admin:wrong http://localhost:10000/api/admin
# Expected: 401 Unauthorized

# Missing credentials
curl http://localhost:10000/api/admin
# Expected: 401 Unauthorized
```

### Testing API Key Auth

```bash
# Valid API key in header
curl -H "X-API-Key: key_123abc" http://localhost:10000/api/protected
# Expected: 200 OK

# Valid API key in query parameter
curl "http://localhost:10000/api/protected?api_key=key_123abc"
# Expected: 200 OK

# Invalid API key
curl -H "X-API-Key: invalid_key" http://localhost:10000/api/protected
# Expected: 401 Unauthorized

# Missing API key
curl http://localhost:10000/api/protected
# Expected: 401 Unauthorized
```

### Testing JWT Auth

First, generate a test JWT token at https://jwt.io or using a library:

```python
import jwt
import time

# Generate JWT
payload = {
    "iss": "https://auth.example.com",
    "sub": "user123",
    "aud": "api.example.com",
    "exp": int(time.time()) + 3600,
    "iat": int(time.time())
}

# Use your private key
token = jwt.encode(payload, private_key, algorithm="RS256")
```

```bash
# Valid JWT token
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:10000/api/user
# Expected: 200 OK

# Invalid JWT token
curl -H "Authorization: Bearer invalid.token.here" http://localhost:10000/api/user
# Expected: 401 Unauthorized

# Missing Authorization header
curl http://localhost:10000/api/user
# Expected: 401 Unauthorized

# Expired token
curl -H "Authorization: Bearer EXPIRED_TOKEN" http://localhost:10000/api/user
# Expected: 401 Unauthorized
```

### Load Testing with Authentication

```bash
# Apache Bench with API key
ab -n 1000 -c 10 -H "X-API-Key: key_123abc" http://localhost:10000/api/protected

# wrk with JWT
wrk -t4 -c100 -d30s -H "Authorization: Bearer YOUR_JWT" http://localhost:10000/api/user
```

## Troubleshooting

### Common Issues

#### 1. 401 Unauthorized with correct credentials

**Symptom:** Authentication fails even with correct credentials

**Possible causes:**
- Credentials not properly configured in gateway
- Typo in username/password/key
- Wrong authentication type configured
- Case sensitivity issues

**Solution:**
```bash
# Check generated config
python gal-cli.py generate -f examples/authentication-test.yaml

# Verify credentials in output
# For Basic Auth, check users section
# For API Key, check keys list
# For JWT, verify issuer/audience
```

#### 2. JWT validation fails

**Symptom:** Valid JWT tokens are rejected

**Possible causes:**
- Incorrect issuer or audience
- JWKS endpoint unreachable
- Token expired
- Algorithm mismatch
- Required claims missing

**Solution:**
```bash
# Verify JWT at jwt.io
# Check issuer matches configuration
# Verify JWKS endpoint is accessible
curl https://auth.example.com/.well-known/jwks.json

# Check token expiration
# Verify algorithm in JWT header matches config
```

#### 3. API key not recognized

**Symptom:** API key in header/query is not validated

**Possible causes:**
- Key name mismatch (case sensitive)
- Location mismatch (header vs query)
- Key not in configured keys list
- Special characters in key causing parsing issues

**Solution:**
```yaml
# Verify configuration
authentication:
  type: api_key
  api_key:
    key_name: X-API-Key  # Must match exactly (case-sensitive)
    in_location: header   # Must match request location
    keys:
      - "your_actual_key"  # Must match exactly
```

#### 4. Basic Auth prompts not appearing

**Symptom:** Browser doesn't show authentication prompt

**Possible causes:**
- Incorrect realm configuration
- Previous cached credentials
- Browser security settings

**Solution:**
- Clear browser cache and cookies
- Test with curl first
- Verify realm is configured correctly

#### 5. JWKS fetch failures (Envoy)

**Symptom:** Envoy cannot fetch JWKS

**Possible causes:**
- JWKS cluster not configured
- DNS resolution failure
- HTTPS certificate validation failure
- Network connectivity issues

**Solution:**
- Verify JWKS URL is accessible
- Check cluster configuration includes TLS settings
- Test JWKS endpoint manually:
```bash
curl https://auth.example.com/.well-known/jwks.json
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Generate config with verbose output
python gal-cli.py generate -f config.yaml --verbose

# Check gateway logs
# Kong
docker logs <kong-container>

# APISIX
docker logs <apisix-container>

# Traefik
docker logs <traefik-container>

# Envoy
docker logs <envoy-container>
```

## Migration Guide

### From v1.0.0 to v1.1.0

Authentication is a new feature in v1.1.0. Existing configurations without authentication will continue to work.

**Adding authentication to existing routes:**

```yaml
# Before (v1.0.0)
routes:
  - path_prefix: /api/users
    methods: [GET, POST]

# After (v1.1.0)
routes:
  - path_prefix: /api/users
    methods: [GET, POST]
    authentication:  # New field
      enabled: true
      type: api_key
      api_key:
        keys: ["your_key"]
```

### Combining with Rate Limiting

Authentication and rate limiting work together seamlessly:

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
      key_claim: sub  # Rate limit per JWT subject
```

## Advanced Topics

### Multi-tenancy with JWT Claims

Use JWT claims for multi-tenant rate limiting:

```yaml
rate_limit:
  enabled: true
  key_type: jwt_claim
  key_claim: tenant_id  # Custom claim
  requests_per_second: 100
```

### OAuth 2.0 Integration

GAL JWT support works with any OAuth 2.0 / OIDC provider:

- Auth0
- Okta
- Keycloak
- AWS Cognito
- Azure AD
- Google Cloud Identity

Configure the JWKS endpoint from your OAuth provider:

```yaml
jwt:
  issuer: "https://your-tenant.auth0.com/"
  audience: "https://your-api.example.com"
  jwks_uri: "https://your-tenant.auth0.com/.well-known/jwks.json"
```

### Custom Authentication

For custom authentication requirements not covered by built-in types:

1. **Traefik**: Use forwardAuth middleware with custom validation service
2. **Envoy**: Use ext_authz filter with custom gRPC/HTTP service
3. **Kong**: Develop custom plugin
4. **APISIX**: Use serverless plugin with Lua code

## Summary

GAL v1.1.0 provides comprehensive authentication support:

✅ Three authentication types: Basic, API Key, JWT
✅ All four gateway providers supported
✅ Per-route authentication configuration
✅ Combine with rate limiting
✅ Production-ready JWT with JWKS support
✅ Flexible credential management

For questions or issues, visit: https://github.com/your-org/gal/issues
