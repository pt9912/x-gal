# Circuit Breaker Anleitung

**Umfassende Anleitung für Circuit Breaker Pattern in GAL (Gateway Abstraction Layer)**

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Schnellstart](#schnellstart)
3. [Konfigurationsoptionen](#konfigurationsoptionen)
4. [Provider-Implementierung](#provider-implementierung)
5. [Häufige Anwendungsfälle](#häufige-anwendungsfälle)
6. [Best Practices](#best-practices)
7. [Circuit Breaker Testen](#circuit-breaker-testen)
8. [Troubleshooting](#troubleshooting)

---

## Übersicht

Das Circuit Breaker Pattern ist ein Resilience-Mechanismus, der verhindert, dass fehlerhafte oder langsame Upstream-Services das gesamte System zum Absturz bringen. GAL bietet eine einheitliche Circuit Breaker-Konfiguration für alle unterstützten Gateway-Provider.

### Was ist ein Circuit Breaker?

Ein Circuit Breaker funktioniert wie eine elektrische Sicherung: Wenn zu viele Fehler auftreten, "öffnet" sich der Circuit Breaker und blockiert weitere Requests temporär, um dem fehlerhaften Service Zeit zur Erholung zu geben.

**Circuit Breaker Zustände**:

```
CLOSED (Normal) → OPEN (Broken) → HALF_OPEN (Testing) → CLOSED
```

1. **CLOSED** (Geschlossen): Normal operation, alle Requests werden durchgelassen
2. **OPEN** (Offen): Circuit ist "gebrochen", Requests werden sofort abgelehnt
3. **HALF_OPEN** (Halb-offen): Testet mit wenigen Requests, ob Service wieder funktioniert

### Warum ist Circuit Breaker wichtig?

- ✅ **Fehler-Isolation**: Verhindert Cascading Failures
- ✅ **Schnelle Fehlerbehandlung**: Sofortige Rückmeldung bei defekten Services
- ✅ **Automatische Erholung**: Testet automatisch, wann Service wieder verfügbar ist
- ✅ **Resource-Schonung**: Verschwendet keine Ressourcen für defekte Services
- ✅ **Bessere User Experience**: Schnelle Fehlerseiten statt Timeouts

### Provider-Unterstützung

| Feature | Kong | APISIX | Traefik | Envoy | Implementierung |
|---------|------|--------|---------|-------|-----------------|
| **Circuit Breaker** | ⚠️ | ✅ | ✅ | ✅ | Kong: Third-party only |
| **Max Failures** | - | ✅ | ✅ | ✅ | Fehler-Schwellwert |
| **Timeout** | - | ✅ | ✅ | ✅ | Erholungszeit |
| **Half-Open Requests** | - | ✅ | - | ✅ | Test-Requests |
| **Status Code Detection** | - | ✅ | ✅ | ✅ | Welche Codes = Fehler |

**Coverage**: 75% (3 von 4 Providern haben native Unterstützung)

- **APISIX**: Native `api-breaker` Plugin ✅
- **Traefik**: Native `CircuitBreaker` Middleware ✅
- **Envoy**: Native `Outlier Detection` ✅
- **Kong**: Nur Third-Party Plugin (kong-circuit-breaker) ⚠️

---

## Schnellstart

### Einfache Circuit Breaker-Konfiguration

Basis-Konfiguration für alle Provider (außer Kong):

```yaml
version: "1.0"
provider: apisix

services:
  - name: payment_service
    type: rest
    protocol: http
    upstream:
      host: payment.internal
      port: 8080
    routes:
      - path_prefix: /api/payments
        methods: [GET, POST]
        circuit_breaker:
          enabled: true
          max_failures: 5           # Nach 5 Fehlern → OPEN
          timeout: "30s"            # 30 Sekunden warten
          half_open_requests: 3     # 3 Test-Requests in HALF_OPEN
```

### Fortgeschrittene Konfiguration

Mit custom Status Codes und Response-Konfiguration:

```yaml
routes:
  - path_prefix: /api/payments
    methods: [GET, POST]
    circuit_breaker:
      enabled: true
      max_failures: 5
      timeout: "30s"
      half_open_requests: 3

      # Welche Status Codes sind "Fehler"?
      unhealthy_status_codes: [500, 502, 503, 504]

      # Welche Status Codes sind "gesund"?
      healthy_status_codes: [200, 201, 202, 204]

      # Response wenn Circuit OPEN ist
      failure_response_code: 503
      failure_response_message: "Service temporarily unavailable"
```

### Circuit Breaker mit Rate Limiting kombinieren

Schütze deinen Service vor Überlastung und Ausfällen:

```yaml
routes:
  - path_prefix: /api/critical
    methods: [GET, POST]

    # Rate Limiting: Maximal 100 Requests/Sekunde
    rate_limit:
      enabled: true
      requests_per_second: 100
      burst: 150

    # Circuit Breaker: Bei Problemen sofort abschalten
    circuit_breaker:
      enabled: true
      max_failures: 10
      timeout: "60s"
      unhealthy_status_codes: [500, 502, 503, 504, 429]
```

---

## Konfigurationsoptionen

### CircuitBreakerConfig Felder

```yaml
circuit_breaker:
  # Aktivierung
  enabled: true

  # Maximale aufeinanderfolgende Fehler vor OPEN
  max_failures: 5

  # Wartezeit bis HALF_OPEN-Test (Format: "30s", "1m", "2h")
  timeout: "30s"

  # Anzahl Test-Requests in HALF_OPEN-Phase
  half_open_requests: 3

  # HTTP Status Codes die als "Fehler" zählen
  unhealthy_status_codes:
    - 500  # Internal Server Error
    - 502  # Bad Gateway
    - 503  # Service Unavailable
    - 504  # Gateway Timeout

  # HTTP Status Codes die als "gesund" zählen
  healthy_status_codes:
    - 200  # OK
    - 201  # Created
    - 202  # Accepted
    - 204  # No Content

  # Response Code wenn Circuit OPEN ist
  failure_response_code: 503

  # Response Message wenn Circuit OPEN ist
  failure_response_message: "Service temporarily unavailable"
```

### Standard-Werte

Wenn Felder weggelassen werden, gelten folgende Defaults:

```yaml
circuit_breaker:
  enabled: true
  max_failures: 5
  timeout: "30s"
  half_open_requests: 3
  unhealthy_status_codes: [500, 502, 503, 504]
  healthy_status_codes: [200, 201, 202, 204]
  failure_response_code: 503
  failure_response_message: "Service temporarily unavailable"
```

### Parameter-Erklärung

#### max_failures (int)
Anzahl aufeinanderfolgender Fehler, bevor Circuit auf OPEN schaltet.

```yaml
max_failures: 5  # Nach 5 Fehlern → OPEN
```

**Empfehlung**:
- **Kritische Services**: 3-5 Fehler
- **Normale Services**: 5-10 Fehler
- **Robuste Services**: 10-20 Fehler

#### timeout (string)
Wartezeit in OPEN-Phase, bevor HALF_OPEN-Test startet.

```yaml
timeout: "30s"   # 30 Sekunden
timeout: "1m"    # 1 Minute
timeout: "2h"    # 2 Stunden
```

**Empfehlung**:
- **Schnelle Erholung**: 10-30 Sekunden
- **Normale Erholung**: 30-60 Sekunden
- **Lange Erholung**: 1-5 Minuten

#### half_open_requests (int)
Anzahl Test-Requests in HALF_OPEN-Phase.

```yaml
half_open_requests: 3  # 3 Test-Requests
```

**Empfehlung**:
- **Vorsichtig**: 1-3 Requests
- **Normal**: 3-5 Requests
- **Aggressiv**: 5-10 Requests

#### unhealthy_status_codes (list)
HTTP Status Codes die als Fehler gewertet werden.

```yaml
unhealthy_status_codes:
  - 500  # Internal Server Error
  - 502  # Bad Gateway
  - 503  # Service Unavailable
  - 504  # Gateway Timeout
  - 429  # Too Many Requests (optional)
```

#### healthy_status_codes (list)
HTTP Status Codes die als erfolgreich gewertet werden.

```yaml
healthy_status_codes:
  - 200  # OK
  - 201  # Created
  - 202  # Accepted
  - 204  # No Content
  - 304  # Not Modified (optional)
```

---

## Provider-Implementierung

### APISIX (api-breaker plugin)

APISIX verwendet das native `api-breaker` Plugin mit zustandsbasierter Erkennung:

```yaml
# GAL Konfiguration
circuit_breaker:
  enabled: true
  max_failures: 5
  timeout: "30s"
  half_open_requests: 3
  unhealthy_status_codes: [500, 502, 503, 504]
  healthy_status_codes: [200, 201, 202, 204]

# Wird zu APISIX-Config:
{
  "plugins": {
    "api-breaker": {
      "break_response_code": 503,
      "max_breaker_sec": 30,
      "unhealthy": {
        "http_statuses": [500, 502, 503, 504],
        "failures": 5
      },
      "healthy": {
        "http_statuses": [200, 201, 202, 204],
        "successes": 3
      }
    }
  }
}
```

**APISIX Besonderheiten**:
- ✅ Vollständige Circuit Breaker-Unterstützung
- ✅ State-basierte Erkennung (CLOSED/OPEN/HALF_OPEN)
- ✅ Flexible Status Code-Konfiguration
- ✅ Timeout in Sekunden (`max_breaker_sec`)

### Traefik (CircuitBreaker middleware)

Traefik verwendet Expression-basierte Circuit Breaker:

```yaml
# GAL Konfiguration
circuit_breaker:
  enabled: true
  max_failures: 5
  unhealthy_status_codes: [500, 504]

# Wird zu Traefik-Config:
middlewares:
  payment_router_0_circuitbreaker:
    circuitBreaker:
      expression: 'ResponseCodeRatio(500, 505, 0, 600) > 0.50'
```

**Traefik Expression-Syntax**:

GAL generiert automatisch passende Expressions:

```yaml
# Beispiel 1: Status Code Ratio
max_failures: 5
unhealthy_status_codes: [500, 502, 503, 504]
# → Expression: "ResponseCodeRatio(500, 505, 0, 600) > 0.50"

# Beispiel 2: Network Error Ratio (Fallback)
max_failures: 3
unhealthy_status_codes: []
# → Expression: "NetworkErrorRatio() > 0.30"
```

**Traefik Besonderheiten**:
- ✅ Expression-basierte Konfiguration
- ✅ Flexible Ratio-Berechnung
- ✅ `ResponseCodeRatio(min, max, 0, 600)`
- ⚠️ Timeout nicht direkt konfigurierbar

### Envoy (Outlier Detection)

Envoy verwendet Outlier Detection für Circuit Breaking:

```yaml
# GAL Konfiguration
circuit_breaker:
  enabled: true
  max_failures: 5
  timeout: "30s"
  half_open_requests: 3

# Wird zu Envoy-Config:
clusters:
  - name: payment_cluster
    outlier_detection:
      consecutive_5xx: 5
      interval: 10s
      base_ejection_time: 30s
      max_ejection_percent: 50
      enforcing_consecutive_5xx: 100
      success_rate_minimum_hosts: 3
      success_rate_request_volume: 10
      enforcing_success_rate: 100
```

**Envoy Besonderheiten**:
- ✅ Outlier Detection auf Cluster-Level
- ✅ `consecutive_5xx` für Fehler-Erkennung
- ✅ `base_ejection_time` für Timeout
- ✅ Success Rate Enforcement
- ⚠️ Max 50% der Hosts können ausgeschlossen werden

### Kong (⚠️ Keine native Unterstützung)

Kong hat **keine native** Circuit Breaker-Unterstützung.

**Warnung**:
```yaml
# GAL Konfiguration
circuit_breaker:
  enabled: true

# Kong generiert WARNUNG:
⚠ Circuit breaker configured for route payment_service/api/payments,
  but Kong does not have native circuit breaker support.
  Consider using kong-circuit-breaker plugin or switch to a provider
  with native support.
```

**Alternativen für Kong**:
1. **Third-Party Plugin**: `kong-circuit-breaker` (Dream11)
2. **Provider wechseln**: APISIX, Traefik oder Envoy verwenden
3. **External Service**: Circuit Breaker in Application-Code

---

## Häufige Anwendungsfälle

### 1. Payment Service (Kritisch)

Sofortiger Schutz für kritische Payment-Services:

```yaml
services:
  - name: payment_service
    routes:
      - path_prefix: /api/payments
        methods: [POST]
        circuit_breaker:
          enabled: true
          max_failures: 3           # Sehr sensitiv
          timeout: "60s"            # Längere Erholung
          unhealthy_status_codes: [500, 502, 503, 504]
          failure_response_code: 503
          failure_response_message: "Payment service unavailable"
```

### 2. External API Integration

Schutz vor externen API-Ausfällen:

```yaml
services:
  - name: external_api
    upstream:
      host: api.external.com
      port: 443
    routes:
      - path_prefix: /api/external
        circuit_breaker:
          enabled: true
          max_failures: 5
          timeout: "2m"             # Externe APIs brauchen länger
          unhealthy_status_codes: [429, 500, 502, 503, 504]
```

### 3. Database Service

Schutz vor Database-Überlastung:

```yaml
services:
  - name: database_api
    routes:
      - path_prefix: /api/db
        circuit_breaker:
          enabled: true
          max_failures: 10
          timeout: "30s"
          unhealthy_status_codes: [500, 503]
          healthy_status_codes: [200, 201]
```

### 4. Microservices Mesh

Circuit Breaker für alle Microservices:

```yaml
services:
  - name: user_service
    routes:
      - path_prefix: /api/users
        circuit_breaker:
          enabled: true
          max_failures: 5
          timeout: "30s"

  - name: order_service
    routes:
      - path_prefix: /api/orders
        circuit_breaker:
          enabled: true
          max_failures: 7
          timeout: "45s"

  - name: inventory_service
    routes:
      - path_prefix: /api/inventory
        circuit_breaker:
          enabled: true
          max_failures: 10
          timeout: "60s"
```

### 5. Circuit Breaker + Rate Limiting + Authentication

Vollständiger Schutz-Stack:

```yaml
routes:
  - path_prefix: /api/protected
    methods: [GET, POST]

    # 1. Rate Limiting (Überlastungsschutz)
    rate_limit:
      enabled: true
      requests_per_second: 100
      burst: 150

    # 2. Authentication (Zugriffsschutz)
    authentication:
      enabled: true
      type: jwt
      jwt:
        issuer: "https://auth.example.com"

    # 3. Circuit Breaker (Fehler-Schutz)
    circuit_breaker:
      enabled: true
      max_failures: 5
      timeout: "30s"
```

### 6. Gradual Rollback bei Deployments

Schnelle Fehler-Erkennung nach Deployments:

```yaml
# Nach neuem Deployment: Sehr sensitive Settings
circuit_breaker:
  enabled: true
  max_failures: 3             # Sehr sensitiv
  timeout: "15s"              # Schneller Test
  half_open_requests: 1       # Vorsichtig testen

# Nach Stabilisierung: Normal Settings
circuit_breaker:
  enabled: true
  max_failures: 10
  timeout: "60s"
  half_open_requests: 5
```

### 7. Multi-Region Failover

Circuit Breaker für Region-Failover:

```yaml
services:
  - name: primary_region
    upstream:
      host: api.us-east-1.example.com
    routes:
      - path_prefix: /api
        circuit_breaker:
          enabled: true
          max_failures: 5
          timeout: "30s"

  - name: fallback_region
    upstream:
      host: api.eu-west-1.example.com
    routes:
      - path_prefix: /api/fallback
        circuit_breaker:
          enabled: true
          max_failures: 5
          timeout: "30s"
```

---

## Best Practices

### 1. ✅ Richtige Schwellwerte wählen

**Zu sensitiv** (schlecht):
```yaml
max_failures: 1  # ❌ Öffnet bei jedem Fehler
timeout: "5s"    # ❌ Zu kurze Erholung
```

**Gut kalibriert**:
```yaml
max_failures: 5-10  # ✅ Toleriert vereinzelte Fehler
timeout: "30s-60s"  # ✅ Angemessene Erholung
```

### 2. ✅ Service-spezifische Konfiguration

Verschiedene Services brauchen verschiedene Settings:

```yaml
# Kritischer Payment Service
- name: payment
  circuit_breaker:
    max_failures: 3
    timeout: "60s"

# Robuster Logging Service
- name: logging
  circuit_breaker:
    max_failures: 20
    timeout: "10s"
```

### 3. ✅ Unhealthy Status Codes richtig wählen

```yaml
# ✅ Gut: Nur echte Fehler
unhealthy_status_codes: [500, 502, 503, 504]

# ⚠️ Optional: Rate Limiting einbeziehen
unhealthy_status_codes: [429, 500, 502, 503, 504]

# ❌ Schlecht: Client-Fehler einbeziehen
unhealthy_status_codes: [400, 404, 500]  # 400/404 sind keine Service-Fehler!
```

### 4. ✅ Monitoring und Alerting

**Wichtige Metriken**:
- Circuit Breaker State Changes (CLOSED → OPEN)
- Anzahl rejected Requests in OPEN-Phase
- Success Rate in HALF_OPEN-Phase
- Durchschnittliche Erholungszeit

```yaml
# Logging aktivieren für Debugging
# Siehe Provider-spezifische Logs
```

### 5. ✅ Graceful Degradation

Liefere sinnvolle Fallback-Responses:

```yaml
circuit_breaker:
  failure_response_code: 503
  failure_response_message: "Service temporarily unavailable. Please try again later."
```

**Application-Level Fallback**:
```javascript
// Client-Code
try {
  const response = await fetch('/api/data');
  if (response.status === 503) {
    // Fallback: Cached Data oder Default-Werte
    return getCachedData();
  }
  return response.json();
} catch (error) {
  return getDefaultData();
}
```

### 6. ✅ Testing in Staging

Teste Circuit Breaker in Staging-Umgebung:

```bash
# Simuliere Fehler
for i in {1..10}; do
  curl -X POST http://staging.api/test/fail
done

# Circuit sollte nach max_failures öffnen
curl http://staging.api/test
# → 503 Service temporarily unavailable

# Warte timeout-Dauer
sleep 30

# Circuit sollte HALF_OPEN testen
curl http://staging.api/test
```

### 7. ✅ Dokumentiere Settings

Dokumentiere, warum du bestimmte Settings gewählt hast:

```yaml
circuit_breaker:
  # Payment Service ist kritisch: Sehr sensitive Settings
  # Bei 3 Fehlern sofort abschalten um Daten-Inkonsistenz zu vermeiden
  max_failures: 3

  # Längeres Timeout: Payment Provider braucht 30-60s zur Erholung
  timeout: "60s"

  # Vorsichtig testen: Nur 1 Request in HALF_OPEN
  half_open_requests: 1
```

---

## Circuit Breaker Testen

### Mit cURL

#### Test 1: Normale Requests

```bash
# Normale Requests sollten durchgehen
for i in {1..5}; do
  curl -X GET http://api.example.com/api/test
  echo "Request $i completed"
done
```

#### Test 2: Fehler provozieren

```bash
# Provoziere Fehler um Circuit zu öffnen
# (Voraussetzung: Backend gibt 500 zurück)
for i in {1..10}; do
  curl -X GET http://api.example.com/api/fail
  echo "Error request $i: $(date)"
done

# Circuit sollte nach max_failures öffnen
curl -v http://api.example.com/api/test
# → HTTP/1.1 503 Service temporarily unavailable
```

#### Test 3: Erholung testen

```bash
# Warte timeout-Dauer
sleep 30

# Circuit sollte jetzt HALF_OPEN sein und Requests testen
curl -v http://api.example.com/api/test
# → Wenn erfolgreich: Circuit geht zu CLOSED
# → Wenn fehlschlägt: Circuit geht zurück zu OPEN
```

### Mit Python Requests

```python
import requests
import time

def test_circuit_breaker():
    """Test Circuit Breaker functionality"""
    api_url = "http://api.example.com/api/test"

    # 1. Provoziere Fehler
    print("Provoking failures...")
    for i in range(10):
        response = requests.get(api_url + "/fail")
        print(f"Request {i+1}: Status {response.status_code}")

    # 2. Circuit sollte jetzt OPEN sein
    print("\nTesting circuit OPEN state...")
    response = requests.get(api_url)
    assert response.status_code == 503, "Circuit should be OPEN"
    print(f"✓ Circuit is OPEN: {response.status_code}")

    # 3. Warte auf timeout
    print("\nWaiting for timeout (30s)...")
    time.sleep(30)

    # 4. Circuit sollte HALF_OPEN sein
    print("\nTesting circuit HALF_OPEN state...")
    response = requests.get(api_url)
    print(f"Half-open test: Status {response.status_code}")

    # 5. Wenn erfolgreich: Circuit sollte CLOSED sein
    if response.status_code == 200:
        print("✓ Circuit recovered to CLOSED")
    else:
        print("✗ Circuit failed half-open test")

if __name__ == "__main__":
    test_circuit_breaker()
```

### Automatisierte Tests

```python
import pytest
import requests
import time

@pytest.fixture
def api_base_url():
    return "http://localhost:8080"

def test_circuit_opens_after_failures(api_base_url):
    """Test that circuit opens after max_failures"""
    # Provoziere 5 Fehler (max_failures = 5)
    for _ in range(5):
        requests.get(f"{api_base_url}/api/fail")

    # Circuit sollte OPEN sein
    response = requests.get(f"{api_base_url}/api/test")
    assert response.status_code == 503

def test_circuit_half_open_after_timeout(api_base_url):
    """Test that circuit goes to HALF_OPEN after timeout"""
    # Öffne Circuit
    for _ in range(5):
        requests.get(f"{api_base_url}/api/fail")

    # Warte timeout (30s)
    time.sleep(30)

    # Circuit sollte HALF_OPEN sein und Requests testen
    response = requests.get(f"{api_base_url}/api/test")
    # Wenn Backend funktioniert: 200, sonst 503
    assert response.status_code in [200, 503]

def test_circuit_closes_after_successful_half_open(api_base_url):
    """Test that circuit closes after successful half_open_requests"""
    # Öffne Circuit
    for _ in range(5):
        requests.get(f"{api_base_url}/api/fail")

    # Warte timeout
    time.sleep(30)

    # half_open_requests (z.B. 3) erfolgreiche Requests
    for _ in range(3):
        response = requests.get(f"{api_base_url}/api/test")
        assert response.status_code == 200

    # Circuit sollte jetzt CLOSED sein
    response = requests.get(f"{api_base_url}/api/test")
    assert response.status_code == 200
```

### Provider-spezifisches Testing

#### APISIX Testing

```bash
# APISIX Admin API abfragen
curl -X GET http://localhost:9180/apisix/admin/routes/1 \
  -H "X-API-KEY: your-admin-key"

# Circuit Breaker Status prüfen
# (APISIX speichert Circuit State in Memory/Redis)
```

#### Envoy Testing

```bash
# Envoy Admin Interface
curl http://localhost:9901/stats | grep outlier_detection

# Outlier Detection Stats:
# cluster.payment_cluster.outlier_detection.ejections_active: 1
# cluster.payment_cluster.outlier_detection.ejections_total: 5
```

#### Traefik Testing

```bash
# Traefik Dashboard
open http://localhost:8080/dashboard/

# Circuit Breaker Metrics in Dashboard sichtbar
# Anzahl offener Circuits
# Anzahl abgelehnter Requests
```

---

## Troubleshooting

### Problem 1: Circuit öffnet zu häufig

**Symptom**: Circuit Breaker öffnet bei vereinzelten Fehlern.

**Ursache**: `max_failures` zu niedrig eingestellt.

**Lösung**:
```yaml
# ❌ Zu sensitiv
max_failures: 1

# ✅ Toleriert vereinzelte Fehler
max_failures: 5-10
```

### Problem 2: Circuit öffnet nie

**Symptom**: Trotz vieler Fehler öffnet Circuit nie.

**Lösung 1**: Prüfe `unhealthy_status_codes`
```yaml
# ❌ Falsch: Backend gibt 502 zurück, aber nur 500 konfiguriert
unhealthy_status_codes: [500]

# ✅ Richtig: Alle 5xx-Fehler
unhealthy_status_codes: [500, 502, 503, 504]
```

**Lösung 2**: Prüfe Provider-Logs
```bash
# APISIX Logs
docker logs apisix | grep api-breaker

# Envoy Logs
docker logs envoy | grep outlier_detection

# Traefik Logs
docker logs traefik | grep circuitbreaker
```

### Problem 3: Circuit bleibt dauerhaft OPEN

**Symptom**: Circuit erholt sich nie, bleibt permanent OPEN.

**Ursache**: Backend ist dauerhaft kaputt oder `timeout` zu kurz.

**Lösung**:
```yaml
# ❌ Timeout zu kurz
timeout: "5s"  # Backend braucht länger zur Erholung

# ✅ Längerer Timeout
timeout: "60s"

# ✅ Oder Backend fixen!
```

### Problem 4: HALF_OPEN Tests schlagen fehl

**Symptom**: Circuit geht zu HALF_OPEN, aber Tests schlagen immer fehl.

**Lösung 1**: Reduziere `half_open_requests`
```yaml
# ❌ Zu viele Test-Requests
half_open_requests: 10

# ✅ Weniger Test-Requests
half_open_requests: 1-3
```

**Lösung 2**: Erhöhe `timeout`
```yaml
# Gib Backend mehr Zeit zur Erholung
timeout: "2m"  # Statt 30s
```

### Problem 5: Kong Circuit Breaker funktioniert nicht

**Symptom**: Kong ignoriert Circuit Breaker-Konfiguration.

**Ursache**: Kong hat keine native Unterstützung.

**Lösung**:
1. **Option 1**: Wechsle zu APISIX, Traefik oder Envoy
```yaml
# Ändere Provider in gateway.yaml
provider: apisix  # Statt kong
```

2. **Option 2**: Installiere Third-Party Plugin
```bash
# kong-circuit-breaker (Dream11)
luarocks install kong-circuit-breaker
```

3. **Option 3**: Implementiere in Application-Code
```javascript
// Circuit Breaker in Node.js
const CircuitBreaker = require('opossum');
const breaker = new CircuitBreaker(apiCall, {
  timeout: 30000,
  errorThresholdPercentage: 50,
  resetTimeout: 30000
});
```

### Problem 6: Fehler-Metriken stimmen nicht

**Symptom**: Circuit öffnet, obwohl Metriken gut aussehen.

**Lösung**: Prüfe Provider-spezifische Metrics

**APISIX**:
```bash
# APISIX Prometheus Metrics
curl http://localhost:9091/apisix/prometheus/metrics | grep api_breaker
```

**Envoy**:
```bash
# Envoy Stats
curl http://localhost:9901/stats | grep outlier
```

**Traefik**:
```bash
# Traefik Metrics
curl http://localhost:8080/metrics | grep circuit
```

### Problem 7: Circuit Breaker ignoriert healthy_status_codes

**Symptom**: 201, 202 werden als Fehler gewertet.

**Lösung**: Erweitere `healthy_status_codes`
```yaml
# ✅ Alle Success-Codes
healthy_status_codes: [200, 201, 202, 204, 304]
```

---

## Best Practice Checkliste

### Vor Deployment

- [ ] ✅ `max_failures` an Service-Kritikalität anpassen
- [ ] ✅ `timeout` basierend auf Service-Erholungszeit wählen
- [ ] ✅ `unhealthy_status_codes` korrekt konfigurieren (nur 5xx!)
- [ ] ✅ `healthy_status_codes` vollständig definieren
- [ ] ✅ Provider-Support prüfen (Kong hat keine native Unterstützung!)
- [ ] ✅ Circuit Breaker in Staging testen
- [ ] ✅ Monitoring für Circuit States einrichten

### Monitoring & Alerting

- [ ] ✅ Alert bei Circuit State = OPEN
- [ ] ✅ Dashboard für Circuit Breaker Metrics
- [ ] ✅ Log Circuit State Changes
- [ ] ✅ Track Erholungszeit (Zeit in OPEN-Phase)
- [ ] ✅ Monitor HALF_OPEN Success Rate

### Testing

- [ ] ✅ Test: Circuit öffnet nach max_failures
- [ ] ✅ Test: Circuit geht zu HALF_OPEN nach timeout
- [ ] ✅ Test: Circuit schließt nach erfolgreichen Tests
- [ ] ✅ Test: Circuit bleibt OPEN bei fehlgeschlagenen Tests
- [ ] ✅ Load Testing mit Circuit Breaker

---

## Zusammenfassung

Circuit Breaker in GAL ermöglicht:

✅ **Fehler-Isolation**: Verhindert Cascading Failures
✅ **Automatische Erholung**: Selbstheilende Systeme
✅ **Resource-Schonung**: Verschwendet keine Ressourcen
✅ **Provider-Abstraktion**: APISIX, Traefik, Envoy (75% Coverage)

**Wichtige Erkenntnisse**:
- ⚠️ Kong hat keine native Unterstützung (nur Third-Party)
- ✅ APISIX, Traefik, Envoy haben vollständige Unterstützung
- ⚠️ Settings müssen pro Service kalibriert werden
- ✅ Kombiniere mit Rate Limiting für optimalen Schutz

**Nächste Schritte**:
- Siehe [RATE_LIMITING.md](RATE_LIMITING.md) für Traffic-Schutz
- Siehe [examples/circuit-breaker-example.yaml](../../examples/circuit-breaker-example.yaml) für vollständige Beispiele
- Siehe [PROVIDERS.md](PROVIDERS.md) für Provider-Details

**Hilfe benötigt?**
- Probleme melden: https://github.com/pt9912/x-gal/issues
- Dokumentation: https://docs.gal.dev
- Beispiele: [examples/](../../examples/)
