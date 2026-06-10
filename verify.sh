#!/bin/bash
# 🔍 VERIFICATION SCRIPT - Check if all Aztec Explorer files are in place

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         AZTEC EXPLORER - PROJECT VERIFICATION                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (missing)"
        return 1
    fi
}

echo "📦 Core Application Files"
echo "─────────────────────────────────────────────────────────────────"
check_file "app/__init__.py"
check_file "app/config.py"
check_file "app/extensions.py"
check_file "run.py"
check_file "manage.py"
echo ""

echo "📍 Places Module"
echo "─────────────────────────────────────────────────────────────────"
check_file "app/places/__init__.py"
check_file "app/places/models.py"
check_file "app/places/repositories.py"
check_file "app/places/services.py"
check_file "app/places/controllers.py"
echo ""

echo "🚶 Tours Module"
echo "─────────────────────────────────────────────────────────────────"
check_file "app/tours/__init__.py"
check_file "app/tours/models.py"
check_file "app/tours/repositories.py"
check_file "app/tours/services.py"
check_file "app/tours/controllers.py"
echo ""

echo "👤 Users Module"
echo "─────────────────────────────────────────────────────────────────"
check_file "app/users/__init__.py"
check_file "app/users/models.py"
check_file "app/users/repositories.py"
check_file "app/users/services.py"
check_file "app/users/controllers.py"
echo ""

echo "💳 Payments Module"
echo "─────────────────────────────────────────────────────────────────"
check_file "app/payments/__init__.py"
check_file "app/payments/models.py"
check_file "app/payments/repositories.py"
check_file "app/payments/services.py"
check_file "app/payments/controllers.py"
echo ""

echo "📚 Historical Module"
echo "─────────────────────────────────────────────────────────────────"
check_file "app/historical/__init__.py"
check_file "app/historical/models.py"
check_file "app/historical/repositories.py"
check_file "app/historical/services.py"
check_file "app/historical/controllers.py"
echo ""

echo "🔧 Shared Utilities"
echo "─────────────────────────────────────────────────────────────────"
check_file "app/shared/__init__.py"
check_file "app/shared/enums.py"
check_file "app/shared/constants.py"
check_file "app/shared/utils.py"
echo ""

echo "🧪 Tests"
echo "─────────────────────────────────────────────────────────────────"
check_dir "tests"
check_file "tests/conftest.py"
check_file "tests/test_places.py"
check_file "tests/test_users.py"
check_file "tests/test_tours.py"
check_file "tests/test_historical.py"
echo ""

echo "📋 Configuration & Dependencies"
echo "─────────────────────────────────────────────────────────────────"
check_file "requirements.txt"
check_file ".env.example"
check_file ".gitignore"
echo ""

echo "📚 Documentation"
echo "─────────────────────────────────────────────────────────────────"
check_file "README.md"
check_file "BACKEND_README.md"
check_file "BACKEND_SETUP.md"
check_file "API_EXAMPLES.md"
check_file "SETUP_COMPLETE.md"
check_file "ARCHITECTURE_VISUAL.md"
echo ""

echo "🌱 Database & Seeding"
echo "─────────────────────────────────────────────────────────────────"
check_file "seed.py"
check_dir "migrations"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "📊 Module Count"
echo "─────────────────────────────────────────────────────────────────"
MODULES=$(find app -maxdepth 1 -type d -not -name "app" -not -name "shared" -not -name "middleware" | wc -l)
echo "Functional Modules: $MODULES (expected 5)"
echo ""

echo "🐍 Python Files"
echo "─────────────────────────────────────────────────────────────────"
PY_FILES=$(find app -name "*.py" | wc -l)
echo "Total Python files: $PY_FILES"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "✨ Verification Complete!"
echo ""
echo "Next Steps:"
echo "  1. Configure .env: cp .env.example .env"
echo "  2. Install dependencies: pip install -r requirements.txt"
echo "  3. Initialize database: python manage.py init"
echo "  4. Seed test data: python seed.py"
echo "  5. Run server: python run.py"
echo ""
echo "Documentation:"
echo "  - Full guide: BACKEND_README.md"
echo "  - API examples: API_EXAMPLES.md"
echo "  - Quick start: SETUP_COMPLETE.md"
echo ""
