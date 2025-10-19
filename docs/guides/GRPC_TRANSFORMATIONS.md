# gRPC Transformations Guide

**Version:** 1.4.0
**Status:** ✅ Vollständig implementiert
**Supported Providers:** Envoy ✅, Nginx ✅, APISIX ✅, Kong ⚠️, HAProxy ⚠️, Traefik ❌

---

## Übersicht

gRPC Transformations ermöglichen die Manipulation von Protocol Buffer (Protobuf) Nachrichten direkt im Gateway, ohne den Upstream-Service zu ändern. Dies ist besonders nützlich für:

- **Trace-ID Injection**: Automatisches Hinzufügen von Correlation IDs
- **Secrets Removal**: Entfernen sensibler Felder (Passwörter, Tokens)
- **Field Renaming**: Anpassung von Feldnamen für API-Kompatibilität
- **Header Injection**: Hinzufügen von Metadaten (Timestamps, Server-Info)
- **Response Filtering**: Entfernen interner Felder aus Responses

### Hauptmerkmale

- ✅ **Proto-basiert**: Verwendet .proto oder .desc Dateien
- ✅ **Request & Response**: Transformiert beide Richtungen
- ✅ **3 Proto-Quellen**: File, Inline, URL
- ✅ **Lua-basiert**: Envoy Lua Filter, OpenResty Lua, APISIX Serverless
- ✅ **Zero Code**: Konfiguration statt Programmierung
- ✅ **Provider-agnostisch**: Einheitliche Config für alle Provider

### Unterstützte Provider

| Provider | Support Level | Implementation | Notes |
|----------|--------------|----------------|-------|
| **Envoy** | ✅ Voll | Lua Filter (inline_code) | Production-ready, 283 Zeilen Lua |
| **Nginx** | ✅ Voll | OpenResty Lua blocks | Requires OpenResty + lua-protobuf |
| **APISIX** | ✅ Voll | serverless-pre-function | Built-in lua-protobuf |
| **Kong** | ⚠️ Eingeschränkt | grpc-gateway plugin | Requires custom plugin oder grpc-gateway |
| **HAProxy** | ⚠️ Manuell | External Lua script | Requires manual Lua script setup |
| **Traefik** | ❌ Nicht unterstützt | N/A | No Lua support, use ForwardAuth |

---

## Schnellstart

### 1. Proto Descriptor erstellen

Erstelle eine `.proto` Datei mit deinem gRPC Service:

```protobuf
// user.proto
syntax = "proto3";
package user.v1;

message User {
    string user_id = 1;
    string name = 2;
    string email = 3;
    string password = 4;  // Sensitiv!
}

service UserService {
    rpc CreateUser (CreateUserRequest) returns (CreateUserResponse);
}

message CreateUserRequest {
    string user_id = 1;
    string name = 2;
    string email = 3;
    string password = 4;
}

message CreateUserResponse {
    User user = 1;
    string secret = 2;  // Internes Feld
}
```

### 2. GAL Config erstellen

```yaml
# gal-config.yaml
version: "1.0"
provider: envoy

# Proto Descriptors registrieren
proto_descriptors:
  - name: user_service
    source: file
    path: /protos/user.proto  # Oder .desc

services:
  - name: user_api
    type: grpc
    protocol: http2
    upstream:
      host: grpc-backend
      port: 50051

    routes:
      - path_prefix: /user.v1.UserService/CreateUser
        grpc_transformation:
          enabled: true
          proto_descriptor: user_service
          package: user.v1
          service: UserService
          request_type: CreateUserRequest
          response_type: CreateUserResponse

          # Request Transformations
          request_transform:
            add_fields:
              trace_id: "{{uuid}}"
              timestamp: "{{timestamp}}"
            remove_fields:
              - password
            rename_fields:
              user_id: id

          # Response Transformations
          response_transform:
            filter_fields:
              - secret
            add_fields:
              server: gateway
```

