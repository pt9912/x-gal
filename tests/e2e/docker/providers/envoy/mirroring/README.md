# Envoy Request Mirroring E2E Tests

End-to-End tests for **Request Mirroring** (Traffic Shadowing) with Envoy.

## 🎯 Feature

**Feature 6: Request Mirroring / Traffic Shadowing**

Tests verify that Envoy correctly mirrors (shadows) production traffic to a separate backend for testing, debugging, or comparison purposes.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Environment                         │
│                                                             │
│  ┌──────────────┐         ┌──────────────────────┐         │
│  │   Pytest     │────────▶│  Docker Compose      │         │
│  │  Test Suite  │         │  up -d --build       │         │
│  └──────────────┘         └──────────┬───────────┘         │
│                                      │                      │
│                    ┌─────────────────▼──────────────┐       │
│                    │   Docker Network (Isolated)    │       │
│                    │                                │       │
│   ┌────────────────┼────────────────────────────────┼────┐  │
│   │                │                                │    │  │
│   │  ┌─────────────▼─────────┐  ┌─────────────────▼──┐ │  │
│   │  │  Backend Primary      │  │  Backend Shadow    │ │  │
│   │  │  (Python HTTP Server) │  │  (Python HTTP)     │ │  │
│   │  │  Port: 8080           │  │  Port: 8080        │ │  │
│   │  │  Returns: "primary"   │  │  Returns: "shadow" │ │  │
│   │  └───────────┬───────────┘  └──────────┬─────────┘ │  │
│   │              │                          │           │  │
│   │              │    Health Checks (✓)     │           │  │
│   │              │                          │           │  │
│   │              │                          │           │  │
│   │              │    ┌─────────────────────┘           │  │
│   │              │    │ Mirrored Requests               │  │
│   │              │    │ (100% or 50% sampling)          │  │
│   │              │    │                                 │  │
│   │              │    │                                 │  │
│   │  ┌───────────▼────▼─────────────┐                  │  │
│   │  │   Envoy Proxy                │                  │  │
│   │  │   Request Mirroring:         │                  │  │
│   │  │   - /api/v1: 100% mirroring  │                  │  │
│   │  │   - /api/v2: 50% mirroring   │                  │  │
│   │  │   - /api/v3: No mirroring    │                  │  │
│   │  └──────────┬───────────────────┘                  │  │
│   │             │                                       │  │
│   │             │ Primary Response Only                 │  │
│   │             │ (Shadow response ignored)             │  │
│   └─────────────┼───────────────────────────────────────┘  │
│                 │                                          │
│      ┌──────────▼──────────┐                               │
│      │  Pytest HTTP Client │                               │
│      │  100-1000 Requests  │                               │
│      │  Verify Mirroring   │                               │
│      └─────────────────────┘                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Components

### 1. Backend Services

**Primary Backend** (`backend-primary`)
- Python HTTP server that handles production traffic
- Returns `{"backend": "primary", ...}`
- Tracks request count: `X-Request-Count` header
- Logs all requests to stdout

**Shadow Backend** (`backend-shadow`)
- Python HTTP server that receives mirrored traffic
- Returns `{"backend": "shadow", ...}`
- Tracks request count independently
- Logs all requests to stdout
- **Response is ignored by Envoy** (fire-and-forget)

### 2. Envoy Proxy

**Configuration:**
- Port 10001: HTTP Proxy
- Port 9902: Admin API

**Routes:**
1. `/api/v1` - 100% mirroring to shadow backend
2. `/api/v2` - 50% sampling (mirroring)
3. `/api/v3` - No mirroring (baseline)

**Mirroring Behavior:**
- Client receives response **only from primary backend**
- Shadow backend response is **ignored** (fire-and-forget)
- Mirrored requests are **async** and don't block primary response
- If shadow backend is down, primary requests continue normally

### 3. Test Suite

**Test File:** `tests/test_envoy_mirroring_e2e.py`

**Test Cases:**
1. `test_100_percent_mirroring` - Verify all requests to `/api/v1` are mirrored
2. `test_50_percent_mirroring_sampling` - Verify ~50% of `/api/v2` requests are mirrored
3. `test_no_mirroring_baseline` - Verify `/api/v3` has no mirroring
4. `test_post_request_mirroring` - Verify POST requests are mirrored with body
5. `test_envoy_cluster_health` - Verify both clusters are healthy
6. `test_envoy_mirroring_stats` - Verify Envoy stats show mirroring activity

