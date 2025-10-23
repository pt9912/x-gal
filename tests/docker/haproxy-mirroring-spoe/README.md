# HAProxy Request Mirroring with SPOE (Production Example)

**Production-ready HAProxy Request Mirroring** using **SPOE (Stream Processing Offload Engine)** and **spoa-mirror** agent.

This is the **NATIVE HAProxy mirroring solution** for production environments.

---

## 🎯 What This Demonstrates

This directory contains a **complete, production-ready example** of HAProxy request mirroring using:

- ✅ **SPOE (Stream Processing Offload Engine)** - HAProxy's native mirroring mechanism (since 2.0)
- ✅ **spoa-mirror** - Official HAProxy SPOE agent for async request mirroring
- ✅ **Fire-and-forget mirroring** - Primary response not delayed by shadow backend
- ✅ **Sample percentage** - Mirror 100% or sample (e.g., 50%) of traffic
- ✅ **Request body mirroring** - Mirrors POST/PUT bodies (requires `option http-buffer-request`)
- ✅ **Custom headers** - Add mirroring metadata to requests

---

## 🏗️ Architecture

```
Client → HAProxy (Port 10005)
           │
           ├─ SPOE Filter (filter spoe engine mirror)
           │     │
           │     └─ spoa-mirror Agent (Port 12345)
           │           │
           │           └─ Shadow Backend (async, fire-and-forget)
           │
           └─ Primary Backend (synchronous response)
```

**Flow:**

1. Client sends request to HAProxy (`:10005`)
2. HAProxy checks `txn.mirror_enabled` variable
3. If mirroring enabled, SPOE filter sends request to **spoa-mirror agent**
4. **spoa-mirror** asynchronously mirrors request to **shadow backend** (`:8080`)
5. HAProxy immediately forwards request to **primary backend** (no delay)
6. Client receives response from primary backend only

---

## 📦 Components

### 1. **HAProxy 2.9** (`haproxy-spoe.cfg`)
- Frontend with SPOE filter (`filter spoe engine mirror`)
- Backend definitions (primary, shadow)
- ACL-based routing (`/api/v1`, `/api/v2`, `/api/v3`)
- Sample percentage with `rand()` ACL
- Stats endpoint (`:9999`)

### 2. **spoa-mirror Agent** (`haproxytech/spoa-mirror`)
- Official HAProxy SPOE agent for request mirroring
- Listens on port **12345** for SPOE messages from HAProxy
- Mirrors requests to shadow backend (`http://backend-shadow:8080`)
- Fire-and-forget (async, does not block HAProxy)

### 3. **SPOE Configuration** (`spoe-mirror.conf`)
- SPOE agent definition (`spoe-agent mirror-agent`)
- SPOE message definition (`spoe-message mirror-request`)
- Event trigger: `on-frontend-http-request` if `txn.mirror_enabled`
- Request data: method, URI, headers, body

### 4. **Backend Services**
- **Primary Backend** - Production traffic (port 8080)
- **Shadow Backend** - Mirrored traffic (port 8080)

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Ports available: **10005** (HAProxy), **9998** (stats)

### Start the Stack

```bash
cd tests/docker/haproxy-mirroring-spoe
docker compose up -d
```

### Wait for Services to be Healthy

```bash
docker compose ps
```

Expected output:
```
NAME                    STATUS
haproxy-spoe            Up (healthy)
spoa-mirror-agent       Up (healthy)
backend-primary-spoe    Up (healthy)
backend-shadow-spoe     Up (healthy)
```

### Send Test Requests

```bash
# Test /api/v1 - 100% mirroring
for i in {1..10}; do
  curl -s http://localhost:10005/api/v1 | jq -r '.backend'
done
# Expected: 10x "primary" responses (client only sees primary)

# Test /api/v2 - 50% mirroring
for i in {1..20}; do
  curl -s http://localhost:10005/api/v2 | jq -r '.backend'
done
# Expected: 20x "primary" responses (client only sees primary)

# Test /api/v3 - No mirroring (baseline)
for i in {1..5}; do
  curl -s http://localhost:10005/api/v3 | jq -r '.backend'
done
# Expected: 5x "primary" responses
```

### Check Shadow Backend Received Mirrors

```bash
# View shadow backend logs to verify mirrored requests
docker compose logs backend-shadow | grep "Received request"
```

