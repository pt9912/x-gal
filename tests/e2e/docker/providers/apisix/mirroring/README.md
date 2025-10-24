# APISIX Request Mirroring E2E Tests

Docker-based end-to-end tests for validating APISIX request mirroring functionality.

## Overview

This test suite validates **Feature 6: Request Mirroring / Traffic Shadowing** for Apache APISIX Gateway using the `proxy-mirror` plugin.

### Test Scenarios

1. **100% Request Mirroring** (`/api/v1`)
   - All requests are mirrored to shadow backend
   - `sample_ratio`: 1.0 (default)
   - Primary responses returned to client
   - Shadow receives duplicate traffic

2. **50% Sampling** (`/api/v2`)
   - Only ~50% of requests are mirrored
   - `sample_ratio`: 0.5
   - Probabilistic sampling
   - Useful for testing with reduced shadow load

3. **No Mirroring (Baseline)** (`/api/v3`)
   - No mirroring configured
   - Only primary backend receives traffic
   - Baseline for comparison

4. **POST Request Mirroring** (`/api/v1`)
   - Validates request body mirroring
   - Shadow receives full request payload
   - Asynchronous (fire-and-forget)

## Architecture

```
Client Request
      |
      v
  APISIX (Port 10003)
      |
      +---> Primary Backend (8080)  [Synchronous Response]
      |
      +---> Shadow Backend (8080)   [Asynchronous Mirror]
```

### Components

- **APISIX Gateway**: Apache APISIX 3.7.0 (Debian)
- **etcd**: Configuration storage (Bitnami etcd 3.5)
- **Primary Backend**: Python HTTP server (returns `X-Backend-Name: primary`)
- **Shadow Backend**: Python HTTP server (receives mirrored traffic)

### Ports

- **10003**: APISIX Proxy (HTTP)
- **9182**: APISIX Admin API
- **8080**: Backend services (internal)

## Prerequisites

```bash
# Docker and Docker Compose
docker --version          # >= 20.10
docker compose version    # >= 2.0

# Python dependencies
pip install pytest requests
```

## Running Tests

### Full Test Suite

```bash
# Run all APISIX mirroring tests
pytest tests/test_apisix_mirroring_e2e.py -v -s

# Run specific test
pytest tests/test_apisix_mirroring_e2e.py::TestAPISIXRequestMirroringE2E::test_100_percent_mirroring -v -s
```

### Manual Testing

```bash
# Start the environment
cd tests/docker/apisix-mirroring
docker compose up -d --build

# Wait for APISIX to be ready (30-60 seconds)
# Check health
curl http://localhost:10003/health

# Generate APISIX config from GAL YAML
python3 -c "
from gal.config import Config
from gal.providers.apisix import APISIXProvider
import json

config = Config.from_yaml('mirroring-config.yaml')
provider = APISIXProvider()
output = provider.generate(config)

with open('/tmp/apisix-mirroring.json', 'w') as f:
    f.write(output)
print('Config generated: /tmp/apisix-mirroring.json')
"

# Deploy config via Admin API
ADMIN_URL="http://localhost:9182"
API_KEY="edd1c9f034335f136f87ad84b625c8f1"

# Upload routes, services, upstreams using Admin API
# (See test_apisix_mirroring_e2e.py fixture for deployment logic)

# Test 100% mirroring
for i in {1..10}; do
  curl -s http://localhost:10003/api/v1 | jq '.backend'
done

# Test 50% mirroring
for i in {1..10}; do
  curl -s http://localhost:10003/api/v2 | jq '.backend'
done

# Test no mirroring
for i in {1..10}; do
  curl -s http://localhost:10003/api/v3 | jq '.backend'
done

# Cleanup
docker compose down -v
```

## APISIX Admin API Examples

```bash
ADMIN_URL="http://localhost:9182"
API_KEY="edd1c9f034335f136f87ad84b625c8f1"

# List all routes
curl -H "X-API-KEY: $API_KEY" $ADMIN_URL/apisix/admin/routes

# Get specific route
curl -H "X-API-KEY: $API_KEY" $ADMIN_URL/apisix/admin/routes/1

# List upstreams
curl -H "X-API-KEY: $API_KEY" $ADMIN_URL/apisix/admin/upstreams

# Check APISIX status
curl http://localhost:10003/health
```

## Configuration Files

