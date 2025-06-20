.PHONY: install run test clean docker help fix-opencv run-recording dev clean-all

help:	## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:	## Install dependencies and setup (with headless OpenCV)
	@chmod +x scripts/install.sh
	@./scripts/install.sh

fix-opencv:	## Fix OpenCV installation (force headless version)
	@echo "🔧 Fixing OpenCV installation for headless environment..."
	@if [ ! -d "venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@source venv/bin/activate && \
	echo "🧹 Removing existing OpenCV installations..." && \
	pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python 2>/dev/null || true && \
	echo "📦 Installing headless OpenCV..." && \
	pip install opencv-python-headless>=4.8.0 && \
	echo "🔍 Verifying installation..." && \
	python -c "import cv2; print(f'✅ OpenCV version: {cv2.__version__}'); print('✅ Headless OpenCV installed successfully')" && \
	echo "✅ OpenCV fix complete!"

run:	## Run the application  
	@chmod +x scripts/run.sh
	@./scripts/run.sh

run-recording:	## Run with recording examples
	@chmod +x scripts/run_with_recording.sh
	@./scripts/run_with_recording.sh

test:	## Run tests
	@chmod +x scripts/test.sh
	@./scripts/test.sh

docker:	## Run with Docker
	@chmod +x scripts/docker_run.sh
	@./scripts/docker_run.sh

dev:	## Run in development mode (auto-restart)
	@chmod +x scripts/dev.sh
	@./scripts/dev.sh

clean:	## Clean up generated files
	@echo "🧹 Cleaning up..."
	@rm -rf __pycache__/ .pytest_cache/ *.pyc
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@rm -rf output/segments/* logs/*.log 2>/dev/null || true
	@echo "✅ Cleanup complete"

clean-all:	## Clean everything including venv
	@echo "🧹 Deep cleaning (including virtual environment)..."
	@rm -rf venv/ __pycache__/ .pytest_cache/ *.pyc
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@rm -rf output/ logs/ 2>/dev/null || true
	@echo "✅ Deep cleanup complete - run 'make install' to reinstall"