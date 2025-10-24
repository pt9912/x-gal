---
name: pre-push
description: Führt automatisch Code Quality Checks (black, isort, flake8) vor jedem git push aus, um CI/CD Fehler zu vermeiden. Nutze diesen Skill PROAKTIV vor jedem `git push`, um sicherzustellen, dass alle Code Quality Standards erfüllt sind.
---

# Pre-Push Code Quality Check Skill

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

### Schritt 5: Unit Tests
Führe alle Unit-Tests aus (ohne Docker):
```bash
pytest -v --tb=short --ignore=tests/test_docker_runtime.py
```

**Erwartetes Ergebnis:**
- `759 passed` → Alle Tests bestehen
- Fehler → **NICHT PUSHEN!** Behebe die Tests zuerst

### Schritt 6: E2E Tests
Führe alle E2E-Tests aus (Dauern über 5 Minuten):
```bash
pytest tests/e2e/ -v -s
```

### Schritt 7: Git Status prüfen
Falls Dateien geändert wurden:
```bash
git status
git add -A
git commit --amend --no-edit
# ODER
git commit -m "style: Apply code formatting"
```

### Schritt 8: Push erlauben
✅ **Alle Checks bestanden → PUSH ERLAUBT**

## Ausgabe-Format

Gib dem Nutzer eine klare Zusammenfassung

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

### Kritische Flake8 Fehler (F822 - Undefined names in __all__)

**Typisches Beispiel:**
```
./gal/config.py:14:1: F822 undefined name 'HeaderConfig' in __all__
./gal/config.py:14:1: F822 undefined name 'CorsConfig' in __all__
```

**Ursache:**
- Klassennamen in `__all__` stimmen nicht mit tatsächlich definierten Klassen überein
- Alte Namen nach Refactoring nicht aktualisiert
- Copy-Paste-Fehler beim Hinzufügen neuer Exporte

**Lösung:**
1. Finde alle tatsächlich definierten Klassen:
   ```bash
   grep -E "^class " gal/config.py | awk '{print $2}' | sed 's/[(:].*$//'
   ```

2. Vergleiche mit `__all__` Export-Liste in gal/config.py

3. Aktualisiere `__all__` mit korrekten Klassennamen:
   ```python
   __all__ = [
       # Falsch:
       "HeaderConfig",        # Klasse existiert nicht!
       "CorsConfig",          # Klasse existiert nicht!

       # Richtig:
       "HeaderManipulation",  # Tatsächlicher Klassenname
       "CORSPolicy",          # Tatsächlicher Klassenname
   ]
   ```

4. Führe Pre-Push Check erneut aus

**Warum wurde dieser Fehler nicht früher entdeckt?**
- Der Pre-Push Skill wurde nicht ausgeführt vor dem Push
- Vertrauen auf GitHub Actions statt lokale Validierung
- F822-Check war im Skill korrekt konfiguriert, aber nicht genutzt

## Best Practices

1. **Immer vor dem Push ausführen** - Verhindert CI/CD Fehler
2. **Bei Fehlern nicht pushen** - Behebe sie lokal zuerst
3. **Geänderte Dateien committen** - Verwende `--amend` oder neuen Commit
4. **Unit Tests optional ausführen** - Nur bei größeren Code-Änderungen nötig
5. **Docker Tests IMMER ausführen bei Docker-Änderungen** - Verhindert Container-Fehler in CI/CD
6. **Docker Compose Syntax validieren** - Nutze `docker compose config` vor dem Push
7. **Container-Logs bei Fehlern prüfen** - Nicht blind auf GitHub Actions verlassen

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

