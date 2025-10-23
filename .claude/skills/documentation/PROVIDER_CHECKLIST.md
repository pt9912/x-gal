# Checklist: Neuer Provider

Diese Checkliste umfasst **alle 20+ Schritte**, die beim Hinzufügen eines neuen Providers notwendig sind.

## 1. Code-Implementierung

### 1.1 Provider-Klasse
- [ ] `gal/providers/<provider>.py` erstellen
- [ ] Vollständige Docstrings für Klasse und alle Methoden
- [ ] `parse()` und `generate()` Methoden dokumentieren
- [ ] Provider-spezifische Besonderheiten dokumentieren

### 1.2 Parser-Klasse (falls Import unterstützt)
- [ ] `gal/parsers/<provider>_parser.py` erstellen
- [ ] Vollständige Docstrings für Parser-Klasse
- [ ] Import-Format dokumentieren (OpenAPI, Terraform, etc.)
- [ ] Limitierungen beim Import dokumentieren

### 1.3 Config-Modelle
- [ ] Provider-spezifische Config-Klasse in `gal/config.py` (z.B. `GCPAPIGatewayConfig`)
- [ ] Alle Parameter mit Docstrings versehen
- [ ] Beispiele in Docstrings

### 1.4 CLI-Integration
- [ ] Provider in `gal-cli.py` registrieren (generate, validate, import, etc.)
- [ ] CLI-Verwendung dokumentieren

---

## 2. Basis-Dokumentation

### 2.1 README.md
- [ ] Provider-Anzahl aktualisieren ("7 Provider" → "9 Provider")
- [ ] Provider zur unterstützten Liste hinzufügen
- [ ] Feature-Matrix für neuen Provider erstellen
- [ ] Installation/Setup-Hinweise

### 2.2 docs/index.md (MkDocs Landing Page)
- [ ] Provider-Anzahl aktualisieren
- [ ] Provider zur Provider-Tabelle hinzufügen
- [ ] Provider-Guide zu Features-Links hinzufügen

### 2.3 docs/README.md
- [ ] Provider zur Guides-Tabelle hinzufügen
- [ ] Provider zur unterstützten Provider-Tabelle hinzufügen

---

## 3. Provider-Übersicht (docs/guides/PROVIDERS.md)

**SEHR WICHTIG!** Vollständiger Provider-Abschnitt mit:

- [ ] Übersicht & Stärken
- [ ] Ideale Use-Cases
- [ ] GAL-Generierung (Output-Format & Struktur)
- [ ] Transformationen (wie Provider Transformationen handhabt)
- [ ] gRPC-Support (falls vorhanden)
- [ ] Authentifizierung
- [ ] Rate Limiting
- [ ] Circuit Breaker (falls unterstützt)
- [ ] Health Checks
- [ ] Deployment-Befehle
- [ ] Monitoring & Observability
- [ ] Best Practices

---

## 4. Provider-spezifischer Guide (docs/guides/<PROVIDER>.md)

Umfassender Guide (1000+ Zeilen auf Deutsch!):

- [ ] Übersicht & Architektur
- [ ] Schnellstart
- [ ] Konfigurationsoptionen (alle Parameter)
- [ ] Provider-spezifische Features
- [ ] Deployment-Strategien
- [ ] Import/Export (falls unterstützt)
- [ ] Authentication/Authorization
- [ ] CORS Configuration
- [ ] Multi-Region/Multi-Zone (falls Cloud-Provider)
- [ ] Migration von/zu anderen Providern
- [ ] Best Practices
- [ ] Troubleshooting
- [ ] Performance & Limits
- [ ] Security Best Practices

### 4.1 Mermaid-Diagramme (4 Diagramme)

Siehe [MERMAID_GUIDE.md](MERMAID_GUIDE.md) für Details:

- [ ] **Architektur-Diagramm** (Graph TB): Client → Gateway → Backend
- [ ] **Request Flow Sequenzdiagramm**: Schritt-für-Schritt Request Processing
- [ ] **Deployment-Flowchart** (Flowchart TD): 3-5 Deployment-Szenarien
- [ ] **Migration-Flow** (Flowchart LR): Provider → GAL → andere Provider

---

## 5. Import-Guide (falls Import unterstützt)

### 5.1 docs/import/<provider>.md
- [ ] Import-Prozess dokumentieren
- [ ] Feature-Support-Matrix (was wird beim Import unterstützt)
- [ ] Import-Beispiele (Basic, JWT, CORS, etc.)
- [ ] Migration-Guides (zu/von anderen Providern)
- [ ] Limitierungen und Workarounds
- [ ] Troubleshooting

---

## 6. Alle Feature-Guides aktualisieren

**KRITISCH & ZEITAUFWÄNDIG!** Jeder Feature-Guide braucht eine neue Provider-Sektion!

### Format der Provider-Sektion:
```markdown
## Provider-spezifische Implementierungen

### [Bestehende Provider...]

### [NEUER PROVIDER]

[Provider] implementiert [Feature] mit [Mechanismus].

**[Feature-Typ]:**
- Mechanismus: [Extension / Config-Format]
- Features: [Spezifische Features]
- Hinweis: [Provider-spezifische Limitierungen]

**Generiertes Config-Beispiel:**
```yaml
# Config-Beispiel
```

**Deployment:**
```bash
# Deployment-Befehle
```
```