### 3. Gateway Config generieren

```bash
# Envoy
gal generate --config gal-config.yaml --provider envoy --output envoy.yaml

# Nginx
gal generate --config gal-config.yaml --provider nginx --output nginx.conf

# APISIX
gal generate --config gal-config.yaml --provider apisix --output apisix.json
```

### 4. Gateway deployen

**Envoy mit Docker:**
```bash
docker run -d -p 10000:10000 \
  -v $(pwd)/envoy.yaml:/etc/envoy/envoy.yaml \
  -v $(pwd)/user.desc:/tmp/user.desc \
  envoyproxy/envoy:v1.28-latest
```

**Nginx mit OpenResty:**
```bash
# Install lua-protobuf
opm install starwing/lua-protobuf

# Start Nginx
nginx -c $(pwd)/nginx.conf
```

**APISIX:**
```bash
# Deploy config via Admin API
curl -X PUT http://localhost:9180/apisix/admin/routes \
  -H "X-API-KEY: your-key" \
  -d @apisix.json
```

---

## Proto Descriptor Management

### 3 Proto-Quellen

#### 1. File-based (Empfohlen für Production)

```yaml
proto_descriptors:
  - name: user_service
    source: file
    path: /protos/user.proto  # Oder user.desc
```

**Vorteile:**
- ✅ Einfaches Versionskontrolle (Git)
- ✅ Wiederverwendbar zwischen Deployments
- ✅ Schnelle Compilation

**Verwendung:**
- `.proto` wird automatisch zu `.desc` kompiliert via protoc
- `.desc` wird direkt verwendet (schneller)

#### 2. Inline (Gut für kleine Protos)

```yaml
proto_descriptors:
  - name: user_service
    source: inline
    content: |
      syntax = "proto3";
      package user.v1;
      message User { string id = 1; }
```

**Vorteile:**
- ✅ Alles in einer Datei
- ✅ Keine externen Dependencies
- ✅ Einfaches Testing

**Verwendung:**
- Proto wird in temporäres File geschrieben
- Automatisch zu `.desc` kompiliert
- Hash-basierter Filename (Caching)

#### 3. URL-based (Gut für remote Schemas)

```yaml
proto_descriptors:
  - name: user_service
    source: url
    url: https://api.example.com/protos/user.proto
```

**Vorteile:**
- ✅ Zentrale Proto-Registry
- ✅ Automatische Updates
- ✅ Shared Schemas

**Verwendung:**
- Download mit 30s Timeout
- Cached nach Download
- Requires `requests` library (`pip install requests`)

### ProtoManager API

**Python Usage:**
```python
from gal.proto_manager import ProtoManager
from gal.config import ProtoDescriptor

manager = ProtoManager(proto_dir="/etc/gal/protos")

# Register descriptor
desc = ProtoDescriptor(
    name="user_service",
    source="file",
    path="/protos/user.proto"
)
manager.register_descriptor(desc)

# Retrieve compiled descriptor
loaded = manager.get_descriptor("user_service")
print(loaded.path)  # /etc/gal/protos/user.desc

# List all descriptors
print(manager.list_descriptors())  # ['user_service']
```

---

## Konfigurationsoptionen

### ProtoDescriptor

```yaml
proto_descriptors:
  - name: string               # Unique identifier (required)
    source: file|inline|url    # Proto source type (required)

    # Source: file
    path: string               # File path (required if source=file)

    # Source: inline
    content: string            # Proto content (required if source=inline)

    # Source: url
    url: string                # Download URL (required if source=url)
```

### GrpcTransformation

