# Migration Assistant

**Status:** ✅ Abgeschlossen
**Release:** v1.3.0
**Tests:** 31/31 bestanden (100%)

## Übersicht

Der Migration Assistant ist ein **interaktiver CLI-Befehl**, der Nutzer durch den kompletten Migrations-Prozess von einem Provider zu einem anderen führt. Er kombiniert Import, Compatibility Check und Export in einem automatisierten Workflow mit detailliertem Migration Report.

## Use Cases

1. **Guided Migration**: Nginx → HAProxy Migration mit Anleitung
2. **Risk Assessment**: Zeige Risiken und Inkompatibilitäten vor Migration
3. **Rollback Plan**: Generiere Rollback-Dokumentation
4. **Documentation**: Erstelle Migration Report für Team

## CLI Command

### Syntax

```bash
gal migrate [OPTIONS]
```

### Optionen

| Option | Kurzform | Beschreibung | Erforderlich |
|--------|----------|--------------|--------------|
| `--source-provider` | `-s` | Source Provider (envoy, kong, apisix, traefik, nginx, haproxy) | Nein* |
| `--source-config` | `-i` | Pfad zur Source Config-Datei | Nein* |
| `--target-provider` | `-t` | Target Provider | Nein* |
| `--output-dir` | `-o` | Output-Verzeichnis für generierte Dateien | Nein* |
| `--yes` | `-y` | Bestätigung überspringen (nicht-interaktiv) | Nein |

\* *Wenn nicht angegeben, startet der interaktive Modus mit Prompts*

### Verwendung

**Vollständig interaktiver Modus:**
```bash
gal migrate
# → Prompts für alle Parameter
```

**Nicht-interaktiver Modus:**
```bash
gal migrate \
  --source-provider kong \
  --source-config examples/kong.yaml \
  --target-provider envoy \
  --output-dir ./migration \
  --yes
```

**Gemischter Modus:**
```bash
# Nur Source angeben, Rest interaktiv
gal migrate --source-provider nginx --source-config nginx.conf
```

## Funktionsweise

Der `gal migrate` Befehl führt folgende Schritte aus:

### 5-Schritte Migration Workflow

1. **[1/5] 📖 Reading Source Config** - Liest die Source Provider Konfiguration
2. **[2/5] 🔍 Parsing and Analyzing** - Parst die Config und extrahiert Services/Routes
3. **[3/5] 🔄 Converting to GAL Format** - Konvertiert zu GAL Config (gal-config.yaml)
4. **[4/5] ✅ Validating Compatibility** - Prüft Kompatibilität mit Target Provider
5. **[5/5] 🎯 Generating Target Config** - Generiert Target Provider Config

### Generierte Dateien

Der Befehl erstellt 3 Dateien im Output-Verzeichnis:

```
<output-dir>/
├── gal-config.yaml         # GAL-Format Config (provider-agnostisch)
├── <target>.<ext>          # Target Provider Config (envoy.yaml, kong.yaml, nginx.conf, etc.)
└── migration-report.md     # Detaillierter Migration Report
```

**Beispiel Output:**
```
migration/
├── gal-config.yaml         # GAL format
├── envoy.yaml              # Envoy config
└── migration-report.md     # Report
```

## Workflow-Beispiel

### Nicht-interaktiver Modus (empfohlen)

```bash
$ gal migrate \
    --source-provider kong \
    --source-config examples/kong.yaml \
    --target-provider envoy \
    --output-dir ./migration \
    --yes

================================================================================
🔀 GAL Migration Assistant
================================================================================


Migration Plan:
  Source: kong (examples/kong.yaml)
  Target: envoy
  Output: ./migration


[1/5] 📖 Reading Kong config...
   ✓ Config file read successfully
[2/5] 🔍 Parsing and analyzing...
   ✓ Parsed 5 services
   ✓ Found 0 routes
[3/5] 🔄 Converting to GAL format...
   ✓ GAL config saved: migration/gal-config.yaml
[4/5] ✅ Validating compatibility with Envoy...
   ✓ Compatibility: 100.0% (1/1 features)
[5/5] 🎯 Generating Envoy config...
   ✓ Envoy config saved: migration/envoy.yaml

📄 Generating migration report...
   ✓ Migration report saved: migration/migration-report.md

================================================================================
✅ Migration complete!
================================================================================

Files created:
  📄 migration/gal-config.yaml (GAL format)
  📄 migration/envoy.yaml (Envoy config)
  📄 migration/migration-report.md (Migration report)

Compatibility: 100.0% (1/1 features)

Next steps:
  1. Review migration-report.md
  2. Test envoy.yaml in staging
  3. Deploy to production
```

### Interaktiver Modus

Wenn Sie `gal migrate` ohne Parameter aufrufen, werden Sie interaktiv nach allen Parametern gefragt:

```bash
$ gal migrate

================================================================================
🔀 GAL Migration Assistant
================================================================================

Source Provider [envoy/kong/apisix/traefik/nginx/haproxy]: kong
Source Configuration File: examples/kong.yaml
Target Provider [envoy/kong/apisix/traefik/nginx/haproxy]: envoy
Output Directory [./migration]:

Migration Plan:
  Source: kong (examples/kong.yaml)
  Target: envoy
  Output: ./migration

Proceed with migration? [Y/n]: y

[1/5] 📖 Reading Kong config...
...
```

## Migration Report Format

Der generierte `migration-report.md` enthält folgende Sektionen:

```markdown
# Migration Report: Kong → Envoy

**Date:** 2025-10-19 10:41:08
**Source:** examples/output/kong.yaml (Kong)
**Target:** Envoy

## Summary

- **Compatibility:** 100.0% (1/1 features)
- **Services Migrated:** 5
- **Routes Migrated:** 0
- **Warnings:** 0

## Features Status

### ✅ Fully Supported Features

- **load_balancing_round_robin:** ✅ Load Balancing (Round Robin) fully supported

## Services

### user_service

- **Type:** rest
- **Protocol:** http
- **Upstream:** :0
- **Routes:** 0
- **Load Balancer:** round_robin

(... weitere Services ...)

## Testing Checklist

- [ ] Test in staging environment
- [ ] Verify all 0 routes
- [ ] Check load balancing distribution
- [ ] Validate health check behavior
- [ ] Monitor backend connectivity
- [ ] Performance comparison

## Next Steps

1. ✅ Review this report
2. ⏳ Test in staging environment
3. ⏳ Deploy to production
4. ⏳ Monitor and validate
```

Der Report ist **vollständig automatisch generiert** und enthält:

- **Summary**: Compatibility Score, Services, Routes, Warnings
- **Features Status**: Vollständig unterstützte, teilweise unterstützte und nicht unterstützte Features
- **Services**: Detaillierte Informationen zu jedem migrierten Service
- **Testing Checklist**: Markdown-Checkliste für Migration Testing
- **Next Steps**: Empfohlene Schritte nach der Migration

## Test Coverage

**Tests:** 31/31 bestanden (100%)

**Test-Kategorien:**

1. **TestMigrateBasic** (7 tests)
   - Kong → Envoy, Envoy → Kong, Traefik → Nginx Migrationen
   - Output-Verzeichnis Erstellung
   - Progress Steps Anzeige
   - Summary Display

2. **TestMigrateFileGeneration** (7 tests)
   - GAL Config YAML Format Validierung
   - Target Config Format Validierung
   - Migration Report Format und Inhalt
   - Timestamp und Checklist Validierung

3. **TestMigrateCompatibility** (4 tests)
   - Compatibility Score Anzeige
   - Compatibility Validierung
   - Report Integration
   - Warnungen für partial support

4. **TestMigrateEdgeCases** (5 tests)
   - Ungültige Provider
   - Nicht-existente Config-Dateien
   - Leere Configs
   - Gleicher Source und Target Provider

5. **TestMigrateAllProviders** (1 test)
   - Kong → alle anderen Provider (5 Kombinationen)

6. **TestMigrateYesFlag** (2 tests)
   - `--yes` Flag funktioniert
   - `-y` Kurzform funktioniert

7. **TestMigrateReportContent** (5 tests)
   - Alle Report-Sektionen vorhanden
   - Summary Metriken vollständig
   - Service Details gelistet
   - Testing Checklist vorhanden
   - Next Steps vorhanden

**Test-Datei:** `tests/test_migrate.py` (820+ Zeilen)

## Features

✅ **5-Schritte Migration Workflow**
- Reading, Parsing, Converting, Validating, Generating

✅ **Interaktiver & Nicht-interaktiver Modus**
- Vollständig parametrisierbar oder komplett interaktiv

✅ **3 Generierte Dateien**
- GAL Config, Target Config, Migration Report

✅ **Automatic Compatibility Validation**
- Integration mit CompatibilityChecker (Feature 7)

✅ **Provider-agnostische Migration**
- Alle 6×6 = 36 Provider-Kombinationen unterstützt

✅ **Detaillierter Migration Report**
- Markdown-Format, vollständig automatisch generiert

✅ **Progress Indicators**
- Schritt-für-Schritt Fortschrittsanzeige mit Emojis

## Implementierungsstatus

**Status:** ✅ Vollständig abgeschlossen

**Dateien:**
- `gal-cli.py`: +380 Zeilen (migrate command + _generate_migration_report helper)
- `tests/test_migrate.py`: 820+ Zeilen, 31 Tests
- `docs/import/migration.md`: Dokumentation aktualisiert

**Akzeptanzkriterien:** 10/10 erfüllt
- ✅ Interaktiver CLI Workflow
- ✅ Nicht-interaktiver Modus (--yes Flag)
- ✅ Provider-Auswahl über CLI-Optionen
- ✅ Config Import Integration
- ✅ Compatibility Check Integration
- ✅ Migration Report Generation (Markdown)
- ✅ 3 Output-Dateien (GAL, Target, Report)
- ✅ Progress Indicators
- ✅ CLI Integration
- ✅ 31 Tests, 100% Pass Rate
