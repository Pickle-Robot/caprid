.PHONY: install run capture capture-stable cloud-capture run-recording test docker dev clean help

help:	## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:	## Install dependencies and setup
	@chmod +x scripts/install.sh
	@./scripts/install.sh

run:	## Run the application  
	@chmod +x scripts/run.sh
	@./scripts/run.sh

capture:	## Capture 10 seconds of video
	@echo "📹 Capturing 10 seconds of video from camera..."
	@bash -c "source venv/bin/activate && PYTHONPATH=. python scripts/capture_10_seconds.py"

capture-stable:	## Capture 10 seconds of video using stable script
	@echo "📹 Capturing 10 seconds of video from camera..."
	@bash -c "source venv/bin/activate && PYTHONPATH=. python scripts/capture_10_seconds_stable.py"

cloud-capture:	## Capture 10 seconds of video and upload to GCS
	@echo "☁️  Capturing 10 seconds of video and uploading to Google Cloud Storage..."
	@bash -c "export GOOGLE_CLOUD_PROJECT=pickle-devops-dev && export GCS_BUCKET_NAME=caprid-videos-demo && source venv/bin/activate && PYTHONPATH=. python scripts/capture_10_seconds_cloud.py"

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

start-buffer:  ## Start the rolling buffer service
	sudo systemctl start rolling_buffer.service

stop-buffer:   ## Stop the rolling buffer service
	sudo systemctl stop rolling_buffer.service

status-buffer: ## Show status of the rolling buffer service
	- sudo systemctl status rolling_buffer.service

enable-buffer: ## Enable rolling buffer to start on boot
	sudo systemctl enable rolling_buffer.service

disable-buffer: ## Disable rolling buffer from starting on boot
	sudo systemctl disable rolling_buffer.service

install-buffer-service:  ## Install and reload the rolling buffer systemd service
	chmod +x scripts/run_rolling_buffer.sh
	sudo cp rolling_buffer.service /etc/systemd/system/rolling_buffer.service
	sudo systemctl daemon-reload

extract-clip:  ## Extract a clip from the rolling buffer. Usage: make extract-clip START="2025-07-07T15:00:00" DURATION=10 OUT=output_clip.mp4
    @source venv/bin/activate && PYTHONPATH=. python scripts/extract_clip.py "$(START)" "$(DURATION)" "$(OUT)"