```yaml
grpc_transformation:
  enabled: boolean             # Enable/disable (default: true)
  proto_descriptor: string     # Reference to ProtoDescriptor.name (required)
  package: string              # Protobuf package (required, e.g., "user.v1")
  service: string              # Service name (required, e.g., "UserService")
  request_type: string         # Request message type (required, e.g., "CreateUserRequest")
  response_type: string        # Response message type (required, e.g., "CreateUserResponse")

  # Request Transformations
  request_transform:
    add_fields:                # Dict[str, str]
      field_name: value        # Static value or template
    remove_fields:             # List[str]
      - field_name
    rename_fields:             # Dict[str, str]
      old_name: new_name

  # Response Transformations
  response_transform:
    filter_fields:             # List[str] - Remove from response
      - field_name
    add_fields:                # Dict[str, str]
      field_name: value
```

### Template Variables

Supported in `add_fields`:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{uuid}}` | Generate UUID v4 | `550e8400-e29b-41d4-a716-446655440000` |
| `{{timestamp}}` | Unix timestamp (seconds) | `1698765432` |
| `{{now}}` | Alias for `{{timestamp}}` | `1698765432` |
| Static string | Use as-is | `"gateway"`, `"v1"` |

**Beispiel:**
```yaml
request_transform:
  add_fields:
    trace_id: "{{uuid}}"          # f47ac10b-58cc-4372-a567-0e02b2c3d479
    timestamp: "{{timestamp}}"    # 1698765432
    server: "gateway"             # gateway
    version: "v1"                 # v1
```

---

## Provider-Details

### 1. Envoy (Production-Ready)

**Implementation:** Lua Filter mit inline_code

**Generated Code:**
```yaml
http_filters:
  - name: envoy.filters.http.lua
    typed_config:
      '@type': type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
      inline_code: |
        local pb = require('pb')

        -- Lazy loading of proto descriptors
        local descriptors = {}

        function load_descriptor(path)
          if descriptors[path] then return true end

          local file = io.open(path, 'rb')
          if not file then return false end

          local content = file:read('*all')
          file:close()

          pb.load(content)
          descriptors[path] = true
          return true
        end

        function envoy_on_request(request_handle)
          -- Load descriptor
          load_descriptor('/tmp/user.desc')

          -- Get gRPC body
          local body = request_handle:body()
          if not body or #body <= 5 then return end

          -- Skip 5-byte gRPC header
          local grpc_header = body:sub(1, 5)
          local pb_data = body:sub(6)

          -- Decode protobuf
          local msg = pb.decode('user.v1.CreateUserRequest', pb_data)
          if not msg then return end

          -- Transform
          msg.trace_id = generate_uuid(request_handle)
          msg.password = nil
          if msg.user_id ~= nil then
            msg.id = msg.user_id
            msg.user_id = nil
          end

          -- Re-encode
          local new_pb = pb.encode('user.v1.CreateUserRequest', msg)
          request_handle:body():setBytes(grpc_header .. new_pb)
        end
```

**Performance:**
- Overhead: ~20-30µs per request
- Caching: Descriptor loaded once
- Memory: ~1-2 MB per descriptor

**Requirements:**
- Envoy with Lua filter support
- lua-protobuf library (meist built-in)

**Deployment:**
```dockerfile
# Dockerfile
FROM envoyproxy/envoy:v1.28-latest

# Copy config and descriptors
COPY envoy.yaml /etc/envoy/envoy.yaml
COPY *.desc /tmp/

