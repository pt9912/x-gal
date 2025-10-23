# GAL Provider-Dokumentation

## Übersicht

GAL unterstützt neun führende API-Gateway-Provider - sechs selbst-gehostete und drei Cloud-native Provider. Jeder Provider hat spezifische Eigenschaften, Stärken und ideale Use Cases.

## Unterstützte Provider

| Provider | Output-Format | Transformations | gRPC | REST | GAL Deploy API | Cloud |
|----------|--------------|-----------------|------|------|----------------|-------|
| Envoy | YAML | Lua Filters | ✅ | ✅ | ✅ File + API check | Self-Hosted |
| Kong | YAML | Plugins | ✅ | ✅ | ✅ File + Admin API | Self-Hosted |
| APISIX | JSON | Lua Serverless | ✅ | ✅ | ✅ File + Admin API | Self-Hosted |
| Traefik | YAML | Middleware | ✅ | ✅ | ✅ File + API verify | Self-Hosted |
| Nginx | CONF | ngx_http modules | ✅ | ✅ | ✅ File + reload | Self-Hosted |
| HAProxy | CFG | ACLs + Lua | ✅ | ✅ | ✅ File + reload | Self-Hosted |
| **Azure APIM** | **ARM+JSON** | **Policy XML** | **✅** | **✅** | **✅ ARM Deploy** | **Azure Cloud** |
| **GCP API Gateway** | **OpenAPI 2.0** | **Backend-basiert** | **⚠️** | **✅** | **✅ gcloud CLI** | **Google Cloud** |
| **AWS API Gateway** | **OpenAPI 3.0** | **VTL Mapping** | **⚠️** | **✅** | **✅ AWS CLI** | **AWS Cloud** |

## Envoy Proxy

### Übersicht

Envoy ist ein Cloud-native High-Performance Edge/Service Proxy, entwickelt für moderne Service-Mesh-Architekturen.

> **💡 API-Referenz:** Für technische Details zur Implementierung siehe `gal/providers/envoy.py:12-49` (EnvoyProvider Klassen-Docstring)

**Stärken:**
- Extrem performant (C++)
- Umfangreiche Observability
- Service Mesh Ready (Istio, Consul)
- L7 und L4 Proxy
- HTTP/2 und gRPC nativ

**Ideal für:**
- Kubernetes-Deployments
- Service Mesh Architectures
- High-Performance Requirements
- Advanced Traffic Management

### GAL-Generierung

**Output:** `envoy.yaml` (Static Resources Configuration)

**Struktur:**

```yaml
static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 10000
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                route_config:
                  virtual_hosts:
                    - routes:
                        # Service routes

  clusters:
    # Upstream services

admin:
  address:
    socket_address:
      port_value: 9901
```

### Transformationen

Envoy nutzt **Lua Filters** für Payload-Transformationen:

```yaml
http_filters:
  - name: envoy.filters.http.lua
    typed_config:
      inline_code: |
        function envoy_on_request(request_handle)
          local path = request_handle:headers():get(':path')
          if string.find(path, '/api/users') then
            local body = request_handle:body()
            -- Transform body
          end
        end
```

**Features:**
- Default-Werte setzen
- Computed Fields (UUID, Timestamp)
- Request Header/Body Manipulation

### gRPC-Support

Automatische HTTP/2-Konfiguration für gRPC-Services:

```yaml
clusters:
  - name: grpc_service_cluster
    http2_protocol_options: {}  # Aktiviert HTTP/2
```

### Request Mirroring

✅ **Native Support: request_mirror_policies**

Envoy unterstützt Request Mirroring nativ mit `request_mirror_policies`.

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    mirroring:
      enabled: true
      targets:
        - name: shadow-v2
          upstream:
            host: shadow.example.com
            port: 443
          sample_percentage: 50
```

**Generierte Envoy Config:**
```yaml
routes:
  - match: { prefix: "/api/users" }
    route:
      cluster: primary_cluster
      request_mirror_policies:
        - cluster: shadow-v2_cluster
          runtime_fraction:
            default_value:
              numerator: 50
              denominator: 100
```

**Hinweise:**
- ✅ Native request_mirror_policies
- ✅ runtime_fraction für Sample Percentage
- ✅ Multiple Mirror Targets (Array)
- ⚠️ Keine Custom Headers direkt (nutze Lua Filter)

> **Vollständige Dokumentation:** Siehe [Request Mirroring Guide](REQUEST_MIRRORING.md#1-envoy-native)

### Deployment

GAL unterstützt direktes Deployment für Envoy:

**Python API:**

```python
from gal import Manager
from gal.providers.envoy import EnvoyProvider

manager = Manager()
provider = EnvoyProvider()
config = manager.load_config("config.yaml")

# File-based deployment
provider.deploy(config, output_file="/etc/envoy/envoy.yaml")

# Mit Admin API check
provider.deploy(config,
               output_file="envoy.yaml",
               admin_url="http://localhost:9901")
```

**Docker:**

```bash
# Konfiguration generieren
python gal-cli.py generate -c config.yaml -p envoy -o envoy.yaml

# Envoy starten
docker run -d \
  -v $(pwd)/envoy.yaml:/etc/envoy/envoy.yaml \
  -p 10000:10000 \
  -p 9901:9901 \
  envoyproxy/envoy:v1.28-latest
```

**Kubernetes:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: envoy-config
data:
  envoy.yaml: |
    # Generated configuration

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: envoy-gateway
spec:
  template:
    spec:
      containers:
      - name: envoy
        image: envoyproxy/envoy:v1.28-latest
        volumeMounts:
        - name: config
          mountPath: /etc/envoy
      volumes:
      - name: config
        configMap:
          name: envoy-config
```

---

## Kong API Gateway

### Übersicht

Kong ist ein weit verbreitetes, plugin-basiertes API-Gateway mit umfangreichem Enterprise-Funktionsumfang.

> **💡 API-Referenz:** Für technische Details zur Implementierung siehe `gal/providers/kong.py:12-52` (KongProvider Klassen-Docstring)

**Stärken:**
- Großes Plugin-Ökosystem
- Developer Portal
- Enterprise-Features
- Multi-Cloud Support
- Grafische UI (Kong Manager)

**Ideal für:**
- API Management
- Microservices
- Multi-Tenant Environments
- Enterprise Use Cases

### GAL-Generierung

**Output:** `kong.yaml` (Declarative Configuration v3.0)

**Struktur:**

```yaml
_format_version: '3.0'

services:
  - name: user_service
    protocol: http
    host: user-service
    port: 8080
    routes:
      - name: user_service_route
        paths:
          - /api/users
        methods:
          - GET
          - POST
    plugins:
      - name: request-transformer
        config:
          add:
            headers:
              - x-default-role: 'user'
```

### Transformationen

Kong nutzt das **request-transformer Plugin**:

```yaml
plugins:
  - name: request-transformer
    config:
      add:
        headers:
          - x-default-status: 'active'
          - x-default-role: 'user'
```

**Limitationen:**
- Keine nativen Computed Fields
- Defaults als Headers
- Erweiterte Transformationen benötigen Custom Plugins

### gRPC-Support

```yaml
services:
  - name: grpc_service
    protocol: grpc
    host: grpc-server
    port: 9090
```

### Request Mirroring

✅ **Nginx Mirror Module (Empfohlen für OpenSource)**

Kong basiert auf **Nginx/OpenResty**, daher nutzen wir das native **ngx_http_mirror_module** für asynchrones Request Mirroring.

**GAL Config:**
```yaml
services:
  - name: user_api
    routes:
      - path_prefix: /api/users
        mirroring:
          enabled: true
          targets:
            - name: shadow-v2
              upstream:
                host: shadow.example.com
                port: 443
              sample_percentage: 100
              headers:
                X-Mirror: "true"
                X-Shadow-Version: "v2"
```

**Generierte Kong Config (Nginx Mirror Module via KONG_NGINX_PROXY_INCLUDE):**

