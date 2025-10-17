# GAL Entwickler-Guide

## Übersicht

Dieser Guide hilft Entwicklern beim Einstieg in die GAL-Codebasis, erklärt die Entwicklungsumgebung und Best Practices für Contributions.

## Entwicklungsumgebung Setup

### Voraussetzungen

- Python 3.8 oder höher
- Git
- Docker (optional, für Container-basierte Entwicklung)
- Ein Code-Editor (VS Code, PyCharm, etc.)

### Lokales Setup

```bash
# Repository klonen
git clone https://github.com/pt9912/x-gal.git
cd x-gal

# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Development-Abhängigkeiten installieren
pip install pytest pytest-cov black flake8 mypy

# Paket im Development-Modus installieren
pip install -e .
```

### Entwicklung mit Docker

```bash
# Image bauen
docker build -t gal:dev .

# Interaktive Shell
docker run -it --rm -v $(pwd):/app -w /app gal:dev sh

# Tests ausführen
docker run --rm -v $(pwd):/app -w /app gal:dev pytest
```

## Projektstruktur

```
x-gal/
├── gal/                        # Hauptpaket
│   ├── __init__.py
│   ├── config.py              # Konfigurationsmodelle
│   ├── manager.py             # Manager-Orchestration
│   ├── provider.py            # Provider ABC
│   ├── providers/             # Provider-Implementierungen
│   │   ├── __init__.py
│   │   ├── envoy.py
│   │   ├── kong.py
│   │   ├── apisix.py
│   │   └── traefik.py
│   └── transformation/        # Transformation-Engine (geplant)
│       ├── __init__.py
│       ├── engine.py
│       └── generators.py
├── tests/                     # Test-Suite
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_manager.py
│   └── test_providers.py
├── examples/                  # Beispiel-Konfigurationen
│   ├── gateway-config.yaml
│   └── output/
├── docs/                      # Dokumentation
│   ├── api/
│   ├── architecture/
│   └── guides/
├── gal-cli.py                 # CLI Entry-Point
├── setup.py                   # Package-Setup
├── requirements.txt           # Produktions-Dependencies
├── Dockerfile                 # Docker-Konfiguration
├── docker-compose.yml         # Docker Compose Services
└── README.md                  # Haupt-Readme

```

## Code-Organisation

### 1. config.py - Konfigurationsmodelle

**Verantwortlichkeit:** Definition aller Datenmodelle

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Service:
    name: str
    type: str  # grpc oder rest
    protocol: str
    upstream: Upstream
    routes: List[Route]
    transformation: Optional[Transformation] = None
```

**Best Practices:**
- Verwende `@dataclass` für alle Modelle
- Nutze Type Hints konsequent
- Optional-Felder mit `Optional[Type] = None`
- Nutze `field(default_factory=list)` für mutable defaults

### 2. manager.py - Orchestration

**Verantwortlichkeit:** Provider-Management und Workflow-Koordination

```python
class Manager:
    def __init__(self):
        self.providers: Dict[str, Provider] = {}

    def register_provider(self, provider: Provider):
        """Register a gateway provider"""
        self.providers[provider.name()] = provider
```

**Best Practices:**
- Manager kennt keine Provider-Details
- Nutze Registry Pattern für Provider
- Validierung vor Generation
- Aussagekräftige Error Messages

### 3. provider.py - Provider Interface

**Verantwortlichkeit:** ABC für alle Provider

```python
from abc import ABC, abstractmethod

class Provider(ABC):
    @abstractmethod
    def name(self) -> str:
        """Return provider name"""
        pass

    @abstractmethod
    def validate(self, config: Config) -> bool:
        """Validate configuration for this provider"""
        pass

    @abstractmethod
    def generate(self, config: Config) -> str:
        """Generate provider-specific configuration"""
        pass
```

**Best Practices:**
- Minimales Interface (nur notwendige Methoden)
- `deploy()` ist optional
- Klare Dokumentation der Erwartungen
- Konsistente Rückgabewerte

### 4. Provider-Implementierungen

**Struktur einer Provider-Implementierung:**

```python
class NewProvider(Provider):
    def name(self) -> str:
        return "newprovider"

    def validate(self, config: Config) -> bool:
        # Provider-spezifische Validierung
        if not config.services:
            raise ValueError("No services defined")
        return True

    def generate(self, config: Config) -> str:
        output = []
        output.append("# Configuration Header")

        # Service-Generierung
        for service in config.services:
            output.append(f"service: {service.name}")
            # ... weitere Logik

        return "\n".join(output)
