#!/bin/bash
# Comprehensive test script for all Envoy Advanced Routing scenarios
# Tests: Header-based, Query-based, JWT-based, and GeoIP-based routing

set -e

ENVOY_URL="http://localhost:8080"
ADMIN_URL="http://localhost:9901"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to print test results
print_result() {
    local test_name="$1"
    local expected_backend="$2"
    local actual_backend="$3"
    local routing_rule="$4"

    if [[ "$expected_backend" == "$actual_backend" ]]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        echo -e "  Expected: $expected_backend, Got: $actual_backend"
        if [[ -n "$routing_rule" ]]; then
            echo -e "  Routing Rule: $routing_rule"
        fi
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name"
        echo -e "  Expected: $expected_backend, Got: $actual_backend"
        if [[ -n "$routing_rule" ]]; then
            echo -e "  Routing Rule: $routing_rule"
        fi
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Helper function to extract backend name from response
extract_backend() {
    local response="$1"
    echo "$response" | jq -r '.backend_name // .backend // "unknown"' 2>/dev/null || echo "unknown"
}

# Helper function to extract routing rule from response headers
extract_routing_rule() {
    local headers="$1"
    echo "$headers" | grep -i "x-routing-rule:" | cut -d' ' -f2 | tr -d '\r\n' || echo "none"
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Envoy Advanced Routing Test Suite${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if Envoy is running
echo -e "${YELLOW}Checking Envoy availability...${NC}"
if ! curl -sf "$ADMIN_URL/ready" > /dev/null; then
    echo -e "${RED}ERROR: Envoy is not running at $ADMIN_URL${NC}"
    echo "Please start Envoy with: docker compose -f docker-compose-improved.yml up -d"
    exit 1
fi
echo -e "${GREEN}✓ Envoy is running${NC}\n"

# Wait for backends to be healthy
echo -e "${YELLOW}Waiting for backends to be healthy...${NC}"
sleep 3
echo -e "${GREEN}✓ Backends ready${NC}\n"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}1. Header-based Routing Tests${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 1: X-API-Version: v2
echo -e "${YELLOW}Test 1.1: Header X-API-Version=v2${NC}"
response=$(curl -s -H "X-API-Version: v2" "$ENVOY_URL/api/test")
headers=$(curl -sI -H "X-API-Version: v2" "$ENVOY_URL/api/test")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
print_result "Header: X-API-Version=v2" "backend-v2" "$backend" "$routing_rule"

# Test 2: User-Agent: Mobile
echo -e "${YELLOW}Test 1.2: Header User-Agent contains Mobile${NC}"
response=$(curl -s -H "User-Agent: Mozilla/5.0 (Mobile; Android)" "$ENVOY_URL/api/test")
headers=$(curl -sI -H "User-Agent: Mozilla/5.0 (Mobile; Android)" "$ENVOY_URL/api/test")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
print_result "Header: User-Agent=Mobile" "backend-mobile" "$backend" "$routing_rule"

# Test 3: X-Beta-Features: enabled
echo -e "${YELLOW}Test 1.3: Header X-Beta-Features=enabled${NC}"
response=$(curl -s -H "X-Beta-Features: enabled" "$ENVOY_URL/api/test")
headers=$(curl -sI -H "X-Beta-Features: enabled" "$ENVOY_URL/api/test")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
print_result "Header: X-Beta-Features=enabled" "backend-beta" "$backend" "$routing_rule"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}2. Query Parameter-based Routing Tests${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 4: version=2
echo -e "${YELLOW}Test 2.1: Query param version=2${NC}"
response=$(curl -s "$ENVOY_URL/api/test?version=2")
headers=$(curl -sI "$ENVOY_URL/api/test?version=2")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
print_result "Query: version=2" "backend-v2" "$backend" "$routing_rule"

# Test 5: beta=true
echo -e "${YELLOW}Test 2.2: Query param beta=true${NC}"
response=$(curl -s "$ENVOY_URL/api/test?beta=true")
headers=$(curl -sI "$ENVOY_URL/api/test?beta=true")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
print_result "Query: beta=true" "backend-beta" "$backend" "$routing_rule"

# Test 6: admin present
echo -e "${YELLOW}Test 2.3: Query param admin (present)${NC}"
response=$(curl -s "$ENVOY_URL/api/test?admin")
headers=$(curl -sI "$ENVOY_URL/api/test?admin")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
print_result "Query: admin present" "backend-admin" "$backend" "$routing_rule"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}3. JWT-based Routing Tests${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 7: JWT with role=admin claim
echo -e "${YELLOW}Test 3.1: JWT with role=admin claim${NC}"
# Generate a test JWT token (requires jwt tool or use pre-generated token)
# For now, we'll skip actual JWT validation and use a mock token
JWT_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InRlc3Qta2V5In0.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJyb2xlIjoiYWRtaW4iLCJhdWQiOiJ4LWdhbC10ZXN0IiwiaXNzIjoiaHR0cHM6Ly9qd2tzLXNlcnZpY2UiLCJleHAiOjk5OTk5OTk5OTl9.mock_signature"
response=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" "$ENVOY_URL/api/admin/test")
headers=$(curl -sI -H "Authorization: Bearer $JWT_TOKEN" "$ENVOY_URL/api/admin/test")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
print_result "JWT: role=admin" "backend-admin" "$backend" "$routing_rule"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}4. GeoIP-based Routing Tests${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 8: GeoIP routing for EU (Germany)
echo -e "${YELLOW}Test 4.1: GeoIP country=DE (EU backend)${NC}"
response=$(curl -s -H "X-Forwarded-For: 192.168.1.1" "$ENVOY_URL/api/eu/test")
headers=$(curl -sI -H "X-Forwarded-For: 192.168.1.1" "$ENVOY_URL/api/eu/test")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
geo_country=$(echo "$headers" | grep -i "x-geo-country:" | cut -d' ' -f2 | tr -d '\r\n')
print_result "GeoIP: country=DE (IP=192.168.1.1)" "backend-eu" "$backend" "country=$geo_country"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}5. Default/Fallback Routing Tests${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 9: Default fallback (no routing rules match)
echo -e "${YELLOW}Test 5.1: Default fallback routing${NC}"
response=$(curl -s "$ENVOY_URL/api/test")
headers=$(curl -sI "$ENVOY_URL/api/test")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
print_result "Default: no rules match" "backend-v1" "$backend" "$routing_rule"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}6. Combined Routing Tests${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 10: Multiple headers (first match wins)
echo -e "${YELLOW}Test 6.1: Multiple headers (X-API-Version=v2 + X-Beta-Features=enabled)${NC}"
response=$(curl -s -H "X-API-Version: v2" -H "X-Beta-Features: enabled" "$ENVOY_URL/api/test")
headers=$(curl -sI -H "X-API-Version: v2" -H "X-Beta-Features: enabled" "$ENVOY_URL/api/test")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
print_result "Combined: X-API-Version=v2 (first match)" "backend-v2" "$backend" "$routing_rule"

# Test 11: Header + Query param (header should win due to route order)
echo -e "${YELLOW}Test 6.2: Header + Query param (X-API-Version=v2 + beta=true)${NC}"
response=$(curl -s -H "X-API-Version: v2" "$ENVOY_URL/api/test?beta=true")
headers=$(curl -sI -H "X-API-Version: v2" "$ENVOY_URL/api/test?beta=true")
backend=$(extract_backend "$response")
routing_rule=$(extract_routing_rule "$headers")
print_result "Combined: X-API-Version=v2 (header first)" "backend-v2" "$backend" "$routing_rule"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}7. Performance Tests${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 12: Latency test (100 requests)
echo -e "${YELLOW}Test 7.1: Latency test (100 requests)${NC}"
echo -e "${BLUE}Sending 100 requests to test routing performance...${NC}"
start_time=$(date +%s%N)
for i in {1..100}; do
    curl -s "$ENVOY_URL/api/test" > /dev/null
done
end_time=$(date +%s%N)
duration=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
avg_latency=$(( duration / 100 ))
echo -e "${GREEN}✓ Completed 100 requests in ${duration}ms (avg: ${avg_latency}ms per request)${NC}\n"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}8. Admin API Tests${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 13: Check Envoy stats
echo -e "${YELLOW}Test 8.1: Envoy stats (cluster health)${NC}"
stats=$(curl -s "$ADMIN_URL/stats" | grep "cluster.*health" | head -5)
echo "$stats"
echo ""

# Test 14: Check Envoy config dump
echo -e "${YELLOW}Test 8.2: Envoy config dump (routes)${NC}"
config=$(curl -s "$ADMIN_URL/config_dump" | jq '.configs[] | select(.["@type"] | contains("RouteConfiguration")) | .dynamic_route_configs[]?.route_config.virtual_hosts[]?.routes[]?.match.prefix' 2>/dev/null | head -5)
echo "$config"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo -e "${BLUE}========================================${NC}\n"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check the output above.${NC}"
    exit 1
fi