*nginx-template.conf:*
```nginx
location /api/users {
    mirror /mirror-users;
    mirror_request_body on;
    proxy_pass http://backend-primary:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

location = /mirror-users {
    internal;
    proxy_pass https://shadow.example.com:443/api/users;
    proxy_set_header X-Mirror "true";
    proxy_set_header X-Shadow-Version "v2";
}
```

*docker-compose.yml:*
```yaml
kong:
  image: kong:3.4
  environment:
    KONG_NGINX_PROXY_INCLUDE: /usr/local/kong/custom/nginx-template.conf
  volumes:
    - ./nginx-template.conf:/usr/local/kong/custom/nginx-template.conf:ro
```

**Alternative: Kong Enterprise Plugin**
```yaml
plugins:
  - name: request-mirror  # Enterprise only
    config:
      mirror_host: https://shadow.example.com:443
      mirror_path: /api/users
      sample_rate: 1.0
      headers:
        X-Mirror: "true"
```

**Hinweise:**
- ✅ **Nginx Mirror Module** - Empfohlen für Kong OpenSource (keine Lizenz benötigt)
- ✅ **Asynchronous** - Blockiert nicht die primäre Response
- ✅ **Production-Ready** - Battle-tested Nginx mirror module
- ✅ **Custom Headers** - Beliebige Header auf Mirror-Requests
- ⚠️ **Enterprise Plugin** - Benötigt Kong Enterprise Lizenz
- ⚠️ **Sampling** - 50% Sampling via `split_clients` erfordert `http` block

> **E2E Tests:** Siehe `tests/test_kong_mirroring_e2e.py` (8 Tests, alle bestanden ✅)
>
> **Docker Setup:** Siehe `tests/docker/kong-mirroring/` für vollständige Konfiguration

### Deployment

GAL unterstützt direktes Deployment für Kong via Admin API:

**Python API:**

```python
from gal import Manager
from gal.providers.kong import KongProvider

manager = Manager()
provider = KongProvider()
config = manager.load_config("config.yaml")

# Deployment via Admin API
provider.deploy(config,
               output_file="kong.yaml",
               admin_url="http://localhost:8001")
```

**Docker:**

```bash
# Kong DB-less mit Declarative Config
docker run -d \
  -v $(pwd)/kong.yaml:/usr/local/kong/declarative/kong.yaml \
  -e KONG_DATABASE=off \
  -e KONG_DECLARATIVE_CONFIG=/usr/local/kong/declarative/kong.yaml \
  -e KONG_PROXY_ACCESS_LOG=/dev/stdout \
  -e KONG_ADMIN_ACCESS_LOG=/dev/stdout \
  -e KONG_PROXY_ERROR_LOG=/dev/stderr \
  -e KONG_ADMIN_ERROR_LOG=/dev/stderr \
  -p 8000:8000 \
  -p 8443:8443 \
  kong:3.4
```

**Kubernetes (mit Ingress Controller):**

```bash
kubectl create configmap kong-config --from-file=kong.yaml
```

---

## Apache APISIX

### Übersicht

APISIX ist ein Cloud-native, High-Performance API-Gateway mit dynamischer Konfiguration und Plugin-Verwaltung.

> **💡 API-Referenz:** Für technische Details zur Implementierung siehe `gal/providers/apisix.py:13-54` (APISIXProvider Klassen-Docstring) und `apisix.py:159-218` (_generate_lua_transformation Methode)

**Stärken:**
- Sehr hohe Performance
- Dynamic Configuration
- Low Latency
- Serverless-ready
- Active-Active Cluster

**Ideal für:**
- Cloud-Native Applications
- High-Traffic Scenarios
- Dynamic Routing
- Edge Computing

### GAL-Generierung

**Output:** `apisix.json` (JSON Configuration)

**Struktur:**

```json
{
  "routes": [
    {
      "uri": "/api/users/*",
      "name": "user_service_route",
      "service_id": "user_service",
      "methods": ["GET", "POST"]
    }
  ],
  "services": [
    {
      "id": "user_service",
      "upstream_id": "user_service_upstream",
      "plugins": {
        "serverless-pre-function": {
          "phase": "rewrite",
          "functions": ["...lua code..."]
        }
      }
    }
  ],
  "upstreams": [
    {
      "id": "user_service_upstream",
      "type": "roundrobin",
      "nodes": {
        "user-service:8080": 1
      }
    }
  ]
}
```

### Transformationen

APISIX nutzt **Serverless Pre-Function Plugin** mit Lua:

```lua
return function(conf, ctx)
  local core = require('apisix.core')
  local cjson = require('cjson.safe')
  local body = core.request.get_body()

  if body then
    local json_body = cjson.decode(body)
    if json_body then
      -- Apply defaults
      json_body.status = json_body.status or 'active'

      -- Compute fields
      if not json_body.user_id then
        json_body.user_id = 'usr_' .. core.utils.uuid()
      end

      ngx.req.set_body_data(cjson.encode(json_body))
    end
  end
end
```

**Features:**
- Vollständige Lua-Programmierung
- Volle Kontrolle über Request/Response
- Computed Fields mit UUIDs
- Timestamp-Generierung

### Request Mirroring

✅ **Native Support: proxy-mirror Plugin**

APISIX unterstützt Request Mirroring nativ mit dem `proxy-mirror` Plugin.

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    mirroring:
      enabled: true
      targets:
        - name: shadow-v2
          upstream:
            host: shadow.example.com
            port: 443
          sample_percentage: 50
```

**Generierte APISIX Config:**
```json
{
  "routes": [{
    "uri": "/api/users/*",
    "plugins": {
      "proxy-mirror": {
        "host": "https://shadow.example.com:443",
        "sample_ratio": 0.5
      }
    },
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "backend.example.com:443": 1
      }
    }
  }]
}
```

**Hinweise:**
- ✅ Native proxy-mirror Plugin
- ✅ `sample_ratio` für Sample Percentage (0.0-1.0)
- ✅ Fire-and-forget (kein Response Wait)
- ⚠️ Nur 1 Mirror Target pro Route (keine Multiple Targets)
- ⚠️ Custom Headers via zusätzliches serverless-pre-function Plugin

> **Vollständige Dokumentation:** Siehe [Request Mirroring Guide](REQUEST_MIRRORING.md#3-apache-apisix-native)

### Deployment

GAL unterstützt direktes Deployment für APISIX via Admin API:

**Python API:**

```python
from gal import Manager
from gal.providers.apisix import APISIXProvider

manager = Manager()
provider = APISIXProvider()
config = manager.load_config("config.yaml")

# Deployment via Admin API
provider.deploy(config,
               output_file="apisix.json",
               admin_url="http://localhost:9180",
               api_key="your-api-key")
```

**Docker:**

```bash
# APISIX mit Standalone Config
docker run -d \
  -v $(pwd)/apisix.json:/usr/local/apisix/conf/config.json \
  -e APISIX_STAND_ALONE=true \
  -p 9080:9080 \
  -p 9443:9443 \
  apache/apisix:3.7.0-debian
```

---

## Traefik

### Übersicht

Traefik ist ein moderner HTTP Reverse Proxy und Load Balancer für Microservices mit automatischer Service Discovery.

> **💡 API-Referenz:** Für technische Details zur Implementierung siehe `gal/providers/traefik.py:12-58` (TraefikProvider Klassen-Docstring)

**Stärken:**
- Automatische Service Discovery
- Docker/Kubernetes Integration
- Let's Encrypt Support
- Dashboard UI
- Zero-config für Docker

**Ideal für:**
- Docker Swarm
- Kubernetes
- Container-basierte Deployments
- Development Environments

### GAL-Generierung

**Output:** `traefik.yaml` (Dynamic Configuration)

**Struktur:**

```yaml
http:
  routers:
    user_service_router_0:
      rule: 'PathPrefix(`/api/users`)'
      service: user_service_service
      middlewares:
        - user_service_transform

  services:
    user_service_service:
      loadBalancer:
        servers:
          - url: 'http://user-service:8080'

  middlewares:
    user_service_transform:
      plugin:
        user_service_transformer:
          defaults:
            status: 'active'
            role: 'user'
