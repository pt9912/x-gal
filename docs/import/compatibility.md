# Compatibility Checker & Provider Comparison

## Übersicht

Der **Compatibility Checker** analysiert GAL-Konfigurationen und prüft, welche Features mit verschiedenen API Gateway-Providern kompatibel sind. Dies hilft bei der **Provider-Auswahl**, **Migration Planning** und **Feature-Planung**.

**Hauptfunktionen:**
- ✅ **Check Compatibility**: Prüft ob eine Config mit einem spezifischen Provider kompatibel ist
- 📊 **Compare Providers**: Vergleicht Kompatibilität über mehrere Provider hinweg
- 💡 **Recommendations**: Gibt Empfehlungen für nicht unterstützte Features
- 🎯 **Compatibility Score**: Berechnet einen Score von 0-100%

**Verfügbar ab:** v1.3.0

## CLI Usage

### Check Compatibility (Single Provider)

Prüft Kompatibilität mit einem einzelnen Provider:

```bash
gal check-compatibility --config CONFIG --target-provider PROVIDER [--verbose]
```

**Parameter:**
- `--config`, `-c`: Pfad zur GAL-Konfiguration (erforderlich)
- `--target-provider`, `-p`: Ziel-Provider (envoy, kong, apisix, traefik, nginx, haproxy)
- `--verbose`, `-v`: Zeigt detaillierte Feature-Informationen

**Beispiel:**

```bash
gal check-compatibility \
  --config examples/gateway-config.yaml \
  --target-provider traefik \
  --verbose
```

**Ausgabe:**

```
================================================================================
COMPATIBILITY REPORT: TRAEFIK
================================================================================

✅ Status: COMPATIBLE
📊 Compatibility Score: 81.2%
🔍 Features Checked: 8

✅ Fully Supported:   6
⚠️  Partially Supported: 1
❌ Not Supported:     1

⚠️  WARNINGS:
  • ❌ Active Health Checks not supported
  • ⚠️ Load Balancing (IP Hash) partially supported

💡 RECOMMENDATIONS:
  • Traefik OSS only supports passive health checks. Consider Traefik Enterprise or use passive checks.
  • IP hash via sticky sessions with cookie. May not be true consistent hashing.
```

### Compare Providers

Vergleicht Kompatibilität über mehrere Provider:

```bash
gal compare-providers --config CONFIG [--providers PROVIDERS] [--verbose]
```

**Parameter:**
- `--config`, `-c`: Pfad zur GAL-Konfiguration (erforderlich)
- `--providers`, `-p`: Komma-separierte Provider-Liste (Standard: alle 6 Provider)
- `--verbose`, `-v`: Zeigt detaillierte Reports für jeden Provider

**Beispiel:**

```bash
# Alle Provider vergleichen
gal compare-providers --config examples/health-checks-example.yaml

# Nur bestimmte Provider vergleichen
gal compare-providers \
  --config examples/gateway-config.yaml \
  --providers envoy,traefik,nginx
```

**Ausgabe:**

```
====================================================================================================
PROVIDER COMPARISON
====================================================================================================

Provider     Status          Score      Supported    Partial    Unsupported
----------------------------------------------------------------------------------------------------
envoy        ✅ Compatible    100.0%     8            0          0
kong         ✅ Compatible    95.0%      7            1          0
apisix       ✅ Compatible    95.0%      7            1          0
nginx        ✅ Compatible    87.5%      7            0          1
traefik      ✅ Compatible    81.2%      6            1          1
haproxy      ✅ Compatible    75.0%      6            0          2

Summary: 6/6 providers are compatible

✨ Best choice: envoy (100% compatible)
```

## Use Cases

### 1. Provider-Auswahl

**Szenario:** Sie planen ein neues Projekt und möchten den besten Provider wählen.

