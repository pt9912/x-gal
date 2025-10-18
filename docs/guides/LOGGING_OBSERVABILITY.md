# Logging & Observability Guide

**Feature Status:** ✅ Vollständig implementiert (v1.2.0)

Umfassendes Logging und Observability für alle Gateway-Provider mit strukturiertem Logging, Metriken-Export und Monitoring-Integration.

## Übersicht

Logging & Observability bietet:

- **Strukturiertes Logging**: JSON- oder textbasierte Access Logs
- **Metriken-Export**: Prometheus und OpenTelemetry Integration
- **Log Sampling**: Reduzierung des Log-Volumens bei High-Traffic
- **Custom Fields**: Zusätzliche Metadaten in Logs
- **Provider-agnostisch**: Einheitliche Konfiguration für alle Provider

### Feature-Matrix

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy |
|---------|-------|------|--------|---------|-------|---------|
| JSON Logs | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Text Logs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Custom Fields | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Log Sampling | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| Prometheus | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| OpenTelemetry | ✅ | ⚠️ | ⚠️ | ✅ | ❌ | ❌ |

**Legende:**
- ✅ Native Unterstützung
- ⚠️ Teilweise/Externe Tools erforderlich
- ❌ Nicht unterstützt

## Schnellstart

### Beispiel 1: Basis JSON Logging

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

  # Strukturiertes Logging aktivieren
  logging:
    enabled: true
    format: json  # json oder text
    level: info   # debug, info, warning, error
    access_log_path: /var/log/gateway/access.log
    error_log_path: /var/log/gateway/error.log

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.internal
      port: 8080
    routes:
      - path_prefix: /api
```

**Generiertes Envoy Access Log (JSON):**
```json
{
  "request_id": "12345678-1234-1234-1234-123456789abc",
  "method": "GET",
  "path": "/api/users",
  "protocol": "HTTP/1.1",
  "response_code": "200",
  "bytes_received": "0",
  "bytes_sent": "1234",
  "duration": "45",
  "upstream_service_time": "42",
  "x_forwarded_for": "10.0.0.1"
}
```

### Beispiel 2: Prometheus Metriken

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

  # Prometheus Metriken aktivieren
  metrics:
    enabled: true
    exporter: prometheus  # prometheus, opentelemetry, both
    prometheus_port: 9090
    prometheus_path: /metrics

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.internal
      port: 8080
    routes:
      - path_prefix: /api
```

**Metriken abrufen:**
```bash
# Envoy
curl http://localhost:9901/stats/prometheus

# Kong
curl http://localhost:8001/metrics

# APISIX
curl http://localhost:9091/apisix/prometheus/metrics

# Traefik (benötigt static config für metrics port)
curl http://localhost:8082/metrics
```

### Beispiel 3: Logging + Metriken + Custom Fields

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

  # Logging mit Custom Fields
  logging:
    enabled: true
    format: json
    level: info
    access_log_path: /var/log/gateway/access.log
    sample_rate: 0.5  # Nur 50% der Requests loggen
    include_headers:
      - X-Request-ID
      - User-Agent
      - X-Correlation-ID
    exclude_paths:
      - /health
      - /metrics
      - /ping
    custom_fields:
      environment: production
      cluster: eu-west-1
      version: v1.2.0

  # Prometheus + OpenTelemetry
  metrics:
    enabled: true
    exporter: both
    prometheus_port: 9090
    opentelemetry_endpoint: http://otel-collector:4317
    custom_labels:
      cluster: eu-west-1
      environment: production

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      host: api.internal
      port: 8080
    routes:
      - path_prefix: /api
