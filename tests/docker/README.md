# Docker Runtime Tests

End-to-End tests that use **real Docker containers** to verify traffic splitting functionality works in actual gateways.

## Architecture

```
┌─────────────┐
│   Test      │
│  (pytest)   │
└──────┬──────┘
       │
       ├─ docker compose up
       │
       ▼
┌────────────────────────────────────┐
│      Docker Network                │
│                                    │
│  ┌──────────┐    ┌─────────────┐  │
│  │ Backend  │    │   Backend   │  │
│  │ Stable   │    │   Canary    │  │
│  │ (90%)    │    │   (10%)     │  │
│  └────┬─────┘    └─────┬───────┘  │
│       │                │          │
│       └────────┬───────┘          │
│                │                  │
│         ┌──────▼──────┐           │
│         │    Envoy    │           │
│         │   Proxy     │           │
│         │ Port: 10000 │           │
│         └─────────────┘           │
│                                    │
└────────────────────────────────────┘
       ▲
       │
       └─ HTTP Requests (1000x)
```

## Test Scenarios

### 1. Envoy Traffic Splitting (tests/docker/envoy/)

**Config:** 90% Stable, 10% Canary

**Tests:**
- `test_traffic_distribution_90_10`: Sends 1000 requests, verifies 90/10 ± 5% distribution
- `test_backend_responses`: Verifies backend responses are correct
- `test_envoy_admin_stats`: Verifies Envoy admin API shows traffic stats

**Results:**
```
Stable: 905 requests (90.5%) ✅
Canary: 95 requests (9.5%)   ✅
Failed: 0 requests           ✅
```

## Running Tests

### Prerequisites

1. **Docker installed:**
   ```bash
   docker --version  # Should be >= 20.10
   ```

2. **Python dependencies:**
   ```bash
   pip install pytest requests
   ```

### Run Tests

**Run all Docker runtime tests:**
```bash
pytest tests/test_docker_runtime.py -v -s
```

**Run specific test:**
```bash
pytest tests/test_docker_runtime.py::TestEnvoyTrafficSplitRuntime::test_traffic_distribution_90_10 -v -s
```

**Manual Docker Compose:**
```bash
cd tests/docker/envoy
docker compose up --build

# In another terminal:
curl http://localhost:10000/api/v1
curl http://localhost:9901/stats  # Envoy admin
```

## Directory Structure

```
tests/docker/
├── README.md                    # This file
├── backends/
│   ├── Dockerfile              # Backend container image
│   ├── stable.py               # Stable backend (returns "stable")
│   └── canary.py               # Canary backend (returns "canary")
├── envoy/
│   ├── docker-compose.yml      # Envoy + Backends setup
│   └── envoy.yaml              # Generated Envoy config (90/10 split)
└── nginx/                      # (Future: Nginx tests)
    ├── docker-compose.yml
    └── nginx.conf
```

## Backend Mock Servers

Both backends are simple Python HTTP servers that:
- Listen on port 8080
- Return JSON with `{"backend": "stable|canary"}`
- Set HTTP header `X-Backend-Name: stable|canary`

This allows easy verification of which backend handled each request.

## Test Tolerance

Traffic distribution tests allow **±5% tolerance**:
- 90% target → Accept 850-950 requests (85%-95%)
- 10% target → Accept 50-150 requests (5%-15%)

This accounts for statistical variance in random load balancing.

## Troubleshooting

**Ports already in use:**
```bash
# Check what's using port 10000
lsof -i :10000

# Or change port in docker-compose.yml
```

**Containers not starting:**
```bash
cd tests/docker/envoy
docker compose logs
```

**Cleanup stuck containers:**
```bash
cd tests/docker/envoy
docker compose down -v
docker system prune
```

## Adding New Providers

To add runtime tests for another provider (e.g., Nginx):

1. **Generate config:**
   ```python
   config = Config.from_yaml('examples/traffic-split-example.yaml')
   nginx_config = NginxProvider().generate(config)
   ```

2. **Create docker-compose.yml:**
   ```yaml
   services:
     nginx:
       image: nginx:alpine
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf:ro
       ports:
         - "8080:8080"
   ```

3. **Add test class:**
   ```python
   class TestNginxTrafficSplitRuntime:
       def test_traffic_distribution_90_10(self):
           # ... similar to Envoy test
   ```

## CI/CD Integration

**GitHub Actions:**
```yaml
- name: Run Docker Runtime Tests
  run: |
    pytest tests/test_docker_runtime.py -v
  env:
    DOCKER_BUILDKIT: 1
```

**GitLab CI:**
```yaml
test_docker:
  image: docker:latest
  services:
    - docker:dind
  script:
    - pytest tests/test_docker_runtime.py -v
```

## Performance

**Test Duration:**
- Build images: ~10-15s (cached: ~2s)
- Container startup: ~5-10s
- 1000 requests: ~10-15s
- Cleanup: ~2-3s
- **Total: ~30-40s per test class**

## Future Enhancements

- [ ] Add Nginx runtime tests
- [ ] Add Kong runtime tests
- [ ] Add HAProxy runtime tests
- [ ] Test header-based routing
- [ ] Test cookie-based routing
- [ ] Test multi-target splits (70/20/10)
- [ ] Kubernetes-based tests (minikube/kind)
- [ ] Performance benchmarks (latency P50/P95/P99)