```

**Best Practices:**
- Nutze `output = []` für Zeilen-basierte Generierung
- Validiere Input gründlich
- Provider-spezifische Kommentare
- Nutze Templates für wiederkehrende Strukturen
- Teste mit verschiedenen Service-Typen

## Entwicklungsworkflow

### Branch-Strategie

```bash
# Feature-Branch erstellen
git checkout -b feature/neue-funktion

# Entwickeln und testen
# ... Code ändern ...
pytest

# Commit mit aussagekräftiger Message
git add .
git commit -m "Add neue Funktion mit X, Y, Z"

# Push und Pull Request
git push origin feature/neue-funktion
```

### Commit-Konventionen

Folge dem Conventional Commits Standard:

```
type(scope): kurze Beschreibung

Längere Beschreibung mit Details

- Bullet points für Änderungen
- Weitere Details
```

**Types:**
- `feat:` Neue Features
- `fix:` Bugfixes
- `docs:` Dokumentation
- `test:` Tests
- `refactor:` Refactoring
- `chore:` Build, Dependencies, etc.

**Beispiele:**

```
feat(providers): Add support for Traefik provider

- Implement TraefikProvider class
- Add router and service generation
- Include middleware support for transformations

Closes #42
```

```
fix(config): Handle missing transformation validation

Previously, configurations without validation would cause
NoneType errors. Now defaults to empty validation.

