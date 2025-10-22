# Apache APISIX Provider Anleitung

**Umfassende Anleitung für Apache APISIX Provider in GAL (Gateway Abstraction Layer)**

## Inhaltsverzeichnis

1. [Übersicht](#ubersicht)
2. [Schnellstart](#schnellstart)
3. [Installation und Setup](#installation-und-setup)
4. [Konfigurationsoptionen](#konfigurationsoptionen)
5. [Provider-Vergleich](#provider-vergleich)

**Weitere Dokumentation:**
- [Feature-Implementierungen](APISIX_FEATURES.md) - Details zu Plugins, Auth, Rate Limiting, Circuit Breaker
- [Best Practices & Troubleshooting](APISIX_DEPLOYMENT.md) - Best Practices, Troubleshooting

---
## Übersicht

**Apache APISIX** ist ein hochperformantes, cloud-natives API-Gateway basierend auf Nginx und OpenResty. Es bietet dynamische Routing-, Plugin- und Load-Balancing-Funktionen mit extrem geringer Latenz.

### Warum APISIX?

- **🚀 Performance**: Basiert auf Nginx/OpenResty - ultra-niedrige Latenz
- **🔌 Plugin-Ökosystem**: 80+ offizielle Plugins für alle Anwendungsfälle
- **☁️ Cloud-Native**: Kubernetes-native mit etcd für Service Discovery
- **📊 Dashboard**: Grafische Benutzeroberfläche für einfache Verwaltung
- **🔄 Dynamic Configuration**: Änderungen ohne Neustart (via etcd)
- **🌍 Multi-Protocol**: HTTP/HTTPS, gRPC, WebSocket, MQTT, Dubbo

### Feature-Matrix

| Feature | APISIX Support | GAL Implementation |
|---------|----------------|-------------------|
| Load Balancing | ✅ Vollständig | `upstream.load_balancer` |
| Active Health Checks | ✅ Native | `upstream.health_check.active` |
| Passive Health Checks | ✅ Native | `upstream.health_check.passive` |
| Rate Limiting | ✅ limit-req, limit-count | `route.rate_limit` |
| Authentication | ✅ JWT, Basic, Key | `route.authentication` |
| CORS | ✅ cors Plugin | `route.cors` |
| Timeout & Retry | ✅ timeout, proxy-retry | `route.timeout`, `route.retry` |
| Circuit Breaker | ✅ api-breaker Plugin | `upstream.circuit_breaker` |
| WebSocket | ✅ Native | `route.websocket` |
| Header Manipulation | ✅ Plugins | `route.headers` |
| Body Transformation | ✅ Serverless Lua | `route.body_transformation` |

**Bewertung**: ✅ = Vollständig unterstützt | ⚠️ = Teilweise unterstützt | ❌ = Nicht unterstützt

---

## Schnellstart

### Beispiel 1: Basic Load Balancing

```yaml
services:
  - name: api_service
    protocol: http
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
        - host: api-2.internal
          port: 8080
      load_balancer:
        algorithm: round_robin
    routes:
      - path_prefix: /api
```

**Generierte APISIX-Konfiguration:**

```json
{
  "routes": [{
    "uri": "/api*",
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "api-1.internal:8080": 1,
        "api-2.internal:8080": 1
      }
    }
  }]
}
```

### Beispiel 2: JWT Authentication + Rate Limiting

```yaml
services:
  - name: secure_api
    protocol: http
    upstream:
      host: api.internal
      port: 8080
    routes:
      - path_prefix: /api
        authentication:
          enabled: true
          type: jwt
          jwt:
            issuer: "https://auth.example.com"
            audiences: ["api"]
        rate_limit:
          enabled: true
          requests_per_second: 100
```

**Generierte APISIX-Konfiguration:**

```json
{
  "routes": [{
    "uri": "/api*",
    "plugins": {
      "jwt-auth": {
        "key": "api-key",
        "secret": "secret-key"
      },
      "limit-count": {
        "count": 100,
        "time_window": 1,
        "rejected_code": 429
      }
    }
  }]
}
```

### Beispiel 3: Complete Production Setup

```yaml
services:
  - name: production_api
    protocol: http
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
          weight: 3
        - host: api-2.internal
          port: 8080
          weight: 1
      load_balancer:
        algorithm: weighted
      health_check:
        active:
          enabled: true
          path: /health
          interval: 5s
          timeout: 3s
          healthy_threshold: 2
          unhealthy_threshold: 3
      circuit_breaker:
        enabled: true
        max_failures: 5
        timeout: 30s
    routes:
      - path_prefix: /api
        rate_limit:
          enabled: true
          requests_per_second: 100
        timeout:
          connect: 5s
          read: 30s
        retry:
          enabled: true
          attempts: 3
```

---

## Installation und Setup

### Docker (Empfohlen)

```bash
# APISIX mit etcd starten
docker run -d --name apisix \
  -p 9080:9080 \
  -p 9443:9443 \
  -p 9180:9180 \
  apache/apisix:latest

# APISIX Dashboard (optional)
docker run -d --name apisix-dashboard \
  -p 9000:9000 \
  apache/apisix-dashboard:latest
```

### Docker Compose

```yaml
version: "3"
services:
  apisix:
    image: apache/apisix:latest
    ports:
      - "9080:9080"
      - "9443:9443"
      - "9180:9180"
    volumes:
      - ./apisix_conf:/usr/local/apisix/conf
      - ./apisix-config.yaml:/usr/local/apisix/conf/apisix.yaml
    depends_on:
      - etcd

  etcd:
    image: bitnami/etcd:latest
    environment:
      - ALLOW_NONE_AUTHENTICATION=yes
      - ETCD_ADVERTISE_CLIENT_URLS=http://etcd:2379
    ports:
      - "2379:2379"
```

### Kubernetes (Helm)

```bash
# APISIX Helm Repository hinzufügen
helm repo add apisix https://charts.apiseven.com
helm repo update

# APISIX Ingress Controller installieren
helm install apisix apisix/apisix \
  --namespace apisix \
  --create-namespace \
  --set gateway.type=LoadBalancer
```

### GAL-Konfiguration generieren

```bash
# APISIX-Konfiguration generieren
gal generate --config config.yaml --provider apisix --output apisix-config.yaml

# Oder via Docker
docker run --rm -v $(pwd):/app ghcr.io/pt9912/x-gal:latest \
  generate --config config.yaml --provider apisix --output apisix-config.yaml
```

### Konfiguration anwenden

APISIX unterstützt zwei Konfigurationsmethoden:

**1. Admin API (Empfohlen für Dynamik)**

```bash
# Route erstellen
curl -X PUT http://localhost:9180/apisix/admin/routes/1 \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  -d @apisix-config.yaml
```

**2. Deklarative Konfiguration (apisix.yaml)**

```bash
# Konfigurationsdatei kopieren
cp apisix-config.yaml /usr/local/apisix/conf/apisix.yaml

# APISIX neu laden
docker exec apisix apisix reload
```

---

## Konfigurationsoptionen

### Global Config

```yaml
global:
  host: 0.0.0.0
  port: 9080
  log_level: info
```

**APISIX Mapping:**

```yaml
# conf/config.yaml
apisix:
  node_listen: 9080
  enable_admin: true
  config_center: etcd
```

### Upstream Config

```yaml
services:
  - name: my_service
    upstream:
      targets:
        - host: backend-1.internal
          port: 8080
          weight: 1
      load_balancer:
        algorithm: round_robin
      health_check:
        active:
          enabled: true
          path: /health
```

**APISIX Mapping:**

```json
{
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "backend-1.internal:8080": 1
    },
    "checks": {
      "active": {
        "http_path": "/health",
        "healthy": {
          "interval": 5,
          "successes": 2
        }
      }
    }
  }
}
```

### Route Config

```yaml
routes:
  - path_prefix: /api
    rate_limit:
      enabled: true
      requests_per_second: 100
```

**APISIX Mapping:**

```json
{
  "routes": [{
    "uri": "/api*",
    "plugins": {
      "limit-count": {
        "count": 100,
        "time_window": 1
      }
    }
  }]
}
```

---

## Feature-Implementierungen

### 1. Load Balancing

APISIX unterstützt 4 Load-Balancing-Algorithmen:

| GAL Algorithm | APISIX Type | Beschreibung |
|---------------|-------------|--------------|
| `round_robin` | `roundrobin` | Gleichmäßige Verteilung |
| `least_conn` | `least_conn` | Verbindung zu Server mit wenigsten aktiven Connections |
| `ip_hash` | `chash` | Consistent Hashing nach Client-IP |
| `weighted` | `roundrobin` + weights | Gewichtete Verteilung |

**Implementierung** (gal/providers/apisix.py:247-265):

```python
# Load Balancing
lb_algo = "roundrobin"  # Default
if service.upstream and service.upstream.load_balancer:
    lb_config = service.upstream.load_balancer
    if lb_config.algorithm == "least_conn":
        lb_algo = "least_conn"
    elif lb_config.algorithm == "ip_hash":
        lb_algo = "chash"
        upstream_config["key"] = "remote_addr"
    elif lb_config.algorithm in ["round_robin", "weighted"]:
        lb_algo = "roundrobin"

upstream_config["type"] = lb_algo
```

**Beispiel:**

```yaml
upstream:
  targets:
    - host: api-1.internal
      port: 8080
      weight: 3
    - host: api-2.internal
      port: 8080
      weight: 1
  load_balancer:
    algorithm: weighted
```

### 2. Health Checks

APISIX bietet Active und Passive Health Checks mit detaillierter Konfiguration.

**Active Health Checks** (gal/providers/apisix.py:267-280):

```python
if service.upstream and service.upstream.health_check:
    hc = service.upstream.health_check
    if hc.active and hc.active.enabled:
        upstream_config["checks"] = {
            "active": {
                "type": "http",
                "http_path": hc.active.path,
                "healthy": {
                    "interval": int(hc.active.interval.rstrip("sS")),
                    "successes": hc.active.healthy_threshold,
                },
                "unhealthy": {
                    "interval": int(hc.active.interval.rstrip("sS")),
                    "http_failures": hc.active.unhealthy_threshold,
                },
            }
        }
```

**Passive Health Checks** (gal/providers/apisix.py:281-290):

```python
if hc.passive and hc.passive.enabled:
    if "checks" not in upstream_config:
        upstream_config["checks"] = {}
    upstream_config["checks"]["passive"] = {
        "type": "http",
        "healthy": {"successes": 3},
        "unhealthy": {
            "http_failures": hc.passive.max_failures,
        },
    }
```

**Beispiel:**

```yaml
upstream:
  health_check:
    active:
      enabled: true
      path: /health
      interval: 5s
      timeout: 3s
      healthy_threshold: 2
      unhealthy_threshold: 3
    passive:
      enabled: true
      max_failures: 5
```

### 3. Rate Limiting

APISIX bietet zwei Rate-Limiting-Plugins:

**limit-count Plugin** (empfohlen):

```python
# gal/providers/apisix.py:323-332
if route.rate_limit and route.rate_limit.enabled:
    rl = route.rate_limit
    plugins["limit-count"] = {
        "count": rl.requests_per_second,
        "time_window": 1,
        "rejected_code": 429,
        "rejected_msg": "Too many requests",
        "key": "remote_addr",  # oder "http_x_api_key"
        "policy": "local",
    }
```

**limit-req Plugin** (Nginx-Stil):

```json
{
  "plugins": {
    "limit-req": {
      "rate": 100,
      "burst": 200,
      "rejected_code": 429,
      "key": "remote_addr"
    }
  }
}
```

**Beispiel:**

```yaml
routes:
  - path_prefix: /api
    rate_limit:
      enabled: true
      requests_per_second: 100
      burst: 200
```

### 4. Authentication

APISIX unterstützt JWT, Basic Auth und API Key Authentication.

**JWT Authentication** (gal/providers/apisix.py:334-352):

```python
if route.authentication and route.authentication.enabled:
    auth_type = route.authentication.type
    if auth_type == "jwt":
        jwt_config = route.authentication.jwt
        plugins["jwt-auth"] = {
            "key": "api-key",
            "secret": "secret-key",
            "algorithm": "HS256",
        }
```

**Basic Authentication:**

```json
{
  "plugins": {
    "basic-auth": {}
  },
  "consumers": [{
    "username": "admin",
    "plugins": {
      "basic-auth": {
        "username": "admin",
        "password": "admin123"
      }
    }
  }]
}
```

**API Key Authentication:**

```json
{
  "plugins": {
    "key-auth": {}
  },
  "consumers": [{
    "username": "user1",
    "plugins": {
      "key-auth": {
        "key": "api-key-12345"
      }
    }
  }]
}
```

**Beispiel:**

```yaml
routes:
  - path_prefix: /api
    authentication:
      enabled: true
      type: jwt
      jwt:
        issuer: "https://auth.example.com"
        audiences: ["api"]
```

### 5. CORS

APISIX verwendet das `cors` Plugin für Cross-Origin Resource Sharing.

**Implementierung** (gal/providers/apisix.py:354-365):

```python
if route.cors and route.cors.enabled:
    cors_config = route.cors
    plugins["cors"] = {
        "allow_origins": ",".join(cors_config.allowed_origins),
        "allow_methods": ",".join(cors_config.allowed_methods or ["*"]),
        "allow_headers": ",".join(cors_config.allowed_headers or ["*"]),
        "allow_credential": cors_config.allow_credentials,
        "max_age": cors_config.max_age or 86400,
    }
```

**Beispiel:**

```yaml
routes:
  - path_prefix: /api
    cors:
      enabled: true
      allowed_origins:
        - "https://app.example.com"
        - "https://admin.example.com"
      allowed_methods: ["GET", "POST", "PUT", "DELETE"]
      allow_credentials: true
```

### 6. Timeout & Retry

**Timeout Configuration** (gal/providers/apisix.py:294-307):

```python
if route.timeout:
    if "plugins" not in route_config:
        route_config["plugins"] = {}
    timeout = route.timeout
    connect_seconds = int(timeout.connect.rstrip("sS"))
    send_seconds = int(timeout.send.rstrip("sS"))
    read_seconds = int(timeout.read.rstrip("sS"))
    route_config["plugins"]["timeout"] = {
        "connect": connect_seconds,
        "send": send_seconds,
        "read": read_seconds,
    }
```

**Retry Configuration** (gal/providers/apisix.py:309-341):

```python
if route.retry and route.retry.enabled:
    retry = route.retry
    retry_status_codes = []
    for condition in retry.retry_on:
        if condition == "http_502":
            retry_status_codes.append(502)
        elif condition == "http_503":
            retry_status_codes.append(503)
        elif condition == "http_504":
            retry_status_codes.append(504)
        elif condition == "http_5xx":
            retry_status_codes.extend([500, 502, 503, 504])

    route_config["plugins"]["proxy-retry"] = {
        "retries": retry.attempts,
        "retry_timeout": int(retry.max_interval.rstrip("msMS")),
        "vars": [["status", "==", code] for code in retry_status_codes],
    }
```

**Beispiel:**

```yaml
routes:
  - path_prefix: /api
    timeout:
      connect: 5s
      read: 30s
      send: 30s
    retry:
      enabled: true
      attempts: 3
      retry_on: ["http_502", "http_503", "http_504"]
```

### 7. Circuit Breaker

APISIX verwendet das `api-breaker` Plugin.

**Implementierung** (gal/providers/apisix.py:371-382):

```python
if service.upstream and service.upstream.circuit_breaker:
    cb = service.upstream.circuit_breaker
    if cb.enabled:
        plugins["api-breaker"] = {
            "break_response_code": 503,
            "unhealthy": {
                "http_statuses": [500, 502, 503, 504],
                "failures": cb.max_failures,
            },
            "healthy": {
                "successes": 3,
            },
        }
```

**Beispiel:**

```yaml
upstream:
  circuit_breaker:
    enabled: true
    max_failures: 5
    timeout: 30s
```

### 8. WebSocket

APISIX unterstützt WebSocket nativ über das `enable_websocket` Flag.

**Implementierung** (gal/providers/apisix.py:291-294):

```python
# WebSocket support
if route.websocket and route.websocket.enabled:
    route_config["enable_websocket"] = True
```

**Beispiel:**

```yaml
routes:
  - path_prefix: /ws
    websocket:
      enabled: true
      idle_timeout: 300s
```

### 9. Header Manipulation

APISIX verwendet die Plugins `request-transformer` und `response-transformer`.

**Request Headers:**

```json
{
  "plugins": {
    "proxy-rewrite": {
      "headers": {
        "X-Request-ID": "$request_id",
        "X-Gateway": "GAL-APISIX"
      }
    }
  }
}
```

**Response Headers:**

```json
{
  "plugins": {
    "response-rewrite": {
      "headers": {
        "X-Server": "APISIX",
        "X-Response-Time": "$upstream_response_time"
      }
    }
  }
}
```

### 10. Body Transformation

APISIX verwendet Serverless Lua-Funktionen für Body-Transformation.

**Implementierung** (gal/providers/apisix.py:512-620):

```python
def _generate_apisix_request_transformation_lua(self, transformation):
    """Generate Lua code for request body transformation."""
    lua_code = """
local core = require("apisix.core")
local cjson = require("cjson.safe")

-- Read request body
local body, err = core.request.get_body()
if not body then
    return
end

-- Parse JSON
local json_body = cjson.decode(body)
if not json_body then
    return
end
"""
    # Add fields
    if transformation.add_fields:
        lua_code += "\n-- Add fields\n"
        for key, value in transformation.add_fields.items():
            if value == "{{uuid}}":
                lua_code += f'json_body["{key}"] = core.utils.uuid()\n'
            elif value in ["{{now}}", "{{timestamp}}"]:
                lua_code += f'json_body["{key}"] = os.date("%Y-%m-%dT%H:%M:%S")\n'
            else:
                lua_code += f'json_body["{key}"] = "{value}"\n'

    # Remove fields
    if transformation.remove_fields:
        lua_code += "\n-- Remove fields\n"
        for field in transformation.remove_fields:
            lua_code += f'json_body["{field}"] = nil\n'

    return lua_code
```

**Beispiel:**

```yaml
routes:
  - path_prefix: /api
    body_transformation:
      enabled: true
      request:
        add_fields:
          trace_id: "{{uuid}}"
          timestamp: "{{now}}"
        remove_fields:
          - internal_id
```

---

## Provider-Vergleich

| Feature | APISIX | Envoy | Kong | Traefik | Nginx | HAProxy |
|---------|--------|-------|------|---------|-------|---------|
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Ease of Use** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Dynamic Config** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ | ⚠️ |
| **Plugin System** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⚠️ | ⚠️ |
| **Dashboard** | ⭐⭐⭐⭐⭐ | ⚠️ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ | ⭐⭐⭐ |
| **Cloud-Native** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |

### APISIX vs Envoy
- **APISIX**: Einfacher, besseres Plugin-Ökosystem, Dashboard, Lua-Programmierbarkeit
- **Envoy**: Tiefere Integration mit Service Mesh (Istio), bessere Observability

### APISIX vs Kong
- **APISIX**: Schneller, kostenlos (Open Source), etcd-basiert
- **Kong**: Reiferes Ökosystem, Enterprise-Features, PostgreSQL/Cassandra

### APISIX vs Traefik
- **APISIX**: Mehr Plugins, bessere Performance, Lua-Scripting
- **Traefik**: Einfachere Konfiguration, bessere Let's Encrypt Integration

### APISIX vs Nginx/HAProxy
- **APISIX**: Dynamische Konfiguration, Plugins, Dashboard
- **Nginx/HAProxy**: Niedriger Overhead, etablierter, kein etcd erforderlich

---

