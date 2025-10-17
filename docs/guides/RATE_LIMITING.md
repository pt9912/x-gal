# Rate Limiting Guide

## Overview

Rate Limiting ist ein essenzielles Feature zur Kontrolle der Anzahl von Anfragen, die ein Client an Ihre API senden kann. Es hilft, Ihre Backend-Services vor Überlastung zu schützen und stellt sicher, dass alle Clients fair auf Ressourcen zugreifen können.

GAL v1.1.0 bietet native Rate Limiting Unterstützung für alle unterstützten Gateway-Provider:
- **Kong**: rate-limiting Plugin
- **APISIX**: limit-count Plugin
- **Traefik**: rateLimit Middleware
- **Envoy**: local_ratelimit Filter

## Quick Start

### Einfaches Rate Limiting

Fügen Sie Rate Limiting zu einer Route hinzu:

```yaml
services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.internal
      port: 8080
    routes:
      - path_prefix: /api/v1
        methods: [GET, POST]
        rate_limit:
          enabled: true
          requests_per_second: 100
          burst: 200
```

## Konfigurationsoptionen

### Vollständige Rate Limit Konfiguration

```yaml
rate_limit:
  enabled: true                          # Standard: true
  requests_per_second: 100               # Standard: 100
  burst: 200                             # Standard: requests_per_second * 2
  key_type: ip_address                   # Standard: ip_address
  key_header: X-API-Key                  # Optional: für key_type: header
  key_claim: sub                         # Optional: für key_type: jwt_claim
  response_status: 429                   # Standard: 429
  response_message: "Rate limit exceeded" # Standard: "Rate limit exceeded"
```

### Parameter-Beschreibung

| Parameter | Typ | Standard | Beschreibung |
|-----------|-----|----------|--------------|
| `enabled` | boolean | `true` | Aktiviert oder deaktiviert Rate Limiting |
| `requests_per_second` | integer | `100` | Maximale Anzahl von Anfragen pro Sekunde |
| `burst` | integer | `requests_per_second * 2` | Burst-Kapazität für kurzzeitige Spitzen |
| `key_type` | string | `ip_address` | Identifizierungs-Methode (ip_address, header, jwt_claim) |
| `key_header` | string | `null` | Header-Name wenn key_type=header |
| `key_claim` | string | `null` | JWT Claim wenn key_type=jwt_claim |
| `response_status` | integer | `429` | HTTP Status Code bei Rate Limit Überschreitung |
| `response_message` | string | `"Rate limit exceeded"` | Fehlermeldung bei Rate Limit Überschreitung |

## Key Types

### IP-basiertes Rate Limiting

Limitiert basierend auf der Client-IP-Adresse (Standard):

```yaml
rate_limit:
  enabled: true
  requests_per_second: 100
  key_type: ip_address
```

### Header-basiertes Rate Limiting

Limitiert basierend auf einem spezifischen Request-Header (z.B. API-Key):

```yaml
rate_limit:
  enabled: true
  requests_per_second: 1000
  key_type: header
  key_header: X-API-Key
```

### JWT Claim-basiertes Rate Limiting

Limitiert basierend auf einem JWT Claim (z.B. user ID):

```yaml
rate_limit:
  enabled: true
  requests_per_second: 500
  key_type: jwt_claim
  key_claim: sub
```

## Beispiele

### Public vs. Private API

Unterschiedliche Limits für verschiedene Endpunkte:

```yaml
services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.internal
      port: 8080
    routes:
      # Public API - niedrigeres Limit
      - path_prefix: /api/public
        methods: [GET]
        rate_limit:
          enabled: true
          requests_per_second: 10
          burst: 20
          key_type: ip_address

      # Authenticated API - höheres Limit
      - path_prefix: /api/private
        methods: [GET, POST, PUT, DELETE]
        rate_limit:
          enabled: true
          requests_per_second: 100
          burst: 200
          key_type: header
          key_header: X-API-Key
```

### Custom Error Response

