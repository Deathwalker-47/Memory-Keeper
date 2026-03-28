#!/bin/bash
# Memory Keeper — Quick Install Script

set -e

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
    exit 1
fi

PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Found Python $PY_VERSION"

# Check version >= 3.10
$PYTHON -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ required"' 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: Python 3.10+ is required. Found $PY_VERSION."
    exit 1
fi

# Install memory-keeper
echo ""
echo "Installing Memory Keeper..."
$PYTHON -m pip install -e ".[dev]"

# Run init
echo ""
echo "Running setup wizard..."
memory-keeper init

echo ""
echo "==================================="
echo "  Installation Complete!"
echo "==================================="
echo ""
echo "Start Memory Keeper:"
echo "  memory-keeper serve"
echo ""
echo "Then install the SillyTavern extension:"
echo "  Copy adapters/sillytavern/ to your ST extensions directory"
echo ""
