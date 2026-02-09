#!/bin/bash

# DGI System - Connection Diagnostic Tool
# Run this to diagnose "Erreur de connexion" issues

echo "🔍 DGI System Diagnostic Tool"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Docker
echo "1️⃣ Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"
echo ""

# Check Docker Compose
echo "2️⃣ Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose installed${NC}"
echo ""

# Check running containers
echo "3️⃣ Checking running containers..."
echo ""
docker-compose ps
echo ""

# Check each service health
echo "4️⃣ Testing service health endpoints..."
echo ""

services=(
    "http://localhost:8000;API Gateway"
    "http://localhost:8005;Orchestrator"
    "http://localhost:8004;Intelligence"
    "http://localhost:8001;OCR"
    "http://localhost:8080;Frontend"
)

for service in "${services[@]}"; do
    IFS=";" read -r url name <<< "$service"
    
    if [ "$name" = "Frontend" ]; then
        # Frontend check (just connection)
        if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|301\|302"; then
            echo -e "${GREEN}✓ $name is responding${NC}"
        else
            echo -e "${RED}✗ $name is NOT responding${NC}"
        fi
    else
        # Backend services (check /health)
        response=$(curl -s "${url}/health" 2>&1)
        if echo "$response" | grep -q "healthy\|ok"; then
            echo -e "${GREEN}✓ $name is healthy${NC}"
        else
            echo -e "${RED}✗ $name is NOT healthy${NC}"
            echo -e "${YELLOW}  Response: $response${NC}"
        fi
    fi
done
echo ""

# Check PostgreSQL
echo "5️⃣ Checking PostgreSQL..."
if docker-compose exec -T postgres pg_isready -U dgi_user &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}✗ PostgreSQL is NOT ready${NC}"
fi
echo ""

# Check environment variables
echo "6️⃣ Checking environment variables..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env file exists${NC}"
    
    if grep -q "ANTHROPIC_API_KEY=sk-ant" .env; then
        echo -e "${GREEN}✓ Anthropic API key configured${NC}"
    else
        echo -e "${RED}✗ Anthropic API key missing or invalid${NC}"
    fi
else
    echo -e "${RED}✗ .env file not found${NC}"
fi
echo ""

# Check Google Cloud credentials
echo "7️⃣ Checking Google Cloud credentials..."
if [ -f "gcp-key.json" ] || [ -f "credentials/google-credentials.json" ]; then
    echo -e "${GREEN}✓ Google Cloud credentials found${NC}"
else
    echo -e "${YELLOW}⚠ Google Cloud credentials not found${NC}"
    echo "  Location: gcp-key.json or credentials/google-credentials.json"
fi
echo ""

# Test API endpoint
echo "8️⃣ Testing API Gateway endpoint..."
login_response=$(curl -s -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"demo@dgi.ma","password":"demo123"}' 2>&1)

if echo "$login_response" | grep -q "access_token"; then
    echo -e "${GREEN}✓ API Gateway authentication working${NC}"
else
    echo -e "${RED}✗ API Gateway authentication failed${NC}"
    echo -e "${YELLOW}Response: $login_response${NC}"
fi
echo ""

# Check container logs for errors
echo "9️⃣ Checking for recent errors in logs..."
echo ""
echo "API Gateway errors:"
docker-compose logs --tail=10 api-gateway 2>&1 | grep -i "error\|failed\|exception" || echo "  No errors found"
echo ""
echo "Orchestrator errors:"
docker-compose logs --tail=10 orchestrator-service 2>&1 | grep -i "error\|failed\|exception" || echo "  No errors found"
echo ""

# Summary
echo "================================"
echo "📊 Diagnostic Summary"
echo "================================"
echo ""
echo "Common fixes:"
echo ""
echo "1. If services are not running:"
echo "   docker-compose up -d"
echo ""
echo "2. If services are unhealthy:"
echo "   docker-compose restart"
echo ""
echo "3. If API key issues:"
echo "   Check .env file and ensure ANTHROPIC_API_KEY is set"
echo ""
echo "4. If frontend can't connect:"
echo "   Check VITE_API_URL in frontend/.env"
echo "   Should be: http://localhost:8000"
echo ""
echo "5. View full logs:"
echo "   docker-compose logs -f"
echo ""
echo "6. Reset everything:"
echo "   docker-compose down -v"
echo "   docker-compose up -d"
echo ""