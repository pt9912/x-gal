# WebSocket Support - GAL Gateway

**Version:** 1.2.0
**Status:** Produktionsbereit
**Provider Support:** Envoy, Kong, APISIX, Traefik, Nginx, HAProxy

---

## Übersicht

WebSocket ermöglicht bidirektionale, Echtzeit-Kommunikation zwischen Client und Server über eine persistente TCP-Verbindung. Im Gegensatz zu klassischem HTTP Request/Response erlaubt WebSocket Push-Nachrichten vom Server zum Client.

### Warum WebSocket?

- **Real-time Updates:** Live-Dashboards, Aktienkurse, Sportergebnisse
- **Chat-Anwendungen:** Instant Messaging, Collaboration Tools
- **Gaming:** Multiplayer-Spiele mit niedrigen Latenzen
- **IoT:** Sensor-Daten, Live-Monitoring
- **Streaming:** Audio/Video-Streaming, Live-Events

### WebSocket vs HTTP

| Feature | HTTP | WebSocket |
|---------|------|-----------|
| **Kommunikation** | Request/Response | Bidirektional |
| **Verbindung** | Stateless, kurzlebig | Stateful, persistent |
| **Overhead** | Header bei jedem Request | Einmaliger Handshake |
| **Latenz** | Höher (Polling) | Niedrig (Push) |
| **Server Push** | ❌ (Server Sent Events) | ✅ Native |

---

## Schnellstart

### Basis-Konfiguration

```yaml
version: "1.0"
provider: envoy

services:
  - name: chat_service
    type: rest
    protocol: http
    upstream:
      host: chat-backend
      port: 8080

    routes:
      - path_prefix: /ws/chat
        websocket:
          enabled: true
          idle_timeout: 300s
          ping_interval: 30s
```

### Mit erweiterten Optionen

```yaml
routes:
  - path_prefix: /ws/realtime
    websocket:
      enabled: true
      idle_timeout: 600s        # 10 Minuten Idle Timeout
      ping_interval: 60s        # Ping alle 60 Sekunden
      max_message_size: 2097152 # 2MB maximale Message-Größe
      compression: true         # Per-Message Compression aktivieren
```

### WebSocket + Authentication

```yaml
routes:
  - path_prefix: /ws/secure
    authentication:
      enabled: true
      type: jwt
      jwt:
        issuer: https://auth.example.com
        audience: wss://api.example.com
        jwks_uri: https://auth.example.com/.well-known/jwks.json

    websocket:
      enabled: true
      idle_timeout: 300s
      ping_interval: 30s
```

---

## Konfigurationsoptionen

### WebSocketConfig Felder

```yaml
websocket:
  enabled: true                # WebSocket aktivieren
  idle_timeout: "300s"         # Maximale Idle-Zeit (5 Minuten default)
  ping_interval: "30s"         # Ping-Interval für Keep-Alive
  max_message_size: 1048576    # Max Message Size in Bytes (1MB default)
  compression: false           # Per-Message Compression (false default)
```

#### `enabled`
- **Typ:** Boolean
- **Default:** `true`
- **Beschreibung:** Aktiviert WebSocket Support für diese Route

#### `idle_timeout`
- **Typ:** String (Duration)
- **Default:** `"300s"` (5 Minuten)
- **Beschreibung:** Maximale Zeit ohne Aktivität, bevor die Verbindung geschlossen wird
- **Beispiele:** `"60s"`, `"10m"`, `"1h"`

#### `ping_interval`
- **Typ:** String (Duration)
- **Default:** `"30s"`
- **Beschreibung:** Interval für Ping-Frames (Keep-Alive)
- **Hinweis:** Sollte kleiner als `idle_timeout` sein

#### `max_message_size`
- **Typ:** Integer
- **Default:** `1048576` (1MB)
- **Beschreibung:** Maximale Größe einer WebSocket-Message in Bytes
- **Empfehlung:**
  - Chat: 64KB - 256KB
  - Datei-Upload: 10MB+
  - JSON APIs: 1MB - 5MB

