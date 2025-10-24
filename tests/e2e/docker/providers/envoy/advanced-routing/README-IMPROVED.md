# Envoy Advanced Routing - Vollständige Implementierung

Diese verbesserte Implementierung zeigt **alle** Advanced Routing Features von Envoy:

## Features

### 1. **Header-based Routing** ✅
- `X-API-Version: v2` → backend-v2
- `User-Agent: Mobile` → backend-mobile
- `X-Beta-Features: enabled` → backend-beta

### 2. **Query Parameter Routing** ✅
- `?version=2` → backend-v2
- `?beta=true` → backend-beta
- `?admin` → backend-admin

### 3. **JWT Claim-based Routing** ✅
- JWT mit `role=admin` → backend-admin
- Vollständige JWT-Validierung mit JWKS
- Lua Filter für Claim-Extraktion

### 4. **GeoIP-based Routing** ✅
- IP aus Deutschland (`192.168.1.1`) → backend-eu
- ext_authz gRPC Service für GeoIP-Lookups
- Metadata-basiertes Routing

### 5. **Fallback Routing** ✅
- Keine Regel matcht → backend-v1 (Default)

## Architektur

```
┌──────────────┐
│   Client     │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│              Envoy Gateway (Port 8080)                │
│  ┌────────────────────────────────────────────────┐  │
│  │  HTTP Filters (Processing Order):              │  │
│  │  1. JWT Authn Filter                           │  │
│  │     - Validates JWT tokens                     │  │
│  │     - Extracts claims to metadata              │  │
│  │  2. Ext Authz Filter (GeoIP)                   │  │
│  │     - Calls GeoIP gRPC service                 │  │
│  │     - Adds country to metadata                 │  │
│  │  3. Lua Filter                                 │  │
│  │     - Processes JWT claims                     │  │
│  │     - Adds debug headers                       │  │
│  │  4. Router Filter                              │  │
│  │     - Routes based on headers/query/metadata   │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌─────────────┐   ┌─────────────┐
│ JWKS Service│   │GeoIP Service│
│  (Port 8080)│   │ (Port 9090) │
└─────────────┘   └─────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│  Backend Services (alle Port 8080)          │
│  - backend-v1 (Default/Fallback)             │
│  - backend-v2 (API Version 2)                │
│  - backend-admin (Admin Features)            │
│  - backend-eu (EU Region/GDPR)               │
│  - backend-beta (Beta Features)              │
│  - backend-mobile (Mobile Optimized)         │
└──────────────────────────────────────────────┘
```

## Unterschiede zur Original-Implementierung

| Feature | Original (envoy.yaml) | Improved (envoy-improved.yaml) |
|---------|----------------------|-------------------------------|
| JWT Routing | ❌ Nur Kommentar | ✅ Vollständig implementiert |
| GeoIP Routing | ❌ Nur Kommentar | ✅ Mit gRPC ext_authz |
| JWT Validation | ❌ Keine | ✅ JWKS-basiert |
| Claim Extraction | ❌ Keine | ✅ Lua Filter |
| Metadata Routing | ❌ Keine | ✅ JWT + GeoIP metadata |
| Debug Headers | ❌ Keine | ✅ X-Routing-Rule, X-JWT-Role, X-Geo-Country |
| Services | 6 Backends | 8 Services (6 Backends + JWKS + GeoIP) |

## Setup & Start

### 1. Services starten
```bash
# Verwende die verbesserte Konfiguration
docker-compose -f docker-compose-improved.yml up -d

# Logs anschauen
docker-compose -f docker-compose-improved.yml logs -f envoy

# Health Check
curl http://localhost:9901/ready
```

### 2. Services testen
```bash
# Executable machen
chmod +x test_all_routing.sh

# Alle Tests ausführen
./test_all_routing.sh
```

## Test-Szenarien

### Header-based Routing
```bash
# Test 1: API Version v2
curl -H "X-API-Version: v2" http://localhost:8080/api/test

# Test 2: Mobile User-Agent
curl -H "User-Agent: Mozilla/5.0 (Mobile; Android)" http://localhost:8080/api/test

# Test 3: Beta Features
curl -H "X-Beta-Features: enabled" http://localhost:8080/api/test
```

### Query Parameter Routing
```bash
# Test 4: Version parameter
curl http://localhost:8080/api/test?version=2

# Test 5: Beta flag
curl http://localhost:8080/api/test?beta=true

# Test 6: Admin access
curl http://localhost:8080/api/test?admin
```

### JWT-based Routing
```bash
# Test 7: JWT mit role=admin claim
# Zuerst einen JWT Token generieren (siehe tools/keygen/)
JWT_TOKEN="eyJhbGc..."
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8080/api/admin/test

# Response enthält JWT-Claim-Header:
# X-JWT-Role: admin
# X-JWT-Subject: test-user
```

