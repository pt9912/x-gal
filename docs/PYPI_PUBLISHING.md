# PyPI Publishing Guide

Dieser Guide beschreibt, wie GAL (Gateway Abstraction Layer) auf PyPI veröffentlicht wird.

## Übersicht

GAL wird auf [PyPI](https://pypi.org/project/gal-gateway/) unter dem Namen `gal-gateway` veröffentlicht.

- **Package Name:** `gal-gateway`
- **Import Name:** `gal`
- **CLI Command:** `gal`
- **PyPI URL:** https://pypi.org/project/gal-gateway/
- **TestPyPI URL:** https://test.pypi.org/project/gal-gateway/

---

## Installation für Nutzer

### Von PyPI (Empfohlen)

```bash
pip install gal-gateway
```

### Von TestPyPI (Pre-Release Versionen)

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ gal-gateway
```

### Von GitHub (Development)

```bash
pip install git+https://github.com/pt9912/x-gal.git@develop
```

### Von Source

```bash
git clone https://github.com/pt9912/x-gal.git
cd x-gal
pip install -e ".[dev]"
```

---

## PyPI Account Setup (Für Maintainer)

### 1. PyPI Account erstellen

1. Gehe zu https://pypi.org/account/register/
2. Erstelle einen Account
3. Verifiziere deine E-Mail-Adresse

### 2. TestPyPI Account erstellen

1. Gehe zu https://test.pypi.org/account/register/
2. Erstelle einen separaten Account (TestPyPI ist eine separate Instanz!)
3. Verifiziere deine E-Mail-Adresse

### 3. Two-Factor Authentication (2FA) aktivieren

**PyPI:**
1. Gehe zu https://pypi.org/manage/account/
2. Klicke auf "Account security" → "Add 2FA"
3. Wähle eine Methode (TOTP App empfohlen)
4. Folge den Anweisungen

**TestPyPI:**
1. Wiederhole die Schritte für https://test.pypi.org/manage/account/

⚠️ **WICHTIG:** 2FA ist für alle PyPI-Accounts verpflichtend!

### 4. API Tokens generieren

**PyPI Token:**
1. Gehe zu https://pypi.org/manage/account/token/
2. Klicke auf "Add API token"
3. Name: `gal-gateway-github-actions`
4. Scope: "Entire account" (später auf Project beschränken)
5. Kopiere den Token (nur einmal sichtbar!)

**TestPyPI Token:**
1. Gehe zu https://test.pypi.org/manage/account/token/
2. Klicke auf "Add API token"
3. Name: `gal-gateway-github-actions-test`
4. Scope: "Entire account"
5. Kopiere den Token

### 5. GitHub Secrets konfigurieren

1. Gehe zu https://github.com/pt9912/x-gal/settings/secrets/actions
2. Klicke auf "New repository secret"

**Secret 1: PYPI_API_TOKEN**
- Name: `PYPI_API_TOKEN`
- Value: `<dein PyPI Token>`

**Secret 2: TEST_PYPI_API_TOKEN**
- Name: `TEST_PYPI_API_TOKEN`
- Value: `<dein TestPyPI Token>`

---

## Release Prozess

### 1. Pre-Release (TestPyPI)

**Use Case:** Testen vor dem finalen Release

```bash
# 1. Stelle sicher, dass alle Tests passen
pytest -v --cov=gal

# 2. Erstelle Pre-Release Tag
git tag -a v1.1.0-rc1 -m "Release Candidate 1 für v1.1.0"
git push origin v1.1.0-rc1

# 3. GitHub Actions veröffentlicht automatisch auf TestPyPI
# (Check: https://github.com/pt9912/x-gal/actions)

# 4. Teste Installation von TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            gal-gateway==1.1.0rc1

# 5. Teste das Package
gal --version
gal generate examples/rate-limiting-example.yaml
```

**Pre-Release Tags:**
- `v1.1.0-alpha1` - Alpha Release (frühe Testversion)
- `v1.1.0-beta1` - Beta Release (Feature-Complete, aber Bugs möglich)
- `v1.1.0-rc1` - Release Candidate (fast fertig)

### 2. Stable Release (PyPI)

**Use Case:** Offizieller Release

```bash
# 1. Stelle sicher, dass alle Tests passen
pytest -v --cov=gal

# 2. Update VERSION Datei
echo "1.1.0" > VERSION

# 3. Update CHANGELOG.md
# - Verschiebe "Unreleased" nach "[1.1.0] - 2025-10-XX"
# - Füge Release-Datum hinzu

# 4. Commit Version Bump
git add VERSION CHANGELOG.md
git commit -m "chore: Bump version to 1.1.0"
git push origin main

# 5. Erstelle Release Tag
git tag -a v1.1.0 -m "Release v1.1.0 - Traffic Management & Security"
git push origin v1.1.0

# 6. GitHub Actions veröffentlicht automatisch auf PyPI
# (Check: https://github.com/pt9912/x-gal/actions)

# 7. Verifiziere PyPI Release
# - Gehe zu https://pypi.org/project/gal-gateway/
# - Prüfe Version 1.1.0

# 8. Teste Installation von PyPI
pip install gal-gateway==1.1.0

# 9. Teste das Package
gal --version
```

---

## Manuelle Veröffentlichung (Falls GitHub Actions nicht funktioniert)

### TestPyPI

```bash
# 1. Build Package
python -m build

# 2. Check Package
twine check dist/*

# 3. Upload to TestPyPI
twine upload --repository testpypi dist/*
# Username: __token__
# Password: <TEST_PYPI_API_TOKEN>
```

### PyPI

```bash
# 1. Build Package
python -m build

# 2. Check Package
twine check dist/*

# 3. Upload to PyPI
twine upload dist/*
# Username: __token__
# Password: <PYPI_API_TOKEN>
```

---

## Workflow Details

Der Release Workflow (`.github/workflows/release.yml`) besteht aus 4 Jobs:

### 1. `create-release`
- Erstellt GitHub Release
- Nutzt `RELEASE_NOTES.md` als Body

### 2. `build-artifacts`
- Baut Python Wheel (`.whl`) und Source Distribution (`.tar.gz`)
- Erstellt Archiv mit Source Code
- Hochladen zu GitHub Release

### 3. `publish-testpypi`
- **Bedingung:** Tag enthält `-alpha`, `-beta`, oder `-rc`
- Veröffentlicht auf TestPyPI
- Nutzt `TEST_PYPI_API_TOKEN` Secret

### 4. `publish-pypi`
- **Bedingung:** Tag enthält KEINE Pre-Release Suffixe
- Veröffentlicht auf PyPI
- Nutzt `PYPI_API_TOKEN` Secret

---

## Package Metadaten

### pyproject.toml

```toml
[project]
name = "gal-gateway"
version = "1.1.0"  # Dynamisch aus VERSION Datei
description = "Gateway Abstraction Layer - Provider-agnostic API Gateway configuration"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [{name = "Dietmar Burkard"}]

keywords = [
    "api-gateway", "envoy", "kong", "apisix", "traefik",
    "rate-limiting", "authentication", "cors", "circuit-breaker",
    "health-checks", "load-balancing", "jwt", "security"
]

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Code Generators",
    "Topic :: System :: Networking",
    "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    "Topic :: Security",
    # ...
]

dependencies = [
    "click>=8.1.0",
    "pyyaml>=6.0",
    "requests>=2.31.0",
]

[project.scripts]
gal = "gal.cli:cli"
```

### Wichtige Felder

- **name:** PyPI Package Name (`gal-gateway`)
- **version:** Aus `VERSION` Datei gelesen (Semantic Versioning)
- **description:** Kurzbeschreibung (max 200 Zeichen)
- **readme:** README.md als Long Description
- **requires-python:** Mindest-Python-Version (3.10+)
- **keywords:** Suchbegriffe für PyPI
- **classifiers:** PyPI Kategorien/Tags
- **dependencies:** Runtime-Abhängigkeiten
- **scripts:** CLI Entry Point (`gal` Command)

---

## Troubleshooting

### Problem: `twine upload` schlägt fehl mit 403 Forbidden

**Ursache:** Ungültiger API Token oder fehlende Permissions

**Lösung:**
1. Prüfe, ob Token korrekt ist
2. Prüfe, ob Token Scope "Entire account" oder "Project: gal-gateway" hat
3. Erstelle neuen Token falls nötig

### Problem: Package bereits auf PyPI vorhanden

**Ursache:** Version bereits veröffentlicht (PyPI erlaubt kein Überschreiben)

**Lösung:**
1. Bumpe Version in `VERSION` Datei
2. Erstelle neuen Tag
3. Veröffentliche erneut

### Problem: `ModuleNotFoundError` nach Installation

**Ursache:** Package-Struktur falsch oder `__init__.py` fehlt

**Lösung:**
1. Prüfe, ob `gal/__init__.py` existiert
2. Prüfe `setup.py` `packages=find_packages()`
3. Teste lokal: `pip install -e .`

### Problem: CLI Command `gal` nicht gefunden

**Ursache:** Entry Point nicht korrekt konfiguriert

**Lösung:**
1. Prüfe `pyproject.toml` `[project.scripts]`
2. Prüfe `setup.py` `entry_points`
3. Reinstalliere: `pip uninstall gal-gateway && pip install gal-gateway`

### Problem: Dependencies nicht installiert

**Ursache:** `install_requires` fehlt oder falsch

**Lösung:**
1. Prüfe `pyproject.toml` `dependencies`
2. Prüfe `setup.py` `install_requires`
3. Teste: `pip install gal-gateway[dev]`

---

## Best Practices

### 1. Semantic Versioning

- **Major (1.0.0 → 2.0.0):** Breaking Changes
- **Minor (1.0.0 → 1.1.0):** Neue Features, backwards compatible
- **Patch (1.0.0 → 1.0.1):** Bugfixes, backwards compatible

### 2. Pre-Release Versionen

- **Alpha (1.1.0-alpha1):** Frühe Entwicklungsversion, instabil
- **Beta (1.1.0-beta1):** Feature-complete, aber Bugs möglich
- **RC (1.1.0-rc1):** Release Candidate, fast fertig

### 3. Changelog Pflege

- Nutze `CHANGELOG.md` nach [Keep a Changelog](https://keepachangelog.com/)
- Kategorien: Added, Changed, Deprecated, Removed, Fixed, Security

### 4. Testing vor Release

```bash
# Lokal testen
pytest -v --cov=gal

# Build testen
python -m build
twine check dist/*

# TestPyPI testen (Pre-Release)
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ gal-gateway
```

### 5. Release Notes

- Nutze `RELEASE_NOTES.md` für jedes Release
- Beschreibe neue Features, Breaking Changes, Bugfixes
- Füge Beispiele und Migration-Guides hinzu

---

## Security

### API Tokens

- ⚠️ **Niemals** API Tokens in Git committen!
- ⚠️ **Niemals** API Tokens in Logs/Issues teilen!
- ✅ Nutze GitHub Secrets für CI/CD
- ✅ Beschränke Token Scope auf Projekt (nach erstem Release)

### 2FA

- ✅ 2FA ist **verpflichtend** für PyPI
- ✅ Nutze TOTP App (Google Authenticator, Authy, etc.)
- ✅ Bewahre Recovery Codes sicher auf

### Package Signing

- Optional: GPG-Signierung von Releases
- PyPI unterstützt PGP-Signaturen (nicht verpflichtend)

---

## Weiterführende Links

- **PyPI:** https://pypi.org/project/gal-gateway/
- **TestPyPI:** https://test.pypi.org/project/gal-gateway/
- **Python Packaging Guide:** https://packaging.python.org/
- **Twine Docs:** https://twine.readthedocs.io/
- **GitHub Actions:** https://github.com/pt9912/x-gal/actions
- **Semantic Versioning:** https://semver.org/

---

**Letzte Aktualisierung:** 2025-10-18
