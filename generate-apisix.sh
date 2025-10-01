#!/bin/bash
# Generate APISIX configuration
python3 gal-cli.py generate --config examples/gateway-config.yaml --provider apisix --output generated/apisix.json
echo "✓ APISIX configuration generated: generated/apisix.json"