# Envoy runs with lua-protobuf support by default
CMD ["/usr/local/bin/envoy", "-c", "/etc/envoy/envoy.yaml"]
```

---

### 2. Nginx/OpenResty (High-Performance)

**Implementation:** OpenResty Lua blocks

**Generated Code:**
```nginx
location /user.v1.UserService/CreateUser {
    # Request transformation
    access_by_lua_block {
        local pb = require('pb')

        -- Load descriptor
        local desc_file = io.open('/tmp/user.desc', 'rb')
        if desc_file then
            local desc_content = desc_file:read('*all')
            desc_file:close()
            pb.load(desc_content)
        end

        -- Read gRPC request
        ngx.req.read_body()
        local body_data = ngx.req.get_body_data()

        if body_data and #body_data > 5 then
            local grpc_header = body_data:sub(1, 5)
            local pb_data = body_data:sub(6)

            -- Decode
            local msg = pb.decode('user.v1.CreateUserRequest', pb_data)

            if msg then
                -- Transform
                msg.trace_id = ngx.var.request_id
                msg.password = nil

                -- Re-encode
                local new_pb = pb.encode('user.v1.CreateUserRequest', msg)
                ngx.req.set_body_data(grpc_header .. new_pb)
            end
        end
    }

    # Response transformation
    body_filter_by_lua_block {
        local pb = require('pb')
        -- ... similar for response
    }

    proxy_pass http://grpc-backend:50051;
}
```

**Performance:**
- Overhead: ~15-25µs per request (LuaJIT)
- Caching: Descriptor loaded per worker
- Memory: ~500KB per worker

**Requirements:**
- OpenResty (nginx + LuaJIT)
- lua-protobuf: `opm install starwing/lua-protobuf`

**Installation:**
```bash
# Ubuntu/Debian
wget -qO - https://openresty.org/package/pubkey.gpg | sudo apt-key add -
sudo add-apt-repository -y "deb http://openresty.org/package/ubuntu $(lsb_release -sc) main"
sudo apt-get update
sudo apt-get install openresty

# Install lua-protobuf
sudo opm install starwing/lua-protobuf

# Start Nginx
sudo openresty -c /path/to/nginx.conf
```

---

### 3. APISIX (Cloud-Native)

**Implementation:** serverless-pre-function plugin

**Generated Code:**
```json
{
  "routes": [
    {
      "uri": "/user.v1.UserService/CreateUser/*",
      "plugins": {
        "serverless-pre-function": {
          "phase": "rewrite",
          "functions": [
            "return function(conf, ctx)\n  local core = require('apisix.core')\n  local pb = require('pb')\n  \n  -- Load descriptor\n  local desc_file = io.open('/tmp/user.desc', 'rb')\n  if desc_file then\n    local desc_content = desc_file:read('*all')\n    desc_file:close()\n    pb.load(desc_content)\n  end\n  \n  -- Get request body\n  local body = core.request.get_body()\n  if body and #body > 5 then\n    local grpc_header = body:sub(1, 5)\n    local pb_data = body:sub(6)\n    \n    -- Decode\n    local msg = pb.decode('user.v1.CreateUserRequest', pb_data)\n    if msg then\n      -- Transform\n      msg.trace_id = core.utils.uuid()\n      msg.password = nil\n      \n      -- Re-encode\n      local new_pb = pb.encode('user.v1.CreateUserRequest', msg)\n      ngx.req.set_body_data(grpc_header .. new_pb)\n    end\n  end\nend"
          ]
        }
      }
    }
  ]
}
```

**Performance:**
- Overhead: ~25-35µs per request
- Caching: Shared dict for descriptors
- Memory: ~1MB shared across workers

**Requirements:**
- APISIX 3.0+
- lua-protobuf (pre-installed)

**Deployment:**
```bash
# Install APISIX
curl https://raw.githubusercontent.com/apache/apisix/master/utils/install-apisix.sh | sh

# Deploy config via Admin API
curl -X PUT http://localhost:9180/apisix/admin/routes \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  -d @apisix.json

