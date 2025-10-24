#!/bin/bash
# Generate RSA keys, JWKS, and JWT tokens for Envoy testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/keys"

echo "================================="
echo "JWT Key & Token Generator"
echo "================================="
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build Docker image
echo "📦 Building keygen Docker image..."
docker build -t jwt-keygen "$SCRIPT_DIR" 2>&1 | grep -E "(Step|Successfully)" || true
echo "✅ Image built"
echo ""

# Generate RSA keys and JWKS
echo "🔑 Generating RSA key pair and JWKS..."
docker run --rm -v "$OUTPUT_DIR:/output" -v "$SCRIPT_DIR/generate_jwks.py:/app/generate_jwks.py:ro" jwt-keygen python3 generate_jwks.py
echo "✅ Keys generated:"
echo "   - ${OUTPUT_DIR}/private_key.pem"
echo "   - ${OUTPUT_DIR}/jwks.json"
echo ""

# Generate JWT tokens
echo "🎫 Generating JWT tokens..."
docker run --rm -v "$OUTPUT_DIR:/app" jwt-keygen python3 generate_jwt.py
echo "✅ Tokens generated:"
echo "   - ${OUTPUT_DIR}/admin_token.jwt"
echo "   - ${OUTPUT_DIR}/user_token.jwt"
echo "   - ${OUTPUT_DIR}/beta_token.jwt"
echo "   - ${OUTPUT_DIR}/tokens_summary.json"
echo ""

# Display JWKS
echo "📋 JWKS Content:"
cat "$OUTPUT_DIR/jwks.json" | jq '.' 2>/dev/null || cat "$OUTPUT_DIR/jwks.json"
echo ""

# Display tokens
echo "================================="
echo "Generated Tokens"
echo "================================="
echo ""

if [ -f "$OUTPUT_DIR/admin_token.jwt" ]; then
    ADMIN_TOKEN=$(cat "$OUTPUT_DIR/admin_token.jwt")
    echo "1. ADMIN TOKEN (role=admin):"
    echo "   File: ${OUTPUT_DIR}/admin_token.jwt"
    echo "   Token: ${ADMIN_TOKEN:0:60}...${ADMIN_TOKEN: -30}"
    echo ""
    echo "   Test command:"
    echo "   curl -H 'Authorization: Bearer $ADMIN_TOKEN' http://localhost:8080/api/admin/test"
    echo ""
fi

if [ -f "$OUTPUT_DIR/user_token.jwt" ]; then
    USER_TOKEN=$(cat "$OUTPUT_DIR/user_token.jwt")
    echo "2. USER TOKEN (role=user):"
    echo "   File: ${OUTPUT_DIR}/user_token.jwt"
    echo "   Token: ${USER_TOKEN:0:60}...${USER_TOKEN: -30}"
    echo ""
fi

if [ -f "$OUTPUT_DIR/beta_token.jwt" ]; then
    BETA_TOKEN=$(cat "$OUTPUT_DIR/beta_token.jwt")
    echo "3. BETA TOKEN (role=beta):"
    echo "   File: ${OUTPUT_DIR}/beta_token.jwt"
    echo "   Token: ${BETA_TOKEN:0:60}...${BETA_TOKEN: -30}"
    echo ""
fi

echo "================================="
echo "✅ All done!"
echo "================================="
echo ""
echo "Next steps:"
echo "  1. Update JWKS service with the generated jwks.json"
echo "  2. Use the tokens to test JWT authentication"
echo "  3. Verify tokens at https://jwt.io"
echo ""
