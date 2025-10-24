# Provider Test Setups

Docker Compose Setups für alle unterstützten API Gateway Provider.

## 📁 Struktur

```
providers/
├── envoy/              # Envoy Proxy
├── nginx/              # NGINX (mit OpenResty)
├── kong/               # Kong Gateway
├── apisix/             # Apache APISIX
├── traefik/            # Traefik
└── haproxy/            # HAProxy
```

## 🎯 Features pro Provider

| Provider | Basic | Mirroring | Advanced Routing | Status |
|----------|-------|-----------|------------------|--------|
| Envoy    | ✅    | ✅        | ✅               | Vollständig |
| Nginx    | ✅    | ✅        | 🚧               | In Arbeit |
| Kong     | ✅    | ✅        | 🚧               | In Arbeit |
| APISIX   | ✅    | ✅        | 🚧               | In Arbeit |
| Traefik  | ✅    | ✅        | 🚧               | In Arbeit |
| HAProxy  | ✅    | ✅ (SPOE) | 🚧               | In Arbeit |

## 📋 Standard-Features

Jeder Provider unterstützt mindestens:

### Basic
- HTTP/HTTPS Proxy
- Load Balancing
- Health Checks
- Basic Authentication (optional)

### Mirroring
- Request Shadowing/Mirroring
- Percentage-based Sampling
- Fire-and-forget Pattern

### Advanced Routing
- Header-basiertes Routing
- Query-Parameter Routing
- Path-basiertes Routing
- Fallback/Default Routing

## 🐳 Docker Setup

### Gemeinsame Komponenten

**Backends** (`../backends/`):
- `advanced_backend.py` - Multi-purpose Backend für Routing Tests
- `primary.py` - Primary Backend für Mirroring
- `shadow.py` - Shadow Backend für Mirroring
- `stable.py` / `canary.py` - Für Traffic Split Tests

### Port-Konventionen

| Service | Port Range | Beispiel |
|---------|------------|----------|
| Gateway | 8080-8089  | 8080 |
| Admin   | 9900-9910  | 9901 (Envoy) |
| Backends | 8090-8099 | 8090, 8091 |

## 🧪 E2E Tests

### Test-Struktur
```
tests/e2e/
├── mirroring/          # Mirroring Tests für alle Provider
├── advanced_routing/   # Routing Tests
└── runtime/           # Basic Runtime Tests
```

### Tests ausführen

```bash
# Alle Tests eines Providers
pytest tests/e2e/ -m envoy

# Spezifisches Feature
pytest tests/e2e/mirroring/ -k nginx

# Mit Docker Logs
pytest tests/e2e/advanced_routing/ -v -s
```

## 📊 Provider-Vergleich

### Performance

| Provider | Latency (P50) | Throughput | Memory |
|----------|---------------|------------|---------|
| Envoy    | < 5ms        | High       | Medium  |
| Nginx    | < 3ms        | Very High  | Low     |
| Kong     | < 10ms       | Medium     | High    |
| APISIX   | < 7ms        | High       | Medium  |
| Traefik  | < 8ms        | Medium     | Medium  |
| HAProxy  | < 2ms        | Very High  | Low     |

### Komplexität

| Provider | Setup | Config | Debugging |
|----------|-------|--------|-----------|
| Envoy    | Medium| Medium | Easy      |
| Nginx    | Easy  | Easy   | Medium    |
| Kong     | Medium| Easy   | Easy      |
| APISIX   | Medium| Medium | Easy      |
| Traefik  | Easy  | Easy   | Easy      |
| HAProxy  | Easy  | Medium | Hard      |

## 🔧 Neue Features hinzufügen

1. **Verzeichnis erstellen**:
   ```bash
   mkdir -p providers/[provider]/[feature]
   ```

2. **Docker Compose erstellen**:
   - `docker-compose.yml`
   - `gal-config.yaml`
   - Provider-spezifische Config

3. **E2E Test schreiben**:
   - Nutze `BaseE2ETest`
   - Implementiere health checks
   - Füge pytest markers hinzu

4. **Dokumentation**:
   - README im Feature-Ordner
   - Update Provider README

## 🐛 Debugging

### Allgemeine Tipps

1. **Container Status**:
   ```bash
   docker-compose ps
   ```

2. **Logs**:
   ```bash
   docker-compose logs -f [service]
   ```

3. **Netzwerk**:
   ```bash
   docker network inspect [network]
   ```

4. **Shell Access**:
   ```bash
   docker-compose exec [service] sh
   ```

### Provider-spezifisch

- **Envoy**: Admin Interface auf Port 9901
- **Kong**: Admin API auf Port 8001
- **APISIX**: Admin API auf Port 9080
- **Traefik**: Dashboard auf Port 8080

## 📚 Dokumentation

- [E2E Test Best Practices](../../E2E_TEST_BEST_PRACTICES.md)
- [BaseE2ETest Usage](../../base.py)
- Provider-spezifische READMEs in jeweiligen Ordnern