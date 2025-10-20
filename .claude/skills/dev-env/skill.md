---
name: dev-env
description: Richtet automatisch die lokale Python-Entwicklungsumgebung ein (venv, pytest, black, isort, flake8). Nutze diesen Skill bei pytest/python Fehlern oder "setup dev environment".
---

# Development Environment Setup Skill

## Zweck

Dieser Skill richtet automatisch die lokale Entwicklungsumgebung für x-gal ein, installiert alle Abhängigkeiten und ermöglicht das lokale Testen.

## Wann dieser Skill aufgerufen wird

Claude sollte diesen Skill **automatisch** verwenden in folgenden Situationen:

- Wenn pytest/python Befehle fehlschlagen wegen fehlender Module
- Wenn der Nutzer "setup dev environment" oder ähnliches sagt
- Vor dem lokalen Ausführen von Tests
- Nach einem frischen Clone des Repositories

## Anweisungen

### 1. Prüfe Python-Verfügbarkeit

Zuerst prüfe, welche Python-Versionen verfügbar sind:

```bash
# Prüfe verfügbare Python-Versionen
which python3 python3.10 python3.11 python3.12 2>/dev/null

# Prüfe Default-Version
python3 --version
```

**Erwartete Python-Versionen:** 3.10, 3.11 oder 3.12

### 2. Erstelle Virtual Environment

Falls noch nicht vorhanden, erstelle ein virtuelles Environment:

```bash
# Prüfe ob .venv bereits existiert
if [ -d ".venv" ]; then
    echo "✓ Virtual environment already exists"
else
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
```

### 3. Aktiviere Virtual Environment & Installiere Dependencies

Aktiviere das venv und installiere alle Abhängigkeiten:

```bash
# Aktiviere venv
source .venv/bin/activate

# Installiere Package in Development Mode
pip install -e .

# Installiere Dev-Dependencies
pip install pytest pytest-cov black isort flake8
```

**Dev-Dependencies:**
- `pytest` - Test Runner
- `pytest-cov` - Test Coverage
- `black` - Code Formatter
- `isort` - Import Sorter
- `flake8` - Linter

### 4. Verifiziere Installation

Prüfe, dass alles korrekt installiert wurde:

```bash
# Aktiviere venv
source .venv/bin/activate

# Prüfe pytest
pytest --version

# Prüfe GAL Installation
python -c "import gal; print(f'GAL version: {gal.__version__ if hasattr(gal, \"__version__\") else \"dev\"}')"

# Liste installierte Packages
pip list | grep -E "(gal-gateway|pytest|black|isort|flake8)"
```

**Erwartete Ausgabe:**
- pytest: 8.x.x
- pytest-cov: 7.x.x
- black: 24.x.x
- isort: 5.x.x
- flake8: 7.x.x
- gal-gateway: 1.3.0 (editable)

### 5. Führe Test-Suite aus (Optional)

Falls der Nutzer Tests ausführen möchte:

```bash
# Aktiviere venv
source .venv/bin/activate

# Führe alle Tests aus
pytest -v

# Oder nur spezifische Tests
pytest tests/test_import_azure_apim.py -v

# Mit Coverage
pytest --cov=gal --cov-report=term --cov-report=html
```

### 6. Code Quality Tools ausführen (Optional)

```bash
# Aktiviere venv
source .venv/bin/activate

# Black (Formatter)
black --check gal/ tests/

# isort (Import Sorter)
isort --check-only gal/ tests/

# flake8 (Linter)
flake8 gal/ tests/
```

## Status-Zusammenfassung

Nach erfolgreicher Installation, zeige:

```
✅ Development Environment Setup Complete

Python Version: 3.12.3
Virtual Environment: /Development/x-gal/.venv
GAL Package: 1.3.0 (editable install)

Installed Dev Tools:
- pytest 8.4.2
- pytest-cov 7.0.0
- black 24.x.x
- isort 5.x.x
- flake8 7.x.x

Usage:
  source .venv/bin/activate  # Activate venv
  pytest -v                   # Run tests
  black gal/                  # Format code
  flake8 gal/                 # Lint code
```