#### `compression`
- **Typ:** Boolean
- **Default:** `false`
- **Beschreibung:** Aktiviert Per-Message Deflate Compression (RFC 7692)
- **Trade-off:** Reduziert Bandbreite, erhöht CPU-Last

---

## Provider-Implementierung

### Envoy

**Support:** ✅ Native WebSocket via HTTP/1.1 Upgrade

**Generierte Konfiguration:**

```yaml
# Envoy unterstützt WebSocket automatisch via HTTP/1.1 Upgrade
route_config:
  virtual_hosts:
    - name: chat_service
      routes:
        - match:
            prefix: /ws/chat
          route:
            cluster: chat_backend
            timeout: 300s  # idle_timeout
            upgrade_configs:
              - upgrade_type: websocket
```

**Features:**
- ✅ Automatische Upgrade-Header-Verarbeitung
- ✅ Idle Timeout via `timeout`
- ✅ Ping/Pong automatisch
- ⚠️ `max_message_size` nicht direkt konfigurierbar (via Buffer Limits)

### Kong

**Support:** ✅ Native WebSocket Support

**Generierte Konfiguration:**

```yaml
# Kong unterstützt WebSocket out-of-the-box
routes:
  - name: chat_route
    paths:
      - /ws/chat
    protocols:
      - http
      - https
    service: chat_service

services:
  - name: chat_service
    url: http://chat-backend:8080
    read_timeout: 300000  # idle_timeout in ms
    write_timeout: 300000
```

**Features:**
- ✅ Automatische WebSocket-Erkennung
- ✅ Timeouts via `read_timeout`/`write_timeout`
- ✅ Funktioniert mit allen Kong-Plugins (Auth, Rate Limiting)
- ⚠️ `ping_interval` nicht konfigurierbar

### APISIX

**Support:** ✅ Native WebSocket Support

**Generierte Konfiguration:**

```yaml
# APISIX unterstützt WebSocket nativ
routes:
  - uri: /ws/chat
    service_id: chat_service
    enable_websocket: true
    timeout:
      connect: 5
      send: 300
      read: 300

services:
  - id: chat_service
    upstream_id: chat_upstream
```

**Features:**
- ✅ `enable_websocket: true` Flag
- ✅ Timeout-Konfiguration
- ✅ Kompatibel mit APISIX-Plugins
- ✅ WebSocket-spezifische Metrics

### Traefik

**Support:** ✅ Native WebSocket Support

**Generierte Konfiguration:**

```yaml
# Traefik unterstützt WebSocket automatisch
http:
  routers:
    chat-router:
      rule: PathPrefix(`/ws/chat`)
      service: chat-service

  services:
    chat-service:
      loadBalancer:
        servers:
          - url: http://chat-backend:8080
        responseForwarding:
          flushInterval: 100ms  # Für WebSocket wichtig
```

**Features:**
- ✅ Automatische WebSocket-Erkennung
- ✅ `flushInterval` für niedrige Latenz
- ✅ Sticky Sessions für WebSocket
- ⚠️ Timeout über `serversTransport` konfigurierbar

### Nginx

**Support:** ✅ WebSocket via proxy_http_version 1.1

**Generierte Konfiguration:**

```nginx
# Nginx WebSocket Konfiguration
upstream chat_backend {
    server chat-backend:8080;
    keepalive 32;
}

server {
    listen 80;

    location /ws/chat {
        # WebSocket-spezifische Headers
        proxy_pass http://chat_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_read_timeout 300s;      # idle_timeout
        proxy_send_timeout 300s;
        proxy_connect_timeout 5s;

        # Keep-Alive
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Features:**
- ✅ `Upgrade` und `Connection` Header
- ✅ `proxy_http_version 1.1` erforderlich
- ✅ Timeouts via `proxy_read_timeout`
- ✅ Keepalive Connections
- ⚠️ `ping_interval` nicht direkt konfigurierbar

### HAProxy

**Support:** ✅ Native WebSocket Support

**Generierte Konfiguration:**

```haproxy
# HAProxy WebSocket Konfiguration
frontend http_frontend
    bind *:80

    # WebSocket ACL
    acl is_websocket path_beg /ws/chat
    acl is_websocket_upgrade hdr(Upgrade) -i websocket

    use_backend chat_backend if is_websocket is_websocket_upgrade