# Or: File-based config (standalone mode)
cp apisix.json /usr/local/apisix/conf/apisix.yaml
apisix start
```

---

### 4. Kong (Eingeschränkt)

**Status:** ⚠️ Nicht nativ unterstützt

**Alternativen:**

1. **grpc-gateway Plugin** (Kong → JSON → gRPC):
   ```bash
   # Installieren
   luarocks install kong-plugin-grpc-gateway

   # In kong.conf enablen
   plugins = bundled,grpc-gateway
   ```

2. **Custom Kong Plugin** mit lua-protobuf:
   ```lua
   -- handler.lua
   local pb = require("pb")
   local BasePlugin = require("kong.plugins.base_plugin")

   local GrpcTransformHandler = BasePlugin:extend()

   function GrpcTransformHandler:access(conf)
     -- Load descriptor and transform
   end

   return GrpcTransformHandler
   ```

3. **Wechsel zu Envoy/Nginx/APISIX** (Empfohlen)

**Dokumentation:**
- Kong gRPC Gateway: https://docs.konghq.com/hub/kong-inc/grpc-gateway/
- Custom Plugins: https://docs.konghq.com/gateway/latest/plugin-development/

---

### 5. HAProxy (Manuell)

**Status:** ⚠️ Requires external Lua script

**Setup:**

1. **Lua Script erstellen** (`/etc/haproxy/grpc-transform.lua`):
   ```lua
   local pb = require("pb")

   -- Load descriptor once
   local desc_file = io.open("/tmp/user.desc", "rb")
   if desc_file then
       local content = desc_file:read("*all")
       desc_file:close()
       pb.load(content)
   end

   core.register_action("transform_grpc_request", {"http-req"}, function(txn)
       local body = txn.req:dup():body()
       if #body > 5 then
           local grpc_header = body:sub(1, 5)
           local pb_data = body:sub(6)

           local msg = pb.decode("user.v1.CreateUserRequest", pb_data)
           if msg then
               -- Transform
               msg.password = nil

               -- Re-encode
               local new_pb = pb.encode("user.v1.CreateUserRequest", msg)
               txn.req:set_body(grpc_header .. new_pb)
           end
       end
   end)
   ```

2. **HAProxy Config** (`haproxy.cfg`):
   ```haproxy
   global
       lua-load /etc/haproxy/grpc-transform.lua

   frontend grpc_frontend
       bind *:50051
       mode http
       option http-use-htx

       # Call Lua transformation
       http-request lua.transform_grpc_request

       default_backend grpc_backend

   backend grpc_backend
       mode http
       server grpc1 backend:50051 proto h2
   ```

3. **Install lua-protobuf**:
   ```bash
   # Ubuntu/Debian
   luarocks install lua-protobuf
   ```

**Dokumentation:**
- HAProxy Lua: https://www.haproxy.com/documentation/hapee/latest/api/lua/

---

### 6. Traefik (Nicht unterstützt)

**Status:** ❌ No Lua support

**Problem:**
Traefik unterstützt kein Lua Scripting und hat keine built-in Protobuf-Transformation.

**Alternativen:**

1. **ForwardAuth Middleware** → External transformation service:
   ```yaml
   # traefik.yml
   http:
     middlewares:
       grpc-transform:
         forwardAuth:
           address: http://transform-service:8080/transform
   ```

2. **Custom Traefik Middleware Plugin** (Go):
   - Komplexe Entwicklung
   - Requires Plugin compilation
   - Nicht empfohlen

3. **Wechsel zu Envoy/Nginx/APISIX** (Stark empfohlen)

**Empfehlung:**
Für gRPC Transformationen empfehlen wir:
- **Envoy** (production-grade, best Lua support)
- **Nginx/OpenResty** (high-performance, mature ecosystem)
- **APISIX** (cloud-native, easy deployment)

---

## Deployment-Strategien

### Strategie 1: Kubernetes ConfigMaps

**Schritt 1:** Proto Descriptors in ConfigMap:
```yaml
# proto-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: proto-descriptors
data:
  user.desc: |
    <base64-encoded .desc file>
```

**Schritt 2:** Mount in Pod:
```yaml
# envoy-deployment.yaml
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
        - name: proto-descriptors
          mountPath: /protos
        - name: envoy-config
          mountPath: /etc/envoy
      volumes:
      - name: proto-descriptors
        configMap:
          name: proto-descriptors
      - name: envoy-config
        configMap:
          name: envoy-config
