#!/bin/bash
# Quickstart script for Envoy Advanced Routing demo
# Starts all services and runs comprehensive tests

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ███████╗███╗   ██╗██╗   ██╗ ██████╗ ██╗   ██╗             ║
║   ██╔════╝████╗  ██║██║   ██║██╔═══██╗╚██╗ ██╔╝             ║
║   █████╗  ██╔██╗ ██║██║   ██║██║   ██║ ╚████╔╝              ║
║   ██╔══╝  ██║╚██╗██║╚██╗ ██╔╝██║   ██║  ╚██╔╝               ║
║   ███████╗██║ ╚████║ ╚████╔╝ ╚██████╔╝   ██║                ║
║   ╚══════╝╚═╝  ╚═══╝  ╚═══╝   ╚═════╝    ╚═╝                ║
║                                                               ║
║           Advanced Routing Demo - Quickstart                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BLUE}This script will:${NC}"
echo "  1. Build all required Docker images"
echo "  2. Start Envoy Gateway with 8 services"
echo "  3. Wait for all services to be healthy"
echo "  4. Run comprehensive routing tests"
echo ""
echo -e "${YELLOW}Features tested:${NC}"
echo "  ✓ Header-based Routing (X-API-Version, User-Agent, X-Beta-Features)"
echo "  ✓ Query Parameter Routing (version, beta, admin)"
echo "  ✓ JWT Claim-based Routing (role=admin)"
echo "  ✓ GeoIP-based Routing (country=DE)"
echo "  ✓ Fallback Routing (default backend)"
echo ""
read -p "Press ENTER to continue or Ctrl+C to abort..."

# Step 1: Clean up previous deployment
echo -e "\n${BLUE}Step 1/5: Cleaning up previous deployment...${NC}"
docker compose -f docker-compose-improved.yml down -v 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Step 2: Build images
echo -e "\n${BLUE}Step 2/5: Building Docker images...${NC}"
docker compose -f docker-compose-improved.yml build --parallel
echo -e "${GREEN}✓ Images built${NC}"

# Step 3: Start services
echo -e "\n${BLUE}Step 3/5: Starting services...${NC}"
docker compose -f docker-compose-improved.yml up -d

echo -e "${YELLOW}Services started:${NC}"
docker compose -f docker-compose-improved.yml ps

# Step 4: Wait for services to be healthy
echo -e "\n${BLUE}Step 4/5: Waiting for services to be healthy...${NC}"
echo -e "${YELLOW}This may take 30-60 seconds...${NC}"

MAX_WAIT=60
WAITED=0
ALL_HEALTHY=false

while [ $WAITED -lt $MAX_WAIT ]; do
    # Check Envoy readiness
    if curl -sf http://localhost:9901/ready > /dev/null 2>&1; then
        # Check JWKS service
        if curl -sf http://localhost:8080/.well-known/jwks.json > /dev/null 2>&1; then
            echo -e "${GREEN}✓ All services are healthy!${NC}"
            ALL_HEALTHY=true
            break
        fi
    fi

    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

echo ""

if [ "$ALL_HEALTHY" = false ]; then
    echo -e "${RED}❌ Services did not become healthy within ${MAX_WAIT}s${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    docker compose -f docker-compose-improved.yml logs --tail=20
    exit 1
fi

# Print service status
echo -e "\n${CYAN}Service Status:${NC}"
echo "┌─────────────────────────┬──────────┬────────────────────┐"
echo "│ Service                 │ Port     │ Status             │"
echo "├─────────────────────────┼──────────┼────────────────────┤"
printf "│ %-23s │ %-8s │ " "Envoy Gateway" "8080"
if curl -sf http://localhost:8080/api/test > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}          │"
else
    echo -e "${RED}✗ Down${NC}             │"
fi
printf "│ %-23s │ %-8s │ " "Envoy Admin" "9901"
if curl -sf http://localhost:9901/ready > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}          │"
else
    echo -e "${RED}✗ Down${NC}             │"
fi
printf "│ %-23s │ %-8s │ " "JWKS Service" "8080"
if curl -sf http://localhost:8080/.well-known/jwks.json > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}          │"
else
    echo -e "${RED}✗ Down${NC}             │"
fi
echo "└─────────────────────────┴──────────┴────────────────────┘"

# Step 5: Run tests
echo -e "\n${BLUE}Step 5/5: Running comprehensive routing tests...${NC}"
echo ""

# Check if Python is available
if command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Running Python test suite...${NC}"
    chmod +x test_routing_comprehensive.py
    python3 test_routing_comprehensive.py
    TEST_EXIT_CODE=$?
else
    echo -e "${YELLOW}Python3 not found, running bash test suite...${NC}"
    chmod +x test_all_routing.sh
    ./test_all_routing.sh
    TEST_EXIT_CODE=$?
fi

# Summary
echo -e "\n${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                         SUMMARY                               ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed successfully!${NC}"
else
    echo -e "${RED}❌ Some tests failed. Check the output above.${NC}"
fi

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. View Envoy Admin UI: http://localhost:9901"
echo "  2. Test manually:"
echo "     curl -H 'X-API-Version: v2' http://localhost:8080/api/test"
echo "     curl http://localhost:8080/api/test?beta=true"
echo "  3. View logs:"
echo "     docker compose -f docker-compose-improved.yml logs -f envoy"
echo "  4. Stop services:"
echo "     docker compose -f docker-compose-improved.yml down"
echo ""

echo -e "${CYAN}📚 Documentation:${NC}"
echo "  - See README-IMPROVED.md for detailed usage"
echo "  - Envoy config: envoy-improved.yaml"
echo "  - GAL config: gal-config.yaml"
echo ""

exit $TEST_EXIT_CODE
