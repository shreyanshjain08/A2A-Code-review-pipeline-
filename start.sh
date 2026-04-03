#!/bin/bash
# ============================================================
# A2A Code Review Pipeline — Start All Services
# ============================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}"
echo "╔══════════════════════════════════════════════╗"
echo "║   🚀 A2A Code Review Pipeline               ║"
echo "║   Agent-to-Agent Protocol Demo               ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}❌ Please edit .env and add your GEMINI_API_KEY${NC}"
    echo -e "   Get a free key from: ${BLUE}https://aistudio.google.com${NC}"
    exit 1
fi

# Check for GEMINI_API_KEY
source .env
if [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ] || [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}❌ GEMINI_API_KEY is not set in .env${NC}"
    echo -e "   Get a free key from: ${BLUE}https://aistudio.google.com${NC}"
    exit 1
fi

echo -e "${GREEN}✅ GEMINI_API_KEY found${NC}"
echo ""

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down all agents...${NC}"
    kill $(jobs -p) 2>/dev/null
    wait 2>/dev/null
    echo -e "${GREEN}✅ All agents stopped${NC}"
}
trap cleanup EXIT

# Start Code Writer Agent
echo -e "${BLUE}🖊️  Starting Code Writer Agent on port ${CODE_WRITER_PORT:-5001}...${NC}"
venv/bin/python agents/code_writer/agent.py &
sleep 2

# Start Code Reviewer Agent
echo -e "${BLUE}🔍 Starting Code Reviewer Agent on port ${CODE_REVIEWER_PORT:-5002}...${NC}"
venv/bin/python agents/code_reviewer/agent.py &
sleep 2

# Start Code Refactorer Agent
echo -e "${BLUE}✨ Starting Code Refactorer Agent on port ${CODE_REFACTORER_PORT:-5003}...${NC}"
venv/bin/python agents/code_refactorer/agent.py &
sleep 2

# Start Orchestrator
echo -e "${BLUE}🚀 Starting Orchestrator on port ${ORCHESTRATOR_PORT:-3000}...${NC}"
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ All services are running!               ║${NC}"
echo -e "${GREEN}║                                              ║${NC}"
echo -e "${GREEN}║   🌐 Web UI: http://localhost:${ORCHESTRATOR_PORT:-3000}            ║${NC}"
echo -e "${GREEN}║                                              ║${NC}"
echo -e "${GREEN}║   Agents:                                    ║${NC}"
echo -e "${GREEN}║   • Code Writer:    :${CODE_WRITER_PORT:-5001}                  ║${NC}"
echo -e "${GREEN}║   • Code Reviewer:  :${CODE_REVIEWER_PORT:-5002}                  ║${NC}"
echo -e "${GREEN}║   • Code Refactorer::${CODE_REFACTORER_PORT:-5003}                  ║${NC}"
echo -e "${GREEN}║                                              ║${NC}"
echo -e "${GREEN}║   Press Ctrl+C to stop all services          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

venv/bin/python orchestrator/server.py
