---
name: Documentation Manager
description: Verwaltet und aktualisiert die Dokumentation für x-gal (GAL - Gateway Abstraction Layer). Nutze diesen Skill PROAKTIV, wenn neue Features hinzugefügt werden, neue Provider hinzugefügt oder bestehende Provider erweitert werden, oder Dokumentation aktualisiert werden muss. WICHTIG Bei neuen Providern müssen 20+ Dokumente aktualisiert werden (Feature-Guides, PROVIDERS.md, README, etc.).
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
- Aktualisiere Provider-Guide 
  
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

### Neuer Provider hinzugefügt (z.B. GCP API Gateway)

**WICHTIG:** Bei neuen Providern müssen VIELE Dokumente aktualisiert werden!

1. **Provider-Klasse** (`gal/providers/<provider>.py`):
   - Vollständige Docstrings für Klasse und alle Methoden
   - Dokumentiere Provider-spezifische Besonderheiten
   - parse() und generate() Methoden dokumentieren

2. **Parser-Klasse** (`gal/parsers/<provider>_parser.py`) (falls Import unterstützt):
   - Vollständige Docstrings für Parser-Klasse
   - Dokumentiere Import-Format (OpenAPI, Terraform, etc.)
   - Dokumentiere Limitierungen beim Import

3. **Config-Modelle** (`gal/config.py`):
   - Provider-spezifische Config-Klasse dokumentieren (z.B. `GCPAPIGatewayConfig`)
   - Alle Parameter mit Docstrings versehen
   - Beispiele in Docstrings

4. **CLI-Integration** (`gal-cli.py`):
   - Provider in allen Commands registrieren (generate, validate, import, etc.)
   - Dokumentiere CLI-Verwendung

5. **README.md**:
   - Provider-Anzahl aktualisieren ("7 Provider" → "9 Provider")
   - Provider zur unterstützten Liste hinzufügen
   - Feature-Matrix für neuen Provider erstellen
   - Installation/Setup-Hinweise

6. **docs/README.md**:
   - Provider zur Guides-Tabelle hinzufügen
   - Provider zur unterstützten Provider-Tabelle hinzufügen

7. **docs/index.md** (MkDocs Landing Page):
   - Provider-Anzahl aktualisieren
   - Provider zur Provider-Tabelle hinzufügen
   - Provider-Guide zu Features-Links hinzufügen

8. **docs/guides/PROVIDERS.md** - **SEHR WICHTIG!**:
   - Provider zur Provider-Übersichts-Tabelle hinzufügen
   - Vollständiger Provider-Abschnitt mit:
     - Übersicht & Stärken
     - Ideale Use-Cases
     - GAL-Generierung (Output-Format & Struktur)
     - Transformationen (wie Provider Transformationen handhabt)
     - gRPC-Support (falls vorhanden)
     - Authentifizierung
     - Rate Limiting
     - Circuit Breaker (falls unterstützt)
     - Health Checks
     - Deployment-Befehle
     - Monitoring & Observability
     - Best Practices

9. **Provider-spezifischer Guide** (`docs/guides/<PROVIDER>.md`):
   - Umfassender Guide (1000+ Zeilen auf Deutsch!)
   - Struktur:
     - Übersicht & Architektur
     - Schnellstart
     - Konfigurationsoptionen (alle Parameter)
     - Provider-spezifische Features
     - Deployment-Strategien
     - Import/Export (falls unterstützt)
     - Authentication/Authorization
     - CORS Configuration
     - Multi-Region/Multi-Zone (falls Cloud-Provider)
     - Migration von/zu anderen Providern
     - Best Practices
     - Troubleshooting
     - Performance & Limits
     - Security Best Practices

   - **Mermaid-Diagramme** - **SEHR EMPFOHLEN für neue Provider!**
     - **WICHTIG:** MkDocs Material unterstützt Mermaid nativ (siehe mkdocs.yml:122-124)
     - Verwende den `mermaid-expert` Agent für professionelle Diagramme
     - **Empfohlene Diagramme für Provider-Guides:**
       1. **Architektur-Diagramm** (Graph TB):
          - Client Layer → Gateway → Backend Services
          - Authentication Layer, Traffic Management, Monitoring
          - Zeigt alle Komponenten und deren Interaktionen
          - Professionelles Farbschema (8+ Farben für verschiedene Komponenten)

       2. **Request Flow Sequenzdiagramm** (Sequence Diagram):
          - Client → Gateway → Backend Request Flow
          - Authentication Flow (JWT, API Key)
          - CORS Preflight (OPTIONS) Flow
          - Alternative Flows (Fehlerszenarien)
          - Auto-nummerierte Schritte
          - Detaillierte Header-Informationen

       3. **Deployment-Flowchart** (Flowchart TD):
          - Entscheidungsbaum für verschiedene Deployment-Szenarien
          - 3-5 Deployment-Szenarien mit Entscheidungslogik
          - Jedes Szenario mit konkreten Deployment-Schritten
          - Use-Case-Beschreibungen

       4. **Migration-Flow** (Flowchart LR):
          - Migration von/zu anderen Providern
          - GAL Import/Export Layer Visualisierung
          - Migrations-Schritte mit Annotations
          - Migration-Checkliste-Tabelle

     - **Mermaid-Syntax:**
       ```markdown
       ```mermaid
       graph TB
           Client[Client] --> Gateway[API Gateway]
           Gateway --> Backend[Backend Service]
       ```
       ```

     - **Best Practices für Mermaid:**
       - Konsistentes Farbschema über alle Diagramme
       - Deutsche Beschriftungen
       - Kurze, prägnante Labels
       - Erklärungstext nach jedem Diagramm
       - Production-ready Styling

     - **Beispiel (GCP API Gateway):**
       - 4 Mermaid-Diagramme: Architektur, Request Flow, Deployment, Migration
       - ~200 Zeilen Mermaid-Code
       - Professionelles 8-Farben-Schema
       - Alle Diagramme interaktiv in MkDocs