```

## Konfigurationsoptionen

### LoggingConfig

Konfiguration für Access Logs und Error Logs.

```yaml
logging:
  enabled: true                              # Logging aktivieren (default: true)
  format: json                               # Log-Format: json, text, custom (default: json)
  level: info                                # Log-Level: debug, info, warning, error (default: info)
  access_log_path: /var/log/gateway/access.log  # Pfad zum Access Log
  error_log_path: /var/log/gateway/error.log    # Pfad zum Error Log
  sample_rate: 1.0                           # Sampling-Rate 0.0-1.0 (default: 1.0 = 100%)
  include_request_body: false                # Request Body in Logs (default: false)
  include_response_body: false               # Response Body in Logs (default: false)
  include_headers:                           # Headers in Logs einbeziehen
    - X-Request-ID
    - User-Agent
    - X-Correlation-ID
  exclude_paths:                             # Pfade von Logging ausschließen
    - /health
    - /metrics
    - /ping
  custom_fields:                             # Zusätzliche Felder in Logs
    environment: production
    cluster: eu-west-1
    version: v1.2.0
```

**Parameter:**

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `enabled` | bool | `true` | Logging aktivieren/deaktivieren |
| `format` | string | `json` | Log-Format: `json`, `text`, `custom` |
| `level` | string | `info` | Log-Level: `debug`, `info`, `warning`, `error` |
| `access_log_path` | string | `/var/log/gateway/access.log` | Pfad zum Access Log |
| `error_log_path` | string | `/var/log/gateway/error.log` | Pfad zum Error Log |
| `sample_rate` | float | `1.0` | Sampling-Rate (0.0 = 0%, 1.0 = 100%) |
| `include_request_body` | bool | `false` | Request Body in Logs einbeziehen |
| `include_response_body` | bool | `false` | Response Body in Logs einbeziehen |
| `include_headers` | list | `["X-Request-ID", "User-Agent"]` | Headers in Logs |
| `exclude_paths` | list | `["/health", "/metrics"]` | Pfade von Logging ausschließen |
| `custom_fields` | dict | `{}` | Zusätzliche Felder (Key-Value Paare) |

### MetricsConfig

Konfiguration für Metriken-Export (Prometheus, OpenTelemetry).

```yaml
metrics:
  enabled: true                              # Metriken aktivieren (default: true)
  exporter: prometheus                       # Exporter: prometheus, opentelemetry, both
  prometheus_port: 9090                      # Prometheus Metriken Port (default: 9090)
  prometheus_path: /metrics                  # Prometheus Metriken Pfad (default: /metrics)
  opentelemetry_endpoint: http://otel-collector:4317  # OpenTelemetry Collector Endpoint
  include_histograms: true                   # Request Duration Histograms (default: true)
  include_counters: true                     # Request/Error Counter (default: true)
  custom_labels:                             # Zusätzliche Labels für Metriken
    cluster: prod
    region: eu-west-1
```

**Parameter:**

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `enabled` | bool | `true` | Metriken aktivieren/deaktivieren |
| `exporter` | string | `prometheus` | Exporter: `prometheus`, `opentelemetry`, `both` |
| `prometheus_port` | int | `9090` | Port für Prometheus Metriken |
| `prometheus_path` | string | `/metrics` | Pfad für Prometheus Metriken |
| `opentelemetry_endpoint` | string | `""` | OpenTelemetry Collector Endpoint (gRPC) |
| `include_histograms` | bool | `true` | Request Duration Histograms einbeziehen |
| `include_counters` | bool | `true` | Request/Error Counter einbeziehen |
| `custom_labels` | dict | `{}` | Zusätzliche Labels (Key-Value Paare) |

## Provider-Implementierungen

### 1. Envoy

**Logging:**
- Native JSON Access Logs über `envoy.access_loggers.file`
- Alle Standard-Felder: request_id, method, path, protocol, response_code, duration, etc.
- Custom Fields über `json_format`
- Log Sampling über `runtime_filter` mit `percent_sampled`

**Metriken:**
- Prometheus: Admin Interface `/stats/prometheus`
- OpenTelemetry: `stats_sinks` mit `envoy.stat_sinks.open_telemetry`

**Beispiel-Konfiguration:**
```yaml
access_log:
- name: envoy.access_loggers.file
  typed_config:
    '@type': type.googleapis.com/envoy.extensions.access_loggers.file.v3.FileAccessLog
    path: /var/log/envoy/access.log
    json_format:
      request_id: "%REQ(X-REQUEST-ID)%"
      method: "%REQ(:METHOD)%"
      path: "%REQ(X-ENVOY-ORIGINAL-PATH?:PATH)%"
      protocol: "%PROTOCOL%"
      response_code: "%RESPONSE_CODE%"
      duration: "%DURATION%"
      environment: "production"
    filter:
      runtime_filter:
        runtime_key: access_log_sampling
        percent_sampled:
          numerator: 50
          denominator: HUNDRED
