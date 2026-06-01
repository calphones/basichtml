#!/usr/bin/env bash
# Interior AI Designer — Environment Setup Script
# Run from the repo root: bash interior_ai/scripts/setup_env.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== Interior AI Designer — Environment Setup ==="
echo "Root: $ROOT"
echo ""

# ── Python version check ──────────────────────────────────────────────────
PYTHON_MIN="3.10"
python3 -c "
import sys
v = sys.version_info
req = tuple(int(x) for x in '${PYTHON_MIN}'.split('.'))
if (v.major, v.minor) < req:
    print(f'ERROR: Python {req[0]}.{req[1]}+ required, got {v.major}.{v.minor}')
    sys.exit(1)
print(f'Python {v.major}.{v.minor}.{v.micro} ✓')
"

# ── Virtualenv ────────────────────────────────────────────────────────────
if [ ! -d "$ROOT/.venv" ]; then
    echo "Creating virtualenv at .venv ..."
    python3 -m venv "$ROOT/.venv"
fi
source "$ROOT/.venv/bin/activate"

echo "Installing Python dependencies ..."
pip install --upgrade pip --quiet
pip install -r "$ROOT/interior_ai/requirements.txt" --quiet
echo "Python dependencies installed ✓"

# ── Blender check ─────────────────────────────────────────────────────────
if command -v blender &>/dev/null; then
    BLENDER_VER=$(blender --version 2>&1 | head -1)
    echo "Blender: $BLENDER_VER ✓"
    export BLENDER_PATH=$(command -v blender)
else
    echo "WARNING: Blender not found in PATH."
    echo "  Download from https://www.blender.org/download/ (3.6 LTS or 4.x)"
    echo "  Then set: export BLENDER_PATH=/path/to/blender"
fi

# ── Tesseract check ───────────────────────────────────────────────────────
if command -v tesseract &>/dev/null; then
    echo "Tesseract OCR: $(tesseract --version 2>&1 | head -1) ✓"
else
    echo "INFO: Tesseract OCR not found. Install for dimension annotation parsing:"
    echo "  Ubuntu: sudo apt install tesseract-ocr"
    echo "  macOS:  brew install tesseract"
fi

# ── Create required directories ───────────────────────────────────────────
mkdir -p "$ROOT/assets/furniture" "$ROOT/assets/hdri" "$ROOT/assets/textures"
mkdir -p "$ROOT/output/renders" "$ROOT/output/scenes"
mkdir -p "/tmp/interior_ai/uploads"
echo "Asset directories created ✓"

# ── Node.js / frontend ────────────────────────────────────────────────────
if command -v node &>/dev/null; then
    echo "Node.js: $(node --version) ✓"
    if [ -d "$ROOT/interior_ai/frontend" ]; then
        echo "Installing frontend dependencies ..."
        cd "$ROOT/interior_ai/frontend" && npm install --silent
        echo "Frontend dependencies installed ✓"
        cd "$ROOT"
    fi
else
    echo "INFO: Node.js not found. Frontend will not be available."
    echo "  Install from https://nodejs.org (18+)"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start the system:"
echo "  source .venv/bin/activate"
echo "  # API server:"
echo "  python -m interior_ai.main server"
echo ""
echo "  # Frontend (separate terminal):"
echo "  cd interior_ai/frontend && npm run dev"
echo ""
echo "  # CLI design generation:"
echo "  python -m interior_ai.main design --floor-plan your_plan.pdf --style modern_organic"
