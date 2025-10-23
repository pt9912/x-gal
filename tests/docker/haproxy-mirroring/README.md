# HAProxy Request Mirroring E2E Tests

Docker-based end-to-end tests for HAProxy request routing with mirroring configuration.

## Important Note: HAProxy Request Mirroring Support

**HAProxy supports request mirroring via SPOE (Stream Processing Offload Engine)** since version 2.0.

SPOE is a **native HAProxy feature**, but requires an **external SPOE agent process** (`spoa-mirror`) for request mirroring implementation.

### HAProxy Mirroring Solutions

#### 1. **SPOE + spoa-mirror** - ✅ **Native HAProxy** (Recommended for Production)

**SPOE (Stream Processing Offload Engine)** is HAProxy's native method for request mirroring.

```bash
# Compile spoa-mirror agent (from HAProxy contrib/)
cd contrib/spoa_example
make
./spoa-mirror -p 12345 -f /etc/haproxy/spoa-mirror.conf
```

**Features:**
- ✅ Native HAProxy feature (since 2.0)
- ✅ Fire-and-forget (async)
- ✅ Sample percentage support
- ✅ Custom headers
- ✅ Production-ready
- ⚠️ Complex setup (external agent process)

**See:**
- [REQUEST_MIRRORING.md](../../../docs/guides/REQUEST_MIRRORING.md#4-haproxy-️-spoe-basiert---haproxy-20) for complete SPOE documentation
- **[../haproxy-mirroring-spoe/](../haproxy-mirroring-spoe/)** - Complete production-ready SPOE example with Docker Compose

---

#### 2. **GoReplay (gor)** - ⭐ **Easiest Alternative**

[https://github.com/buger/goreplay](https://github.com/buger/goreplay)

```bash
# Capture traffic from HAProxy and replay to shadow backend
docker run -d --name gor \
  --network host \
  goreplay/goreplay:latest \
  --input-raw :8080 \
  --output-http "http://shadow-backend:8080|50%"
```

**Features:**
- ✅ Simple setup (no HAProxy changes)
- ✅ Sample percentage support
- ✅ Recommended for testing/staging
- ⚠️ External dependency

---

#### 3. **Teeproxy** - Simple but Synchronous

[https://github.com/chrissnell/teeproxy](https://github.com/chrissnell/teeproxy)

```bash
# Mirror requests to multiple backends
teeproxy -l :8080 -a localhost:9000 -b localhost:9001
```

**Features:**
- ✅ Lightweight
- ⚠️ Synchronous (waits for both responses)

---

#### 4. **Lua Scripting** - Custom Implementation

```haproxy
# Requires HAProxy with Lua support
global
    lua-load /etc/haproxy/mirror.lua

frontend http_front
    http-request lua.mirror-request
```

**Features:**
- ⚠️ Custom implementation needed
- ⚠️ Not fire-and-forget by default

---

### What These Tests Validate

These E2E tests validate HAProxy routing configuration **without SPOE setup**:
- ✅ HAProxy routing configuration
- ✅ Backend health checks
- ✅ Request handling (GET, POST)
- ✅ Concurrent request handling
- ✅ HAProxy stats endpoint

For **production mirroring**, use:
1. **SPOE + spoa-mirror** (native, complex)
2. **GoReplay** (external, simple)

## Architecture

```
Client → HAProxy (Port 10004)
           ├─> Primary Backend (backend-primary:8080)
           └─> (Shadow Backend would require external tool)
```

## Running the Tests

### Prerequisites
- Docker and Docker Compose installed
- Python 3.8+
- pytest and requests libraries

### Run Tests

```bash
# Run all HAProxy mirroring tests
pytest tests/test_haproxy_mirroring_e2e.py -v -s

# Run specific test
pytest tests/test_haproxy_mirroring_e2e.py::TestHAProxyRequestMirroringE2E::test_primary_backend_routing -v -s
```

### Manual Testing

```bash
# Start containers
cd tests/docker/haproxy-mirroring
docker compose up -d

# Wait for services to be healthy
docker compose ps

# Test primary backend routing
curl http://localhost:10004/api/v1
curl http://localhost:10004/api/v2
curl http://localhost:10004/api/v3

# View HAProxy stats
open http://localhost:9999/stats

# Check HAProxy config
docker compose exec haproxy haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg

# View logs
docker compose logs -f haproxy

# Stop containers
docker compose down -v
```

## Test Scenarios

### 1. Primary Backend Routing (`test_primary_backend_routing`)
- **Route:** `/api/v1`
- **Expected:** All requests routed to primary backend
- **Validates:** HAProxy routing configuration

### 2. API v2 Routing (`test_api_v2_routing`)
- **Route:** `/api/v2`
- **Expected:** All requests routed to primary backend
- **Validates:** Multiple route configuration

### 3. No Mirroring Baseline (`test_no_mirroring_baseline`)
- **Route:** `/api/v3`
- **Expected:** All requests routed to primary backend
- **Validates:** Baseline routing without mirroring

### 4. POST Request Routing (`test_post_request_routing`)
- **Route:** `/api/v1` (POST)
- **Expected:** POST requests handled correctly
- **Validates:** Request body forwarding

### 5. Backend Health (`test_haproxy_backend_health`)
- **Validates:** Backends are reachable through HAProxy

### 6. Stats Endpoint (`test_haproxy_stats_endpoint`)
- **Endpoint:** `http://localhost:9999/stats`
- **Validates:** HAProxy statistics UI is accessible

### 7. Mirroring Statistics (`test_haproxy_mirroring_stats`)
- **Purpose:** Analyze HAProxy backend traffic statistics
- **Method:** Parse HAProxy stats CSV format (`/stats;csv`)
- **Validates:** Primary backend receives requests correctly
- **Note:** True mirroring stats require SPOE + spoa-mirror setup
- **CSV Fields:** `pxname` (backend name), `svname` (server), `stot` (total sessions)

### 8. Concurrent Requests (`test_multiple_concurrent_requests`)
- **Load:** 50 concurrent requests
- **Expected:** ≥95% success rate
- **Validates:** HAProxy handles concurrent traffic

### 9. Configuration Verification (`test_haproxy_configuration_verification`)
- **Validates:** HAProxy config syntax is valid

### 10. Mirroring Solutions Note (`test_haproxy_mirroring_limitation_note`)
- **Purpose:** Documents HAProxy's request mirroring solutions (SPOE, GoReplay, etc.)
- **Always passes** - informational test

## Configuration Files

### docker-compose.yml
- **backend-primary:** Primary production backend (port 8080)
- **backend-shadow:** Shadow backend for mirroring (port 8080)
- **haproxy:** HAProxy 2.9 (proxy port 10004, stats port 9999)

### haproxy-mirroring.cfg
HAProxy configuration with:
- Frontend on port 10000
- Backend definitions (primary, shadow)
- ACL-based routing for `/api/v1`, `/api/v2`, `/api/v3`
- Stats endpoint on port 9999
- Health check endpoint

### mirroring-config.yaml
GAL configuration demonstrating mirroring syntax:
- 3 services with different mirroring configurations
- 100% mirroring, 50% mirroring, no mirroring scenarios
- Note: Production requires SPOE + spoa-mirror or external tools

## HAProxy Request Mirroring in Production

### Option 1: SPOE + spoa-mirror (Native, Recommended for Production)

**SPOE (Stream Processing Offload Engine)** is HAProxy's native mirroring solution since version 2.0.

```bash
# Compile and start spoa-mirror agent
cd contrib/spoa_example
make
./spoa-mirror -p 12345 -f /etc/haproxy/spoa-mirror.conf
```

```haproxy
# haproxy.cfg
backend spoe-mirror
    mode tcp
    server spoe1 127.0.0.1:12345 check

frontend http_front
    bind *:8080
    filter spoe engine mirror config /etc/haproxy/spoe-mirror.conf

    # 50% sampling
    acl mirror_sample rand(50)
    http-request set-var(txn.mirror_enabled) bool(true) if mirror_sample

    default_backend primary_backend
```

```
# spoe-mirror.conf
[mirror]
spoe-agent mirror-agent
    messages   mirror-request
    option     async
    option     send-frag-payload
    timeout    processing 500ms
    use-backend spoe-mirror

spoe-message mirror-request
    args method=method path=path headers=req.hdrs body=req.body
    event on-frontend-http-request if { var(txn.mirror_enabled) -m bool }
```

**See:** [REQUEST_MIRRORING.md](../../../docs/guides/REQUEST_MIRRORING.md#4-haproxy-️-spoe-basiert---haproxy-20) for complete configuration.

---

### Option 2: GoReplay (gor) - Easiest Alternative

```bash
# Deploy alongside HAProxy (no HAProxy changes needed!)
docker run -d --name gor \
  --network host \
  goreplay/goreplay:latest \
  --input-raw :8080 \
  --output-http "http://shadow-backend:8080|50%"
```

---

### Option 3: Lua Scripting (Not Recommended)
```haproxy
# haproxy.cfg (requires HAProxy with Lua support)
global
    lua-load /etc/haproxy/mirror.lua

frontend http_front
    http-request lua.mirror-request
```

```lua
-- mirror.lua
core.register_action("mirror-request", { "http-req" }, function(txn)
    -- Async HTTP request to shadow backend
    -- Implementation depends on Lua HTTP client
end)
```

## Comparison with Other Providers

| Feature | Envoy | Nginx | APISIX | HAProxy |
|---------|-------|-------|--------|---------|
| **Native Mirroring** | ✅ Yes (async) | ✅ Yes (mirror directive) | ✅ Yes (proxy-mirror plugin) | ⚠️ Yes (SPOE, complex) |
| **Sample Percentage** | ✅ Yes (runtime_fraction) | ✅ Yes (split_clients) | ✅ Yes (sample_ratio) | ✅ Yes (rand() ACL) |
| **Mirror Request Body** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes (SPOE) |
| **Mirror Headers** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes (SPOE) |
| **Fire-and-Forget** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes (SPOE async) |
| **Setup Complexity** | 🟢 Low | 🟢 Low | 🟢 Low | 🔴 High (SPOE agent) |
| **Production Ready** | ✅ Built-in | ✅ Built-in | ✅ Built-in | ✅ SPOE (2.0+) |

**Recommendation:**
- **Simple setup:** Use **Envoy**, **Nginx**, or **APISIX** (easier mirroring)
- **HAProxy required:** Use **SPOE + spoa-mirror** (native, complex) or **GoReplay** (external, simple)

## Troubleshooting

### Containers not starting
```bash
# Check container status
docker compose ps

# View logs
docker compose logs haproxy
docker compose logs backend-primary
docker compose logs backend-shadow

# Rebuild
docker compose down -v
docker compose up -d --build
```

### HAProxy config errors
```bash
# Test config syntax
docker compose exec haproxy haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg

# View config
docker compose exec haproxy cat /usr/local/etc/haproxy/haproxy.cfg
```

### Backends not responding
```bash
# Check backend health
docker compose exec backend-primary python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8080').read())"

# Restart backends
docker compose restart backend-primary backend-shadow
```

### Port conflicts
The tests use:
- **10004:** HAProxy proxy port (external)
- **9999:** HAProxy stats port
- **8080:** Backend ports (internal)

If ports are in use:
```bash
# Check what's using the port
sudo lsof -i :10004
sudo lsof -i :9999

# Change ports in docker-compose.yml
```

## References

- [HAProxy Documentation](https://docs.haproxy.org/)
- [HAProxy SPOE](https://www.haproxy.com/documentation/hapee/latest/api/spoe/)
- [GoReplay GitHub](https://github.com/buger/goreplay)
- [Teeproxy GitHub](https://github.com/chrissnell/teeproxy)
- [GAL Request Mirroring Documentation](../../../docs/guides/PROVIDERS_FEATURES.md)