```

**Metriken abrufen:**
```bash
curl http://localhost:9901/stats/prometheus
```

### 2. Kong

**Logging:**
- `file-log` Plugin für Access Logs
- JSON Format Support
- Custom Fields via `custom_fields_by_lua`

**Metriken:**
- `prometheus` Plugin
- Metriken über Kong Admin API: `http://localhost:8001/metrics`

**Beispiel-Konfiguration:**
```yaml
plugins:
- name: file-log
  config:
    path: /var/log/kong/access.log
    format: json
    custom_fields_by_lua:
      environment: production
      cluster: eu-west-1

- name: prometheus
  config: {}
```

**Metriken abrufen:**
```bash
curl http://localhost:8001/metrics
```

### 3. APISIX

**Logging:**
- `file-logger` Plugin
- `include_req_body` und `include_resp_body` Optionen

**Metriken:**
- `prometheus` Plugin
- Metriken-Endpoint: `:9091/apisix/prometheus/metrics`

**Beispiel-Konfiguration:**
```yaml
global_plugins:
  file-logger:
    path: /var/log/apisix/access.log
    include_req_body: true
    include_resp_body: false

  prometheus: {}
```

**Metriken abrufen:**
```bash
curl http://localhost:9091/apisix/prometheus/metrics
```

### 4. Traefik

**Logging:**
- `accessLog` Konfiguration
- JSON oder Common Format
- Custom Fields Support

**Metriken:**
- `prometheus` via `entryPoint`
- Benötigt static config für Metrics Port

**Beispiel-Konfiguration:**
```yaml
accessLog:
  filePath: /var/log/traefik/access.log
  format: json
  fields:
    defaultMode: keep
    headers:
      defaultMode: keep

metrics:
  prometheus:
    entryPoint: metrics
```

**Static Config (traefik.yml):**
```yaml
entryPoints:
  metrics:
    address: ":8082"
```

**Metriken abrufen:**
```bash
curl http://localhost:8082/metrics
```

### 5. Nginx

**Logging:**
- `log_format` mit JSON Support
- Konfigurierbare Log Levels (debug, info, warn, error)
- Custom Fields in JSON Format

**Metriken:**
- Externe Exporter erforderlich: `nginx-prometheus-exporter`
- Oder VTS Module (nginx-module-vts)

**Beispiel-Konfiguration:**
```nginx
http {
    # JSON Log Format
    log_format json_combined escape=json
      '{'
        '"time_local":"$time_local",'
        '"remote_addr":"$remote_addr",'
        '"request_method":"$request_method",'
        '"request_uri":"$request_uri",'
        '"status":"$status",'
        '"request_time":"$request_time",'
        '"environment":"production"'
      '}';

    access_log /var/log/nginx/access.log json_combined;
    error_log /var/log/nginx/error.log info;
}
```

**Metriken mit nginx-prometheus-exporter:**
```bash
# Exporter starten
nginx-prometheus-exporter -nginx.scrape-uri=http://localhost:8080/stub_status

# Metriken abrufen
curl http://localhost:9113/metrics
```

