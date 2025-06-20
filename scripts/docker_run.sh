#!/bin/bash
# Docker run script for Reolink Stream Processor

echo "🐳 Running Reolink Stream Processor in Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    echo "🔧 Using docker-compose..."
    
    # Load environment variables
    if [ -f ".env" ]; then
        echo "🔑 Loading environment variables from .env"
    else
        echo "⚠️ No .env file found. Using config.yaml settings."
    fi
    
    # Run with docker-compose
    docker-compose up --build
    
else
    echo "🔧 Using docker run..."
    
    # Build image
    echo "🏗️ Building Docker image..."
    docker build -t reolink-processor .
    
    # Run container
    echo "▶️ Starting container..."
    docker run -it \
        -v $(pwd)/output:/app/output \
        -v $(pwd)/logs:/app/logs \
        -v $(pwd)/config.yaml:/app/config.yaml \
        --network host \
        reolink-processor
fi

echo "👋 Docker container stopped"
