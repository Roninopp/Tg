#!/bin/bash

# Virtual Environment Setup for Python 3.11+
# Fixes "externally-managed-environment" error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}Virtual Environment Setup${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if venv already exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
    echo "Do you want to recreate it? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -rf venv
        echo -e "${GREEN}✓ Removed old venv${NC}"
    else
        echo -e "${GREEN}✓ Using existing venv${NC}"
    fi
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv venv
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    else
        echo -e "${RED}✗ Failed to create venv${NC}"
        echo "Install python3-venv: sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate venv
echo ""
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}✗ Failed to activate venv${NC}"
    exit 1
fi

# Upgrade pip
echo ""
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip

# Run dependency installer
echo ""
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}Installing Dependencies${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

python install_dependencies.py

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${GREEN}✓ SETUP COMPLETE!${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    echo "Virtual environment is ACTIVE (venv)"
    echo ""
    echo -e "${YELLOW}⚠ IMPORTANT:${NC}"
    echo "Always activate venv before running the bot!"
    echo ""
    echo "To activate in future:"
    echo -e "${BLUE}  source venv/bin/activate${NC}"
    echo ""
    echo "To deactivate:"
    echo -e "${BLUE}  deactivate${NC}"
    echo ""
    echo "Now you can run:"
    echo -e "${BLUE}  python3 lavalink_setup.py${NC}"
    echo -e "${BLUE}  python3 music_bot.py${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Installation failed${NC}"
    echo "Check errors above"
    exit 1
fi