Expected output (for `/api/v1` and `/api/v2`):
```
backend-shadow-spoe | Received request: GET /api/v1
backend-shadow-spoe | Received request: GET /api/v1
backend-shadow-spoe | Received request: GET /api/v2
backend-shadow-spoe | Received request: GET /api/v2
...
```

### View HAProxy Stats

Open in browser:
```
http://localhost:9998/stats
```

Or via CLI:
```bash
curl -s http://localhost:9998/stats;csv | grep backend
```

### Stop the Stack

```bash
docker compose down -v
```

---

## 📊 Configuration Examples

### Example 1: 100% Mirroring (`/api/v1`)

**haproxy-spoe.cfg:**
```haproxy
frontend http_front
    acl is_api_v1 path_beg /api/v1
    http-request set-var(txn.mirror_enabled) bool(true) if is_api_v1
    use_backend api_v1_backend if is_api_v1

backend api_v1_backend
    option http-buffer-request  # Required for POST/PUT body mirroring
    server primary backend-primary:8080 check
```

**spoe-mirror.conf:**
```
spoe-message mirror-request
    args method=method uri=path headers=req.hdrs body=req.body
    event on-frontend-http-request if { var(txn.mirror_enabled) -m bool }
```

### Example 2: 50% Sampling (`/api/v2`)

**haproxy-spoe.cfg:**
```haproxy
frontend http_front
    acl is_api_v2 path_beg /api/v2
    acl mirror_sample_50 rand(50)  # 50% sampling
    http-request set-var(txn.mirror_enabled) bool(true) if is_api_v2 mirror_sample_50
    use_backend api_v2_backend if is_api_v2
```

### Example 3: No Mirroring (`/api/v3`)

**haproxy-spoe.cfg:**
```haproxy
frontend http_front
    acl is_api_v3 path_beg /api/v3
    use_backend api_v3_backend if is_api_v3

backend api_v3_backend
    server primary backend-primary:8080 check
    # No http-buffer-request, no txn.mirror_enabled
```

---

## 🔍 How SPOE Works

### 1. **SPOE Filter in HAProxy**

```haproxy
frontend http_front
    filter spoe engine mirror config /usr/local/etc/haproxy/spoe-mirror.conf
```

This loads the SPOE engine named "mirror" with configuration from `spoe-mirror.conf`.

### 2. **SPOE Message Trigger**

```
spoe-message mirror-request
    event on-frontend-http-request if { var(txn.mirror_enabled) -m bool }
```

SPOE sends message to **spoa-mirror** agent only when `txn.mirror_enabled` is `true`.

### 3. **spoa-mirror Agent**

```bash
spoa-mirror -u http://backend-shadow:8080 -p 12345
```

- Listens on port **12345** for SPOE messages from HAProxy
- Extracts request data (method, URI, headers, body) from SPOE message
- Makes async HTTP request to shadow backend
- Does **not** send response back to HAProxy (fire-and-forget)

### 4. **Request Flow**

```
1. HAProxy receives request → /api/v1
2. ACL matches → is_api_v1
3. Set variable → txn.mirror_enabled = true
4. SPOE filter triggers → on-frontend-http-request
5. SPOE sends message to spoa-mirror (async)
6. HAProxy forwards request to primary backend (no delay!)
7. spoa-mirror sends request to shadow backend (background)
8. Client receives response from primary backend
```

---

## ⚙️ SPOE Configuration Details

### **spoe-mirror.conf** Breakdown

```
[mirror]

# SPOE Agent - Connection to spoa-mirror process
spoe-agent mirror-agent
    messages   mirror-request        # Message types to process
    option     async                 # Fire-and-forget (no response expected)
    option     send-frag-payload     # Support large request bodies
    option     var-prefix mirror     # Prefix for SPOE variables
    timeout    processing 500ms      # Max time for SPOE processing
    maxconnrate 100                  # Rate limiting (100 conn/sec)
    maxerrrate  50                   # Throttle if >50 errors/sec
    use-backend spoe-mirror          # Backend definition in haproxy.cfg

# SPOE Message - What data to send
spoe-message mirror-request
    args method=method \             # HTTP method (GET, POST, etc.)
         uri=path \                  # Request URI
         headers=req.hdrs \          # Request headers
         body=req.body               # Request body (POST/PUT)
    event on-frontend-http-request if { var(txn.mirror_enabled) -m bool }
```

