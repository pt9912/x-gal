---
name: Documentation Manager
description: Verwaltet und aktualisiert die Dokumentation für x-gal (GAL - Gateway Abstraction Layer). Nutze diesen Skill, wenn neue Features hinzugefügt, Provider erweitert oder Dokumentation aktualisiert werden muss.
---

# Documentation Manager Skill

## Zweck

Dieser Skill stellt sicher, dass die Dokumentation immer aktuell bleibt, wenn Code-Änderungen vorgenommen werden.

## Wann dieser Skill aufgerufen wird

Claude sollte diesen Skill **automatisch** verwenden in folgenden Situationen:

- Nach Hinzufügen neuer Provider (z.B. neuer Gateway-Provider)
- Nach Hinzufügen neuer Features (Authentication, CORS, Rate Limiting, etc.)
- Nach Erweiterung bestehender Provider-Funktionalität
- Nach API-Änderungen in Config-Modellen
- Nach Hinzufügen neuer CLI-Befehle
- Wenn der Nutzer explizit um Dokumentations-Updates bittet
- Nach größeren Refactorings

## Anweisungen

### 1. Code-Änderungen analysieren

Prüfe, welche Art von Änderungen vorgenommen wurden:
- **Neue Provider**: APISIX, Kong, Traefik, Envoy Erweiterungen
- **Neue Config-Modelle**: Dataclasses in `gal/config.py`
- **Neue Features**: Authentication, CORS, Rate Limiting, Circuit Breaker, Health Checks, etc.
- **Breaking Changes**: Config-Änderungen, die bestehende YAML-Configs brechen
- **CLI-Erweiterungen**: Neue Befehle oder Optionen

### 2. Python Docstrings hinzufügen/aktualisieren

**Für neue oder geänderte Klassen/Methoden:**

- Verwende Google-Style Docstrings (wie im Projekt üblich)
- Füge vollständige Docstrings hinzu mit:
  - Beschreibung (Was macht die Methode/Klasse?)
  - `Args:` für alle Parameter
  - `Returns:` für Rückgabewerte
  - `Raises:` für mögliche Exceptions
  - `Example:` mit praktischem Code-Beispiel (optional)

**Beispiel für neue Methode:**
```python
def generate_upstream(self, service: Service) -> dict:
    """Generate upstream configuration for the service.

    Args:
        service: Service configuration object containing upstream details

    Returns:
        dict: Provider-specific upstream configuration

    Raises:
        ValueError: If service configuration is invalid

    Example:
        >>> upstream = provider.generate_upstream(service)
        >>> print(upstream['nodes'])
    """
```

**Beispiel für Dataclass:**
```python
@dataclass
class HealthCheckConfig:
    """Health check configuration for upstream targets.

    Attributes:
        active: Active health check configuration (periodic probing)
        passive: Passive health check configuration (traffic monitoring)
    """
    active: Optional[ActiveHealthCheck] = None
    passive: Optional[PassiveHealthCheck] = None
```

### 3. README.md aktualisieren

**Bei neuen Features:**
- Füge Feature zur Feature-Liste hinzu (mit ✅ oder 🚧)
- Füge Verwendungs-Beispiel zur Usage-Sektion hinzu
- Aktualisiere Provider-Kompatibilitäts-Matrix

**Bei neuen Providern:**
- Füge Provider zur unterstützten Provider-Liste hinzu
- Aktualisiere Feature-Matrix (welche Features der Provider unterstützt)
- Füge Provider-spezifische Hinweise hinzu

**Bei Breaking Changes:**
- Füge Hinweis zur README hinzu
- Dokumentiere Migration-Path für bestehende Configs
- Aktualisiere Beispiele

### 4. Feature-Guide erstellen/aktualisieren (docs/guides/)

**Bei neuem Feature:**
- Erstelle neuen Guide: `docs/guides/<FEATURE_NAME>.md` (auf Deutsch!)
- Struktur:
  - **Übersicht**: Was ist das Feature, warum nutzen?
  - **Schnellstart**: 1-2 einfache Beispiele
  - **Konfigurationsoptionen**: Alle Config-Parameter dokumentiert
  - **Provider-Implementierung**: Wie jeder Provider das Feature umsetzt
  - **Häufige Anwendungsfälle**: 5-10 Beispiele
  - **Best Practices**: Empfehlungen
  - **Troubleshooting**: Häufige Probleme und Lösungen

**Bei Feature-Erweiterung:**
- Aktualisiere bestehenden Guide
- Füge neue Beispiele hinzu
- Aktualisiere Provider-Kompatibilitäts-Matrix im Guide

### 5. Beispiel-Konfigurationen erstellen (examples/)

