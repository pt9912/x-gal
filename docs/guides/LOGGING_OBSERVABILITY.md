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

### GCP API Gateway

GCP API Gateway bietet native Integration mit Cloud Logging, Cloud Monitoring und Cloud Trace.

**Logging:**
- Cloud Logging Integration (automatisch aktiviert)
- Strukturierte JSON Logs
- Request/Response Logging
- Trace Context für Distributed Tracing

**Metriken:**
- Cloud Monitoring Metriken (automatisch)
- Request Rate, Error Rate, Latency
- Custom Metrics via Backend Services
- Prometheus-Export via Cloud Monitoring

**Cloud Logging (automatisch aktiviert):**
```yaml
swagger: "2.0"
info:
  title: "API with Logging"
  version: "1.0.0"

x-google-backend:
  address: https://backend.example.com
  deadline: 30.0

paths:
  /api/users:
    get:
      summary: "List users"
      operationId: listUsers
```

**Cloud Logging Log-Einträge:**
```json
{
  "httpRequest": {
    "requestMethod": "GET",
    "requestUrl": "https://my-gateway-xyz.uc.gateway.dev/api/users",
    "status": 200,
    "responseSize": "1234",
    "userAgent": "Mozilla/5.0...",
    "remoteIp": "203.0.113.42",
    "latency": "0.123s"
  },
  "timestamp": "2025-10-20T10:30:00.123456Z",
  "severity": "INFO",
  "trace": "projects/my-project/traces/abc123...",
  "spanId": "def456...",
  "resource": {
    "type": "api",
    "labels": {
      "project_id": "my-project",
      "service": "my-gateway-xyz.uc.gateway.dev",
      "method": "google.api.gateway.v1.ApiGatewayService.HandleRequest"
    }
  }
}
```

**Logs abfragen mit gcloud:**
```bash
# Alle API Gateway Logs
gcloud logging read "resource.type=api" \
  --project=my-project \
  --limit=100 \
  --format=json

# Fehler-Logs (4xx/5xx)
gcloud logging read "resource.type=api AND httpRequest.status>=400" \
  --project=my-project \
  --limit=50

# Logs für spezifischen Endpoint
gcloud logging read "resource.type=api AND httpRequest.requestUrl=~\"/api/users\"" \
  --project=my-project \
  --limit=20

# Logs mit Latency > 1s
gcloud logging read "resource.type=api AND httpRequest.latency>\"1s\"" \
  --project=my-project \
  --limit=30

# JSON-formatierte Logs mit jq parsen
gcloud logging read "resource.type=api" \
  --project=my-project \
  --format=json \
  --limit=10 | jq '.[] | {time: .timestamp, method: .httpRequest.requestMethod, url: .httpRequest.requestUrl, status: .httpRequest.status, latency: .httpRequest.latency}'
```

**Cloud Monitoring Metriken:**
```bash
# Request Count Metrik
gcloud monitoring time-series list \
  --filter='metric.type="serviceruntime.googleapis.com/api/request_count"' \
  --project=my-project \
  --format=json

# Request Latency (P50, P95, P99)
gcloud monitoring time-series list \
  --filter='metric.type="serviceruntime.googleapis.com/api/request_latencies"' \
  --project=my-project \
  --format=json

# Error Rate
gcloud monitoring time-series list \
  --filter='metric.type="serviceruntime.googleapis.com/api/request_count" AND metric.label.response_code_class="5xx"' \
  --project=my-project \
  --format=json
```

**Cloud Trace für Distributed Tracing:**
```bash
# Traces abrufen
gcloud trace traces list \
  --project=my-project \
  --limit=10

# Trace Details anzeigen
gcloud trace traces describe TRACE_ID \
  --project=my-project
```

**Cloud Console Log Explorer:**
```
# Log Explorer Query Language
resource.type="api"
httpRequest.requestUrl=~"/api/users"
severity>=ERROR
timestamp>"2025-10-20T00:00:00Z"
```

