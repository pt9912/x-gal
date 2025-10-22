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

### Schritt 5: Unit Tests (Optional)
Falls gewünscht, führe alle Unit-Tests aus (ohne Docker):
```bash
pytest -v --tb=short --ignore=tests/test_docker_runtime.py
```

**Erwartetes Ergebnis:**
- `759 passed` → Alle Tests bestehen
- Fehler → **NICHT PUSHEN!** Behebe die Tests zuerst

### Schritt 6: Docker Runtime Tests (Kritisch bei Docker-Änderungen)
**WICHTIG:** Führe diese Tests aus, wenn Docker Compose Konfigurationen geändert wurden!

Prüfe, ob Docker-bezogene Dateien geändert wurden:
```bash
git diff --name-only develop | grep -E "tests/docker/|test_docker_runtime.py"
```

Falls Docker-Dateien geändert wurden, führe die Tests lokal aus:
```bash
pytest tests/test_docker_runtime.py -v -s
```

**Erwartetes Ergebnis:**
- `8 passed` → Alle Docker-Tests bestehen
- Timeout/Container-Fehler → **NICHT PUSHEN!** Behebe die Docker-Konfiguration zuerst

**Typische Docker-Fehler:**
- **Port-Konflikte**: Prüfe `docker-compose.yml` auf Port-Mappings (intern vs extern)
- **YAML-Syntax**: Validiere mit `docker compose config` im jeweiligen Verzeichnis
- **Container-Logs**: Prüfe Logs mit `docker compose logs <service>` bei Fehlern
- **Health Checks**: Stelle sicher, dass alle Services Health Checks haben

**Debug-Befehle bei Fehlern:**
```bash
# Docker Compose Syntax validieren
cd tests/docker/<provider> && docker compose config

# Container manuell starten und Logs prüfen
cd tests/docker/<provider> && docker compose up

# Container-Status prüfen
docker compose ps

# Logs eines spezifischen Services anzeigen
docker compose logs <service-name>

# Aufräumen nach fehlgeschlagenen Tests
docker compose down -v
```

**Provider-spezifische Checks:**
- **Traefik**: Port-Trennung zwischen Dashboard (:8080) und Entrypoint (:80)
- **APISIX**: YAML-Format (nicht JSON) in `apisix.yaml` verwenden
- **Envoy**: Cluster-Namen müssen mit Service-Namen übereinstimmen
- **Kong**: Admin API muss vor Proxy-Konfiguration verfügbar sein
- **Nginx**: Upstream-Server müssen im `upstream` Block definiert sein
- **HAProxy**: Server-Zeilen müssen korrekte Weight-Syntax haben

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

Gib dem Nutzer eine klare Zusammenfassung:

### Wenn keine Docker-Änderungen vorhanden sind:
```
🔍 Pre-Push Code Quality Check
==============================

✅ Black Formatierung: OK (0 Dateien geändert)
✅ Isort Import-Sortierung: OK (0 Dateien geändert)
✅ Flake8 Linting: OK (0 Fehler)
⏭️  Unit Tests: Übersprungen (optional)
⏭️  Docker Tests: Nicht nötig (keine Docker-Änderungen)

✅ ALLE CHECKS BESTANDEN - PUSH ERLAUBT!

Nächster Schritt:
  git push origin develop
```