### 6. HAProxy

**Logging:**
- Syslog Logging
- Log Level Mapping (debug, info, notice, err)
- JSON Format über `log-format` Directive

**Metriken:**
- Stats Endpoint: `/stats;csv`
- Externe Exporter: `haproxy_exporter`

**Beispiel-Konfiguration:**
```haproxy
global
    log 127.0.0.1 local0 info
    # JSON format requires log-format directive

defaults
    log global
    option httplog
```

**Metriken mit haproxy_exporter:**
```bash
# Exporter starten
haproxy_exporter --haproxy.scrape-uri="http://localhost:8404/stats;csv"

# Metriken abrufen
curl http://localhost:9101/metrics
```

## Häufige Anwendungsfälle

### 1. Production API mit vollständigem Logging

High-Traffic API mit strukturiertem Logging, Custom Fields und Metriken.

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

  logging:
    enabled: true
    format: json
    level: info
    access_log_path: /var/log/gateway/access.log
    error_log_path: /var/log/gateway/error.log
    include_headers:
      - X-Request-ID
      - X-Correlation-ID
      - User-Agent
      - X-Forwarded-For
    exclude_paths:
      - /health
      - /metrics
    custom_fields:
      environment: production
      cluster: eu-west-1
      service: api-gateway
      version: v1.2.0

  metrics:
    enabled: true
    exporter: both
    prometheus_port: 9090
    opentelemetry_endpoint: http://otel-collector:4317
    custom_labels:
      environment: production
      cluster: eu-west-1

services:
  - name: api_service
    type: rest
    protocol: http
    upstream:
      targets:
        - host: api-1.internal
          port: 8080
        - host: api-2.internal
          port: 8080
      load_balancer:
        algorithm: least_conn
    routes:
      - path_prefix: /api
```

**Anwendungsfall:** Production API mit vollständigem Observability Stack.

### 2. High-Traffic API mit Log Sampling

Reduzierung des Log-Volumens bei hohem Traffic durch Sampling.

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

  logging:
    enabled: true
    format: json
    level: warning  # Nur Warnings/Errors
    access_log_path: /var/log/gateway/access.log
    sample_rate: 0.1  # Nur 10% der Requests loggen
    exclude_paths:
      - /health
      - /metrics
      - /ping
      - /favicon.ico
    custom_fields:
      environment: production
      sampling: "10percent"

services:
  - name: high_traffic_api
    type: rest
    protocol: http
    upstream:
      host: api.internal
      port: 8080
    routes:
      - path_prefix: /api
```

**Anwendungsfall:** High-Traffic API (>10k req/s) mit reduziertem Log-Volumen.

### 3. Microservices mit Distributed Tracing

Correlation IDs und Trace IDs für Distributed Tracing.

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

  logging:
    enabled: true
    format: json
    level: info
    access_log_path: /var/log/gateway/access.log
    include_headers:
      - X-Request-ID
      - X-Correlation-ID
      - X-B3-TraceId       # Zipkin/Jaeger
      - X-B3-SpanId
      - Traceparent        # W3C Trace Context
    custom_fields:
      service: gateway
      span_kind: server

  metrics:
    enabled: true
    exporter: opentelemetry
    opentelemetry_endpoint: http://otel-collector:4317

services:
  - name: user_service
    type: rest
    protocol: http
    upstream:
      host: users.internal
      port: 8080
    routes:
      - path_prefix: /users

  - name: order_service
    type: rest
    protocol: http
    upstream:
      host: orders.internal
      port: 8080
    routes:
      - path_prefix: /orders
```

**Anwendungsfall:** Microservices-Architektur mit Distributed Tracing (Jaeger/Zipkin/OpenTelemetry).

### 4. Development Environment mit Debug Logging

Detailliertes Logging für Entwicklung und Debugging.

```yaml
version: "1.0"
provider: nginx

