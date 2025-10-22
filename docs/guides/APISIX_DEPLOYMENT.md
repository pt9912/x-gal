# Apache APISIX Best Practices & Troubleshooting

**Best Practices und Troubleshooting für Apache APISIX Provider in GAL**

**Navigation:**
- [← Zurück zur APISIX Übersicht](APISIX.md)
- [← Feature-Implementierungen](APISIX_FEATURES.md)

## Inhaltsverzeichnis

1. [Best Practices](#best-practices)
2. [Troubleshooting](#troubleshooting)
3. [Zusammenfassung](#zusammenfassung)

---
## Best Practices

### 1. Verwende etcd für dynamische Konfiguration

etcd ermöglicht Änderungen ohne Neustart:

```yaml
apisix:
  config_center: etcd
etcd:
  host:
    - "http://etcd:2379"
  prefix: "/apisix"
  timeout: 30
```

### 2. Aktiviere Health Checks für Production

Kombiniere Active + Passive Health Checks:

```yaml
upstream:
  health_check:
    active:
      enabled: true
      path: /health
      interval: 5s
    passive:
      enabled: true
      max_failures: 3
```

### 3. Verwende limit-count für Rate Limiting

`limit-count` ist performanter als `limit-req`:

```yaml
routes:
  - path_prefix: /api
    rate_limit:
      enabled: true
      requests_per_second: 100
```

### 4. Aktiviere das Dashboard für Monitoring

```bash
docker run -d --name apisix-dashboard \
  -p 9000:9000 \
  apache/apisix-dashboard:latest
```

### 5. Verwende Serverless Lua für komplexe Logik

Für Transformationen, die über Plugins hinausgehen:

```yaml
routes:
  - path_prefix: /api
    body_transformation:
      enabled: true
      request:
        add_fields:
          trace_id: "{{uuid}}"
```

### 6. Konfiguriere Timeouts für alle Routes

```yaml
routes:
  - path_prefix: /api
    timeout:
      connect: 5s
      read: 30s
      send: 30s
```

### 7. Nutze Circuit Breaker für resiliente Services

```yaml
upstream:
  circuit_breaker:
    enabled: true
    max_failures: 5
    timeout: 30s
```

---

## Troubleshooting

### Problem 1: "etcd connection refused"

**Symptom**: APISIX startet nicht, Fehlermeldung: `connection refused: http://etcd:2379`

**Lösung**:
```bash
# etcd Status prüfen
docker ps | grep etcd

# etcd neu starten
docker start etcd

# APISIX Logs prüfen
docker logs apisix

# etcd-URL in config.yaml prüfen
etcd:
  host:
    - "http://localhost:2379"  # Verwende localhost wenn nicht in Docker network
```

### Problem 2: Health Checks schlagen fehl

**Symptom**: Upstream-Server werden als unhealthy markiert

**Lösung**:
```bash
# Prüfe Health Check Endpunkt
curl http://backend:8080/health

# Erweitere Timeout
upstream:
  health_check:
    active:
      timeout: 10s  # Erhöhen

# Prüfe APISIX Logs
docker logs apisix | grep health_checker
```

### Problem 3: Rate Limiting funktioniert nicht

**Symptom**: Requests werden nicht limitiert

**Lösung**:
```bash
# Prüfe Plugin-Konfiguration
curl http://localhost:9180/apisix/admin/routes/1 \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1"

# Stelle sicher, dass limit-count Plugin aktiv ist
{
  "plugins": {
    "limit-count": {
      "count": 100,
      "time_window": 1,
      "key": "remote_addr"
    }
  }
}

# Teste mit curl
for i in {1..110}; do curl http://localhost:9080/api; done
```

### Problem 4: JWT Authentication schlägt fehl

**Symptom**: 401 Unauthorized trotz gültigem Token

**Lösung**:
```bash
# Prüfe JWT-Plugin-Konfiguration
curl http://localhost:9180/apisix/admin/routes/1 \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1"

# Consumer mit JWT-Secret erstellen
curl -X PUT http://localhost:9180/apisix/admin/consumers \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  -d '{
    "username": "user1",
    "plugins": {
      "jwt-auth": {
        "key": "api-key",
        "secret": "secret-key"
      }
    }
  }'
```

### Problem 5: Plugin-Konfiguration wird nicht angewendet

**Symptom**: Plugin-Änderungen haben keine Wirkung

**Lösung**:
```bash
# etcd-Cache leeren
etcdctl del /apisix --prefix

# APISIX neu laden
docker exec apisix apisix reload

# Plugin-Status prüfen
curl http://localhost:9180/apisix/admin/plugins/list \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1"
```

### Problem 6: Hohe Latenz

**Symptom**: Requests dauern ungewöhnlich lange

**Lösung**:
```bash
# Prüfe APISIX Prometheus Metrics
curl http://localhost:9091/apisix/prometheus/metrics

# Aktiviere Access Logs mit Timing
nginx_config:
  http:
    access_log: "/dev/stdout"
    access_log_format: '$remote_addr - $upstream_response_time'

# Deaktiviere unnötige Plugins
# Nutze upstream keepalive
upstream:
  keepalive: 320
  keepalive_timeout: 60s
```

---

## Zusammenfassung

### APISIX mit GAL

GAL macht APISIX-Konfiguration einfach und provider-agnostisch:

**Vorteile**:
- ✅ **Einheitliche Konfiguration**: YAML statt JSON Admin API
- ✅ **Provider-Wechsel**: Von APISIX zu Envoy/Kong in Minuten
- ✅ **Feature-Abstraktion**: Keine APISIX-spezifischen Plugins im Config
- ✅ **Validierung**: Frühzeitige Fehlerkennung vor Deployment
- ✅ **Multi-Provider**: Parallel Configs für mehrere Gateways

**APISIX-Features komplett unterstützt**:
- Load Balancing (alle Algorithmen)
- Active/Passive Health Checks
- Rate Limiting (limit-count)
- Authentication (JWT, Basic, Key)
- CORS
- Timeout & Retry
- Circuit Breaker (api-breaker)
- WebSocket
- Header Manipulation
- Body Transformation (Serverless Lua)

**Best Use Cases für APISIX**:
1. **Cloud-Native Microservices**: Kubernetes + etcd Integration
2. **High Performance APIs**: Ultra-niedrige Latenz erforderlich
3. **Dynamic Configuration**: Häufige Config-Änderungen
4. **Dashboard-Driven**: Grafische Verwaltung bevorzugt
5. **Lua-Programmierbarkeit**: Custom Logic erforderlich

**Workflow**:
```bash
# 1. GAL-Konfiguration schreiben
vim config.yaml

# 2. APISIX-Config generieren
gal generate --config config.yaml --provider apisix --output apisix-config.yaml

# 3. Via Admin API anwenden
curl -X PUT http://localhost:9180/apisix/admin/routes/1 \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  -d @apisix-config.yaml

# 4. Testen
curl http://localhost:9080/api
```

**Links**:
- APISIX Website: https://apisix.apache.org/
- GitHub: https://github.com/apache/apisix
- Plugins: https://apisix.apache.org/docs/apisix/plugins/overview/
- Dashboard: https://github.com/apache/apisix-dashboard

---

**Navigation**:
- [← Zurück zur Übersicht](https://github.com/pt9912/x-gal#readme)
- [Envoy Provider Guide](ENVOY.md)
- [Kong Provider Guide](KONG.md)
- [Traefik Provider Guide](TRAEFIK.md)
- [Nginx Provider Guide](NGINX.md)
- [HAProxy Provider Guide](HAPROXY.md)