### Wenn Docker-Änderungen vorhanden sind:
```
🔍 Pre-Push Code Quality Check
==============================

✅ Black Formatierung: OK (0 Dateien geändert)
✅ Isort Import-Sortierung: OK (0 Dateien geändert)
✅ Flake8 Linting: OK (0 Fehler)
⏭️  Unit Tests: Übersprungen (optional)
⚠️  Docker-Änderungen erkannt:
    - tests/docker/traefik/docker-compose.yml
    - tests/docker/apisix/apisix.yaml

🐳 Docker Runtime Tests werden ausgeführt...
✅ Docker Tests: 8/8 Tests bestanden (2m30s)
    - Envoy: 897/103 (89.7%/10.3%) ✅
    - Nginx: 914/86 (91.4%/8.6%) ✅
    - Kong: 900/100 (90.0%/10.0%) ✅
    - HAProxy: 900/100 (90.0%/10.0%) ✅
    - Traefik: 900/100 (90.0%/10.0%) ✅
    - APISIX: 906/94 (90.6%/9.4%) ✅

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

Falls Docker-Tests fehlschlagen:

```
🔍 Pre-Push Code Quality Check
==============================

✅ Black Formatierung: OK
✅ Isort Import-Sortierung: OK
✅ Flake8 Linting: OK
⏭️  Unit Tests: Übersprungen
❌ Docker Tests: 2 FEHLER GEFUNDEN!

