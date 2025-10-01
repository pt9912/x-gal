# Quick Start Guide

## Installation

1. **Create virtual environment:**
```bash
cd gateway-abstraction-layer-python
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Make CLI executable:**
```bash
chmod +x gal-cli.py
```

## Basic Usage

### Generate Configuration

```bash
# For Envoy
python gal-cli.py generate --config examples/gateway-config.yaml --provider envoy --output generated/envoy.yaml

# For Kong
python gal-cli.py generate --config examples/gateway-config.yaml --provider kong --output generated/kong.yaml

# For APISIX
python gal-cli.py generate --config examples/gateway-config.yaml --provider apisix --output generated/apisix.json

# For Traefik
python gal-cli.py generate --config examples/gateway-config.yaml --provider traefik --output generated/traefik.yaml
```

### Generate All at Once

```bash
python gal-cli.py generate-all --config examples/gateway-config.yaml --output-dir generated
```

### Validate Configuration

```bash
python gal-cli.py validate --config examples/gateway-config.yaml
```

### Show Configuration Info

```bash
python gal-cli.py info --config examples/gateway-config.yaml
```

### List Available Providers

```bash
python gal-cli.py list-providers
```

## Configuration File

The configuration file (`gateway-config.yaml`) defines:

- **Provider**: Which gateway to use (envoy, kong, apisix, traefik)
- **Global settings**: Host, port, timeout
- **Services**: Your backend services (gRPC and REST)
- **Transformations**: Default values and computed fields
- **Plugins**: Additional gateway features

## Example Services

The default configuration includes:
- 3 gRPC services (user, order, notification)
- 2 REST services (product, payment)

Each with automatic:
- Default value injection
- UUID generation
- Timestamp generation
- Field validation

## Next Steps

1. Customize `examples/gateway-config.yaml` with your services
2. Generate configurations for your provider
3. Deploy to your gateway
4. Test your API

## Tips

- Use `--help` on any command for more options
- The `info` command shows detailed configuration
- Generate all providers at once to compare
- Validation runs automatically before generation
