---
name: documentation
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

## Hauptszenarien

### Szenario 1: Neues Feature hinzugefügt

**Siehe:** [FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md) für vollständige Checkliste (10+ Schritte)

**Quick Summary:**
1. **Config-Modelle** mit Docstrings (`gal/config.py`)
2. **Provider-Implementierung** für alle 9 Provider (`gal/providers/*.py`)
3. **Feature-Guide** erstellen (`docs/guides/<FEATURE>.md`, 800-1500 Zeilen, Deutsch)
4. **Beispiele** (`examples/<feature>-example.yaml`, 10-15 Szenarien)
5. **Tests** (`tests/test_<feature>.py`)
6. **README.md** + **docs/index.md** + **mkdocs.yml** aktualisieren
7. **ROADMAP.md** + **vx.x.x-PLAN.md** + **CHANGELOG.md** aktualisieren

**Feature-Guide Struktur:**
- Übersicht & Schnellstart
- Konfigurationsoptionen (alle Parameter)
- **Provider-Implementierungen** (9 Provider: Envoy, Nginx, Kong, APISIX, Traefik, HAProxy, Azure APIM, AWS, GCP)
- Häufige Anwendungsfälle (5-10 Beispiele)
- Best Practices & Troubleshooting

### Szenario 2: Neuer Provider hinzugefügt

**Siehe:** [PROVIDER_CHECKLIST.md](PROVIDER_CHECKLIST.md) für vollständige Checkliste (20+ Schritte)

**Quick Summary:**
1. **Provider-Klasse** + **Parser-Klasse** mit Docstrings
2. **Config-Modelle** dokumentieren
3. **CLI-Integration** (`gal-cli.py`)
4. **README.md** + **docs/index.md** + **docs/README.md** (Provider-Anzahl aktualisieren)
5. **docs/guides/PROVIDERS.md** - Vollständiger Provider-Abschnitt
6. **Provider-Guide** (`docs/guides/<PROVIDER>.md`, 1000+ Zeilen, Deutsch)
7. **Import-Guide** (`docs/import/<provider>.md`, falls Import unterstützt)
8. **Beispiele** (`examples/<provider>-example.yaml`, 5-15 Szenarien)
9. **mkdocs.yml** - 2 Stellen aktualisieren (Features + Import)
10. **ALLE Feature-Guides aktualisieren** - Provider-Beispiele für JEDES Feature hinzufügen!
11. **Migration & Kompatibilität** (`docs/import/migration.md`, `compatibility.md`)
12. **Tests** (`test_<provider>.py` + `test_import_<provider>.py`)

**Wichtig:**
- **Mermaid-Diagramme**: 4 Diagramme pro Provider (Architektur, Request Flow, Deployment, Migration)
- **Siehe:** [MERMAID_GUIDE.md](MERMAID_GUIDE.md) für Details

**Provider-Guide Struktur (1000+ Zeilen):**
- Übersicht & Architektur
- **4 Mermaid-Diagramme** (siehe MERMAID_GUIDE.md)
- Schnellstart
- Konfigurationsoptionen
- Provider-spezifische Features
- Deployment-Strategien
- Import/Export (falls unterstützt)
- Authentication/Authorization
- CORS Configuration
- Multi-Region/Multi-Zone (falls Cloud-Provider)
- Migration von/zu anderen Providern
- Best Practices & Troubleshooting
- Performance & Limits
- Security Best Practices

**Feature-Guides die aktualisiert werden müssen (11 Guides):**
- AUTHENTICATION.md
- CORS.md
- RATE_LIMITING.md
- HEADERS.md
- TIMEOUT_RETRY.md
- LOGGING_OBSERVABILITY.md
- BODY_TRANSFORMATION.md
- CIRCUIT_BREAKER.md
- HEALTH_CHECKS.md
- GRPC_TRANSFORMATIONS.md
- WEBSOCKET.md

### Szenario 3: Provider-Erweiterung (Feature zu existierendem Provider)

1. **Provider-Code** dokumentieren (Docstrings für neue Methoden)
2. **Feature-Guide** aktualisieren (Provider-Implementierung-Sektion erweitern)
3. **Tests** erweitern (Provider-spezifische Tests)
4. **CHANGELOG.md** unter "Changed" oder "Added"

### Szenario 4: Config Breaking Change

1. **Migration-Guide** erstellen (alte vs. neue Config, Beispiele)
2. **README.md**: Breaking Changes Sektion hinzufügen
3. **CHANGELOG.md**: Unter "Changed" mit **BREAKING** Prefix
4. **Alle Beispiele** in `examples/` aktualisieren
5. **Tests** aktualisieren (alte Config-Tests entfernen/anpassen)

## Python Docstrings Best Practices

Verwende Google-Style Docstrings (wie im Projekt üblich):

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

## Beispiel-Konfigurationen Format

