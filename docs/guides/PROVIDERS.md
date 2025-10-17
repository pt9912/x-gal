# GAL Provider-Dokumentation

## Übersicht

GAL unterstützt vier führende API-Gateway-Provider. Jeder Provider hat spezifische Eigenschaften, Stärken und ideale Use Cases.

## Unterstützte Provider

| Provider | Output-Format | Transformations | gRPC | REST | GAL Deploy API |
|----------|--------------|-----------------|------|------|----------------|
| Envoy | YAML | Lua Filters | ✅ | ✅ | ✅ File + API check |
| Kong | YAML | Plugins | ✅ | ✅ | ✅ File + Admin API |
| APISIX | JSON | Lua Serverless | ✅ | ✅ | ✅ File + Admin API |
| Traefik | YAML | Middleware | ✅ | ✅ | ✅ File + API verify |

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

## Provider-Vergleich

### Performance

| Provider | Requests/sec | Latency (p50) | Latency (p99) |
|----------|--------------|---------------|---------------|
| Envoy | ~100k | <1ms | <5ms |
| APISIX | ~80k | <1ms | <6ms |
| Kong | ~50k | 2ms | 15ms |
| Traefik | ~40k | 3ms | 20ms |

*Benchmark-Werte sind Richtwerte und variieren je nach Setup*

### Transformations-Vergleich

| Feature | Envoy | Kong | APISIX | Traefik |
|---------|-------|------|--------|---------|
| Defaults | ✅ Lua | ✅ Headers | ✅ Lua | ⚠️ Plugins |
| Computed Fields | ✅ Lua | ❌ | ✅ Lua | ❌ |
| UUID Generation | ✅ | ❌ | ✅ | ❌ |
| Timestamp | ✅ | ❌ | ✅ | ❌ |
| Validation | ⚠️ Limited | ⚠️ Limited | ✅ Full | ❌ |

### Use Case Matrix

| Use Case | Empfohlen | Warum |
|----------|-----------|-------|
| Kubernetes Service Mesh | Envoy | Native Integration |
| API Management Platform | Kong | Enterprise Features |
| High-Traffic Edge | APISIX | Performance |
| Docker Development | Traefik | Auto-Discovery |
| gRPC Heavy | Envoy, APISIX | Native HTTP/2 |
| Multi-Cloud | Kong, APISIX | Provider-agnostic |

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