**Bei neuem Feature:**
- Erstelle `examples/<feature>-example.yaml`
- Füge 10-15 realistische Szenarien hinzu
- Jedes Szenario mit:
  - Kommentaren die den Use-Case erklären
  - Vollständiger lauffähiger Config
  - Provider-spezifischen Hinweisen

**Format:**
```yaml
# ===========================================================================
# Example X: <Use-Case Name>
# ===========================================================================
# Use Case: <Beschreibung>
# Features: <Was wird demonstriert>
# ===========================================================================
services:
  - name: example_service
    # ...
```

### 6. ROADMAP.md aktualisieren

**Bei neuem Feature (wenn Teil von v1.X.0):**
- Markiere Feature als Done (✅) in der Feature-Liste
- Aktualisiere Progress-Prozentsatz
- Füge Implementation-Details hinzu
- Aktualisiere "Last Updated" Datum

**Bei neuem Feature (außerhalb Roadmap):**
- Füge Feature zu "Future Features" hinzu
- Oder erstelle neue Version in Roadmap

### 7. CHANGELOG.md vorbereiten

**Für den nächsten Release:**
- Füge Notiz zu CHANGELOG.md hinzu unter "Unreleased"
- Kategorisiere Änderung:
  - **Added**: Neue Features
  - **Changed**: API-Änderungen
  - **Fixed**: Bugfixes
  - **Deprecated**: Bald entfernte Features

Beispiel:
```markdown
## [Unreleased]

### Added
- Health Checks & Load Balancing support für alle Provider
- Neue Config-Modelle: `HealthCheckConfig`, `LoadBalancerConfig`
- Beispiel-Konfigurationen in `examples/health-checks-example.yaml`

### Changed
- `Upstream` config erweitert um `targets` für Multi-Server-Setups
- Provider-Generierung unterstützt jetzt Health-Check-Konfiguration
```

### 8. mkdocs.yml Navigation aktualisieren

**Bei neuem Guide:**
- Füge Guide zur `nav:` Sektion in `mkdocs.yml` hinzu
- Sortiere nach Kategorie:
  - **Guides**: Schnellstart, Provider-Übersicht, Provider-spezifisch, Transformationen, Entwicklung
  - **Features**: Authentication, CORS, Rate Limiting, Circuit Breaker, etc.
  - **API-Referenz**: CLI, Konfiguration
  - **Architektur**: ARCHITECTURE.md

**Bei neuem Feature:**
- Füge Feature-Guide unter `Features:` in der Navigation hinzu
- Alphabetische Sortierung innerhalb der Kategorie

**Bei Provider-Erweiterung:**
- Aktualisiere Provider-Guide in der Navigation (falls Name geändert)

**Beispiel mkdocs.yml Update:**
```yaml
nav:
  - Start: index.md
  - Guides:
    - Schnellstart: guides/QUICKSTART.md
    - Provider Übersicht: guides/PROVIDERS.md
    - Nginx: guides/NGINX.md
    # ... weitere Provider
  - Features:
    - Authentication: guides/AUTHENTICATION.md
    - CORS: guides/CORS.md
    - Health Checks: guides/HEALTH_CHECKS.md  # ← Neu hinzugefügt
    # ... weitere Features
```

**Bei docs/index.md Aktualisierung:**
- Aktualisiere Feature-Liste auf Landing Page
- Aktualisiere Provider-Tabelle
- Aktualisiere Versionshinweise-Sektion
- Füge neue Quick-Links hinzu

### 9. Tests aktualisieren

**Bei neuem Feature:**
- Erstelle/erweitere Test-Datei: `tests/test_<feature>.py`
- Teste alle Provider (Envoy, Kong, APISIX, Traefik, Nginx, HAProxy)
- Teste Config-Modell-Validierung
- Teste Edge-Cases

### 10. Dokumentations-Checkliste

Verwende diese Checkliste für jede Code-Änderung:

```
Dokumentation Update Checklist:
□ Python Docstrings für neue/geänderte Klassen und Methoden
□ README.md Features/Provider-Matrix aktualisiert
□ docs/README.md aktualisiert (Dokumentations-Hauptseite)
□ docs/index.md aktualisiert (MkDocs Landing Page)
□ Feature-Guide in docs/guides/ erstellt/aktualisiert (auf Deutsch!)
□ mkdocs.yml Navigation aktualisiert (neue Guides/Features hinzugefügt)
□ Beispiel-Konfiguration in examples/ erstellt
□ ROADMAP.md aktualisiert (falls Teil von v1.X.0)
□ vx.x.x-PLAN.md aktualisiert (Feature-Status, Progress, Implementation Details)
□ CHANGELOG.md "Unreleased" Sektion aktualisiert
□ Tests geschrieben und erfolgreich
□ Breaking Changes dokumentiert
□ Provider-Kompatibilität dokumentiert
□ GitHub Pages Deployment erfolgreich (nach Push)
```