Fixes #15
```

## Testing

### Test-Organisation

```
tests/
├── test_config.py          # Config-Modell Tests
├── test_manager.py         # Manager Tests
└── test_providers.py       # Alle Provider Tests
```

### Tests schreiben

**Unit Test Beispiel:**

```python
def test_config_loading():
    """Test loading configuration from YAML"""
    yaml_content = """
    version: "1.0"
    provider: test
    services:
      - name: test_service
        type: rest
        protocol: http
        upstream:
          host: test.local
          port: 8080
        routes:
          - path_prefix: /api
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_file = f.name

    try:
        config = Config.from_yaml(temp_file)
        assert config.version == "1.0"
        assert len(config.services) == 1
    finally:
        Path(temp_file).unlink()
```

**Mock Provider für Tests:**

```python
class MockProvider(Provider):
    def __init__(self, provider_name="mock", should_validate=True):
        self._name = provider_name
        self._should_validate = should_validate

    def name(self) -> str:
        return self._name

    def validate(self, config: Config) -> bool:
        return self._should_validate

    def generate(self, config: Config) -> str:
        return f"# Mock configuration for {self._name}"
```

### Tests ausführen

```bash
# Alle Tests
pytest

# Mit Coverage
pytest --cov=gal --cov-report=term-missing

# Spezifische Testdatei
pytest tests/test_config.py

# Spezifischer Test
pytest tests/test_config.py::test_config_loading

# Mit Verbose Output
pytest -v

# Tests parallel ausführen (mit pytest-xdist)
pytest -n auto
```

### Test Coverage Ziele

- **Minimum:** 80% Coverage
- **Ziel:** 95%+ Coverage
- **Aktuell:** 99% Coverage

## Code-Qualität

### Linting

```bash
# Flake8 (PEP 8)
flake8 gal/ tests/

# Black (Auto-Formatting)
black gal/ tests/

# MyPy (Type Checking)
mypy gal/
```

### Pre-Commit Hook

Erstelle `.git/hooks/pre-commit`:

```bash
#!/bin/bash
set -e

echo "Running tests..."
pytest

echo "Running linters..."
flake8 gal/ tests/
black --check gal/ tests/

echo "Running type checker..."
mypy gal/

echo "✓ All checks passed"
```

```bash
chmod +x .git/hooks/pre-commit
```

## Debugging

### Logging einrichten

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# In Code
logger.debug(f"Loading config from {filepath}")
logger.info(f"Registered provider: {provider.name()}")
logger.warning(f"Service {service.name} has no routes")
logger.error(f"Failed to generate: {e}")
```

### Debugging mit pdb

```python
# Breakpoint setzen
import pdb; pdb.set_trace()

# Oder mit Python 3.7+
breakpoint()
```

### Debugging im Docker Container

```bash
# Container mit bash starten
docker run -it --rm -v $(pwd):/app -w /app gal:dev bash

# Python interaktiv
python
>>> from gal.config import Config
>>> config = Config.from_yaml('examples/gateway-config.yaml')
>>> config.services[0].name
```

## Einen neuen Provider hinzufügen

### Schritt 1: Provider-Datei erstellen

```bash
touch gal/providers/newgateway.py
```

### Schritt 2: Provider implementieren

```python
# gal/providers/newgateway.py
from ..provider import Provider
from ..config import Config

class NewGatewayProvider(Provider):
    def name(self) -> str:
        return "newgateway"

    def validate(self, config: Config) -> bool:
        """Validate configuration for NewGateway"""
        # Spezifische Validierungen
        if not config.services:
            raise ValueError("At least one service required")
        return True

    def generate(self, config: Config) -> str:
        """Generate NewGateway configuration"""
        output = []

        # Header
        output.append("# NewGateway Configuration")
        output.append(f"version: {config.version}")
        output.append("")

        # Services
        output.append("services:")
        for service in config.services:
            output.append(f"  - name: {service.name}")
            output.append(f"    upstream: {service.upstream.host}:{service.upstream.port}")

            # Routes
            output.append("    routes:")
            for route in service.routes:
                output.append(f"      - {route.path_prefix}")

        return "\n".join(output)
```

### Schritt 3: Provider exportieren

```python
# gal/providers/__init__.py
from .envoy import EnvoyProvider
from .kong import KongProvider
from .apisix import APISIXProvider
from .traefik import TraefikProvider
from .newgateway import NewGatewayProvider  # Neu

__all__ = [
    'EnvoyProvider',
    'KongProvider',
    'APISIXProvider',
    'TraefikProvider',
    'NewGatewayProvider',  # Neu
]
```

### Schritt 4: In CLI registrieren

```python
# gal-cli.py
from gal.providers import (
    EnvoyProvider, KongProvider, APISIXProvider,
    TraefikProvider, NewGatewayProvider
)

# In allen CLI-Befehlen
manager.register_provider(NewGatewayProvider())
```

### Schritt 5: Tests schreiben

```python
# tests/test_providers.py
class TestNewGatewayProvider:
    """Test NewGateway provider"""

    def test_name(self):
        provider = NewGatewayProvider()
        assert provider.name() == "newgateway"

    def test_generate_basic_config(self):
        provider = NewGatewayProvider()
        config = self._create_basic_config()

        result = provider.generate(config)

        assert "# NewGateway Configuration" in result
        assert "services:" in result

    def _create_basic_config(self):
        # Helper method
        ...
```

### Schritt 6: Dokumentation

Füge den Provider zur Dokumentation hinzu:
- README.md
- docs/guides/PROVIDERS.md
- docs/api/CLI_REFERENCE.md

## Performance-Optimierung

### Profiling

```python
import cProfile
import pstats

# Profiling aktivieren
profiler = cProfile.Profile()
profiler.enable()

# Code ausführen
manager.generate(config)

# Profiling beenden
profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20
```

### Memory Profiling

```bash
# Mit memory_profiler
pip install memory_profiler

# Dekorator hinzufügen
from memory_profiler import profile

@profile
def generate(self, config):
    ...

# Ausführen
python -m memory_profiler gal-cli.py generate -c config.yaml
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: pytest --cov=gal --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Häufige Probleme

### Problem: Import-Fehler

```python
# Falsch
from gal.providers.envoy import EnvoyProvider

# Richtig
from gal.providers import EnvoyProvider
```

### Problem: Circular Imports

Vermeide zirkuläre Imports durch:
- Forward References mit Strings
- TYPE_CHECKING Import
- Refactoring

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config
```

## Ressourcen

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Type Hints (PEP 484)](https://www.python.org/dev/peps/pep-0484/)
- [Dataclasses Guide](https://docs.python.org/3/library/dataclasses.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## Contribution Checklist

Vor dem Pull Request:

- [ ] Tests geschrieben und alle bestehen
- [ ] Code-Coverage ≥ 95%
- [ ] Linting (flake8) ohne Fehler
- [ ] Type Checking (mypy) ohne Fehler
- [ ] Dokumentation aktualisiert
- [ ] CHANGELOG.md aktualisiert
- [ ] Commit Messages folgen Konventionen
- [ ] Branch ist rebased auf main

## Support

Bei Fragen:
- GitHub Issues: https://github.com/pt9912/x-gal/issues
- Discussions: https://github.com/pt9912/x-gal/discussions
