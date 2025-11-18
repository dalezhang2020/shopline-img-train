#!/bin/bash

###############################################################################
# SKU Recognition API Server Startup Script
#
# This script starts the FastAPI server with proper environment configuration
# Usage:
#   ./scripts/start_api.sh              # Start in production mode
#   ./scripts/start_api.sh --dev        # Start in development mode (hot reload)
#   ./scripts/start_api.sh --workers 4  # Start with 4 workers
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default settings
DEV_MODE=false
WORKERS=1
PORT=8000
HOST="0.0.0.0"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dev)
      DEV_MODE=true
      shift
      ;;
    --workers)
      WORKERS="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  --dev              Start in development mode with hot reload"
      echo "  --workers N        Number of Uvicorn workers (default: 1)"
      echo "  --port PORT        Port to listen on (default: 8000)"
      echo "  --host HOST        Host to bind to (default: 0.0.0.0)"
      echo "  --help             Show this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Print banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         SKU Recognition API Server Startup                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Change to project root
cd "$PROJECT_ROOT"
echo -e "${YELLOW}📂 Project Root:${NC} $PROJECT_ROOT"

# Check if .env file exists
if [ ! -f ".env" ]; then
  echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env with your MySQL credentials${NC}"
  else
    echo -e "${RED}❌ .env.example not found!${NC}"
    exit 1
  fi
fi

# Load environment variables
if [ -f ".env" ]; then
  export $(cat .env | grep -v '^#' | xargs)
  echo -e "${GREEN}✅ Loaded environment variables from .env${NC}"
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
  echo -e "${RED}❌ Python 3 is not installed!${NC}"
  exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✅ Python:${NC} $PYTHON_VERSION"

# Check if virtual environment should be used
if [ -d "venv" ]; then
  echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
  source venv/bin/activate
  echo -e "${GREEN}✅ Virtual environment activated${NC}"
elif [ -d ".venv" ]; then
  echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
  source .venv/bin/activate
  echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
  echo -e "${YELLOW}⚠️  No virtual environment found. Using system Python.${NC}"
  echo -e "${YELLOW}   Consider creating one: python3 -m venv venv${NC}"
fi

# Check if required packages are installed
echo -e "${YELLOW}🔍 Checking dependencies...${NC}"

MISSING_PACKAGES=()

python3 -c "import fastapi" 2>/dev/null || MISSING_PACKAGES+=("fastapi")
python3 -c "import uvicorn" 2>/dev/null || MISSING_PACKAGES+=("uvicorn")
python3 -c "import torch" 2>/dev/null || MISSING_PACKAGES+=("torch")
python3 -c "import PIL" 2>/dev/null || MISSING_PACKAGES+=("Pillow")

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
  echo -e "${RED}❌ Missing packages: ${MISSING_PACKAGES[*]}${NC}"
  echo -e "${YELLOW}📦 Installing dependencies from requirements.txt...${NC}"
  pip install -r requirements.txt
  echo -e "${GREEN}✅ Dependencies installed${NC}"
else
  echo -e "${GREEN}✅ All required packages installed${NC}"
fi

# Check if vector database exists
FAISS_INDEX="data/embeddings/faiss_index.bin"
METADATA="data/embeddings/sku_metadata.pkl"

if [ ! -f "$FAISS_INDEX" ] || [ ! -f "$METADATA" ]; then
  echo -e "${RED}❌ Vector database not found!${NC}"
  echo -e "${YELLOW}📊 You need to build the vector database first:${NC}"
  echo -e "   ${BLUE}python scripts/build_robust_vector_db.py --augment-per-image 2${NC}"
  echo ""
  read -p "Do you want to build it now? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🔨 Building vector database (this may take a while)...${NC}"
    python3 scripts/build_robust_vector_db.py --augment-per-image 2
    echo -e "${GREEN}✅ Vector database built successfully${NC}"
  else
    echo -e "${RED}❌ Cannot start API without vector database${NC}"
    exit 1
  fi
else
  # Get database size
  DB_SIZE=$(python3 -c "import pickle; print(len(pickle.load(open('$METADATA', 'rb'))))" 2>/dev/null || echo "unknown")
  echo -e "${GREEN}✅ Vector database found${NC}"
  echo -e "   📊 Database size: ${BLUE}${DB_SIZE}${NC} SKUs"
fi

# Check if config file exists
if [ ! -f "config/config.yaml" ]; then
  echo -e "${RED}❌ config/config.yaml not found!${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Configuration file found${NC}"

# Print server configuration
echo ""
echo -e "${BLUE}🚀 Server Configuration:${NC}"
echo -e "   Host:    ${GREEN}${HOST}${NC}"
echo -e "   Port:    ${GREEN}${PORT}${NC}"
echo -e "   Workers: ${GREEN}${WORKERS}${NC}"
echo -e "   Mode:    ${GREEN}$([ "$DEV_MODE" = true ] && echo "Development (hot reload)" || echo "Production")${NC}"
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Build uvicorn command
UVICORN_CMD="uvicorn scripts.api_server:app --host $HOST --port $PORT"

if [ "$DEV_MODE" = true ]; then
  UVICORN_CMD="$UVICORN_CMD --reload"
  echo -e "${YELLOW}🔥 Starting in DEVELOPMENT mode with hot reload...${NC}"
else
  UVICORN_CMD="$UVICORN_CMD --workers $WORKERS"
  echo -e "${GREEN}🔥 Starting in PRODUCTION mode...${NC}"
fi

echo -e "${YELLOW}📝 Access the API documentation at:${NC}"
echo -e "   ${BLUE}http://localhost:${PORT}/docs${NC} (Swagger UI)"
echo -e "   ${BLUE}http://localhost:${PORT}/redoc${NC} (ReDoc)"
echo ""
echo -e "${YELLOW}💡 Health check:${NC}"
echo -e "   ${BLUE}curl http://localhost:${PORT}/api/v1/health${NC}"
echo ""
echo -e "${GREEN}Press Ctrl+C to stop the server${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Start the server
exec $UVICORN_CMD
