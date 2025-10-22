# HAProxy Best Practices & Troubleshooting

**Best Practices und Troubleshooting für HAProxy Provider in GAL**

**Navigation:**
- [← Zurück zur HAProxy Übersicht](HAPROXY.md)
- [← Feature-Implementierungen](HAPROXY_FEATURES.md)

## Inhaltsverzeichnis

1. [Best Practices](#best-practices)
2. [Troubleshooting](#troubleshooting)
3. [Weiterführende Ressourcen](#weiterfuhrende-ressourcen)

---
## Best Practices

### 1. Kombiniere Active + Passive Health Checks

**Empfehlung:**
```yaml
health_check:
  active:
    enabled: true
    interval: "10s"
  passive:
    enabled: true
    max_failures: 3
```

**Vorteil:** Schnelle Reaktion bei Ausfällen + Traffic-basierte Überwachung.

### 2. Nutze Weighted Load Balancing für heterogene Server

**Empfehlung:**
```yaml
targets:
  - host: large-instance.internal
    port: 8080
    weight: 4
  - host: medium-instance.internal
    port: 8080
    weight: 2
  - host: small-instance.internal
    port: 8080
    weight: 1
```

**Vorteil:** Optimale Ressourcen-Nutzung.

### 3. Setze angemessene Timeouts

**Empfehlung:**
```yaml
global:
  timeout: "60s"  # Für lange API-Requests
```

**Mapping:**
```haproxy
defaults
    timeout client  60s
    timeout server  60s
    timeout connect 5s   # Immer kurz (Connection Setup)
```

### 4. Aktiviere Connection Pooling

**HAProxy Standard:**
```haproxy
defaults
    option http-server-close  # Connection Reuse
```

**Vorteil:** Reduziert Backend-Verbindungen.

### 5. Nutze Stick-Tables effizient

**Empfehlung:**
```haproxy
stick-table type ip size 100k expire 30s store http_req_rate(10s)
```

- `size 100k`: Für ~100k gleichzeitige IPs
- `expire 30s`: Automatisches Cleanup
- `store http_req_rate(10s)`: 10s Zeitfenster

### 6. Monitoring via Stats Socket

**Setup:**
```haproxy
global
    stats socket /var/lib/haproxy/stats level admin
```

**Nutzung:**
```bash
# Server Status
echo "show servers state" | socat /var/lib/haproxy/stats -

# Disable Server
echo "disable server backend_api/server1" | socat /var/lib/haproxy/stats -

# Enable Server
echo "enable server backend_api/server1" | socat /var/lib/haproxy/stats -
```

### 7. Logging für Production

**Empfehlung:**
```haproxy
defaults
    option httplog
    log global
```

**Mit Rsyslog:**
```bash
# /etc/rsyslog.d/haproxy.conf
$ModLoad imudp
$UDPServerRun 514
local0.* /var/log/haproxy/access.log
```

---

## Troubleshooting

### 1. "503 Service Unavailable"

**Symptom:** Alle Requests → 503

**Mögliche Ursachen:**
1. Alle Backend-Server down
2. Health Checks schlagen fehl
3. Backend nicht erreichbar

**Debugging:**
```bash
# Server Status prüfen
echo "show servers state" | socat /var/lib/haproxy/stats -

# HAProxy Logs
tail -f /var/log/haproxy/access.log

# Health Check testen
curl http://backend-server:8080/health
```

**Lösung:**
```bash
# Server manuell aktivieren
echo "enable server backend_api/server1" | socat /var/lib/haproxy/stats -

# Health Check Path anpassen
backend backend_api
    option httpchk GET /actuator/health HTTP/1.1
```

### 2. Rate Limiting funktioniert nicht

**Symptom:** Keine 429 Responses

**Mögliche Ursachen:**
1. Stick-Table nicht definiert
2. ACL falsch
3. Track nicht aktiv

**Debugging:**
```bash
# Stick-Table anzeigen
echo "show table" | socat /var/lib/haproxy/stats -
```

**Lösung:**
```haproxy
frontend http_frontend
    # WICHTIG: Stick-Table definieren
    stick-table type ip size 100k expire 30s store http_req_rate(10s)
    
    # WICHTIG: Track BEFORE deny
    http-request track-sc0 src if is_route
    http-request deny deny_status 429 if is_route { sc_http_req_rate(0) gt 100 }
```

### 3. Sticky Sessions funktionieren nicht

**Symptom:** Requests landen auf verschiedenen Servern

**Mögliche Ursachen:**
1. Cookie wird nicht gesetzt
2. Cookie wird nicht gesendet
3. Balance algorithm falsch

**Debugging:**
```bash
# Request mit Cookie-Inspektion
curl -v http://localhost/api

# Cookie in Response prüfen
# Set-Cookie: SERVERID=server1; path=/
```

**Lösung:**
```haproxy
backend backend_api
    cookie SERVERID insert indirect nocache
    server server1 api-1.internal:8080 cookie server1
    server server2 api-2.internal:8080 cookie server2
```

### 4. Headers werden nicht gesetzt

**Symptom:** X-Request-ID fehlt

**Mögliche Ursachen:**
1. ACL-Condition falsch
2. Direktive an falscher Stelle

**Lösung:**
```haproxy
frontend http_frontend
    # WICHTIG: if Condition muss matchen
    http-request set-header X-Request-ID "%[uuid()]" if is_route
    
    # NICHT im Backend setzen (zu spät)
```

### 5. Config Reload schlägt fehl

**Symptom:** `haproxy -c -f haproxy.cfg` zeigt Fehler

**Mögliche Ursachen:**
1. Syntax-Fehler
2. Fehlende Direktiven
3. Ungültige Werte

**Debugging:**
```bash
# Detaillierte Fehlerausgabe
haproxy -c -f haproxy.cfg -V

# Zeile für Zeile prüfen
haproxy -c -f haproxy.cfg -d
```

**Häufige Fehler:**
```haproxy
# FALSCH: Fehlende Quotes
http-request set-header X-Test value with spaces

# RICHTIG
http-request set-header X-Test "value with spaces"

# FALSCH: Ungültiger Balance Algorithm
balance round-robin

# RICHTIG
balance roundrobin
```

### 6. Performance-Probleme

**Symptom:** Hohe Latenz, niedrige Throughput

**Debugging:**
```bash
# Stats anzeigen
echo "show info" | socat /var/lib/haproxy/stats -

# Connection Limits prüfen
echo "show stat" | socat /var/lib/haproxy/stats -
```

**Tuning:**
```haproxy
global
    maxconn 10000  # Erhöhen für mehr gleichzeitige Connections
    
defaults
    timeout http-keep-alive 10s  # Connection Reuse
    option http-server-close
    
backend backend_api
    balance leastconn  # Bessere Verteilung bei ungleichen Requests
```

---

## Weiterführende Ressourcen

### Offizielle Dokumentation

- **HAProxy Docs**: https://docs.haproxy.org/
- **Configuration Manual**: https://cbonte.github.io/haproxy-dconv/2.9/configuration.html
- **Best Practices**: https://www.haproxy.com/documentation/hapee/latest/configuration/best-practices/

### GAL Dokumentation

- **Hauptdokumentation**: [README.md](https://github.com/pt9912/x-gal#readme)
- **Rate Limiting Guide**: [RATE_LIMITING.md](RATE_LIMITING.md)
- **Health Checks Guide**: [HEALTH_CHECKS.md](HEALTH_CHECKS.md)
- **Authentication Guide**: [AUTHENTICATION.md](AUTHENTICATION.md)

### Beispiele

- **HAProxy Examples**: [examples/haproxy-example.yaml](https://github.com/pt9912/x-gal/blob/main/examples/haproxy-example.yaml)
- **Alle Provider**: [examples/](../../examples/)

---

**Letzte Aktualisierung:** 2025-10-18  
**GAL Version:** 1.2.0  
**HAProxy Version:** 2.9+