```yaml
# ===========================================================================
# Example X: <Use-Case Name>
# ===========================================================================
# Use Case: <Beschreibung>
# Features: <Was wird demonstriert>
# Providers: <Welche Provider unterstützen dies>
# ===========================================================================
services:
  - name: example_service
    # ...
```

## Validierung vor Abschluss

Nach jedem Dokumentations-Update:

### 1. Code Quality
```bash
black --check .
isort --check-only .
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

### 2. Tests
```bash
pytest -v
pytest --cov=gal --cov-report=term
```

### 3. Config-Examples
```bash
python gal-cli.py generate examples/<example>.yaml
```

### 4. MkDocs
```bash
mkdocs build --strict  # Strict mode - zeigt broken links
mkdocs serve           # Lokal testen auf http://127.0.0.1:8000
```

### 5. GitHub Pages
- Nach Push: GitHub Actions Workflow überwachen
- Deployment auf https://pt9912.github.io/x-gal/ verifizieren
- Navigation und Suchfunktion testen

## Integration mit anderen Skills

- **Release Skill**: Dokumentation muss vor Release komplett sein
- **Actions Monitor**: Nach Docs-Update GitHub Actions überwachen

## Fehlerbehandlung

- Falls Docstrings fehlen: Google-Style Docstrings hinzufügen
- Falls Beispiele nicht funktionieren: Config-Syntax prüfen, Provider testen
- Falls Links broken: Dateipfade und relative Pfade prüfen
- Falls Tests fehlschlagen: Docs mit Code synchronisieren

## Tools

- **Read**: Existierende Dokumentation lesen
- **Write/Edit**: Dokumentation aktualisieren
- **Bash**: `pytest`, `python gal-cli.py`, `mkdocs` ausführen
- **TodoWrite**: Dokumentations-Checkliste tracken
- **Glob**: Dokumentationsdateien finden
- **Task (mermaid-expert)**: Für professionelle Mermaid-Diagramme

## Best Practices

1. **Immer YAML-Beispiele hinzufügen**: Praktische Configs > theoretische Beschreibungen
2. **User-First**: Aus Gateway-Admin-Perspektive schreiben
3. **Provider-Kompatibilität klar machen**: Immer dokumentieren, welche Provider ein Feature unterstützen
4. **Deutsche Dokumentation**: Alle Guides auf Deutsch (außer Code und YAML)
5. **Up-to-date**: Dokumentation gleichzeitig mit Code aktualisieren, nicht später
6. **Test Examples**: Alle YAML-Beispiele müssen generierbar sein
7. **Real-World Use-Cases**: Beispiele sollen echte Produktions-Szenarien zeigen
8. **Mermaid-Diagramme für neue Provider**: 4 Diagramme (siehe MERMAID_GUIDE.md)

## Output-Format

Nach Dokumentations-Update zeige Zusammenfassung:

```
📚 Dokumentation aktualisiert:

✅ Python Docstrings:
  - HealthCheckConfig Dataclass vollständig dokumentiert
  - APISIXProvider._generate_upstream() Methode dokumentiert

✅ Feature-Guide:
  - docs/guides/HEALTH_CHECKS.md erstellt (1000+ Zeilen, Deutsch)
  - Alle Provider-Implementierungen dokumentiert (9 Provider)
  - 15+ Use-Cases mit Beispielen

✅ Beispiele:
  - examples/health-checks-example.yaml erstellt
  - 15 Szenarien (Basic HC, Canary, Blue-Green, Multi-DC, etc.)

✅ README.md + docs/index.md + mkdocs.yml:
  - Health Checks zur Feature-Liste hinzugefügt
  - Navigation aktualisiert

✅ ROADMAP.md + vx.x.x-PLAN.md:
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

## Wartung

Aktualisiere diesen Skill, wenn:
- Neue Provider-Typen hinzukommen
- Dokumentations-Struktur geändert wird
- Neue Dokumentations-Tools eingeführt werden (z.B. neue MkDocs-Plugins)
- Best Practices für Dokumentation ändern

---

**Version:** 2.0.0 (Progressive Disclosure)
**Status:** ✅ Production Ready
**Letzte Aktualisierung:** 2025-10-23

## Changelog

**Version 2.0.0** (2025-10-23)
- ✅ Progressive Disclosure implementiert (752 → ~400 Zeilen)
- ✅ Checklisten ausgelagert:
  - MERMAID_GUIDE.md (Mermaid-Diagramm Best Practices)
  - PROVIDER_CHECKLIST.md (20+ Schritte für neue Provider)
  - FEATURE_CHECKLIST.md (10+ Schritte für neue Features)
- ✅ Quick Summaries für Hauptszenarien
- ✅ Fokus auf Projekt-spezifische Details
- ✅ Best Practices gemäß https://docs.claude.com/de/docs/agents-and-tools/agent-skills/best-practices

**Version 1.0.0** (2025-10-18)
- Initial Release mit vollständiger Dokumentations-Verwaltung
