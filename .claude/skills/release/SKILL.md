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

### 9. Git Commit und Tag erstellen

- Führe aus: `git add .`
- Commit-Message: `chore: release v<VERSION>`
- Tag erstellen: `git tag v<VERSION>`
- Füge die übliche Co-Authored-By Signatur hinzu

### 10. Push zu GitHub

- Führe aus: `git push`
- Führe aus: `git push --tags`

### 11. GitHub Actions beobachten (develop)

- **WICHTIG:** Warte auf den Abschluss der GitHub Actions
- Führe aus: `gh run watch` um den Status zu überwachen
- Falls Actions fehlschlagen:
  - Zeige die Fehler-Logs an
  - Stoppe den Release-Prozess
  - Informiere den Nutzer über das Problem
  - Gib Hinweise zur Fehlerbehebung
  - **WICHTIG:** Merge NICHT in main, wenn Actions fehlgeschlagen sind
- Falls Actions erfolgreich sind:
  - Informiere den Nutzer über den Erfolg
  - Fahre mit dem Merge in main fort

### 12. Develop in Main mergen

- **WICHTIG:** Der Release muss auch im main Branch verfügbar sein
- Wechsle zum main Branch: `git checkout main`
- Pull neueste Änderungen: `git pull origin main`
- Merge develop in main: `git merge develop`
- Falls Merge-Konflikte auftreten:
  - Zeige die Konflikte an
  - Informiere den Nutzer
  - Bitte um manuelle Konfliktlösung
  - Warte auf Bestätigung, bevor fortgefahren wird
- Push zu main: `git push origin main`
- **WICHTIG:** Beobachte GitHub Actions für main Branch
- Führe aus: `gh run watch` um den Status zu überwachen
- Falls Actions auf main fehlschlagen:
  - Zeige die Fehler-Logs an
  - Informiere den Nutzer über das Problem
- Wechsle zurück zum develop Branch: `git checkout develop`

### 13. GitHub Release erstellen

- **WICHTIG:** Das GitHub Release wird AUTOMATISCH erstellt durch den Tag-Push
- Der `.github/workflows/release.yml` Workflow wird automatisch gestartet
- Dieser Workflow:
  - Erstellt das GitHub Release mit RELEASE_NOTES.md
  - Baut die Distribution Packages (Wheel und Source)
  - Erstellt ein Source-Archiv (tar.gz)
  - Lädt alle Artifacts zum Release hoch
  - Veröffentlicht optional zu PyPI (aktuell deaktiviert)
- Beobachte den Release-Workflow: `gh run watch`
- Falls der Workflow fehlschlägt:
  - Zeige die Fehler an
  - Informiere den Nutzer
  - Gib Hinweise zur Fehlerbehebung
- Zeige die Release-URL an: `https://github.com/pt9912/x-gal/releases/tag/v<VERSION>`

### 14. Zurück zu develop und synchronisieren

- **WICHTIG:** Develop und Main müssen synchron bleiben
- Wechsle zum develop Branch: `git checkout develop`
- Pull neueste Änderungen von main: `git pull origin main`
- Merge main in develop: `git merge main`
- Falls Merge-Konflikte auftreten (sollte normalerweise nicht passieren):
  - Zeige die Konflikte an
  - Informiere den Nutzer
  - Bitte um manuelle Konfliktlösung
- Push zu develop: `git push origin develop`
- Bestätige, dass develop und main jetzt synchron sind

### 15. Abschluss

- Zeige eine Zusammenfassung aller durchgeführten Schritte
- Informiere über nächste Schritte:
  - PyPI Publishing ist aktuell deaktiviert (`.github/workflows/release.yml` - Zeile 78)
  - Docker Images werden automatisch gebaut (bei aktiviertem Docker Workflow)
  - Distribution Packages sind im GitHub Release verfügbar
- Zeige Links:
  - GitHub Release URL: `https://github.com/pt9912/x-gal/releases/tag/v<VERSION>`
  - GitHub Actions für develop: `https://github.com/pt9912/x-gal/actions`
  - GitHub Actions für main: `https://github.com/pt9912/x-gal/actions`
  - Docker Hub (falls konfiguriert): `ghcr.io/pt9912/x-gal:<VERSION>`
- Bestätige, dass develop und main synchronisiert sind
- Informiere über manuelle Installation: `pip install <Release-Artifact-URL>`

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
