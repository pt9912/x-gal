# GAL Test Suite

Umfassende Test-Suite für das Gateway Abstraction Layer (GAL) Projekt.

## 📁 Struktur

```
tests/
├── unit/                       # Unit-Tests (schnell, keine externen Abhängigkeiten)
│   ├── config/                 # Config & Feature Tests
│   ├── providers/              # Provider-spezifische Tests
│   ├── import/                 # Import-Funktionalität
│   ├── cli/                    # CLI Tests
│   └── misc/                   # Sonstige Tests
│
├── e2e/                        # End-to-End Tests (Docker-basiert)
│   ├── base.py                 # BaseE2ETest Klasse
│   ├── conftest.py             # Gemeinsame pytest fixtures
│   ├── mirroring/              # Request Mirroring Tests
│   ├── advanced_routing/       # Advanced Routing Tests
│   ├── runtime/                # Runtime Tests
│   └── docker/                 # Docker Compose Setups
│
├── pytest.ini                  # pytest Konfiguration
├── E2E_TEST_BEST_PRACTICES.md # Best Practices Dokumentation
└── README.md                   # Diese Datei
```

## 🚀 Test-Ausführung

### Alle Tests ausführen
```bash
# Aktiviere Virtual Environment
source /Development/x-gal/.venv/bin/activate

# Alle Tests
pytest

# Mit Coverage
pytest --cov=gal --cov-report=html
```

### Unit-Tests
```bash
# Alle Unit-Tests
pytest tests/unit/

# Spezifische Kategorie
pytest tests/unit/config/
pytest tests/unit/providers/

# Schnelle Tests nur
pytest tests/unit/ -m "not slow"
```

### E2E-Tests
```bash
# Alle E2E-Tests (benötigt Docker)
pytest tests/e2e/

# Spezifisches Feature
pytest tests/e2e/mirroring/
pytest tests/e2e/advanced_routing/

# Spezifischer Provider
pytest tests/e2e/ -m "provider(envoy)"
pytest tests/e2e/ -m "envoy"

# Ohne langsame Tests
pytest tests/e2e/ -m "not slow"
```

### Parallel Execution
```bash
# Unit-Tests parallel (schneller)
pytest tests/unit/ -n auto

# E2E-Tests (Vorsicht: Docker-Ressourcen!)
pytest tests/e2e/ -n 2
```

## 🏷️ Test Markers

### Speed Markers
- `@pytest.mark.slow` - Langsame Tests (> 5 Sekunden)
- `@pytest.mark.fast` - Schnelle Tests (< 1 Sekunde)

### Environment Markers
- `@pytest.mark.docker` - Benötigt Docker/Docker-Compose
- `@pytest.mark.integration` - Integration Tests

### Feature Markers
- `@pytest.mark.mirroring` - Request Mirroring
- `@pytest.mark.routing` - Advanced Routing
- `@pytest.mark.authentication` - Authentication
- `@pytest.mark.ratelimit` - Rate Limiting
- `@pytest.mark.circuitbreaker` - Circuit Breaker
- `@pytest.mark.cors` - CORS
- `@pytest.mark.grpc` - gRPC

### Provider Markers
- `@pytest.mark.envoy` - Envoy-spezifisch
- `@pytest.mark.nginx` - Nginx-spezifisch
- `@pytest.mark.kong` - Kong-spezifisch
- `@pytest.mark.apisix` - APISIX-spezifisch
- `@pytest.mark.traefik` - Traefik-spezifisch
- `@pytest.mark.haproxy` - HAProxy-spezifisch
- `@pytest.mark.aws` - AWS API Gateway
- `@pytest.mark.azure` - Azure API Management
- `@pytest.mark.gcp` - GCP API Gateway

## 📊 Test Coverage

```bash
# Coverage Report generieren
pytest --cov=gal --cov-report=html --cov-report=term

# HTML Report öffnen
open htmlcov/index.html
```

