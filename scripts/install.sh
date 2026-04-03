#!/bin/bash
# Memory Keeper — Quick Install Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "==================================="
echo "  Memory Keeper — Installation"
echo "==================================="
echo ""

# Check Python version
PYTHON=""
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "Error: Python 3.10+ is required but not found."
    echo "Install from https://www.python.org/downloads/"
    exit 1
fi

PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Found Python $PY_VERSION"

$PYTHON -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ required"' 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: Python 3.10+ is required. Found $PY_VERSION."
    exit 1
fi

# Create virtual environment if it doesn't exist
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install memory-keeper
echo ""
echo "Installing Memory Keeper..."
cd "$PROJECT_DIR"
pip install -e ".[dev]"

# Run init
echo ""
echo "Running setup wizard..."
memory-keeper init

echo ""
echo "==================================="
echo "  Installation Complete!"
echo "==================================="
echo ""
echo "To activate the environment in future sessions:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "Start Memory Keeper:"
echo "  memory-keeper serve"
echo ""
echo "Then install the SillyTavern extension:"
echo "  Copy adapters/sillytavern/ to your ST extensions directory"
echo ""
