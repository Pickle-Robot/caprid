#!/bin/bash
# Test script for Reolink Stream Processor

echo "🧪 Running Reolink Stream Processor Tests..."

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run ./scripts/install.sh first"
    exit 1
fi

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install pytest pytest-cov

# Run unit tests (no hardware required)
echo "🔬 Running unit tests..."
python -m pytest tests/unit/ -v

# Ask if user wants to run integration tests
echo ""
read -p "🤖 Run integration tests? (requires camera connection) [y/N]: " run_integration

if [[ $run_integration =~ ^[Yy]$ ]]; then
    echo "🌐 Running integration tests..."
    
    # Check if test config exists
    if [ ! -f "test_config.yaml" ]; then
        echo "⚙️ Creating test_config.yaml..."
        cp config.yaml test_config.yaml
        echo "📝 Please edit test_config.yaml with test camera settings"
        echo "Press Enter when ready..."
        read
    fi
    
    python -m pytest tests/integration/ -v
else
    echo "⏭️ Skipping integration tests"
fi

echo ""
echo "✅ Testing complete!"