backend chat_backend
    # WebSocket Timeout
    timeout tunnel 300s  # idle_timeout
    timeout client 300s
    timeout server 300s

    server chat1 chat-backend:8080 check
```

**Features:**
- ✅ `timeout tunnel` für WebSocket-Verbindungen
- ✅ ACL für WebSocket-Erkennung
- ✅ Health Checks für WebSocket-Backends
- ✅ Load Balancing über WebSocket-Verbindungen

---

## Provider-Vergleich

| Feature | Envoy | Kong | APISIX | Traefik | Nginx | HAProxy |
|---------|-------|------|--------|---------|-------|---------|
| **Native Support** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Idle Timeout** | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| **Ping Interval** | ✅ Auto | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| **Max Message Size** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| **Compression** | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| **Load Balancing** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Health Checks** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Authentication** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Rate Limiting** | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |

**Legende:**
- ✅ Full Support
- ⚠️ Limited / Manual Configuration
- ❌ Not Supported

---

## Häufige Anwendungsfälle

### Use Case 1: Chat-Anwendung

```yaml
services:
  - name: chat_service
    upstream:
      targets:
        - host: chat-backend-1
          port: 8080
        - host: chat-backend-2
          port: 8080
      load_balancer:
        algorithm: ip_hash  # Sticky Sessions für WebSocket
        sticky_sessions: true

    routes:
      - path_prefix: /ws/chat
        authentication:
          enabled: true
          type: jwt
          jwt:
            issuer: https://auth.example.com
            audience: wss://chat.example.com
            jwks_uri: https://auth.example.com/.well-known/jwks.json

        websocket:
          enabled: true
          idle_timeout: 600s  # 10 Minuten für aktive Chats
          ping_interval: 30s
          max_message_size: 262144  # 256KB für Text-Nachrichten
```

**Erklärung:**
- `ip_hash` Load Balancing für Sticky Sessions (wichtig für WebSocket)
- JWT Authentication für Zugriffskontrolle
- 10 Minuten Idle Timeout (Nutzer schreibt, liest)
- 30s Ping Interval für Keep-Alive
- 256KB Message Size für Chat-Nachrichten

### Use Case 2: Live-Dashboard (Metrics)

```yaml
services:
  - name: metrics_service
    upstream:
      host: metrics-backend
      port: 9090

    routes:
      - path_prefix: /ws/metrics
        rate_limit:
          enabled: true
          requests_per_second: 10
          key_type: ip_address

        websocket:
          enabled: true
          idle_timeout: 300s
          ping_interval: 60s
          compression: true  # JSON-Daten komprimieren
```

**Erklärung:**
- Rate Limiting: 10 Verbindungen pro Sekunde pro IP
- Compression aktiviert für JSON-Metrics-Daten
- 5 Minuten Timeout (Dashboard lädt neue Daten)

### Use Case 3: IoT Sensor-Daten

```yaml
services:
  - name: iot_service
    upstream:
      targets:
        - host: iot-processor-1
          port: 8080
        - host: iot-processor-2
          port: 8080
      load_balancer:
        algorithm: least_conn

    routes:
      - path_prefix: /ws/sensors
        authentication:
          enabled: true
          type: api_key
          api_key:
            keys:
              - device_key_123
              - device_key_456
            key_name: X-Device-Key

        websocket:
          enabled: true
          idle_timeout: 3600s  # 1 Stunde
          ping_interval: 120s  # 2 Minuten (Batterie schonen)
          max_message_size: 10240  # 10KB für Sensor-Daten