global:
  host: 0.0.0.0
  port: 80

  logging:
    enabled: true
    format: json
    level: debug  # Alle Debug-Informationen
    access_log_path: /var/log/nginx/access.log
    error_log_path: /var/log/nginx/error.log
    include_request_body: true   # Request Body loggen
    include_response_body: true  # Response Body loggen
    custom_fields:
      environment: development
      debug: "true"

services:
  - name: dev_api
    type: rest
    protocol: http
    upstream:
      host: localhost
      port: 3000
    routes:
      - path_prefix: /api
```

**Anwendungsfall:** Lokale Entwicklungsumgebung mit maximalem Logging.

### 5. Security Audit Logging

Umfassendes Logging für Security Audits und Compliance.

```yaml
version: "1.0"
provider: envoy

global:
  host: 0.0.0.0
  port: 10000
  admin_port: 9901

  logging:
    enabled: true
    format: json
    level: info
    access_log_path: /var/log/gateway/audit.log
    sample_rate: 1.0  # Alle Requests loggen
    include_headers:
      - Authorization
      - X-API-Key
      - X-Client-ID
      - X-Forwarded-For
      - User-Agent
      - X-Real-IP
    custom_fields:
      audit: "true"
      compliance: pci-dss
      retention_days: "365"

  metrics:
    enabled: true
    exporter: prometheus
    prometheus_port: 9090

services:
  - name: payment_api
    type: rest
    protocol: http
    upstream:
      host: payment.internal
      port: 8080
    routes:
      - path_prefix: /payment
        authentication:
          enabled: true
          type: jwt
          jwt:
            issuer: https://auth.example.com
```

**Anwendungsfall:** Payment API mit vollständigem Audit Trail für PCI-DSS Compliance.

### 6. Multi-Tenant SaaS mit Tenant-spezifischem Logging

Custom Fields für Tenant-Identifikation.

```yaml
version: "1.0"
provider: kong

global:
  host: 0.0.0.0
  port: 8000

  logging:
    enabled: true
    format: json
    level: info
    access_log_path: /var/log/kong/access.log
    include_headers:
      - X-Tenant-ID
      - X-Organization-ID
      - X-User-ID
    custom_fields:
      environment: production
      service_type: multi-tenant-saas

  metrics:
    enabled: true
    exporter: prometheus

services:
  - name: saas_api
    type: rest
    protocol: http
    upstream:
      host: api.internal
      port: 8080
    routes:
      - path_prefix: /api
```

**Anwendungsfall:** Multi-Tenant SaaS mit Tenant-spezifischem Logging für Billing und Analytics.

## Best Practices

### 1. Strukturiertes JSON Logging verwenden

**Empfehlung:** Verwende JSON-Format für Access Logs in Production.

**Vorteile:**
- Einfaches Parsing durch Log-Aggregatoren (ELK, Splunk, Grafana Loki)
- Strukturierte Queries möglich
- Automatische Feld-Extraktion

```yaml
logging:
  format: json  # ✅ EMPFOHLEN für Production
  # format: text  # Nur für lokale Entwicklung
```

### 2. Log Sampling bei High-Traffic

**Empfehlung:** Verwende Log Sampling bei sehr hohem Traffic (>5k req/s).

```yaml
logging:
  sample_rate: 0.1  # 10% sampling bei sehr hohem Traffic
  # sample_rate: 1.0  # 100% bei niedrigem/mittlerem Traffic
```

**Faustregel:**
- < 1k req/s: `sample_rate: 1.0` (100%)
- 1k-5k req/s: `sample_rate: 0.5` (50%)
- 5k-10k req/s: `sample_rate: 0.2` (20%)
- > 10k req/s: `sample_rate: 0.1` (10%)

### 3. Health Check Endpoints ausschließen

**Empfehlung:** Schließe Health Checks und Monitoring-Endpoints vom Logging aus.

```yaml
logging:
  exclude_paths:
    - /health
    - /metrics
    - /ping
    - /readiness
    - /liveness
    - /_status