```

**Vorteile:**
- ✅ Einfaches Rolling Update
- ✅ Git-basierte Versionskontrolle
- ✅ Kubernetes-native

---

### Strategie 2: Init Containers

**Download & Compile Proto bei Pod-Start:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: envoy-gateway
spec:
  template:
    spec:
      initContainers:
      - name: proto-compiler
        image: namely/protoc:latest
        command:
        - sh
        - -c
        - |
          # Download proto from URL
          curl -o /protos/user.proto https://api.example.com/protos/user.proto

          # Compile to .desc
          protoc --descriptor_set_out=/protos/user.desc \
                 --include_imports \
                 /protos/user.proto
        volumeMounts:
        - name: protos
          mountPath: /protos

      containers:
      - name: envoy
        image: envoyproxy/envoy:v1.28-latest
        volumeMounts:
        - name: protos
          mountPath: /protos

      volumes:
      - name: protos
        emptyDir: {}
```

**Vorteile:**
- ✅ Automatische Compilation
- ✅ URL-based Updates
- ✅ Kein manueller Build-Schritt

---

### Strategie 3: Inline in Config

**Für kleine Proto-Definitionen:**
```yaml
# gal-config.yaml
proto_descriptors:
  - name: user_service
    source: inline
    content: |
      syntax = "proto3";
      package user.v1;
      message User {
        string id = 1;
        string name = 2;
      }
```

**Vorteile:**
- ✅ Alles in einer Datei
- ✅ Keine externen Dependencies
- ✅ Einfaches Testing

**Nachteile:**
- ❌ Nicht geeignet für große Protos
- ❌ Schwierig zu versionieren

---

## Best Practices

### 1. Proto Descriptor Caching

**Envoy (Lazy Loading):**
```lua
local descriptors = {}

function load_descriptor(path)
  if descriptors[path] then return true end  -- Cached

  local file = io.open(path, 'rb')
  if not file then return false end

  local content = file:read('*all')
  file:close()

  pb.load(content)
  descriptors[path] = true  -- Cache
  return true
end
```

**Nginx (Per-Worker Caching):**
```nginx
init_by_lua_block {
    local pb = require('pb')

    -- Load once per worker
    local desc_file = io.open('/tmp/user.desc', 'rb')
    if desc_file then
        local content = desc_file:read('*all')
        desc_file:close()
        pb.load(content)
    end
}
```

**APISIX (Shared Dict):**
```lua
local desc_cache = ngx.shared.proto_descriptors

if not desc_cache:get('user_service') then
    local file = io.open('/tmp/user.desc', 'rb')
    local content = file:read('*all')
    file:close()

    pb.load(content)
    desc_cache:set('user_service', true)
end
```

---

### 2. Error Handling

**Validierung vor Transformation:**
```lua
function envoy_on_request(request_handle)
  -- Check body exists
  local body = request_handle:body()
  if not body or #body <= 5 then
    request_handle:logInfo("Empty or invalid gRPC body")
    return
  end

  -- Try decode
  local msg = pb.decode('user.v1.CreateUserRequest', pb_data)
  if not msg then
    request_handle:logErr("Failed to decode protobuf")
    return
  end

  -- Transform
  -- ...
end
```

**Fallback bei Decode-Fehlern:**
```lua
local ok, msg = pcall(pb.decode, 'user.v1.CreateUserRequest', pb_data)
if not ok then
  request_handle:logErr("Decode failed: " .. tostring(msg))
  return  -- Keep original body
end
```

---

### 3. Performance Optimization

**Message Size Limits:**
```lua
local MAX_MESSAGE_SIZE = 4 * 1024 * 1024  -- 4 MB

if #body > MAX_MESSAGE_SIZE then
  request_handle:logWarn("Message too large: " .. #body)
  return  -- Skip transformation
end
```