### **haproxy-spoe.cfg** SPOE Backend

```haproxy
backend spoe-mirror
    mode tcp
    server spoe1 spoa-mirror:12345 check
```

This backend connects HAProxy to the **spoa-mirror agent** on port 12345.

---

## 🧪 Testing

### Test 1: Verify Primary Backend Responds

```bash
curl http://localhost:10005/api/v1
```

Expected:
```json
{
  "message": "Hello from primary backend",
  "backend": "primary",
  "path": "/api/v1"
}
```

### Test 2: Verify Shadow Backend Receives Mirrors

```bash
# Send 10 requests
for i in {1..10}; do curl -s http://localhost:10005/api/v1; done

# Check shadow backend logs
docker compose logs backend-shadow | grep "Received request"
```

Expected: 10 log entries showing mirrored requests.

### Test 3: Verify 50% Sampling

```bash
# Send 100 requests to /api/v2
for i in {1..100}; do curl -s http://localhost:10005/api/v2; done

# Count shadow backend requests
docker compose logs backend-shadow | grep "GET /api/v2" | wc -l
```

Expected: ~50 requests (±10 due to randomness).

### Test 4: POST Request with Body

```bash
curl -X POST http://localhost:10005/api/v1 \
  -H "Content-Type: application/json" \
  -d '{"test": "data", "user_id": 123}'
```

Expected:
- Primary backend responds with 200
- Shadow backend logs show POST body received

### Test 5: No Mirroring Baseline

```bash
# Send 10 requests to /api/v3 (no mirroring)
for i in {1..10}; do curl -s http://localhost:10005/api/v3; done

# Check shadow backend logs
docker compose logs backend-shadow | grep "GET /api/v3" | wc -l
```

Expected: **0** requests (no mirroring configured).

---

## 📈 Monitoring

### HAProxy Stats Dashboard

```
http://localhost:9998/stats
```

Metrics to monitor:
- **http_front**: Total requests, errors, rate
- **api_v1_backend**: Primary backend health, response times
- **spoe-mirror**: SPOE backend connection status

### Shadow Backend Request Count

```bash
# Count mirrored requests in last 5 minutes
docker compose logs --since 5m backend-shadow | grep "Received request" | wc -l
```

### SPOE Agent Logs

```bash
docker compose logs spoa-mirror
```

Look for:
- `Listening on :12345` - Agent is running
- `Mirroring request to http://backend-shadow:8080` - Requests being mirrored

---

## 🔧 Troubleshooting

### SPOE Agent Not Connecting

**Error:**
```
haproxy[1]: [ALERT] 123/145623 (1) : backend 'spoe-mirror' has no server available!
```

**Solution:**
```bash
# Check spoa-mirror agent is running
docker compose ps spoa-mirror

# Check spoa-mirror agent logs
docker compose logs spoa-mirror

# Restart spoa-mirror agent
docker compose restart spoa-mirror
```

### Request Bodies Not Mirrored

**Error:** Shadow backend logs show GET requests but no POST body.

**Solution:** Ensure `option http-buffer-request` is enabled in backend:

```haproxy
backend api_v1_backend
    option http-buffer-request  # Required for POST/PUT body mirroring
    server primary backend-primary:8080 check
```

**Warning:** This buffers the entire request body in memory. Limit body size to prevent memory issues:

```haproxy
# Limit request body to 1MB
acl body_too_large req.body_size gt 1048576
http-request deny if body_too_large
```

### Shadow Backend Not Receiving Requests

**Check 1:** Verify `txn.mirror_enabled` is set

```haproxy
# Debug: Log mirroring status
http-request set-header X-Mirror-Debug "%[var(txn.mirror_enabled)]"
```

**Check 2:** Verify SPOE filter is loaded

```bash
docker compose exec haproxy haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg
```

Look for: `Configuration file is valid`

**Check 3:** Verify SPOE message event

```
spoe-message mirror-request
    event on-frontend-http-request if { var(txn.mirror_enabled) -m bool }
```

**Check 4:** View shadow backend logs

```bash
docker compose logs -f backend-shadow
```

### High Latency Due to Mirroring

**Issue:** Primary responses are slow because `option http-buffer-request` buffers body.

**Solutions:**

