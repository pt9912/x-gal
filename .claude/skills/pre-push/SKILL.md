# Pre-Push Code Quality Check Skill

**Name:** pre-push
**Beschreibung:** Führt automatisch Code Quality Checks (black, isort, flake8) vor jedem git push aus, um CI/CD Fehler zu vermeiden.
**Trigger:** Nutze diesen Skill PROAKTIV vor jedem `git push`, um sicherzustellen, dass alle Code Quality Standards erfüllt sind.

---

## Zweck

Dieser Skill verhindert, dass Code mit Formatierungs- oder Linting-Fehlern zu GitHub gepusht wird. Er führt alle Code Quality Checks lokal aus, die auch in GitHub Actions laufen.

## Wann nutzen?

✅ **IMMER vor `git push origin develop`**
✅ **IMMER vor `git push origin main`**
✅ **Nach größeren Code-Änderungen (z.B. neue Features)**
✅ **Wenn der Nutzer explizit darum bittet**

❌ **NICHT bei reinen Dokumentations-Änderungen (nur .md Dateien)**

## Workflow

### Schritt 1: Venv aktivieren
Stelle sicher, dass die virtuelle Umgebung aktiv ist:
```bash
source venv/bin/activate
```

Falls venv nicht existiert:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

### Schritt 2: Black Formatierung
Formatiere alle Python-Dateien:
```bash
black .
```

**Erwartetes Ergebnis:**
- `All done! ✨ 🍰 ✨` → Perfekt, weiter
- `X files reformatted` → Dateien wurden formatiert, stage sie mit `git add`

### Schritt 3: Isort Import-Sortierung
Sortiere alle Imports:
```bash
isort .
```

**Erwartetes Ergebnis:**
- `Skipped X files` oder keine Ausgabe → Perfekt, weiter
- `Fixing /path/to/file.py` → Dateien wurden geändert, stage sie mit `git add`

### Schritt 4: Flake8 Linting
Prüfe auf kritische Code-Fehler:
```bash
flake8 gal/ tests/ gal-cli.py --count --select=E9,F63,F7,F82 --show-source --statistics
```

**Erwartetes Ergebnis:**
- `0` → Keine Fehler, perfekt!
- `> 0` → **FEHLER GEFUNDEN!** Behebe sie, bevor du pushst

**Fehlertypen:**
- `F821`: Undefined name (fehlende Variablen)
- `F822`: Undefined name in __all__
- `F824`: Unused global/nonlocal

### Schritt 5: Tests (Optional)
Falls gewünscht, führe alle Tests aus:
```bash
pytest -v --tb=short
```

**Erwartetes Ergebnis:**
- `323 passed` → Alle Tests bestehen
- Fehler → **NICHT PUSHEN!** Behebe die Tests zuerst

### Schritt 6: Git Status prüfen
Falls Dateien geändert wurden:
```bash
git status
git add -A
git commit --amend --no-edit
# ODER
git commit -m "style: Apply code formatting"
```

### Schritt 7: Push erlauben
✅ **Alle Checks bestanden → PUSH ERLAUBT**

## Ausgabe-Format

Gib dem Nutzer eine klare Zusammenfassung:

```
🔍 Pre-Push Code Quality Check
==============================

✅ Black Formatierung: OK (0 Dateien geändert)
✅ Isort Import-Sortierung: OK (0 Dateien geändert)
✅ Flake8 Linting: OK (0 Fehler)
⏭️  Tests: Übersprungen (optional)

✅ ALLE CHECKS BESTANDEN - PUSH ERLAUBT!

Nächster Schritt:
  git push origin develop
```

Falls Fehler gefunden wurden:

```
🔍 Pre-Push Code Quality Check
==============================

✅ Black Formatierung: 5 Dateien reformatiert
✅ Isort Import-Sortierung: 3 Dateien geändert
❌ Flake8 Linting: 2 FEHLER GEFUNDEN!

Fehler:
  - gal/providers/nginx.py:404:23: F821 undefined name 'config'
  - tests/test_foo.py:50:12: F821 undefined name 'bar'

❌ PUSH BLOCKIERT - Behebe die Fehler zuerst!

Geänderte Dateien müssen committed werden:
  git add -A
  git commit --amend --no-edit
```

## Fehlerbehandlung

### Venv nicht gefunden
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

### Black/Isort/Flake8 nicht installiert
```bash
pip install -e .[dev]
```

### Kritische Flake8 Fehler
1. Öffne die betroffene Datei
2. Behebe den Fehler (z.B. fehlende Variable definieren)
3. Führe Pre-Push Check erneut aus

## Best Practices

1. **Immer vor dem Push ausführen** - Verhindert CI/CD Fehler
2. **Bei Fehlern nicht pushen** - Behebe sie lokal zuerst
3. **Geänderte Dateien committen** - Verwende `--amend` oder neuen Commit
4. **Tests optional ausführen** - Nur bei größeren Änderungen nötig

## Integration in Workflow

Der Skill sollte automatisch aufgerufen werden, wenn:
- Der Nutzer `git push` erwähnt
- Der Nutzer sagt "Bitte pushen"
- Claude bereit ist zu pushen

**Beispiel:**
```
User: "Bitte pushen und die Actions beobachten"
Claude: "Ich führe zuerst den Pre-Push Code Quality Check aus..."
[Skill wird ausgeführt]
Claude: "✅ Alle Checks bestanden. Ich pushe jetzt..."
```

---

## Beispiel-Ausführung

```bash
# Schritt 1: Venv aktivieren
source venv/bin/activate

# Schritt 2: Black
black .
# → All done! ✨ 🍰 ✨
# → 25 files reformatted, 4 files left unchanged.

# Schritt 3: Isort
isort .
# → Fixing /Development/x-gal/gal-cli.py
# → Skipped 2 files

# Schritt 4: Flake8
flake8 gal/ tests/ gal-cli.py --count --select=E9,F63,F7,F82 --show-source --statistics
# → 0

# Schritt 5: Geänderte Dateien committen
git add -A
git commit -m "style: Apply code formatting"

# Schritt 6: Push
git push origin develop
```

---

## Wartung

Aktualisiere diesen Skill, wenn:
- Neue Code Quality Tools hinzugefügt werden
- GitHub Actions Workflow geändert wird
- Neue Linting-Regeln eingeführt werden

**Autor:** Claude Code (generiert)
**Version:** 1.0.0
**Letzte Aktualisierung:** 2025-10-18