```

**Erklärung:**
- API Key Auth für Geräte-Authentifizierung
- 1 Stunde Timeout für selten sendende Sensoren
- 2 Minuten Ping Interval (Batterie sparen)
- Kleine Message Size für Sensor-Daten

### Use Case 4: Multiplayer-Gaming

```yaml
services:
  - name: game_service
    upstream:
      targets:
        - host: game-server-1
          port: 8080
          weight: 2
        - host: game-server-2
          port: 8080
          weight: 1
      load_balancer:
        algorithm: weighted
        sticky_sessions: true
        cookie_name: GAME_SESSION

    routes:
      - path_prefix: /ws/game
        websocket:
          enabled: true
          idle_timeout: 7200s  # 2 Stunden (lange Gaming-Sessions)
          ping_interval: 10s   # Schnelle Keep-Alive für Latenz
          max_message_size: 524288  # 512KB für Game State
```

**Erklärung:**
- Weighted Load Balancing (unterschiedliche Server-Kapazitäten)
- Sticky Sessions via Cookie (Session-Persistenz)
- 2 Stunden Timeout (lange Gaming-Sessions)
- 10s Ping Interval für niedrige Latenz

### Use Case 5: File Upload/Download Streaming

```yaml
services:
  - name: upload_service
    upstream:
      host: upload-backend
      port: 8080

    routes:
      - path_prefix: /ws/upload
        authentication:
          enabled: true
          type: jwt

        rate_limit:
          enabled: true
          requests_per_second: 5
          key_type: jwt_claim
          key_claim: sub  # User ID

        websocket:
          enabled: true
          idle_timeout: 1800s  # 30 Minuten
          ping_interval: 60s
          max_message_size: 10485760  # 10MB für Chunks
          compression: false  # Keine Compression bei Binärdaten
```

**Erklärung:**
- JWT Authentication für User-Zugriff
- Rate Limiting pro User (5 Uploads/s)
- 30 Minuten Timeout für große Dateien
- 10MB Message Size für Upload-Chunks
- Compression deaktiviert (Binärdaten)

---

## Best Practices

### 1. Idle Timeout richtig wählen

```yaml
# ❌ Zu kurz
websocket:
  idle_timeout: 30s  # Verbindung bricht zu schnell ab

# ✅ Angemessen
websocket:
  idle_timeout: 300s  # 5 Minuten für Chat
  idle_timeout: 3600s  # 1 Stunde für IoT
```

**Faustregeln:**
- **Chat/Messaging:** 5-10 Minuten
- **Live-Dashboards:** 5-15 Minuten
- **IoT/Sensoren:** 30-60 Minuten
- **Gaming:** 1-2 Stunden

### 2. Ping Interval < Idle Timeout

```yaml
# ❌ Ping Interval größer als Idle Timeout
websocket:
  idle_timeout: 60s
  ping_interval: 90s  # Verbindung wird vorher geschlossen!

# ✅ Ping Interval deutlich kleiner
websocket:
  idle_timeout: 300s
  ping_interval: 30s  # 10x Pings vor Timeout
```

**Empfehlung:** `ping_interval` sollte mindestens 5-10x kleiner als `idle_timeout` sein.

### 3. Load Balancing für WebSocket

```yaml
# ✅ IP Hash oder Sticky Sessions verwenden
upstream:
  load_balancer:
    algorithm: ip_hash  # Session-Persistenz
    sticky_sessions: true
    cookie_name: WS_SESSION
```

**Warum?** WebSocket-Verbindungen sind stateful. Ohne Sticky Sessions verlieren Clients die Verbindung bei Load Balancer-Umschaltung.

### 4. Authentication kombinieren

```yaml
# ✅ JWT für WebSocket-Verbindungen
routes:
  - path_prefix: /ws/secure
    authentication:
      enabled: true
      type: jwt
      jwt:
        issuer: https://auth.example.com
        jwks_uri: https://auth.example.com/.well-known/jwks.json

    websocket:
      enabled: true
```

**Vorteil:** JWT im Upgrade-Request validiert, dann persistente Verbindung.

### 5. Rate Limiting anwenden

```yaml
# ✅ Rate Limiting für WebSocket-Verbindungen
rate_limit:
  enabled: true
  requests_per_second: 10  # Max 10 neue Verbindungen/s
  key_type: ip_address
