# HAProxy Request Mirroring E2E Tests

Docker-based end-to-end tests for HAProxy request routing with mirroring configuration.

## Important Note: HAProxy Request Mirroring Limitation

**HAProxy does NOT support native async request mirroring** like Envoy or Nginx.

To implement request mirroring/shadowing with HAProxy in production, you need external tools:

### Recommended Solutions

1. **GoReplay (gor)** - [https://github.com/buger/goreplay](https://github.com/buger/goreplay)
   ```bash
   # Capture traffic from HAProxy and replay to shadow backend
   gor --input-raw :8080 --output-http http://shadow-backend:8080
   ```

2. **Teeproxy** - [https://github.com/chrissnell/teeproxy](https://github.com/chrissnell/teeproxy)
   ```bash
   # Mirror requests to multiple backends
   teeproxy -l :8080 -a localhost:9000 -b localhost:9001
   ```

3. **SPOE (Stream Processing Offload Engine)**
   - Requires external SPOE agent
   - Complex setup, high performance
   - Used in production HAProxy deployments

4. **Lua Scripting**
   - Requires HAProxy compiled with Lua support
   - Async HTTP client needed for true fire-and-forget
   - Custom implementation per use case

### What These Tests Validate

These E2E tests validate:
- ✅ HAProxy routing configuration
- ✅ Backend health checks
- ✅ Request handling (GET, POST)
- ✅ Concurrent request handling
- ✅ HAProxy stats endpoint

They do **NOT** test actual request mirroring (as HAProxy lacks this feature).

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

### 7. Concurrent Requests (`test_multiple_concurrent_requests`)
- **Load:** 50 concurrent requests
- **Expected:** ≥95% success rate
- **Validates:** HAProxy handles concurrent traffic

### 8. Configuration Verification (`test_haproxy_configuration_verification`)
- **Validates:** HAProxy config syntax is valid

### 9. Mirroring Limitation Note (`test_haproxy_mirroring_limitation_note`)
- **Purpose:** Documents HAProxy's request mirroring limitation
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
- Note: Actual implementation requires external tools

## HAProxy Request Mirroring in Production

### Option 1: GoReplay (Recommended)
```bash
# Deploy alongside HAProxy
docker run -d --name gor \
  --network host \
  goreplay/goreplay:latest \
  --input-raw :8080 \
  --output-http http://shadow-backend:8080 \
  --output-http-track-response
```

### Option 2: SPOE Agent
```haproxy
# haproxy.cfg
backend spoe-mirror
    mode tcp
    server spoe1 127.0.0.1:12345

frontend http_front
    filter spoe engine mirror config /etc/haproxy/spoe-mirror.conf
```

```
# spoe-mirror.conf
[mirror]
spoe-agent mirror-agent
    messages   mirror-request
    option     async
    timeout    processing 2s
    maxconnrate 100
    maxerrrate  50
    use-backend spoe-mirror

spoe-message mirror-request
    args method=method path=path
    event on-frontend-http-request
```

### Option 3: Lua Scripting
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
| **Native Mirroring** | ✅ Yes (async) | ✅ Yes (mirror directive) | ✅ Yes (proxy-mirror plugin) | ❌ No |
| **Sample Percentage** | ✅ Yes (runtime_fraction) | ✅ Yes (split_clients) | ✅ Yes (sample_ratio) | ⚠️  External tool |
| **Mirror Request Body** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️  External tool |
| **Mirror Headers** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️  External tool |
| **Fire-and-Forget** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️  External tool |
| **Production Ready** | ✅ Built-in | ✅ Built-in | ✅ Built-in | ⚠️  SPOE/gor/teeproxy |

**Recommendation:** For request mirroring, use **Envoy**, **Nginx**, or **APISIX** if possible.
If HAProxy is required, integrate **GoReplay** or **SPOE** for production mirroring.

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