## Spezielle Szenarien

### Neues Feature hinzugefügt (z.B. WebSocket Support)

1. **Config-Modelle** (`gal/config.py`):
   - Füge Docstrings zu neuen Dataclasses hinzu
   - Dokumentiere alle Attribute

2. **Provider-Implementierung** (`gal/providers/*.py`):
   - Docstrings für neue Provider-Methoden
   - Dokumentiere Provider-spezifische Limitierungen

3. **Feature-Guide** (`docs/guides/<FEATURE>.md`):
   - Erstelle vollständigen Guide auf Deutsch
   - Struktur: Übersicht, Schnellstart, Konfiguration, Provider-Impl, Use-Cases, Best Practices

4. **Beispiele** (`examples/<feature>-example.yaml`):
   - 10-15 realistische Szenarien
   - Provider-Kompatibilitäts-Hinweise

5. **Tests** (`tests/test_<feature>.py`):
   - Tests für alle Provider
   - Edge-Case-Tests

6. **README.md**:
   - Feature zur Liste hinzufügen
   - Provider-Matrix aktualisieren

7. **docs/index.md** (MkDocs Landing Page):
   - Feature zu Features-Sektion hinzufügen
   - Feature-Tabelle aktualisieren

8. **mkdocs.yml**:
   - Feature-Guide zur Navigation hinzufügen unter `Features:`

9. **ROADMAP.md** (falls Teil von v1.X.0):
   - Feature als Done markieren
   - Progress aktualisieren

10. **vx.x.x-PLAN.md** (falls Teil von v1.X.0):
   - Feature-Status aktualisieren (Pending → In Progress → Done)
   - Progress-Prozentsatz aktualisieren
   - Implementation Details hinzufügen (Commits, Dateien, Test-Ergebnisse)
   - Milestone als erledigt markieren

11. **CHANGELOG.md**:
   - Unter "Added" eintragen

### Neuer Provider hinzugefügt (z.B. Nginx)

1. **Provider-Klasse** (`gal/providers/nginx.py`):
   - Vollständige Docstrings für Klasse und alle Methoden
   - Dokumentiere Provider-spezifische Besonderheiten

2. **Config-Factory** (`gal/config_factory.py`):
   - Provider-Registrierung dokumentieren

3. **README.md**:
   - Provider zur unterstützten Liste hinzufügen
   - Feature-Matrix für neuen Provider erstellen
   - Installation/Setup-Hinweise

4. **docs/README.md**:
   - Provider zur Guides-Tabelle hinzufügen
   - Provider zur unterstützten Provider-Tabelle hinzufügen

5. **docs/index.md** (MkDocs Landing Page):
   - Provider zur Provider-Tabelle hinzufügen
   - Provider-Guide zu Guides-Navigation hinzufügen

6. **mkdocs.yml**:
   - Provider-Guide zur Navigation hinzufügen unter `Guides:`

7. **Tests** (`tests/test_nginx.py`):
   - Vollständige Test-Suite für Provider
   - Alle Features testen

8. **Beispiele**:
   - Alle bestehenden Beispiele auf neuen Provider testen
   - Provider-spezifische Beispiele hinzufügen

9. **Guides**:
   - Alle Feature-Guides um Provider-Implementierung erweitern

10. **ROADMAP.md**:
   - Provider zur Liste hinzufügen
   - Feature-Matrix aktualisieren

11. **vx.x.x-PLAN.md** (falls Teil von v1.X.0):
   - Provider-Feature als Done markieren
   - Implementation Details dokumentieren

12. **CHANGELOG.md**:
   - Unter "Added" eintragen

### Config Breaking Change

1. **Migration-Guide** erstellen:
   - Dokumentiere alte vs. neue Config
   - Gib Beispiele für Migration
   - Erstelle Konvertierungs-Script (falls sinnvoll)

2. **README.md**:
   - **Breaking Changes** Sektion hinzufügen
   - Dokumentiere Migration-Path

3. **CHANGELOG.md**:
   - Unter "Changed" mit **BREAKING** Prefix
   - Erkläre Migration-Path detailliert

4. **Alle Beispiele aktualisieren**:
   - Alle YAML-Dateien in `examples/` anpassen

5. **Tests aktualisieren**:
   - Alte Config-Tests entfernen/anpassen
   - Neue Config-Tests hinzufügen

### Provider-Erweiterung (Feature zu existierendem Provider)

1. **Provider-Code** dokumentieren:
   - Docstrings für neue Methoden
   - Kommentare für komplexe Provider-spezifische Logik

2. **Feature-Guide aktualisieren**:
   - Provider-Implementierung-Sektion erweitern
   - Beispiele für Provider hinzufügen

3. **Tests erweitern**:
   - Provider-spezifische Tests für Feature

