# Request Mirroring Anleitung

**Umfassende Anleitung für Request Mirroring, Shadow Traffic und Production Testing in GAL (Gateway Abstraction Layer)**

## Inhaltsverzeichnis

1. [Übersicht](#ubersicht)
2. [Schnellstart](#schnellstart)
3. [Konfigurationsoptionen](#konfigurationsoptionen)
4. [Provider-Implementierung](#provider-implementierung)
5. [Häufige Anwendungsfälle](#haufige-anwendungsfalle)
6. [Best Practices](#best-practices)
7. [Request Mirroring Testen](#request-mirroring-testen)
8. [Troubleshooting](#troubleshooting)

---

## Übersicht

Request Mirroring (auch Shadow Traffic oder Dark Traffic genannt) ist ein essentielles Feature für sichere Production-Tests. GAL bietet eine einheitliche Request Mirroring-Konfiguration für alle unterstützten Gateway-Provider.

### Was ist Request Mirroring?

Request Mirroring dupliziert eingehende Requests und sendet sie an **Shadow Backends**, ohne die primäre Response zu beeinflussen. Dies ermöglicht Testing unter realer Last ohne Risiko für Produktions-Nutzer.

**Request Flow mit Mirroring**:

```
                      ┌─────────────────┐
Client Request ──────►│   API Gateway   │
                      └────────┬────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
          ┌──────────────────┐  ┌──────────────────┐
          │ Primary Backend  │  │ Shadow Backend   │
          │   (Production)   │  │  (New Version)   │
          └────────┬─────────┘  └──────────────────┘
                   │                      │
                   │                      │ (ignored)
                   ▼                      ▼
          Response to Client         Logs/Metrics
```

### Warum ist Request Mirroring wichtig?

- ✅ **Sichere Production-Tests**: Neue Versionen mit echten Requests testen
- ✅ **Zero User Impact**: Shadow Traffic beeinflusst primäre Response nicht
- ✅ **Performance Validation**: Latenz und Throughput unter realer Last messen
- ✅ **Bug Detection**: Bugs finden, bevor Features live gehen
- ✅ **Data Collection**: Metriken und Logs von neuen Versionen sammeln
- ✅ **Gradual Rollout**: Schrittweise von 1% → 100% Shadow Traffic erhöhen

### Provider-Unterstützung

| Feature | Envoy | Nginx | APISIX | HAProxy | Kong | Traefik | Azure APIM | AWS API GW | GCP API GW |
|---------|-------|-------|--------|---------|------|---------|------------|------------|------------|
| **Request Mirroring** | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ |
| **Native Support** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Sample Percentage** | ✅ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| **Custom Headers** | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Multiple Mirrors** | ✅ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ |
| **Fire-and-Forget** | ✅ | ✅ | ✅ | ⚠️ | ❌ | ⚠️ | ✅ | ⚠️ | ⚠️ |

**Legende:**
- ✅ Native Support (eingebautes Feature)
- ⚠️ Workaround erforderlich (Plugin, Lambda, Custom Code, External Tools)
- ❌ Nicht unterstützt

**Wichtiger Hinweis für HAProxy:**
HAProxy unterstützt **kein natives async Request Mirroring**. Für Production Mirroring benötigt HAProxy externe Tools:
- **GoReplay (gor)** - Empfohlen ([https://github.com/buger/goreplay](https://github.com/buger/goreplay))
- **Teeproxy** - Request Duplikation ([https://github.com/chrissnell/teeproxy](https://github.com/chrissnell/teeproxy))
- **SPOE (Stream Processing Offload Engine)** - HAProxy-native, komplex
- **Lua Scripting** - Custom Implementation

Siehe [HAProxy Mirroring Tests](../../tests/docker/haproxy-mirroring/README.md) für Details.

---

## Schnellstart

### Minimale Konfiguration

```yaml
version: "1.0"
provider: gal

services:
  - name: api_service
    protocol: http
    upstream:
      targets:
        - host: api-v1.internal
          port: 8080

    routes:
      - path_prefix: /api/users
        methods: [GET, POST]

        # Request Mirroring aktivieren
        mirroring:
          enabled: true
          targets:
            - name: shadow-v2
              upstream:
                host: shadow-api-v2.internal
                port: 8080
              sample_percentage: 100.0  # 100% aller Requests
```

### Deployment

```bash
# Config generieren
gal generate --config config.yaml --provider envoy --output envoy.yaml

# Gateway starten
envoy -c envoy.yaml
```

### Verifikation

```bash
# Request an Primary Backend
curl http://localhost:8080/api/users

# Shadow Backend Logs prüfen
curl http://shadow-api-v2.internal:8080/metrics
```

---

## Konfigurationsoptionen

### MirroringConfig

```yaml
mirroring:
  enabled: true                    # Request Mirroring aktivieren
  mirror_request_body: true        # Body mitspiegeln (default: true)
  mirror_headers: true             # Headers mitspiegeln (default: true)
  targets:                         # Liste der Shadow Backends
    - name: shadow-v2              # Eindeutiger Name
      upstream:
        host: shadow-api-v2.internal
        port: 8080
      sample_percentage: 50.0      # 50% der Requests (0-100)
      timeout: "5s"                # Timeout für Shadow Requests
      headers:                     # Custom Headers für Shadow
        X-Mirror: "true"
        X-Shadow-Version: "v2"
```

### Parameter-Referenz

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `enabled` | boolean | false | Request Mirroring aktivieren |
| `mirror_request_body` | boolean | true | Request Body an Shadow Backend senden |
| `mirror_headers` | boolean | true | Request Headers an Shadow Backend senden |
| `targets` | list | [] | Liste der Shadow Backend Targets |

### MirrorTarget

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `name` | string | *required* | Eindeutiger Name für Shadow Target |
| `upstream` | object | *required* | Backend-Konfiguration (host, port) |
| `sample_percentage` | float | 100.0 | Prozent der Requests (0-100) |
| `timeout` | string | "5s" | Timeout für Shadow Requests |
| `headers` | dict | {} | Custom Headers für Shadow Backend |

---

## Provider-Implementierung

### 1. Envoy (✅ Native)

**Mechanismus:** `request_mirror_policies`

```yaml
# Envoy Config (generiert von GAL)
clusters:
  - name: shadow_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    dns_lookup_family: V4_ONLY
    load_assignment:
      cluster_name: shadow_cluster
      endpoints:
        - lb_endpoints:
          - endpoint:
              address:
                socket_address:
                  address: shadow-api-v2.internal
                  port_value: 8080

routes:
  - match:
      prefix: "/api/users"
    route:
      cluster: primary_cluster
      request_mirror_policies:
        - cluster: shadow_cluster
          runtime_fraction:
            default_value:
              numerator: 50    # 50% sampling
              denominator: HUNDRED
```

**Features:**
- ✅ Native `request_mirror_policies` support
- ✅ Sample percentage via `runtime_fraction`
- ✅ Custom headers via filter chains
- ✅ Multiple mirrors supported

**Envoy Version:** Envoy 1.10+

---

### 2. Nginx (✅ Native)

**Mechanismus:** `mirror` directive

```nginx
# Nginx Config (generiert von GAL)
upstream shadow_backend {
    server shadow-api-v2.internal:8080;
}

server {
    listen 8080;

    location /api/users {
        # Primary backend
        proxy_pass http://api-v1.internal:8080;

        # Mirror to shadow backend
        mirror /mirror_shadow;
        mirror_request_body on;

        # 50% sampling via split_clients
        split_clients "${remote_addr}${request_uri}" $mirror_flag {
            50%     "1";
            *       "0";
        }
    }

    location = /mirror_shadow {
        internal;
        proxy_pass http://shadow_backend$request_uri;
        proxy_set_header X-Mirror "true";
        proxy_set_header X-Shadow-Version "v2";

        # Don't wait for shadow response
        proxy_ignore_client_abort on;
    }
}
```

**Features:**
- ✅ Native `mirror` directive (Nginx 1.13+)
- ✅ Sample percentage via `split_clients`
- ✅ Custom headers via `proxy_set_header`
- ✅ Multiple mirrors via multiple `mirror` directives

**Nginx Version:** Nginx 1.13.4+ (mirror directive support)

---

### 3. Apache APISIX (✅ Native)

**Mechanismus:** `proxy-mirror` plugin

```yaml
# APISIX Config (generiert von GAL)
routes:
  - uri: /api/users
    methods: [GET, POST]
    upstream:
      nodes:
        "api-v1.internal:8080": 1
      type: roundrobin

    plugins:
      proxy-mirror:
        host: "http://shadow-api-v2.internal:8080"
        path: /api/users
        sample_ratio: 0.5  # 50% sampling
        request_headers:
          X-Mirror: "true"
          X-Shadow-Version: "v2"
```

**Features:**
- ✅ Native `proxy-mirror` plugin
- ✅ Sample percentage via `sample_ratio` (0.0-1.0)
- ✅ Custom headers via `request_headers`
- ✅ Multiple mirrors via multiple plugin instances

**APISIX Version:** APISIX 2.5+

---

### 4. HAProxy (❌ Keine Native Unterstützung - Externe Tools erforderlich)

**⚠️ WICHTIG: HAProxy unterstützt KEIN natives async Request Mirroring!**

HAProxy hat **keine** `http-request mirror` Direktive und keine eingebaute Funktion für fire-and-forget Request Mirroring. Für Production Mirroring benötigt HAProxy externe Tools.

**Empfohlene Lösungen:**

#### Option 1: GoReplay (gor) - **Empfohlen** ✅

```bash
# GoReplay neben HAProxy deployen
docker run -d --name gor \
  --network host \
  goreplay/goreplay:latest \
  --input-raw :8080 \
  --output-http "http://shadow-api-v2.internal:8080" \
  --output-http-track-response

# Mit Sampling (50%)
gor --input-raw :8080 \
    --output-http "http://shadow-api-v2.internal:8080|50%"
```

**Vorteile:**
- ✅ Production-ready, weit verbreitet
- ✅ Einfache Integration
- ✅ Sample percentage support
- ✅ Request/Response tracking
- ✅ Filter by path, header, etc.

#### Option 2: Teeproxy

```bash
# Teeproxy als Proxy vor HAProxy
teeproxy \
  -l :8080 \
  -a localhost:8081 \
  -b http://shadow-api-v2.internal:8080
```

#### Option 3: SPOE (Stream Processing Offload Engine)

```haproxy
# haproxy.cfg
global
    stats socket /var/run/haproxy.sock mode 600 level admin

backend spoe-mirror
    mode tcp
    server spoe1 127.0.0.1:12345

frontend http_front
    bind *:8080
    filter spoe engine mirror config /etc/haproxy/spoe-mirror.conf
    default_backend primary_backend
```

```
# spoe-mirror.conf
[mirror]
spoe-agent mirror-agent
    messages   mirror-request
    option     async
    timeout    processing 2s
    use-backend spoe-mirror

spoe-message mirror-request
    args method=method path=path
    event on-frontend-http-request
```

**Nachteile:** Komplex, benötigt externen SPOE Agent

#### Option 4: Lua Scripting

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
    -- NOT fire-and-forget by default!
end)
```

**Nachteile:** Lua nicht fire-and-forget, blockiert Request

**Features:**
- ❌ Kein natives Request Mirroring
- ⚠️ Sample percentage via externe Tools (gor, teeproxy)
- ⚠️ Custom headers via externe Tools
- ⚠️ Multiple mirrors via externe Tools
- ⚠️ Fire-and-Forget nur mit externen Tools (gor, SPOE)

**HAProxy Routing-Konfiguration (von GAL generiert):**

```haproxy
# HAProxy Config für Routing (kein Mirroring)
frontend http_front
    bind *:8080
    mode http

    acl is_api_users path_beg /api/users
    use_backend api_backend if is_api_users

    default_backend api_backend

backend api_backend
    mode http
    server api1 api-v1.internal:8080 check
```

**GAL generiert HAProxy-Konfigurationen mit Routing, aber dokumentiert, dass externes Mirroring-Tool benötigt wird.**

**Siehe auch:**
- [HAProxy Mirroring E2E Tests](../../tests/docker/haproxy-mirroring/README.md) - Dokumentiert Limitation
- [GoReplay GitHub](https://github.com/buger/goreplay) - Empfohlenes Tool
- [Teeproxy GitHub](https://github.com/chrissnell/teeproxy) - Alternative Lösung

---

### 5. Kong (⚠️ Partial - Plugin/Workaround)

**Mechanismus:** `request-transformer` + `post-function` oder Enterprise Plugin

**Kong Open Source Workaround:**

```yaml
# Kong Declarative Config (generiert von GAL)
services:
  - name: api_service
    url: http://api-v1.internal:8080

routes:
  - name: api_users_route
    paths:
      - /api/users
    service: api_service

plugins:
  # Option 1: post-function Plugin (Lua)
  - name: post-function
    route: api_users_route
    config:
      access:
        - |
          -- Mirror request to shadow backend
          local http = require "resty.http"
          local httpc = http.new()

          -- Sample 50% of requests
          if math.random() < 0.5 then
            httpc:request_uri("http://shadow-api-v2.internal:8080" .. kong.request.get_path(), {
              method = kong.request.get_method(),
              body = kong.request.get_raw_body(),
              headers = {
                ["X-Mirror"] = "true",
                ["X-Shadow-Version"] = "v2"
              }
            })
          end
```

**Kong Enterprise:**
```yaml
plugins:
  # Option 2: request-transformer-advanced (Enterprise)
  - name: request-transformer-advanced
    config:
      add:
        headers:
          - "X-Mirror: true"
      mirror:
        enabled: true
        upstream_url: "http://shadow-api-v2.internal:8080"
        sample_percentage: 50
```

**Features:**
- ⚠️ Open Source: Lua Scripting erforderlich
- ✅ Enterprise: Native plugin support
- ✅ Sample percentage via Lua `math.random()` oder Enterprise config
- ✅ Custom headers supported

**Kong Version:** Kong 2.0+

---

### 6. Traefik (⚠️ Limited - Custom Middleware)

**Mechanismus:** Custom Middleware (Plugin erforderlich)

**Traefik Middleware (Custom Plugin erforderlich):**

```yaml
# Traefik Config (generiert von GAL)
http:
  routers:
    api-router:
      rule: "PathPrefix(`/api/users`)"
      service: api-service
      middlewares:
        - mirror-middleware

  services:
    api-service:
      loadBalancer:
        servers:
          - url: "http://api-v1.internal:8080"

  middlewares:
    mirror-middleware:
      plugin:
        traefik-mirror-plugin:
          shadow_url: "http://shadow-api-v2.internal:8080"
          sample_percentage: 50
          headers:
            X-Mirror: "true"
            X-Shadow-Version: "v2"
```

**⚠️ Achtung:** Traefik hat KEIN natives Request Mirroring Feature. Ein Custom Plugin muss entwickelt werden.

**Workaround:**
- Entwickle ein Traefik Plugin (Go)
- Oder verwende einen externen Service Mesh (Linkerd, Istio)

**Features:**
- ⚠️ Custom Plugin erforderlich
- ⚠️ Kein natives Feature in Traefik

---

### 7. Azure API Management (✅ Native)

**Mechanismus:** `send-request` policy

```xml
<!-- Azure APIM Policy (generiert von GAL) -->
<policies>
    <inbound>
        <base />

        <!-- Mirror Request to Shadow Backend -->
        <choose>
            <when condition="@(new Random().Next(100) < 50)">
                <send-request mode="new" response-variable-name="mirrorResponse"
                              timeout="5" ignore-error="true">
                    <set-url>http://shadow-api-v2.internal:8080@(context.Request.Url.Path)</set-url>
                    <set-method>@(context.Request.Method)</set-method>
                    <set-header name="X-Mirror" exists-action="override">
                        <value>true</value>
                    </set-header>
                    <set-header name="X-Shadow-Version" exists-action="override">
                        <value>v2</value>
                    </set-header>
                    <set-body>@(context.Request.Body.As<string>(preserveContent: true))</set-body>
                </send-request>
            </when>
        </choose>
    </inbound>

    <backend>
        <!-- Primary backend -->
        <base />
    </backend>
</policies>
```

**Features:**
- ✅ Native `send-request` policy
- ✅ Sample percentage via `<choose>` + Random
- ✅ Custom headers via `<set-header>`
- ✅ Multiple mirrors via multiple `send-request`
- ✅ `ignore-error="true"` → Shadow Response wird ignoriert

**Azure APIM Tier:** Standard oder Premium

---

### 8. AWS API Gateway (⚠️ Workaround - Lambda@Edge)

**Mechanismus:** Lambda@Edge Function

**GAL Config:**

```yaml
global_config:
  aws_apigateway:
    api_name: "MyAPI"
    # Request Mirroring Workaround
    mirroring_workaround: "lambda_edge"
    mirroring_lambda_edge_arn: "arn:aws:lambda:us-east-1:123456789012:function:mirror-traffic"
```

**Lambda@Edge Function (Nutzer muss erstellen):**

```javascript
// Lambda@Edge Function für Request Mirroring
const https = require('https');

exports.handler = async (event) => {
    const request = event.Records[0].cf.request;

    // Sample 50% of requests
    if (Math.random() < 0.5) {
        // Mirror request to shadow backend
        const options = {
            hostname: 'shadow-api-v2.internal',
            port: 8080,
            path: request.uri,
            method: request.method,
            headers: {
                ...request.headers,
                'x-mirror': 'true',
                'x-shadow-version': 'v2'
            }
        };

        // Send mirrored request (fire-and-forget)
        const req = https.request(options);
        if (request.body && request.body.data) {
            req.write(Buffer.from(request.body.data, request.body.encoding));
        }
        req.end();
    }

    // Return original request (no modifications)
    return request;
};
```

**Features:**
- ⚠️ Lambda@Edge erforderlich (Custom Code)
- ✅ Sample percentage via JavaScript `Math.random()`
- ✅ Custom headers supported
- ⚠️ Zusätzliche Kosten für Lambda Invocations

**AWS Regions:** Lambda@Edge muss in `us-east-1` deployed werden

---

### 9. GCP API Gateway (⚠️ Workaround - Cloud Functions)

**Mechanismus:** Cloud Functions

**GAL Config:**

```yaml
global_config:
  gcp_apigateway:
    api_id: "my-api"
    project_id: "my-project"
    # Request Mirroring Workaround
    mirroring_workaround: "cloud_functions"
    mirroring_cloud_function_url: "https://us-central1-my-project.cloudfunctions.net/mirror-traffic"
```

**Cloud Function (Nutzer muss erstellen):**

```javascript
// Cloud Function für Request Mirroring
const axios = require('axios');

exports.mirrorTraffic = async (req, res) => {
    // Sample 50% of requests
    if (Math.random() < 0.5) {
        // Mirror request to shadow backend
        try {
            await axios({
                method: req.method,
                url: `http://shadow-api-v2.internal:8080${req.path}`,
                headers: {
                    ...req.headers,
                    'x-mirror': 'true',
                    'x-shadow-version': 'v2'
                },
                data: req.body,
                timeout: 5000
            });
        } catch (error) {
            // Ignore errors from shadow backend
            console.error('Mirror request failed:', error.message);
        }
    }

    // Always return success (don't block primary request)
    res.status(200).send('OK');
};
```

**Features:**
- ⚠️ Cloud Functions erforderlich (Custom Code)
- ✅ Sample percentage via JavaScript `Math.random()`
- ✅ Custom headers supported
- ⚠️ Zusätzliche Kosten für Cloud Functions Invocations

---

## Häufige Anwendungsfälle

### 1. Canary Deployment (5% → 100%)

**Schrittweise neue Version mit Shadow Traffic testen:**

```yaml
# Phase 1: 5% Shadow Traffic
mirroring:
  enabled: true
  targets:
    - name: canary-v2
      upstream:
        host: api-v2.internal
        port: 8080
      sample_percentage: 5.0  # Start mit 5%
```

**Rollout-Plan:**
1. **Woche 1:** 5% Shadow Traffic → Metriken überwachen
2. **Woche 2:** 25% Shadow Traffic → Bug-Reports prüfen
3. **Woche 3:** 50% Shadow Traffic → Performance validieren
4. **Woche 4:** 100% Shadow Traffic → Full Production Test
5. **Woche 5:** Traffic Splitting aktivieren (Feature 5) → Echte User-Requests

---

### 2. Performance Testing unter realer Last

**Shadow Backend Performance messen:**

```yaml
mirroring:
  enabled: true
  targets:
    - name: performance-test
      upstream:
        host: new-api-optimized.internal
        port: 8080
      sample_percentage: 100.0  # Alle Requests
      headers:
        X-Test-Run: "performance-test-2024-01"
```

**Metriken sammeln:**
```bash
# Shadow Backend Prometheus Metrics
curl http://new-api-optimized.internal:8080/metrics | grep http_request_duration

# CloudWatch Logs (AWS)
aws logs tail /aws/apigateway/shadow-backend --follow
```

---

### 3. Bug Detection vor Production Rollout

**Neue Version mit Shadow Traffic testen:**

```yaml
mirroring:
  enabled: true
  targets:
    - name: bug-detection-v2
      upstream:
        host: api-v2-staging.internal
        port: 8080
      sample_percentage: 50.0
      headers:
        X-Environment: "shadow"
        X-Bug-Tracking: "enabled"
```

**Error Tracking aktivieren:**
```python
# Shadow Backend Error Handler
@app.errorhandler(Exception)
def handle_shadow_error(error):
    if request.headers.get('X-Environment') == 'shadow':
        # Log error to Sentry/DataDog
        sentry.capture_exception(error)
        # Don't crash - shadow errors are ignored
        return jsonify({"error": "shadow"}), 500
    else:
        # Production errors should crash
        raise error
```

---

### 4. Multi-Version Testing (A/B/C Testing)

**3 Versionen gleichzeitig testen:**

```yaml
mirroring:
  enabled: true
  targets:
    - name: shadow-v2
      upstream:
        host: api-v2.internal
        port: 8080
      sample_percentage: 33.0  # 33% v2
      headers:
        X-Version: "v2"

    - name: shadow-v3
      upstream:
        host: api-v3.internal
        port: 8080
      sample_percentage: 33.0  # 33% v3
      headers:
        X-Version: "v3"
```

**Result:**
- 33% Requests → v2 Shadow Backend
- 33% Requests → v3 Shadow Backend
- 34% Requests → Kein Shadow (nur Primary)

---

### 5. Data Collection für Machine Learning

**Requests für ML Training sammeln:**

```yaml
mirroring:
  enabled: true
  targets:
    - name: ml-data-collector
      upstream:
        host: ml-collector.internal
        port: 8080
      sample_percentage: 10.0  # 10% sampling
      headers:
        X-Data-Collection: "ml-training"
        X-Dataset: "production-2024"
```

**ML Collector Backend:**
```python
@app.post("/api/users")
def collect_data():
    # Store request/response for ML training
    request_data = {
        "timestamp": datetime.utcnow(),
        "request": request.json,
        "headers": dict(request.headers)
    }

    # Save to S3/BigQuery
    save_to_dataset(request_data)

    return {"status": "collected"}, 200
```

---

## Best Practices

### 1. Sample Percentage sinnvoll wählen

**Empfohlene Werte:**

| Use Case | Sample % | Begründung |
|----------|----------|------------|
| **Canary Start** | 1-5% | Minimales Risiko, erste Fehler finden |
| **Performance Testing** | 25-50% | Repräsentative Last, nicht zu teuer |
| **Full Production Test** | 100% | Finale Validation vor Rollout |
| **Data Collection** | 5-10% | Genug Daten, nicht zu viele Kosten |
| **Bug Detection** | 50-100% | Maximale Coverage für Fehler |

### 2. Shadow Backend Monitoring

**Wichtige Metriken überwachen:**

```yaml
# Prometheus Metrics für Shadow Backend
http_request_duration_seconds{backend="shadow"}
http_request_errors_total{backend="shadow"}
http_request_count{backend="shadow"}
```

**Alerts einrichten:**
```yaml
# Prometheus Alert für Shadow Errors
- alert: ShadowBackendHighErrorRate
  expr: |
    rate(http_request_errors_total{backend="shadow"}[5m]) > 0.05
  for: 10m
  annotations:
    summary: "Shadow Backend hat erhöhte Error Rate (>5%)"
```

### 3. Timeout konfigurieren

**Shadow Requests sollten kurze Timeouts haben:**

```yaml
mirroring:
  targets:
    - name: shadow
      timeout: "3s"  # Kurzer Timeout (Standard: 5s)
```

**Warum?**
- Shadow Requests sollten Primary Request nicht verzögern
- Langsame Shadow Backends sollten Primary nicht blockieren

### 4. Headers für Shadow identifizieren

**Immer X-Mirror Header setzen:**

```yaml
mirroring:
  targets:
    - name: shadow
      headers:
        X-Mirror: "true"              # Shadow Backend kann ignorieren
        X-Shadow-Version: "v2"        # Versionierung
        X-Request-ID: "{{uuid}}"      # Tracing
        X-Environment: "shadow"       # Environment Tag
```

**Shadow Backend kann dann:**
- Errors ignorieren (nicht zu Sentry senden)
- Separate Logging aktivieren
- Separate Metriken sammeln

### 5. Shadow Response ignorieren

**Wichtig:** Shadow Response sollte NIEMALS die Primary Response beeinflussen!

```python
# Shadow Backend Error Handling
@app.errorhandler(500)
def handle_error(error):
    if request.headers.get('X-Mirror') == 'true':
        # Shadow Request - Error ignorieren
        logger.warning(f"Shadow request error: {error}")
        return {"status": "shadow_error"}, 500
    else:
        # Primary Request - Error propagieren
        raise error
```

### 6. Costs überwachen (Cloud Provider)

**Cloud Provider berechnen Shadow Requests:**

| Provider | Kosten | Hinweise |
|----------|--------|----------|
| **AWS Lambda@Edge** | $0.60 / 1M requests | Zusätzlich zu API Gateway |
| **GCP Cloud Functions** | $0.40 / 1M invocations | Zusätzlich zu API Gateway |
| **Azure APIM** | Inkludiert | Keine zusätzlichen Kosten für `send-request` |

**Empfehlung:** Sample Percentage reduzieren (z.B. 10% statt 100%), um Kosten zu sparen.

---

## Request Mirroring Testen

### 1. Lokales Testing mit Docker Compose

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  gateway:
    image: envoyproxy/envoy:v1.27-latest
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml
    ports:
      - "8080:8080"

  primary-backend:
    image: kennethreitz/httpbin
    environment:
      - SERVICE_NAME=primary
    ports:
      - "8081:80"

  shadow-backend:
    image: kennethreitz/httpbin
    environment:
      - SERVICE_NAME=shadow
    ports:
      - "8082:80"
```

**Test ausführen:**

```bash
# Gateway starten
docker-compose up -d

# Request senden
curl http://localhost:8080/api/users

# Primary Backend Logs
docker-compose logs primary-backend

# Shadow Backend Logs
docker-compose logs shadow-backend
```

### 2. Sample Percentage validieren

**Test-Script:**

```bash
#!/bin/bash
# test-mirroring-percentage.sh

TOTAL_REQUESTS=1000
GATEWAY_URL="http://localhost:8080/api/users"
SHADOW_URL="http://localhost:8082/metrics"

# Send requests
for i in $(seq 1 $TOTAL_REQUESTS); do
    curl -s $GATEWAY_URL > /dev/null
done

# Check shadow backend request count
SHADOW_REQUESTS=$(curl -s $SHADOW_URL | grep 'http_requests_total' | awk '{print $2}')

echo "Total Requests: $TOTAL_REQUESTS"
echo "Shadow Requests: $SHADOW_REQUESTS"
echo "Sample Percentage: $(echo "scale=2; $SHADOW_REQUESTS / $TOTAL_REQUESTS * 100" | bc)%"
```

**Expected Output (50% sampling):**
```
Total Requests: 1000
Shadow Requests: 503
Sample Percentage: 50.30%
```

### 3. Custom Headers validieren

**Test-Script:**

```bash
# Request mit Header-Inspektion
curl -v http://localhost:8080/api/users 2>&1 | grep -i 'x-mirror'

# Shadow Backend Request prüfen
docker-compose exec shadow-backend cat /var/log/requests.log | grep 'X-Mirror'
```

**Expected Output:**
```
X-Mirror: true
X-Shadow-Version: v2
```

---

## Troubleshooting

### Problem 1: Shadow Requests kommen nicht an

**Symptome:**
- Primary Backend funktioniert
- Shadow Backend erhält keine Requests

**Lösungen:**

1. **Provider Logs prüfen:**
```bash
# Envoy
docker logs gateway-container 2>&1 | grep mirror

# Nginx
nginx -T | grep mirror

# HAProxy
haproxy -c -f /etc/haproxy/haproxy.cfg
```

2. **Network Connectivity testen:**
```bash
# Von Gateway zu Shadow Backend
docker exec gateway-container curl http://shadow-backend:8080/health
```

3. **Sample Percentage erhöhen:**
```yaml
# Temporär auf 100% setzen
mirroring:
  targets:
    - sample_percentage: 100.0
```

---

### Problem 2: Shadow Backend verlangsamt Primary Requests

**Symptome:**
- Primary Response Latency erhöht
- Gateway Logs zeigen Timeouts

**Lösungen:**

1. **Timeout reduzieren:**
```yaml
mirroring:
  targets:
    - timeout: "1s"  # Sehr kurzer Timeout
```

2. **Fire-and-forget sicherstellen:**
```bash
# Envoy: async_client verwendet?
envoy.yaml: request_mirror_policies (automatisch async)

# Nginx: mirror_request_body on?
nginx.conf: proxy_ignore_client_abort on;
```

3. **Sample Percentage reduzieren:**
```yaml
mirroring:
  targets:
    - sample_percentage: 25.0  # Weniger Last
```

---

### Problem 3: Cloud Provider Workaround funktioniert nicht

**AWS Lambda@Edge:**

```bash
# Lambda Function Logs prüfen
aws logs tail /aws/lambda/us-east-1.mirror-traffic --follow

# Lambda Execution Role prüfen
aws iam get-role --role-name lambda-edge-execution-role

# CloudFront Distribution prüfen
aws cloudfront get-distribution --id E1234567890ABC
```

**GCP Cloud Functions:**

```bash
# Function Logs prüfen
gcloud functions logs read mirror-traffic --limit=50

# Function Status prüfen
gcloud functions describe mirror-traffic --region=us-central1

# Network Connectivity testen
gcloud functions call mirror-traffic --data='{"test":"true"}'
```

---

### Problem 4: Sample Percentage zu hoch/niedrig

**Symptome:**
- Erwartete 50%, aber nur 30% Shadow Requests
- Oder: 50% konfiguriert, aber 100% Shadow Requests

**Lösungen:**

1. **Sample Percentage Validation:**
```python
# Test-Script
import requests
import time

TOTAL = 1000
shadow_count = 0

for _ in range(TOTAL):
    response = requests.get("http://localhost:8080/api/users")
    # Check if shadow backend was called (via custom header or logs)
    shadow_count += check_shadow_backend_called()
    time.sleep(0.01)

print(f"Actual Sample %: {shadow_count / TOTAL * 100:.2f}%")
```

2. **Provider-spezifische Debugging:**

**Envoy:** `runtime_fraction` prüfen
```yaml
runtime_fraction:
  default_value:
    numerator: 50      # Check this value
    denominator: HUNDRED
```

**Nginx:** `split_clients` prüfen
```nginx
split_clients "${remote_addr}${request_uri}" $mirror_flag {
    50%     "1";    # Check this percentage
    *       "0";
}
```

---

## Verwandte Themen

- [Traffic Splitting Guide](TRAFFIC_SPLITTING.md) - A/B Testing, Canary Deployments
- [Provider Übersicht](PROVIDERS.md) - Provider-spezifische Features
- [Best Practices](BEST_PRACTICES.md) - Allgemeine Best Practices

---

**Status:** ✅ Request Mirroring ist implementiert für 9/9 Provider (Feature 6 abgeschlossen)
**Version:** GAL v1.4.0+
**Letzte Aktualisierung:** 2025-10-22