Docker-Fehler:
  - TestTraefikTrafficSplitRuntime::test_traffic_distribution_90_10
    Error: listen tcp :8080: bind: address already in use

  - TestAPISIXTrafficSplitRuntime::test_traffic_distribution_90_10
    Error: failed to classify line: {

❌ PUSH BLOCKIERT - Behebe die Docker-Konfiguration zuerst!

Debug-Hinweise:
  1. Traefik Port-Konflikt: Prüfe docker-compose.yml (Port-Mapping)
  2. APISIX YAML-Fehler: Konvertiere JSON zu YAML in apisix.yaml

Validierung:
  cd tests/docker/traefik && docker compose config
  cd tests/docker/apisix && docker compose config
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

---

## Beispiel-Ausführung

### Beispiel 1: Normale Code-Änderungen (ohne Docker)
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

# Schritt 5: Prüfe auf Docker-Änderungen
git diff --name-only develop | grep -E "tests/docker/|test_docker_runtime.py"
# → (keine Ausgabe)

# Schritt 6: Geänderte Dateien committen
git add -A
git commit -m "style: Apply code formatting"

# Schritt 7: Push
git push origin develop
```

### Beispiel 2: Docker-Änderungen (mit Docker Runtime Tests)
```bash
# Schritt 1: Venv aktivieren
source venv/bin/activate

# Schritt 2-4: Black, Isort, Flake8 (wie oben)

# Schritt 5: Prüfe auf Docker-Änderungen
git diff --name-only develop | grep -E "tests/docker/|test_docker_runtime.py"
# → tests/docker/traefik/docker-compose.yml
# → tests/docker/apisix/apisix.yaml

# Schritt 6: Docker Compose Syntax validieren
cd tests/docker/traefik && docker compose config
# → (Ausgabe der validierten Config)
cd tests/docker/apisix && docker compose config
# → (Ausgabe der validierten Config)

# Schritt 7: Docker Runtime Tests ausführen
cd /Development/x-gal
pytest tests/test_docker_runtime.py -v -s
# → 8 passed in 150.04s (0:02:30)

# Schritt 8: Push
git push origin develop
```

### Beispiel 3: Docker-Tests schlagen fehl (Debugging)
```bash
# Schritt 7: Docker Runtime Tests ausführen
pytest tests/test_docker_runtime.py::TestTraefikTrafficSplitRuntime -v -s
# → FAILED - Error: listen tcp :8080: bind: address already in use

# Debug: Container manuell starten
cd tests/docker/traefik
docker compose up
# → Error: listen tcp :8080: bind: address already in use

# Debug: Logs prüfen
docker compose logs traefik
# → traefik    | Error: cannot bind listener: listen tcp :8080: bind: address already in use

# Fix: docker-compose.yml anpassen (Port 80 intern, 8080 extern)
# Dann erneut testen
pytest tests/test_docker_runtime.py::TestTraefikTrafficSplitRuntime -v -s
# → PASSED ✅

# Aufräumen
docker compose down -v
```

---

## Wartung

Aktualisiere diesen Skill, wenn:
- Neue Code Quality Tools hinzugefügt werden
- GitHub Actions Workflow geändert wird
- Neue Linting-Regeln eingeführt werden
- Neue Docker-Provider hinzugefügt werden
- Docker Compose Konfigurationen geändert werden

## Warum ist dieser Skill so wichtig?

### Real-World Beispiel: Docker-Tests (Commit 8b95647)

**Problem:**
- Docker Compose Tests erstellt und direkt gepusht (11:37 Uhr)
- Tests wurden **nie lokal ausgeführt** vor dem Push
- GitHub Actions schlugen fehl (Traefik + APISIX)

**Fehler gefunden:**
1. **Traefik Port-Konflikt**: Dashboard und Entrypoint konkurrierten um Port 8080
2. **APISIX YAML-Format**: JSON statt YAML in apisix.yaml

**Debugging-Zeit:** 3.5 Stunden (14:32 - 15:06)

**Hätte verhindert werden können durch:**
```bash
# Pre-Push Skill hätte erkannt:
git diff --name-only develop | grep -E "tests/docker/"
# → tests/docker/traefik/docker-compose.yml
# → tests/docker/apisix/apisix.yaml

# Docker Tests lokal ausführen:
pytest tests/test_docker_runtime.py -v -s
# → FAILED - Port conflict (Traefik)
# → FAILED - YAML error (APISIX)

# Fehler in 5 Minuten behoben statt 3.5 Stunden!
```

### Real-World Beispiel: Flake8 F822 Fehler (Commit edad068)

**Problem:**
- `__all__` Export-Liste mit 8 nicht-existierenden Klassennamen
- Direkt gepusht ohne lokale Flake8-Validierung
- GitHub Actions Code Quality Check schlug fehl

**Fehler gefunden:**
```
F822 undefined name 'HeaderConfig' in __all__
F822 undefined name 'CorsConfig' in __all__
F822 undefined name 'RetryPolicyConfig' in __all__
... (8 Fehler total)
```

**Hätte verhindert werden können durch:**
```bash
# Pre-Push Skill hätte erkannt:
flake8 gal/config.py --count --select=E9,F63,F7,F82
# → 8 errors found!

# Fehler in 2 Minuten behoben statt nach Push!
```

### Lesson Learned

**Ohne Pre-Push Skill:**
- Docker-Fehler: 3.5 Stunden Debugging nach Push
- Flake8-Fehler: Zusätzlicher Fix-Commit nötig
- GitHub Actions Ressourcen verschwendet
- Entwickler-Frustration durch CI/CD-Failures

**Mit Pre-Push Skill:**
- Fehler werden **vor** dem Push gefunden
- 5 Minuten lokales Debugging
- Kein Failed CI/CD Run
- Saubere Git-History

## Changelog

**Version 2.1.0** (2025-10-22)
- ✅ Erweiterte Fehlerbehandlung für F822 (undefined names in __all__)
- ✅ Real-World Beispiele hinzugefügt (Docker + Flake8 Fehler)
- ✅ Root Cause Analysis dokumentiert
- ✅ Debugging-Commands für __all__ Validierung

**Version 2.0.0** (2025-10-22)
- ✅ Docker Runtime Tests hinzugefügt (Schritt 6)
- ✅ Automatische Erkennung von Docker-Änderungen
- ✅ Provider-spezifische Debug-Hinweise (Traefik, APISIX, etc.)
- ✅ Docker Compose Syntax-Validierung
- ✅ Erweiterte Fehlerbehandlung für Container-Probleme
- ✅ Drei vollständige Beispiele (Normal, Docker, Debugging)

**Version 1.0.0** (2025-10-18)
- Initial Release mit Black, Isort, Flake8, Unit Tests

**Autor:** Claude Code (generiert)
**Version:** 2.1.0
**Letzte Aktualisierung:** 2025-10-22
