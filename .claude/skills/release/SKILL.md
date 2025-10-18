---
name: Release Manager
description: Automatisiert den vollständigen Release-Prozess für x-gal (GAL - Gateway Abstraction Layer). Nutze diesen Skill, wenn der Nutzer einen neuen Release/Version erstellen möchte oder Begriffe wie "release", "version bump", "neue Version" erwähnt.
---

# Release Manager Skill

## Zweck

Dieser Skill orchestriert den kompletten Release-Prozess für das x-gal (GAL - Gateway Abstraction Layer) Projekt und stellt sicher, dass alle notwendigen Schritte korrekt ausgeführt werden.

## Anweisungen für Release-Prozess

Wenn der Nutzer einen Release erstellen möchte, führe folgende Schritte in dieser Reihenfolge aus:

### 1. Versionsnummer abfragen

- Frage den Nutzer nach der neuen Versionsnummer (Format: `x.y.z`, z.B. `1.1.0`)
- Validiere das Format (muss `x.y.z` entsprechen, kein `v` Präfix)

### 2. Version bumpen

- Aktualisiere die `VERSION` Datei mit der neuen Version
- Aktualisiere `Dockerfile` (falls die Version dort hardcoded ist)
- Aktualisiere `CHANGELOG.md`:
  - Erstelle eine neue Sektion `## [x.y.z] - YYYY-MM-DD`
  - Füge TODOs für die verschiedenen Kategorien ein:
    - `### Added`
    - `### Changed`
    - `### Fixed`
    - `### Deprecated`
    - `### Removed`
    - `### Security`

### 3. CHANGELOG.md vervollständigen

- **WICHTIG:** Das bump-version Skript hat TODOs im CHANGELOG.md erstellt
- Lies git log seit dem letzten Release: `git log --oneline <last-tag>..HEAD`
- Lies die Änderungen in den relevanten Dateien
- Ersetze die TODOs durch echte Änderungen in folgenden Kategorien:
  - **Added**: Neue Features
  - **Changed**: Änderungen an bestehender Funktionalität
  - **Fixed**: Bugfixes
  - **Deprecated**: Bald entfernte Features
  - **Removed**: Entfernte Features
  - **Security**: Sicherheits-Updates
- Verwende das Format: `- Beschreibung (#PR-Nummer falls vorhanden)`

### 4. RELEASE_NOTES.md erstellen

- **WICHTIG:** Erstelle die RELEASE_NOTES.md vollständig neu
- Lies das gerade aktualisierte CHANGELOG.md für die neue Version
- Lies die aktuelle RELEASE_NOTES.md (falls vorhanden) für das Format
- Erstelle eine umfassende RELEASE_NOTES.md mit:
  - Version und Datum
  - Zusammenfassung der wichtigsten Änderungen
  - Detaillierte Beschreibung aller Features, Bugfixes, etc.
  - Upgrade-Hinweise (falls nötig)
  - Breaking Changes (falls vorhanden)
  - Test-Statistiken (falls relevant)

**Format-Vorlage:**

```markdown
# GAL v<VERSION>

Released: <DATUM>

## Zusammenfassung

[Kurze Zusammenfassung der wichtigsten Änderungen]

## Neue Features

### Feature 1
[Detaillierte Beschreibung mit Code-Beispielen falls sinnvoll]

### Feature 2
...

## Verbesserungen

- [Verbesserung 1]
- [Verbesserung 2]

## Bugfixes

- [Fix 1]
- [Fix 2]

## Breaking Changes

[Falls vorhanden]

## Installation

```bash
# Via PyPI (wenn aktiviert)
pip install gal-gateway

# Via Docker
docker pull ghcr.io/pt9912/x-gal:<VERSION>

# Oder manuell
git clone https://github.com/pt9912/x-gal.git
cd x-gal
pip install -e .
```

## Test-Statistiken

- Anzahl Tests: XXX (aus pytest)
- Coverage: XX%
- Python Versionen: 3.10, 3.11, 3.12

## Bekannte Einschränkungen

[Falls vorhanden]
```

### 5. Dokumentation prüfen

- **WICHTIG:** Dokumentation muss aktuell sein vor dem Release
- Prüfe, dass wichtige Dateien existieren und aktuell sind:
  - `README.md`
  - `ROADMAP.md`
  - `docs/guides/AUTHENTICATION.md`
  - `docs/guides/CORS.md`
  - `docs/guides/HEADER_MANIPULATION.md`
  - `docs/guides/RATE_LIMITING.md`
  - `docs/guides/CIRCUIT_BREAKER.md`
  - `docs/guides/HEALTH_CHECKS.md`
  - Alle Beispiel-YAMLs in `examples/`