**Cloud Monitoring Dashboards:**
```bash
# Dashboard mit API Metriken erstellen
cat > dashboard.json <<EOF
{
  "displayName": "API Gateway Metrics",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"serviceruntime.googleapis.com/api/request_count\" resource.type=\"api\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "xPos": 6,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Error Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"serviceruntime.googleapis.com/api/request_count\" resource.type=\"api\" metric.label.response_code_class=\"5xx\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF

# Dashboard erstellen
gcloud monitoring dashboards create --config-from-file=dashboard.json \
  --project=my-project
```

**Alerting Policies:**
```bash
# Alert bei hoher Error Rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="API Gateway High Error Rate" \
  --condition-display-name="Error Rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s \
  --condition-filter='metric.type="serviceruntime.googleapis.com/api/request_count" resource.type="api" metric.label.response_code_class="5xx"' \
  --project=my-project

# Alert bei hoher Latency
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="API Gateway High Latency" \
  --condition-display-name="P95 Latency > 1s" \
  --condition-threshold-value=1000 \
  --condition-threshold-duration=300s \
  --condition-filter='metric.type="serviceruntime.googleapis.com/api/request_latencies"' \
  --project=my-project
```

**Log-basierte Metriken:**
```bash
# Custom Log-basierte Metrik erstellen
gcloud logging metrics create api_custom_metric \
  --description="Custom API metric" \
  --log-filter='resource.type="api" AND httpRequest.requestUrl=~"/api/critical"' \
  --value-extractor='EXTRACT(httpRequest.latency)' \
  --metric-kind=DELTA \
  --value-type=DISTRIBUTION \
  --project=my-project
```

**Deployment mit Logging:**
```bash
# API Gateway deployen (Logging automatisch aktiviert)
gcloud api-gateway api-configs create config-v1 \
  --api=my-api \
  --openapi-spec=openapi.yaml \
  --project=my-project

gcloud api-gateway gateways create my-gateway \
  --api=my-api \
  --api-config=config-v1 \
  --location=us-central1 \
  --project=my-project

# Logs in Echtzeit verfolgen
gcloud logging tail "resource.type=api" \
  --project=my-project
```

**GCP API Gateway Besonderheiten:**
- ✅ Cloud Logging automatisch aktiviert (keine Konfiguration erforderlich)
- ✅ Strukturierte JSON Logs mit Request/Response Details
- ✅ Cloud Trace Integration für Distributed Tracing
- ✅ Cloud Monitoring Metriken (Request Rate, Error Rate, Latency)
- ✅ X-Cloud-Trace-Context Header automatisch gesetzt
- ✅ Log-basierte Metriken und Alerting
- ✅ Integration mit Cloud Operations Suite
- ⚠️ Keine Log Sampling-Konfiguration (alle Requests werden geloggt)
- ⚠️ Keine Custom Log Fields auf Gateway-Ebene (nur via Backend)

**Beispiel: Complete Observability Setup:**
```bash
# 1. API Gateway deployen
gcloud api-gateway gateways create prod-gateway \
  --api=my-api \
  --api-config=config-v1 \
  --location=us-central1 \
  --project=my-project

# 2. Log Sink für BigQuery erstellen (Long-term Storage)
gcloud logging sinks create api-gateway-bq-sink \
  bigquery.googleapis.com/projects/my-project/datasets/api_logs \
  --log-filter='resource.type="api"' \
  --project=my-project

# 3. Alerting Policy erstellen
gcloud alpha monitoring policies create \
  --notification-channels=EMAIL_CHANNEL_ID \
  --display-name="API Gateway Error Rate Alert" \
  --condition-threshold-value=1 \
  --condition-filter='metric.type="serviceruntime.googleapis.com/api/request_count" resource.type="api" metric.label.response_code_class="5xx"' \
  --project=my-project

# 4. Uptime Check erstellen
gcloud monitoring uptime create api-gateway-health \
  --resource-type=uptime-url \
  --host=my-gateway-xyz.uc.gateway.dev \
  --path=/health \
  --project=my-project

# 5. Logs analysieren
gcloud logging read "resource.type=api" \
  --project=my-project \
  --limit=100 \
  --format=json | jq '[.[] | {status: .httpRequest.status, latency: .httpRequest.latency}] | group_by(.status) | map({status: .[0].status, count: length})'
```