Benutzerdefinierte Fehlerantwort:

```yaml
rate_limit:
  enabled: true
  requests_per_second: 50
  response_status: 503
  response_message: "Service temporarily unavailable due to high load"
```

### Rate Limiting mit Transformationen

Kombinieren Sie Rate Limiting mit Request Transformations:

```yaml
services:
  - name: user_service
    type: rest
    protocol: http
    upstream:
      host: users.internal
      port: 8080
    routes:
      - path_prefix: /api/users
        methods: [POST]
        rate_limit:
          enabled: true
          requests_per_second: 50
          burst: 100
    transformation:
      enabled: true
      defaults:
        created_by: "api"
      computed_fields:
        - field: id
          generator: uuid
          prefix: "usr_"
```

## Provider-spezifische Implementierungen

### Kong

Kong verwendet das `rate-limiting` Plugin:

```yaml
# Generierte Kong-Konfiguration
- name: api_service_route
  paths:
    - /api/v1
  plugins:
    - name: rate-limiting
      config:
        second: 100
        policy: local
        fault_tolerant: true
```

**Features:**
- ✅ Per-Route Konfiguration
- ✅ Lokale oder verteilte Rate Limiting (Redis/Cluster)
- ✅ Verschiedene Zeitfenster (second, minute, hour, day)

### APISIX

APISIX verwendet das `limit-count` Plugin:

```json
{
  "routes": [{
    "uri": "/api/v1/*",
    "plugins": {
      "limit-count": {
        "count": 100,
        "time_window": 1,
        "rejected_code": 429,
        "rejected_msg": "Rate limit exceeded",
        "key": "remote_addr",
        "policy": "local"
      }
    }
  }]
}
```

**Features:**
- ✅ Per-Route Konfiguration
- ✅ Flexible Key-Strategien (IP, Header, Consumer)
- ✅ Redis-basierte verteilte Limits

### Traefik

Traefik verwendet die `rateLimit` Middleware:

```yaml
http:
  middlewares:
    api_service_router_0_ratelimit:
      rateLimit:
        average: 100
        burst: 200
  routers:
    api_service_router_0:
      rule: 'PathPrefix(`/api/v1`)'
      middlewares:
        - api_service_router_0_ratelimit
```

**Features:**
- ✅ Per-Route Konfiguration
- ✅ Token-Bucket-Algorithmus
- ✅ Burst-Handling

### Envoy

Envoy verwendet den `local_ratelimit` Filter:

```yaml
http_filters:
  - name: envoy.filters.http.local_ratelimit
    typed_config:
      '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
      stat_prefix: http_local_rate_limiter
      token_bucket:
        max_tokens: 200
        tokens_per_fill: 100
        fill_interval: 1s
      status_code: 429
```

**Features:**
- ⚠️ Globale Konfiguration (gilt für alle Routes)
- ✅ Token-Bucket-Algorithmus
- ✅ Hochperformant (C++)

**Hinweis:** Die aktuelle Envoy-Implementierung verwendet eine globale Rate Limiting Konfiguration. Für per-route Konfigurationen sollte der externe Rate Limit Service verwendet werden.

## Best Practices

### 1. Burst-Dimensionierung

Setzen Sie `burst` auf das 2-3-fache von `requests_per_second`:

```yaml
rate_limit:
  requests_per_second: 100
  burst: 200  # 2x für normale Spitzen
  # burst: 300  # 3x für höhere Variabilität
```

### 2. Gestaffelte Limits

Unterschiedliche Limits für verschiedene Zugriffsebenen:

```yaml
# Free Tier
rate_limit:
  requests_per_second: 10

# Paid Tier
rate_limit:
  requests_per_second: 100

# Enterprise
rate_limit:
  requests_per_second: 1000
```

### 3. Aussagekräftige Fehlermeldungen

Geben Sie hilfreiche Fehlerantworten:

```yaml
rate_limit:
  enabled: true
  requests_per_second: 100
  response_status: 429
  response_message: "Rate limit of 100 requests per second exceeded. Please retry after 1 second."
```

### 4. Monitoring

Überwachen Sie Rate Limiting Metriken:
- Anzahl der gerateten Anfragen
- Top-IPs/Keys die gelimitiert werden
- Rate Limit Auslastung (aktuell/maximum)

### 5. Graceful Degradation

Verwenden Sie progressive Rate Limits:

```yaml
# Warn bei 80%
rate_limit:
  requests_per_second: 100
  burst: 120  # Kleiner Burst für Warnungen

# Block bei 100%
rate_limit:
  requests_per_second: 100
  burst: 200  # Größerer Burst für harte Limits
```

## Troubleshooting

### Problem: Legitime Benutzer werden geblockt

**Lösung:** Erhöhen Sie den `burst` Wert:

```yaml
rate_limit:
  requests_per_second: 100
  burst: 500  # Erhöht von 200
```

### Problem: Rate Limits greifen nicht

**Lösung:** Überprüfen Sie:
1. `enabled: true` ist gesetzt
2. Provider-Konfiguration wurde deployed
3. Provider wurde neu gestartet (bei file-based configs)

### Problem: Zu viele False Positives

**Lösung:** Wechseln Sie von IP zu Header/JWT-basiertem Rate Limiting:

```yaml
rate_limit:
  key_type: header
  key_header: X-API-Key
```

## Testing

### Manuelles Testing mit curl

```bash
# Test Rate Limiting
for i in {1..150}; do
  curl -w "\n%{http_code}\n" http://localhost:10000/api/v1/test
  sleep 0.01
done

# Mit API Key
for i in {1..150}; do
  curl -H "X-API-Key: test123" \
       -w "\n%{http_code}\n" \
       http://localhost:10000/api/v1/test
done
```

### Load Testing mit ab (Apache Bench)

```bash
# 1000 Requests, 10 gleichzeitige Connections
ab -n 1000 -c 10 http://localhost:10000/api/v1/test

# Mit Custom Header
ab -n 1000 -c 10 -H "X-API-Key: test123" \
   http://localhost:10000/api/v1/test
```

## Migration von v1.0.0

In GAL v1.0.0 gab es kein natives Rate Limiting. Migrieren Sie bestehende Konfigurationen:

**Vorher (v1.0.0 - manuell konfiguriert):**
```yaml
# Manuelles Rate Limiting Plugin (Kong)
plugins:
  - name: rate_limiting
    enabled: true
    config:
      requests_per_second: 100
```

**Nachher (v1.1.0 - nativ):**
```yaml
# Native Rate Limiting Konfiguration
routes:
  - path_prefix: /api/v1
    rate_limit:
      enabled: true
      requests_per_second: 100
      burst: 200
```

## Weiterführende Ressourcen

- [v1.1.0 Implementierungsplan](../v1.1.0-PLAN.md)
- [Roadmap](../../ROADMAP.md)
- [Provider-Dokumentation](PROVIDERS.md)

### Provider-spezifische Dokumentation

- [Kong Rate Limiting Plugin](https://docs.konghq.com/hub/kong-inc/rate-limiting/)
- [APISIX limit-count Plugin](https://apisix.apache.org/docs/apisix/plugins/limit-count/)
- [Traefik RateLimit Middleware](https://doc.traefik.io/traefik/middlewares/http/ratelimit/)
- [Envoy Local Rate Limit](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/local_rate_limit_filter)

## Zusammenfassung

Rate Limiting ist ein kritisches Feature für Production-APIs. GAL v1.1.0 bietet:

✅ **Einheitliche Konfiguration** für alle Provider
✅ **Flexible Key-Strategien** (IP, Header, JWT)
✅ **Burst-Handling** für Traffic-Spitzen
✅ **Custom Error Responses**
✅ **Per-Route Konfiguration**

Beginnen Sie mit konservativen Limits und passen Sie basierend auf Monitoring-Daten an.