- Informiere, falls wichtige Dokumentation fehlt oder veraltet ist

### 6. Lint prüfen

- **WICHTIG:** Lint muss VOR den Tests ausgeführt werden
- Führe Black aus: `black --check .`
- Führe isort aus: `isort --check-only .`
- Führe flake8 aus: `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`
- Falls Fehler auftreten:
  - Zeige die Fehler an
  - Informiere den Nutzer
  - Biete automatische Fixes an: `black .` und `isort .`
  - Stoppe den Release-Prozess bis Fehler behoben sind

### 7. Tests ausführen

- Führe aus: `python -m pytest -v --cov=gal --cov-report=term`
- Falls Fehler auftreten:
  - Zeige die Fehler an
  - Stoppe den Release-Prozess und informiere den Nutzer
- Notiere Coverage-Prozentsatz für RELEASE_NOTES.md

### 8. Build erstellen

- Führe aus: `python -m build`
- Falls Fehler auftreten:
  - Zeige die Fehler an
  - Stoppe den Release-Prozess und informiere den Nutzer
- Prüfe, dass `dist/` Verzeichnis erstellt wurde mit `.whl` und `.tar.gz` Dateien

### 9. Git Commit erstellen

- Führe aus: `git add VERSION CHANGELOG.md RELEASE_NOTES.md`
- Commit-Message: `chore: Bump version to <VERSION>`
- Füge detaillierte Commit-Message hinzu mit:
  - `VERSION: alte_version → neue_version`
  - `CHANGELOG.md: Add v<VERSION> release notes (German)`
  - `RELEASE_NOTES.md: v<VERSION> release notes (German)`
  - Zusammenfassung der wichtigsten Änderungen
- Füge die übliche Co-Authored-By Signatur hinzu

### 10. Push zu GitHub (develop)

- Führe aus: `git push origin develop`
- Warte kurz bis der Push verarbeitet wurde

### 11. GitHub Actions beobachten (develop - Tests)

- **WICHTIG:** Warte auf den Abschluss der Test-GitHub Actions auf develop
- Führe aus: `gh run watch` um den Status zu überwachen
- Falls Actions fehlschlagen:
  - Zeige die Fehler-Logs an
  - Stoppe den Release-Prozess
  - Informiere den Nutzer über das Problem
  - Gib Hinweise zur Fehlerbehebung
  - **WICHTIG:** Erstelle KEINEN Tag, wenn Tests fehlgeschlagen sind
- Falls Actions erfolgreich sind:
  - Informiere den Nutzer über den Erfolg
  - Fahre mit der Tag-Erstellung fort

### 12. Release Tag erstellen und pushen

- **WICHTIG:** Tag wird von develop aus erstellt
- Erstelle annotated Tag: `git tag -a v<VERSION> -m "Release v<VERSION> - <Kurztitel>"`
- Füge erweiterte Tag-Message hinzu mit:
  - Highlights der wichtigsten Features
  - Statistiken (Features/Tests/Docs)
  - Hinweis auf RELEASE_NOTES.md für Details
- Push Tag zu GitHub: `git push origin v<VERSION>`
- **WICHTIG:** Der Tag-Push triggert automatisch den Release-Workflow

### 13. GitHub Release Workflow beobachten

- **WICHTIG:** Das GitHub Release wird AUTOMATISCH erstellt durch den Tag-Push
- Der `.github/workflows/release.yml` Workflow wird automatisch gestartet
- Dieser Workflow führt folgende Jobs aus:
  - **create-release:** Erstellt GitHub Release mit RELEASE_NOTES.md
  - **build-artifacts:** Baut Distribution Packages (Wheel, Source, Archive)
  - **publish-testpypi:** Veröffentlicht zu TestPyPI (nur bei Pre-Release Tags: -alpha, -beta, -rc)
  - **publish-pypi:** Veröffentlicht zu PyPI (nur bei stabilen Tags ohne Pre-Release Suffix)
- Beobachte den Release-Workflow: `gh run watch <run-id>`
- Prüfe alle Jobs:
  - ✅ Create GitHub Release
  - ✅ Build Release Artifacts
  - ✅ Publish to PyPI (bei stabilen Releases, wenn PYPI_API_TOKEN konfiguriert)
  - ⊝ Publish to TestPyPI (übersprungen bei stabilen Releases)
- Falls der Workflow fehlschlägt:
  - Zeige die Fehler an
  - Informiere den Nutzer
  - Gib Hinweise zur Fehlerbehebung
  - **WICHTIG:** Bei PyPI-Fehlern: Prüfe ob PYPI_API_TOKEN und TEST_PYPI_API_TOKEN Secrets konfiguriert sind
