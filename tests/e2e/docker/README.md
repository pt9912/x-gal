# Docker E2E Test Setups

Docker Compose Setups für End-to-End Tests aller GAL Features und Provider.

## 📁 Struktur

```
docker/
├── backends/               # Gemeinsame Backend-Services für alle Tests
│   ├── advanced_backend.py # Multi-purpose Backend (Routing Tests)
│   ├── primary.py          # Primary Backend (Mirroring Tests)
│   ├── shadow.py           # Shadow Backend (Mirroring Tests)
│   ├── stable.py           # Stable Backend (Traffic Split)
│   ├── canary.py           # Canary Backend (Traffic Split)
│   └── Dockerfile
│
└── providers/              # Provider → Feature Organisation
    ├── envoy/
    │   ├── basic/          # Grundfunktionalität
    │   ├── mirroring/      # Request Mirroring/Shadowing
    │   └── advanced-routing/ # Header/Query-basiertes Routing
    │
    ├── nginx/
    │   ├── basic/
    │   ├── mirroring/
    │   └── advanced-routing/ # (Bereit für Implementation)
    │
    ├── kong/
    │   ├── basic/
    │   ├── mirroring/
    │   └── advanced-routing/ # (Bereit für Implementation)
    │
    ├── apisix/
    │   ├── basic/
    │   ├── mirroring/
    │   └── advanced-routing/ # (Bereit für Implementation)
    │
    ├── traefik/
    │   ├── basic/
    │   ├── mirroring/
    │   └── advanced-routing/ # (Bereit für Implementation)
    │
    └── haproxy/
        ├── basic/
        ├── mirroring/
        ├── mirroring-spoe/  # Spezielle SPOE Implementation
        └── advanced-routing/ # (Bereit für Implementation)
```

## 🎯 Features

### Basic
- HTTP/HTTPS Proxy
- Load Balancing
- Health Checks
- Basic Authentication

### Request Mirroring
- Traffic Shadowing (fire-and-forget)
- Percentage-based Sampling
- Async Mirroring ohne Client-Impact
- Request Body Mirroring

### Advanced Routing
- Header-basiertes Routing (exact, prefix, contains, regex)
- Query-Parameter Routing (exact, exists, regex)
- JWT Claims-basiertes Routing (mit Extensions)
- Geo-basiertes Routing (mit GeoIP)
- Fallback/Default Routing

### Traffic Splitting
- Gewichtsbasierte Verteilung (90/10, 70/30, etc.)
- Canary Deployments
- Blue/Green Deployments
- A/B Testing

## 📊 Provider Feature Matrix

| Provider | Basic | Mirroring | Advanced Routing | Traffic Split | Status |
|----------|-------|-----------|------------------|---------------|--------|
| **Envoy**    | ✅ | ✅ | ✅ | ✅ | Vollständig |
| **Nginx**    | ✅ | ✅ | 🚧 | ✅ | In Arbeit |
| **Kong**     | ✅ | ✅ | 🚧 | ✅ | In Arbeit |
| **APISIX**   | ✅ | ✅ | 🚧 | ✅ | In Arbeit |
| **Traefik**  | ✅ | ✅ | 🚧 | ✅ | In Arbeit |
| **HAProxy**  | ✅ | ✅ (SPOE) | 🚧 | ✅ | In Arbeit |

## 🐳 Docker Setup

### Port-Konventionen

| Service | Port Range | Beispiele |
|---------|------------|-----------|
| Gateway | 8080-8089  | 8080 (Default) |
| Admin   | 9900-9910  | 9901 (Envoy), 8001 (Kong) |
| Backends | 8090-8099 | 8090, 8091 |
| Metrics | 9090-9099  | 9090 (Prometheus) |

### Gemeinsame Backend-Services

Die Backend-Services in `backends/` werden von allen Tests verwendet:

- **advanced_backend.py**: Identifiziert sich basierend auf Environment-Variablen
  - Für Advanced Routing Tests
  - Unterstützt: BACKEND_NAME, BACKEND_VERSION, BACKEND_TYPE, BACKEND_REGION

- **primary.py / shadow.py**: Für Mirroring Tests
  - Primary: Hauptbackend, dessen Response zurückgegeben wird
  - Shadow: Empfängt gespiegelte Requests (fire-and-forget)

- **stable.py / canary.py**: Für Traffic Split Tests
  - Stable: Produktionsversion
  - Canary: Neue Version für schrittweises Rollout

## 🧪 E2E Tests ausführen

### Verzeichnisstruktur der Tests

```
tests/e2e/
├── base.py                 # BaseE2ETest Klasse
├── conftest.py             # Gemeinsame pytest fixtures
├── mirroring/              # Mirroring Tests für alle Provider
│   ├── test_envoy_mirroring_e2e.py
│   ├── test_nginx_mirroring_e2e.py
│   └── ...
├── advanced_routing/       # Routing Tests
│   └── test_envoy_advanced_routing.py
└── runtime/               # Basic Runtime Tests
    └── test_docker_runtime.py
```

### Tests ausführen

```bash
# Aktiviere Virtual Environment
source /Development/x-gal/.venv/bin/activate

# Alle E2E Tests
pytest tests/e2e/ -v -s

# Provider-spezifisch
pytest tests/e2e/ -m envoy
pytest tests/e2e/ -m nginx

# Feature-spezifisch
pytest tests/e2e/mirroring/ -v
pytest tests/e2e/advanced_routing/ -v

# Einzelner Test
pytest tests/e2e/advanced_routing/test_envoy_advanced_routing.py -v -s
```

