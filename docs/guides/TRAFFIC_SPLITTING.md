# Traffic Splitting Anleitung

**Umfassende Anleitung für A/B Testing, Canary Deployments und Traffic Splitting in GAL (Gateway Abstraction Layer)**

## Inhaltsverzeichnis

1. [Übersicht](#ubersicht)
2. [Schnellstart](#schnellstart)
3. [Konfigurationsoptionen](#konfigurationsoptionen)
4. [Provider-Implementierung](#provider-implementierung)
5. [Häufige Anwendungsfälle](#haufige-anwendungsfalle)
6. [Best Practices](#best-practices)
7. [Traffic Splitting Testen](#traffic-splitting-testen)
8. [Troubleshooting](#troubleshooting)

---

## Übersicht

Traffic Splitting ist ein essentielles Feature für moderne Deployment-Strategien wie Canary Deployments, A/B Testing und Blue/Green Deployments. GAL bietet eine einheitliche Traffic Splitting-Konfiguration für alle unterstützten Gateway-Provider.

### Was ist Traffic Splitting?

Traffic Splitting verteilt eingehende Requests auf verschiedene Backend-Versionen basierend auf **Gewichtungen**, **Headers** oder **Cookies**. Dies ermöglicht kontrollierte Rollouts neuer Features ohne Risiko für alle Nutzer.

**Traffic Splitting Strategien**:

```
Weight-based:  90% → Stable, 10% → Canary
Header-based:  X-Version: beta → Beta Backend
Cookie-based:  canary_user=true → Canary Backend
```

### Warum ist Traffic Splitting wichtig?

- ✅ **Risikofreie Deployments**: Neue Versionen schrittweise ausrollen
- ✅ **A/B Testing**: Feature-Varianten mit echten Nutzern testen
- ✅ **Canary Deployments**: Kleine Nutzergruppen als "Kanarienvögel"
- ✅ **Blue/Green Deployments**: Sofortiges Switching zwischen Versionen
- ✅ **Feature Flags**: Header-basierte Feature-Freischaltung
- ✅ **User Segmentation**: Verschiedene Nutzergruppen testen unterschiedliche Features

### Provider-Unterstützung

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy | Implementierung |
|---------|-------|------|--------|---------|-------|---------|-----------------|
| **Traffic Splitting** | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | Native/Plugin |
| **Weight-based** | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | Gewichts-Verteilung |
| **Header-based** | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | - | Header-Matching |
| **Cookie-based** | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | - | Cookie-Matching |
| **Dynamic Weights** | ✅ | ✅ | ✅ | ✅ | - | - | Zur Laufzeit änderbar |

**Coverage**: 100% (6 von 6 Open-Source-Providern haben Unterstützung)

**Open-Source Providers:**
- **Envoy**: Weighted Clusters ✅
- **Kong**: Weighted Upstream Targets ✅
- **APISIX**: Native `traffic-split` Plugin ✅
- **Traefik**: WeightedRoundRobin Services ✅
- **Nginx**: `set_random` + conditional routing ✅
- **HAProxy**: Weighted Servers ✅

**Cloud Providers (Limitiert):**
- **Azure APIM**: ⚠️ Begrenzte Unterstützung (Backend Pool ohne Gewichte)
- **AWS API Gateway**: ⚠️ Begrenzte Unterstützung (Weighted Targets in VPC Link)
- **GCP API Gateway**: ⚠️ Keine native Unterstützung (Load Balancer extern)

> **Hinweis:** Cloud-Provider haben eingeschränkte Traffic Splitting-Features.
> Für volle Kontrolle verwende Open-Source Gateways (Envoy, APISIX, Traefik).

---

## Schnellstart

### 1. Einfaches Canary Deployment (90/10)

Verteile 90% Traffic auf stabile Version, 10% auf Canary:

```yaml
version: "1.0"
provider: envoy

services:
  - name: api
    type: rest
    protocol: http
    upstream:
      host: placeholder  # Wird von traffic_split überschrieben
      port: 8080
    routes:
      - path_prefix: /api/v1
        methods: [GET, POST, PUT, DELETE]
        traffic_split:
          enabled: true
          targets:
            - name: stable
              weight: 90
              upstream:
                host: api-v1-stable
                port: 8080
              description: "Stable production version"
            - name: canary
              weight: 10
              upstream:
                host: api-v1-canary
                port: 8080
              description: "Canary deployment for testing"
```

**Deployment:**
```bash
gal generate -f gateway.yaml -o envoy.yaml
```

### 2. A/B Testing (50/50 Split)

Teste zwei Feature-Varianten mit gleichverteiltem Traffic:

```yaml
services:
  - name: ab_testing_api
    type: rest
    protocol: http
    upstream:
      host: placeholder
      port: 8080
    routes:
      - path_prefix: /api/v2
        methods: [GET, POST]
        traffic_split:
          enabled: true
          targets:
            - name: version_a
              weight: 50
              upstream:
                host: api-v2-a
                port: 8080
              description: "Version A - existing algorithm"
            - name: version_b
              weight: 50
              upstream:
                host: api-v2-b
                port: 8080
              description: "Version B - new algorithm"
```

### 3. Header-based Beta Testing

Route Nutzer mit `X-Version: beta` Header zum Beta-Backend:

```yaml
services:
  - name: beta_testing_api
    type: rest
    protocol: http
    upstream:
      host: placeholder
      port: 8080
    routes:
      - path_prefix: /api/beta
        methods: [GET, POST, PUT, DELETE]
        traffic_split:
          enabled: true
          targets:
            - name: production
              weight: 100
              upstream:
                host: api-prod
                port: 8080
            - name: beta
              weight: 0  # Nur via Header-Routing
              upstream:
                host: api-beta
                port: 8080
          routing_rules:
            header_rules:
              - header_name: "X-Version"
                header_value: "beta"
                target_name: "beta"
          fallback_target: "production"
```

**Nutzung:**
```bash
# Normale Nutzer → Production
curl http://api.example.com/api/beta

# Beta-Nutzer → Beta Backend
curl -H "X-Version: beta" http://api.example.com/api/beta
```

### 4. Cookie-based User Segmentation

Route Nutzer mit spezifischem Cookie zum Canary-Backend:

```yaml
services:
  - name: user_segment_api
    type: rest
    protocol: http
    upstream:
      host: placeholder
      port: 8080
    routes:
      - path_prefix: /api/users
        traffic_split:
          enabled: true
          targets:
            - name: stable
              weight: 100
              upstream:
                host: api-stable
                port: 8080
            - name: canary_users
              weight: 0  # Nur via Cookie
              upstream:
                host: api-canary
                port: 8080
          routing_rules:
            cookie_rules:
              - cookie_name: "canary_user"
                cookie_value: "true"
                target_name: "canary_users"
          fallback_target: "stable"
```

---

## Konfigurationsoptionen

### TrafficSplitConfig

Hauptkonfiguration für Traffic Splitting auf Route-Ebene.

```yaml
traffic_split:
  enabled: true|false          # Traffic Splitting aktivieren
  targets: []                  # Liste von SplitTarget (min. 1)
  routing_rules:               # Optional: Header/Cookie Routing
    header_rules: []           # Header-basierte Regeln
    cookie_rules: []           # Cookie-basierte Regeln
  fallback_target: "name"      # Fallback bei nicht-matchenden Rules
```

### SplitTarget

Einzelnes Backend-Ziel mit Gewichtung.

```yaml
targets:
  - name: "stable"                # Eindeutiger Name (required)
    weight: 90                    # Gewichtung 0-100 (required)
    upstream:                     # Backend-Konfiguration (required)
      host: "api-stable"
      port: 8080
    description: "Stable version" # Optional
```

**Validierung:**
- ✅ Gewichte müssen zwischen **0-100** sein
- ✅ Summe aller Gewichte muss **100** sein (außer bei Routing Rules)
- ✅ Target-Namen müssen **eindeutig** sein
- ✅ Mindestens **1 Target** erforderlich

### Header-based Routing Rules

Route basierend auf HTTP-Headern.

```yaml
routing_rules:
  header_rules:
    - header_name: "X-Version"    # HTTP Header (case-insensitive)
      header_value: "beta"        # Erwarteter Wert
      target_name: "beta"         # Ziel-Target
    - header_name: "X-Environment"
      header_value: "staging"
      target_name: "staging"
```

**Priorität:** Header Rules > Cookie Rules > Weight-based

### Cookie-based Routing Rules

Route basierend auf HTTP-Cookies.

```yaml
routing_rules:
  cookie_rules:
    - cookie_name: "canary_user"  # Cookie-Name
      cookie_value: "true"        # Erwarteter Wert
      target_name: "canary"       # Ziel-Target
    - cookie_name: "user_tier"
      cookie_value: "premium"
      target_name: "premium_backend"
```

---

## Provider-Implementierung

### Envoy - Weighted Clusters

Envoy verwendet `weighted_clusters` für Traffic Splitting.

**Generierte Konfiguration:**
```yaml
routes:
  - match:
      prefix: '/api/v1'
    route:
      weighted_clusters:
        clusters:
        - name: canary_deployment_api_stable_cluster
          weight: 90
        - name: canary_deployment_api_canary_cluster
          weight: 10
        total_weight: 100

clusters:
  - name: canary_deployment_api_stable_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api-v1-stable
                port_value: 8080
```

**Eigenschaften:**
- ✅ Exakte Gewichtungen (90% = weight 90)
- ✅ Separate Cluster pro Target
- ✅ Deterministisches Routing
- ⚠️ Header/Cookie-Routing benötigt Lua-Filter

**Deployment:**
```bash
gal generate -f gateway.yaml -o envoy.yaml
envoy -c envoy.yaml
```

### Nginx - set_random + Conditional Routing

Nginx verwendet `set_random` für probabilistische Verteilung.

**Generierte Konfiguration:**
```nginx
location /api/v1 {
    # Weight-based traffic splitting
    set $split_backend '';
    # stable: 90% (cumulative: 90%)
    set_random $rand_split 0 100;
    if ($rand_split < 90) {
        set $split_backend 'stable';
        proxy_pass http://api-v1-stable:8080;
    }
    if ($split_backend = '') {
        set $split_backend 'canary';
        proxy_pass http://api-v1-canary:8080;
    }
}

# Header-based routing
location /api/beta {
    set $backend_target '';
    if ($http_x_version = 'beta') {
        set $backend_target 'beta';
    }
    if ($backend_target = 'beta') {
        proxy_pass http://api-beta:8080;
    }
}
```

**Eigenschaften:**
- ✅ `set_random` für probabilistische Verteilung
- ✅ Header-Routing via `$http_*` Variablen
- ✅ Cookie-Routing via `$cookie_*` Variablen
- ⚠️ Nicht session-persistent (jede Request neu)
- ⚠️ Mehrere `if`-Statements (nicht optimal, aber funktional)

### Kong - Weighted Upstream Targets

Kong verwendet Upstreams mit gewichteten Targets.

**Generierte Konfiguration:**
```yaml
upstreams:
- name: canary_deployment_api_route0_upstream
  algorithm: round-robin
  targets:
  - target: api-v1-stable:8080
    weight: 900  # Kong: 0-1000 (90% = 900)
  - target: api-v1-canary:8080
    weight: 100  # Kong: 0-1000 (10% = 100)

services:
- name: canary_deployment_api
  protocol: http
  host: canary_deployment_api_route0_upstream
  routes:
  - name: canary_deployment_api_route
    paths:
    - /api/v1
```

**Eigenschaften:**
- ✅ Gewichtungsskala 0-1000 (GAL 0-100 × 10)
- ✅ Round-robin respektiert Gewichte
- ✅ Dynamische Rekonfiguration via Admin API
- ⚠️ 1 Service = 1 Upstream (Limitation)
- ⚠️ Header/Cookie-Routing benötigt request-transformer Plugin

### APISIX - traffic-split Plugin

APISIX hat natives `traffic-split` Plugin mit Rules.

**Generierte Konfiguration:**
```json
{
  "routes": [{
    "plugins": {
      "traffic-split": {
        "rules": [
          {
            "match": [{
              "vars": [["http_x_version", "==", "beta"]]
            }],
            "weighted_upstreams": [{
              "upstream": {
                "name": "beta_testing_api_beta_upstream",
                "type": "roundrobin",
                "nodes": {"api-beta:8080": 1}
              },
              "weight": 1
            }]
          },
          {
            "weighted_upstreams": [
              {
                "upstream": {"nodes": {"api-prod:8080": 1}},
                "weight": 100
              },
              {
                "upstream": {"nodes": {"api-beta:8080": 1}},
                "weight": 0
              }
            ]
          }
        ]
      }
    }
  }]
}
```

**Eigenschaften:**
- ✅ Native Plugin-Unterstützung
- ✅ Rules mit `match` Conditions
- ✅ Header-Matching (`http_*` vars)
- ✅ Cookie-Matching (`cookie_*` vars)
- ✅ Keine Lua benötigt
- ✅ Dynamische Rekonfiguration via Admin API

### Traefik - WeightedRoundRobin Services

Traefik verwendet `weighted` Services.

**Generierte Konfiguration:**
```yaml
http:
  routers:
    canary_deployment_api_router_0:
      rule: 'PathPrefix(`/api/v1`)'
      service: canary_deployment_api_route0_service

  services:
    canary_deployment_api_route0_service:
      weighted:
        services:
        - name: canary_deployment_api_stable_service
          weight: 90
        - name: canary_deployment_api_canary_service
          weight: 10

    canary_deployment_api_stable_service:
      loadBalancer:
        servers:
        - url: 'http://api-v1-stable:8080'

    canary_deployment_api_canary_service:
      loadBalancer:
        servers:
        - url: 'http://api-v1-canary:8080'
```

**Eigenschaften:**
- ✅ Native weighted Services
- ✅ Saubere YAML-Struktur
- ✅ Dynamische File Provider Rekonfiguration
- ✅ Kompatibel mit Kubernetes IngressRoute
- ⚠️ Header/Cookie-Routing benötigt separate Router mit Priority

---

## Häufige Anwendungsfälle

### 1. Canary Deployment (Schrittweiser Rollout)

Strategie: Neue Version schrittweise ausrollen (5% → 25% → 50% → 100%)

**Phase 1: 5% Canary**
```yaml
traffic_split:
  enabled: true
  targets:
    - name: current
      weight: 95
      upstream: {host: api-v1, port: 8080}
    - name: new
      weight: 5
      upstream: {host: api-v2, port: 8080}
```

**Phase 2: 25% Canary** (wenn Phase 1 erfolgreich)
```yaml
targets:
  - name: current
    weight: 75
  - name: new
    weight: 25
```

**Phase 3: 50/50 Split**
```yaml
targets:
  - name: current
    weight: 50
  - name: new
    weight: 50
```

**Phase 4: 100% Neues Backend**
```yaml
targets:
  - name: current
    weight: 0
  - name: new
    weight: 100
```

**Rollback:** Gewichte wieder auf `current: 100, new: 0` setzen

### 2. A/B Testing

Strategie: Zwei Versionen parallel testen und Metriken vergleichen

```yaml
traffic_split:
  enabled: true
  targets:
    - name: version_a
      weight: 50
      upstream: {host: api-v2-a, port: 8080}
      description: "Existing recommendation algorithm"
    - name: version_b
      weight: 50
      upstream: {host: api-v2-b, port: 8080}
      description: "New ML-based recommendation"
```

**Metriken sammeln:**
- Conversion Rate
- Click-Through Rate (CTR)
- Response Time
- Error Rate

**Auswertung:**
```bash
# Prometheus Queries
rate(http_requests_total{version="a"}[5m])
rate(http_requests_total{version="b"}[5m])
```

### 3. Blue/Green Deployment

Strategie: Sofortiges Switching zwischen zwei Versionen

**Blue aktiv, Green standby:**
```yaml
traffic_split:
  enabled: true
  targets:
    - name: blue
      weight: 100
      upstream: {host: api-blue, port: 8080}
    - name: green
      weight: 0
      upstream: {host: api-green, port: 8080}
```

**Instant Switch zu Green:**
```yaml
targets:
  - name: blue
    weight: 0
  - name: green
    weight: 100
```

**Rollback:** Instant Switch zurück zu Blue

### 4. Feature Flags via Headers

Strategie: Features via HTTP-Header freischalten

```yaml
traffic_split:
  enabled: true
  targets:
    - name: stable
      weight: 100
      upstream: {host: api-stable, port: 8080}
    - name: experimental
      weight: 0
      upstream: {host: api-experimental, port: 8080}
  routing_rules:
    header_rules:
      - header_name: "X-Feature-Flag"
        header_value: "new-checkout"
        target_name: "experimental"
  fallback_target: "stable"
```

**Nutzung:**
```bash
# Standard-Nutzer → Stable
curl http://api.example.com/checkout

# Beta-Tester → Experimental
curl -H "X-Feature-Flag: new-checkout" http://api.example.com/checkout
```

### 5. User Segmentation (Premium/Free)

Strategie: Verschiedene Nutzergruppen auf verschiedene Backends routen

```yaml
traffic_split:
  enabled: true
  targets:
    - name: free_tier
      weight: 80
      upstream: {host: api-free, port: 8080}
    - name: premium_tier
      weight: 20
      upstream: {host: api-premium, port: 8080}
  routing_rules:
    cookie_rules:
      - cookie_name: "user_tier"
        cookie_value: "premium"
        target_name: "premium_tier"
    header_rules:
      - header_name: "X-Subscription"
        header_value: "premium"
        target_name: "premium_tier"
  fallback_target: "free_tier"
```

### 6. Multi-Stage Rollout (3 Versionen gleichzeitig)

Strategie: Stable, Beta und Canary gleichzeitig laufen lassen

```yaml
traffic_split:
  enabled: true
  targets:
    - name: stable
      weight: 70
      upstream: {host: api-stable, port: 8080}
    - name: beta
      weight: 20
      upstream: {host: api-beta, port: 8080}
    - name: canary
      weight: 10
      upstream: {host: api-canary, port: 8080}
```

---

## Best Practices

### 1. Gewichte schrittweise erhöhen

❌ **Schlecht:** Sofort von 0% auf 100%
```yaml
# Riskant: Neue Version erhält sofort 100% Traffic
targets:
  - {name: old, weight: 0}
  - {name: new, weight: 100}
```

✅ **Gut:** Schrittweise erhöhen mit Monitoring
```yaml
# Phase 1: 5% Canary
targets:
  - {name: old, weight: 95}
  - {name: new, weight: 5}

# Phase 2 (nach 24h Monitoring): 25%
# Phase 3 (nach weiteren 24h): 50%
# Phase 4 (nach weiteren 24h): 100%
```

### 2. Immer Monitoring einrichten

Überwache folgende Metriken pro Traffic Split Target:

```yaml
# Prometheus Metriken
- http_requests_total{target="stable"}
- http_requests_total{target="canary"}
- http_request_duration_seconds{target="stable"}
- http_request_duration_seconds{target="canary"}
- http_errors_total{target="stable"}
- http_errors_total{target="canary"}
```

### 3. Fallback-Target definieren

Immer einen Fallback für Header/Cookie-Routing:

```yaml
traffic_split:
  enabled: true
  targets: [...]
  routing_rules: [...]
  fallback_target: "stable"  # ✅ Wichtig!
```

### 4. Session Stickiness beachten

⚠️ **Problem:** Nutzer wechseln zwischen Backends
```yaml
# Schlecht: Nutzer kann zwischen stable/canary springen
# → Schlechte User Experience
traffic_split:
  enabled: true
  targets:
    - {name: stable, weight: 50}
    - {name: canary, weight: 50}
```

✅ **Lösung:** Session Cookies verwenden
```yaml
# Nutzer bleiben auf demselben Backend
routing_rules:
  cookie_rules:
    - cookie_name: "backend_version"
      cookie_value: "canary"
      target_name: "canary"
```

### 5. Rollback-Plan bereithalten

Immer einen schnellen Rollback-Mechanismus:

```bash
# Rollback via CLI
gal generate -f gateway-rollback.yaml -o envoy.yaml
envoy -c envoy.yaml --hot-restart

# Oder: Gewichte dynamisch anpassen (APISIX/Kong)
curl -X PATCH http://apisix-admin:9080/apisix/admin/routes/1 \
  -d '{"plugins": {"traffic-split": {"rules": [...]}}}'
```

### 6. Dokumentiere Target-Versionen

Klare Beschreibungen für jedes Target:

```yaml
targets:
  - name: v1_2_5
    weight: 90
    upstream: {host: api-v1-2-5, port: 8080}
    description: "Stable version 1.2.5 (2024-01-15)"
  - name: v1_3_0_rc1
    weight: 10
    upstream: {host: api-v1-3-0-rc1, port: 8080}
    description: "Release Candidate 1.3.0-rc1 (2024-01-20)"
```

### 7. Rate Limiting pro Target

Verhindere, dass Canary überlastet wird:

```yaml
routes:
  - path_prefix: /api
    traffic_split: [...]
    rate_limit:
      enabled: true
      requests_per_second: 1000  # Limit für gesamten Endpunkt
```

---

## Traffic Splitting Testen

### 1. Unit Tests (Lokale Entwicklung)

Teste Config-Validierung:

```python
from gal.config import TrafficSplitConfig, SplitTarget, UpstreamTarget

def test_weight_sum_validation():
    target1 = SplitTarget(name="stable", weight=90, ...)
    target2 = SplitTarget(name="canary", weight=20, ...)  # Summe = 110

    with pytest.raises(ValueError, match="must sum to 100"):
        TrafficSplitConfig(enabled=True, targets=[target1, target2])
```

### 2. Integration Tests (Provider Output)

Teste generierte Konfiguration:

```python
def test_envoy_weighted_clusters():
    config = Config.from_yaml("traffic-split-example.yaml")
    provider = EnvoyProvider()
    output = provider.generate(config)

    assert "weighted_clusters:" in output
    assert "weight: 90" in output
    assert "weight: 10" in output
```

### 3. Manuelle Tests (Browser/cURL)

**Weight-based Testing:**
```bash
# 100 Requests senden, Verteilung prüfen
for i in {1..100}; do
  curl -s http://localhost:8080/api | grep -o "Backend: [a-z]*"
done | sort | uniq -c

# Erwartete Ausgabe (90/10 Split):
# 90 Backend: stable
# 10 Backend: canary
```

**Header-based Testing:**
```bash
# Normal → Production
curl -v http://localhost:8080/api | grep "Backend:"
# Output: Backend: production

# Mit Beta-Header → Beta
curl -v -H "X-Version: beta" http://localhost:8080/api | grep "Backend:"
# Output: Backend: beta
```

**Cookie-based Testing:**
```bash
# Mit Canary-Cookie → Canary
curl -v --cookie "canary_user=true" http://localhost:8080/api | grep "Backend:"
# Output: Backend: canary
```

### 4. Load Testing (k6, Apache Bench)

**k6 Script für Traffic Split Testing:**

```javascript
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  vus: 100,
  duration: '30s',
};

export default function() {
  let res = http.get('http://localhost:8080/api');
  check(res, {
    'is status 200': (r) => r.status === 200,
    'backend is stable or canary': (r) =>
      r.body.includes('Backend: stable') ||
      r.body.includes('Backend: canary'),
  });
}
```

**Ausführen:**
```bash
k6 run traffic-split-test.js

# Ergebnis analysieren:
# http_req_duration..........: avg=10ms min=5ms max=50ms
# Backend stable: ~90% der Requests
# Backend canary: ~10% der Requests
```

---

## Troubleshooting

### Problem 1: Gewichte summieren sich nicht zu 100

**Fehlermeldung:**
```
ValueError: Total weight must sum to 100 for weight-based routing, got 110
```

**Lösung:**
```yaml
# ❌ Falsch: 90 + 20 = 110
targets:
  - {name: stable, weight: 90}
  - {name: canary, weight: 20}

# ✅ Korrekt: 90 + 10 = 100
targets:
  - {name: stable, weight: 90}
  - {name: canary, weight: 10}
```

### Problem 2: Fallback Target existiert nicht

**Fehlermeldung:**
```
ValueError: Fallback target 'production' not found in targets
```

**Lösung:**
```yaml
# ❌ Falsch: Target "production" nicht in Liste
targets:
  - {name: stable, weight: 100}
  - {name: canary, weight: 0}
fallback_target: "production"  # Existiert nicht!

# ✅ Korrekt: Fallback muss in targets sein
targets:
  - {name: production, weight: 100}
  - {name: canary, weight: 0}
fallback_target: "production"
```

### Problem 3: Alle Requests gehen zu einem Backend

**Symptom:** Trotz 90/10 Split gehen 100% zu einem Backend

**Mögliche Ursachen:**
1. **Provider nicht neu gestartet**
   ```bash
   # Lösung: Provider neu laden
   docker restart envoy
   nginx -s reload
   ```

2. **Falsche Cluster-Namen (Envoy)**
   ```bash
   # Check Envoy Admin API
   curl http://localhost:9901/clusters | grep api

   # Erwartet: api_stable_cluster, api_canary_cluster
   ```

3. **Kong Upstream nicht aktiv**
   ```bash
   # Check Kong Admin API
   curl http://localhost:8001/upstreams/api_route0_upstream/targets

   # Erwartet: Beide Targets mit korrekten Gewichten
   ```

### Problem 4: Header-Routing funktioniert nicht

**Symptom:** Header wird ignoriert, fallback_target wird verwendet

**Debug-Schritte:**

1. **Header-Namen Case-Sensitivity prüfen**
   ```yaml
   # ❌ Falsch: Header-Namen sind case-sensitive
   header_rules:
     - header_name: "x-version"  # Wird als "X-Version" gesendet!

   # ✅ Korrekt: Exakte Schreibweise verwenden
   header_rules:
     - header_name: "X-Version"
   ```

2. **Provider-spezifische Variable prüfen**
   ```nginx
   # Nginx: Header "X-Version" → Variable "$http_x_version"
   if ($http_x_version = 'beta') {
       proxy_pass http://api-beta:8080;
   }
   ```

3. **APISIX vars prüfen**
   ```json
   // APISIX: "X-Version" → "http_x_version"
   {
     "vars": [["http_x_version", "==", "beta"]]
   }
   ```

### Problem 5: Traffic Split zu langsam

**Symptom:** Response Time deutlich höher mit Traffic Splitting

**Mögliche Ursachen:**
1. **Zu viele if-Statements (Nginx)**
   ```nginx
   # Problematisch: 10+ if-Statements
   # Lösung: Nginx Plus verwenden oder zu APISIX wechseln
   ```

2. **Upstream Health Checks fehlen**
   ```yaml
   # Lösung: Health Checks hinzufügen
   upstream:
     health_check:
       active:
         enabled: true
         interval: "10s"
   ```

3. **Connection Pooling deaktiviert**
   ```yaml
   # Lösung: Connection Pooling aktivieren
   upstream:
     load_balancer:
       algorithm: round_robin
       sticky_sessions: true  # Reduziert Connection Overhead
   ```

---

## Weiterführende Ressourcen

### Provider-Dokumentation
- [Envoy Weighted Clusters](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/route/v3/route_components.proto#envoy-v3-api-msg-config-route-v3-weightedcluster)
- [Kong Load Balancing](https://docs.konghq.com/gateway/latest/admin-api/load-balancing/)
- [APISIX traffic-split Plugin](https://apisix.apache.org/docs/apisix/plugins/traffic-split/)
- [Traefik Weighted Services](https://doc.traefik.io/traefik/routing/services/#weighted-round-robin)
- [Nginx split_clients](https://nginx.org/en/docs/http/ngx_http_split_clients_module.html)

### Deployment Patterns
- [Martin Fowler: BlueGreenDeployment](https://martinfowler.com/bliki/BlueGreenDeployment.html)
- [Martin Fowler: CanaryRelease](https://martinfowler.com/bliki/CanaryRelease.html)
- [Google: Deployment Patterns](https://cloud.google.com/architecture/application-deployment-and-testing-strategies)

### GAL Beispiele
- [examples/traffic-split-example.yaml](../../examples/traffic-split-example.yaml)
- [tests/test_traffic_split.py](../../tests/test_traffic_split.py)

---

**Version:** 1.4.0
**Feature:** A/B Testing & Traffic Splitting
**Letzte Aktualisierung:** 2025-01-22