- Zeige die Release-URL an: `https://github.com/pt9912/x-gal/releases/tag/v<VERSION>`
- Zeige PyPI-URL an (falls erfolgreich): `https://pypi.org/project/gal-gateway/`

### 14. Develop in Main mergen

- **WICHTIG:** Der Release muss auch im main Branch verfügbar sein
- Wechsle zum main Branch: `git checkout main`
- Pull neueste Änderungen: `git pull origin main`
- Merge develop in main: `git merge develop --no-edit`
- Falls Merge-Konflikte auftreten:
  - Zeige die Konflikte an
  - Informiere den Nutzer
  - Bitte um manuelle Konfliktlösung
  - Warte auf Bestätigung, bevor fortgefahren wird
- Push zu main: `git push origin main`

### 15. Main zurück in Develop mergen

- **WICHTIG:** Nach dem Release muss develop wieder auf dem Stand von main sein
- Wechsle zurück zum develop Branch: `git checkout develop`
- Pull neueste Änderungen: `git pull origin develop`
- Merge main in develop: `git merge main --no-edit`
- Falls Merge-Konflikte auftreten (sollte nicht vorkommen):
  - Zeige die Konflikte an
  - Informiere den Nutzer
  - Bitte um manuelle Konfliktlösung
- Push zu develop: `git push origin develop`
- Bestätige, dass develop und main jetzt vollständig synchron sind

### 16. Abschluss

- Zeige eine Zusammenfassung aller durchgeführten Schritte
- Informiere über veröffentlichte Artifacts:
  - ✅ GitHub Release erstellt mit RELEASE_NOTES.md
  - ✅ Distribution Packages (Wheel, Source, Archive) hochgeladen
  - ✅ PyPI Publishing automatisch (bei stabilen Releases mit konfiguriertem PYPI_API_TOKEN)
  - ✅ TestPyPI Publishing automatisch (bei Pre-Release Tags mit TEST_PYPI_API_TOKEN)
  - ✅ Docker Images werden automatisch gebaut (bei Tags)
- Zeige Links:
  - GitHub Release URL: `https://github.com/pt9912/x-gal/releases/tag/v<VERSION>`
  - PyPI Package (falls published): `https://pypi.org/project/gal-gateway/`
  - GitHub Container Registry: `ghcr.io/pt9912/x-gal:v<VERSION>`
  - GitHub Actions: `https://github.com/pt9912/x-gal/actions`
- Bestätige, dass develop und main synchronisiert sind
- Zeige Installations-Befehle:
  - Von PyPI (empfohlen): `pip install gal-gateway`
  - Von Docker: `docker pull ghcr.io/pt9912/x-gal:v<VERSION>`
  - Von Release-Artifact: `pip install <Release-Artifact-URL>`
- **WICHTIG:** Falls PyPI Publishing fehlgeschlagen ist:
  - Prüfe ob PYPI_API_TOKEN Secret konfiguriert ist
  - Siehe docs/PYPI_PUBLISHING.md für Setup-Anleitung
  - Falls nötig, manuelles Publishing: `twine upload dist/*`

## Fehlerbehandlung

- Bei jedem Fehler: Stoppe den Prozess sofort
- Informiere den Nutzer über den Fehler
- Gib Hinweise zur Behebung
- Frage, ob der Nutzer den Prozess nach der Fehlerbeseitigung fortsetzen möchte

## Wichtige Hinweise

- Dieser Skill sollte nur im `develop` Branch ausgeführt werden
- Nach erfolgreichem Release muss `develop` in `main` gemergt werden
- Der Skill nutzt GitHub Actions Workflows für automatisierte Prozesse:
  - `.github/workflows/test.yml` - Läuft bei jedem Push auf develop/main
  - `.github/workflows/release.yml` - Läuft automatisch bei Tag-Push
  - `.github/workflows/docker-build.yml` - Docker Image Build
- Python Build-System: `pyproject.toml` mit setuptools
- Versionsverwaltung: `VERSION` Datei (wird von pyproject.toml gelesen)

## Verwendete Tools

- Bash: Für Python/pip/git Befehle
- Read: Für das Lesen von CHANGELOG.md, git log, VERSION, etc.
- Write/Edit: Für VERSION, CHANGELOG.md, RELEASE_NOTES.md
- TodoWrite: Für Fortschrittsverfolgung des Release-Prozesses
- Glob: Für das Finden von Dokumentationsdateien
