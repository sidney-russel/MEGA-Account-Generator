#!/bin/bash
set -e

echo "============================================"
echo "  MEGA Account Generator - Linux Build"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "Using: $PYTHON_VERSION"

# Check/install PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
fi

# Find customtkinter path
CTK_PATH=$(python3 -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))" 2>/dev/null)
if [ -z "$CTK_PATH" ]; then
    echo "ERROR: customtkinter not found. Run: pip3 install -r requirements.txt"
    exit 1
fi
echo "CustomTkinter: $CTK_PATH"

# Find megatools path
MEGA_DIR=""
for dir in /usr/bin /usr/local/bin /usr/sbin; do
    if [ -f "$dir/megareg" ]; then
        MEGA_DIR="$dir"
        break
    fi
done

if [ -z "$MEGA_DIR" ]; then
    echo "WARNING: megatools not found in standard paths."
    echo "  Install: sudo apt install megatools"
    echo "  The built binary will need megatools in PATH."
    MEGA_DIR="/usr/bin"
fi
echo "Megatools: $MEGA_DIR"

echo ""
echo "Building standalone binary..."
echo ""

python3 -m PyInstaller --noconfirm --onefile \
    --add-data "$CTK_PATH:customtkinter/" \
    --add-data "logo.ico:." \
    --add-data "logo.png:." \
    --hidden-import "PIL._tkinter_finder" \
    --hidden-import "babel.numbers" \
    --hidden-import "openpyxl" \
    --hidden-import "openpyxl.cell._writer" \
    --hidden-import "openpyxl.workbook._writer" \
    --hidden-import "openpyxl.worksheet._writer" \
    --hidden-import "PIL" \
    --hidden-import "requests" \
    --hidden-import "colorama" \
    --hidden-import "tqdm" \
    --icon "logo.ico" \
    --name "MEGA-Generator" \
    gui.py

echo ""
echo "============================================"
echo "  Build complete!"
echo "============================================"
echo ""
echo "Binary: $(pwd)/dist/MEGA-Generator"
echo "Size: $(du -h dist/MEGA-Generator | cut -f1)"
echo ""
echo "To run:"
echo "  ./dist/MEGA-Generator"
echo ""
echo "To install system-wide:"
echo "  sudo cp dist/MEGA-Generator /usr/local/bin/mega-generator"
echo "  mega-generator"
echo ""
