# Checklist: Neues Feature

Diese Checkliste umfasst **alle 10+ Schritte**, die beim Hinzufügen eines neuen Features notwendig sind.

## 1. Code-Implementierung

### 1.1 Config-Modelle (gal/config.py)
- [ ] Neue Dataclasses für Feature erstellen
- [ ] Vollständige Docstrings hinzufügen
- [ ] Alle Attribute dokumentieren
- [ ] Beispiele in Docstrings

**Beispiel:**
```python
@dataclass
class HealthCheckConfig:
    """Health check configuration for upstream targets.

    Attributes:
        active: Active health check configuration (periodic probing)
        passive: Passive health check configuration (traffic monitoring)

    Example:
        >>> hc = HealthCheckConfig(
        ...     active=ActiveHealthCheck(enabled=True, interval=5)
        ... )
    """
    active: Optional[ActiveHealthCheck] = None
    passive: Optional[PassiveHealthCheck] = None
```

### 1.2 Provider-Implementierung (gal/providers/*.py)
- [ ] Feature in alle Provider implementieren (oder markiere als "nicht unterstützt")
- [ ] Docstrings für neue Provider-Methoden
- [ ] Provider-spezifische Limitierungen dokumentieren

**Provider die aktualisiert werden müssen:**
- [ ] Envoy (`gal/providers/envoy.py`)
- [ ] Nginx (`gal/providers/nginx.py`)
- [ ] Kong (`gal/providers/kong.py`)
- [ ] APISIX (`gal/providers/apisix.py`)
- [ ] Traefik (`gal/providers/traefik.py`)
- [ ] HAProxy (`gal/providers/haproxy.py`)
- [ ] Azure API Management (`gal/providers/azure_apim.py`)
- [ ] AWS API Gateway (`gal/providers/aws_apigateway.py`)
- [ ] GCP API Gateway (`gal/providers/gcp_apigateway.py`)

---

## 2. Feature-Guide (docs/guides/<FEATURE>.md)

Erstelle vollständigen Guide auf Deutsch (800-1500 Zeilen):

### 2.1 Struktur
- [ ] **Übersicht**: Was ist das Feature, warum nutzen?
- [ ] **Schnellstart**: 1-2 einfache Beispiele
- [ ] **Konfigurationsoptionen**: Alle Config-Parameter dokumentiert
- [ ] **Provider-Implementierung**: Wie jeder Provider das Feature umsetzt (9 Provider!)
- [ ] **Häufige Anwendungsfälle**: 5-10 Beispiele
- [ ] **Best Practices**: Empfehlungen
- [ ] **Troubleshooting**: Häufige Probleme und Lösungen

### 2.2 Provider-Implementierungen (9 Sektionen!)

Für **jeden Provider** eine Sektion:

```markdown
## Provider-spezifische Implementierungen

### Envoy
[Feature] wird in Envoy mit [Mechanismus] implementiert.

**[Feature-Details]:**
- Mechanismus: [envoy.filters.http.* / etc.]
- Features: [Spezifische Features]
- Hinweis: [Limitierungen]

**Generiertes Config-Beispiel:**
```yaml
# Envoy config
```

**Deployment:**
```bash
# Deployment-Befehle
```

### Nginx
[Feature] wird in Nginx mit [Mechanismus] implementiert.
...

[Wiederholen für alle 9 Provider]
```

**Provider:**
- [ ] Envoy
- [ ] Nginx
- [ ] Kong
- [ ] APISIX
- [ ] Traefik
- [ ] HAProxy
- [ ] Azure API Management
- [ ] AWS API Gateway
- [ ] GCP API Gateway

---

## 3. Beispiel-Konfigurationen (examples/)

### 3.1 examples/<feature>-example.yaml
- [ ] 10-15 realistische Szenarien
- [ ] Jedes Szenario mit Kommentaren die den Use-Case erklären
- [ ] Vollständige lauffähiger Config
- [ ] Provider-spezifischen Hinweisen

**Format:**
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

---

## 4. Tests (tests/test_<feature>.py)

### 4.1 Test-Suite erstellen
- [ ] Tests für alle Provider (9 Provider)
- [ ] Config-Modell-Validierung testen
- [ ] Edge-Cases testen
- [ ] Error-Handling testen

**Mindestens:**
- [ ] Test: Feature aktiviert/deaktiviert
- [ ] Test: Alle Config-Parameter
- [ ] Test: Provider-spezifische Generierung
- [ ] Test: Validierung (falsche Werte)

---

## 5. Dokumentation aktualisieren

### 5.1 README.md
- [ ] Feature zur Feature-Liste hinzufügen (mit ✅ oder 🚧)
- [ ] Verwendungs-Beispiel zur Usage-Sektion hinzufügen
- [ ] Provider-Kompatibilitäts-Matrix aktualisieren

