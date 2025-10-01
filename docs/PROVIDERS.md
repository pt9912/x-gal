# Provider Documentation

## Envoy Proxy

**Generated Format:** YAML

**Features:**
- ✅ gRPC and HTTP support
- ✅ Lua filters for transformations
- ✅ Advanced routing
- ✅ Load balancing
- ✅ Admin interface

**Example:**
```bash
python gal-cli.py generate --config examples/gateway-config.yaml --provider envoy -o envoy.yaml
```

**Use Case:** Complex service mesh, high-performance proxying

## Kong API Gateway

**Generated Format:** Declarative YAML

**Features:**
- ✅ Plugin ecosystem
- ✅ Request/Response transformation
- ✅ Authentication plugins
- ✅ Rate limiting
- ✅ Admin API

**Example:**
```bash
python gal-cli.py generate --config examples/gateway-config.yaml --provider kong -o kong.yaml
```

**Use Case:** API management, plugin-based features

## Apache APISIX

**Generated Format:** JSON

**Features:**
- ✅ Lua scripting
- ✅ Dynamic routing
- ✅ Serverless functions
- ✅ High performance
- ✅ Low latency

**Example:**
```bash
python gal-cli.py generate --config examples/gateway-config.yaml --provider apisix -o apisix.json
```

**Use Case:** Cloud-native, microservices

## Traefik

**Generated Format:** YAML

**Features:**
- ✅ Automatic service discovery
- ✅ Kubernetes integration
- ✅ Let's Encrypt support
- ✅ Middleware system
- ✅ Dynamic configuration

**Example:**
```bash
python gal-cli.py generate --config examples/gateway-config.yaml --provider traefik -o traefik.yaml
```

**Use Case:** Container orchestration, Kubernetes

## Comparison

| Feature | Envoy | Kong | APISIX | Traefik |
|---------|-------|------|--------|---------|
| gRPC Support | ✅ | ✅ | ✅ | ✅ |
| Performance | Excellent | Good | Excellent | Good |
| Configuration | Complex | Moderate | Moderate | Simple |
| Plugins | Limited | Extensive | Growing | Middleware |
| Learning Curve | Steep | Moderate | Moderate | Easy |
| Best For | Service Mesh | API Mgmt | Cloud Native | Containers |

## Choosing a Provider

**Choose Envoy if:**
- You need maximum performance
- Building a service mesh
- Complex routing requirements
- Willing to invest in learning

**Choose Kong if:**
- You need extensive plugins
- API management features
- Established ecosystem
- Enterprise support

**Choose APISIX if:**
- Cloud-native architecture
- Need customization via Lua
- High performance requirements
- Apache ecosystem

**Choose Traefik if:**
- Using Kubernetes/Docker
- Need automatic discovery
- Want simple configuration
- Quick setup