### Manuelles Testing

```bash
# Envoy Advanced Routing
cd tests/e2e/docker/providers/envoy/advanced-routing
docker-compose up -d --build

# Test verschiedene Routing-Szenarien
curl http://localhost:8080/api                           # → backend-v1 (default)
curl -H "X-API-Version: v2" http://localhost:8080/api   # → backend-v2
curl -H "User-Agent: Mobile" http://localhost:8080/api  # → backend-mobile

# Admin Interface
curl http://localhost:9901/clusters
curl http://localhost:9901/stats

# Cleanup
docker-compose down -v
```

## 🔍 Debugging

### Container Status
```bash
docker-compose ps
docker-compose logs -f [service]
```

### Provider Admin Interfaces

| Provider | Admin URL | Features |
|----------|-----------|----------|
| Envoy | http://localhost:9901 | /clusters, /stats, /config_dump |
| Kong | http://localhost:8001 | /status, /routes, /services |
| APISIX | http://localhost:9080 | /apisix/admin |
| Traefik | http://localhost:8080 | Dashboard |
| HAProxy | http://localhost:8404 | /stats |

### Log Analysis

Die E2E Tests speichern automatisch Logs bei Fehlern:
```bash
# Gespeicherte Logs finden
ls test_logs_*.txt

# Live Logs anschauen
docker-compose logs -f [service]
```

## 📈 Performance Benchmarks

### Latency Targets

| Provider | P50 | P95 | P99 | Memory |
|----------|-----|-----|-----|---------|
| Envoy    | <5ms | <10ms | <15ms | ~50MB |
| Nginx    | <3ms | <7ms | <10ms | ~20MB |
| Kong     | <10ms | <20ms | <30ms | ~100MB |
| APISIX   | <7ms | <15ms | <20ms | ~80MB |
| Traefik  | <8ms | <15ms | <25ms | ~60MB |
| HAProxy  | <2ms | <5ms | <8ms | ~15MB |

## 🚀 Neue Features hinzufügen

### 1. Provider/Feature Ordner erstellen
```bash
mkdir -p providers/[provider]/[feature]
```

### 2. Docker Compose Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  gateway:
    image: [provider-image]
    volumes:
      - ./config.yaml:/config.yaml
    ports:
      - "8080:8080"
    networks:
      - test-network

  backend:
    build:
      context: ../../../backends
    environment:
      - BACKEND_NAME=backend-v1
    networks:
      - test-network

networks:
  test-network:
    driver: bridge
```

### 3. E2E Test schreiben
```python
from e2e.base import BaseE2ETest

class TestProviderFeature(BaseE2ETest):
    COMPOSE_FILE = "docker-compose.yml"
    SERVICE_PORT = 8080

    @classmethod
    def _get_test_dir(cls):
        return str(
            Path(__file__).parent.parent / "docker" / "providers" / "[provider]" / "[feature]"
        )

    def test_feature(self):
        response = self.make_request("/api")
        self.assert_response(response, 200)
```

## 📚 Dokumentation

### Provider-spezifisch
- [Envoy README](providers/envoy/README.md)
- [Providers Overview](providers/README.md)

### Test-Framework
- [E2E Test Best Practices](../E2E_TEST_BEST_PRACTICES.md)
- [BaseE2ETest Documentation](../base.py)
- [Test Suite README](../../README.md)

## 🐛 Troubleshooting

### Port bereits belegt
```bash
# Prüfen welcher Prozess den Port nutzt
lsof -i :8080

# Alle Test-Container stoppen
docker ps -q | xargs docker stop
```

### Health Checks fehlgeschlagen
```bash
# Container-Status prüfen
docker-compose ps

# Logs des problematischen Services
docker-compose logs [service]

# Manueller Health Check
docker exec [container] curl http://localhost:8080/health
```

### Test-Isolation Probleme
- Nutze timestamp-basierte Log-Filterung
- Verwende eindeutige Request-IDs
- Stelle sicher, dass `docker-compose down -v` ausgeführt wird

## 🔄 CI/CD Integration

### GitHub Actions Beispiel
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        provider: [envoy, nginx, kong]

    steps:
      - uses: actions/checkout@v2

      - name: Run E2E Tests
        run: |
          pytest tests/e2e/ -m ${{ matrix.provider }} -v

      - name: Upload Logs
        if: failure()
        uses: actions/upload-artifact@v2
        with:
          name: test-logs-${{ matrix.provider }}
          path: test_logs_*.txt
```

## 📝 Best Practices

1. **Immer BaseE2ETest verwenden** für konsistentes Setup/Teardown
2. **Health Checks** in Docker Compose definieren
3. **Isolierte Netzwerke** pro Test verwenden
4. **Logs speichern** bei Test-Fehlern
5. **Timestamp-basierte Log-Filterung** für Test-Isolation
6. **Progress Indicators** für lange Tests
7. **Cleanup mit `-v`** für Volume-Bereinigung

## 🚧 TODOs

- [ ] Advanced Routing für weitere Provider implementieren
- [ ] GraphQL Support Tests
- [ ] WebSocket Tests
- [ ] gRPC Tests
- [ ] Performance Baseline Tests
- [ ] Chaos Engineering Tests

---

**Entwickelt für das GAL-Projekt** | [GitHub](https://github.com/pt9912/x-gal)