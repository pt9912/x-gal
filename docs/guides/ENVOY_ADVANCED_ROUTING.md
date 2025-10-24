# Envoy Advanced Routing Guide

Comprehensive guide for implementing advanced routing with Envoy through GAL.

## 📋 Übersicht

Advanced Routing ermöglicht es, Requests basierend auf verschiedenen Kriterien an unterschiedliche Backends zu routen:
- **Header-based Routing**: Route basierend auf HTTP-Headers
- **Query Parameter Routing**: Route basierend auf Query-Parametern
- **JWT Claims Routing**: Route basierend auf JWT-Token Claims
- **Geo-based Routing**: Route basierend auf geografischen Informationen

## 🎯 Unterstützte Features

### Header-based Routing
- **Exact Match**: Header muss exakt einem Wert entsprechen
- **Prefix Match**: Header muss mit einem Prefix beginnen
- **Contains Match**: Header muss einen Substring enthalten
- **Regex Match**: Header muss einem regulären Ausdruck entsprechen

### Query Parameter Routing
- **Exact Match**: Parameter muss exakt einem Wert entsprechen
- **Exists Check**: Parameter muss vorhanden sein (Wert egal)
- **Regex Match**: Parameter muss einem regulären Ausdruck entsprechen

### JWT Claims Routing (mit Lua)
- **Role-based**: Route basierend auf `role` Claim
- **Scope-based**: Route basierend auf `scope` Claim
- **Custom Claims**: Route basierend auf beliebigen Claims

### Geo-based Routing (mit GeoIP)
- **Country-based**: Route basierend auf Herkunftsland
- **Region-based**: Route basierend auf Region/Kontinent

## 📝 Konfiguration

### Basis-Beispiel

```yaml
# gal-config.yaml
services:
  - name: api_service
    routes:
      - path_prefix: /api

        # Advanced Routing Konfiguration
        advanced_routing:
          enabled: true
          strategy: first_match  # oder "all_match"

          # Header-based Rules
          header_rules:
            - header_name: "X-API-Version"
              match_type: exact
              match_value: "v2"
              target: "v2_backend"
              description: "Route to v2 backend for API version 2"

            - header_name: "User-Agent"
              match_type: contains
              match_value: "Mobile"
              target: "mobile_backend"
              description: "Route mobile clients to optimized backend"

          # Query Parameter Rules
          query_param_rules:
            - param_name: "beta"
              match_type: exact
              match_value: "true"
              target: "beta_backend"
              description: "Route beta users to beta backend"

            - param_name: "admin"
              match_type: exists
              target: "admin_backend"
              description: "Route admin requests to admin backend"

        # Advanced Routing Targets
        advanced_routing_targets:
          - name: "v2_backend"
            upstream:
              host: backend-v2
              port: 8080
            description: "Version 2 API backend"

          - name: "mobile_backend"
            upstream:
              host: backend-mobile
              port: 8080
            description: "Optimized mobile API backend"

          - name: "beta_backend"
            upstream:
              host: backend-beta
              port: 8080
            description: "Beta features backend"

          - name: "admin_backend"
            upstream:
              host: backend-admin
              port: 8080
            description: "Admin API with extended permissions"

        # Fallback für nicht gematchte Requests
        upstream:
          host: backend-v1
          port: 8080
```

### Erweiterte Beispiele

#### 1. Multi-Criteria Routing

```yaml
advanced_routing:
  enabled: true
  strategy: first_match

  header_rules:
    # Exakte API-Version
    - header_name: "X-API-Version"
      match_type: exact
      match_value: "v2"
      target: "v2_backend"

    # Mobile User-Agents
    - header_name: "User-Agent"
      match_type: regex
      match_value: ".*(iPhone|Android|Mobile).*"
      target: "mobile_backend"

    # Beta Features
    - header_name: "X-Beta-Features"
      match_type: exact
      match_value: "enabled"
      target: "beta_backend"

    # Admin Access
    - header_name: "X-Admin-Access"
      match_type: exact
      match_value: "true"
      target: "admin_backend"

    # EU Region
    - header_name: "X-Region"
      match_type: exact
      match_value: "EU"
      target: "eu_backend"
```

#### 2. JWT Claims Routing (Benötigt Lua Filter)

```yaml
advanced_routing:
  enabled: true

  jwt_claims_rules:
    - claim_path: "role"
      match_type: exact
      match_value: "admin"
      target: "admin_backend"
      description: "Route admin users to admin backend"

    - claim_path: "subscription"
      match_type: exact
      match_value: "premium"
      target: "premium_backend"
      description: "Route premium users to high-performance backend"
```

#### 3. Geo-based Routing (Benötigt GeoIP Database)

```yaml
advanced_routing:
  enabled: true

  geo_rules:
    - geo_type: country
      match_value: "DE"
      target: "eu_backend"
      description: "Route German traffic to EU backend"

    - geo_type: country
      match_value: "US"
      target: "us_backend"
      description: "Route US traffic to US backend"
```

## 🚀 Generierte Envoy-Konfiguration