```

### Transformationen

Traefik nutzt **Middleware Plugins**:

```yaml
middlewares:
  my_transformer:
    plugin:
      my_transformer:
        defaults:
          field: value
```

**Limitationen:**
- Plugin-Entwicklung benötigt Go
- Keine nativen Transformationen
- Fokus auf Routing/Load Balancing

### Request Mirroring

⚠️ **Limited Support: Middleware**

Traefik hat **kein natives Request Mirroring**. Custom Middleware oder externe Lösung erforderlich.

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    mirroring:
      enabled: true
      targets:
        - name: shadow-v2
          upstream:
            host: shadow.example.com
            port: 443
```

**Traefik Config (Custom Middleware erforderlich):**
```yaml
http:
  routers:
    user_api:
      rule: "PathPrefix(`/api/users`)"
      service: user_api_service
      middlewares:
        - mirror-middleware  # Custom Plugin erforderlich

  services:
    user_api_service:
      loadBalancer:
        servers:
          - url: "http://backend.example.com"

  middlewares:
    mirror-middleware:
      plugin:
        # Custom Go Plugin für Mirroring
        # Keine native Unterstützung
```

**Workarounds:**
1. **Custom Traefik Plugin (Go)**: Entwickle eigenes Mirroring-Plugin
2. **Externe Service Mesh**: Nutze Linkerd/Istio für Traffic Mirroring
3. **ForwardAuth Middleware**: Proxy zu externem Mirroring-Service
4. **Alternative Provider**: Envoy, Nginx, APISIX für native Mirroring

**Hinweise:**
- ⚠️ Kein natives Request Mirroring
- ⚠️ Custom Plugin-Entwicklung erforderlich (Go)
- ⚠️ Komplexe Integration
- ✅ Alternative: Service Mesh (Linkerd, Istio)

