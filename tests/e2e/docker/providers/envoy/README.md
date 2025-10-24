# Envoy Provider Test Setups

Docker Compose Setups für Envoy-basierte E2E Tests.

**Hinweis:** Verwendet `docker compose` (V2 Plugin) statt legacy `docker-compose`.

## 📁 Struktur

```
envoy/
├── basic/               # Grundlegende Envoy-Funktionalität
├── mirroring/          # Request Mirroring/Shadowing
├── advanced-routing/   # Header/Query-basiertes Routing
└── README.md
```

## 🚀 Features

### Basic
- Grundlegende Proxy-Funktionalität
- Health Checks
- Load Balancing

### Mirroring
- Request Shadowing zu Secondary Cluster
- Fire-and-forget Pattern
- Envoy Shadow Policy Konfiguration

### Advanced Routing
- Header-basiertes Routing (exact, prefix, contains, regex)
- Query-Parameter Routing
- Fallback Routing
- Multi-Backend Setup mit 6 verschiedenen Backends

## 🧪 Tests ausführen

```bash
# Aktiviere Virtual Environment
source /Development/x-gal/.venv/bin/activate

# Basic Tests
pytest tests/e2e/runtime/test_docker_runtime.py -k envoy

# Mirroring Tests
pytest tests/e2e/mirroring/test_envoy_mirroring_e2e.py -v

# Advanced Routing Tests
pytest tests/e2e/advanced_routing/test_envoy_advanced_routing.py -v
```

## 📝 Konfiguration

### envoy.yaml
Generiert durch GAL aus `gal-config.yaml`:
```bash
python -m gal generate -c gal-config.yaml -p envoy -o envoy.yaml
```

### Docker Compose
- Port 8080: Envoy Gateway
- Port 9901: Envoy Admin Interface
- Backends auf verschiedenen Ports

## 🔍 Debugging

### Admin Interface
```bash
# Cluster Status
curl http://localhost:9901/clusters

# Routes
curl http://localhost:9901/config_dump

# Stats
curl http://localhost:9901/stats
```

### Logs
```bash
cd tests/e2e/docker/providers/envoy/[feature]/
docker compose logs -f envoy
```

## 📊 Metriken

Envoy exportiert Prometheus-kompatible Metriken:
```bash
curl http://localhost:9901/stats/prometheus
```

## 🔗 Links

- [Envoy Documentation](https://www.envoyproxy.io/docs/envoy/latest/)
- [GAL Envoy Provider](../../../../../gal/providers/envoy.py)