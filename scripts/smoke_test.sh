#!/bin/bash

# RSS Bot Platform - Smoke Test Script
# Tests basic functionality of all services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🧪 Starting RSS Bot Platform Smoke Tests${NC}"
echo "================================================"

# Configuration
BASE_PORTS=(8001 8002 8003 8004 8005 8006 8007 8008 8009)
SERVICE_NAMES=("db_svc" "bot_svc" "payment_svc" "controller_svc" "ai_svc" "formatting_svc" "channel_mgr_svc" "user_svc" "miniapp_svc")
SERVICE_TOKEN="${SERVICE_TOKEN:-dev_service_token_change_in_production}"

# Test counters
PASSED=0
FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local service_name=$1
    local port=$2
    local endpoint=$3
    local expected_status=$4
    local description=$5
    
    echo -n "Testing $service_name $endpoint... "
    
    if command -v curl &> /dev/null; then
        if [[ "$endpoint" == "/health" || "$endpoint" == "/ready" ]]; then
            # Health endpoints don't need auth token
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" "http://localhost:$port$endpoint" || echo "HTTPSTATUS:000")
        else
            # Other endpoints need service token
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" -H "X-Service-Token: $SERVICE_TOKEN" "http://localhost:$port$endpoint" || echo "HTTPSTATUS:000")
        fi
        
        status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
        
        if [[ "$status" == "$expected_status" ]]; then
            echo -e "${GREEN}✓ PASS${NC} ($description)"
            ((PASSED++))
        else
            echo -e "${RED}✗ FAIL${NC} ($description) - Expected: $expected_status, Got: $status"
            ((FAILED++))
        fi
    else
        echo -e "${RED}✗ SKIP${NC} (curl not available)"
        ((FAILED++))
    fi
}

# Test service availability
echo -e "\n${YELLOW}🏥 Health Check Tests${NC}"
echo "------------------------"

for i in "${!SERVICE_NAMES[@]}"; do
    service="${SERVICE_NAMES[$i]}"
    port="${BASE_PORTS[$i]}"
    test_endpoint "$service" "$port" "/health" "200" "Service health check"
done

# Test readiness
echo -e "\n${YELLOW}🚀 Readiness Check Tests${NC}"
echo "-------------------------"

for i in "${!SERVICE_NAMES[@]}"; do
    service="${SERVICE_NAMES[$i]}"
    port="${BASE_PORTS[$i]}"
    test_endpoint "$service" "$port" "/ready" "200" "Service readiness check"
done

# Test service-specific endpoints
echo -e "\n${YELLOW}🔧 Service-Specific Tests${NC}"
echo "--------------------------"

# Database service
test_endpoint "db_svc" "8001" "/tables" "200" "Database introspection"
test_endpoint "db_svc" "8001" "/models" "200" "Model listing"

# Controller service
test_endpoint "controller_svc" "8004" "/services" "200" "Service registry"

# Bot service (might fail if no bot token)
test_endpoint "bot_svc" "8002" "/bot/info" "200" "Bot information"

# Payment service
test_endpoint "payment_svc" "8003" "/plans" "200" "Payment plans"

# User service
test_endpoint "user_svc" "8008" "/stats" "200" "User statistics"

# AI service
test_endpoint "ai_svc" "8005" "/models" "200" "AI models list"

# Formatting service
test_endpoint "formatting_svc" "8006" "/jobs" "200" "Formatting jobs"

# Channel manager service
test_endpoint "channel_mgr_svc" "8007" "/stats" "200" "Channel statistics"

# MiniApp service
test_endpoint "miniapp_svc" "8009" "/api/dashboard-data" "200" "Dashboard data"

# Test service integration (basic flow)
echo -e "\n${YELLOW}🔄 Integration Tests${NC}"
echo "---------------------"

echo -n "Testing service registration flow... "
if command -v curl &> /dev/null; then
    # Try to register a test service with controller
    register_response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -H "X-Service-Token: $SERVICE_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "test_service",
            "version": "1.0.0",
            "base_url": "http://localhost:9999",
            "capabilities": ["test"],
            "health_endpoint": "/health"
        }' \
        "http://localhost:8004/register" || echo "HTTPSTATUS:000")
    
    status=$(echo "$register_response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [[ "$status" == "200" ]]; then
        echo -e "${GREEN}✓ PASS${NC} (Service registration)"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC} (Service registration) - Status: $status"
        ((FAILED++))
    fi
else
    echo -e "${RED}✗ SKIP${NC} (curl not available)"
    ((FAILED++))
fi

# Database connectivity test
echo -n "Testing database connectivity... "
if command -v curl &> /dev/null; then
    db_response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -H "X-Service-Token: $SERVICE_TOKEN" \
        "http://localhost:8001/stats" || echo "HTTPSTATUS:000")
    
    status=$(echo "$db_response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [[ "$status" == "200" ]]; then
        echo -e "${GREEN}✓ PASS${NC} (Database connectivity)"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC} (Database connectivity) - Status: $status"
        ((FAILED++))
    fi
else
    echo -e "${RED}✗ SKIP${NC} (curl not available)"
    ((FAILED++))
fi

# Summary
echo -e "\n${YELLOW}📊 Test Summary${NC}"
echo "=================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo -e "Total:  $((PASSED + FAILED))"

if [[ $FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 All tests passed! The RSS Bot platform is working correctly.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed. Please check the service logs and configuration.${NC}"
    exit 1
fi