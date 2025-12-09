#!/bin/bash

# RSS Bot Platform - Development Startup Script
# Starts all services natively using Rye for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting RSS Bot Platform (Development Mode)${NC}"
echo "=================================================="

# Check if .env file exists
if [[ ! -f .env ]]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}📝 Please edit .env file with your actual configuration before proceeding.${NC}"
    read -p "Press Enter to continue after editing .env file..."
fi

# Source environment variables
if [[ -f .env ]]; then
    echo -e "${BLUE}🔧 Loading environment variables...${NC}"
    set -a
    source .env
    set +a
fi

# Check if Rye is installed
if ! command -v rye &> /dev/null; then
    echo -e "${RED}❌ Rye is not installed. Please install Rye first:${NC}"
    echo "curl -sSf https://rye-up.com/get | bash"
    exit 1
fi

# Check if dependencies are installed
if [[ ! -d .venv ]]; then
    echo -e "${YELLOW}📦 Installing dependencies with Rye...${NC}"
    rye sync
fi

# Function to start a service in background
start_service() {
    local service_name=$1
    local service_path=$2
    local port=$3
    
    echo -e "${BLUE}Starting $service_name on port $port...${NC}"
    
    cd "$service_path"
    rye run python main.py &
    local pid=$!
    echo $pid > "/tmp/rssbot_${service_name}.pid"
    cd - > /dev/null
    
    # Wait a moment for service to start
    sleep 2
    
    # Check if service is responding
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $service_name started successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  $service_name may be starting up (port $port)${NC}"
    fi
}

# Function to stop all services
stop_services() {
    echo -e "\n${YELLOW}🛑 Stopping all services...${NC}"
    
    for pid_file in /tmp/rssbot_*.pid; do
        if [[ -f "$pid_file" ]]; then
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                echo "Stopping process $pid"
                kill "$pid"
            fi
            rm -f "$pid_file"
        fi
    done
    
    echo -e "${GREEN}✓ All services stopped${NC}"
    exit 0
}

# Set up signal handlers
trap stop_services SIGINT SIGTERM

# Start infrastructure services first (if not using Docker)
echo -e "\n${YELLOW}🗄️  Infrastructure Services${NC}"
echo "Note: Make sure PostgreSQL and Redis are running"
echo "Docker: docker-compose -f infra/docker-compose.yml up -d postgres redis"
echo "Arch Linux: sudo systemctl start postgresql redis"

# Wait for user confirmation
read -p "Press Enter when database services are ready..."

# Start core services in order
echo -e "\n${YELLOW}🔧 Starting Core Services${NC}"
echo "--------------------------------"

# Database service first
start_service "db_svc" "services/db_svc" "8001"

# Controller service
start_service "controller_svc" "services/controller_svc" "8004"

# Bot service
start_service "bot_svc" "services/bot_svc" "8002"

echo -e "\n${YELLOW}⚙️  Starting Application Services${NC}"
echo "-----------------------------------"

# Formatting service
start_service "formatting_svc" "services/formatting_svc" "8006"

# Payment service
start_service "payment_svc" "services/payment_svc" "8003"

# User service
start_service "user_svc" "services/user_svc" "8008"

# Channel manager service
start_service "channel_mgr_svc" "services/channel_mgr_svc" "8007"

# AI service
start_service "ai_svc" "services/ai_svc" "8005"

# MiniApp service
start_service "miniapp_svc" "services/miniapp_svc" "8009"

echo -e "\n${GREEN}🎉 All services started!${NC}"
echo "=============================="
echo -e "Dashboard: ${BLUE}http://localhost:8009/dashboard${NC}"
echo -e "API Docs:"
echo -e "  - Controller: ${BLUE}http://localhost:8004/docs${NC}"
echo -e "  - Database:   ${BLUE}http://localhost:8001/docs${NC}"
echo -e "  - Bot:        ${BLUE}http://localhost:8002/docs${NC}"
echo -e "  - Formatting: ${BLUE}http://localhost:8006/docs${NC}"
echo -e "  - Payment:    ${BLUE}http://localhost:8003/docs${NC}"
echo -e "  - User:       ${BLUE}http://localhost:8008/docs${NC}"
echo -e "  - Channels:   ${BLUE}http://localhost:8007/docs${NC}"
echo -e "  - AI:         ${BLUE}http://localhost:8005/docs${NC}"
echo -e "  - MiniApp:    ${BLUE}http://localhost:8009/docs${NC}"

echo -e "\n${YELLOW}📊 Run smoke tests:${NC} ./scripts/smoke_test.sh"
echo -e "${YELLOW}🛑 Stop all services:${NC} Ctrl+C or kill this script"

# Keep script running and monitor services
echo -e "\n${BLUE}🔍 Monitoring services... (Ctrl+C to stop)${NC}"
while true; do
    sleep 30
    
    # Check if any service has died
    dead_services=()
    for pid_file in /tmp/rssbot_*.pid; do
        if [[ -f "$pid_file" ]]; then
            pid=$(cat "$pid_file")
            if ! kill -0 "$pid" 2>/dev/null; then
                service_name=$(basename "$pid_file" .pid | sed 's/rssbot_//')
                dead_services+=("$service_name")
            fi
        fi
    done
    
    if [[ ${#dead_services[@]} -gt 0 ]]; then
        echo -e "${RED}⚠️  Services that stopped: ${dead_services[*]}${NC}"
    fi
done