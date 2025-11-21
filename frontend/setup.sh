#!/bin/bash

echo "================================================"
echo "   License Admin Dashboard - Setup Script"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Node.js
echo -e "${BLUE}Checking prerequisites...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}❌ Node.js version must be 18 or higher${NC}"
    echo "Current version: $(node -v)"
    exit 1
fi

echo -e "${GREEN}✓ Node.js $(node -v) detected${NC}"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ npm $(npm -v) detected${NC}"

# Install dependencies
echo ""
echo -e "${BLUE}Installing dependencies...${NC}"
npm install

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create .env.local if not exists
if [ ! -f ".env.local" ]; then
    echo ""
    echo -e "${BLUE}Creating environment file...${NC}"
    cp .env.example .env.local
    echo -e "${GREEN}✓ Created .env.local${NC}"
    echo -e "${YELLOW}⚠ Please edit .env.local and set your LICENSE_SERVER_URL${NC}"
else
    echo -e "${GREEN}✓ .env.local already exists${NC}"
fi

# Check if FastAPI server is running
echo ""
echo -e "${BLUE}Checking FastAPI server...${NC}"
if curl -s http://localhost:8000/admin/stats > /dev/null 2>&1; then
    echo -e "${GREEN}✓ FastAPI server is running${NC}"
else
    echo -e "${YELLOW}⚠ FastAPI server is not running on port 8000${NC}"
    echo "Please start your FastAPI server:"
    echo "  uvicorn app:app --reload --port 8000"
fi

# Summary
echo ""
echo "================================================"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Edit .env.local with your server URL (if needed)"
echo "2. Ensure FastAPI server is running on port 8000"
echo "3. Run: npm run dev"
echo "4. Open: http://localhost:3000"
echo ""
echo "For production build:"
echo "  npm run build && npm start"
echo ""