```bash
# Config mit gewünschten Features erstellen
cat > my-requirements.yaml <<EOF
version: "1.0"
provider: envoy
global:
  host: "0.0.0.0"
  port: 8080
services:
  - name: api
    type: rest
    protocol: http
    upstream:
      host: api.internal
      port: 8080
      health_check:
        active:
          enabled: true
          http_path: /health
      load_balancer:
        algorithm: round_robin
    routes:
      - path_prefix: /api/v1
        rate_limit:
          enabled: true
          requests_per_second: 100
        authentication:
          enabled: true
          type: jwt
EOF

# Alle Provider vergleichen
gal compare-providers --config my-requirements.yaml
```

**Ergebnis:** Sie sehen sofort, welche Provider alle gewünschten Features unterstützen.

### 2. Migration Planning

**Szenario:** Sie migrieren von Provider A nach Provider B.

```bash
# 1. Importieren Sie Ihre existierende Config
gal import-config \
  --provider nginx \
  --input /etc/nginx/nginx.conf \
  --output current-config.yaml

# 2. Prüfen Sie Kompatibilität mit Ziel-Provider
gal check-compatibility \
  --config current-config.yaml \
  --target-provider envoy \
  --verbose

# 3. Vergleichen Sie mit alternativen Providern
gal compare-providers \
  --config current-config.yaml \
  --providers envoy,kong,apisix
```

**Ergebnis:** Sie erhalten eine Liste nicht unterstützter Features und Empfehlungen für Alternativen.

### 3. Feature-Planung

**Szenario:** Sie möchten neue Features hinzufügen und prüfen, ob Ihr Provider diese unterstützt.

```bash
# Erweitern Sie Ihre Config um neue Features
# (z.B. Circuit Breaker, Advanced Auth)

# Prüfen Sie Kompatibilität
gal check-compatibility \
  --config enhanced-config.yaml \
  --target-provider traefik \
  --verbose
```

**Ergebnis:** Sie sehen, ob Ihr aktueller Provider die neuen Features unterstützt oder ob ein Wechsel erforderlich ist.

## Feature Support Matrix

### Legend

- ✅ **FULL**: Vollständige Unterstützung
- ⚠️ **PARTIAL**: Teilweise Unterstützung (mit Einschränkungen)
- ❌ **UNSUPPORTED**: Nicht unterstützt

### Routing & Traffic Management

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy |
|---------|-------|------|--------|---------|-------|---------|
| Path-based Routing | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| HTTP Methods | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Load Balancing

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy |
|---------|-------|------|--------|---------|-------|---------|
| Round Robin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Least Connections | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| IP Hash | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| Sticky Sessions | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ |

**Hinweise:**
- **Traefik IP Hash:** Implementiert via Sticky Sessions mit Cookie (nicht echtes IP Hashing)
- **Nginx Sticky Sessions:** Erfordert Nginx Plus oder third-party modules

### Health Checks

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy |
|---------|-------|------|--------|---------|-------|---------|
| Active Health Checks | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Passive Health Checks | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ |

**Hinweise:**
- **Traefik Active:** Nur in Traefik Enterprise verfügbar
- **Nginx Active:** Nur in Nginx Plus verfügbar (OSS hat `max_fails/fail_timeout`)
- **Nginx Passive:** Via `max_fails` und `fail_timeout` Direktiven

### Security & Authentication

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy |
|---------|-------|------|--------|---------|-------|---------|
| Rate Limiting | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Basic Authentication | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ |
| API Key Authentication | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| JWT Authentication | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| CORS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Hinweise:**
- **Envoy Rate Limiting:** OSS ist global, per-route erfordert external rate limit service
- **Envoy Basic Auth:** Erfordert Lua Filter oder ext_authz
- **Nginx JWT:** Erfordert OpenResty mit lua-resty-jwt
- **Nginx API Key:** Via Lua oder map-basierte Validierung
- **HAProxy JWT/API Key:** Via Lua scripting

