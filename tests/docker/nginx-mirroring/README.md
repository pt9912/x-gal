# Nginx Request Mirroring E2E Tests

Docker-based end-to-end tests for **Feature 6: Request Mirroring / Traffic Shadowing** with Nginx.

## Overview

These tests verify that Nginx correctly implements request mirroring (traffic shadowing) functionality, where incoming requests are:
- Proxied to the **primary backend** (production traffic)
- Simultaneously **mirrored** to a **shadow backend** (for testing, debugging, or analysis)

The shadow backend receives a copy of the request but its response is **ignored** - the client only receives the response from the primary backend.

## Test Scenarios

### 1. 100% Mirroring (`/api/v1`)
- **All requests** to `/api/v1` are mirrored to the shadow backend
- Uses Nginx's `mirror` directive with `mirror_request_body on`
- Verifies primary backend returns all responses

### 2. 50% Sampling (`/api/v2`)
- **~50% of requests** to `/api/v2` are mirrored (sampling)
- Uses Nginx's `split_clients` directive for probabilistic mirroring
- Useful for reducing load on shadow backend

### 3. No Mirroring (`/api/v3`)
- **Baseline route** with no mirroring configured
- All traffic goes to primary backend only

## Architecture

```
Client Request
     │
     ├─────────> Nginx Proxy (Port 10002)
     │                 │
     │                 ├──────> Primary Backend (Port 8080)
     │                 │             │
     │                 │             └──> Response to Client ✅
     │                 │
     │                 └─(mirror)─> Shadow Backend (Port 8080)
     │                                    │
     │                                    └──> Response ignored ❌
```

## Files

- **`docker-compose.yml`** - Docker Compose configuration for 3 services:
  - `backend-primary` - Primary production backend
  - `backend-shadow` - Shadow backend (receives mirrored traffic)
  - `nginx` - Nginx proxy with mirroring enabled

- **`nginx-mirroring.conf`** - Nginx configuration with:
  - `/api/v1` - 100% mirroring
  - `/api/v2` - 50% sampling with `split_clients`
  - `/api/v3` - No mirroring (baseline)
  - `/mirror_shadow` - Internal location for mirroring

- **`mirroring-config.yaml`** - GAL configuration for mirroring (reference)

## Running the Tests

### Prerequisites

```bash
# Install dependencies
pip install pytest requests

# Ensure Docker and Docker Compose are installed
docker --version
docker compose version
```

### Run Tests

```bash
# Run Nginx mirroring tests
pytest tests/test_nginx_mirroring_e2e.py -v -s

# Run specific test
pytest tests/test_nginx_mirroring_e2e.py::TestNginxRequestMirroringE2E::test_100_percent_mirroring -v -s
```

### Manual Testing

```bash
# Start environment
cd tests/docker/nginx-mirroring
docker compose up -d

# Wait for health checks
sleep 5

# Test 100% mirroring (all requests mirrored)
for i in {1..10}; do
  curl -s http://localhost:10002/api/v1 | jq '.backend'
done
# Output: "primary" (10 times)

# Test 50% sampling (approximately half mirrored)
for i in {1..10}; do
  curl -s http://localhost:10002/api/v2 | jq '.backend'
done
# Output: "primary" (10 times - shadow receives ~50% as mirrors)

# Test no mirroring (baseline)
for i in {1..10}; do
  curl -s http://localhost:10002/api/v3 | jq '.backend'
done
# Output: "primary" (10 times - no mirroring)

# Check Nginx logs
docker compose logs nginx

# Check shadow backend received mirrors
docker compose logs backend-shadow | grep "GET /api"

# Stop environment
docker compose down -v
```

## Test Coverage

The E2E test suite (`test_nginx_mirroring_e2e.py`) includes:

1. ✅ **100% Mirroring** - Verifies all requests to `/api/v1` return from primary
2. ✅ **50% Sampling** - Verifies requests to `/api/v2` with probabilistic mirroring
3. ✅ **No Mirroring** - Baseline test for `/api/v3` without mirroring
4. ✅ **POST Requests** - Verifies POST request bodies are mirrored correctly
5. ✅ **Backend Health** - Checks both backends are reachable
6. ✅ **Mirror Headers** - Custom headers (`X-Mirror`, `X-Shadow-Version`) added
7. ✅ **Concurrent Requests** - 50 concurrent requests handled correctly
8. ✅ **Config Verification** - Nginx configuration syntax validation

## Nginx Mirroring Implementation

### Key Nginx Directives

```nginx
# 100% Mirroring
location /api/v1 {
    mirror /mirror_shadow;         # Mirror to internal location
    mirror_request_body on;        # Include request body
    proxy_pass http://primary_backend;
}

# Internal mirror location
location = /mirror_shadow {
    internal;
    proxy_pass http://shadow_backend$request_uri;
    proxy_set_header X-Mirror "true";
}

# 50% Sampling
split_clients "$remote_addr$request_uri" $mirror_v2_sample {
    50%     1;
    *       0;
}

location /api/v2 {
    if ($mirror_v2_sample = "1") {
        set $do_mirror 1;
    }
    mirror /mirror_shadow;
    mirror_request_body on;
    proxy_pass http://primary_backend;
}
```

### Nginx Mirroring Characteristics

- **Asynchronous**: Mirrored requests don't block client responses
- **Fire-and-Forget**: Shadow responses are ignored (not returned to client)
- **Request Body**: `mirror_request_body on` mirrors POST/PUT bodies
- **Headers**: Custom headers can be added to mirrored requests
- **Sampling**: Use `split_clients` for probabilistic mirroring

## Limitations

### Nginx vs Envoy Mirroring

| Feature | Nginx | Envoy |
|---------|-------|-------|
| **Stats/Metrics** | ❌ No built-in stats for mirrored requests | ✅ Full stats via admin API |
| **Sampling** | ⚠️ Requires `split_clients` workaround | ✅ Native `runtime_fraction` |
| **Percentage Control** | ⚠️ Granularity limited (10%, 25%, 50%) | ✅ Fine-grained (1-100%) |
| **Mirror Count** | ✅ Trackable via shadow backend logs | ✅ Trackable via Envoy stats |
| **Headers** | ✅ Custom headers supported | ✅ Custom headers supported |
| **Body Mirroring** | ✅ `mirror_request_body on` | ✅ Default behavior |

### Verification Challenges

- **Cannot verify exact mirror count** without instrumenting shadow backend (no Nginx stats)
- **50% sampling** is probabilistic - actual rate may vary per request pattern
- **Shadow responses ignored** - must check logs or add instrumentation to verify delivery

## Troubleshooting

### Nginx not starting

```bash
# Check logs
docker compose logs nginx

# Verify config syntax
docker compose exec nginx nginx -t

# Check port conflicts
sudo lsof -i :10002
```

### Requests failing

```bash
# Check backend health
docker compose ps

# Test backends directly
docker compose exec backend-primary curl http://localhost:8080/
docker compose exec backend-shadow curl http://localhost:8080/

# Restart services
docker compose restart
```

### Verify mirroring works

```bash
# Watch shadow backend logs in real-time
docker compose logs -f backend-shadow

# Send test requests in another terminal
for i in {1..5}; do
  curl http://localhost:10002/api/v1
  sleep 1
done

# You should see "[SHADOW] GET /api/v1 ..." in logs
```

## Resources

- [Nginx ngx_http_mirror_module](http://nginx.org/en/docs/http/ngx_http_mirror_module.html)
- [Nginx split_clients](http://nginx.org/en/docs/http/ngx_http_split_clients_module.html)
- [GAL Feature 6: Request Mirroring](../../../docs/guides/NGINX_FEATURES.md)
- [Envoy Request Mirroring Tests](../envoy-mirroring/) (comparison)

## Related Tests

- `tests/test_envoy_mirroring_e2e.py` - Envoy mirroring E2E tests
- `tests/test_mirroring_config.py` - Unit tests for mirroring config
- `tests/test_nginx.py` - Nginx provider unit tests