```

### 4. Custom Fields für Kontext verwenden

**Empfehlung:** Füge Custom Fields für Umgebung, Cluster, Version hinzu.

```yaml
logging:
  custom_fields:
    environment: production     # ✅ WICHTIG
    cluster: eu-west-1         # ✅ WICHTIG
    version: v1.2.0            # ✅ WICHTIG
    datacenter: aws-eu-west-1
    team: platform
```

### 5. Prometheus + OpenTelemetry kombinieren

**Empfehlung:** Verwende beide Exporter für maximale Flexibilität.

```yaml
metrics:
  exporter: both  # ✅ Prometheus + OpenTelemetry
  prometheus_port: 9090
  opentelemetry_endpoint: http://otel-collector:4317
```

**Vorteile:**
- Prometheus: Pull-based Metriken für Alerting
- OpenTelemetry: Push-based für Traces + Metrics

### 6. Log Rotation konfigurieren

**Empfehlung:** Konfiguriere Log Rotation mit `logrotate`.

```bash
# /etc/logrotate.d/gateway
/var/log/gateway/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        # Signal reload (provider-spezifisch)
        systemctl reload envoy || true
    endscript
}
```

### 7. Zentrale Log-Aggregation verwenden

**Empfehlung:** Verwende zentrale Log-Aggregation (ELK, Grafana Loki, Splunk).

**Setup-Beispiel mit Fluentd:**
```yaml
# fluentd.conf
<source>
  @type tail
  path /var/log/gateway/access.log
  pos_file /var/log/td-agent/gateway.pos
  tag gateway.access
  <parse>
    @type json
    time_format %Y-%m-%dT%H:%M:%S.%NZ
  </parse>
</source>

<match gateway.**>
  @type elasticsearch
  host elasticsearch.internal
  port 9200
  logstash_format true
  logstash_prefix gateway
</match>
```

## Troubleshooting

### Problem 1: Logs werden nicht geschrieben

**Symptome:**
- Access Log Datei bleibt leer
- Keine Log-Einträge sichtbar

**Lösungen:**

1. **Prüfe Dateiberechtigungen:**
```bash
# Verzeichnis und Datei erstellen
sudo mkdir -p /var/log/gateway
sudo touch /var/log/gateway/access.log
sudo chown gateway:gateway /var/log/gateway/access.log
sudo chmod 644 /var/log/gateway/access.log
```

2. **Prüfe Gateway-Prozess Benutzer:**
```bash
# Envoy
ps aux | grep envoy
# User muss Schreibrechte auf Log-Datei haben
```

3. **Prüfe Logging-Konfiguration:**
```yaml
logging:
  enabled: true  # ✅ Muss true sein
  access_log_path: /var/log/gateway/access.log  # Pfad prüfen
```

### Problem 2: JSON Parsing Fehler

**Symptome:**
- Log-Aggregator kann JSON nicht parsen
- Fehlermeldung: "Invalid JSON"

**Lösungen:**

1. **Prüfe JSON Format:**
```bash
# Teste ob Log valides JSON ist
tail -1 /var/log/gateway/access.log | jq .
```

2. **Escape Sonderzeichen in Custom Fields:**
```yaml
logging:
  custom_fields:
    description: "API Gateway"  # ✅ Mit Quotes
    # description: API Gateway  # ❌ Könnte Probleme verursachen
```

3. **Provider-spezifische Syntax prüfen:**
```nginx
# Nginx: Escape JSON
log_format json_combined escape=json
  '{...}';
```

### Problem 3: Prometheus Metriken nicht verfügbar

**Symptome:**
- `/metrics` Endpoint gibt 404
- Prometheus kann Gateway nicht scrapen

**Lösungen:**

1. **Prüfe Metrics-Konfiguration:**
```yaml
metrics:
  enabled: true  # ✅ Muss true sein
  exporter: prometheus
  prometheus_port: 9090