### Advanced Features

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy |
|---------|-------|------|--------|---------|-------|---------|
| Circuit Breaker | ✅ | ✅ | ✅ | ⚠️ | ❌ | ⚠️ |
| Header Manipulation (Request) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Header Manipulation (Response) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Timeout Configuration | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Retry Policy | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Hinweise:**
- **Traefik Circuit Breaker:** Nur in Traefik Enterprise
- **Nginx Circuit Breaker:** Nicht verfügbar (nur passive health checks)
- **HAProxy Circuit Breaker:** Limited via `observe layer7`

## Compatibility Score Berechnung

Der **Compatibility Score** wird wie folgt berechnet:

```
Score = (FULL × 1.0 + PARTIAL × 0.5 + UNSUPPORTED × 0.0) / Total Features
```

**Bewertung:**
- **100%**: Perfekt kompatibel - alle Features voll unterstützt
- **90-99%**: Sehr gut - minimale Einschränkungen
- **80-89%**: Gut - akzeptable Einschränkungen
- **70-79%**: OK - signifikante Einschränkungen
- **< 70%**: Problematisch - viele nicht unterstützte Features

**Kompatibilitäts-Schwellwert:** >= 80% (konfigurierbar)

## Interpretation der Ergebnisse

### Fully Supported Features ✅

Features die **ohne Einschränkungen** funktionieren.

**Beispiel:**
```
✅ FULLY SUPPORTED FEATURES:
  • routing_path_prefix
    ✅ Path-based Routing fully supported
  • rate_limiting
    ✅ Rate Limiting fully supported
```

**Empfehlung:** Keine Aktion erforderlich.

### Partially Supported Features ⚠️

Features die **mit Einschränkungen** funktionieren.

**Beispiel:**
```
⚠️  PARTIALLY SUPPORTED FEATURES:
  • load_balancing_ip_hash
    ⚠️ Load Balancing (IP Hash) partially supported
    💡 IP hash via sticky sessions with cookie. May not be true consistent hashing.
```

**Empfehlung:**
1. Prüfen Sie die Recommendation
2. Testen Sie die Implementierung
3. Evaluieren Sie Alternativen

### Unsupported Features ❌

Features die **nicht verfügbar** sind.

**Beispiel:**
```
❌ UNSUPPORTED FEATURES:
  • health_check_active
    ❌ Active Health Checks not supported
    💡 Traefik OSS only supports passive health checks. Consider Traefik Enterprise or use passive checks.
```

**Empfehlung:**
1. Verwenden Sie die empfohlene Alternative
2. Erwägen Sie einen Provider-Wechsel
3. Prüfen Sie ob das Feature kritisch ist

## Best Practices

### 1. Früh validieren

Prüfen Sie Kompatibilität **vor** der Implementierung:

```bash
# Erstellen Sie eine Requirements-Config
# Prüfen Sie Provider-Kompatibilität
# Wählen Sie Provider basierend auf Ergebnissen
```

### 2. Regelmäßig überprüfen

Bei Feature-Erweiterungen:

```bash
# Nach jeder größeren Config-Änderung
gal check-compatibility --config CONFIG --target-provider PROVIDER
```

### 3. Alle Provider vergleichen

Für wichtige Entscheidungen:

```bash
# Vergleichen Sie alle verfügbaren Provider
gal compare-providers --config CONFIG --verbose
```

### 4. Dokumentieren Sie Einschränkungen

Halten Sie fest:
- Welche Features partial/unsupported sind
- Warum ein Feature nicht unterstützt wird
- Welche Alternativen Sie verwenden

### 5. Testen Sie Partial Features

Features mit PARTIAL Support sollten getestet werden:

```bash
# 1. Generieren Sie Provider-Config
gal generate --config CONFIG --provider PROVIDER

# 2. Deployen Sie in Test-Environment
# 3. Testen Sie das Verhalten
# 4. Dokumentieren Sie Einschränkungen
```

## Beispiele

### Beispiel 1: Einfache API