4. **CHANGELOG.md**:
   - Unter "Changed" oder "Added"

## Validierung

Nach jedem Dokumentations-Update:

1. **Lint-Check**:
   - `black --check .` - Code-Formatierung
   - `isort --check-only .` - Import-Sortierung
   - `flake8 .` - Code-Qualität

2. **Test-Check**:
   - `python -m pytest -v` - Alle Tests müssen passen
   - Coverage prüfen

3. **Config-Examples**:
   - Alle YAML-Beispiele in `examples/` testen
   - `python gal-cli.py generate examples/<example>.yaml`

4. **MkDocs-Build**:
   - `mkdocs build --strict` - Dokumentation bauen (strict mode)
   - Prüfe auf broken links oder fehlende Dateien
   - `mkdocs serve` - Lokal testen auf http://127.0.0.1:8000

5. **Link-Check**:
   - Alle Links in Markdown-Dateien prüfen
   - Interne Verweise auf andere Guides
   - Externe Links (GitHub, Provider-Docs)

6. **Build-Check**:
   - `python -m build` - Distribution Packages erstellen

7. **GitHub Pages Deployment**:
   - Nach Push auf main/develop: GitHub Actions Workflow überwachen
   - Verifiziere erfolgreichen Deployment auf https://pt9912.github.io/x-gal/
   - Teste Navigation und Suchfunktion

## Integration mit anderen Skills

- **Release Skill**: Dokumentation muss vor Release komplett sein
- **Actions Monitor**: Nach Docs-Update GitHub Actions überwachen

## Fehlerbehandlung

- Falls Docstrings fehlen: Google-Style Docstrings hinzufügen
- Falls Beispiele nicht funktionieren: Config-Syntax prüfen, Provider testen
- Falls Links broken: Dateipfade und relative Pfade prüfen
- Falls Tests fehlschlagen: Docs mit Code synchronisieren

## Tools

- Read: Existierende Dokumentation lesen
- Write/Edit: Dokumentation aktualisieren
- Bash: `pytest`, `python gal-cli.py`, `python -m build` ausführen
- TodoWrite: Dokumentations-Checkliste tracken
- Glob: Dokumentationsdateien finden

## Best Practices

1. **Immer YAML-Beispiele hinzufügen**: Praktische Configs > theoretische Beschreibungen
2. **User-First**: Aus Gateway-Admin-Perspektive schreiben
3. **Provider-Kompatibilität klar machen**: Immer dokumentieren, welche Provider ein Feature unterstützen
4. **Deutsche Dokumentation**: Alle Guides auf Deutsch (außer Code und YAML)
5. **Up-to-date**: Dokumentation gleichzeitig mit Code aktualisieren, nicht später
6. **Test Examples**: Alle YAML-Beispiele müssen generierbar sein
7. **Real-World Use-Cases**: Beispiele sollen echte Produktions-Szenarien zeigen

## Output-Format

Nach Dokumentations-Update zeige Zusammenfassung:

```
📚 Dokumentation aktualisiert:

✅ Python Docstrings:
  - HealthCheckConfig Dataclass vollständig dokumentiert
  - APISIXProvider._generate_upstream() Methode dokumentiert

✅ Feature-Guide:
  - docs/guides/HEALTH_CHECKS.md erstellt (1000+ Zeilen, Deutsch)
  - Alle Provider-Implementierungen dokumentiert
  - 15+ Use-Cases mit Beispielen

✅ Beispiele:
  - examples/health-checks-example.yaml erstellt
  - 15 Szenarien (Basic HC, Canary, Blue-Green, Multi-DC, etc.)

✅ README.md:
  - Health Checks zur Feature-Liste hinzugefügt
  - Provider-Matrix aktualisiert

✅ docs/README.md:
  - Feature zu Guides-Tabelle hinzugefügt

✅ docs/index.md (MkDocs Landing Page):
  - Feature zu Features-Sektion hinzugefügt
  - Feature-Links aktualisiert

✅ mkdocs.yml:
  - HEALTH_CHECKS.md zur Navigation hinzugefügt (Features)

✅ ROADMAP.md:
  - Feature 7 als Done markiert
  - Progress 71% → 86%

✅ CHANGELOG.md:
  - "Added: Health Checks & Load Balancing für alle Provider"

✅ Tests:
  - tests/test_health_checks.py erstellt
  - 50+ Tests für alle Provider

🔗 Nächste Schritte:
  - Beispiele testen: python gal-cli.py generate examples/health-checks-example.yaml
  - Tests ausführen: pytest tests/test_health_checks.py -v
  - MkDocs lokal testen: mkdocs serve
  - GitHub Pages Deployment nach Push überwachen
  - Vor Release: CHANGELOG.md vervollständigen
```