10. **Import-Guide** (`docs/import/<provider>.md`) (falls Import unterstützt):
   - Import-Prozess dokumentieren
   - Feature-Support-Matrix (was wird beim Import unterstützt)
   - Import-Beispiele (Basic, JWT, CORS, etc.)
   - Migration-Guides (zu/von anderen Providern)
   - Limitierungen und Workarounds
   - Troubleshooting

11. **Beispiel-Konfiguration** (`examples/<provider>-example.yaml`):
   - 5-15 realistische Szenarien
   - Provider-spezifische Features zeigen
   - Jedes Szenario mit Kommentaren
   - Deployment-Anweisungen

12. **mkdocs.yml** - **2 Stellen aktualisieren!**:
   - Provider-Guide zur Navigation unter `Features:` hinzufügen
   - Import-Guide zur Navigation unter `Config Import & Migration:` hinzufügen

13. **Alle Feature-Guides aktualisieren** - **KRITISCH & ZEITAUFWÄNDIG!**:

   **WICHTIG:** Jeder Feature-Guide hat eine "Provider-spezifische Implementierungen" Sektion!
   Für JEDEN neuen Provider muss eine NEUE Untersektion hinzugefügt werden!

   **Format der Provider-Sektion in Feature-Guides:**
   ```markdown
   ## Provider-spezifische Implementierungen

   ### Kong
   [Kong-spezifische Implementation...]

   ### APISIX
   [APISIX-spezifische Implementation...]

   ### GCP API Gateway  ← NEU HINZUFÜGEN!

   GCP API Gateway implementiert [Feature] mit [Mechanismus].

   **[Feature-Typ]:**
   - Mechanismus: [x-google-* Extension / OpenAPI 2.0 / etc.]
   - Features: [Spezifische Features]
   - Hinweis: [GCP-spezifische Limitierungen]

   **Generiertes Config-Beispiel:**
   ```yaml
   swagger: "2.0"
   # ... OpenAPI 2.0 Beispiel
   ```

   **Deployment:**
   ```bash
   gcloud api-gateway apis create API_ID ...
   ```
   ```

   **Feature-Guides die aktualisiert werden müssen:**

   - **docs/guides/AUTHENTICATION.md**:
     * Füge "### GCP API Gateway" Sektion nach anderen Providern hinzu
     * Dokumentiere JWT Authentication (x-google-issuer, x-google-jwks_uri)
     * Dokumentiere API Key Support (falls implementiert)
     * Zeige OpenAPI 2.0 securityDefinitions Beispiel
     * Zeige gcloud Deployment-Befehle

   - **docs/guides/CORS.md**:
     * Füge "### GCP API Gateway" Sektion hinzu
     * Dokumentiere OPTIONS Methods für CORS Preflight
     * Zeige Access-Control-* Headers in Responses
     * Zeige cors_allow_origins, cors_allow_methods Config

   - **docs/guides/RATE_LIMITING.md**:
     * Füge "### GCP API Gateway" Sektion hinzu
     * Dokumentiere GCP API Gateway Quotas & Rate Limits
     * Zeige Cloud Endpoints Quota-Konfiguration (falls unterstützt)
     * Oder: Dokumentiere "Nicht nativ unterstützt, nutze Backend-Rate-Limiting"

   - **docs/guides/HEADERS.md**:
     * Füge "### GCP API Gateway" Sektion hinzu
     * Dokumentiere X-Forwarded-* Headers
     * Dokumentiere Custom Header Injection (falls unterstützt)
     * Zeige Backend-Header-Transformation

   - **docs/guides/TIMEOUT_RETRY.md**:
     * Füge "### GCP API Gateway" Sektion hinzu
     * Dokumentiere backend_deadline Parameter
     * Dokumentiere Timeout-Konfiguration in x-google-backend
     * Zeige Retry-Strategien (falls unterstützt)

   - **docs/guides/LOGGING_OBSERVABILITY.md**:
     * Füge "### GCP API Gateway" Sektion hinzu
     * Dokumentiere Cloud Logging Integration
     * Dokumentiere Cloud Monitoring Metrics
     * Dokumentiere Cloud Trace für Distributed Tracing
     * Zeige Log-Analyse-Beispiele

   - **docs/guides/BODY_TRANSFORMATION.md** (falls unterstützt):
     * Füge "### GCP API Gateway" Sektion hinzu ODER
     * Dokumentiere "Nicht unterstützt - nutze Backend-Transformation"

   - **docs/guides/CIRCUIT_BREAKER.md** (falls unterstützt):
     * Füge "### GCP API Gateway" Sektion hinzu ODER
     * Dokumentiere "Nicht nativ unterstützt - nutze Backend Circuit Breaker"

   - **docs/guides/HEALTH_CHECKS.md** (falls unterstützt):
     * Füge "### GCP API Gateway" Sektion hinzu
     * Dokumentiere Backend Health Checks (falls unterstützt)
     * Oder: Dokumentiere Cloud Load Balancer Health Checks

   - **docs/guides/GRPC_TRANSFORMATIONS.md** (falls unterstützt):
     * Füge "### GCP API Gateway" Sektion hinzu
     * Dokumentiere gRPC-JSON Transcoding (falls unterstützt)

   - **docs/guides/WEBSOCKET.md** (falls unterstützt):
     * Füge "### GCP API Gateway" Sektion hinzu
     * Dokumentiere WebSocket-Support (falls unterstützt)

   **Für jeden Guide:**
   - Suche nach "## Provider-spezifische Implementierungen"
   - Füge neue "### [Provider-Name]" Sektion hinzu
   - Format: Beschreibung → Features → Generiertes Config-Beispiel → Deployment
   - Sortierung: Alphabetisch ODER nach Reihenfolge der bestehenden Provider

