#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check venv
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Создаю виртуальное окружение...${NC}"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -e ".[dev]" -q
fi

# Activate
source "$VENV_DIR/bin/activate"

# Run tempmail with all args
exec tempmail "$@"
