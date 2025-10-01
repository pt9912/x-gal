#!/bin/bash
# Generate Envoy configuration
python3 gal-cli.py generate --config examples/gateway-config.yaml --provider envoy --output generated/envoy.yaml
echo "✓ Envoy configuration generated: generated/envoy.yaml"