### GeoIP-based Routing
```bash
# Test 8: Deutsche IP → EU Backend
curl -H "X-Forwarded-For: 192.168.1.1" http://localhost:8080/api/eu/test

# Response enthält GeoIP-Header:
# X-Geo-Country: DE
# X-Geo-IP: 192.168.1.1
```

### Default Fallback
```bash
# Test 9: Keine Routing-Regel matcht
curl http://localhost:8080/api/test
# → backend-v1
```

## Envoy Admin API

```bash
# Stats
curl http://localhost:9901/stats

# Config Dump
curl http://localhost:9901/config_dump | jq

# Ready Check
curl http://localhost:9901/ready

# Cluster Status
curl http://localhost:9901/clusters

# Runtime Info
curl http://localhost:9901/runtime
```

## Debugging

### 1. Envoy Logs
```bash
docker logs envoy-advanced-routing -f
```

### 2. Backend Logs
```bash
docker logs backend-v2 -f
docker logs backend-admin -f
```

### 3. JWKS Service Logs
```bash
docker logs jwks-service -f
```

### 4. GeoIP Service Logs
```bash
docker logs geoip-service -f
```

### 5. Response Headers analysieren
```bash
# Mit verbose output
curl -v http://localhost:8080/api/test

# Nur Headers
curl -I http://localhost:8080/api/test

# Wichtige Debug-Header:
# - X-Routing-Rule: Welche Routing-Regel wurde verwendet
# - X-JWT-Role: JWT Claim "role"
# - X-JWT-Subject: JWT Claim "sub"
# - X-Geo-Country: GeoIP Country Code
# - X-Geo-IP: Client IP Address
```

## Erweiterte Features

### Lua Filter
Der Lua Filter (`envoy.filters.http.lua`) extrahiert JWT Claims und GeoIP Metadata:

```lua
function envoy_on_request(request_handle)
  -- JWT Claims extrahieren
  local metadata = request_handle:metadata()
  if metadata["jwt_payload"]["role"] ~= nil then
    request_handle:headers():add("X-JWT-Role", metadata["jwt_payload"]["role"])
  end

  -- GeoIP Metadata extrahieren
  local geo = metadata["envoy.filters.http.ext_authz"]
  if geo["country"] ~= nil then
    request_handle:headers():add("X-Geo-Country", geo["country"])
  end
end
```

### JWT Validation Flow
1. Client sendet Request mit `Authorization: Bearer <token>`
2. Envoy `jwt_authn` Filter validiert Token gegen JWKS
3. JWT Payload wird in Metadata gespeichert: `jwt_payload`
4. Lua Filter extrahiert Claims und fügt sie als Header hinzu
5. Router kann basierend auf JWT Metadata routen

### GeoIP Lookup Flow
1. Client sendet Request mit `X-Forwarded-For` Header
2. Envoy `ext_authz` Filter ruft GeoIP gRPC Service auf
3. GeoIP Service liefert Country Code zurück
4. Envoy speichert Country Code in Metadata: `envoy.filters.http.ext_authz.country`
5. Router kann basierend auf Country Code routen

## JWT Token Generator

```bash
# JWT Token mit role=admin generieren
cd tools/keygen
docker build -t jwt-keygen .
docker run -v $(pwd)/keys:/app jwt-keygen

# Token verwenden
JWT=$(cat keys/test_token.jwt)
curl -H "Authorization: Bearer $JWT" http://localhost:8080/api/admin/test
```

## Performance

Benchmark mit 1000 Requests:
```bash
# Apache Bench
ab -n 1000 -c 10 http://localhost:8080/api/test

# wrk (wenn installiert)
wrk -t4 -c100 -d30s http://localhost:8080/api/test

# Eigener Benchmark
time for i in {1..1000}; do curl -s http://localhost:8080/api/test > /dev/null; done
```

## Cleanup

```bash
# Services stoppen
docker-compose -f docker-compose-improved.yml down

# Mit Volumes löschen
docker-compose -f docker-compose-improved.yml down -v

# Images löschen
docker-compose -f docker-compose-improved.yml down --rmi all
```

## Nächste Schritte

1. **Traffic Splitting** (Feature 5) hinzufügen:
   - Weighted Routing (90/10, 50/50)
   - Canary Deployments

2. **Request Mirroring** (Feature 6) hinzufügen:
   - Shadow Traffic zu Test-Backends

3. **Circuit Breaker** erweitern:
   - Outlier Detection
   - Retry Policies

4. **Rate Limiting** hinzufügen:
   - Global Rate Limits
   - Per-User Rate Limits

## Siehe auch

- [Envoy Documentation](https://www.envoyproxy.io/docs/envoy/latest/)
- [Envoy JWT Authn](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/jwt_authn_filter)
- [Envoy Ext Authz](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_authz_filter)
- [Envoy Lua Filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/lua_filter)
