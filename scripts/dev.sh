#!/bin/bash
# Development script with auto-restart

echo "🔧 Starting Development Mode..."

# Check if watchdog is installed
if ! python -c "import watchdog" 2>/dev/null; then
    echo "📦 Installing watchdog for auto-restart..."
    pip install watchdog
fi

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

echo "👁️ Watching for file changes... (Ctrl+C to stop)"
echo "Files will auto-restart when you modify Python files"

# Auto-restart on file changes
watchmedo auto-restart \
    --patterns="*.py" \
    --recursive \
    --signal SIGTERM \
    PYTHONPATH=./src python -- -m main
