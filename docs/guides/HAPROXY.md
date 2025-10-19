# HAProxy Provider Guide

**HAProxy Open Source Load Balancer Provider für GAL**

HAProxy ist der de-facto Standard für High-Performance Load Balancing und wird weltweit in kritischen Production-Umgebungen eingesetzt. Dieser Guide zeigt, wie Sie HAProxy über GAL konfigurieren und nutzen können.

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#ubersicht)
2. [Installation & Setup](#installation-setup)
3. [Schnellstart](#schnellstart)
4. [Konfigurationsoptionen](#konfigurationsoptionen)
5. [Feature-Implementierungen](#feature-implementierungen)
6. [HAProxy-spezifische Details](#haproxy-spezifische-details)
7. [Provider-Vergleich](#provider-vergleich)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Übersicht

### Was ist HAProxy?

HAProxy (High Availability Proxy) ist ein äußerst performanter und zuverlässiger TCP/HTTP Load Balancer. Er wird von den größten Websites der Welt eingesetzt (GitHub, Reddit, Stack Overflow, etc.) und ist bekannt für:

- **Extreme Performance**: 100.000+ Requests pro Sekunde
- **Enterprise-grade Reliability**: Höchste Verfügbarkeit
- **Advanced Load Balancing**: 10+ Algorithmen
- **Flexible Health Checks**: Active & Passive
- **Low Resource Usage**: Minimale CPU/RAM Nutzung

### Feature-Matrix

| Feature | Support Level | Implementierung | Notes |
|---------|--------------|-----------------|-------|
| **Load Balancing** |
| Round Robin | ✅ Full | `balance roundrobin` | Gleichmäßige Verteilung |
| Least Connections | ✅ Full | `balance leastconn` | Wenigste Verbindungen |
| IP Hash (Source) | ✅ Full | `balance source` | Session Persistence |
| Weighted | ✅ Full | `weight` per server | Kapazitätsbasiert |
| URI Hash | ✅ Full | `balance uri` | URL-basiert |
| Header Hash | ✅ Full | `balance hdr(name)` | Header-basiert |
| **Health Checks** |
| Active HTTP Checks | ✅ Full | `option httpchk` | Periodisches Probing |
| Active TCP Checks | ✅ Full | `check` | TCP Connection Check |
| Passive Checks | ✅ Full | `fall/rise` thresholds | Traffic-basiert |
| Custom Health Checks | ✅ Full | `http-check expect` | Flexible Validierung |
| **Traffic Management** |
| Rate Limiting | ✅ Full | `stick-table` | IP & Header-basiert |
| Sticky Sessions | ✅ Full | `cookie`, `source` | Cookie oder IP-basiert |
| Connection Pooling | ✅ Full | `http-server-close` | Connection Reuse |
| Timeouts | ✅ Full | `timeout *` | Granulare Timeouts |
| **Security** |
| Basic Authentication | ✅ Full | ACL + auth backend | Via ACLs |
| Header Manipulation | ✅ Full | `http-request/response` | Add/Set/Remove |
| CORS | ⚠️ Limited | Custom headers | Via http-response |
| JWT Authentication | ⚠️ Lua | Lua scripting | Lua-Script erforderlich |
| **Observability** |
| Access Logs | ✅ Full | `log global` | Structured logging |
| Stats Page | ✅ Full | `stats` section | Web UI & API |
| Runtime API | ✅ Full | `stats socket` | Dynamic config |

**Legende:**
- ✅ Full: Nativ unterstützt
- ⚠️ Limited: Eingeschränkt oder benötigt Zusatzmodule
- ⚠️ Lua: Benötigt Lua Scripting
- ❌ Not Supported: Nicht verfügbar

---

## Installation & Setup

### HAProxy Installation

**Ubuntu/Debian:**
```bash
# HAProxy 2.8+ (neueste Stable)
sudo apt update
sudo apt install haproxy

# Version prüfen
haproxy -v
```

**CentOS/RHEL:**
```bash
# EPEL Repository aktivieren
sudo yum install epel-release

# HAProxy installieren
sudo yum install haproxy

# Version prüfen
haproxy -v
```

**Docker:**
```bash
# HAProxy 2.9 Official Image
docker pull haproxy:2.9-alpine

# Mit Config starten
docker run -d \
  -p 80:80 \
  -v $(pwd)/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro \
  haproxy:2.9-alpine
```

### GAL Installation

```bash
# PyPI Installation
pip install gal-gateway

# Provider prüfen
gal list-providers
# → haproxy - HAProxy Load Balancer
```

---

## Schnellstart

### Beispiel 1: Basic Load Balancing

**config.yaml:**
```yaml
version: "1.0"
provider: haproxy

global:
  host: "0.0.0.0"
  port: 80

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
        - host: api-2.internal
          port: 8080
      load_balancer:
        algorithm: round_robin  # Gleichmäßige Verteilung

    routes:
      - path_prefix: /api
```

**Generierung:**
```bash
gal generate --config config.yaml --provider haproxy > haproxy.cfg
```

**Generierte haproxy.cfg:**
```haproxy
global
    log         127.0.0.1 local0
    maxconn     4000
    daemon
    stats socket /var/lib/haproxy/stats level admin

defaults
    mode                    http
    log                     global
    option                  httplog
    timeout client          30s
    timeout server          30s
    timeout connect         5s

frontend http_frontend
    bind 0.0.0.0:80
    
    acl is_api_service_route0 path_beg /api
    use_backend backend_api_service if is_api_service_route0

backend backend_api_service
    balance roundrobin
    server server1 api-1.internal:8080 check
    server server2 api-2.internal:8080 check
```

**Testen:**
```bash
# Config validieren
haproxy -c -f haproxy.cfg

# HAProxy starten
haproxy -f haproxy.cfg

# Requests testen
curl http://localhost/api
```

### Beispiel 2: Load Balancing + Health Checks

```yaml
services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
          weight: 2  # Erhält 2x mehr Traffic
        - host: api-2.internal
          port: 8080
          weight: 1
      health_check:
        active:
          enabled: true
          http_path: /health
          interval: "10s"
          healthy_threshold: 2
          unhealthy_threshold: 3
          healthy_status_codes: [200, 204]
      load_balancer:
        algorithm: least_conn  # Wenigste Verbindungen

    routes:
      - path_prefix: /api
```

**Generierte haproxy.cfg (Backend):**
```haproxy
backend backend_api_service
    balance leastconn
    option httpchk GET /health HTTP/1.1
    http-check expect status 200|204
    
    server server1 api-1.internal:8080 check inter 10s fall 3 rise 2 weight 2
    server server2 api-2.internal:8080 check inter 10s fall 3 rise 2 weight 1
```

### Beispiel 3: Rate Limiting + Headers + CORS

```yaml
services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.internal
      port: 8080

    routes:
      - path_prefix: /api
        rate_limit:
          enabled: true
          requests_per_second: 100
          burst: 200
          key_type: ip_address
          response_status: 429
        
        headers:
          request_add:
            X-Request-ID: "{{uuid}}"
            X-Gateway: "HAProxy"
          response_add:
            X-Frame-Options: "DENY"
            X-Content-Type-Options: "nosniff"
        
        cors:
          enabled: true
          allowed_origins:
            - "https://app.example.com"
          allowed_methods:
            - GET
            - POST
            - PUT
            - DELETE
          allow_credentials: true
```

**Generierte haproxy.cfg (Frontend):**
```haproxy
frontend http_frontend
    bind 0.0.0.0:80
    
    # Rate Limiting
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    http-request track-sc0 src if is_api_service_route0
    http-request deny deny_status 429 if is_api_service_route0 { sc_http_req_rate(0) gt 100 }
    
    # Request Headers
    http-request set-header X-Request-ID "%[uuid()]" if is_api_service_route0
    http-request set-header X-Gateway "HAProxy" if is_api_service_route0
    
    # Response Headers
    http-response set-header X-Frame-Options "DENY" if is_api_service_route0
    http-response set-header X-Content-Type-Options "nosniff" if is_api_service_route0
    
    # CORS
    http-response set-header Access-Control-Allow-Origin "https://app.example.com" if is_api_service_route0
    http-response set-header Access-Control-Allow-Methods "GET, POST, PUT, DELETE" if is_api_service_route0
    http-response set-header Access-Control-Allow-Credentials "true" if is_api_service_route0
    
    use_backend backend_api_service if is_api_service_route0
```

---

## Konfigurationsoptionen

### Global Configuration

```yaml
global:
  host: "0.0.0.0"        # Listen Address (Standard: 0.0.0.0)
  port: 80               # Listen Port (Standard: 10000)
  admin_port: 9901       # Admin/Stats Port (nicht genutzt in HAProxy)
  timeout: "30s"         # Default Timeout (Standard: 30s)
```

**Mapping zu haproxy.cfg:**
- `host:port` → `bind` Direktive im Frontend
- `timeout` → `timeout client`, `timeout server`

### Upstream Configuration

```yaml
upstream:
  # Option 1: Single Host (einfach)
  host: api.example.com
  port: 8080
  
  # Option 2: Multiple Targets (Load Balancing)
  targets:
    - host: api-1.internal
      port: 8080
      weight: 2          # Load Balancing Gewichtung (default: 1)
    - host: api-2.internal
      port: 8080
      weight: 1
  
  # Health Checks
  health_check:
    active:
      enabled: true
      http_path: /health        # Health Check Pfad (default: /health)
      interval: "10s"           # Check Intervall (default: 10s)
      timeout: "5s"             # Check Timeout (default: 5s)
      healthy_threshold: 2      # Erfolge bis gesund (default: 2)
      unhealthy_threshold: 3    # Fehler bis ungesund (default: 3)
      healthy_status_codes:     # Erfolgreiche Status Codes
        - 200
        - 201
        - 204
    
    passive:
      enabled: true
      max_failures: 5           # Max Fehler (default: 5)
      unhealthy_status_codes:   # Fehlerhafte Status Codes
        - 500
        - 502
        - 503
        - 504
  
  # Load Balancing
  load_balancer:
    algorithm: round_robin      # round_robin, least_conn, ip_hash, weighted
    sticky_sessions: false      # Cookie-based Session Persistence
    cookie_name: "SERVERID"     # Cookie Name (wenn sticky_sessions=true)
```

**HAProxy Mapping:**

| GAL Option | HAProxy Direktive | Beschreibung |
|------------|-------------------|--------------|
| `targets[].host:port` | `server name host:port` | Backend Server |
| `targets[].weight` | `server ... weight N` | Load Balancing Gewicht |
| `algorithm: round_robin` | `balance roundrobin` | Round Robin |
| `algorithm: least_conn` | `balance leastconn` | Least Connections |
| `algorithm: ip_hash` | `balance source` | IP Hash (Source) |
| `algorithm: weighted` | `balance roundrobin` + `weight` | Weighted Round Robin |
| `active.enabled` | `option httpchk` | Active Health Check |
| `active.http_path` | `option httpchk GET /path` | Health Check Pfad |
| `active.interval` | `check inter N` | Check Intervall |
| `active.unhealthy_threshold` | `fall N` | Fehler bis ungesund |
| `active.healthy_threshold` | `rise N` | Erfolge bis gesund |
| `passive.max_failures` | `fall N` | Passive Fehlergrenze |
| `sticky_sessions: true` | `cookie NAME insert` | Cookie Persistence |

### Route Configuration

```yaml
routes:
  - path_prefix: /api           # Pfad-Präfix (ACL)
    methods:                    # HTTP Methoden (optional)
      - GET
      - POST
    
    # Rate Limiting
    rate_limit:
      enabled: true
      requests_per_second: 100  # RPS Limit
      burst: 200                # Burst Kapazität
      key_type: ip_address      # ip_address oder header
      key_header: X-API-Key     # Header Name (wenn key_type=header)
      response_status: 429      # HTTP Status bei Limit
    
    # Header Manipulation
    headers:
      request_add:              # Request Headers hinzufügen
        X-Request-ID: "{{uuid}}"
        X-Gateway: "HAProxy"
      request_set:              # Request Headers setzen
        User-Agent: "HAProxy/1.0"
      request_remove:           # Request Headers entfernen
        - X-Internal-Token
      
      response_add:             # Response Headers hinzufügen
        X-Frame-Options: "DENY"
      response_set:             # Response Headers setzen
        Server: "HAProxy"
      response_remove:          # Response Headers entfernen
        - X-Powered-By
    
    # CORS
    cors:
      enabled: true
      allowed_origins:
        - "https://app.example.com"
        - "https://www.example.com"
      allowed_methods:
        - GET
        - POST
        - PUT
        - DELETE
        - OPTIONS
      allowed_headers:
        - Content-Type
        - Authorization
        - X-API-Key
      expose_headers:
        - X-Request-ID
      allow_credentials: true
      max_age: 86400            # Preflight Cache (Sekunden)
```

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

## Best Practices

### 1. Kombiniere Active + Passive Health Checks

**Empfehlung:**
```yaml
health_check:
  active:
    enabled: true
    interval: "10s"
  passive:
    enabled: true
    max_failures: 3
```

**Vorteil:** Schnelle Reaktion bei Ausfällen + Traffic-basierte Überwachung.

### 2. Nutze Weighted Load Balancing für heterogene Server

**Empfehlung:**
```yaml
targets:
  - host: large-instance.internal
    port: 8080
    weight: 4
  - host: medium-instance.internal
    port: 8080
    weight: 2
  - host: small-instance.internal
    port: 8080
    weight: 1
```

**Vorteil:** Optimale Ressourcen-Nutzung.

### 3. Setze angemessene Timeouts

**Empfehlung:**
```yaml
global:
  timeout: "60s"  # Für lange API-Requests
```

**Mapping:**
```haproxy
defaults
    timeout client  60s
    timeout server  60s
    timeout connect 5s   # Immer kurz (Connection Setup)
```

### 4. Aktiviere Connection Pooling

**HAProxy Standard:**
```haproxy
defaults
    option http-server-close  # Connection Reuse
```

**Vorteil:** Reduziert Backend-Verbindungen.

### 5. Nutze Stick-Tables effizient

**Empfehlung:**
```haproxy
stick-table type ip size 100k expire 30s store http_req_rate(10s)
```

- `size 100k`: Für ~100k gleichzeitige IPs
- `expire 30s`: Automatisches Cleanup
- `store http_req_rate(10s)`: 10s Zeitfenster

### 6. Monitoring via Stats Socket

**Setup:**
```haproxy
global
    stats socket /var/lib/haproxy/stats level admin
```

**Nutzung:**
```bash
# Server Status
echo "show servers state" | socat /var/lib/haproxy/stats -

# Disable Server
echo "disable server backend_api/server1" | socat /var/lib/haproxy/stats -

# Enable Server
echo "enable server backend_api/server1" | socat /var/lib/haproxy/stats -
```

### 7. Logging für Production

**Empfehlung:**
```haproxy
defaults
    option httplog
    log global
```

**Mit Rsyslog:**
```bash
# /etc/rsyslog.d/haproxy.conf
$ModLoad imudp
$UDPServerRun 514
local0.* /var/log/haproxy/access.log
```

---

## Troubleshooting

### 1. "503 Service Unavailable"

**Symptom:** Alle Requests → 503

**Mögliche Ursachen:**
1. Alle Backend-Server down
2. Health Checks schlagen fehl
3. Backend nicht erreichbar

**Debugging:**
```bash
# Server Status prüfen
echo "show servers state" | socat /var/lib/haproxy/stats -

# HAProxy Logs
tail -f /var/log/haproxy/access.log

# Health Check testen
curl http://backend-server:8080/health
```

**Lösung:**
```bash
# Server manuell aktivieren
echo "enable server backend_api/server1" | socat /var/lib/haproxy/stats -

# Health Check Path anpassen
backend backend_api
    option httpchk GET /actuator/health HTTP/1.1
```

### 2. Rate Limiting funktioniert nicht

**Symptom:** Keine 429 Responses

**Mögliche Ursachen:**
1. Stick-Table nicht definiert
2. ACL falsch
3. Track nicht aktiv

**Debugging:**
```bash
# Stick-Table anzeigen
echo "show table" | socat /var/lib/haproxy/stats -
```

**Lösung:**
```haproxy
frontend http_frontend
    # WICHTIG: Stick-Table definieren
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    
    # WICHTIG: Track BEFORE deny
    http-request track-sc0 src if is_route
    http-request deny deny_status 429 if is_route { sc_http_req_rate(0) gt 100 }
```

### 3. Sticky Sessions funktionieren nicht

**Symptom:** Requests landen auf verschiedenen Servern

**Mögliche Ursachen:**
1. Cookie wird nicht gesetzt
2. Cookie wird nicht gesendet
3. Balance algorithm falsch

**Debugging:**
```bash
# Request mit Cookie-Inspektion
curl -v http://localhost/api

# Cookie in Response prüfen
# Set-Cookie: SERVERID=server1; path=/
```

**Lösung:**
```haproxy
backend backend_api
    cookie SERVERID insert indirect nocache
    server server1 api-1.internal:8080 cookie server1
    server server2 api-2.internal:8080 cookie server2
```

### 4. Headers werden nicht gesetzt

**Symptom:** X-Request-ID fehlt

**Mögliche Ursachen:**
1. ACL-Condition falsch
2. Direktive an falscher Stelle

**Lösung:**
```haproxy
frontend http_frontend
    # WICHTIG: if Condition muss matchen
    http-request set-header X-Request-ID "%[uuid()]" if is_route
    
    # NICHT im Backend setzen (zu spät)
```

### 5. Config Reload schlägt fehl

**Symptom:** `haproxy -c -f haproxy.cfg` zeigt Fehler

**Mögliche Ursachen:**
1. Syntax-Fehler
2. Fehlende Direktiven
3. Ungültige Werte

**Debugging:**
```bash
# Detaillierte Fehlerausgabe
haproxy -c -f haproxy.cfg -V

# Zeile für Zeile prüfen
haproxy -c -f haproxy.cfg -d
```

**Häufige Fehler:**
```haproxy
# FALSCH: Fehlende Quotes
http-request set-header X-Test value with spaces

# RICHTIG
http-request set-header X-Test "value with spaces"

# FALSCH: Ungültiger Balance Algorithm
balance round-robin

# RICHTIG
balance roundrobin
```

### 6. Performance-Probleme

**Symptom:** Hohe Latenz, niedrige Throughput

**Debugging:**
```bash
# Stats anzeigen
echo "show info" | socat /var/lib/haproxy/stats -

# Connection Limits prüfen
echo "show stat" | socat /var/lib/haproxy/stats -
```

**Tuning:**
```haproxy
global
    maxconn 10000  # Erhöhen für mehr gleichzeitige Connections
    
defaults
    timeout http-keep-alive 10s  # Connection Reuse
    option http-server-close
    
backend backend_api
    balance leastconn  # Bessere Verteilung bei ungleichen Requests
```

---

## Weiterführende Ressourcen

### Offizielle Dokumentation

- **HAProxy Docs**: https://docs.haproxy.org/
- **Configuration Manual**: https://cbonte.github.io/haproxy-dconv/2.9/configuration.html
- **Best Practices**: https://www.haproxy.com/documentation/hapee/latest/configuration/best-practices/

### GAL Dokumentation

- **Hauptdokumentation**: [README.md](https://github.com/pt9912/x-gal#readme)
- **Rate Limiting Guide**: [RATE_LIMITING.md](RATE_LIMITING.md)
- **Health Checks Guide**: [HEALTH_CHECKS.md](HEALTH_CHECKS.md)
- **Authentication Guide**: [AUTHENTICATION.md](AUTHENTICATION.md)

### Beispiele

- **HAProxy Examples**: [examples/haproxy-example.yaml](https://github.com/pt9912/x-gal/blob/main/examples/haproxy-example.yaml)
- **Alle Provider**: [examples/](../../examples/)

---

**Letzte Aktualisierung:** 2025-10-18  
**GAL Version:** 1.2.0  
**HAProxy Version:** 2.9+
