#!/usr/bin/env bash
# setup_env.sh — Create virtual environment and install dependencies
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "═══════════════════════════════════════"
echo " Career Assistant AI Agent — Setup"
echo "═══════════════════════════════════════"

cd "$PROJECT_DIR"

# 1. Create virtual environment
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment (.venv)..."
    python3 -m venv .venv
else
    echo "→ Virtual environment already exists."
fi

# 2. Activate
echo "→ Activating virtual environment..."
source .venv/bin/activate

# 3. Upgrade pip
echo "→ Upgrading pip..."
pip install --upgrade pip -q

# 4. Install dependencies
echo "→ Installing dependencies..."
pip install -r requirements.txt -q

# 5. Copy .env if not present
if [ ! -f ".env" ]; then
    echo "→ Creating .env from .env.example..."
    cp .env.example .env
    echo "  ⚠️  Please edit .env and fill in your API keys!"
else
    echo "→ .env already exists."
fi

# 6. Create CV profile placeholder if not present
if [ ! -f "data/cv_profile.json" ]; then
    echo "→ Creating data/cv_profile.json from sample..."
    cp data/cv_profile_sample.json data/cv_profile.json
    echo "  ⚠️  Please edit data/cv_profile.json with your real CV data!"
else
    echo "→ data/cv_profile.json already exists."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your OpenAI and Telegram credentials"
echo "  2. Edit data/cv_profile.json with your real CV"
echo "  3. Run: uvicorn app.main:app --reload"
echo "  4. Test: pytest tests/ -v"
