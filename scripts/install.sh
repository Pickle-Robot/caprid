#!/bin/bash
# Installation script for Reolink Stream Processor

echo "🚀 Installing Reolink Stream Processor..."

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ required. Found: $python_version"
    exit 1
fi

echo "✅ Python version OK: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
            # ...existing code...
        
        # Create virtual environment
        if [ ! -d "venv" ]; then
            echo "📦 Creating virtual environment..."
            python3 -m venv venv
        fi
        
        # Install ffmpeg if not present
        if ! command -v ffmpeg >/dev/null 2>&1; then
            echo "🔧 Installing ffmpeg (required for video processing)..."
            sudo apt-get update
            sudo apt-get install -y ffmpeg
        else
            echo "✅ ffmpeg already installed."
        fi
        
        # ...existing code... -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p output/segments
mkdir -p logs
mkdir -p examples

# Set up configuration
if [ ! -f "config.yaml" ]; then
    echo "⚙️ Creating default config.yaml..."
    cat > config.yaml << 'EOF'
reolink:
  host: "192.168.1.100"  # Update with your camera IP
  username: "admin"
  password: "change_me"   # Update with your camera password
  port: 80
  channel: 0

stream:
  resolution: "HD"
  fps: 15
  timeout: 30

processing:
  save_frames: false
  output_dir: "./output"
  enable_motion_detection: true
  motion_threshold: 1000
  segment_recording:
    enabled: true
    buffer_seconds: 60
    format: "mp4"
    fps: 30

logging:
  level: "INFO"
  file: "logs/reolink_processor.log"
EOF
    echo "📝 Please edit config.yaml with your camera settings!"
fi

# Set up environment file
if [ ! -f ".env" ]; then
    echo "🔐 Creating .env template..."
    cat > .env << 'EOF'
# Reolink Camera Settings
REOLINK_HOST=192.168.1.100
REOLINK_USER=admin
REOLINK_PASS=your_password_here
REOLINK_PORT=80
REOLINK_CHANNEL=0
EOF
    echo "🔑 Please edit .env with your camera credentials!"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your camera settings"
echo "2. Run: ./scripts/run.sh"
echo "3. Or: source venv/bin/activate && python -m src.main"