### 5.2 docs/README.md
- [ ] Feature-Guide zur Guides-Tabelle hinzufügen

### 5.3 docs/index.md (MkDocs Landing Page)
- [ ] Feature zu Features-Sektion hinzufügen
- [ ] Feature-Tabelle aktualisieren
- [ ] Feature-Links hinzufügen

### 5.4 mkdocs.yml
- [ ] Feature-Guide zur Navigation hinzufügen unter `Features:`
- [ ] Alphabetische Sortierung innerhalb der Kategorie

**Beispiel:**
```yaml
nav:
  - Features:
    - Authentication: guides/AUTHENTICATION.md
    - CORS: guides/CORS.md
    - Health Checks: guides/HEALTH_CHECKS.md  # ← Neu
    - Rate Limiting: guides/RATE_LIMITING.md
```

---

## 6. ROADMAP & CHANGELOG

### 6.1 ROADMAP.md (falls Teil von v1.X.0)
- [ ] Feature als Done markieren (✅)
- [ ] Progress-Prozentsatz aktualisieren
- [ ] Implementation-Details hinzufügen
- [ ] "Last Updated" Datum aktualisieren

### 6.2 vx.x.x-PLAN.md (falls Teil von v1.X.0)
- [ ] Feature-Status aktualisieren (Pending → In Progress → Done)
- [ ] Progress-Prozentsatz aktualisieren
- [ ] Implementation Details hinzufügen:
  - Commits
  - Dateien (Code, Tests, Docs)
  - Test-Ergebnisse
  - Coverage
- [ ] Milestone als erledigt markieren

### 6.3 CHANGELOG.md
- [ ] Unter "Unreleased" → "Added" eintragen
- [ ] Feature-Beschreibung
- [ ] Provider-Kompatibilität erwähnen

**Beispiel:**
```markdown
## [Unreleased]

### Added
- Health Checks & Load Balancing support für alle Provider
- Neue Config-Modelle: `HealthCheckConfig`, `LoadBalancerConfig`
- Beispiel-Konfigurationen in `examples/health-checks-example.yaml`
- Vollständiger Feature-Guide in `docs/guides/HEALTH_CHECKS.md`
- Provider-Support: Envoy, Nginx, Kong, APISIX, Traefik, HAProxy, Azure APIM, AWS API Gateway, GCP API Gateway
```

---

## 7. Validierung vor Abschluss

### 7.1 Code Quality
- [ ] Black Formatierung: `black --check .`
- [ ] Import Sortierung: `isort --check-only .`
- [ ] Linting: `flake8 .`

### 7.2 Tests
- [ ] Alle Tests bestehen: `pytest -v`
- [ ] Coverage prüfen: `pytest --cov=gal --cov-report=term`

### 7.3 Config-Examples
- [ ] Alle YAML-Beispiele testen: `python gal-cli.py generate examples/<feature>-example.yaml`

### 7.4 MkDocs
- [ ] Dokumentation bauen: `mkdocs build --strict`
- [ ] Lokal testen: `mkdocs serve`
- [ ] Alle Links prüfen (interne Verweise)

### 7.5 GitHub Pages
- [ ] Nach Push: GitHub Actions Workflow überwachen
- [ ] Deployment auf https://pt9912.github.io/x-gal/ verifizieren
- [ ] Navigation und Suchfunktion testen

---

## Statistiken für Abschluss

Nach Fertigstellung, dokumentiere:

- **Code:**
  - Config-Modelle: XXX Zeilen
  - Provider-Implementierungen: XXX Zeilen (9 Provider)
  - Test Coverage: XX%

- **Dokumentation:**
  - Feature-Guide: XXX Zeilen (auf Deutsch)
  - Provider-Sektionen: 9 (alle Provider dokumentiert)
  - Beispiele: XX Szenarien

- **Tests:**
  - Unit Tests: XXX Tests
  - Provider-Tests: XX Tests pro Provider
  - Coverage: XX%

---

## Breaking Changes (falls vorhanden)

Falls das Feature Breaking Changes einführt:

- [ ] **Migration-Guide** erstellen
- [ ] Alte vs. neue Config dokumentieren
- [ ] Migration-Beispiele geben
- [ ] Konvertierungs-Script erstellen (falls sinnvoll)
- [ ] **README.md** Breaking Changes Sektion hinzufügen
- [ ] **CHANGELOG.md** unter "Changed" mit **BREAKING** Prefix
- [ ] Alle Beispiele in `examples/` aktualisieren
- [ ] Alte Config-Tests entfernen/anpassen
