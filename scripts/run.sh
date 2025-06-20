#!/bin/bash
# Run script for Reolink Stream Processor

echo "🎥 Starting Reolink Stream Processor..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./scripts/install.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "🔧 Loading environment variables..."
    export $(cat .env | grep -v '#' | xargs)
fi

# Check if config exists
if [ ! -f "config.yaml" ]; then
    echo "❌ config.yaml not found. Run ./scripts/install.sh first"
    exit 1
fi

# Create output directories if they don't exist
mkdir -p output/segments
mkdir -p logs

# Run the application
echo "▶️ Starting application..."
echo "Press Ctrl+C to stop"
echo "Press 'q' in video window to quit"
echo ""

python -m src.main

echo "👋 Application stopped"
