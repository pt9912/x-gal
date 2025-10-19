# Timeout & Retry Policies - Umfassender Leitfaden

Dieser Leitfaden beschreibt, wie man Timeout- und Retry-Richtlinien in GAL (Gateway Abstraction Layer) konfiguriert, um die Zuverlässigkeit und Resilienz von API-Gateway-Deployments zu verbessern.

## Inhaltsverzeichnis

1. [Übersicht](#ubersicht)
2. [Schnellstart](#schnellstart)
3. [Konfigurationsoptionen](#konfigurationsoptionen)
4. [Provider-Implementierungen](#provider-implementierungen)
5. [Häufige Anwendungsfälle](#haufige-anwendungsfalle)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Provider-Vergleich](#provider-vergleich)

---

## Übersicht

### Was sind Timeouts?

**Timeouts** definieren maximale Wartezeiten für verschiedene Phasen der Kommunikation zwischen Gateway und Upstream-Services:

- **Connection Timeout**: Maximale Zeit zum Aufbau einer TCP-Verbindung
- **Send Timeout**: Maximale Zeit zum Senden einer Request an den Upstream
- **Read Timeout**: Maximale Zeit zum Empfangen einer Response vom Upstream
- **Idle Timeout**: Maximale Zeit für inaktive Keep-Alive-Verbindungen

### Was sind Retries?

**Retries** (Wiederholungsversuche) ermöglichen es dem Gateway, fehlgeschlagene Requests automatisch zu wiederholen, bevor ein Fehler an den Client zurückgegeben wird.

**Retry-Bedingungen** bestimmen, wann ein Request wiederholt wird:
- `connect_timeout`: Bei Connection-Timeouts
- `http_5xx`: Bei allen 5xx HTTP-Statuscodes
- `http_502`, `http_503`, `http_504`: Bei spezifischen 5xx-Codes
- `reset`: Bei Connection-Reset
- `refused`: Bei Connection-Refused

**Retry-Strategien**:
- **Exponential Backoff**: Wartezeit verdoppelt sich mit jedem Versuch (empfohlen)
- **Linear Backoff**: Konstante Wartezeit zwischen Versuchen

### Warum sind Timeouts & Retries wichtig?

1. **Resilienz**: Automatische Wiederholung bei transienten Fehlern
2. **Verfügbarkeit**: Vermeidung von Request-Hangs bei langsamen Upstreams
3. **Performance**: Schnelleres Failover zu gesunden Servern
4. **Benutzerfreundlichkeit**: Bessere User Experience durch kürzere Wartezeiten
5. **Ressourcen-Schonung**: Vermeidung von Thread-Blockierung

---

## Schnellstart

### Beispiel 1: Basic Timeout-Konfiguration

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "5s"
          send: "30s"
          read: "60s"
          idle: "300s"
```

**Erklärung**:
- Connection-Aufbau: Max. 5 Sekunden
- Request-Senden: Max. 30 Sekunden
- Response-Empfang: Max. 60 Sekunden
- Idle-Verbindung: Max. 5 Minuten

### Beispiel 2: Basic Retry-Konfiguration

```yaml
services:
  - name: api_service
    upstream:
      host: api-backend
      port: 8080
    routes:
      - path_prefix: /api
        retry:
          enabled: true
          attempts: 3
          backoff: exponential
          base_interval: "25ms"
          max_interval: "250ms"
          retry_on:
            - connect_timeout
            - http_5xx
```

**Erklärung**:
- Maximal 3 Wiederholungsversuche
- Exponential Backoff: 25ms → 50ms → 100ms
- Wiederholung bei: Connection-Timeout oder 5xx-Fehler

### Beispiel 3: Timeout & Retry kombiniert (EMPFOHLEN)

```yaml
services:
  - name: payment_service
    upstream:
      host: payment-backend
      port: 8080
    routes:
      - path_prefix: /api/payments
        timeout:
          connect: "3s"
          send: "10s"
          read: "30s"
        retry:
          enabled: true
          attempts: 3
          backoff: exponential
          base_interval: "50ms"
          max_interval: "500ms"
          retry_on:
            - connect_timeout
            - http_502
            - http_503
            - http_504
```

**Erklärung**:
- Kurze Timeouts für schnelles Failover
- Aggressive Retry-Strategie für kritische Payment-API
- Spezifische 5xx-Codes statt generischem `http_5xx`

---

## Konfigurationsoptionen

### TimeoutConfig

```yaml
timeout:
  connect: "5s"      # Connection-Timeout (default: "5s")
  send: "30s"        # Send-Timeout (default: "30s")
  read: "60s"        # Read-Timeout (default: "60s")
  idle: "300s"       # Idle-Timeout (default: "300s")
```

**Parameter**:

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `connect` | string | `"5s"` | Maximale Zeit zum Aufbau der TCP-Verbindung zum Upstream |
| `send` | string | `"30s"` | Maximale Zeit zum Senden des Requests an den Upstream |
| `read` | string | `"60s"` | Maximale Zeit zum Empfangen der Response vom Upstream |
| `idle` | string | `"300s"` | Maximale Zeit für inaktive Keep-Alive-Verbindungen (5 Minuten) |

**Format**: Zeitangaben als String mit Suffix:
- `s` = Sekunden (z.B. `"5s"`, `"30s"`)
- `m` = Minuten (z.B. `"1m"`, `"10m"`)
- `ms` = Millisekunden (z.B. `"500ms"`)

### RetryConfig

```yaml
retry:
  enabled: true                  # Retry aktivieren (default: true)
  attempts: 3                    # Anzahl der Versuche (default: 3)
  backoff: exponential           # Backoff-Strategie (default: "exponential")
  base_interval: "25ms"          # Basis-Intervall (default: "25ms")
  max_interval: "250ms"          # Maximales Intervall (default: "250ms")
  retry_on:                      # Retry-Bedingungen (default: ["connect_timeout", "http_5xx"])
    - connect_timeout
    - http_5xx
    - http_502
    - http_503
```

**Parameter**:

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `enabled` | boolean | `true` | Aktiviert/Deaktiviert Retry-Logik |
| `attempts` | integer | `3` | Anzahl der Wiederholungsversuche (inkl. Originalversuch) |
| `backoff` | string | `"exponential"` | Backoff-Strategie: `"exponential"` oder `"linear"` |
| `base_interval` | string | `"25ms"` | Basis-Intervall für Exponential Backoff |
| `max_interval` | string | `"250ms"` | Maximales Intervall zwischen Retries |
| `retry_on` | list[string] | `["connect_timeout", "http_5xx"]` | Liste der Retry-Bedingungen |

**Retry-Bedingungen**:

| Bedingung | Beschreibung |
|-----------|--------------|
| `connect_timeout` | Wiederholung bei Connection-Timeout |
| `http_5xx` | Wiederholung bei allen 5xx HTTP-Statuscodes |
| `http_502` | Wiederholung bei HTTP 502 Bad Gateway |
| `http_503` | Wiederholung bei HTTP 503 Service Unavailable |
| `http_504` | Wiederholung bei HTTP 504 Gateway Timeout |
| `retriable_4xx` | Wiederholung bei retriable 4xx-Codes (z.B. 429 Too Many Requests) |
| `reset` | Wiederholung bei Connection-Reset |
| `refused` | Wiederholung bei Connection-Refused |

**Backoff-Strategien**:

1. **Exponential Backoff** (empfohlen):
   - Versuch 1: Sofort
   - Versuch 2: Nach `base_interval` (z.B. 25ms)
   - Versuch 3: Nach `base_interval * 2` (z.B. 50ms)
   - Versuch 4: Nach `base_interval * 4` (z.B. 100ms)
   - Maximum: `max_interval`

2. **Linear Backoff**:
   - Versuch 1: Sofort
   - Versuch 2: Nach `base_interval` (z.B. 25ms)
   - Versuch 3: Nach `base_interval` (z.B. 25ms)
   - Versuch 4: Nach `base_interval` (z.B. 25ms)

---

## Provider-Implementierungen

### Envoy

**Timeout-Konfiguration**:
```yaml
# Envoy Static Configuration (envoy.yaml)
clusters:
  - name: api_service_cluster
    connect_timeout: 5s
    # ...

routes:
  - route:
      timeout: 60s          # read timeout
      idle_timeout: 300s    # idle timeout
```

**Retry-Konfiguration**:
```yaml
routes:
  - route:
      retry_policy:
        num_retries: 3
        per_try_timeout: 25ms
        retry_on: "connect-failure,5xx"
        retriable_status_codes: [502, 503, 504]
```

**Besonderheiten**:
- Cluster-Level: `connect_timeout`
- Route-Level: `timeout` (read), `idle_timeout`
- Retry-Conditions: `connect-failure`, `5xx`, `reset`, `refused`
- `retriable_status_codes` für spezifische 5xx-Codes

**GAL-Mapping**:
- `connect_timeout` → cluster.connect_timeout
- `http_5xx` → retry_on: "5xx"
- `http_502` → retriable_status_codes: [502]

### Kong

**Timeout-Konfiguration**:
```yaml
services:
  - name: api_service
    connect_timeout: 10000     # Millisekunden
    read_timeout: 120000       # Millisekunden
    write_timeout: 60000       # Millisekunden
```

**Retry-Konfiguration**:
```yaml
services:
  - name: api_service
    retries: 3
```

**Besonderheiten**:
- Service-Level: Alle Timeouts in **Millisekunden**
- Retry: Nur Anzahl der Versuche, keine konditionalen Retries
- Keine native Backoff-Konfiguration

**GAL-Mapping**:
- `timeout.connect: "10s"` → `connect_timeout: 10000`
- `timeout.read: "120s"` → `read_timeout: 120000`
- `timeout.send: "60s"` → `write_timeout: 60000`
- `retry.attempts: 3` → `retries: 3`

### APISIX

**Timeout-Konfiguration**:
```json
{
  "routes": [{
    "plugins": {
      "timeout": {
        "connect": 10,
        "send": 60,
        "read": 120
      }
    }
  }]
}
```

**Retry-Konfiguration**:
```json
{
  "routes": [{
    "plugins": {
      "proxy-retry": {
        "retries": 3,
        "retry_timeout": 500,
        "vars": [
          ["status", "==", 502],
          ["status", "==", 503]
        ]
      }
    }
  }]
}
```

**Besonderheiten**:
- Plugin-basiert: `timeout` Plugin
- Retry via `proxy-retry` Plugin
- Timeouts in **Sekunden**
- Retry-Conditions via `vars` (Status-Code-Filter)

**GAL-Mapping**:
- `timeout.connect: "10s"` → `timeout.connect: 10`
- `retry_on: [http_502, http_503]` → `vars: [["status", "==", 502], ...]`

### Traefik

**Timeout-Konfiguration**:
```yaml
services:
  api_service_service:
    loadBalancer:
      serversTransport:
        forwardingTimeouts:
          dialTimeout: 10s
          responseHeaderTimeout: 120s
          idleConnTimeout: 600s
```

**Retry-Konfiguration**:
```yaml
middlewares:
  api_service_router_0_retry:
    retry:
      attempts: 5
      initialInterval: 50ms
```

**Besonderheiten**:
- Service-Level: `serversTransport.forwardingTimeouts`
- Retry als **Middleware** konfiguriert
- `dialTimeout` = Connection Timeout
- `responseHeaderTimeout` = Read Timeout
- `idleConnTimeout` = Idle Timeout

**GAL-Mapping**:
- `timeout.connect` → `dialTimeout`
- `timeout.read` → `responseHeaderTimeout`
- `timeout.idle` → `idleConnTimeout`
- `retry` → Middleware erstellen

### Nginx

**Timeout-Konfiguration**:
```nginx
location /api {
    proxy_connect_timeout 10s;
    proxy_send_timeout 60s;
    proxy_read_timeout 120s;
}
```

**Retry-Konfiguration**:
```nginx
location /api {
    proxy_next_upstream timeout http_502 http_503;
    proxy_next_upstream_tries 3;
    proxy_next_upstream_timeout 500ms;
}
```

**Besonderheiten**:
- Location-Level: `proxy_*_timeout` Direktiven
- Retry via `proxy_next_upstream`
- Retry-Conditions: `timeout`, `error`, `http_502`, `http_503`, etc.

**GAL-Mapping**:
- `connect_timeout` → `proxy_next_upstream timeout`
- `http_502` → `proxy_next_upstream http_502`
- `attempts: 3` → `proxy_next_upstream_tries 3`

### HAProxy

**Timeout-Konfiguration**:
```haproxy
backend backend_api_service
    timeout connect 10s
    timeout server 120s
    timeout client 600s
```

**Retry-Konfiguration**:
```haproxy
backend backend_api_service
    retry-on conn-failure 502 503
    retries 5
```

**Besonderheiten**:
- Backend-Level: `timeout connect/server/client`
- Retry via `retry-on` Direktive
- Retry-Conditions: `conn-failure`, `empty-response`, HTTP-Statuscodes

**GAL-Mapping**:
- `timeout.connect` → `timeout connect`
- `timeout.read` → `timeout server`
- `timeout.idle` → `timeout client`
- `connect_timeout` → `retry-on conn-failure`
- `http_503` → `retry-on 503`

---

## Häufige Anwendungsfälle

### 1. REST API mit konservativen Timeouts

**Use Case**: Standard-REST-API mit angemessenen Timeouts für normale Workloads.

```yaml
services:
  - name: rest_api
    upstream:
      host: api.internal
      port: 8080
    routes:
      - path_prefix: /api
        timeout:
          connect: "5s"
          send: "30s"
          read: "60s"
          idle: "300s"
```

**Erklärung**: Standard-Timeouts für die meisten APIs geeignet.

### 2. Payment API mit aggressiven Retries

**Use Case**: Kritische Payment-API mit hohen Verfügbarkeitsanforderungen.

```yaml
services:
  - name: payment_api
    upstream:
      host: payment.internal
      port: 8080
    routes:
      - path_prefix: /api/payments
        timeout:
          connect: "3s"
          send: "10s"
          read: "30s"
        retry:
          enabled: true
          attempts: 5
          backoff: exponential
          base_interval: "50ms"
          max_interval: "500ms"
          retry_on:
            - connect_timeout
            - http_502
            - http_503
            - http_504
```

**Erklärung**:
- Kurze Timeouts für schnelles Failover
- 5 Retry-Versuche (mehr als Standard)
- Nur spezifische 5xx-Codes (nicht alle)

### 3. Long-Running Operations

**Use Case**: Batch-Processing oder Report-Generierung mit langen Laufzeiten.

```yaml
services:
  - name: batch_api
    upstream:
      host: batch.internal
      port: 8080
    routes:
      - path_prefix: /api/batch
        timeout:
          connect: "10s"
          send: "60s"
          read: "600s"       # 10 Minuten
          idle: "3600s"      # 1 Stunde
        retry:
          enabled: false      # Keine Retries bei Long-Running
```

**Erklärung**:
- Sehr lange Read-Timeouts (10 Minuten)
- Retry deaktiviert (Long-Running Operations sollten nicht wiederholt werden)

### 4. Microservice mit Circuit Breaker

**Use Case**: Microservice mit Circuit Breaker für schnelles Failover.

```yaml
services:
  - name: user_service
    upstream:
      host: user.internal
      port: 8080
    routes:
      - path_prefix: /api/users
        timeout:
          connect: "2s"
          send: "10s"
          read: "20s"
        retry:
          enabled: true
          attempts: 3
          backoff: exponential
          base_interval: "25ms"
          max_interval: "100ms"
          retry_on:
            - connect_timeout
            - http_503
        circuit_breaker:
          enabled: true
          max_failures: 5
          timeout: "30s"
```

**Erklärung**:
- Kurze Timeouts + Circuit Breaker = schnelles Failover
- Retry nur bei Connect-Timeout und 503 (Service Unavailable)

### 5. gRPC Service

**Use Case**: gRPC-Service mit speziellen Timeout-Anforderungen.

```yaml
services:
  - name: grpc_service
    type: grpc
    protocol: http2
    upstream:
      host: grpc.internal
      port: 50051
    routes:
      - path_prefix: /
        timeout:
          connect: "5s"
          send: "30s"
          read: "120s"       # gRPC Streams können länger dauern
        retry:
          enabled: true
          attempts: 3
          retry_on:
            - reset              # Connection-Reset häufig bei gRPC
            - connect_timeout
```

**Erklärung**:
- Längere Read-Timeouts für gRPC-Streams
- Retry bei `reset` (häufig bei gRPC-Problemen)

### 6. External API mit Rate Limiting

**Use Case**: Externe API mit Rate Limiting und konservativen Retries.

```yaml
services:
  - name: external_api
    upstream:
      host: api.external.com
      port: 443
    routes:
      - path_prefix: /api
        timeout:
          connect: "10s"
          send: "30s"
          read: "60s"
        retry:
          enabled: true
          attempts: 3
          backoff: exponential
          base_interval: "100ms"   # Längerer Backoff für externe API
          max_interval: "1s"
          retry_on:
            - connect_timeout
            - http_503
            - retriable_4xx        # 429 Too Many Requests
```

**Erklärung**:
- Längerer Backoff für externe APIs
- Retry bei `retriable_4xx` (429 Rate Limit)

### 7. Multi-Datacenter mit Failover

**Use Case**: Multi-Datacenter-Deployment mit schnellem Failover.

```yaml
services:
  - name: api_service
    upstream:
      targets:
        - host: api-dc1.internal
          port: 8080
        - host: api-dc2.internal
          port: 8080
      load_balancer:
        algorithm: round_robin
    routes:
      - path_prefix: /api
        timeout:
          connect: "2s"        # Kurz für schnelles Failover
          send: "10s"
          read: "30s"
        retry:
          enabled: true
          attempts: 2          # Nur 2 Versuche (Multi-DC hat viele Server)
          backoff: linear
          base_interval: "10ms"
          retry_on:
            - connect_timeout
            - reset
```

**Erklärung**:
- Sehr kurze Connection-Timeouts (2s)
- Linear Backoff für schnelles Failover zwischen DCs

### 8. WebSocket mit Retry

**Use Case**: WebSocket-Verbindungen mit Retry bei Connection-Fehlern.

```yaml
services:
  - name: websocket_service
    upstream:
      host: ws.internal
      port: 8080
    routes:
      - path_prefix: /ws
        websocket:
          enabled: true
          idle_timeout: "600s"
        timeout:
          connect: "5s"
          send: "30s"
          read: "600s"       # Lange Timeouts für WebSocket
        retry:
          enabled: true
          attempts: 3
          retry_on:
            - connect_timeout
            - reset
```

**Erklärung**:
- Lange Read-Timeouts für WebSocket-Verbindungen
- Retry nur bei Connection-Fehlern (nicht bei Protokollfehlern)

### 9. Idempotente API mit vielen Retries

**Use Case**: Idempotente API (GET/PUT/DELETE) mit vielen Retry-Versuchen.

```yaml
services:
  - name: idempotent_api
    upstream:
      host: api.internal
      port: 8080
    routes:
      - path_prefix: /api/data
        methods:
          - GET
          - PUT
          - DELETE
        timeout:
          connect: "5s"
          send: "30s"
          read: "60s"
        retry:
          enabled: true
          attempts: 7          # Viele Versuche (idempotent)
          backoff: exponential
          base_interval: "25ms"
          max_interval: "1s"
          retry_on:
            - connect_timeout
            - http_5xx
            - reset
```

**Erklärung**:
- Viele Retry-Versuche (7) sind sicher bei idempotenten Operationen
- Exponential Backoff mit höherem Maximum (1s)

### 10. Non-Idempotente API (POST) ohne Retry

**Use Case**: Non-idempotente API (POST) ohne automatische Retries.

```yaml
services:
  - name: order_api
    upstream:
      host: order.internal
      port: 8080
    routes:
      - path_prefix: /api/orders
        methods:
          - POST
        timeout:
          connect: "5s"
          send: "30s"
          read: "60s"
        retry:
          enabled: false       # Keine Retries bei POST (non-idempotent)
```

**Erklärung**:
- POST-Requests sollten nicht automatisch wiederholt werden
- Risiko von Duplikaten (z.B. doppelte Bestellungen)

---

## Best Practices

### 1. Verwende Timeouts immer

**❌ Schlecht**:
```yaml
routes:
  - path_prefix: /api
    # Keine Timeout-Konfiguration
```

**✅ Gut**:
```yaml
routes:
  - path_prefix: /api
    timeout:
      connect: "5s"
      send: "30s"
      read: "60s"
```

**Begründung**: Ohne Timeouts können langsame Upstreams alle Gateway-Threads blockieren.

### 2. Kombiniere Timeouts mit Retries

**❌ Schlecht**:
```yaml
routes:
  - path_prefix: /api
    timeout:
      connect: "5s"
      read: "60s"
    # Keine Retry-Konfiguration
```

**✅ Gut**:
```yaml
routes:
  - path_prefix: /api
    timeout:
      connect: "5s"
      read: "60s"
    retry:
      enabled: true
      attempts: 3
      retry_on:
        - connect_timeout
        - http_5xx
```

**Begründung**: Retries erhöhen die Verfügbarkeit bei transienten Fehlern.

### 3. Verwende Exponential Backoff

**❌ Schlecht**:
```yaml
retry:
  backoff: linear
  base_interval: "25ms"
```

**✅ Gut**:
```yaml
retry:
  backoff: exponential
  base_interval: "25ms"
  max_interval: "250ms"
```

**Begründung**: Exponential Backoff verhindert Thundering-Herd-Probleme.

### 4. Passe Timeouts an den Use Case an

**❌ Schlecht** (One-Size-Fits-All):
```yaml
# Gleiche Timeouts für alle Routes
timeout:
  connect: "5s"
  read: "60s"
```

**✅ Gut** (Use-Case-spezifisch):
```yaml
# Kurze Timeouts für schnelle Endpoints
- path_prefix: /api/health
  timeout:
    connect: "2s"
    read: "5s"

# Lange Timeouts für Report-Generierung
- path_prefix: /api/reports
  timeout:
    connect: "10s"
    read: "600s"
```

**Begründung**: Unterschiedliche Endpoints haben unterschiedliche Performance-Charakteristiken.

### 5. Deaktiviere Retry für Non-Idempotente Operationen

**❌ Schlecht**:
```yaml
- path_prefix: /api/orders
  methods:
    - POST
  retry:
    enabled: true     # ❌ POST ist nicht idempotent!
```

**✅ Gut**:
```yaml
- path_prefix: /api/orders
  methods:
    - POST
  retry:
    enabled: false    # ✅ Keine Retries für POST
```

**Begründung**: POST-Requests können zu Duplikaten führen (z.B. doppelte Bestellungen).

### 6. Verwende spezifische Retry-Bedingungen

**❌ Schlecht**:
```yaml
retry_on:
  - http_5xx         # ❌ Zu allgemein
```

**✅ Gut**:
```yaml
retry_on:
  - connect_timeout
  - http_502         # ✅ Spezifische Codes
  - http_503
  - http_504
```

**Begründung**: Nicht alle 5xx-Fehler sind retriable (z.B. 501 Not Implemented).

### 7. Setze maximale Retry-Versuche

**❌ Schlecht**:
```yaml
retry:
  attempts: 10       # ❌ Zu viele Versuche
```

**✅ Gut**:
```yaml
retry:
  attempts: 3        # ✅ Standard: 3 Versuche
```

**Begründung**: Zu viele Retries erhöhen die Latenz und können Upstreams überlasten.

---

## Troubleshooting

### Problem 1: Requests timeout zu schnell

**Symptome**:
- Viele 504 Gateway Timeout Fehler
- Logs zeigen "upstream timed out"

**Lösung**:
```yaml
timeout:
  read: "120s"      # ✅ Erhöhe Read-Timeout
```

**Diagnose**:
```bash
# Provider-spezifische Logs prüfen
kubectl logs -n gateway gateway-pod | grep timeout
```

### Problem 2: Retries funktionieren nicht

**Symptome**:
- Fehler werden nicht automatisch wiederholt
- Logs zeigen nur einen Versuch

**Mögliche Ursachen**:
1. Retry nicht aktiviert:
```yaml
retry:
  enabled: true     # ✅ Muss true sein
```

2. Falsche Retry-Bedingungen:
```yaml
retry_on:
  - http_502        # ✅ Prüfe, ob der tatsächliche Fehlercode enthalten ist
```

3. Provider-spezifische Limitierungen:
- Kong: Keine konditionalen Retries (nur Anzahl)
- Traefik: Retry erfordert Middleware

### Problem 3: Zu viele Retries überlasten Backend

**Symptome**:
- Backend zeigt hohe Last
- Cascading Failures

**Lösung**:
```yaml
retry:
  attempts: 2               # ✅ Reduziere Versuche
  base_interval: "100ms"    # ✅ Erhöhe Backoff
  max_interval: "1s"
```

### Problem 4: Connection Timeouts zu kurz

**Symptome**:
- Viele "connection timeout" Fehler
- Backend ist langsam, aber erreichbar

**Lösung**:
```yaml
timeout:
  connect: "10s"    # ✅ Erhöhe Connection-Timeout
```

### Problem 5: Idle-Verbindungen werden zu früh geschlossen

**Symptome**:
- Keep-Alive funktioniert nicht
- Viele neue Connections

**Lösung**:
```yaml
timeout:
  idle: "600s"      # ✅ Erhöhe Idle-Timeout (10 Minuten)
```

### Problem 6: Exponential Backoff zu aggressiv

**Symptome**:
- Retries geschehen zu langsam
- Hohe Latenz bei Retry-Erfolg

**Lösung**:
```yaml
retry:
  base_interval: "10ms"     # ✅ Reduziere Base-Interval
  max_interval: "100ms"     # ✅ Reduziere Max-Interval
```

---

## Provider-Vergleich

### Feature-Matrix

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy |
|---------|-------|------|--------|---------|-------|---------|
| **Timeouts** |  |  |  |  |  |  |
| Connection Timeout | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Send/Write Timeout | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| Read Timeout | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Idle Timeout | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ |
| **Retries** |  |  |  |  |  |  |
| Retry Attempts | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Exponential Backoff | ✅ | ❌ | ⚠️ | ✅ | ❌ | ❌ |
| Linear Backoff | ✅ | ❌ | ⚠️ | ⚠️ | ✅ | ⚠️ |
| Retry Conditions | ✅ | ❌ | ✅ | ⚠️ | ✅ | ✅ |
| Status Code-based Retry | ✅ | ❌ | ✅ | ⚠️ | ✅ | ✅ |
| Per-Try Timeout | ✅ | ❌ | ✅ | ⚠️ | ✅ | ⚠️ |

**Legende**:
- ✅ = Vollständig unterstützt
- ⚠️ = Teilweise unterstützt oder Alternative
- ❌ = Nicht unterstützt

### Provider-spezifische Stärken

**Envoy**:
- ✅ Umfassendste Timeout-Konfiguration
- ✅ Granulare Retry-Bedingungen
- ✅ Per-Try-Timeout
- ✅ Retriable Status Codes

**Kong**:
- ✅ Einfache Konfiguration
- ✅ Timeouts in Millisekunden (präzise)
- ❌ Keine konditionalen Retries
- ❌ Kein Backoff

**APISIX**:
- ✅ Plugin-basiert (flexibel)
- ✅ Status Code-basierte Retries
- ⚠️ Retry-Timeout als Gesamt-Timeout
- ⚠️ Kein nativer Exponential Backoff

**Traefik**:
- ✅ Middleware-basiert (wiederverwendbar)
- ✅ Exponential Backoff
- ⚠️ Retry-Bedingungen limitiert
- ⚠️ Keine granularen Retry-Conditions

**Nginx**:
- ✅ Flexible `proxy_next_upstream` Direktive
- ✅ Status Code-basierte Retries
- ✅ Per-Versuch-Timeout
- ❌ Kein Exponential Backoff

**HAProxy**:
- ✅ `retry-on` mit vielen Bedingungen
- ✅ Status Code-basierte Retries
- ✅ Sehr stabil und performant
- ⚠️ Kein nativer Exponential Backoff

### Empfehlungen

**Für maximale Flexibilität**: **Envoy**
- Beste Retry-Konfiguration
- Granulare Timeout-Kontrolle
- Per-Try-Timeout

**Für Einfachheit**: **Kong**
- Einfache Konfiguration
- Ausreichend für die meisten Use Cases
- Gut dokumentiert

**Für Plugin-Ökosystem**: **APISIX**
- Plugin-basierte Architektur
- Flexible Erweiterbarkeit
- Lua-Scripting für Custom-Logik

**Für Cloud-Native**: **Traefik**
- Kubernetes-native
- Middleware-Ansatz
- Auto-Discovery

**Für Performance**: **Nginx** oder **HAProxy**
- Sehr performant
- Niedrige Latenz
- Battle-tested

---

## Zusammenfassung

**Timeout & Retry Policies** sind essenzielle Features für resiliente API-Gateway-Deployments:

1. **Timeouts** verhindern Request-Hangs und Thread-Blockierung
2. **Retries** erhöhen die Verfügbarkeit bei transienten Fehlern
3. **Exponential Backoff** verhindert Thundering-Herd-Probleme
4. **Provider-spezifische Implementierungen** bieten unterschiedliche Trade-offs
5. **Use-Case-spezifische Konfiguration** ist entscheidend für optimale Performance

**Nächste Schritte**:
- Implementiere Timeouts & Retries für deine Services
- Monitore Retry-Raten und Timeout-Metriken
- Tune Parameter basierend auf Produktions-Traffic
- Kombiniere mit Circuit Breaker für maximale Resilienz

**Siehe auch**:
- [Circuit Breaker Guide](CIRCUIT_BREAKER.md)
- [Health Checks & Load Balancing](HEALTH_CHECKS.md)
- [Rate Limiting](RATE_LIMITING.md)

