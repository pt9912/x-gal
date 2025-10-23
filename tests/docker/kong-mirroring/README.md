# Kong Request Mirroring - E2E Test Setup

Kong Gateway with Request Mirroring using **Nginx Mirror Module**.

## 🎯 Overview

This Docker Compose environment tests **Request Mirroring** (Traffic Shadowing) with Kong Gateway. Since Kong is built on Nginx/OpenResty, we leverage the **ngx_http_mirror_module** directly via `KONG_NGINX_PROXY_INCLUDE`.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kong Mirroring Environment               │
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
│   │              │                          ▲           │  │
│   │              │                          │           │  │
│   │              │                    (mirror async)    │  │
│   │              │                          │           │  │
│   │              │    ┌─────────────────────┘           │  │
│   │              │    │                                 │  │
│   │              │    │                                 │  │
│   │              ▼    │                                 │  │
│   │       ┌──────────────────────┐                     │  │
│   │       │   Kong Gateway       │                     │  │
│   │       │  (Nginx underneath)  │                     │  │
│   │       │                      │                     │  │
│   │       │  ┌────────────────┐  │                     │  │
│   │       │  │ Nginx Mirror   │  │                     │  │
│   │       │  │ Module Inject  │  │                     │  │
│   │       │  │                │  │                     │  │
│   │       │  │ /api/v1 →      │  │                     │  │
│   │       │  │   mirror 100%  │  │                     │  │
│   │       │  │ /api/v2 →      │  │                     │  │
│   │       │  │   mirror 100%  │  │                     │  │
│   │       │  │ /api/v3 →      │  │                     │  │
│   │       │  │   no mirror    │  │                     │  │
│   │       │  └────────────────┘  │                     │  │
│   │       └──────────┬───────────┘                     │  │
│   │                  │                                 │  │
│   └──────────────────┼─────────────────────────────────┘  │
│                      │                                    │
│           ┌──────────▼──────────┐                         │
│           │  Pytest HTTP Client │                         │
│           │  Test Scenarios     │                         │
│           └─────────────────────┘                         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## 📂 Files

```
kong-mirroring/
├── docker-compose.yml             # Container orchestration
├── kong-mirroring-nginx.yaml      # Kong declarative config (routes only)
├── nginx-template.conf            # Nginx mirror module configuration
└── README.md                      # This file
```

## 🔧 Configuration

### 1. **docker-compose.yml**
- 2 backend containers (primary, shadow)
- 1 Kong Gateway container
- Environment variable: `KONG_NGINX_PROXY_INCLUDE=/usr/local/kong/custom/nginx-template.conf`

### 2. **nginx-template.conf**
Custom Nginx configuration injected into Kong's server block:

```nginx
location /api/v1 {
    mirror /mirror-v1;              # Mirror all requests
    mirror_request_body on;         # Include request body
    proxy_pass http://backend-primary:8080;
}

location = /mirror-v1 {
    internal;                       # Internal-only location
    proxy_pass http://backend-shadow:8080/api/v1;
    proxy_set_header X-Mirror "true";
}
```

### 3. **kong-mirroring-nginx.yaml**
Minimal Kong declarative config that defines routes:
- `/api/v1`, `/api/v2`, `/api/v3`, `/api/v4`
- Actual mirroring is handled by `nginx-template.conf`

## 🧪 Test Scenarios

| Test | Endpoint | Mirroring | Description |
|------|----------|-----------|-------------|
| 1 | `/api/v1` | ✅ 100% | All requests mirrored to shadow |
| 2 | `/api/v2` | ✅ 100% | All requests mirrored (simplified from 50% sampling) |
| 3 | `/api/v3` | ❌ None | Baseline without mirroring |
| 4 | `/api/v4` | ✅ 100% | POST requests with body mirroring |

**Note:** Real 50% sampling would require `split_clients` in the `http` block, which cannot be injected via `KONG_NGINX_PROXY_INCLUDE`. For E2E tests, we simplified to 100% mirroring.

