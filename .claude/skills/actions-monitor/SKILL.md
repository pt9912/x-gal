---
name: GitHub Actions Monitor
description: Beobachtet GitHub Actions nach git push Operationen. Nutze diesen Skill automatisch nach jedem erfolgreichen git push, um sicherzustellen, dass CI/CD erfolgreich läuft.
---

# GitHub Actions Monitor Skill

## Zweck

Dieser Skill überwacht automatisch GitHub Actions nach einem `git push` und informiert den Nutzer über den Status der CI/CD-Pipeline.

## Wann dieser Skill aufgerufen wird

Claude sollte diesen Skill **automatisch** verwenden in folgenden Situationen:

- Nach einem erfolgreichen `git push` Befehl
- Wenn der Nutzer nach GitHub Actions fragt
- Wenn ein Release-Prozess läuft
- Nach einem Merge zu main oder develop

## Anweisungen

### 1. GitHub Actions Status prüfen

- Führe aus: `gh run list --limit 5`
- Zeige die letzten 5 Workflow-Läufe an
- Identifiziere den neuesten Lauf für den aktuellen Branch

### 2. Actions beobachten

- Führe aus: `gh run watch` um den neuesten Lauf zu überwachen
- Warte auf den Abschluss der Actions
- Zeige den Fortschritt in Echtzeit

### 3. Ergebnis analysieren

**Bei erfolgreichem Abschluss:**
- ✅ Informiere den Nutzer über den Erfolg
- Zeige die Laufzeit an
- Liste alle erfolgreichen Jobs auf

**Bei Fehlschlag:**
- ❌ Informiere den Nutzer über den Fehler
- Führe aus: `gh run view --log-failed` um Fehler-Logs anzuzeigen
- Analysiere die Fehler und gib Hinweise zur Behebung:
  - Lint-Fehler → Auf Code-Qualität hinweisen
  - Test-Fehler → Auf fehlgeschlagene Tests hinweisen
  - Build-Fehler → Auf Kompilierungs-Probleme hinweisen
- Schlage vor, wie der Fehler behoben werden kann

### 4. Status-Zusammenfassung

Zeige eine kompakte Übersicht:
```
🔍 GitHub Actions Status:
Branch: <branch-name>
Commit: <commit-hash>
Status: ✅ Success / ❌ Failed / ⏳ In Progress
Duration: <time>
Jobs: <successful>/<total>
URL: <workflow-url>
```

## Erweiterte Funktionen

### Mehrere Branches überwachen

Wenn Pushes zu mehreren Branches erfolgt sind:
- Liste Actions für jeden Branch auf
- Priorisiere main und develop Branches
- Zeige parallele Läufe an

### Long-Running Actions

Für Actions, die länger als 2 Minuten laufen:
- Informiere den Nutzer über die geschätzte Laufzeit
- Biete an, die Überwachung im Hintergrund fortzusetzen
- Zeige periodische Updates

### Fehlerdiagnose

Bei Fehlern, analysiere:
1. **Lint-Fehler**:
   - Black formatting issues
   - isort import sorting problems
   - flake8 code quality issues
2. **Test-Fehler**: Zeige welche pytest Tests fehlgeschlagen sind
3. **Build-Fehler**: Zeige Python Build Probleme (`python -m build`)
4. **Docker-Fehler**: Zeige Docker Build Probleme
5. **Deployment-Fehler**: Zeige PyPI/Docker Publish Probleme

## Verwendete Tools

- Bash: Für gh CLI Befehle
- TodoWrite: Optional für Fortschrittsverfolgung bei langen Actions

## Fehlerbehandlung

- Falls `gh` CLI nicht verfügbar: Informiere Nutzer über Installation
- Falls keine Actions gefunden: Prüfe ob Push erfolgreich war
- Falls Timeout: Biete an, Status später zu prüfen

## Integration mit anderen Skills

Dieser Skill wird automatisch vom **Release Manager Skill** nach Pushes aufgerufen.