**Grafana Cloud Integration:**
```yaml
# Prometheus-kompatible Metriken via Cloud Monitoring API
# Grafana Data Source konfigurieren:
# Type: Google Cloud Monitoring
# Project: my-project
# Service: API Gateway

# PromQL-ähnliche Queries:
fetch api
| metric 'serviceruntime.googleapis.com/api/request_count'
| group_by 1m, [value_request_count_mean: mean(value.request_count)]
| every 1m
```

**Hinweis:** GCP API Gateway bietet out-of-the-box Observability ohne zusätzliche Konfiguration. Für erweiterte Features:
1. **Cloud Logging** für strukturierte Logs und Log-Analyse
2. **Cloud Monitoring** für Metriken und Alerting
3. **Cloud Trace** für Distributed Tracing
4. **BigQuery** für Long-term Log Storage und Analytics
5. **Grafana Cloud** für Dashboards und Visualisierung

### AWS API Gateway

AWS API Gateway bietet native Integration mit CloudWatch Logs, CloudWatch Metrics und X-Ray Tracing für vollständige Observability.

**CloudWatch Logs (Access & Execution Logs):**
- Access Logs: HTTP Request/Response Details (JSON Format)
- Execution Logs: API Gateway Workflow Details (Debug-Level)
- Log Format: JSON mit `$context` Variablen
- Mechanismus: Stage-Level `accessLogSettings` + `methodSettings`
- CloudWatch Log Groups: Automatisch erstellt oder manuell definiert

**CloudWatch Metrics:**
- Count: Anzahl API-Requests
- 4XXError: Client Errors (400-499)
- 5XXError: Server Errors (500-599)
- Latency: End-to-End Response Time
- IntegrationLatency: Backend Response Time (ohne API Gateway Overhead)
- CacheHitCount / CacheMissCount: API Caching Metriken

**X-Ray Tracing:**
- Distributed Tracing für gesamten Request-Flow
- Integration mit Lambda, DynamoDB, SNS, SQS
- Trace-ID propagiert via `X-Amzn-Trace-Id` Header
- Service Map für Visualisierung der Microservices-Architektur

**Access Logs Konfiguration:**
```bash
# 1. CloudWatch Log Group erstellen
aws logs create-log-group \
  --log-group-name /aws/apigateway/my-api

# 2. Log Group ARN abrufen
LOG_GROUP_ARN=$(aws logs describe-log-groups \
  --log-group-name-prefix /aws/apigateway/my-api \
  --query 'logGroups[0].arn' --output text)

# 3. Stage mit Access Logs konfigurieren
aws apigateway update-stage \
  --rest-api-id abc123xyz \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/accessLogSettings/destinationArn,value=$LOG_GROUP_ARN \
    op=replace,path=/accessLogSettings/format,value='$context.requestId $context.status $context.latency'
```

**JSON Log Format (empfohlen):**
```bash
# Vollständiges JSON Format mit allen Context-Variablen
LOG_FORMAT='{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","path":"$context.path","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength","latency":"$context.responseLatency","integrationLatency":"$context.integrationLatency","userAgent":"$context.identity.userAgent","errorMessage":"$context.error.message"}'

aws apigateway update-stage \
  --rest-api-id abc123xyz \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/accessLogSettings/format,value="$LOG_FORMAT"
```

**Execution Logs aktivieren (Debug):**
```bash
# Execution Logs für detailliertes Debugging
aws apigateway update-stage \
  --rest-api-id abc123xyz \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/*/*/logging/loglevel,value=INFO \
    op=replace,path=/*/*/logging/dataTrace,value=true
```