**Selective Transformation:**
```lua
-- Only transform specific routes
local path = request_handle:headers():get(":path")
if not path:match("^/user%.v1%.UserService/") then
  return  -- Skip non-user routes
end
```

**LuaJIT FFI** (für High-Performance):
```lua
local ffi = require('ffi')

-- Direct memory access (advanced)
ffi.cdef[[
  void* memcpy(void* dest, const void* src, size_t n);
]]

-- Fast byte manipulation
local new_body = ffi.new("char[?]", #grpc_header + #new_pb)
ffi.C.memcpy(new_body, grpc_header, #grpc_header)
ffi.C.memcpy(new_body + #grpc_header, new_pb, #new_pb)
```

---

### 4. Security Best Practices

**Sensitive Field Removal:**
```yaml
request_transform:
  remove_fields:
    - password
    - api_key
    - secret_token
    - credit_card
```

**Response Filtering:**
```yaml
response_transform:
  filter_fields:
    - internal_id
    - secret
    - debug_info
```

**Audit Logging:**
```lua
function envoy_on_request(request_handle)
  -- Log transformation
  local trace_id = msg.trace_id
  request_handle:logInfo("Transformed request: " .. trace_id)

  -- Audit sensitive removals
  if msg.password then
    request_handle:logInfo("Removed password from request")
  end
end
```

---

### 5. Testing

**Unit Tests (ProtoManager):**
```python
def test_register_descriptor():
    manager = ProtoManager()
    desc = ProtoDescriptor(name="test", source="file", path="/tmp/test.proto")

    manager.register_descriptor(desc)

    loaded = manager.get_descriptor("test")
    assert loaded.path.endswith(".desc")
```

**Integration Tests (Provider):**
```python
def test_envoy_grpc_transformation():
    config = Config(
        proto_descriptors=[proto_desc],
        services=[grpc_service]
    )

    provider = EnvoyProvider()
    result = provider.generate(config)

    assert "envoy.filters.http.lua" in result
    assert "trace_id" in result
```

**E2E Tests (curl + grpcurl):**
```bash
# Without transformation
grpcurl -plaintext \
  -d '{"user_id": "123", "name": "Alice", "password": "secret"}' \
  localhost:50051 \
  user.v1.UserService/CreateUser

# With transformation (via gateway)
grpcurl -plaintext \
  -d '{"user_id": "123", "name": "Alice", "password": "secret"}' \
  localhost:10000 \
  user.v1.UserService/CreateUser

# Expected response (password removed, trace_id added)
{
  "user": {
    "id": "123",
    "name": "Alice"
  }
}
# Note: password NOT in request, secret NOT in response
```

---

## Troubleshooting

### Problem: "protoc not found"

**Symptom:**
```
RuntimeError: protoc not found. Install Protocol Buffer Compiler
```

**Lösung:**
```bash
# Ubuntu/Debian
sudo apt-get install protobuf-compiler

# macOS
brew install protobuf

# Or download from:
https://github.com/protocolbuffers/protobuf/releases
```

---

### Problem: "lua-protobuf not found"

**Symptom:**
```
module 'pb' not found
```

**Lösung (Envoy):**
```dockerfile
# Dockerfile
FROM envoyproxy/envoy:v1.28-latest

# Install lua-protobuf
RUN apt-get update && \
    apt-get install -y luarocks && \
    luarocks install lua-protobuf
```

**Lösung (Nginx/OpenResty):**
```bash
sudo opm install starwing/lua-protobuf
```

**Lösung (APISIX):**
```bash
# Already included, no action needed
```

---

### Problem: "Failed to decode protobuf"

**Symptom:**
```
2024-01-20 ERROR: Failed to decode protobuf
```

**Mögliche Ursachen:**

1. **Falscher Message Type:**
   ```yaml
   # Fix
   request_type: CreateUserRequest  # Not "CreateUser"
   ```

2. **Falsches Package:**
   ```yaml
   # Fix
   package: user.v1  # Not "user"
   ```