```

**Zweck:** Schutz vor Connection-Flooding-Attacken.

### 6. Compression gezielt einsetzen

```yaml
# ✅ Compression für JSON-APIs
websocket:
  compression: true  # JSON, XML, Text

# ❌ Keine Compression für Binärdaten
websocket:
  compression: false  # Bilder, Videos, verschlüsselte Daten
```

**Trade-off:** Bandbreite vs. CPU-Last.

### 7. Message Size Limits setzen

```yaml
# ✅ Realistische Message Size Limits
websocket:
  max_message_size: 262144  # 256KB für Chat
  max_message_size: 10485760  # 10MB für File Upload
```

**Zweck:** Schutz vor Memory-Exhaustion-Attacken.

---

## Troubleshooting

### Problem 1: Verbindung schließt nach kurzer Zeit

**Symptom:** WebSocket-Verbindung wird nach 30-60 Sekunden geschlossen.

**Ursache:** Proxy- oder Gateway-Timeout zu kurz.

**Lösung:**
```yaml
websocket:
  idle_timeout: 600s  # Erhöhen
  ping_interval: 30s  # Keep-Alive aktivieren
```

### Problem 2: "Connection: Upgrade" funktioniert nicht

**Symptom:** HTTP 400/502 bei WebSocket-Verbindung.

**Ursache:** Proxy leitet Upgrade-Header nicht weiter.

**Lösung (Nginx):**
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

**Lösung (HAProxy):**
```haproxy
acl is_websocket_upgrade hdr(Upgrade) -i websocket
use_backend ws_backend if is_websocket_upgrade
```

### Problem 3: Load Balancing bricht Verbindung

**Symptom:** WebSocket-Verbindung funktioniert, bricht aber nach Load Balancer-Wechsel.

**Ursache:** Keine Session-Persistenz.

**Lösung:**
```yaml
upstream:
  load_balancer:
    algorithm: ip_hash  # Oder sticky_sessions
    sticky_sessions: true
```

### Problem 4: Hohe Latenz

**Symptom:** Nachrichten kommen mit Verzögerung an.

**Ursache:** Buffering im Proxy.

**Lösung (Nginx):**
```nginx
proxy_buffering off;
proxy_cache off;
```

**Lösung (Traefik):**
```yaml
responseForwarding:
  flushInterval: 100ms
```

### Problem 5: "Message too large"

**Symptom:** Große Nachrichten werden abgelehnt.

**Ursache:** `max_message_size` zu klein.

**Lösung:**
```yaml
websocket:
  max_message_size: 10485760  # 10MB
```

### Problem 6: Authentication schlägt fehl

**Symptom:** WebSocket-Verbindung wird mit 401 abgelehnt.

**Ursache:** JWT/Auth-Header nicht im Upgrade-Request.

**Lösung:**
```javascript
// Client-seitig: Token in Subprotocol oder Query übergeben
const ws = new WebSocket('wss://api.example.com/ws/chat', ['access_token', token]);

// Oder Query Parameter
const ws = new WebSocket('wss://api.example.com/ws/chat?token=' + token);
```

---

## Client-Beispiele

### JavaScript (Browser)

```javascript
// Basis WebSocket-Verbindung
const ws = new WebSocket('wss://api.example.com/ws/chat');