**X-Ray Tracing aktivieren:**
```bash
# X-Ray Tracing für Distributed Tracing
aws apigateway update-stage \
  --rest-api-id abc123xyz \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/tracingEnabled,value=true
```

**Logs abfragen mit AWS CLI:**
```bash
# Access Logs anzeigen
aws logs tail /aws/apigateway/my-api --follow

# Filter: Nur Fehler (4xx/5xx)
aws logs filter-log-events \
  --log-group-name /aws/apigateway/my-api \
  --filter-pattern '{ $.status >= 400 }' \
  --start-time $(date -u -d '1 hour ago' +%s)000

# Filter: Latency > 1 Sekunde
aws logs filter-log-events \
  --log-group-name /aws/apigateway/my-api \
  --filter-pattern '{ $.latency > 1000 }' \
  --start-time $(date -u -d '1 hour ago' +%s)000

# JSON Parsing mit jq
aws logs filter-log-events \
  --log-group-name /aws/apigateway/my-api \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --output json | jq '.events[] | fromjson | {status, latency, path}'
```

**CloudWatch Metrics abfragen:**
```bash
# Request Count (letzte Stunde)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=MyAPI \
  --start-time $(date -u -d '1 hour ago' --iso-8601) \
  --end-time $(date -u --iso-8601) \
  --period 300 \
  --statistics Sum

# Error Rate (4xx + 5xx)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 4XXError \
  --dimensions Name=ApiName,Value=MyAPI \
  --start-time $(date -u -d '1 hour ago' --iso-8601) \
  --end-time $(date -u --iso-8601) \
  --period 300 \
  --statistics Sum

# Latency (Average, P95, P99)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Latency \
  --dimensions Name=ApiName,Value=MyAPI \
  --start-time $(date -u -d '1 hour ago' --iso-8601) \
  --end-time $(date -u --iso-8601) \
  --period 300 \
  --statistics Average,Maximum \
  --extended-statistics p95,p99
```

**X-Ray Traces analysieren:**
```bash
# Traces abrufen
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s)

# Trace Details
aws xray batch-get-traces \
  --trace-ids <trace-id-1> <trace-id-2>
```

**CloudWatch Insights Queries:**
```bash
# CloudWatch Logs Insights Query
aws logs start-query \
  --log-group-name /aws/apigateway/my-api \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, requestId, status, latency
| filter status >= 500
| sort latency desc
| limit 20'

# Query-Ergebnisse abrufen
aws logs get-query-results --query-id <query-id>
```

**CloudWatch Dashboard erstellen:**
```bash
# Dashboard JSON Definition
cat > dashboard.json <<EOF
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApiGateway", "Count", {"stat": "Sum", "label": "Total Requests"}],
          [".", "4XXError", {"stat": "Sum", "label": "Client Errors"}],
          [".", "5XXError", {"stat": "Sum", "label": "Server Errors"}]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "API Gateway Requests"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ApiGateway", "Latency", {"stat": "Average", "label": "Avg Latency"}],
          ["...", {"stat": "p99", "label": "P99 Latency"}]
        ],
        "period": 300,
        "region": "us-east-1",
        "title": "API Gateway Latency"
      }
    }
  ]
}
EOF

# Dashboard erstellen
aws cloudwatch put-dashboard \
  --dashboard-name MyAPI-Dashboard \
  --dashboard-body file://dashboard.json
```

**CloudWatch Alarms:**
```bash
# Alarm bei hoher Error Rate
aws cloudwatch put-metric-alarm \
  --alarm-name "API-High-Error-Rate" \
  --alarm-description "Alert when error rate > 5%" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ApiName,Value=MyAPI \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts

# Alarm bei hoher Latency
aws cloudwatch put-metric-alarm \
  --alarm-name "API-High-Latency" \
  --alarm-description "Alert when P99 latency > 1s" \
  --metric-name Latency \
  --namespace AWS/ApiGateway \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ApiName,Value=MyAPI \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts
```