GAL generiert automatisch die entsprechende Envoy-Konfiguration:

```yaml
# envoy.yaml (generiert)
static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          route_config:
            virtual_hosts:
            - name: backend
              domains: ['*']
              routes:
              # Header-based Route
              - match:
                  prefix: '/api'
                  headers:
                  - name: X-API-Version
                    exact_match: 'v2'
                route:
                  cluster: api_service_v2_backend_cluster

              # Query Parameter Route
              - match:
                  prefix: '/api'
                  query_parameters:
                  - name: beta
                    string_match:
                      exact: 'true'
                route:
                  cluster: api_service_beta_backend_cluster

              # Fallback Route
              - match:
                  prefix: '/api'
                route:
                  cluster: api_service_cluster

  clusters:
  - name: api_service_v2_backend_cluster
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: api_service_v2_backend_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: backend-v2
                port_value: 8080
```

## 🧪 Testing

### Unit Tests

```python
# tests/test_advanced_routing.py
import pytest
from gal.config import Config
from gal.providers.envoy import EnvoyProvider

def test_header_routing_generation():
    """Test header-based routing generates correct Envoy config."""
    config = Config.from_yaml("examples/advanced-routing.yaml")
    provider = EnvoyProvider(config)
    envoy_config = provider.generate()

    # Verify header matching rules are generated
    assert "X-API-Version" in envoy_config
    assert "exact_match: 'v2'" in envoy_config
    assert "api_service_v2_backend_cluster" in envoy_config
```

### E2E Tests mit Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  envoy:
    image: envoyproxy/envoy:v1.31-latest
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml
    ports:
      - "8080:8080"
      - "9901:9901"  # Admin interface
    command: ["-c", "/etc/envoy/envoy.yaml"]
    networks:
      - test-network

  backend-v1:
    build:
      context: ../../../backends
      dockerfile: Dockerfile.backend
    environment:
      BACKEND_NAME: backend-v1
      BACKEND_VERSION: v1
    networks:
      - test-network

  backend-v2:
    build:
      context: ../../../backends
      dockerfile: Dockerfile.backend
    environment:
      BACKEND_NAME: backend-v2
      BACKEND_VERSION: v2
    networks:
      - test-network

networks:
  test-network:
    driver: bridge
```

### Test Execution

```python
# test_envoy_advanced_routing.py
def test_header_routing_e2e():
    """Test that header-based routing works in E2E setup."""
    # Send request with X-API-Version: v2
    response = requests.get(
        "http://localhost:8080/api",
        headers={"X-API-Version": "v2"}
    )
    assert response.status_code == 200
    assert response.json()["backend"]["name"] == "backend-v2"
```

## 🔍 Debugging

### Envoy Admin Interface

```bash
# Cluster Status anzeigen
curl http://localhost:9901/clusters

# Route-Konfiguration anzeigen
curl http://localhost:9901/config_dump | jq '.configs[] | select(.["@type"] == "type.googleapis.com/envoy.admin.v3.RoutesConfigDump")'

# Statistiken anzeigen
curl http://localhost:9901/stats

# Prometheus Metrics
curl http://localhost:9901/stats/prometheus
```

### Log Analysis

```python
# analyze_logs.py
class LogAnalyzer:
    def analyze_routing_decisions(self):
        """Analyze Envoy routing decisions from logs."""
        # Parse Envoy logs
        # Extract routing decisions
        # Verify correct backend selection
```

## ⚡ Performance-Optimierung

### Route Ordering
- Routes werden in der Reihenfolge evaluiert (first_match)
- Häufigste Routes zuerst platzieren
- Spezifische Routes vor generischen Routes

### Connection Pooling
```yaml
clusters:
- name: backend_cluster
  connect_timeout: 5s
  per_connection_buffer_limit_bytes: 1048576
  circuit_breakers:
    thresholds:
    - priority: DEFAULT
      max_connections: 1024
      max_pending_requests: 1024
```

## 🚨 Häufige Probleme

### Problem: Header wird nicht gematcht
**Lösung**: Überprüfen Sie die exakte Schreibweise (case-sensitive!)

### Problem: Query Parameter werden ignoriert
**Lösung**: Stellen Sie sicher, dass der Parameter URL-encoded ist

### Problem: Fallback wird nicht verwendet
**Lösung**: Fallback-Route muss als letzte Route definiert sein

## 📊 Monitoring

### Wichtige Metriken
- `envoy_cluster_upstream_rq_total`: Requests pro Cluster
- `envoy_cluster_upstream_rq_2xx`: Erfolgreiche Requests
- `envoy_http_downstream_rq_total`: Gesamte eingehende Requests
- `envoy_router_downstream_rq_total`: Geroutete Requests

## 🔗 Weiterführende Dokumentation

- [Envoy Route Matching](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/route/v3/route_components.proto)
- [Envoy Header Matching](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/route/v3/route_components.proto#config-route-v3-headermatcher)
- [Envoy Query Parameter Matching](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/route/v3/route_components.proto#config-route-v3-queryparametermatcher)