### Feature-Guides die aktualisiert werden müssen:

- [ ] **docs/guides/AUTHENTICATION.md**: JWT, API Keys, OAuth
- [ ] **docs/guides/CORS.md**: OPTIONS Methods, Access-Control-* Headers
- [ ] **docs/guides/RATE_LIMITING.md**: Quotas, Throttling
- [ ] **docs/guides/HEADERS.md**: X-Forwarded-*, Custom Headers
- [ ] **docs/guides/TIMEOUT_RETRY.md**: Timeouts, Retry-Strategien
- [ ] **docs/guides/LOGGING_OBSERVABILITY.md**: Logging, Metrics, Tracing
- [ ] **docs/guides/BODY_TRANSFORMATION.md** (falls unterstützt)
- [ ] **docs/guides/CIRCUIT_BREAKER.md** (falls unterstützt)
- [ ] **docs/guides/HEALTH_CHECKS.md** (falls unterstützt)
- [ ] **docs/guides/GRPC_TRANSFORMATIONS.md** (falls unterstützt)
- [ ] **docs/guides/WEBSOCKET.md** (falls unterstützt)

---

## 7. Migration & Kompatibilität

### 7.1 docs/import/migration.md
- [ ] Provider zur Migration-Matrix hinzufügen
- [ ] Migration-Pfade dokumentieren (Provider → GAL → andere Provider)

### 7.2 docs/import/compatibility.md
- [ ] Provider zur Kompatibilitäts-Matrix hinzufügen
- [ ] Feature-Support-Level dokumentieren

---

## 8. API-Referenz

### 8.1 docs/api/CLI_REFERENCE.md
- [ ] Provider zu CLI-Beispielen hinzufügen
- [ ] generate, validate, import, migrate Beispiele mit neuem Provider

---

## 9. Beispiel-Konfigurationen

### 9.1 examples/<provider>-example.yaml
- [ ] 5-15 realistische Szenarien
- [ ] Provider-spezifische Features zeigen
- [ ] Jedes Szenario mit Kommentaren
- [ ] Deployment-Anweisungen

---

## 10. Navigation (mkdocs.yml)

**2 Stellen aktualisieren!**

- [ ] Provider-Guide zur Navigation unter `Features:` hinzufügen
- [ ] Import-Guide zur Navigation unter `Config Import & Migration:` hinzufügen (falls Import unterstützt)

---

## 11. Tests

### 11.1 tests/test_<provider>.py
- [ ] Vollständige Test-Suite für Provider (Export)
- [ ] Alle Features testen
- [ ] Edge-Cases testen

### 11.2 tests/test_import_<provider>.py (falls Import)
- [ ] Import-Tests
- [ ] Feature-Support-Tests
- [ ] Error-Handling-Tests

---

## 12. ROADMAP & CHANGELOG

### 12.1 ROADMAP.md
- [ ] Provider zur Liste hinzufügen
- [ ] Feature-Matrix aktualisieren

### 12.2 vx.x.x-PLAN.md (falls Teil von v1.X.0)
- [ ] Provider-Feature als Done markieren
- [ ] Implementation Details dokumentieren (Dateien, Zeilen, Tests, Coverage)
- [ ] Dokumentations-Statistiken (Zeilen, Diagramme)

### 12.3 CHANGELOG.md
- [ ] Unter "Added" eintragen mit allen Details:
  - Provider-Klasse (Zeilen, Coverage)
  - Parser-Klasse (falls vorhanden)
  - Dokumentation (Zeilen)
  - Tests (Anzahl, Coverage)
  - Beispiele

---

## Statistiken für Abschluss

Nach Fertigstellung, dokumentiere:

- **Code:**
  - Provider-Klasse: XXX Zeilen
  - Parser-Klasse: XXX Zeilen (falls vorhanden)
  - Config-Modelle: XX Zeilen
  - Test Coverage: XX%

- **Dokumentation:**
  - Provider-Guide: XXX Zeilen
  - Import-Guide: XXX Zeilen (falls vorhanden)
  - Feature-Guides aktualisiert: XX Guides
  - Mermaid-Diagramme: 4 (Architektur, Request Flow, Deployment, Migration)
  - Beispiele: XX Szenarien

- **Tests:**
  - Unit Tests: XXX Tests
  - Import Tests: XXX Tests (falls vorhanden)
  - Coverage: XX%

---

## Validierung vor Abschluss

- [ ] Alle Beispiele testen: `python gal-cli.py generate examples/<provider>-example.yaml`
- [ ] Tests ausführen: `pytest tests/test_<provider>.py -v`
- [ ] MkDocs bauen: `mkdocs build --strict`
- [ ] MkDocs lokal testen: `mkdocs serve`
- [ ] Alle Links prüfen (interne Verweise)
- [ ] GitHub Pages Deployment nach Push überwachen