## Troubleshooting

### Problem: "python3: command not found"

**Lösung:** Installiere Python 3:
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-venv python3-pip

# macOS
brew install python3

# Fedora/RHEL
sudo dnf install python3 python3-pip
```

### Problem: "ModuleNotFoundError: No module named 'pytest'"

**Lösung:** Virtual Environment aktivieren:
```bash
source .venv/bin/activate
```

Falls immer noch nicht gefunden:
```bash
pip install pytest pytest-cov
```

### Problem: "Permission denied" beim venv erstellen

**Lösung:** Prüfe Schreibrechte oder verwende `--user`:
```bash
# Alternative: User-Installation
pip install --user -e .
pip install --user pytest pytest-cov black isort flake8
```

### Problem: Tests schlagen fehl wegen fehlender Dependencies

**Lösung:** Installiere alle Requirements neu:
```bash
source .venv/bin/activate
pip install -e . --force-reinstall
pip install pytest pytest-cov black isort flake8
```

## Best Practices

### 1. ✅ Immer venv aktivieren

Vor jedem pytest/python Befehl:
```bash
source .venv/bin/activate
```

### 2. ✅ Requirements aktuell halten

Nach Git Pull:
```bash
source .venv/bin/activate
pip install -e . --upgrade
```

### 3. ✅ Tests vor Commits ausführen

```bash
source .venv/bin/activate
pytest -v
black --check gal/
isort --check-only gal/
flake8 gal/
```

### 4. ✅ Coverage Berichte generieren

```bash
source .venv/bin/activate
pytest --cov=gal --cov-report=html
# Öffne htmlcov/index.html im Browser
```

### 5. ✅ Clean Environment

Bei Problemen, venv neu erstellen:
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest pytest-cov black isort flake8
```

## Integration mit anderen Skills

Dieser Skill wird automatisch aufgerufen von:
- **Test Runner** - Vor dem Ausführen von pytest
- **Code Quality Checker** - Vor black/isort/flake8
- **GitHub Actions Monitor** - Bei lokaler Fehleranalyse

## Verwendete Tools

- **Bash**: Für Shell-Befehle
- **Python venv**: Virtual Environment Management
- **pip**: Package Installation
- **pytest**: Test Execution

## Erweiterte Funktionen

### Multi-Python Testing

Teste gegen mehrere Python-Versionen:

```bash
# Python 3.10
python3.10 -m venv .venv310
source .venv310/bin/activate
pip install -e . && pip install pytest
pytest -v
deactivate

# Python 3.11
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -e . && pip install pytest
pytest -v
deactivate

# Python 3.12
python3.12 -m venv .venv312
source .venv312/bin/activate
pip install -e . && pip install pytest
pytest -v
deactivate
```

### Docker Development Environment

Falls lokale Installation nicht möglich:

```bash
# Build Dev Container
docker build -t x-gal-dev -f Dockerfile.dev .

# Run Tests in Container
docker run --rm -v $(pwd):/app x-gal-dev pytest -v

# Interactive Shell
docker run --rm -it -v $(pwd):/app x-gal-dev bash
```

## Zusammenfassung

Dieser Skill automatisiert:
- ✅ Python-Verfügbarkeit prüfen
- ✅ Virtual Environment erstellen
- ✅ Dependencies installieren (Runtime + Dev)
- ✅ Installation verifizieren
- ✅ Tests ausführen (optional)
- ✅ Code Quality Tools einrichten

**Typischer Workflow:**
1. Clone Repository
2. Führe Skill aus → Dev Environment bereit
3. Entwickle lokal mit pytest, black, isort, flake8
4. Push → GitHub Actions validiert automatisch

---

**Version:** 1.0.0
**Status:** ✅ Production Ready
**Letzte Aktualisierung:** 2025-10-20