### `mirroring-config.yaml`
GAL configuration with 3 routes:
- `/api/v1`: 100% mirroring (`sample_percentage: 100.0`)
- `/api/v2`: 50% mirroring (`sample_percentage: 50.0`)
- `/api/v3`: No mirroring

### `apisix-config.yaml`
APISIX server configuration:
- etcd connection
- Admin API settings
- Logging configuration

### Generated Config
APISIX JSON format with:
- Routes with `proxy-mirror` plugin
- Upstreams (primary + shadow)
- Services

## Expected Results

### Test: `test_100_percent_mirroring`
- ✅ 95+ requests succeed (out of 100)
- ✅ All responses from primary backend
- ✅ `proxy-mirror` plugin configured with `sample_ratio: 1.0`

### Test: `test_50_percent_mirroring_sampling`
- ✅ 95+ requests succeed (out of 100)
- ✅ All responses from primary backend
- ✅ `proxy-mirror` plugin configured with `sample_ratio: 0.5`
- ⚠️  Shadow backend receives ~50% of traffic (not verified in test)

### Test: `test_no_mirroring_baseline`
- ✅ 45+ requests succeed (out of 50)
- ✅ All responses from primary backend
- ✅ No `proxy-mirror` plugin in route config

### Test: `test_post_request_mirroring`
- ✅ 45+ POST requests succeed (out of 50)
- ✅ Request bodies mirrored to shadow
- ✅ Response bodies contain expected data

## APISIX proxy-mirror Plugin

### Plugin Configuration

```json
{
  "proxy-mirror": {
    "host": "http://backend-shadow:8080",
    "path": "/api/v1",
    "sample_ratio": 0.5
  }
}
```

### Features

- ✅ Asynchronous mirroring (fire-and-forget)
- ✅ Sample ratio (0.0 - 1.0)
- ✅ Request body mirroring
- ✅ HTTP/HTTPS support
- ❌ Custom headers (not supported)
- ❌ Multiple mirror targets (only one per route)

### Limitations

1. **Single Mirror Target**: Only one shadow backend per route
2. **No Custom Headers**: Cannot add `X-Mirror: true` to mirrored requests
3. **No Response Validation**: Shadow responses are ignored
4. **Sample Ratio in Range**: Must be between 0.0 and 1.0

## Troubleshooting

### APISIX Not Starting

```bash
# Check logs
docker compose logs apisix
docker compose logs etcd

# Check etcd connectivity
docker compose exec apisix curl http://etcd:2379/health

# Restart
docker compose restart apisix
```

### Routes Not Working

```bash
# Verify routes in Admin API
curl -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  http://localhost:9182/apisix/admin/routes

# Check APISIX error logs
docker compose logs apisix | grep -i error

# Reload configuration
docker compose restart apisix
```

### etcd Connection Issues

```bash
# Check etcd status
docker compose ps etcd

# Test etcd connectivity
docker compose exec apisix curl http://etcd:2379/version

# Reset etcd data
docker compose down -v
docker compose up -d
```

## Related Documentation

- [APISIX proxy-mirror Plugin](https://apisix.apache.org/docs/apisix/plugins/proxy-mirror/)
- [APISIX Admin API](https://apisix.apache.org/docs/apisix/admin-api/)
- [GAL Request Mirroring](../../../docs/guides/APISIX.md#request-mirroring)
- [Test Suite: Envoy Mirroring](../envoy-mirroring/README.md)
- [Test Suite: Nginx Mirroring](../nginx-mirroring/README.md)

## Performance Characteristics

### Mirroring Overhead

- **Primary Latency**: No impact (asynchronous mirroring)
- **APISIX CPU**: +5-10% (mirroring logic)
- **Network**: Double bandwidth (100% mirroring)
- **Shadow Backend**: Must handle mirrored load

### Recommended Settings

- **Production Testing**: Start with 5-10% sampling
- **Staging**: Use 50% sampling
- **Load Testing**: Use 100% mirroring
- **Shadow Timeout**: Independent of primary request

## Test Coverage

| Test | Coverage |
|------|----------|
| 100% Mirroring | ✅ GET requests, response validation |
| 50% Sampling | ✅ Probabilistic mirroring |
| No Mirroring | ✅ Baseline comparison |
| POST Mirroring | ✅ Request body mirroring |
| Admin API | ✅ Route/upstream health |
| Concurrent Requests | ✅ 50 parallel requests |
| Plugin Config | ✅ Verify sample_ratio |

**Total**: 8 test cases covering all mirroring scenarios