14. **docs/import/migration.md**:
   - Provider zur Migration-Matrix hinzufügen
   - Migration-Pfade dokumentieren (Provider → GAL → andere Provider)

15. **docs/import/compatibility.md**:
   - Provider zur Kompatibilitäts-Matrix hinzufügen
   - Feature-Support-Level dokumentieren

16. **docs/api/CLI_REFERENCE.md**:
   - Provider zu CLI-Beispielen hinzufügen
   - generate, validate, import, migrate Beispiele mit neuem Provider

17. **Tests** (`tests/test_<provider>.py` + `tests/test_import_<provider>.py`):
   - Vollständige Test-Suite für Provider (Export)
   - Import-Tests (falls Import unterstützt)
   - Alle Features testen
   - Edge-Cases testen

18. **ROADMAP.md**:
   - Provider zur Liste hinzufügen
   - Feature-Matrix aktualisieren

19. **vx.x.x-PLAN.md** (falls Teil von v1.X.0):
   - Provider-Feature als Done markieren
   - Implementation Details dokumentieren (Dateien, Zeilen, Tests, Coverage)
   - Dokumentations-Statistiken (Zeilen, Diagramme)

20. **CHANGELOG.md**:
   - Unter "Added" eintragen mit allen Details:
     - Provider-Klasse (Zeilen, Coverage)
     - Parser-Klasse (falls vorhanden)
     - Dokumentation (Zeilen)
     - Tests (Anzahl, Coverage)
     - Beispiele

**Checkliste für neuen Provider:**
```
□ Provider-Klasse mit Docstrings
□ Parser-Klasse mit Docstrings (falls Import)
□ Config-Modelle dokumentiert
□ CLI-Integration (alle Commands)
□ README.md: Provider-Anzahl & Feature-Matrix
□ docs/index.md: Provider-Anzahl & Tabelle
□ docs/guides/PROVIDERS.md: Vollständiger Provider-Abschnitt
□ docs/guides/<PROVIDER>.md: Umfassender Guide (1000+ Zeilen)
□ docs/import/<provider>.md: Import-Guide (falls Import)
□ examples/<provider>-example.yaml: 5-15 Szenarien
□ mkdocs.yml: Navigation (Features + Import)
□ ALLE Feature-Guides: Provider-Beispiele hinzugefügt
□ docs/import/migration.md: Migration-Matrix
□ docs/import/compatibility.md: Kompatibilitäts-Matrix
□ docs/api/CLI_REFERENCE.md: CLI-Beispiele
□ Tests: test_<provider>.py (Export)
□ Tests: test_import_<provider>.py (Import)
□ ROADMAP.md: Provider hinzugefügt
□ vx.x.x-PLAN.md: Feature als Done markiert
□ CHANGELOG.md: Added-Sektion
```

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