## 🐳 E2E Test Requirements

### Docker Setup
```bash
# Docker installieren
sudo apt-get update
sudo apt-get install docker.io docker-compose

# User zu docker Gruppe hinzufügen
sudo usermod -aG docker $USER

# Logout/Login oder
newgrp docker
```

### E2E Test Lifecycle

1. **Setup**: Docker Compose Environment starten
2. **Health Check**: Warten bis alle Services bereit sind
3. **Test Execution**: Tests ausführen
4. **Teardown**: Logs speichern und Container stoppen

## 🔧 BaseE2ETest Verwendung

```python
from e2e.base import BaseE2ETest
import pytest

@pytest.mark.docker
@pytest.mark.routing
class TestMyFeature(BaseE2ETest):
    # Konfiguration
    COMPOSE_FILE = "docker-compose.yml"
    SERVICE_PORT = 8080
    HEALTH_ENDPOINT = "/health"
    ADMIN_PORT = 9901  # Optional

    @classmethod
    def _get_test_dir(cls):
        """Override für custom Docker-Compose Pfad."""
        return "path/to/compose/dir"

    def test_feature(self):
        """Test implementation."""
        response = self.make_request("/api")
        self.assert_response(response, 200)
```

## 🧪 Test-Beispiele

### Unit-Test
```python
# tests/unit/config/test_advanced_routing.py
import pytest
from gal.config import Config

def test_routing_config():
    config = Config.from_yaml("test.yaml")
    assert config.services[0].routes[0].advanced_routing.enabled
```

### E2E-Test
```python
# tests/e2e/advanced_routing/test_envoy_advanced_routing.py
from e2e.base import BaseE2ETest

class TestEnvoyRouting(BaseE2ETest):
    def test_header_routing(self):
        response = self.make_request(
            "/api",
            headers={"X-API-Version": "v2"}
        )
        assert response.json()["backend"]["name"] == "backend-v2"
```

## 📝 Best Practices

Siehe [E2E_TEST_BEST_PRACTICES.md](./E2E_TEST_BEST_PRACTICES.md) für:
- Health Check Patterns
- Log Analysis
- Test Isolation
- Performance Testing
- Error Handling

## 🐛 Debugging

### E2E Test Logs
```bash
# Logs werden automatisch gespeichert bei Fehler
ls test_logs_*.txt

# Docker Logs manuell anschauen
cd tests/e2e/docker/advanced-routing/envoy-routing
docker-compose logs -f
```

### Einzelnen Test debuggen
```bash
# Mit verbose output
pytest tests/e2e/advanced_routing/test_envoy_advanced_routing.py::TestEnvoyAdvancedRouting::test_header_routing -v -s

# Mit pdb
pytest tests/e2e/advanced_routing/test_envoy_advanced_routing.py --pdb
```

## 🔄 CI/CD Integration

### GitHub Actions
```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov
      - name: Run unit tests
        run: pytest tests/unit/ --cov=gal

  e2e-tests:
    runs-on: ubuntu-latest
    services:
      docker:
        image: docker:dind
    steps:
      - uses: actions/checkout@v2
      - name: Run E2E tests
        run: pytest tests/e2e/ -m "not slow"
```

## 📈 Performance Benchmarks

```bash
# Performance Tests ausführen
pytest tests/e2e/ -m "slow" -v

# Latency Baseline erstellen
pytest tests/e2e/advanced_routing/ -k "performance"
```

## 🤝 Contributing

1. Neue Tests gehören in die passende Kategorie (unit/e2e)
2. E2E Tests sollten BaseE2ETest verwenden
3. Passende Markers verwenden
4. Tests sollten isoliert und wiederholbar sein
5. Cleanup im Teardown sicherstellen

## 📚 Weitere Dokumentation

- [GAL Dokumentation](../docs/)
- [E2E Test Best Practices](./E2E_TEST_BEST_PRACTICES.md)
- [Provider Guides](../docs/guides/)