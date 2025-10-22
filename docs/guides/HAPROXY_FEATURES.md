# HAProxy Feature-Implementierungen

**Detaillierte Implementierung aller Features für HAProxy Provider in GAL**

**Navigation:**
- [← Zurück zur HAProxy Übersicht](HAPROXY.md)
- [→ Best Practices & Troubleshooting](HAPROXY_DEPLOYMENT.md)

## Inhaltsverzeichnis

1. [Feature-Implementierungen](#feature-implementierungen)
2. [HAProxy-spezifische Details](#haproxy-spezifische-details)
3. [HAProxy Feature Coverage](#haproxy-feature-coverage)

---
## Feature-Implementierungen

### 1. Load Balancing Algorithmen

HAProxy unterstützt 10+ Load Balancing Algorithmen. GAL implementiert die wichtigsten:

#### Round Robin (Standard)

**Beschreibung:** Gleichmäßige Verteilung über alle Server.

```yaml
load_balancer:
  algorithm: round_robin
```

**HAProxy:**
```haproxy
backend backend_api
    balance roundrobin
    server server1 api-1.internal:8080
    server server2 api-2.internal:8080
```

**Use Case:** Homogene Server mit ähnlicher Kapazität.

#### Least Connections

**Beschreibung:** Wählt Server mit wenigsten aktiven Verbindungen.

```yaml
load_balancer:
  algorithm: least_conn
```

**HAProxy:**
```haproxy
backend backend_api
    balance leastconn
    server server1 api-1.internal:8080
    server server2 api-2.internal:8080
```

**Use Case:** Long-running Requests, ungleiche Request-Dauer.

#### IP Hash (Source)

**Beschreibung:** Konsistente Server-Auswahl basierend auf Client-IP.

```yaml
load_balancer:
  algorithm: ip_hash
```

**HAProxy:**
```haproxy
backend backend_api
    balance source
    server server1 api-1.internal:8080
    server server2 api-2.internal:8080
```

**Use Case:** Session Persistence ohne Cookies.

#### Weighted Load Balancing

**Beschreibung:** Traffic-Verteilung basierend auf Server-Kapazität.

```yaml
targets:
  - host: powerful-server.internal
    port: 8080
    weight: 3  # Erhält 75% des Traffics
  - host: small-server.internal
    port: 8080
    weight: 1  # Erhält 25% des Traffics

load_balancer:
  algorithm: weighted
```

**HAProxy:**
```haproxy
backend backend_api
    balance roundrobin
    server server1 powerful-server.internal:8080 weight 3
    server server2 small-server.internal:8080 weight 1
```

**Use Case:** Heterogene Server mit unterschiedlicher Kapazität.

### 2. Health Checks

#### Active Health Checks

**Beschreibung:** Periodisches Probing der Backend-Server.

```yaml
health_check:
  active:
    enabled: true
    http_path: /health
    interval: "5s"
    timeout: "3s"
    healthy_threshold: 2      # 2 erfolgreiche Checks → gesund
    unhealthy_threshold: 3    # 3 fehlgeschlagene Checks → ungesund
    healthy_status_codes:
      - 200
      - 204
```

**HAProxy:**
```haproxy
backend backend_api
    option httpchk GET /health HTTP/1.1
    http-check expect status 200|204
    
    server server1 api-1.internal:8080 check inter 5s fall 3 rise 2
```

**Parameter:**
- `check`: Aktiviert Health Checks
- `inter 5s`: Check alle 5 Sekunden
- `fall 3`: 3 Fehler → ungesund
- `rise 2`: 2 Erfolge → gesund

#### Passive Health Checks

**Beschreibung:** Überwacht echten Traffic, markiert fehlerhafte Server.

```yaml
health_check:
  passive:
    enabled: true
    max_failures: 5
```

**HAProxy:**
```haproxy
backend backend_api
    server server1 api-1.internal:8080 check fall 5 rise 2
```

**Use Case:** Kombination mit Active Checks für maximale Zuverlässigkeit.

### 3. Rate Limiting

HAProxy verwendet `stick-tables` für Rate Limiting.

#### IP-basiertes Rate Limiting

```yaml
rate_limit:
  enabled: true
  requests_per_second: 100
  burst: 200
  key_type: ip_address
  response_status: 429
```

**HAProxy:**
```haproxy
frontend http_frontend
    # Stick-Table für IP-basierte Rate Limiting
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    
    # Track Client IP
    http-request track-sc0 src if is_route
    
    # Deny wenn > 100 req/s
    http-request deny deny_status 429 if is_route { sc_http_req_rate(0) gt 100 }
```

**Erklärung:**
- `stick-table type ip`: Tabelle pro Client-IP
- `store http_req_rate(10s)`: Request-Rate über 10 Sekunden
- `track-sc0 src`: Trackt Source IP (Client)
- `sc_http_req_rate(0) gt 100`: Prüft ob Rate > 100

#### Header-basiertes Rate Limiting

```yaml
rate_limit:
  enabled: true
  requests_per_second: 1000
  key_type: header
  key_header: X-API-Key
```

**HAProxy:**
```haproxy
frontend http_frontend
    http-request track-sc0 hdr(X-API-Key) if is_route
    http-request deny deny_status 429 if is_route { sc_http_req_rate(0) gt 1000 }
```

**Use Case:** Unterschiedliche Limits pro API-Key/Tenant.

### 4. Header Manipulation

#### Request Headers

```yaml
headers:
  request_add:
    X-Request-ID: "{{uuid}}"
    X-Real-IP: "{{client_ip}}"
  request_set:
    User-Agent: "HAProxy/1.0"
  request_remove:
    - X-Internal-Token
```

**HAProxy:**
```haproxy
frontend http_frontend
    # Add Headers
    http-request set-header X-Request-ID "%[uuid()]" if is_route
    http-request set-header X-Real-IP "%[src]" if is_route
    
    # Set Headers (überschreiben)
    http-request set-header User-Agent "HAProxy/1.0" if is_route
    
    # Remove Headers
    http-request del-header X-Internal-Token if is_route
```

**Template-Variablen:**
- `{{uuid}}` → `%[uuid()]`: Eindeutige Request-ID
- `{{now}}` → `%[date()]`: ISO8601 Timestamp

#### Response Headers

```yaml
headers:
  response_add:
    X-Frame-Options: "DENY"
    X-Content-Type-Options: "nosniff"
  response_set:
    Server: "HAProxy"
  response_remove:
    - X-Powered-By
```

**HAProxy:**
```haproxy
frontend http_frontend
    # Add Response Headers
    http-response set-header X-Frame-Options "DENY" if is_route
    http-response set-header X-Content-Type-Options "nosniff" if is_route
    
    # Set Response Headers
    http-response set-header Server "HAProxy" if is_route
    
    # Remove Response Headers
    http-response del-header X-Powered-By if is_route
```

### 5. CORS Configuration

HAProxy unterstützt CORS durch Response-Header.

```yaml
cors:
  enabled: true
  allowed_origins:
    - "https://app.example.com"
  allowed_methods:
    - GET
    - POST
    - PUT
    - DELETE
  allowed_headers:
    - Content-Type
    - Authorization
  allow_credentials: true
  max_age: 86400
```

**HAProxy:**
```haproxy
frontend http_frontend
    http-response set-header Access-Control-Allow-Origin "https://app.example.com" if is_route
    http-response set-header Access-Control-Allow-Methods "GET, POST, PUT, DELETE" if is_route
    http-response set-header Access-Control-Allow-Headers "Content-Type, Authorization" if is_route
    http-response set-header Access-Control-Allow-Credentials "true" if is_route
    http-response set-header Access-Control-Max-Age "86400" if is_route
```

**Hinweis:** Preflight OPTIONS Requests müssen ggf. manuell behandelt werden.

### 6. Sticky Sessions

#### Cookie-basierte Persistence

```yaml
load_balancer:
  sticky_sessions: true
  cookie_name: "SERVERID"
```

**HAProxy:**
```haproxy
backend backend_api
    cookie SERVERID insert indirect nocache
    
    server server1 api-1.internal:8080 cookie server1
    server server2 api-2.internal:8080 cookie server2
```

**Erklärung:**
- `cookie SERVERID insert`: Fügt Cookie hinzu
- `indirect`: Cookie nur zwischen Client und HAProxy
- `nocache`: Verhindert Caching
- `cookie server1`: Server-spezifischer Cookie-Wert

#### Source IP-basierte Persistence

```yaml
load_balancer:
  algorithm: ip_hash
```

**HAProxy:**
```haproxy
backend backend_api
    balance source
```

**Use Case:** Wenn Cookies nicht möglich (z.B. native Apps).

### 7. Traffic Splitting & Canary Deployments

**Feature:** Gewichtsbasierte Traffic-Verteilung für A/B Testing, Canary Deployments und Blue/Green Deployments.

**Status:** ✅ **Vollständig unterstützt** (seit v1.4.0)

HAProxy unterstützt Traffic Splitting nativ über **Server Weights** mit `balance roundrobin`.

#### Canary Deployment (90/10 Split)

**Use Case:** Neue Version vorsichtig ausrollen (10% Canary, 90% Stable).

```yaml
routes:
  - path_prefix: /api/v1
    traffic_split:
      enabled: true
      targets:
        - name: stable
          weight: 90
          upstream:
            host: backend-stable
            port: 8080
        - name: canary
          weight: 10
          upstream:
            host: backend-canary
            port: 8080
```

**HAProxy Config:**
```haproxy
backend backend_api_v1
    balance roundrobin
    option httpclose
    option forwardfor

    # 90% Stable, 10% Canary
    server server_stable backend-stable:8080 check inter 10s fall 3 rise 2 weight 90
    server server_canary backend-canary:8080 check inter 10s fall 3 rise 2 weight 10
```

**Erklärung:**
- `balance roundrobin`: Round-Robin-Verteilung mit Gewichtung
- `weight 90`: Stable Backend erhält 90% des Traffics
- `weight 10`: Canary Backend erhält 10% des Traffics
- `check inter 10s`: Health Check alle 10 Sekunden

#### A/B Testing (50/50 Split)

**Use Case:** Zwei Versionen gleichwertig testen.

```yaml
traffic_split:
  enabled: true
  targets:
    - name: version_a
      weight: 50
      upstream:
        host: api-v2-a
        port: 8080
    - name: version_b
      weight: 50
      upstream:
        host: api-v2-b
        port: 8080
```

**HAProxy Config:**
```haproxy
backend backend_ab_testing
    balance roundrobin

    server version_a api-v2-a:8080 check weight 50
    server version_b api-v2-b:8080 check weight 50
```

#### Blue/Green Deployment

**Use Case:** Instant Switch zwischen zwei Environments (100% → 0%).

```yaml
traffic_split:
  enabled: true
  targets:
    - name: blue
      weight: 0    # Aktuell inaktiv
      upstream:
        host: api-blue
        port: 8080
    - name: green
      weight: 100  # Aktuell aktiv
      upstream:
        host: api-green
        port: 8080
```

**Deployment-Strategie:**
1. **Initial:** Blue = 100%, Green = 0%
2. **Deploy neue Version** auf Green Environment
3. **Test Green** ausgiebig
4. **Switch:** Blue = 0%, Green = 100% (Re-Generate haproxy.cfg, reload)
5. **Rollback** bei Problemen: Green = 0%, Blue = 100%

#### Gradual Rollout (5% → 25% → 50% → 100%)

**Use Case:** Schrittweise Migration mit Monitoring.

**Phase 1: 5% Canary**
```yaml
targets:
  - {name: stable, weight: 95, upstream: {host: api-stable, port: 8080}}
  - {name: canary, weight: 5, upstream: {host: api-canary, port: 8080}}
```

**Phase 2: 25% Canary** (nach Monitoring)
```yaml
targets:
  - {name: stable, weight: 75, upstream: {host: api-stable, port: 8080}}
  - {name: canary, weight: 25, upstream: {host: api-canary, port: 8080}}
```

**Phase 3: 50% Canary** (Confidence-Build)
```yaml
targets:
  - {name: stable, weight: 50, upstream: {host: api-stable, port: 8080}}
  - {name: canary, weight: 50, upstream: {host: api-canary, port: 8080}}
```

**Phase 4: 100% Canary** (Full Migration)
```yaml
targets:
  - {name: canary, weight: 100, upstream: {host: api-canary, port: 8080}}
```

#### HAProxy Traffic Splitting Features

| Feature | HAProxy Support | Implementation |
|---------|----------------|----------------|
| **Weight-based Splitting** | ✅ Native | `server ... weight N` |
| **Health Checks** | ✅ Native | `check inter Ns fall N rise N` |
| **Sticky Sessions** | ✅ Native | `cookie NAME insert` |
| **Dynamic Weights** | ⚠️ Runtime API | HAProxy Runtime API (socat/socket) |
| **Header-based Routing** | ⚠️ ACLs | Via `http-request set-header` + ACLs |
| **Cookie-based Routing** | ⚠️ ACLs | Via `hdr(cookie)` ACLs |

**Best Practices:**
- **Start Small:** Begin mit 5-10% Canary Traffic
- **Monitor Metrics:** Error Rate, Latency, Throughput auf beiden Targets
- **Health Checks:** Immer aktivieren für automatisches Failover
- **Gradual Increase:** 5% → 25% → 50% → 100% über mehrere Tage
- **Rollback Plan:** Schnelles Zurücksetzen via Config Reload (`systemctl reload haproxy`)

**Docker E2E Test Results:**
```bash
# Test: 1000 Requests mit 90/10 Split
Stable Backend:  900 requests (90.0%) ✅
Canary Backend:  100 requests (10.0%) ✅
Failed Requests: 0 (0.0%)
```

**Siehe auch:**
- [Traffic Splitting Guide](TRAFFIC_SPLITTING.md) - Vollständige Dokumentation
- [examples/traffic-split-example.yaml](https://github.com/pt9912/x-gal/blob/develop/examples/traffic-split-example.yaml) - 6 Beispiel-Szenarien
- [tests/docker/haproxy/](../../tests/docker/haproxy/) - Docker Compose E2E Tests

### 8. Request Mirroring

✅ **Native Support: http-request mirror (HAProxy 2.4+)**

HAProxy 2.4+ unterstützt Request Mirroring nativ mit der `http-request mirror` Directive.

**GAL Config:**
```yaml
routes:
  - path_prefix: /api/users
    mirroring:
      enabled: true
      targets:
        - name: shadow-v2
          upstream:
            host: shadow.example.com
            port: 443
          sample_percentage: 50
          timeout: 5
          headers:
            X-Mirror: "true"
            X-Shadow-Version: "v2"
```

**Generiert (HAProxy 2.4+):**
```haproxy
# Mirror Backend
backend shadow-v2_mirror
    server mirror1 shadow.example.com:443 check

# Frontend
frontend http_front
    bind *:80
    default_backend user_backend

# Primary Backend mit Mirroring
backend user_backend
    # Sample Percentage via ACL (50%)
    acl mirror_sample rand(100) lt 50
    http-request mirror shadow-v2_mirror if mirror_sample

    # Original Backend
    server srv1 backend.example.com:443 check
```

**Generiert (HAProxy < 2.4 - Lua Workaround):**
```haproxy
# Global section: Load Lua script
global
    lua-load /etc/haproxy/lua/mirror.lua

backend user_backend
    # Call Lua function for mirroring
    http-request lua.mirror_request

    server srv1 backend.example.com:443 check
```

**Lua Script (/etc/haproxy/lua/mirror.lua):**
```lua
-- mirror.lua - Request Mirroring für HAProxy <2.4
core.register_action("mirror_request", { "http-req" }, function(txn)
    local http = require("socket.http")

    -- Sample percentage check (50%)
    if math.random(100) <= 50 then
        -- Fire-and-forget HTTP request
        http.request{
            url = "https://shadow.example.com:443" .. txn.f:path(),
            method = txn.f:method(),
            headers = {
                ["X-Mirror"] = "true",
                ["X-Shadow-Version"] = "v2"
            }
        }
    end
end)
```

**Hinweise:**
- ✅ **HAProxy 2.4+**: Native `http-request mirror` Directive
- ⚠️ **HAProxy <2.4**: Lua-Script-Workaround erforderlich
- ✅ Sample Percentage via `acl mirror_sample rand(100) lt 50`
- ✅ Custom Headers via Lua oder HAProxy http-request set-header
- ✅ Multiple Mirror Targets möglich

**Deployment:**
```bash
# HAProxy Version prüfen
haproxy -v

# HAProxy 2.4+ (natives Mirroring)
gal generate -c config.yaml -p haproxy -o haproxy.cfg
haproxy -f haproxy.cfg -c  # Validate
systemctl reload haproxy

# HAProxy <2.4 (Lua Workaround)
# 1. Lua-Script installieren
mkdir -p /etc/haproxy/lua
cp mirror.lua /etc/haproxy/lua/

# 2. Config generieren & deployen
gal generate -c config.yaml -p haproxy -o haproxy.cfg
haproxy -f haproxy.cfg -c
systemctl reload haproxy
```

**Monitoring:**
```bash
# Mirror Backend Status
echo "show stat" | socat stdio /var/run/haproxy.sock | grep shadow-v2_mirror

# Request Counters
echo "show info" | socat stdio /var/run/haproxy.sock | grep Requests
```

> **Vollständige Dokumentation:** Siehe [Request Mirroring Guide](REQUEST_MIRRORING.md#4-haproxy-native-24)

---

## HAProxy-spezifische Details

### haproxy.cfg Struktur

Eine generierte `haproxy.cfg` besteht aus 4 Hauptsektionen:

```haproxy
# 1. Global Settings
global
    log         127.0.0.1 local0
    chroot      /var/lib/haproxy
    pidfile     /var/run/haproxy.pid
    maxconn     4000
    user        haproxy
    group       haproxy
    daemon
    stats socket /var/lib/haproxy/stats level admin

# 2. Defaults (für alle Frontends/Backends)
defaults
    mode                    http
    log                     global
    option                  httplog
    option                  dontlognull
    option                  http-server-close
    option                  forwardfor except 127.0.0.0/8
    option                  redispatch
    retries                 3
    timeout http-request    30s
    timeout queue           30s
    timeout connect         5s
    timeout client          30s
    timeout server          30s
    timeout http-keep-alive 10s
    timeout check           5s
    maxconn                 3000

# 3. Frontend (Eingehende Requests)
frontend http_frontend
    bind 0.0.0.0:80
    
    # ACLs für Routing
    acl is_api path_beg /api
    
    # Rate Limiting
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    
    # Backend Routing
    use_backend backend_api if is_api

# 4. Backend (Upstream Services)
backend backend_api
    balance roundrobin
    option httpchk GET /health HTTP/1.1
    
    server server1 api-1.internal:8080 check
    server server2 api-2.internal:8080 check
```

### ACLs (Access Control Lists)

GAL generiert automatisch ACLs für Routing:

```haproxy
# Pfad-basiert
acl is_api_route0 path_beg /api

# Methoden-basiert
acl is_api_method method GET POST

# Kombiniert
use_backend backend_api if is_api_route0 is_api_method
```

**Wichtige ACL Typen:**
- `path_beg`: Pfad beginnt mit
- `path_end`: Pfad endet mit
- `path_reg`: Pfad Regex Match
- `hdr(name)`: Header-Wert
- `method`: HTTP Methode

### Stats Page & Runtime API

HAProxy bietet eine integrierte Stats Page und Runtime API:

```haproxy
global
    stats socket /var/lib/haproxy/stats level admin
    stats timeout 30s

# Optional: Web UI Stats Page
listen stats
    bind *:8080
    stats enable
    stats uri /haproxy-stats
    stats refresh 30s
    stats admin if TRUE
```

**Zugriff:**
- Web UI: `http://localhost:8080/haproxy-stats`
- Runtime API: `echo "show info" | socat /var/lib/haproxy/stats -`

### Logging

HAProxy loggt standardmäßig via syslog:

```haproxy
global
    log 127.0.0.1 local0
    log 127.0.0.1 local1 notice

defaults
    log     global
    option  httplog
```

**Syslog Konfiguration (rsyslog):**
```bash
# /etc/rsyslog.d/haproxy.conf
$ModLoad imudp
$UDPServerRun 514

local0.* /var/log/haproxy/access.log
local1.* /var/log/haproxy/errors.log
```

**Log-Format:**
```
Nov 18 12:34:56 localhost haproxy[1234]: 192.168.1.100:54321 [18/Nov/2025:12:34:56.789] http_frontend backend_api/server1 0/0/1/2/3 200 1234 - - ---- 1/1/0/0/0 0/0 "GET /api/users HTTP/1.1"
```

---

## Provider-Vergleich

### Feature-Matrix: HAProxy vs. andere Provider

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | **HAProxy** |
|---------|-------|------|--------|---------|-------|-------------|
| **Load Balancing** |
| Round Robin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Least Connections | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| IP Hash | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (source) |
| Weighted | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Health Checks** |
| Active HTTP | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Active TCP | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Passive | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| **Security** |
| Basic Auth | ⚠️ Lua | ✅ | ✅ | ✅ | ✅ | ✅ ACL |
| JWT Auth | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ Lua |
| API Key | ⚠️ Lua | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ ACL |
| Headers | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CORS | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| **Traffic Management** |
| Rate Limiting | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Sticky Sessions | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Circuit Breaker | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ |
| **Performance** |
| RPS (100k+) | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ |
| Memory Usage | Medium | High | Medium | Low | Low | **Very Low** |
| CPU Usage | Medium | High | Medium | Low | Low | **Very Low** |

**Legende:**
- ✅ Full: Vollständig unterstützt
- ⚠️ Limited: Eingeschränkt oder zusätzliche Module erforderlich
- ❌ Not Supported: Nicht verfügbar

### Wann HAProxy wählen?

**✅ Ideal für:**
- **Extreme Performance-Anforderungen**: 100k+ RPS
- **Low Resource Usage**: Minimale CPU/RAM
- **Layer 4 & 7 Load Balancing**: TCP + HTTP
- **Enterprise Production**: Höchste Zuverlässigkeit
- **Complex Routing**: ACL-basiertes Routing
- **Stats & Monitoring**: Integrierte Stats Page

**⚠️ Limitierungen:**
- **Kein natives JWT**: Benötigt Lua
- **Limitierte CORS**: Nur via Headers
- **Statische Konfiguration**: Reload erforderlich
- **Weniger Plugins**: Kein Plugin-Ökosystem wie Kong

**Alternativen:**
- **Nginx**: Einfacher, aber weniger Features für LB
- **Traefik**: Dynamic Configuration, gute Docker Integration
- **Envoy**: Moderne Service Mesh Integration
- **Kong/APISIX**: Volles API Gateway mit Plugins

---

## HAProxy Feature Coverage

Detaillierte Analyse basierend auf der [offiziellen HAProxy Dokumentation](https://docs.haproxy.org/).

### Core Configuration Sections

| Section | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| `global` | ⚠️ | ✅ | Export | Global Settings (log, maxconn, etc.) |
| `defaults` | ⚠️ | ✅ | Export | Default Optionen (mode, timeouts) |
| `frontend` | ✅ | ✅ | Voll | Listener mit ACLs |
| `backend` | ✅ | ✅ | Voll | Upstream mit Servers |
| `listen` | ❌ | ❌ | Nicht | Combined Frontend+Backend |

### Load Balancing Algorithms

| Algorithm | Import | Export | Status | Bemerkung |
|-----------|--------|--------|--------|-----------|
| `roundrobin` | ✅ | ✅ | Voll | Round Robin (Default) |
| `leastconn` | ✅ | ✅ | Voll | Least Connections |
| `source` | ✅ | ✅ | Voll | Source IP Hash |
| `uri` | ❌ | ❌ | Nicht | URI Hash |
| `url_param` | ❌ | ❌ | Nicht | URL Parameter Hash |
| `hdr` | ❌ | ❌ | Nicht | Header Hash |
| `rdp-cookie` | ❌ | ❌ | Nicht | RDP Cookie Hash |

### Health Check Features

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| `check` (HTTP) | ✅ | ✅ | Voll | Active HTTP Health Checks |
| `check` (TCP) | ⚠️ | ⚠️ | Teilweise | TCP Connect Check |
| `check inter` | ✅ | ✅ | Voll | Health Check Interval |
| `check fall` | ✅ | ✅ | Voll | Failure Threshold |
| `check rise` | ✅ | ✅ | Voll | Success Threshold |
| `httpchk` | ✅ | ✅ | Voll | HTTP Request Method/Path |
| `observe layer4/layer7` | ⚠️ | ⚠️ | Teilweise | Passive Health Checks |
| `on-marked-down` | ❌ | ❌ | Nicht | Fallback Actions |

### ACL (Access Control Lists)

| ACL Type | Import | Export | Status | Bemerkung |
|----------|--------|--------|--------|-----------|
| `path_beg` | ✅ | ✅ | Voll | Path Prefix Matching |
| `path` | ✅ | ✅ | Voll | Exact Path Matching |
| `path_reg` | ❌ | ❌ | Nicht | Regex Path Matching |
| `hdr(host)` | ⚠️ | ⚠️ | Teilweise | Host Header Matching |
| `method` | ❌ | ❌ | Nicht | HTTP Method Matching |
| `src` | ❌ | ❌ | Nicht | Source IP Matching |
| `ssl_fc` | ❌ | ❌ | Nicht | SSL/TLS Matching |

### Stick Tables (Session Persistence)

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| `stick-table` | ✅ | ✅ | Voll | Stick Table Definition |
| `stick on src` | ✅ | ✅ | Voll | IP-based Persistence |
| `stick on cookie` | ✅ | ✅ | Voll | Cookie-based Persistence |
| `stick match` | ❌ | ❌ | Nicht | Conditional Matching |
| `stick store-request` | ❌ | ❌ | Nicht | Store on Request |

### Rate Limiting (Stick Tables)

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| `stick-table type ip size` | ✅ | ✅ | Voll | IP-based Rate Limiting Table |
| `http-request track-sc0` | ✅ | ✅ | Voll | Track Client Requests |
| `http-request deny if` | ✅ | ✅ | Voll | Deny when limit exceeded |
| `sc_http_req_rate` | ✅ | ✅ | Voll | HTTP Request Rate Counter |
| `sc_conn_rate` | ❌ | ❌ | Nicht | Connection Rate Counter |

### Request/Response Headers

| Directive | Import | Export | Status | Bemerkung |
|-----------|--------|--------|--------|-----------|
| `http-request set-header` | ✅ | ✅ | Voll | Add Request Header |
| `http-request del-header` | ✅ | ✅ | Voll | Remove Request Header |
| `http-response set-header` | ✅ | ✅ | Voll | Add Response Header |
| `http-response del-header` | ✅ | ✅ | Voll | Remove Response Header |
| `http-request replace-header` | ❌ | ❌ | Nicht | Replace Header Value |
| `http-response replace-value` | ❌ | ❌ | Nicht | Replace Response Value |

### CORS Support

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| `Access-Control-Allow-Origin` | ✅ | ✅ | Voll | Via http-response set-header |
| `Access-Control-Allow-Methods` | ✅ | ✅ | Voll | Via http-response set-header |
| `Access-Control-Allow-Headers` | ✅ | ✅ | Voll | Via http-response set-header |
| `Access-Control-Allow-Credentials` | ✅ | ✅ | Voll | Via http-response set-header |
| `Access-Control-Max-Age` | ✅ | ✅ | Voll | Via http-response set-header |
| Preflight (OPTIONS) Handling | ❌ | ❌ | Nicht | Manuell via ACLs |

### Authentication Features

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| Basic Auth (ACL) | ⚠️ | ⚠️ | Teilweise | Via ACL + user list |
| JWT Auth (Lua) | ❌ | ❌ | Nicht | Benötigt Lua Scripting |
| API Key (ACL) | ⚠️ | ⚠️ | Teilweise | Via ACL hdr matching |

### Timeouts

| Timeout | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| `timeout connect` | ✅ | ✅ | Voll | Backend Connection Timeout |
| `timeout client` | ✅ | ✅ | Voll | Client Inactivity Timeout |
| `timeout server` | ✅ | ✅ | Voll | Server Inactivity Timeout |
| `timeout http-request` | ⚠️ | ⚠️ | Teilweise | HTTP Request Timeout |
| `timeout http-keep-alive` | ⚠️ | ⚠️ | Teilweise | Keep-Alive Timeout |
| `timeout queue` | ❌ | ❌ | Nicht | Queue Timeout |
| `timeout tunnel` | ❌ | ❌ | Nicht | Tunnel Timeout (WebSocket) |

### Observability

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| Access Logs | ⚠️ | ✅ | Export | Syslog/File Logging |
| Stats Page (HTTP) | ❌ | ✅ | Export | /haproxy?stats Endpoint |
| Stats Socket | ❌ | ✅ | Export | Admin Socket |
| Prometheus Exporter | ❌ | ❌ | Nicht | External Exporter |
| Custom Log Format | ❌ | ❌ | Nicht | log-format Directive |

### Advanced Features

| Feature | Import | Export | Status | Bemerkung |
|---------|--------|--------|--------|-----------|
| Lua Scripting | ❌ | ❌ | Nicht | Custom Lua Scripts |
| SSL/TLS Termination | ❌ | ❌ | Nicht | bind ssl crt |
| HTTP/2 | ❌ | ❌ | Nicht | alpn h2 |
| TCP Mode | ❌ | ❌ | Nicht | mode tcp |
| Server Templates | ❌ | ❌ | Nicht | server-template Directive |
| Dynamic Scaling | ❌ | ❌ | Nicht | Runtime API |

### Coverage Score nach Kategorie

| Kategorie | Features Total | Unterstützt | Coverage |
|-----------|----------------|-------------|----------|
| Core Configuration | 5 | 2 voll, 2 teilweise | ~60% |
| Load Balancing | 7 | 3 voll | 43% |
| Health Checks | 8 | 5 voll, 2 teilweise | ~75% |
| ACL | 7 | 2 voll, 1 teilweise | ~35% |
| Stick Tables | 5 | 3 voll | 60% |
| Rate Limiting | 5 | 4 voll | 80% |
| Headers | 6 | 4 voll | 67% |
| CORS | 6 | 5 voll | 83% |
| Authentication | 3 | 0 voll, 2 teilweise | 33% |
| Timeouts | 7 | 3 voll, 2 teilweise | ~55% |
| Observability | 5 | 2 export | 40% |
| Advanced | 6 | 0 | 0% |

**Gesamt (API Gateway relevante Features):** ~55% Coverage

**Import Coverage:** ~50% (Import bestehender HAProxy Configs → GAL)
**Export Coverage:** ~75% (GAL → HAProxy haproxy.cfg)

### Bidirektionale Feature-Unterstützung

**Vollständig bidirektional (Import ↔ Export):**
1. ✅ Frontend/Backend Configuration
2. ✅ Load Balancing (Round Robin, Least Connections, Source Hash)
3. ✅ Health Checks (Active HTTP)
4. ✅ Stick Tables (Session Persistence)
5. ✅ Rate Limiting (Stick Table-based)
6. ✅ Request/Response Headers
7. ✅ CORS Headers
8. ✅ ACL Path Matching (path_beg, path)
9. ✅ Timeouts (connect, client, server)

**Nur Export (GAL → HAProxy):**
10. ⚠️ Global/Defaults Sections
11. ⚠️ Stats Page Configuration
12. ⚠️ Access Logs

**Features mit Einschränkungen:**
- **JWT/API Key Auth**: Nur via ACLs/Lua (nicht vollständig)
- **SSL/TLS**: Keine Auto-Konfiguration
- **Advanced ACLs**: Regex, Method, Header Matching nicht unterstützt
- **Lua Scripting**: Nicht generierbar/parsebar

### Import-Beispiel (HAProxy → GAL)

**Input (haproxy.cfg):**
```haproxy
frontend http_frontend
    bind 0.0.0.0:80

    acl is_api path_beg /api
    use_backend backend_api if is_api

backend backend_api
    balance roundrobin
    option httpchk GET /health

    server server1 backend-1:8080 check inter 10s fall 3 rise 2
    server server2 backend-2:8080 check inter 10s fall 3 rise 2

    # Rate Limiting
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    http-request track-sc0 src
    http-request deny if { sc_http_req_rate(0) gt 100 }

    # Headers
    http-request set-header X-Forwarded-Proto https
    http-response set-header Access-Control-Allow-Origin *
```

**Output (gal-config.yaml):**
```yaml
version: "1.0"
provider: haproxy
global:
  host: 0.0.0.0
  port: 80
services:
  - name: backend_api
    type: rest
    protocol: http
    upstream:
      targets:
        - host: backend-1
          port: 8080
        - host: backend-2
          port: 8080
      load_balancer:
        algorithm: round_robin
      health_check:
        active:
          enabled: true
          interval: "10s"
          http_path: "/health"
          unhealthy_threshold: 3
          healthy_threshold: 2
    routes:
      - path_prefix: /api
        rate_limit:
          enabled: true
          requests_per_second: 10  # 100 requests per 10s
        headers:
          request_add:
            X-Forwarded-Proto: "https"
          response_add:
            Access-Control-Allow-Origin: "*"
```

### Empfehlungen für zukünftige Erweiterungen

**Priorität 1 (High Impact):**
1. **SSL/TLS Termination** - bind ssl crt Configuration
2. **Advanced ACLs** - Regex, Method, Header Matching
3. **Lua Scripting** - JWT Auth, Custom Logic
4. **Prometheus Metrics** - Native Metrics Export
5. **TCP Mode** - Layer 4 Load Balancing

**Priorität 2 (Medium Impact):**
6. **HTTP/2 Support** - alpn h2
7. **Server Templates** - Dynamic Backend Scaling
8. **Custom Log Format** - log-format Directive
9. **Dynamic Scaling** - Runtime API Integration
10. **WebSocket** - timeout tunnel Configuration

**Priorität 3 (Nice to Have):**
11. **URI/Header Hashing** - Additional LB Algorithms
12. **Passive Health Checks** - observe layer7 vollständig
13. **On-Marked-Down** - Fallback Actions
14. **TCP Health Checks** - Vollständige TCP Check-Support
15. **Preflight CORS** - Automatisches OPTIONS Handling

### Test Coverage (Import)

**HAProxy Import Tests:** Noch nicht implementiert (v1.3.0 Feature 6)

| Test Kategorie | Tests | Status |
|----------------|-------|--------|
| Basic Import | - | ⏳ Pending |
| Frontend/Backend | - | ⏳ Pending |
| Load Balancing | - | ⏳ Pending |
| Health Checks | - | ⏳ Pending |
| Rate Limiting | - | ⏳ Pending |
| Headers | - | ⏳ Pending |
| CORS | - | ⏳ Pending |
| Errors & Warnings | - | ⏳ Pending |

**Status:** Feature 6 (HAProxy Import) ist für v1.3.0 geplant (aktuell 5/8 Features fertig)

### Fazit

**HAProxy Import Coverage (geplant):**
- ✅ **Core Features:** ~75% Coverage erwartet (Frontend, Backend, LB, HC)
- ⚠️ **Authentication:** Eingeschränkt (ACL-based, kein natives JWT)
- ❌ **Advanced Features:** Lua, SSL, TCP Mode nicht unterstützt

**HAProxy Export Coverage:**
- ✅ **Core Features:** 90% Coverage (alle GAL Features → HAProxy)
- ✅ **Best Practices:** Eingebaut (Health Checks, Rate Limiting, Stats)
- ✅ **haproxy.cfg:** Vollständig generiert

**Empfehlung:**
- 🚀 Für High-Performance Workloads: **Perfekt geeignet (100k+ RPS)**
- ✅ Für Standard Load Balancing: **Excellent Choice**
- ⚠️ Für API Gateway Features (JWT, Plugins): **Kong/APISIX besser geeignet**
- ⚠️ Für SSL/TLS Auto-Config: **Traefik besser geeignet**

**Referenzen:**
- 📚 [HAProxy Configuration Manual](https://docs.haproxy.org/2.8/configuration.html)
- 📚 [HAProxy Load Balancing](https://www.haproxy.com/documentation/haproxy-configuration-manual/latest/#4)
- 📚 [HAProxy Health Checks](https://www.haproxy.com/documentation/haproxy-configuration-manual/latest/#5.2-check)
- 📚 [HAProxy ACLs](https://www.haproxy.com/documentation/haproxy-configuration-manual/latest/#7)

---