```bash
$ gal check-compatibility \
    --config examples/gateway-config.yaml \
    --target-provider envoy

✅ Status: COMPATIBLE
📊 Compatibility Score: 100.0%
🔍 Features Checked: 2

✅ Fully Supported:   2
⚠️  Partially Supported: 0
❌ Not Supported:     0
```

**Interpretation:** Perfekt kompatibel - keine Einschränkungen.

### Beispiel 2: Komplexe Config mit Health Checks

```bash
$ gal compare-providers \
    --config examples/health-checks-example.yaml \
    --providers envoy,traefik,nginx

Provider     Status          Score      Supported    Partial    Unsupported
----------------------------------------------------------------------------------------------------
envoy        ✅ Compatible    100.0%     8            0          0
nginx        ✅ Compatible    87.5%      7            0          1
traefik      ✅ Compatible    81.2%      6            1          1

✨ Best choice: envoy (100% compatible)
```

**Interpretation:**
- **Envoy:** Beste Wahl - volle Unterstützung
- **Nginx:** Gut - 1 Feature nicht unterstützt (active health checks)
- **Traefik:** OK - 1 partial + 1 unsupported Feature

### Beispiel 3: Migration von Nginx zu Kong

```bash
# 1. Import Nginx Config
$ gal import-config \
    --provider nginx \
    --input /etc/nginx/nginx.conf \
    --output nginx-imported.yaml

# 2. Check Kong Compatibility
$ gal check-compatibility \
    --config nginx-imported.yaml \
    --target-provider kong \
    --verbose

✅ Status: COMPATIBLE
📊 Compatibility Score: 95.0%

⚠️  WARNINGS:
  • ⚠️ Rate Limiting partially supported

💡 RECOMMENDATIONS:
  • Kong rate limiting uses different time windows. Review rate limit configs.
```

**Interpretation:** Migration ist möglich mit kleinen Anpassungen bei Rate Limiting.

## Troubleshooting

### Problem: "Unknown provider" Fehler

**Ursache:** Provider-Name ist ungültig.

**Lösung:**
```bash
# Gültige Provider: envoy, kong, apisix, traefik, nginx, haproxy
gal check-compatibility --config CONFIG --target-provider envoy
```

### Problem: Niedriger Compatibility Score

**Ursache:** Viele nicht unterstützte Features.

**Lösungen:**
1. Prüfen Sie die Recommendations
2. Erwägen Sie einen anderen Provider
3. Reduzieren Sie nicht-kritische Features

### Problem: Features werden nicht erkannt

**Ursache:** Config verwendet falsche Syntax oder Attribute.

**Lösung:**
```bash
# 1. Validieren Sie die Config
gal validate --config CONFIG

# 2. Prüfen Sie die Config-Struktur
gal info --config CONFIG
```

## Weiterführende Ressourcen

- [Import & Migration Guide](migration.md) - Provider-Import Dokumentation
- [Provider Guides](../guides/PROVIDERS.md) - Provider-spezifische Informationen
- [v1.3.0 Plan](../v1.3.0-PLAN.md) - Feature-Implementierungsplan

### Provider-Dokumentation

- [Envoy Proxy](https://www.envoyproxy.io/)
- [Kong Gateway](https://docs.konghq.com/)
- [Apache APISIX](https://apisix.apache.org/)
- [Traefik](https://doc.traefik.io/traefik/)
- [Nginx](https://nginx.org/en/docs/)
- [HAProxy](https://www.haproxy.com/documentation/)

## Zusammenfassung

Der **Compatibility Checker** ist ein essentielles Tool für:

✅ **Provider-Auswahl** - Finden Sie den besten Provider für Ihre Anforderungen
✅ **Migration Planning** - Planen Sie Migrationen mit Konfidenz
✅ **Feature Validation** - Prüfen Sie Feature-Kompatibilität vor der Implementierung
✅ **Decision Making** - Treffen Sie datenbasierte Entscheidungen

**Verfügbar ab v1.3.0** - nutzen Sie `gal check-compatibility` und `gal compare-providers` für bessere Provider-Entscheidungen!
