# Traefik Best Practices & Troubleshooting

**Best Practices und Troubleshooting für Traefik Provider in GAL**

**Navigation:**
- [← Zurück zur Traefik Übersicht](TRAEFIK.md)
- [← Feature-Implementierungen](TRAEFIK_FEATURES.md)

## Inhaltsverzeichnis

1. [Best Practices](#best-practices)
2. [Troubleshooting](#troubleshooting)
3. [Zusammenfassung](#zusammenfassung)

---
## Best Practices

### 1. Verwende File Provider für GAL-Generated Configs

```yaml
# traefik.yml
providers:
  file:
    filename: /etc/traefik/dynamic-config.yml
    watch: true  # Auto-reload bei Änderungen
```

### 2. Aktiviere Health Checks für Production

```yaml
services:
  - name: api_service
    upstream:
      health_check:
        active:
          enabled: true
          path: /health
          interval: 10s
```

### 3. Nutze Middleware Chains für komplexe Logik

```yaml
http:
  routers:
    api_router:
      middlewares:
        - auth          # 1. Authentication
        - ratelimit     # 2. Rate limiting
        - cors          # 3. CORS
        - circuitbreaker  # 4. Circuit breaker
```

### 4. Konfiguriere Timeouts für alle Routes

```yaml
routes:
  - path_prefix: /api
    timeout:
      connect: 5s
      read: 30s
      idle: 300s
```

### 5. Verwende Let's Encrypt für automatisches HTTPS

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /letsencrypt/acme.json
      tlsChallenge: {}
```

### 6. Aktiviere Dashboard für Monitoring

```yaml
api:
  dashboard: true
  insecure: false  # Production: Verwende BasicAuth!
```

### 7. Nutze Retry für resiliente Services

```yaml
routes:
  - path_prefix: /api
    retry:
      enabled: true
      attempts: 3
      base_interval: 100ms
```

---

## Troubleshooting

### Problem 1: "No matching router found"

**Symptom**: 404 Not Found, obwohl Service existiert

**Lösung**:
```bash
# Prüfe Router-Regel
http:
  routers:
    my_router:
      rule: "PathPrefix(`/api`)"  # Achte auf Backticks!

# Traefik Logs prüfen
docker logs traefik | grep "my_router"

# Dashboard prüfen
open http://localhost:8080/dashboard/
```

### Problem 2: Health Checks schlagen fehl

**Symptom**: Backend-Server werden als unhealthy markiert

**Lösung**:
```bash
# Prüfe Health Check Endpunkt
curl http://backend:8080/health

# Erweitere Timeout
services:
  my_service:
    loadBalancer:
      healthCheck:
        timeout: 10s  # Erhöhen

# Traefik Logs prüfen
docker logs traefik | grep healthcheck
```

### Problem 3: Middleware wird nicht angewendet

**Symptom**: Rate Limiting/Auth funktioniert nicht

**Lösung**:
```bash
# Prüfe Middleware-Definition
http:
  middlewares:
    my_ratelimit:
      rateLimit:
        average: 100

# Prüfe Router-Middleware-Zuordnung
http:
  routers:
    my_router:
      middlewares:
        - my_ratelimit  # Muss exakt übereinstimmen!

# Dashboard prüfen
open http://localhost:8080/dashboard/
```

### Problem 4: Let's Encrypt Zertifikatsfehler

**Symptom**: HTTPS funktioniert nicht, Zertifikatsfehler

**Lösung**:
```bash
# Prüfe acme.json Berechtigungen
chmod 600 /letsencrypt/acme.json

# Prüfe Email und Domain
certificatesResolvers:
  letsencrypt:
    acme:
      email: valid@example.com  # Muss gültig sein!
      storage: /letsencrypt/acme.json

# Staging Environment für Tests
certificatesResolvers:
  letsencrypt:
    acme:
      caServer: "https://acme-staging-v02.api.letsencrypt.org/directory"

# Logs prüfen
docker logs traefik | grep acme
```

### Problem 5: File Provider lädt Änderungen nicht

**Symptom**: Änderungen in dynamic-config.yml werden nicht übernommen

**Lösung**:
```bash
# Prüfe watch: true
providers:
  file:
    filename: /etc/traefik/dynamic-config.yml
    watch: true  # Muss aktiviert sein!

# Prüfe Volume-Mount
docker run ... -v $(pwd)/dynamic-config.yml:/etc/traefik/dynamic-config.yml

# Manuelle Aktualisierung
docker exec traefik kill -USR1 1

# Logs prüfen
docker logs traefik | grep "Configuration loaded"
```

### Problem 6: Hohe Latenz

**Symptom**: Requests dauern ungewöhnlich lange

**Lösung**:
```bash
# Aktiviere Metrics
metrics:
  prometheus: {}

# Prüfe Metrics
curl http://localhost:8082/metrics | grep traefik_service

# Deaktiviere unnötige Middlewares
# Erhöhe Timeouts
serversTransports:
  default:
    forwardingTimeouts:
      dialTimeout: 10s
      responseHeaderTimeout: 30s

# Nutze Connection Pooling
serversTransports:
  default:
    maxIdleConnsPerHost: 200
```

---

## Zusammenfassung

### Traefik mit GAL

GAL macht Traefik-Konfiguration einfach und provider-agnostisch:

**Vorteile**:
- ✅ **Einheitliche Konfiguration**: YAML statt multiple Provider
- ✅ **Provider-Wechsel**: Von Traefik zu Envoy/Kong in Minuten
- ✅ **Feature-Abstraktion**: Keine Traefik-spezifischen Middlewares im Config
- ✅ **Validierung**: Frühzeitige Fehlerkennung vor Deployment
- ✅ **Multi-Provider**: Parallel Configs für mehrere Gateways

**Traefik-Features unterstützt**:
- Load Balancing (mit Sticky Sessions)
- Active Health Checks
- Rate Limiting (rateLimit Middleware)
- Basic Authentication
- CORS (headers Middleware)
- Timeout & Retry
- Circuit Breaker
- WebSocket (native)
- Header Manipulation
- ⚠️ Body Transformation (nicht nativ, Workarounds verfügbar)

**Best Use Cases für Traefik**:
1. **Docker/Kubernetes**: Automatische Service Discovery
2. **Let's Encrypt**: Automatisches HTTPS erforderlich
3. **Cloud-Native Microservices**: Container-basierte Architekturen
4. **Einfache Konfiguration**: Schnelles Setup bevorzugt
5. **Dashboard-Driven**: Echtzeit-Monitoring erforderlich

**Workflow**:
```bash
# 1. GAL-Konfiguration schreiben
vim config.yaml

# 2. Traefik Dynamic Config generieren
gal generate --config config.yaml --provider traefik --output traefik-dynamic.yml

# 3. Traefik starten mit File Provider
docker run -d \
  -v $(pwd)/traefik-dynamic.yml:/etc/traefik/dynamic-config.yml \
  -v $(pwd)/traefik.yml:/etc/traefik/traefik.yml \
  traefik:latest

# 4. Testen
curl http://localhost:80/api

# 5. Dashboard öffnen
open http://localhost:8080/dashboard/
```

**Links**:
- Traefik Website: https://traefik.io/
- GitHub: https://github.com/traefik/traefik
- Docs: https://doc.traefik.io/traefik/
- Plugins: https://plugins.traefik.io/

---

**Navigation**:
- [← Zurück zur Übersicht](https://github.com/pt9912/x-gal#readme)
- [Envoy Provider Guide](ENVOY.md)
- [Kong Provider Guide](KONG.md)
- [APISIX Provider Guide](APISIX.md)
- [Nginx Provider Guide](NGINX.md)
- [HAProxy Provider Guide](HAPROXY.md)
