# Health Checks und Load Balancing Anleitung

**Umfassende Anleitung für Health Checks & Load Balancing in GAL (Gateway Abstraction Layer)**

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Schnellstart](#schnellstart)
3. [Konfigurationsoptionen](#konfigurationsoptionen)
4. [Provider-Implementierung](#provider-implementierung)
5. [Load Balancing Algorithmen](#load-balancing-algorithmen)
6. [Häufige Anwendungsfälle](#häufige-anwendungsfälle)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Übersicht

Health Checks und Load Balancing sind essenzielle Features für hochverfügbare, skalierbare API-Gateways. GAL bietet eine einheitliche Konfiguration für alle unterstützten Gateway-Provider.

### Was sind Health Checks?

Health Checks überwachen kontinuierlich die Verfügbarkeit und Gesundheit von Backend-Services. Es gibt zwei Arten:

**Active Health Checks (Aktive Überwachung)**:
- Gateway sendet periodisch Test-Requests an Backend
- Unabhängig vom echten Traffic
- Kann defekte Services automatisch wieder aktivieren
- Zusätzlicher Traffic zu den Backends

**Passive Health Checks (Passive Überwachung)**:
- Basiert auf echtem Request-Traffic
- Analysiert Antwort-Status-Codes
- Keine zusätzliche Last
- Kann Services nur deaktivieren (nicht reaktivieren)

### Was ist Load Balancing?

Load Balancing verteilt eingehende Requests auf mehrere Backend-Server, um:
- ✅ **Verfügbarkeit** zu erhöhen (Failover bei Ausfällen)
- ✅ **Performance** zu verbessern (Lastverteilung)
- ✅ **Skalierbarkeit** zu ermöglichen (horizontales Scaling)
- ✅ **Wartung** zu erleichtern (Rolling Updates)

### Provider-Unterstützung

| Feature | Kong | APISIX | Traefik | Envoy | Implementierung |
|---------|------|--------|---------|-------|-----------------|
| **Active Health Checks** | ✅ | ✅ | ✅ | ✅ | 100% |
| **Passive Health Checks** | ✅ | ✅ | ⚠️ | ✅ | 75% |
| **Multiple Targets** | ✅ | ✅ | ✅ | ✅ | 100% |
| **Weighted Load Balancing** | ✅ | ✅ | ✅ | ✅ | 100% |
| **Round Robin** | ✅ | ✅ | ✅ | ✅ | 100% |
| **Least Connections** | ✅ | ✅ | ✅ | ✅ | 100% |
| **IP Hash** | ✅ | ✅ | ⚠️ | ✅ | 75% |
| **Sticky Sessions** | ✅ | ⚠️ | ✅ | ⚠️ | 50% |

**Coverage**: 100% für Health Checks, 100% für Load Balancing

---

## Schnellstart

### Einfache Active Health Checks

Basis-Konfiguration für periodisches Probing:

```yaml
version: "1.0"
provider: apisix

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.internal
      port: 8080
      health_check:
        active:
          enabled: true
          http_path: /health           # Welcher Pfad soll geprüft werden?
          interval: "10s"               # Alle 10 Sekunden prüfen
          timeout: "5s"                 # Timeout pro Check
          healthy_threshold: 2          # 2 erfolgreiche Checks → healthy
          unhealthy_threshold: 3        # 3 fehlgeschlagene Checks → unhealthy
          healthy_status_codes:         # Welche Status Codes sind OK?
            - 200
            - 201
            - 204
    routes:
      - path_prefix: /api
        methods: [GET, POST]
```

### Load Balancing mit mehreren Servern

Konfiguration für Round-Robin Load Balancing über 3 Server:

```yaml
version: "1.0"
provider: kong

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
          weight: 1
        - host: api-2.internal
          port: 8080
          weight: 1
        - host: api-3.internal
          port: 8080
          weight: 1
      load_balancer:
        algorithm: round_robin
    routes:
      - path_prefix: /api
        methods: [GET, POST]
```

### Kombiniert: Health Checks + Load Balancing

Production-Ready Konfiguration mit Active & Passive Health Checks und Weighted Load Balancing:

```yaml
version: "1.0"
provider: envoy

services:
  - name: payment_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: payment-1.internal
          port: 8080
          weight: 2    # Doppelt so viel Traffic wie payment-2
        - host: payment-2.internal
          port: 8080
          weight: 1
      health_check:
        active:
          enabled: true
          http_path: /actuator/health
          interval: "15s"
          timeout: "3s"
          healthy_threshold: 2
          unhealthy_threshold: 3
          healthy_status_codes: [200, 204]
        passive:
          enabled: true
          max_failures: 5
          unhealthy_status_codes: [500, 502, 503, 504]
      load_balancer:
        algorithm: weighted
    routes:
      - path_prefix: /api/payments
        methods: [GET, POST]
```

---

## Konfigurationsoptionen

### UpstreamTarget (Einzelner Server)

Definition eines einzelnen Backend-Servers in einem Load-Balancing-Pool:

```yaml
targets:
  - host: api-1.internal     # Hostname oder IP
    port: 8080               # Port
    weight: 2                # Gewichtung (Standard: 1)
```

**Attribute**:
- `host` (string, erforderlich): Hostname oder IP-Adresse
- `port` (int, erforderlich): Port-Nummer
- `weight` (int, optional): Gewichtung für Load Balancing (Standard: 1)

### ActiveHealthCheck (Aktive Überwachung)

Konfiguration für periodisches Probing von Backend-Services:

```yaml
health_check:
  active:
    enabled: true                 # Health Checks aktivieren
    http_path: /health            # Welcher HTTP-Pfad wird geprüft?
    interval: "10s"               # Prüfintervall
    timeout: "5s"                 # Timeout pro einzelnen Check
    healthy_threshold: 2          # Aufeinanderfolgende Erfolge für "healthy"
    unhealthy_threshold: 3        # Aufeinanderfolgende Fehler für "unhealthy"
    healthy_status_codes:         # HTTP Status Codes die als "healthy" gelten
      - 200
      - 201
      - 204
```

**Attribute**:
- `enabled` (bool): Aktive Health Checks aktivieren (Standard: true)
- `http_path` (string): HTTP-Pfad für Probing (Standard: "/health")
- `interval` (string): Prüfintervall (Standard: "10s")
- `timeout` (string): Timeout pro Check (Standard: "5s")
- `healthy_threshold` (int): Erfolge bis "healthy" (Standard: 2)
- `unhealthy_threshold` (int): Fehler bis "unhealthy" (Standard: 3)
- `healthy_status_codes` (list[int]): OK Status Codes (Standard: [200, 201, 204])

**Probing-Ablauf**:
```
Backend healthy:     ──────── (Normal Traffic) ────────
Backend wird slow:   ──────── 1 Fehler ──────── 2 Fehler
Backend marked unhealthy: ──── 3 Fehler (UNHEALTHY!) ────
Backend erholt sich: ────── 1 OK ────── 2 OK (HEALTHY!) ────
```

### PassiveHealthCheck (Passive Überwachung)

Konfiguration für Traffic-basierte Fehlerkennung:

```yaml
health_check:
  passive:
    enabled: true                 # Passive Health Checks aktivieren
    max_failures: 5               # Max. aufeinanderfolgende Fehler
    unhealthy_status_codes:       # Welche Status Codes = Fehler?
      - 500
      - 502
      - 503
      - 504
```

**Attribute**:
- `enabled` (bool): Passive Health Checks aktivieren (Standard: true)
- `max_failures` (int): Max. Fehler bis "unhealthy" (Standard: 5)
- `unhealthy_status_codes` (list[int]): Fehler Status Codes (Standard: [500, 502, 503, 504])

**Wichtig**: Passive Health Checks können Services nur deaktivieren, nicht reaktivieren!

**Empfehlung**: Kombiniere mit Active Health Checks für automatische Reaktivierung:

```yaml
health_check:
  active:
    enabled: true
    interval: "10s"
  passive:
    enabled: true
    max_failures: 3
```

### LoadBalancerConfig (Load Balancing Strategie)

Konfiguration des Load Balancing Algorithmus und Verhaltens:

```yaml
load_balancer:
  algorithm: round_robin        # LB-Algorithmus
  sticky_sessions: false        # Sticky Sessions aktivieren?
  cookie_name: galSession       # Cookie-Name für Sticky Sessions
```

**Attribute**:
- `algorithm` (string): Load Balancing Algorithmus (Standard: "round_robin")
  - `"round_robin"`: Gleichmäßige Verteilung (1→2→3→1→2→3)
  - `"least_conn"`: Server mit wenigsten Verbindungen
  - `"ip_hash"`: Basierend auf Client IP (Konsistenz)
  - `"weighted"`: Gewichtete Verteilung (nutzt `weight` von Targets)
- `sticky_sessions` (bool): Sticky Sessions aktivieren (Standard: false)
- `cookie_name` (string): Session Cookie Name (Standard: "galSession")

---

## Provider-Implementierung

### APISIX

APISIX nutzt native `checks` Konfiguration im Upstream-Objekt.

**Active Health Checks**:
```json
{
  "checks": {
    "active": {
      "type": "http",
      "http_path": "/health",
      "timeout": 5,
      "healthy": {
        "interval": 10,
        "successes": 2,
        "http_statuses": [200, 201, 204]
      },
      "unhealthy": {
        "interval": 10,
        "http_failures": 3
      }
    }
  }
}
```

**Passive Health Checks**:
```json
{
  "checks": {
    "passive": {
      "type": "http",
      "healthy": {
        "successes": 1,
        "http_statuses": [200, 201, 202, 204, 301, 302, 303, 304, 307, 308]
      },
      "unhealthy": {
        "http_failures": 5,
        "http_statuses": [500, 502, 503, 504]
      }
    }
  }
}
```

**Load Balancing**:
```json
{
  "type": "roundrobin",  // oder: least_conn, chash
  "nodes": {
    "api-1.internal:8080": 2,  // weight
    "api-2.internal:8080": 1
  },
  "hash_on": "vars",      // Für chash (IP hash)
  "key": "remote_addr"
}
```

### Kong

Kong nutzt separate `upstreams` Entity mit `healthchecks` und `targets`.

**Active Health Checks**:
```yaml
upstreams:
- name: api_service_upstream
  algorithm: round-robin
  healthchecks:
    active:
      type: http
      http_path: /health
      timeout: 5
      concurrency: 10
      healthy:
        interval: 10
        successes: 2
        http_statuses: [200, 201, 204]
      unhealthy:
        interval: 10
        http_failures: 3
        http_statuses: [429, 500, 503]
```

**Passive Health Checks**:
```yaml
    passive:
      type: http
      healthy:
        successes: 1
        http_statuses: [200, 201, 202, 204, 301, 302, 303, 304, 307, 308]
      unhealthy:
        http_failures: 5
        http_statuses: [500, 502, 503, 504]
        tcp_failures: 0
        timeouts: 0
```

**Targets mit Gewichtung**:
```yaml
  targets:
  - target: api-1.internal:8080
    weight: 200  # Kong nutzt 0-1000 Skala
  - target: api-2.internal:8080
    weight: 100
```

**Load Balancing Algorithmen**:
- `round-robin`: Gleichmäßige Verteilung
- `least-connections`: Server mit wenigsten Verbindungen
- `consistent-hashing`: IP-Hash mit `hash_on: consumer`, `hash_fallback: ip`

### Traefik

Traefik nutzt `loadBalancer` Konfiguration auf Service-Level.

**Multiple Servers**:
```yaml
http:
  services:
    api_service_service:
      loadBalancer:
        servers:
        - url: 'http://api-1.internal:8080'
          weight: 2
        - url: 'http://api-2.internal:8080'
          weight: 1
```

**Health Checks**:
```yaml
        healthCheck:
          path: /health
          interval: 10s
          timeout: 5s
```

**Sticky Sessions**:
```yaml
        sticky:
          cookie:
            name: mySessionCookie
            httpOnly: true
```

**Limitierung**: Traefik hat keine nativen Passive Health Checks. Nutze Kubernetes Readiness Probes oder externe Monitoring-Tools.

### Envoy

Envoy nutzt `health_checks` und `outlier_detection` auf Cluster-Level.

**Active Health Checks**:
```yaml
clusters:
- name: api_service_cluster
  health_checks:
  - timeout: 5s
    interval: 10s
    unhealthy_threshold: 3
    healthy_threshold: 2
    http_health_check:
      path: /health
      expected_statuses:
      - start: 200
        end: 201
      - start: 204
        end: 205
```

**Passive Health Checks (Outlier Detection)**:
```yaml
  outlier_detection:
    consecutive_5xx: 5
    interval: 10s
    base_ejection_time: 30s
    max_ejection_percent: 50
    enforcing_consecutive_5xx: 100
    success_rate_minimum_hosts: 5
    success_rate_request_volume: 10
    enforcing_success_rate: 100
```

**Load Balancing Policies**:
```yaml
  lb_policy: ROUND_ROBIN  # oder: LEAST_REQUEST, RING_HASH, RANDOM
  ring_hash_lb_config:    # Für RING_HASH (IP hash)
    minimum_ring_size: 1024
```

**Weighted Load Balancing**:
```yaml
  load_assignment:
    endpoints:
    - lb_endpoints:
      - endpoint:
          address:
            socket_address:
              address: api-1.internal
              port_value: 8080
        load_balancing_weight:
          value: 2
```

---

## Load Balancing Algorithmen

### Round Robin

**Beschreibung**: Gleichmäßige, zirkuläre Verteilung der Requests.

**Verhalten**:
```
Request 1 → Server 1
Request 2 → Server 2
Request 3 → Server 3
Request 4 → Server 1 (zyklisch)
Request 5 → Server 2
...
```

**Konfiguration**:
```yaml
load_balancer:
  algorithm: round_robin
```

**Vorteile**:
- ✅ Einfach und vorhersagbar
- ✅ Gleichmäßige Lastverteilung (bei gleich starken Servern)
- ✅ Geringe Overhead

**Nachteile**:
- ❌ Ignoriert aktuelle Server-Last
- ❌ Ignoriert unterschiedliche Server-Kapazitäten

**Use Case**: Homogene Backend-Server mit ähnlicher Kapazität

### Least Connections

**Beschreibung**: Sendet Requests an Server mit den wenigsten aktiven Verbindungen.

**Verhalten**:
```
Server 1: 10 aktive Verbindungen
Server 2: 5 aktive Verbindungen  ← Nächster Request geht hier hin
Server 3: 8 aktive Verbindungen
```

**Konfiguration**:
```yaml
load_balancer:
  algorithm: least_conn
```

**Vorteile**:
- ✅ Berücksichtigt aktuelle Last
- ✅ Gut für long-running Requests
- ✅ Dynamische Anpassung

**Nachteile**:
- ❌ Höherer Overhead (Verbindungen tracken)
- ❌ Funktioniert nicht bei sehr kurzen Requests (REST APIs)

**Use Case**: WebSocket, Streaming, lange HTTP-Verbindungen

### IP Hash

**Beschreibung**: Wählt Server basierend auf Client-IP (Konsistent Hashing).

**Verhalten**:
```
Client 192.168.1.1 → Server 1 (immer!)
Client 192.168.1.2 → Server 3 (immer!)
Client 192.168.1.3 → Server 2 (immer!)
```

**Konfiguration**:
```yaml
load_balancer:
  algorithm: ip_hash
```

**Vorteile**:
- ✅ Session Persistence ohne Cookies
- ✅ Vorhersagbares Routing
- ✅ Gut für Caching (Cache-Locality)

**Nachteile**:
- ❌ Ungleichmäßige Verteilung möglich
- ❌ Problem bei Server-Ausfall (Session-Verlust)

**Use Case**: Stateful Applications, Session Persistence, Caching

### Weighted

**Beschreibung**: Verteilung basierend auf Server-Gewichtung.

**Verhalten**:
```yaml
targets:
  - host: server-1   # weight: 3 → 60% Traffic
    weight: 3
  - host: server-2   # weight: 2 → 40% Traffic
    weight: 2
```

**Konfiguration**:
```yaml
load_balancer:
  algorithm: weighted
```

**Vorteile**:
- ✅ Berücksichtigt unterschiedliche Server-Kapazitäten
- ✅ Flexible Traffic-Steuerung
- ✅ Canary Deployments möglich

**Nachteile**:
- ❌ Manuelle Konfiguration nötig
- ❌ Keine automatische Anpassung

**Use Case**: Heterogene Server (unterschiedliche Hardware), Canary Deployments

---

## Häufige Anwendungsfälle

### Use Case 1: Hochverfügbare REST API

**Anforderung**: REST API muss 24/7 verfügbar sein, automatisches Failover bei Ausfällen.

**Lösung**: Round-Robin mit Active Health Checks

```yaml
services:
  - name: rest_api
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
        - host: api-2.internal
          port: 8080
        - host: api-3.internal
          port: 8080
      health_check:
        active:
          enabled: true
          http_path: /health
          interval: "5s"
          healthy_threshold: 2
          unhealthy_threshold: 2
      load_balancer:
        algorithm: round_robin
```

**Warum funktioniert das?**
- Active Health Checks entdecken defekte Server in 10-15 Sekunden (2 * 5s)
- Round-Robin verteilt Last gleichmäßig
- Bei Server-Ausfall: Automatisches Routing zu verbleibenden Servern

### Use Case 2: WebSocket-Service mit Session Persistence

**Anforderung**: WebSocket-Verbindungen müssen zum gleichen Server gehen (Stateful).

**Lösung**: IP Hash oder Sticky Sessions

```yaml
services:
  - name: websocket_service
    upstream:
      targets:
        - host: ws-1.internal
          port: 8080
        - host: ws-2.internal
          port: 8080
      load_balancer:
        algorithm: ip_hash  # Client-IP basiertes Routing
```

**Alternative mit Sticky Sessions (Traefik)**:
```yaml
      load_balancer:
        algorithm: round_robin
        sticky_sessions: true
        cookie_name: wsSession
```

### Use Case 3: Canary Deployment

**Anforderung**: Neues Release an 10% der User ausrollen, 90% auf alter Version.

**Lösung**: Weighted Load Balancing

```yaml
services:
  - name: api_service
    upstream:
      targets:
        - host: api-v1.internal  # Alte Version (90%)
          port: 8080
          weight: 9
        - host: api-v2.internal  # Neue Version (10%)
          port: 8080
          weight: 1
      load_balancer:
        algorithm: weighted
```

**Phased Rollout**:
```
Phase 1: weight 9:1   (90%:10%)
Phase 2: weight 7:3   (70%:30%)
Phase 3: weight 5:5   (50%:50%)
Phase 4: weight 0:10  (0%:100%)
```

### Use Case 4: Heterogene Backend-Server

**Anforderung**: 2x große Server (8 CPU), 1x kleiner Server (2 CPU).

**Lösung**: Weighted Load Balancing nach Kapazität

```yaml
services:
  - name: api_service
    upstream:
      targets:
        - host: large-1.internal
          port: 8080
          weight: 4    # 4x Kapazität
        - host: large-2.internal
          port: 8080
          weight: 4
        - host: small-1.internal
          port: 8080
          weight: 1    # 1x Kapazität
      load_balancer:
        algorithm: weighted
```

**Traffic-Verteilung**: 44% / 44% / 12%

### Use Case 5: Graceful Degradation

**Anforderung**: Bei Teil-Ausfall weiter funktionieren mit reduzierter Kapazität.

**Lösung**: Combined Active + Passive Health Checks

```yaml
services:
  - name: payment_service
    upstream:
      targets:
        - host: payment-1.internal
          port: 8080
        - host: payment-2.internal
          port: 8080
        - host: payment-3.internal
          port: 8080
      health_check:
        active:
          enabled: true
          http_path: /actuator/health
          interval: "10s"
          timeout: "3s"
          healthy_threshold: 2
          unhealthy_threshold: 3
        passive:
          enabled: true
          max_failures: 5
          unhealthy_status_codes: [500, 502, 503, 504]
      load_balancer:
        algorithm: round_robin
```

**Verhalten bei Ausfällen**:
```
3 Server healthy:   100% Kapazität (33% / 33% / 33%)
1 Server down:      66% Kapazität (50% / 50%)
2 Server down:      33% Kapazität (100% auf letztem Server)
```

---

## Best Practices

### 1. Kombiniere Active + Passive Health Checks

**Problem**: Passive Health Checks können Services nicht reaktivieren.

**Lösung**: Nutze beide zusammen:
```yaml
health_check:
  active:           # Für automatische Reaktivierung
    interval: "15s"
  passive:          # Für schnelle Fehlerkennung
    max_failures: 3
```

**Vorteil**: Schnelle Fehlerkennung (Passive) + Automatische Erholung (Active)

### 2. Tune Health Check Intervalle

**Zu kurze Intervalle** (z.B. 1s):
- ❌ Hohe Last auf Backend
- ❌ False Positives bei kurzen Spikes
- ✅ Sehr schnelle Fehlerkennung

**Zu lange Intervalle** (z.B. 60s):
- ✅ Geringe Last
- ❌ Langsame Fehlerkennung
- ❌ Lange Ausfallzeiten

**Empfehlung**: 10-30 Sekunden für Production

```yaml
active:
  interval: "15s"       # Moderate Frequenz
  timeout: "5s"         # Timeout < Interval
  healthy_threshold: 2  # 30s bis recovery (2 * 15s)
  unhealthy_threshold: 2  # 30s bis marking unhealthy
```

### 3. Wähle den richtigen Load Balancing Algorithmus

| Anforderung | Empfohlener Algorithmus |
|-------------|-------------------------|
| Homogene REST APIs | `round_robin` |
| WebSockets / Stateful | `ip_hash` oder Sticky Sessions |
| Heterogene Server | `weighted` |
| Lange Verbindungen | `least_conn` |
| Canary Deployments | `weighted` |

### 4. Implementiere Graceful Shutdown

**Problem**: Bei Deployment werden aktive Requests abgebrochen.

**Lösung**: Deregistriere Server vor Shutdown:
1. Health Check Endpoint gibt 503 zurück
2. Gateway markiert Server als unhealthy
3. Keine neuen Requests mehr
4. Warte bis aktive Requests fertig sind
5. Shutdown

**Health Endpoint Beispiel** (Spring Boot):
```java
@GetMapping("/health")
public ResponseEntity<String> health() {
    if (shutdownRequested) {
        return ResponseEntity.status(503).body("Shutting down");
    }
    return ResponseEntity.ok("Healthy");
}
```

### 5. Monitor Health Check Failures

**Wichtig**: Logge und alertiere auf Health Check Failures!

**Metriken zum Überwachen**:
- Health Check Success Rate
- Anzahl unhealthy Backends
- Time to Recovery
- Failover Events

**Beispiel Alert**:
```
ALERT: api_service hat nur noch 1 von 3 Backends healthy!
Action: Untersuche api-1 und api-2 Logs
```

### 6. Test Health Check Endpoints

**Bad Health Check Endpoint**:
```python
@app.route('/health')
def health():
    return "OK", 200  # Immer OK, auch wenn DB down!
```

**Good Health Check Endpoint**:
```python
@app.route('/health')
def health():
    try:
        # Prüfe kritische Dependencies
        db.execute("SELECT 1")
        redis.ping()
        return "OK", 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return "Unhealthy", 503
```

### 7. Plan für Zero-Downtime Deployments

**Strategie**: Rolling Update mit Health Checks

```
1. Deploy neue Version auf server-1
2. Health Check wird healthy
3. Gateway sendet Traffic zu server-1
4. Deploy auf server-2
5. Repeat für alle Server
```

**Wichtig**: Konfiguriere `healthy_threshold: 2` damit Server nicht zu früh Traffic bekommt!

---

## Troubleshooting

### Problem: Backend wird nicht als healthy markiert

**Symptom**: Health Check schlägt dauerhaft fehl, obwohl Service läuft.

**Mögliche Ursachen**:
1. Health Check Endpoint antwortet nicht mit 200
2. Timeout zu kurz
3. Health Check Pfad falsch konfiguriert
4. Firewall blockiert Health Check Traffic

**Debug-Schritte**:
```bash
# 1. Manuell Health Endpoint testen
curl -v http://api-1.internal:8080/health

# 2. Prüfe Gateway Logs
# APISIX:
curl http://localhost:9180/v1/healthcheck

# Kong:
curl http://localhost:8001/upstreams/api_service_upstream/health

# 3. Prüfe Health Check Config
# Ist http_path korrekt?
# Ist timeout > als Response Time?
# Sind healthy_status_codes korrekt?
```

**Lösung**:
```yaml
health_check:
  active:
    http_path: /actuator/health  # ← Prüfe Pfad!
    timeout: "10s"                # ← Erhöhe Timeout
    healthy_status_codes:         # ← Prüfe erlaubte Codes
      - 200
      - 204
```

### Problem: Traffic wird nicht gleichmäßig verteilt

**Symptom**: Ein Server bekommt deutlich mehr Traffic als andere.

**Mögliche Ursachen**:
1. Falsche Gewichtung
2. Falsch konfigurierter Algorithmus
3. IP Hash mit wenigen Clients
4. Sticky Sessions aktiv

**Debug-Schritte**:
```bash
# 1. Prüfe Backend-Logs
tail -f /var/log/api-1.log | grep -c "Request"
tail -f /var/log/api-2.log | grep -c "Request"

# 2. Prüfe Load Balancer Config
# Sind weights korrekt?
# Ist algorithm korrekt?

# 3. Test mit curl
for i in {1..100}; do
  curl -s http://gateway/api | grep "Server:"
done | sort | uniq -c
```

**Lösung**:
```yaml
# Korrigiere Weights
targets:
  - host: api-1
    weight: 1  # ← Gleiche Gewichtung
  - host: api-2
    weight: 1

# Oder nutze round_robin statt weighted
load_balancer:
  algorithm: round_robin
```

### Problem: Server wird nach Recovery nicht reaktiviert

**Symptom**: Server ist wieder online, aber bekommt keinen Traffic.

**Ursache**: Nur Passive Health Checks konfiguriert (können nicht reaktivieren!).

**Lösung**: Füge Active Health Checks hinzu:
```yaml
health_check:
  active:
    enabled: true
    interval: "10s"
  passive:
    enabled: true
    max_failures: 3
```

### Problem: Health Checks belasten Backend zu sehr

**Symptom**: Health Checks verursachen signifikante Last.

**Ursachen**:
- Interval zu kurz (z.B. 1s)
- Health Endpoint ist zu teuer (DB-Queries, etc.)

**Lösung 1**: Erhöhe Interval
```yaml
health_check:
  active:
    interval: "30s"  # Statt 5s
```

**Lösung 2**: Optimiere Health Endpoint
```python
# Bad: Teurer Health Check
@app.route('/health')
def health():
    users = db.query("SELECT * FROM users")  # ← Teuer!
    return "OK", 200

# Good: Leichtgewichtiger Health Check
@app.route('/health')
def health():
    db.execute("SELECT 1")  # ← Nur Connection-Test
    return "OK", 200
```

### Problem: Requests schlagen fehl während Rolling Update

**Symptom**: 503 Errors während Deployment.

**Ursache**: Server wird zu früh Traffic bekommen (bevor vollständig gestartet).

**Lösung**: Erhöhe `healthy_threshold`:
```yaml
health_check:
  active:
    healthy_threshold: 3  # Statt 1
    interval: "5s"
```

**Bedeutung**: Server muss 3 aufeinanderfolgende Health Checks bestehen (15s) bevor Traffic kommt.

---

## Anhang

### Beispiel: Production-Ready Konfiguration

Vollständige Konfiguration für Production-Einsatz mit allen Features:

```yaml
version: "1.0"
provider: apisix

global_config:
  host: "0.0.0.0"
  port: 9080
  admin_port: 9180

services:
  - name: user_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: user-1.prod.internal
          port: 8080
          weight: 2
        - host: user-2.prod.internal
          port: 8080
          weight: 2
        - host: user-3.prod.internal
          port: 8080
          weight: 1
      health_check:
        active:
          enabled: true
          http_path: /actuator/health
          interval: "15s"
          timeout: "5s"
          healthy_threshold: 3
          unhealthy_threshold: 2
          healthy_status_codes: [200, 204]
        passive:
          enabled: true
          max_failures: 5
          unhealthy_status_codes: [500, 502, 503, 504]
      load_balancer:
        algorithm: weighted
    routes:
      - path_prefix: /api/users
        methods: [GET, POST, PUT, DELETE]
```

### Weiterführende Links

- **APISIX Health Check Docs**: https://apisix.apache.org/docs/apisix/tutorials/health-check/
- **Kong Health Checks Docs**: https://docs.konghq.com/gateway/latest/how-kong-works/health-checks/
- **Traefik Health Check Docs**: https://doc.traefik.io/traefik/routing/services/
- **Envoy Health Checking Docs**: https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/health_checking
- **Envoy Outlier Detection Docs**: https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier

---

**Document Version:** 1.0
**Last Updated:** 2025-10-18
**Author:** GAL Development Team