ws.onopen = () => {
    console.log('WebSocket verbunden');
    ws.send(JSON.stringify({ type: 'hello', user: 'Alice' }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Nachricht erhalten:', data);
};

ws.onerror = (error) => {
    console.error('WebSocket Fehler:', error);
};

ws.onclose = () => {
    console.log('WebSocket geschlossen');
};

// Mit Authentication (JWT in Subprotocol)
const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';
const ws = new WebSocket('wss://api.example.com/ws/secure', ['access_token', token]);
```

### Python

```python
import asyncio
import websockets

async def chat_client():
    uri = "wss://api.example.com/ws/chat"

    async with websockets.connect(uri) as websocket:
        # Nachricht senden
        await websocket.send('{"type": "hello", "user": "Alice"}')

        # Nachricht empfangen
        response = await websocket.recv()
        print(f"Antwort: {response}")

asyncio.run(chat_client())
```

### Go

```go
package main

import (
    "fmt"
    "github.com/gorilla/websocket"
)

func main() {
    url := "wss://api.example.com/ws/chat"

    conn, _, err := websocket.DefaultDialer.Dial(url, nil)
    if err != nil {
        panic(err)
    }
    defer conn.Close()

    // Nachricht senden
    err = conn.WriteMessage(websocket.TextMessage, []byte(`{"type":"hello","user":"Alice"}`))
    if err != nil {
        panic(err)
    }

    // Nachricht empfangen
    _, message, err := conn.ReadMessage()
    if err != nil {
        panic(err)
    }

    fmt.Printf("Antwort: %s\n", message)
}
```

---

## Sicherheit

### 1. Immer WSS (WebSocket Secure) verwenden

```yaml
# ❌ Unsicheres WebSocket
ws://api.example.com/ws/chat

# ✅ Sicheres WebSocket über TLS
wss://api.example.com/ws/chat
```

### 2. Authentication obligatorisch

```yaml
routes:
  - path_prefix: /ws/chat
    authentication:
      enabled: true
      type: jwt  # Oder api_key, basic
```

### 3. Rate Limiting gegen DoS

```yaml
rate_limit:
  enabled: true
  requests_per_second: 10
  key_type: ip_address
```

### 4. Message Size Limits

```yaml
websocket:
  max_message_size: 1048576  # 1MB - verhindert Memory-Exhaustion
```

### 5. CORS Policy

```yaml
cors:
  enabled: true
  allowed_origins:
    - https://app.example.com  # Nur vertrauenswürdige Origins
  allowed_methods:
    - GET
  allow_credentials: true
```

---

## Performance-Optimierung

### 1. Connection Pooling (Nginx)

```nginx
upstream ws_backend {
    server backend:8080;
    keepalive 100;  # Connection Pool
}
```

### 2. Kompression aktivieren

```yaml
websocket:
  compression: true  # Reduziert Bandbreite um 60-80% (JSON)
```

### 3. Ping Interval optimieren

```yaml
# Für niedrige Latenz
websocket:
  ping_interval: 10s  # Gaming

# Für Batterie-Schonung (Mobile/IoT)
websocket:
  ping_interval: 120s  # IoT-Sensoren
```

### 4. Load Balancing Algorithm

```yaml
# Für gleichmäßige Verteilung
upstream:
  load_balancer:
    algorithm: least_conn  # Verbindungen auf wenig ausgelastete Server

# Für Session-Persistenz
upstream:
  load_balancer:
    algorithm: ip_hash  # Gleicher Client → gleicher Server
```

---

## Weiterführende Ressourcen

- **RFC 6455:** WebSocket Protocol Specification
- **RFC 7692:** Compression Extensions for WebSocket
- **MDN WebSocket API:** https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- **Can I use WebSocket:** https://caniuse.com/websockets (Browser Support: 98%+)

---

## Zusammenfassung

WebSocket Support in GAL ermöglicht:
- ✅ **Echtzeitkommunikation** für moderne Anwendungen
- ✅ **Bidirektionale Push-Nachrichten** vom Server
- ✅ **Niedrige Latenz** durch persistente Verbindungen
- ✅ **Volle Provider-Unterstützung** (alle 6 Provider)
- ✅ **Authentication & Rate Limiting** für Sicherheit
- ✅ **Load Balancing** für Hochverfügbarkeit
- ✅ **Einfache Konfiguration** mit YAML

**Next Steps:**
1. Konfiguriere `websocket` in deinen Routes
2. Wähle passende Timeouts für deinen Use Case
3. Aktiviere Compression für JSON-Daten
4. Implementiere Client-seitigen Reconnect-Mechanismus
5. Teste mit Load (ab 1000+ gleichzeitige Verbindungen)

---

**Version:** 1.2.0
**Last Updated:** 2025-10-18
**Author:** GAL Development Team