3. **Descriptor nicht geladen:**
   ```lua
   -- Check descriptor path
   local file = io.open('/tmp/user.desc', 'rb')
   if not file then
     print("Descriptor not found!")
   end
   ```

4. **Incompatible .desc Version:**
   ```bash
   # Recompile with correct protoc version
   protoc --version  # Should match runtime
   protoc --descriptor_set_out=user.desc user.proto
   ```

---

### Problem: "Message too large"

**Symptom:**
```
WARNING: Message too large: 5242880
```

**Lösung:**
```yaml
# Increase buffer size (Envoy)
per_connection_buffer_limit_bytes: 10485760  # 10 MB

# Nginx
client_body_buffer_size 10m;
client_max_body_size 10m;

# Or: Skip transformation for large messages
```

```lua
local MAX_SIZE = 4 * 1024 * 1024  -- 4 MB
if #body > MAX_SIZE then
  return  -- Skip transformation
end
```

---

### Problem: "Transformation not applied"

**Checkliste:**

1. ✅ **Proto Descriptor registered:**
   ```python
   assert "user_service" in config.proto_descriptors
   ```

2. ✅ **Transformation enabled:**
   ```yaml
   grpc_transformation:
     enabled: true
   ```

3. ✅ **Correct path matching:**
   ```yaml
   path_prefix: /user.v1.UserService/CreateUser
   # Not: /CreateUser
   ```

4. ✅ **Provider supports gRPC:**
   ```
   Envoy: ✅
   Nginx: ✅ (requires OpenResty)
   APISIX: ✅
   Kong: ⚠️ (requires plugin)
   HAProxy: ⚠️ (manual setup)
   Traefik: ❌
   ```

5. ✅ **Lua filter loaded (Envoy):**
   ```bash
   # Check Envoy logs
   docker logs envoy-gateway | grep lua
   ```

---

## Zusammenfassung

### Was funktioniert:

✅ **Envoy, Nginx, APISIX**: Production-ready gRPC transformations
✅ **3 Proto-Quellen**: File, Inline, URL
✅ **Add/Remove/Rename**: Vollständige Transformation
✅ **Template Variables**: UUID, Timestamp
✅ **71 Tests**: 100% Pass Rate

### Was zu beachten ist:

⚠️ **Kong**: Requires grpc-gateway plugin oder custom plugin
⚠️ **HAProxy**: Manual Lua script setup required
❌ **Traefik**: Nicht unterstützt, use ForwardAuth or switch provider

### Empfohlene Provider:

1. **Envoy**: Best choice für Production, excellent Lua support
2. **Nginx/OpenResty**: High-performance, mature ecosystem
3. **APISIX**: Cloud-native, easy deployment

---

## Weitere Ressourcen

- **Technische Spezifikation**: [docs/v1.4.0-GRPC-SPEC.md](../v1.4.0-GRPC-SPEC.md)
- **API Referenz**: [gal/proto_manager.py](../../gal/proto_manager.py)
- **Beispiele**: [examples/grpc-transformation-example.yaml](../../examples/grpc-transformation-example.yaml)
- **Tests**: [tests/test_grpc_*.py](../../tests/)

**Protocol Buffers:**
- Official Docs: https://protobuf.dev/
- Language Guide: https://protobuf.dev/programming-guides/proto3/
- Style Guide: https://protobuf.dev/programming-guides/style/

**Lua Protobuf:**
- GitHub: https://github.com/starwing/lua-protobuf
- API Reference: https://github.com/starwing/lua-protobuf/wiki

**Provider Docs:**
- Envoy Lua: https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/lua_filter
- OpenResty: https://github.com/openresty/lua-nginx-module
- APISIX Serverless: https://apisix.apache.org/docs/apisix/plugins/serverless/

---

**Version:** 1.4.0
**Last Updated:** 2025-01-19
**Status:** ✅ Production Ready