> **Vollständige Dokumentation:** Siehe [Request Mirroring Guide](REQUEST_MIRRORING.md#6-traefik-limited-custom-middleware)

### Deployment

GAL unterstützt direktes Deployment für Traefik (File-based):

**Python API:**

```python
from gal import Manager
from gal.providers.traefik import TraefikProvider

manager = Manager()
provider = TraefikProvider()
config = manager.load_config("config.yaml")

# File-based deployment mit API verification
provider.deploy(config,
               output_file="/etc/traefik/dynamic/gal.yaml",
               api_url="http://localhost:8080")
```

**Docker Compose:**

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    command:
      - --providers.file.filename=/etc/traefik/traefik.yaml
    volumes:
      - ./traefik.yaml:/etc/traefik/traefik.yaml
    ports:
      - "80:80"
      - "8080:8080"  # Dashboard

  backend:
    image: my-app:latest
    labels:
      - traefik.enable=true
```

**Kubernetes:**

```bash
kubectl apply -f traefik.yaml
```

---

## Nginx

### Übersicht

Nginx ist der weltweit meistgenutzte Web Server und Reverse Proxy mit extrem hoher Performance und Stabilität.

> **💡 API-Referenz:** Für technische Details zur Implementierung siehe `gal/providers/nginx.py` (NginxProvider)

**Stärken:**
- Extrem hohe Performance
- Bewährte Stabilität
- Geringer Ressourcenverbrauch
- OpenResty für Lua-Scripting
- Umfangreiches Modul-Ökosystem

**Ideal für:**
- High-Traffic Web Applications
- Static Content Delivery
- Reverse Proxy + Load Balancer
- Edge Computing
- Legacy System Integration

### GAL-Generierung

**Output:** `nginx.conf` (Nginx Configuration)

**Struktur:**

```nginx
http {
    upstream user_service_upstream {
        server user-service:8080;
    }

    server {
        listen 80;

        location /api/users {
            proxy_pass http://user_service_upstream;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

### Transformationen

Nginx nutzt **ngx_http Lua Modules** (via OpenResty):

```nginx
location /api/users {
    rewrite_by_lua_block {
        local cjson = require "cjson"
        ngx.req.read_body()
        local body = ngx.req.get_body_data()
        if body then
            local json_body = cjson.decode(body)
            json_body.status = json_body.status or "active"
            ngx.req.set_body_data(cjson.encode(json_body))
        end
    }
    proxy_pass http://backend;
}
```

**Features:**
- Defaults via Lua
- Computed Fields (UUID, Timestamp)
- Header Manipulation
- Request/Response Transformation

### gRPC-Support

```nginx
server {
    listen 443 ssl http2;

    location / {
        grpc_pass grpc://backend:50051;
    }
}
```

### Request Mirroring

✅ **Native Support: mirror Directive**

Nginx unterstützt Request Mirroring nativ mit der `mirror` Directive.

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    mirroring:
      enabled: true
      targets:
        - name: shadow-v2
          upstream:
            host: shadow.example.com
            port: 443
          sample_percentage: 50
```

**Generierte Nginx Config:**
```nginx
# Mirror backend
upstream shadow-v2_mirror {
    server shadow.example.com:443;
}

# Split Clients für Sample Percentage
split_clients "${remote_addr}${msec}" $mirror_target {
    50%     shadow-v2_mirror;
    *       "";
}

location /api/users {
    # Original request
    proxy_pass http://backend;

    # Mirror request (conditional)
    mirror /mirror_shadow-v2;
    mirror_request_body on;
}

location = /mirror_shadow-v2 {
    internal;
    if ($mirror_target = "") {
        return 204;
    }
    proxy_pass http://$mirror_target$request_uri;
    proxy_set_header X-Mirror "true";
}
```

**Hinweise:**
- ✅ Native `mirror` Directive
- ✅ `split_clients` für Sample Percentage
- ✅ `mirror_request_body on` für POST/PUT
- ✅ Custom Headers via `proxy_set_header`
- ⚠️ Kein natives Sample Percentage (workaround via split_clients)

> **Vollständige Dokumentation:** Siehe [Request Mirroring Guide](REQUEST_MIRRORING.md#2-nginx-native)

### Deployment

GAL unterstützt direktes Deployment für Nginx:

**Python API:**

```python
from gal import Manager
from gal.providers.nginx import NginxProvider

manager = Manager()
provider = NginxProvider()
config = manager.load_config("config.yaml")

# File-based deployment
provider.deploy(config, output_file="/etc/nginx/nginx.conf")
```

**Docker:**

```bash
# Konfiguration generieren
python gal-cli.py generate -c config.yaml -p nginx -o nginx.conf

# Nginx starten
docker run -d \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro \
  -p 80:80 \
  -p 443:443 \
  openresty/openresty:latest
```

---

## HAProxy

### Übersicht

HAProxy ist ein extrem schneller und zuverlässiger Load Balancer und Proxy für TCP/HTTP mit erweiterten Routing-Funktionen.

> **💡 API-Referenz:** Für technische Details zur Implementierung siehe `gal/providers/haproxy.py` (HAProxyProvider)

**Stärken:**
- Höchste Performance bei Load Balancing
- Erweiterte ACL-Funktionen
- Health Checking
- Session Persistence
- SSL/TLS Termination

**Ideal für:**
- High-Availability Setups
- TCP Load Balancing
- Complex Routing Requirements
- Legacy Protocol Support
- Mission-Critical Applications

### GAL-Generierung

**Output:** `haproxy.cfg` (HAProxy Configuration)

**Struktur:**

```haproxy
global
    maxconn 4096

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend http_front
    bind *:80
    use_backend user_backend if { path_beg /api/users }

backend user_backend
    balance roundrobin
    server srv1 user-service:8080 check
```

### Transformationen

HAProxy nutzt **HTTP Request/Response Manipulation** und **Lua Scripting**:

```haproxy
backend api_backend
    http-request set-header X-Default-Status active
    http-request set-header X-Request-ID %[uuid()]

    http-request lua.transform_request
    server srv1 backend:8080 check
```

**Features:**
- Header Manipulation
- ACL-basiertes Routing
- Sticky Sessions
- Rate Limiting via stick-tables

### Request Mirroring

✅ **Native Support: http-request mirror (HAProxy 2.4+)**

HAProxy 2.4+ unterstützt Request Mirroring nativ mit der `http-request mirror` Directive.

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    mirroring:
      enabled: true
      targets:
        - name: shadow-v2
          upstream:
            host: shadow.example.com
            port: 443
          sample_percentage: 50
```

**Generierte HAProxy Config (2.4+):**
```haproxy
backend shadow-v2_mirror
    server mirror1 shadow.example.com:443 check

frontend http_front
    bind *:80
    default_backend user_backend

backend user_backend
    # Sample Percentage via ACL
    acl mirror_sample rand(100) lt 50
    http-request mirror shadow-v2_mirror if mirror_sample

    # Custom Headers für Mirror
    http-request set-header X-Mirror true if mirror_sample

    server srv1 backend.example.com:443 check
```

**HAProxy 2.3 oder älter (Lua Script Workaround):**
```haproxy
# global section
global
    lua-load /etc/haproxy/lua/mirror.lua

backend user_backend
    http-request lua.mirror_request
    server srv1 backend.example.com:443
```

**Hinweise:**
- ✅ Native `http-request mirror` (HAProxy 2.4+)
- ✅ Sample Percentage via `rand(100) lt 50` ACL
- ✅ Custom Headers via `http-request set-header`
- ⚠️ HAProxy 2.3 oder älter: Lua Script erforderlich
- ⚠️ Fire-and-forget (kein Response Wait)

> **Vollständige Dokumentation:** Siehe [Request Mirroring Guide](REQUEST_MIRRORING.md#4-haproxy-native-haproxy-24)

### Deployment

GAL unterstützt direktes Deployment für HAProxy:

**Python API:**

```python
from gal import Manager
from gal.providers.haproxy import HAProxyProvider

manager = Manager()
provider = HAProxyProvider()
config = manager.load_config("config.yaml")

# File-based deployment
provider.deploy(config, output_file="/etc/haproxy/haproxy.cfg")
```

**Docker:**

```bash
# Konfiguration generieren
python gal-cli.py generate -c config.yaml -p haproxy -o haproxy.cfg

# HAProxy starten
docker run -d \
  -v $(pwd)/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro \
  -p 80:80 \
  -p 8404:8404 \
  haproxy:2.9-alpine
```

---

## Azure API Management (Cloud Provider)

### Übersicht

Azure API Management (APIM) ist Microsofts vollständig verwalteter Cloud-Native API Gateway Service für Azure-Anwendungen.

> **💡 API-Referenz:** Für technische Details zur Implementierung siehe `gal/providers/azure_apim.py:24-64` (AzureAPIMProvider Klassen-Docstring)

**Stärken:**
- Fully Managed Service (keine Server-Wartung)
- Native Azure Integration (Azure AD, Key Vault, App Services)
- Developer Portal mit Self-Service
- Subscription Keys Management
- OpenAPI 3.0 Import/Export
- Multi-Region Deployment (Premium SKU)
- Application Insights Integration

**Ideal für:**
- Azure Cloud-Native Applications
- Enterprise API Management
- Hybrid Cloud (On-Premises + Azure)
- API Monetization mit Subscription Tiers
- Developer Portals mit API Documentation

### GAL-Generierung

**Output:** `azure-apim-template.json` (ARM Template) + `openapi.json` (OpenAPI 3.0)

**Struktur (ARM Template):**

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "resources": [
    {
      "type": "Microsoft.ApiManagement/service",
      "name": "my-apim-service",
      "sku": {
        "name": "Developer"
      }
    },
    {
      "type": "Microsoft.ApiManagement/service/apis",
      "name": "user_api",
      "properties": {
        "path": "api",
        "protocols": ["https"]
      }
    },
    {
      "type": "Microsoft.ApiManagement/service/products",
      "name": "UserAPI-Product",
      "properties": {
        "subscriptionRequired": true
      }
    }
  ]
}
```

### Transformationen

Azure APIM nutzt **Policy XML** für Transformationen:

```xml
<policies>
    <inbound>
        <base />
        <rate-limit calls="6000" renewal-period="60" />
        <validate-jwt header-name="Authorization">
            <openid-config url="https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration" />
        </validate-jwt>
        <set-header name="X-Custom-Header" exists-action="override">
            <value>custom-value</value>
        </set-header>
    </inbound>
    <outbound>
        <base />
    </outbound>
</policies>
```

**Features:**
- Rate Limiting (calls + renewal-period)
- Azure AD JWT Validation
- Subscription Key Validation
- Header Manipulation (request + response)
- Backend URL Routing
- Caching (cache-lookup, cache-store)

**Authentifizierung:**
- Subscription Keys (API Key Management)
- Azure AD OAuth2/OIDC (validate-jwt policy)
- Custom Headers

### Azure-spezifische Features

**Products & Subscriptions:**
```yaml
azure_apim:
  product_name: "Premium-Tier"
  product_subscription_required: true
  rate_limit_calls: 120000  # 2000 req/min
```

**Developer Portal:**
- Automatisch verfügbar unter `https://<apim-service>.developer.azure-api.net`
- API-Dokumentation aus OpenAPI
- Self-Service Subscription Management
- Interactive API Testing

**SKU-Optionen:**
- Developer: Development/Testing (no SLA)
- Consumption: Serverless, pay-per-request
- Basic: Small production APIs
- Standard: Production APIs mit VNet
- Premium: Enterprise (Multi-Region, 99.99% SLA)

### Request Mirroring

✅ **Native Support: send-request Policy**

Azure APIM unterstützt Request Mirroring nativ über die `send-request` Policy.

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

**Generierte APIM Policy XML:**
```xml
<policies>
  <inbound>
    <base />
    <!-- Original request processing -->
  </inbound>

  <backend>
    <base />
  </backend>

  <outbound>
    <base />
    <!-- Request Mirroring (fire-and-forget) -->
    <choose>
      <when condition="@(new Random().Next(100) < 50)">
        <send-request mode="new" response-variable-name="mirrorResponse" timeout="5" ignore-error="true">
          <set-url>https://shadow.example.com/api/users</set-url>
          <set-method>@(context.Request.Method)</set-method>
          <set-header name="X-Mirror" exists-action="override">
            <value>true</value>
          </set-header>
          <set-header name="X-Shadow-Version" exists-action="override">
            <value>v2</value>
          </set-header>
          <set-body>@(context.Request.Body.As<string>(preserveContent: true))</set-body>
        </send-request>
      </when>
    </choose>
  </outbound>

  <on-error>
    <base />
  </on-error>
</policies>
```

**Deployment:**
```bash
# GAL Config → ARM Template mit Mirroring Policy
gal generate -c config.yaml -p azure_apim -o azure-apim-template.json

# ARM Template deployen
az deployment group create \
  --resource-group gal-rg \
  --template-file azure-apim-template.json

# Policy validieren
az apim api operation policy show \
  --resource-group gal-rg \
  --service-name my-apim-service \
  --api-id user_api \
  --operation-id getUsers
```

**Hinweise:**
- ✅ Native `send-request` Policy (keine externe Funktion erforderlich)
- ✅ Sample Percentage über `@(new Random().Next(100) < 50)` Condition
- ✅ Custom Headers über `set-header` Tags
- ✅ Fire-and-Forget: `ignore-error="true"` + `response-variable-name` (nicht verwendet)
- ✅ Timeout-Konfiguration (1-30s)
- ⚠️ Kosten pro Mirror Request (APIM Requests werden gezählt)
- ⚠️ Latenz durch outbound Policy Execution

### Deployment

GAL unterstützt Azure CLI Deployment:

**Python API:**

```python
from gal import Manager
from gal.providers.azure_apim import AzureAPIMProvider

manager = Manager()
provider = AzureAPIMProvider()
config = manager.load_config("config.yaml")

# ARM Template generieren
arm_template = provider.generate(config)

# OpenAPI Spec generieren
openapi_spec = provider.generate_openapi(config)
```

**Azure CLI:**

```bash
# GAL Config → ARM Template
gal generate -c config.yaml -p azure_apim -o azure-apim-template.json

# Resource Group erstellen
az group create --name gal-rg --location westeurope

# ARM Template deployen
az deployment group create \
  --resource-group gal-rg \
  --template-file azure-apim-template.json
```

**Terraform:**

```hcl
resource "azurerm_template_deployment" "gal_apim" {
  name                = "gal-apim-deployment"
  resource_group_name = azurerm_resource_group.gal.name
  template_body       = file("azure-apim-template.json")
  deployment_mode     = "Incremental"
}
```

**CI/CD (GitHub Actions):**

```yaml
- name: Deploy to Azure APIM
  run: |
    gal generate -c azure-apim.yaml -p azure_apim -o template.json
    az deployment group create \
      --resource-group ${{ secrets.RESOURCE_GROUP }} \
      --template-file template.json
```

### Vergleich: Azure APIM vs Self-Hosted

| Feature | Azure APIM | Self-Hosted (Envoy/Kong/etc.) |
|---------|-----------|-------------------------------|
| **Wartung** | Fully Managed | Manuell |
| **Skalierung** | Automatisch | Manuell |
| **Updates** | Automatisch | Manuell |
| **Kosten** | Pay-per-SKU | Infrastructure Kosten |
| **Developer Portal** | Built-in | Custom |
| **Azure Integration** | Native | Manual |
| **Multi-Cloud** | Azure-only | ✅ |
| **Vendor Lock-in** | Azure | Portabel |

**Wann Azure APIM verwenden?**
- ✅ Azure Cloud-Native Apps
- ✅ Enterprise API Management benötigt
- ✅ Developer Portal erforderlich
- ✅ Fully Managed bevorzugt
- ✅ Azure AD Integration

**Wann Self-Hosted verwenden?**
- ✅ Multi-Cloud (AWS, GCP, Azure)
- ✅ Kubernetes-Native
- ✅ Volle Kontrolle benötigt
- ✅ Cost-Optimierung
- ✅ On-Premises

---

## GCP API Gateway

### Übersicht

GCP API Gateway ist ein vollständig verwalteter Cloud-native API Gateway von Google Cloud Platform.

> **💡 API-Referenz:** Für technische Details zur Implementierung siehe `gal/providers/gcp_apigateway.py:41-58` (GCPAPIGatewayProvider Klassen-Docstring)

**Stärken:**
- Vollständig verwaltet (Serverless)
- Native GCP-Integration (Cloud Run, Cloud Functions, IAM)
- OpenAPI 2.0 (Swagger) basiert
- Automatische Skalierung
- Integriertes Monitoring (Cloud Logging, Monitoring, Trace)

**Ideal für:**
- Cloud-native Applikationen auf GCP
- Serverless Backends (Cloud Run, Cloud Functions)
- Google Sign-In / Firebase Auth Integration
- Multi-Region Global Deployments

### GAL-Generierung

**Output:** `openapi.yaml` (OpenAPI 2.0 / Swagger Specification)

**Struktur:**

```yaml
swagger: "2.0"
info:
  title: "My API"
  version: "1.0.0"

schemes:
  - https

# Backend Configuration
x-google-backend:
  address: "https://backend.run.app"
  deadline: 30.0
  path_translation: APPEND_PATH_TO_ADDRESS

# JWT Authentication
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
  /api/users:
    get:
      summary: "Get users"
      operationId: "getUsers"
      responses:
        200:
          description: "Success"
    options:
      # CORS Preflight
      summary: "CORS preflight"
      responses:
        200:
          description: "CORS headers"
```

### Transformationen

GCP API Gateway hat **keine native Transformation-Engine** wie Envoy/Kong.

**Alternativen:**
- **Backend Transformation:** Implementierung in Cloud Run/Cloud Functions Backend
- **Cloud Endpoints ESP:** Erweiterte Transformation-Features
- **Apigee:** Enterprise API Management mit umfangreichen Transformationen

### gRPC-Support

⚠️ **gRPC-HTTP Transcoding:**
- GCP API Gateway unterstützt gRPC-JSON Transcoding via Cloud Endpoints
- GAL generiert OpenAPI 2.0 Specs, nicht direkt gRPC-fähig
- Für gRPC: Verwende Cloud Endpoints direkt oder Apigee

### Authentifizierung

**Unterstützte Methoden:**
- ✅ **JWT Authentication:** Native Integration (x-google-issuer, x-google-jwks_uri)
- ✅ **Google Sign-In:** Automatisch unterstützt
- ✅ **Firebase Authentication:** Direkte Integration
- ✅ **Custom JWT Issuer:** Auth0, Okta, Keycloak, etc.
- ⚠️ **API Keys:** Begrenzte Unterstützung (OAuth2/JWT empfohlen)
- ❌ **Basic Auth:** Nicht nativ unterstützt (Backend-Implementierung)

### Rate Limiting

❌ **Kein natives Gateway-Level Rate Limiting**

**Alternativen:**
- Cloud Endpoints Quotas (x-google-management Extension)
- Backend Rate Limiting
- Apigee für Enterprise Rate Limiting
- Cloud Armor für DDoS Protection

### Circuit Breaker

❌ **Kein nativer Circuit Breaker**

**Alternativen:**
- Backend Circuit Breaker (z.B. Hystrix, Resilience4j)
- Cloud Run automatische Skalierung bei Überlastung

### Health Checks

⚠️ **Backend Health Checks:**
- Cloud Run: Automatische Health Checks
- Cloud Functions: Built-in Health Monitoring
- Load Balancer: Konfigurierbare Health Checks

### Request Mirroring

⚠️ **Workaround: Cloud Functions**

GCP API Gateway unterstützt Request Mirroring nicht nativ. GAL konfiguriert einen **Cloud Functions Workaround** über `mirroring_cloud_function_url`.

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
          mirroring_cloud_function_url: "https://us-central1-my-project.cloudfunctions.net/mirror-function"
          targets:
            - name: shadow-backend
              upstream:
                host: shadow.example.com
                port: 443
              sample_percentage: 50
              headers:
                X-Mirror: "true"
                X-Shadow-Version: "v2"
```

**Cloud Function Implementation:**
```javascript
// Cloud Functions HTTP Trigger
exports.mirrorRequest = async (req, res) => {
  const axios = require('axios');

  // Mirror request to shadow backend
  const shadowUrl = process.env.SHADOW_BACKEND_URL;
  const sampleRate = parseFloat(process.env.SAMPLE_PERCENTAGE || '100');

  // Sample percentage logic
  if (Math.random() * 100 < sampleRate) {
    try {
      await axios({
        method: req.method,
        url: `${shadowUrl}${req.path}`,
        headers: {
          ...req.headers,
          'X-Mirror': 'true',
          'X-Shadow-Version': 'v2'
        },
        data: req.body,
        timeout: 5000
      });
    } catch (error) {
      console.error('Mirror failed:', error);
      // Ignore errors (fire-and-forget)
    }
  }

  res.status(200).send('OK');
};
```

**Deployment:**
```bash
# Deploy Cloud Function
gcloud functions deploy mirror-function \
  --runtime nodejs18 \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars SHADOW_BACKEND_URL=https://shadow.example.com,SAMPLE_PERCENTAGE=50

# Get Function URL
gcloud functions describe mirror-function --format="value(httpsTrigger.url)"
```

**Hinweise:**
- ⚠️ Erfordert externe Cloud Function
- ⚠️ Zusätzliche Kosten für Function Invocations
- ⚠️ Latenz durch Function Trigger
- ✅ Vollständige Kontrolle über Mirroring-Logik
- ✅ Support für Sample Percentage, Custom Headers

### Deployment-Befehle

**OpenAPI Spec generieren:**
```bash
gal generate -c config.yaml -p gcp_apigateway > openapi.yaml
```

**GCP Deployment:**
```bash
# API erstellen
gcloud api-gateway apis create my-api \
  --project=my-gcp-project

# API Config deployen
gcloud api-gateway api-configs create my-api-config \
  --api=my-api \
  --openapi-spec=openapi.yaml \
  --project=my-gcp-project

# Gateway erstellen
gcloud api-gateway gateways create my-gateway \
  --api=my-api \
  --api-config=my-api-config \
  --location=us-central1 \
  --project=my-gcp-project

# Gateway URL abrufen
gcloud api-gateway gateways describe my-gateway \
  --location=us-central1 \
  --project=my-gcp-project \
  --format="value(defaultHostname)"
```

**Multi-Region Deployment:**
```bash
# Gateway in mehreren Regionen deployen
for region in us-central1 europe-west1 asia-east1; do
  gcloud api-gateway gateways create my-gateway-${region} \
    --api=my-api \
    --api-config=my-api-config \
    --location=${region} \
    --project=my-gcp-project
done
```

### Monitoring & Observability

**Cloud Logging:**
- Automatische Request/Response Logs
- Strukturierte JSON Logs
- Filter nach Status Code, Latency, Endpoint

**Cloud Monitoring:**
- Request Rate, Error Rate, Latency (P50, P95, P99)
- Custom Dashboards
- Alerting Policies

**Cloud Trace:**
- Distributed Tracing
- End-to-End Request Tracking
- Integration mit Cloud Run/Cloud Functions

**Beispiel: Logs abfragen:**
```bash
# Fehler-Logs anzeigen
gcloud logging read "resource.type=api AND httpRequest.status>=400" \
  --project=my-gcp-project \
  --limit=50

# Latency-Analyse
gcloud logging read "resource.type=api AND httpRequest.latency>1s" \
  --project=my-gcp-project \
  --format=json
```

### Best Practices

1. **Verwende JWT statt API Keys** für Production
2. **Implementiere Rate Limiting im Backend** (kein Gateway-Level RL)
3. **Nutze Cloud Monitoring** für Alerting
4. **Multi-Region Deployments** für globale APIs
5. **Cloud Armor** für DDoS Protection
6. **Service Account Auth** für Backend-zu-Backend Communication
7. **OpenAPI 2.0** - GCP unterstützt nur Swagger, kein OpenAPI 3.0

### Limitierungen

- ❌ Nur OpenAPI 2.0 (Swagger), kein OpenAPI 3.0
- ❌ Keine nativen Transformationen
- ❌ Kein Gateway-Level Rate Limiting
- ❌ Kein Circuit Breaker
- ⚠️ gRPC nur via Cloud Endpoints
- ✅ Hervorragend für serverless/cloud-native Workloads

---

## AWS API Gateway (Cloud Provider)

### Übersicht

AWS API Gateway ist ein vollständig verwalteter Service von Amazon Web Services für REST APIs, HTTP APIs und WebSocket APIs.

> **💡 API-Referenz:** Für technische Details zur Implementierung siehe `gal/providers/aws_apigateway.py:12-68` (AWSAPIGatewayProvider Klassen-Docstring)

**Stärken:**
- Vollständig verwaltet (AWS-managed)
- Serverless-Integration (AWS Lambda)
- OpenAPI 3.0 basiert
- Automatische Skalierung
- Native AWS-Services-Integration (Cognito, IAM, CloudWatch, WAF)
- Multi-Region mit CloudFront (EDGE Endpoints)

**Ideal für:**
- AWS-basierte Microservices
- Serverless Architectures (Lambda)
- Pay-per-Use-Modelle
- Multi-Region Deployments
- Enterprise APIs mit Cognito/IAM

### GAL-Generierung

**Output:** `api.json` (OpenAPI 3.0 with x-amazon-apigateway extensions)

**Struktur:**

```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "My API",
    "version": "1.0.0"
  },
  "paths": {
    "/users": {
      "get": {
        "x-amazon-apigateway-integration": {
          "type": "http_proxy",
          "httpMethod": "GET",
          "uri": "https://backend.example.com/users"
        }
      }
    }
  }
}
```

### Transformationen

AWS API Gateway nutzt **VTL (Velocity Template Language)** für Request/Response Transformationen:

```json
{
  "x-amazon-apigateway-integration": {
    "type": "aws_proxy",
    "uri": "arn:aws:apigateway:region:lambda:path/...",
    "requestTemplates": {
      "application/json": "{\"user_id\": \"$input.params('id')\"}"
    },
    "responses": {
      "default": {
        "statusCode": "200",
        "responseTemplates": {
          "application/json": "{\"result\": $input.json('$.body')}"
        }
      }
    }
  }
}
```

**Features:**
- VTL-basierte Request/Response Mapping
- Lambda Proxy Integration (automatisches Mapping)
- HTTP Proxy Integration
- Mock Integration für Testing

### gRPC-Support

⚠️ **Eingeschränkt:** gRPC wird nicht nativ unterstützt.

**Alternativen:**
- REST-to-gRPC Translation via Lambda
- HTTP/2 for REST APIs (aber kein natives gRPC)
- AWS App Mesh für gRPC Service Mesh

### Authentifizierung

AWS API Gateway unterstützt **vier Authentication-Mechanismen**:

**1. API Keys (Subscription-basiert):**
```json
{
  "components": {
    "securitySchemes": {
      "api_key": {
        "type": "apiKey",
        "name": "x-api-key",
        "in": "header"
      }
    }
  }
}
```

**2. Lambda Authorizer (Custom JWT):**
```json
{
  "x-amazon-apigateway-authorizer": {
    "type": "token",
    "authorizerUri": "arn:aws:apigateway:...:lambda:...",
    "authorizerResultTtlInSeconds": 300
  }
}
```

**3. Cognito User Pools (OAuth2/OIDC):**
```json
{
  "x-amazon-apigateway-authorizer": {
    "type": "cognito_user_pools",
    "providerARNs": [
      "arn:aws:cognito-idp:us-east-1:...:userpool/..."
    ]
  }
}
```

**4. IAM Authorization (AWS Signature v4):**
- Für Service-to-Service Communication
- AWS Credentials (Access Key + Secret Key)
- Temporary Credentials via STS

### Rate Limiting

AWS API Gateway implementiert Rate Limiting via **Usage Plans**:

```bash
# Usage Plan erstellen
aws apigateway create-usage-plan \
  --name "BasicPlan" \
  --throttle burstLimit=1000,rateLimit=500 \
  --quota limit=100000,period=MONTH

# API Key zu Usage Plan hinzufügen
aws apigateway create-usage-plan-key \
  --usage-plan-id <plan-id> \
  --key-id <key-id> \
  --key-type API_KEY
```

**Features:**
- **Throttling:** Requests per second (Rate Limit + Burst Limit)
- **Quotas:** Daily/Weekly/Monthly Limits
- **Multi-Tier:** Free/Basic/Premium Plans
- **Per API Key:** Individuelle Limits pro Subscription

**Hinweis:** Rate Limiting wird NICHT in OpenAPI konfiguriert, sondern via AWS CLI/Console!

### Circuit Breaker

❌ **Nicht nativ unterstützt.**

**Workarounds:**
- Lambda Function mit Circuit Breaker Pattern
- DynamoDB für Circuit Breaker State
- AWS Step Functions für komplexe Retry-Logic

### Health Checks

⚠️ **Indirekt via Backend Health Checks:**

- **Lambda:** Health Check via CloudWatch Alarms
- **HTTP Backend:** Health Check via Route 53 Health Checks
- **ECS/EKS:** Target Group Health Checks

### Request Mirroring

⚠️ **Workaround: Lambda@Edge**

AWS API Gateway unterstützt Request Mirroring nicht nativ. GAL konfiguriert einen **Lambda@Edge Workaround** über `mirroring_lambda_edge_arn`.

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
              headers:
                X-Mirror: "true"
                X-Shadow-Version: "v2"
```

**Lambda@Edge Function Implementation:**
```javascript
// Lambda@Edge Viewer Request Handler
exports.handler = async (event) => {
  const request = event.Records[0].cf.request;
  const https = require('https');

  // Sample percentage logic
  const sampleRate = parseInt(process.env.SAMPLE_PERCENTAGE || '100');
  if (Math.random() * 100 < sampleRate) {
    // Mirror request to shadow backend (fire-and-forget)
    const mirrorRequest = {
      hostname: process.env.SHADOW_HOST,
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
# Lambda Function erstellen (us-east-1 for CloudFront/Lambda@Edge)
aws lambda create-function \
  --region us-east-1 \
  --function-name mirror-function \
  --runtime nodejs18.x \
  --role arn:aws:iam::123456789012:role/lambda-edge-role \
  --handler index.handler \
  --zip-file fileb://function.zip \
  --environment Variables="{SHADOW_HOST=shadow.example.com,SAMPLE_PERCENTAGE=50}"

# Lambda@Edge Version publizieren
aws lambda publish-version \
  --region us-east-1 \
  --function-name mirror-function

# CloudFront Distribution mit Lambda@Edge verknüpfen
aws cloudfront update-distribution \
  --id DISTRIBUTION_ID \
  --distribution-config file://distribution-config.json
```

**Hinweise:**
- ⚠️ Erfordert Lambda@Edge (nur us-east-1 Region)
- ⚠️ Zusätzliche Kosten für Lambda Invocations
- ⚠️ 29s Timeout Limit (Lambda@Edge: 5s für Viewer Request)
- ⚠️ CloudFront Distribution erforderlich
- ✅ Vollständige Kontrolle über Mirroring-Logik
- ✅ Support für Sample Percentage, Custom Headers

### Deployment-Befehle

```bash
# OpenAPI generieren
gal generate -c config.yaml -p aws_apigateway -o api.json

# API erstellen
API_ID=$(aws apigateway import-rest-api \
  --body file://api.json \
  --query 'id' --output text)

# API Key erstellen (für API Key Authentication)
aws apigateway create-api-key \
  --name "MyAppKey" \
  --enabled

# Usage Plan erstellen
aws apigateway create-usage-plan \
  --name "BasicPlan" \
  --throttle burstLimit=1000,rateLimit=500 \
  --api-stages apiId=$API_ID,stage=prod

# Deployment erstellen
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod

# API URL anzeigen
echo "https://${API_ID}.execute-api.us-east-1.amazonaws.com/prod"
```

### Monitoring & Observability

**CloudWatch Logs:**
```bash
# CloudWatch Logs aktivieren
aws apigateway update-stage \
  --rest-api-id $API_ID \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/accessLogSettings/destinationArn,value=arn:aws:logs:... \
    op=replace,path=/accessLogSettings/format,value='$context.requestId'
```

**CloudWatch Metrics:**
- **Count:** Anzahl API Requests
- **4XXError:** Client Errors (401, 403, 429)
- **5XXError:** Server Errors (500, 502, 503)
- **Latency:** Gesamte Response-Zeit
- **IntegrationLatency:** Backend-Response-Zeit

**X-Ray Tracing:**
```bash
# X-Ray aktivieren
aws apigateway update-stage \
  --rest-api-id $API_ID \
  --stage-name prod \
  --patch-operations op=replace,path=/tracingEnabled,value=true
```

### Best Practices

**1. API-Design:**
- ✅ Verwende REST-konforme Resource-Namen (`/users`, `/products`)
- ✅ Versioniere deine API (`/v1/users`, `/v2/users`)
- ✅ Implementiere Health Check Endpoints (`/health`)

**2. Security:**
- ✅ HTTPS Only (Standard)
- ✅ API Keys für öffentliche APIs
- ✅ Cognito/Lambda Authorizer für User-APIs
- ✅ IAM Authorization für Service-to-Service
- ✅ AWS WAF für DDoS-Schutz

**3. Cost Optimization:**
- ✅ Verwende HTTP APIs statt REST APIs (günstiger: $1.00/Million vs $3.50/Million)
- ✅ Nutze Caching für Read-Heavy APIs
- ✅ Implementiere CloudFront für EDGE Endpoints (reduziert Data Transfer Costs)

**4. Performance:**
- ✅ Setze Integration Timeout auf 29000ms (Maximum)
- ✅ Nutze Lambda Provisioned Concurrency für Cold Start Reduction
- ✅ Aktiviere Response Caching (TTL: 300-3600s)

**5. Monitoring:**
- ✅ Aktiviere CloudWatch Logs (Access & Execution Logs)
- ✅ Aktiviere X-Ray Tracing für Distributed Tracing
- ✅ Erstelle CloudWatch Alarms für 5XXError Rate

### Limitierungen

- ⚠️ **29 Sekunden Timeout:** Integration Timeout max 29000ms (Hard Limit!)
- ⚠️ **Payload Size:** Max 10MB Request/Response Payload
- ⚠️ **Rate Limiting:** Nur via Usage Plans (nicht in OpenAPI)
- ❌ **gRPC:** Kein natives gRPC-Support
- ❌ **WebSocket:** Nur via separate WebSocket API (nicht REST API)
- ❌ **Circuit Breaker:** Nicht nativ unterstützt
- ⚠️ **Cold Start:** Lambda Integration hat Cold Start Latenz

**Workarounds:**
- **Long-Running Tasks:** SQS + Lambda + Polling Pattern
- **Large Payloads:** S3 Pre-Signed URLs
- **gRPC:** REST-to-gRPC Translation via Lambda

---

## Provider-Vergleich

### Performance

| Provider | Requests/sec | Latency (p50) | Latency (p99) | Deployment |
|----------|--------------|---------------|---------------|------------|
| Nginx | ~120k | <1ms | <3ms | Self-Hosted |
| Envoy | ~100k | <1ms | <5ms | Self-Hosted |
| HAProxy | ~95k | <1ms | <4ms | Self-Hosted |
| APISIX | ~80k | <1ms | <6ms | Self-Hosted |
| Kong | ~50k | 2ms | 15ms | Self-Hosted |
| Traefik | ~40k | 3ms | 20ms | Self-Hosted |
| Azure APIM | Varies* | Varies* | Varies* | Azure Cloud |
| GCP API Gateway | Varies* | Varies* | Varies* | Google Cloud |
| AWS API Gateway | Varies* | Varies* | Varies* | AWS Cloud |

*Benchmark-Werte sind Richtwerte und variieren je nach Setup. Azure APIM Performance hängt von SKU ab (Developer < Basic < Standard < Premium). GCP/AWS API Gateway Performance variiert je nach Region, Endpoint-Typ (REGIONAL/EDGE) und Backend-Typ.*

### Transformations-Vergleich

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy | Azure APIM | GCP API Gateway | AWS API Gateway |
|---------|-------|------|--------|---------|-------|---------|------------|-----------------|-----------------|
| Defaults | ✅ Lua | ✅ Headers | ✅ Lua | ⚠️ Plugins | ✅ ngx | ⚠️ Limited | ✅ Policy XML | ❌ Backend | ⚠️ VTL |
| Computed Fields | ✅ Lua | ❌ | ✅ Lua | ❌ | ✅ ngx | ❌ | ⚠️ Limited | ❌ Backend | ⚠️ VTL |
| UUID Generation | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ⚠️ Custom | ❌ Backend | ⚠️ Lambda |
| Timestamp | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ⚠️ Custom | ❌ Backend | ⚠️ Lambda |
| Validation | ⚠️ Limited | ⚠️ Limited | ✅ Full | ❌ | ⚠️ Limited | ⚠️ Limited | ✅ Policy | ⚠️ OpenAPI | ⚠️ OpenAPI |
| Rate Limiting | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Built-in | ❌ Backend | ✅ Usage Plans |
| JWT Auth | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ Azure AD | ✅ Google JWT | ✅ Cognito/Lambda |
| Header Manipulation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Policy | ⚠️ Limited | ✅ Mapping |

### Request Mirroring/Shadowing-Vergleich

| Provider | Request Mirroring | Implementation | Notes |
|----------|-------------------|----------------|-------|
| Envoy | ✅ Native | request_mirror_policies | Full support, sample percentage, custom headers |
| Nginx | ✅ Native | mirror directive | Full support, sample percentage, multiple targets |
| APISIX | ✅ Native | proxy-mirror plugin | Full support, sample percentage, sample_ratio |
| HAProxy | ✅ Native (2.4+) | http-request mirror | Requires HAProxy 2.4+, Lua scripts for older versions |
| Kong | ⚠️ Plugin/Enterprise | request-transformer or Enterprise plugin | `kong_mirroring_enable_enterprise: true` for full support |
| Traefik | ⚠️ Limited | Middleware | Custom solution required, limited native support |
| Azure APIM | ✅ Native | send-request policy | Full support, cloud-based mirroring |
| AWS API Gateway | ⚠️ Workaround | Lambda@Edge | Requires `mirroring_lambda_edge_arn` config |
| GCP API Gateway | ⚠️ Workaround | Cloud Functions | Requires `mirroring_cloud_function_url` config |

**Legend:**
- ✅ Native: Built-in gateway feature
- ⚠️ Plugin/Enterprise: Requires plugin or Enterprise version
- ⚠️ Limited: Partial support or custom solution required
- ⚠️ Workaround: Requires external service (Lambda, Cloud Functions)

**Key Features:**
- **Sample Percentage**: All native providers support 0-100% traffic sampling
- **Custom Headers**: Add `X-Mirror`, `X-Shadow-Version` to mirrored requests
- **Multiple Targets**: Mirror to 2+ shadow backends simultaneously
- **Cloud Workarounds**: AWS/GCP use serverless functions for mirroring

### Use Case Matrix

| Use Case | Empfohlen | Warum |
|----------|-----------|-------|
| Kubernetes Service Mesh | Envoy | Native Integration |
| API Management Platform | Kong, Azure APIM | Enterprise Features |
| High-Traffic Edge | APISIX | Performance |
| Docker Development | Traefik | Auto-Discovery |
| gRPC Heavy | Envoy, APISIX | Native HTTP/2 |
| Multi-Cloud | Kong, APISIX | Provider-agnostic |
| **Azure Cloud-Native** | **Azure APIM** | **Fully Managed, Azure AD** |
| **GCP Cloud-Native** | **GCP API Gateway** | **Serverless, Cloud Run/Functions** |
| **AWS Cloud-Native** | **AWS API Gateway** | **Lambda, Cognito, CloudWatch** |
| **Developer Portal** | **Azure APIM, Kong** | **Built-in Portal** |
| **Hybrid Cloud** | **Azure APIM, Kong** | **On-Prem + Cloud** |
| **Serverless Backends** | **GCP API Gateway, AWS API Gateway** | **Cloud Run/Functions, Lambda** |
| **Pay-per-Request** | **AWS API Gateway** | **No upfront costs, scale to zero** |

## Provider-Wechsel

### Von Kong zu Envoy

```bash
# 1. GAL-Config erstellen (basierend auf Kong-Setup)
# config.yaml

# 2. Für Envoy generieren
python gal-cli.py generate -c config.yaml -p envoy -o envoy.yaml

# 3. Parallel testen
# Kong und Envoy parallel mit Traffic Mirror

# 4. Schrittweise Migration
# Traffic von Kong zu Envoy verschieben
```

### Best Practices für Migration

1. **Parallel Testing:** Beide Gateways mit gleichem Traffic
2. **Feature Parity:** Prüfe ob alle Features unterstützt sind
3. **Gradual Rollout:** Schrittweise Traffic-Verschiebung
4. **Monitoring:** Intensive Überwachung während Migration
5. **Rollback Plan:** Schneller Rollback zu altem Provider

## Troubleshooting

### Envoy: "No healthy upstream"

```bash
# Prüfe Admin Interface
curl http://localhost:9901/clusters

# Prüfe Service-Erreichbarkeit
kubectl get pods -l app=backend-service
```

### Kong: "No routes matched"

```bash
# Validiere Declarative Config
kong config parse kong.yaml

# Prüfe Logs
docker logs kong-container
```

### APISIX: "failed to fetch api"

```bash
# Validiere JSON
python -m json.tool apisix.json

# Prüfe etcd (wenn nicht standalone)
curl http://localhost:2379/health
```

### Traefik: "Service not found"

```bash
# Dashboard prüfen
open http://localhost:8080/dashboard/

# Config validieren
traefik healthcheck --configFile=traefik.yaml
```

## Python API-Referenz

Alle Provider-Implementierungen enthalten umfassende Google-style Docstrings mit detaillierten Erklärungen, Beispielen und Codebeispielen.

### Klassen-Dokumentation

| Modul | Zeilen | Inhalt |
|-------|--------|--------|
| `gal/provider.py:13-127` | Provider ABC | Basis-Interface für alle Provider |
| `gal/providers/envoy.py:12-209` | EnvoyProvider | Envoy Static Config Generator |
| `gal/providers/kong.py:12-146` | KongProvider | Kong Declarative Config Generator |
| `gal/providers/apisix.py:13-219` | APISIXProvider | APISIX JSON Config Generator |
| `gal/providers/traefik.py:12-155` | TraefikProvider | Traefik Dynamic Config Generator |
| `gal/providers/nginx.py` | NginxProvider | Nginx Config Generator |
| `gal/providers/haproxy.py` | HAProxyProvider | HAProxy Config Generator |
| `gal/providers/azure_apim.py:24-64` | AzureAPIMProvider | Azure APIM ARM Template Generator |
| `gal/providers/gcp_apigateway.py:41-58` | GCPAPIGatewayProvider | GCP API Gateway OpenAPI 2.0 Generator |

### Methoden-Dokumentation

Jeder Provider implementiert:

- **`name() -> str`**: Eindeutiger Provider-Name
- **`validate(config: Config) -> bool`**: Provider-spezifische Validierung
- **`generate(config: Config) -> str`**: Config-zu-Output Transformation

**Beispiel:** `gal/providers/envoy.py:86-112` zeigt die vollständige `generate()` Methode mit allen Parametern und Rückgabewerten.

### Konfigurations-Modelle

Für Details zu Datenstrukturen siehe:

- `gal/config.py:10-42` - GlobalConfig Dataclass
- `gal/config.py:45-68` - Upstream Dataclass
- `gal/config.py:71-98` - Route Dataclass
- `gal/config.py:101-134` - ComputedField Dataclass
- `gal/config.py:137-163` - Validation Dataclass
- `gal/config.py:166-200` - Transformation Dataclass
- `gal/config.py:203-255` - Service Dataclass
- `gal/config.py:258-279` - Plugin Dataclass
- `gal/config.py:282-371` - Config Dataclass (Haupt-Container)

### Transformation Engine

Spezielle Methoden für Lua-Script-Generierung:

- `gal/providers/apisix.py:159-218` - `_generate_lua_transformation()` für APISIX
- `gal/providers/envoy.py:155-177` - Inline Lua für Envoy

Diese Methoden zeigen, wie GAL automatisch Lua-Code für Payload-Transformationen generiert.

## Siehe auch

- [Schnellstart-Guide](QUICKSTART.md)
- [Konfigurationsreferenz](../api/CONFIGURATION.md)
- [Transformations-Guide](TRANSFORMATIONS.md)
- [Architektur-Dokumentation](../architecture/ARCHITECTURE.md)
