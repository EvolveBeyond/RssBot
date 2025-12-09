#!/bin/bash

# Test script for LOCAL_ROUTER_MODE functionality
# Tests both router mode and REST mode to ensure compatibility

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Testing LOCAL_ROUTER_MODE Functionality${NC}"
echo "=============================================="

# Configuration
SERVICE_TOKEN="${SERVICE_TOKEN:-dev_service_token_change_in_production}"
CONTROLLER_PORT=8004

# Test counters
PASSED=0
FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local description=$1
    local url=$2
    local expected_status=$3
    
    echo -n "Testing $description... "
    
    if command -v curl &> /dev/null; then
        if [[ "$url" == *"/health"* || "$url" == *"/ready"* ]]; then
            # Health endpoints don't need auth token
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$url" || echo "HTTPSTATUS:000")
        else
            # Other endpoints need service token
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" -H "X-Service-Token: $SERVICE_TOKEN" "$url" || echo "HTTPSTATUS:000")
        fi
        
        status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
        
        if [[ "$status" == "$expected_status" ]]; then
            echo -e "${GREEN}✓ PASS${NC}"
            ((PASSED++))
        else
            echo -e "${RED}✗ FAIL${NC} (Expected: $expected_status, Got: $status)"
            ((FAILED++))
        fi
    else
        echo -e "${RED}✗ SKIP${NC} (curl not available)"
        ((FAILED++))
    fi
}

# Test router mode discovery
test_router_mode() {
    echo -e "\n${YELLOW}🔄 Testing Router Mode (LOCAL_ROUTER_MODE=true)${NC}"
    echo "---------------------------------------------------"
    
    # Test controller health with mode information
    test_endpoint "Controller health check" "http://localhost:$CONTROLLER_PORT/health" "200"
    
    # Test local services endpoint
    test_endpoint "Local services info" "http://localhost:$CONTROLLER_PORT/local-services" "200"
    
    # Test mounted services
    test_endpoint "Database service via router" "http://localhost:$CONTROLLER_PORT/db/health" "200"
    test_endpoint "User service via router" "http://localhost:$CONTROLLER_PORT/users/health" "200"
    test_endpoint "Example service via router" "http://localhost:$CONTROLLER_PORT/example/health" "200"
    
    # Test service functionality
    test_endpoint "Database tables endpoint" "http://localhost:$CONTROLLER_PORT/db/tables" "200"
    test_endpoint "User stats endpoint" "http://localhost:$CONTROLLER_PORT/users/stats" "200"
    test_endpoint "Example data endpoint" "http://localhost:$CONTROLLER_PORT/example/data" "200"
    
    echo -e "\n${BLUE}ℹ️  Checking local services info...${NC}"
    if command -v curl &> /dev/null && command -v jq &> /dev/null; then
        local_services=$(curl -s -H "X-Service-Token: $SERVICE_TOKEN" "http://localhost:$CONTROLLER_PORT/local-services" | jq -r '.local_services[]?.name' 2>/dev/null || echo "")
        if [[ -n "$local_services" ]]; then
            echo "Mounted services:"
            echo "$local_services" | sed 's/^/  - /'
        fi
    fi
}

# Test service mode detection
test_mode_detection() {
    echo -e "\n${YELLOW}🔍 Testing Mode Detection${NC}"
    echo "-------------------------"
    
    if command -v curl &> /dev/null && command -v jq &> /dev/null; then
        echo -n "Checking controller mode... "
        mode=$(curl -s "http://localhost:$CONTROLLER_PORT/health" | jq -r '.mode' 2>/dev/null || echo "unknown")
        local_count=$(curl -s "http://localhost:$CONTROLLER_PORT/health" | jq -r '.local_services' 2>/dev/null || echo "0")
        
        echo "Mode: $mode, Local services: $local_count"
        
        if [[ "$mode" == "local_router" ]]; then
            echo -e "${GREEN}✓ Router mode detected${NC}"
            ((PASSED++))
        elif [[ "$mode" == "rest_http" ]]; then
            echo -e "${YELLOW}ℹ️  REST mode detected${NC}"
            ((PASSED++))
        else
            echo -e "${RED}✗ Unknown mode: $mode${NC}"
            ((FAILED++))
        fi
    else
        echo -e "${YELLOW}⚠️  Cannot check mode (jq not available)${NC}"
    fi
}

# Test unified API documentation
test_api_docs() {
    echo -e "\n${YELLOW}📚 Testing API Documentation${NC}"
    echo "------------------------------"
    
    test_endpoint "OpenAPI docs endpoint" "http://localhost:$CONTROLLER_PORT/docs" "200"
    test_endpoint "OpenAPI spec endpoint" "http://localhost:$CONTROLLER_PORT/openapi.json" "200"
}

# Check if controller is running
echo -e "${BLUE}🔍 Checking if controller is running...${NC}"
if ! curl -s "http://localhost:$CONTROLLER_PORT/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Controller not running at port $CONTROLLER_PORT${NC}"
    echo -e "${YELLOW}💡 Start controller with: cd services/controller_svc && rye run python main.py${NC}"
    exit 1
fi

# Run tests
test_mode_detection
test_router_mode
test_api_docs

# Summary
echo -e "\n${YELLOW}📊 Test Summary${NC}"
echo "=================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo -e "Total:  $((PASSED + FAILED))"

if [[ $FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 All router mode tests passed!${NC}"
    
    # Show next steps
    echo -e "\n${BLUE}🚀 Next Steps:${NC}"
    echo "1. Test service functionality via mounted endpoints"
    echo "2. Compare performance with REST mode"
    echo "3. Try creating a new service with router.py"
    
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed.${NC}"
    echo -e "${YELLOW}💡 Troubleshooting:${NC}"
    echo "1. Ensure LOCAL_ROUTER_MODE=true in environment"
    echo "2. Check that services have router.py files"
    echo "3. Verify controller startup logs for mounting errors"
    exit 1
fi