1. **Disable body mirroring for large requests:**
   ```haproxy
   acl body_too_large req.body_size gt 1048576
   http-request set-var(txn.mirror_enabled) bool(false) if body_too_large
   ```

2. **Mirror only headers (no body):**
   ```
   spoe-message mirror-request
       args method=method uri=path headers=req.hdrs
       # Remove body=req.body
   ```

3. **Increase SPOE timeout:**
   ```
   spoe-agent mirror-agent
       timeout processing 1s  # Increase from 500ms
   ```

---

## 🎯 Production Deployment

### 1. **Use haproxytech/haproxy-enterprise for Production**

```yaml
haproxy:
  image: haproxytech/haproxy-enterprise:2.9
```

### 2. **Enable SPOE Logging**

```
spoe-agent mirror-agent
    log global
```

### 3. **Monitor SPOE Agent Health**

```bash
# Add healthcheck for spoa-mirror
healthcheck:
  test: ["CMD-SHELL", "netstat -an | grep 12345 || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 3
```

### 4. **Rate Limit SPOE to Prevent Overload**

```
spoe-agent mirror-agent
    maxconnrate 100   # Max 100 mirroring requests/sec
    maxerrrate  50    # Throttle if >50 errors/sec
```

### 5. **Use Persistent Connections**

```
spoe-agent mirror-agent
    option pipelining  # Reuse TCP connections
```

### 6. **Deploy spoa-mirror with High Availability**

```yaml
# Run multiple spoa-mirror instances
spoa-mirror-1:
  image: haproxytech/spoa-mirror:latest
  command: ["-u", "http://backend-shadow:8080", "-p", "12345"]

spoa-mirror-2:
  image: haproxytech/spoa-mirror:latest
  command: ["-u", "http://backend-shadow:8080", "-p", "12346"]
```

```haproxy
backend spoe-mirror
    mode tcp
    balance roundrobin
    server spoe1 spoa-mirror-1:12345 check
    server spoe2 spoa-mirror-2:12346 check
```

---

## 📚 Comparison with Other Providers

| Feature | HAProxy (SPOE) | Envoy | Nginx | APISIX |
|---------|----------------|-------|-------|--------|
| **Native Mirroring** | ⚠️ Yes (SPOE, complex) | ✅ Yes (async) | ✅ Yes (mirror) | ✅ Yes (plugin) |
| **Setup Complexity** | 🔴 High (SPOE agent) | 🟢 Low | 🟢 Low | 🟢 Low |
| **Fire-and-Forget** | ✅ Yes (async SPOE) | ✅ Yes | ✅ Yes | ✅ Yes |
| **Sample Percentage** | ✅ Yes (rand() ACL) | ✅ Yes (runtime_fraction) | ✅ Yes (split_clients) | ✅ Yes (sample_ratio) |
| **Mirror Request Body** | ✅ Yes (http-buffer-request) | ✅ Yes | ✅ Yes | ✅ Yes |
| **Mirror Headers** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Production Ready** | ✅ Yes (HAProxy 2.0+) | ✅ Yes | ✅ Yes | ✅ Yes |
| **External Tools** | ⚠️ spoa-mirror required | ❌ None | ❌ None | ❌ None |

**Recommendation:**
- **HAProxy required?** Use SPOE + spoa-mirror (this example)
- **Easier setup?** Use Envoy, Nginx, or APISIX (built-in mirroring)
- **Simple testing/staging?** Use GoReplay (no HAProxy changes)

---

## 🔗 References

- [HAProxy SPOE Documentation](https://www.haproxy.com/documentation/hapee/latest/api/spoe/)
- [spoa-mirror GitHub](https://github.com/haproxy/spoa-mirror)
- [HAProxy Request Mirroring Guide](https://www.haproxy.com/blog/haproxy-traffic-shadowing-mirroring/)
- [GAL Request Mirroring Documentation](../../../docs/guides/REQUEST_MIRRORING.md)

---

## 📝 Notes

- This is a **production-ready example** of HAProxy SPOE mirroring
- For **simpler E2E tests**, see `../haproxy-mirroring/` (tests routing without SPOE)
- For **external mirroring**, consider **GoReplay** (simpler than SPOE)
- **SPOE requires HAProxy 2.0+** and external **spoa-mirror agent**
- **Body mirroring** requires `option http-buffer-request` (memory usage consideration)