## 🚀 Usage

### Run All Tests

```bash
pytest tests/test_envoy_mirroring_e2e.py -v -s
```

### Run Specific Test

```bash
pytest tests/test_envoy_mirroring_e2e.py::TestEnvoyRequestMirroringE2E::test_100_percent_mirroring -v -s
```

### Manual Testing

```bash
# Start environment
cd tests/docker/envoy-mirroring
docker compose up -d --build

# Wait for services to be ready
docker compose ps

# Send test requests
curl -v http://localhost:10001/api/v1  # 100% mirroring
curl -v http://localhost:10001/api/v2  # 50% mirroring
curl -v http://localhost:10001/api/v3  # No mirroring

# Check Envoy stats
curl http://localhost:9902/stats | grep shadow_cluster

# View backend logs
docker compose logs backend-primary
docker compose logs backend-shadow

# Cleanup
docker compose down -v
```

## 📊 Expected Results

### Test 1: 100% Mirroring

```
Request: GET http://localhost:10001/api/v1
Response: {"backend": "primary", ...}
         X-Backend-Name: primary

Shadow Backend Logs:
  [SHADOW] "GET /api/v1 HTTP/1.1" 200 -
```

### Test 2: 50% Mirroring

```
Request: GET http://localhost:10001/api/v2
Response: {"backend": "primary", ...}
         X-Backend-Name: primary

Shadow Backend Logs (approximately 50% of requests):
  [SHADOW] "GET /api/v2 HTTP/1.1" 200 -
```

### Test 3: No Mirroring

```
Request: GET http://localhost:10001/api/v3
Response: {"backend": "primary", ...}
         X-Backend-Name: primary

Shadow Backend Logs:
  (No logs for /api/v3)
```

### Envoy Stats

```bash
curl http://localhost:9902/stats | grep shadow_cluster

# Expected output:
cluster.shadow_cluster.upstream_rq_total: 50
cluster.shadow_cluster.upstream_rq_completed: 50
cluster.shadow_cluster.upstream_rq_2xx: 50
```

## 🧪 Test Verification

The tests verify:

1. **Primary Response Only**: Client always receives response from primary backend
2. **Shadow Traffic**: Envoy admin stats show requests sent to shadow cluster
3. **Sampling Rate**: ~50% of requests mirrored when configured
4. **POST Body Mirroring**: Request body is mirrored for POST/PUT requests
5. **Cluster Health**: Both primary and shadow clusters report healthy status
6. **No Impact on Primary**: Shadow backend failures don't affect primary responses

## 🔍 Troubleshooting

### Containers not starting

```bash
cd tests/docker/envoy-mirroring
docker compose ps
docker compose logs
```

### Requests failing

```bash
# Check Envoy health
curl http://localhost:9902/ready

# Check backend health
curl http://localhost:10001/api/v1
```

### Shadow backend not receiving traffic

```bash
# Check Envoy config
docker compose exec envoy cat /etc/envoy/envoy.yaml

# Check Envoy cluster status
curl http://localhost:9902/clusters | grep shadow_cluster

# Check Envoy stats
curl http://localhost:9902/stats | grep shadow_cluster
```

## 📝 Notes

- Shadow backend responses are **always ignored** (fire-and-forget)
- Mirrored requests are **async** and don't block primary response
- Shadow backend failures **don't affect** primary traffic
- Sampling percentage can be 0-100 (0 = disabled, 100 = all requests)
- Mirroring includes headers and request body by default
- Envoy admin API (port 9902) is used to verify mirroring stats

## 🎯 Use Cases

Request mirroring is useful for:

1. **Testing new versions**: Mirror production traffic to v2 backend before rollout
2. **Debugging**: Compare responses between old and new implementation
3. **Load testing**: Test new backend with real production traffic patterns
4. **Data collection**: Capture production requests for analysis
5. **Regression testing**: Verify new version behaves identically to old version

## 📚 Related Files

- `envoy-mirroring.yaml` - Envoy configuration with request_mirror_policies
- `docker-compose.yml` - Docker Compose setup (verwendet mit `docker compose` V2)
- `mirroring-config.yaml` - GAL configuration for generating Envoy config
- `../backends/primary.py` - Primary backend server
- `../backends/shadow.py` - Shadow backend server
- `../../test_envoy_mirroring_e2e.py` - Pytest test suite