**Testing:**
```bash
# API Request mit X-Ray Trace-ID
curl -H "X-Amzn-Trace-Id: Root=1-67a12345-12345678901234567890abcd" \
  https://abc123.execute-api.us-east-1.amazonaws.com/prod/api/users

# Logs in Echtzeit verfolgen
aws logs tail /aws/apigateway/my-api --follow --format short

# Metriken live abfragen (alle 30 Sekunden)
watch -n 30 'aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=MyAPI \
  --start-time $(date -u -d "5 minutes ago" --iso-8601) \
  --end-time $(date -u --iso-8601) \
  --period 300 \
  --statistics Sum'
```

**AWS API Gateway-spezifische Features:**
- ✅ CloudWatch Access Logs (JSON Format mit $context Variables)
- ✅ CloudWatch Execution Logs (Debug-Level API Gateway Workflow)
- ✅ CloudWatch Metrics (Count, 4XXError, 5XXError, Latency, IntegrationLatency)
- ✅ X-Ray Distributed Tracing
- ✅ CloudWatch Insights für Log-Analyse
- ✅ CloudWatch Dashboards und Alarms
- ✅ Stage-Level Logging-Konfiguration
- ✅ Method-Level Logging Override

**Limitierungen:**
- ⚠️ Access Logs müssen manuell konfiguriert werden (nicht automatisch)
- ⚠️ CloudWatch Log Groups müssen vorab erstellt werden
- ⚠️ Log Format ist statisch (keine dynamischen Felder wie bei Lambda)
- ⚠️ X-Ray Sampling Rate nicht konfigurierbar (1 Request/Second + 5%)
- ❌ Keine native Log Sampling (alle Requests werden geloggt)

**Complete Observability Setup:**
```bash
#!/bin/bash
# Complete AWS API Gateway Observability Setup

API_ID="abc123xyz"
STAGE_NAME="prod"
REGION="us-east-1"

# 1. CloudWatch Log Group erstellen
aws logs create-log-group \
  --log-group-name "/aws/apigateway/$API_ID-$STAGE_NAME"

# 2. Log Retention setzen (7 Tage)
aws logs put-retention-policy \
  --log-group-name "/aws/apigateway/$API_ID-$STAGE_NAME" \
  --retention-in-days 7

# 3. Stage mit Access Logs + Execution Logs + X-Ray konfigurieren
LOG_GROUP_ARN="arn:aws:logs:$REGION:$(aws sts get-caller-identity --query Account --output text):log-group:/aws/apigateway/$API_ID-$STAGE_NAME"

LOG_FORMAT='{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","path":"$context.path","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength","latency":"$context.responseLatency","integrationLatency":"$context.integrationLatency"}'

aws apigateway update-stage \
  --rest-api-id $API_ID \
  --stage-name $STAGE_NAME \
  --patch-operations \
    op=replace,path=/accessLogSettings/destinationArn,value=$LOG_GROUP_ARN \
    op=replace,path=/accessLogSettings/format,value="$LOG_FORMAT" \
    op=replace,path=/tracingEnabled,value=true \
    op=replace,path=/*/*/logging/loglevel,value=INFO

# 4. CloudWatch Alarms erstellen
aws cloudwatch put-metric-alarm \
  --alarm-name "$API_ID-High-Error-Rate" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ApiName,Value=$API_ID

echo "Observability setup complete!"
echo "Access Logs: /aws/apigateway/$API_ID-$STAGE_NAME"
echo "X-Ray Tracing: Enabled"
echo "CloudWatch Alarms: Created"
```

**Hinweis:** AWS API Gateway bietet vollständige Observability mit CloudWatch (Logs + Metrics) und X-Ray (Distributed Tracing). Für Production-Deployments:
1. **CloudWatch Logs** für Access/Execution Logs
2. **CloudWatch Metrics** für Monitoring und Alerting
3. **X-Ray Tracing** für Distributed Tracing
4. **CloudWatch Insights** für Log-Analyse
5. **CloudWatch Dashboards** für Visualisierung

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
✅ **Provider-agnostisch**: Einheitliche Config für alle 7 Provider
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
