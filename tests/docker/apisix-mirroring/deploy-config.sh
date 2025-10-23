#!/bin/bash
#
# Deploy APISIX configuration via Admin API
#
# This script:
# 1. Generates APISIX config from GAL YAML
# 2. Deploys routes/services/upstreams to APISIX Admin API
# 3. Verifies deployment

set -e

ADMIN_URL="${ADMIN_URL:-http://localhost:9182}"
API_KEY="${API_KEY:-edd1c9f034335f136f87ad84b625c8f1}"
CONFIG_FILE="${CONFIG_FILE:-mirroring-config.yaml}"
OUTPUT_FILE="${OUTPUT_FILE:-/tmp/apisix-mirroring.json}"

echo "🔧 APISIX Configuration Deployment"
echo "=================================="
echo "Admin URL: $ADMIN_URL"
echo "Config: $CONFIG_FILE"
echo ""

# Generate APISIX config from GAL YAML
echo "📝 Generating APISIX configuration from GAL YAML..."
python3 -c "
from gal.config import Config
from gal.providers.apisix import APISIXProvider
import json

config = Config.from_yaml('$CONFIG_FILE')
provider = APISIXProvider()
output = provider.generate(config)

with open('$OUTPUT_FILE', 'w') as f:
    f.write(output)

print('✅ Config generated: $OUTPUT_FILE')
print(f'   Services: {len(config.services)}')

data = json.loads(output)
print(f'   Routes: {len(data.get(\"routes\", []))}')
print(f'   Upstreams: {len(data.get(\"upstreams\", []))}')
"

echo ""
echo "🚀 Deploying to APISIX Admin API..."

# Load generated config
CONFIG_JSON=$(cat "$OUTPUT_FILE")

# Deploy upstreams
echo "📦 Deploying upstreams..."
echo "$CONFIG_JSON" | jq -r '.upstreams[] | @json' | while read -r upstream; do
    UPSTREAM_ID=$(echo "$upstream" | jq -r '.id')
    echo "  → Upstream: $UPSTREAM_ID"

    curl -s -X PUT \
        -H "X-API-KEY: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$upstream" \
        "$ADMIN_URL/apisix/admin/upstreams/$UPSTREAM_ID" | jq -r '.action'
done

# Deploy services
echo ""
echo "🔧 Deploying services..."
echo "$CONFIG_JSON" | jq -r '.services[] | @json' | while read -r service; do
    SERVICE_ID=$(echo "$service" | jq -r '.id')
    echo "  → Service: $SERVICE_ID"

    curl -s -X PUT \
        -H "X-API-KEY: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$service" \
        "$ADMIN_URL/apisix/admin/services/$SERVICE_ID" | jq -r '.action'
done

# Deploy routes
echo ""
echo "🛣️  Deploying routes..."
ROUTE_ID=1
echo "$CONFIG_JSON" | jq -r '.routes[] | @json' | while read -r route; do
    ROUTE_NAME=$(echo "$route" | jq -r '.name')
    ROUTE_URI=$(echo "$route" | jq -r '.uri')
    HAS_MIRROR=$(echo "$route" | jq -r 'has("plugins") and (.plugins | has("proxy-mirror"))')

    echo "  → Route $ROUTE_ID: $ROUTE_URI"

    if [ "$HAS_MIRROR" = "true" ]; then
        SAMPLE_RATIO=$(echo "$route" | jq -r '.plugins."proxy-mirror".sample_ratio // 1.0')
        echo "     Mirror: enabled (sample_ratio=$SAMPLE_RATIO)"
    else
        echo "     Mirror: disabled"
    fi

    curl -s -X PUT \
        -H "X-API-KEY: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$route" \
        "$ADMIN_URL/apisix/admin/routes/$ROUTE_ID" | jq -r '.action'

    ROUTE_ID=$((ROUTE_ID + 1))
done

echo ""
echo "✅ Deployment completed!"
echo ""

# Verify deployment
echo "🔍 Verifying deployment..."
echo ""
echo "Routes:"
curl -s -H "X-API-KEY: $API_KEY" "$ADMIN_URL/apisix/admin/routes" | \
    jq -r '.list[] | "  \(.key | split("/")[-1]): \(.value.uri) - \(if .value.plugins."proxy-mirror" then "MIRRORING" else "no mirror" end)"'

echo ""
echo "Upstreams:"
curl -s -H "X-API-KEY: $API_KEY" "$ADMIN_URL/apisix/admin/upstreams" | \
    jq -r '.list[] | "  \(.key | split("/")[-1]): \(.value.nodes | keys | join(", "))"'

echo ""
echo "Services:"
curl -s -H "X-API-KEY: $API_KEY" "$ADMIN_URL/apisix/admin/services" | \
    jq -r '.list[] | "  \(.key | split("/")[-1]): upstream_id=\(.value.upstream_id)"'

echo ""
echo "✅ All done! APISIX is ready for testing."
echo ""
echo "Test with:"
echo "  curl http://localhost:10003/api/v1  # 100% mirroring"
echo "  curl http://localhost:10003/api/v2  # 50% mirroring"
echo "  curl http://localhost:10003/api/v3  # no mirroring"