```

2. **Prüfe Provider-spezifischen Endpoint:**
```bash
# Envoy
curl http://localhost:9901/stats/prometheus

# Kong
curl http://localhost:8001/metrics

# APISIX
curl http://localhost:9091/apisix/prometheus/metrics

# Traefik (benötigt static config!)
curl http://localhost:8082/metrics
```

3. **Firewall-Regeln prüfen:**
```bash
# Port 9090 öffnen
sudo ufw allow 9090/tcp
```

### Problem 4: Hoher Disk Space Verbrauch

**Symptome:**
- Log-Dateien wachsen sehr schnell
- Disk Space läuft voll

**Lösungen:**

1. **Log Sampling aktivieren:**
```yaml
logging:
  sample_rate: 0.1  # Nur 10% loggen
```

2. **Health Check Endpoints ausschließen:**
```yaml
logging:
  exclude_paths:
    - /health
    - /metrics
    - /ping
```

3. **Log Rotation einrichten:**
```bash
# /etc/logrotate.d/gateway
/var/log/gateway/*.log {
    daily
    rotate 7
    compress
}
```

4. **Log Level erhöhen:**
```yaml
logging:
  level: warning  # Nur Warnings/Errors (statt info/debug)
```

### Problem 5: OpenTelemetry Connection Failed

**Symptome:**
- OpenTelemetry Metriken werden nicht exportiert
- Fehlermeldung: "Connection refused"

**Lösungen:**

1. **Prüfe OpenTelemetry Collector:**
```bash
# Ist Collector erreichbar?
curl http://otel-collector:4317
```

2. **Prüfe Endpoint-Konfiguration:**
```yaml
metrics:
  exporter: opentelemetry
  opentelemetry_endpoint: http://otel-collector:4317  # gRPC Endpoint
  # NICHT: http://otel-collector:4318  # Das ist HTTP
```

3. **Netzwerk-Konnektivität prüfen:**
```bash
# Von Gateway-Container aus
ping otel-collector
telnet otel-collector 4317
```

### Problem 6: Log Performance Impact

**Symptome:**
- Gateway wird langsam
- Hohe CPU/Memory Nutzung durch Logging

**Lösungen:**

1. **Asynchrones Logging aktivieren (provider-spezifisch):**
```nginx
# Nginx
access_log /var/log/nginx/access.log buffer=32k flush=5s;
```

2. **Log Sampling verwenden:**
```yaml
logging:
  sample_rate: 0.5  # 50% weniger Writes
```

3. **Logs auf schnelleres Storage verschieben:**
```bash
# SSD statt HDD
# Oder RAM Disk für sehr hohen Traffic
sudo mount -t tmpfs -o size=1G tmpfs /var/log/gateway
```

4. **Body Logging deaktivieren:**
```yaml
logging:
  include_request_body: false   # ✅
  include_response_body: false  # ✅
```

## Zusammenfassung

Logging & Observability bietet:

✅ **Strukturiertes Logging**: JSON/Text Logs mit Custom Fields
✅ **Metriken-Export**: Prometheus & OpenTelemetry
✅ **Log Sampling**: Traffic-Reduzierung bei High Load
✅ **Provider-agnostisch**: Einheitliche Config für alle 6 Provider
✅ **Production-Ready**: Best Practices und Troubleshooting

**Nächste Schritte:**
1. Logging in Production aktivieren
2. Prometheus Scraping einrichten
3. Log-Aggregation Setup (ELK/Loki)
4. Alerting Rules konfigurieren
5. Dashboards erstellen (Grafana)

**Siehe auch:**
- [Timeout & Retry Policies](TIMEOUT_RETRY.md)
- [Health Checks & Load Balancing](HEALTH_CHECKS.md)
- [Authentication Guide](AUTHENTICATION.md)