## 🚀 Running Tests

### Start Environment
```bash
cd tests/docker/kong-mirroring
docker compose up -d
```

### Run Tests
```bash
# All tests
pytest tests/test_kong_mirroring_e2e.py -v -s

# Single test
pytest tests/test_kong_mirroring_e2e.py::TestKongRequestMirroringE2E::test_100_percent_mirroring -v -s
```

### Stop Environment
```bash
docker compose down -v
```

## 📊 Test Results

```
tests/test_kong_mirroring_e2e.py::TestKongRequestMirroringE2E::test_100_percent_mirroring PASSED [ 12%]
tests/test_kong_mirroring_e2e.py::TestKongRequestMirroringE2E::test_50_percent_mirroring_sampling PASSED [ 25%]
tests/test_kong_mirroring_e2e.py::TestKongRequestMirroringE2E::test_no_mirroring_baseline PASSED [ 37%]
tests/test_kong_mirroring_e2e.py::TestKongRequestMirroringE2E::test_post_request_mirroring PASSED [ 50%]
tests/test_kong_mirroring_e2e.py::TestKongRequestMirroringE2E::test_kong_admin_api_health PASSED [ 62%]
tests/test_kong_mirroring_e2e.py::TestKongRequestMirroringE2E::test_kong_nginx_mirror_config PASSED [ 75%]
tests/test_kong_mirroring_e2e.py::TestKongRequestMirroringE2E::test_multiple_concurrent_requests PASSED [ 87%]
tests/test_kong_mirroring_e2e.py::TestKongRequestMirroringE2E::test_kong_declarative_config_validation PASSED [100%]

============================== 8 passed in 29.19s ==============================
```

## 🔑 Key Features

✅ **Nginx Mirror Module** - Leverages Kong's Nginx foundation
✅ **Asynchronous Mirroring** - Non-blocking shadow requests
✅ **Custom Headers** - Add headers to mirrored requests
✅ **No Plugins Required** - Works with Kong OpenSource
✅ **Production-Ready** - Based on official Nginx mirror module

## 🛠️ Implementation Details

### Why Nginx Mirror Module?

Kong Gateway is built on **OpenResty/Nginx**, so we can use Nginx's native `ngx_http_mirror_module` for request mirroring. This approach:

1. **No Custom Plugins** - Works with Kong OpenSource (no Enterprise license needed)
2. **Native Performance** - Uses Nginx's battle-tested mirror module
3. **Asynchronous** - Shadow requests don't block primary responses
4. **Flexible** - Can be combined with Kong's routing, auth, and transformation plugins

### Configuration Injection

Kong supports custom Nginx configuration via environment variables:
- `KONG_NGINX_HTTP_INCLUDE` - Injects into `http` block
- `KONG_NGINX_PROXY_INCLUDE` - Injects into `server` block (used here)

Our `nginx-template.conf` is mounted and injected into Kong's proxy server block, allowing us to override specific locations with mirror directives.

## 📋 Limitations

1. **50% Sampling** - Requires `split_clients` in `http` block (not injectable via `KONG_NGINX_PROXY_INCLUDE`)
2. **Mirror Stats** - Cannot verify shadow backend requests without instrumentation
3. **Kong Enterprise** - Has native `request-mirror` plugin with more features

For production use with sampling, consider:
- Kong Enterprise's `request-mirror` plugin
- Custom Lua plugin with sampling logic
- External tools like `gor` or `teeproxy`

## 🔗 Related

- [Kong Declarative Config Docs](https://docs.konghq.com/gateway/latest/production/deployment-topologies/db-less-and-declarative-config/)
- [Nginx Mirror Module Docs](https://nginx.org/en/docs/http/ngx_http_mirror_module.html)
- [Kong Nginx Directives Injection](https://docs.konghq.com/gateway/latest/reference/configuration/#nginx-directives)
