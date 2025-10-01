#!/bin/bash
# Generate Kong configuration
python3 gal-cli.py generate --config examples/gateway-config.yaml --provider kong --output generated/kong.yaml
echo "✓ Kong configuration generated: generated/kong.yaml"
