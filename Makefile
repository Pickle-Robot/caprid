.PHONY: install run capture-cloud run-recording test docker dev clean help buffer-start buffer-stop buffer-restart buffer-status buffer-enable buffer-disable buffer-install-service buffer-capture

help:	## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:	## Install dependencies and setup
	@chmod +x scripts/install.sh
	@./scripts/install.sh
	@make buffer-install-service

run:	## Run the application  
	@chmod +x scripts/run.sh
	@./scripts/run.sh

capture-cloud:	## Capture 10 seconds of video and upload to GCS
	@echo "☁️  Capturing 10 seconds of video and uploading to Google Cloud Storage..."
	@bash -c ' \
	export GOOGLE_CLOUD_PROJECT=pickle-terraform-dev && \
	export GCS_BUCKET_NAME=customer1-videos && \
	source venv/bin/activate && \
	PYTHONPATH=./src python scripts/capture_10_seconds_cloud.py \
	'

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
	@rm -rf *.egg-info/ src/*.egg-info/ 2>/dev/null || true
	@echo "✅ Cleanup complete"

buffer-start:  ## Start the rolling buffer service
	sudo systemctl start rolling_buffer.service

buffer-stop:   ## Stop the rolling buffer service
	sudo systemctl stop rolling_buffer.service

buffer-restart: ## Restart the rolling buffer service
	@echo "🔄 Restarting rolling buffer service..."
	@sudo systemctl restart rolling_buffer.service
	@echo "✅ Service restarted"

buffer-status: ## Show status of the rolling buffer service
	- sudo systemctl status rolling_buffer.service

buffer-enable: ## Enable rolling buffer to start on boot
	sudo systemctl enable rolling_buffer.service

buffer-disable: ## Disable rolling buffer from starting on boot
	sudo systemctl disable rolling_buffer.service

buffer-install-service:  ## Install and reload the rolling buffer systemd service
	chmod +x scripts/run_rolling_buffer.sh
	sudo cp rolling_buffer.service /etc/systemd/system/rolling_buffer.service
	sudo systemctl daemon-reload

buffer-capture:  ## Extract a clip from the rolling buffer and upload to GCS. Usage: make buffer-capture 2025-07-07T15:00:00 [GCS_BUCKET_NAME=bucket] [GOOGLE_CLOUD_PROJECT=project]
	@bash -c ' \
	EVENT_TIME="$(word 2,$(MAKECMDGOALS))"; \
	if [ -z "$$EVENT_TIME" ]; then echo "Usage: make buffer-capture <EVENT_TIME:YYYY-MM-DDTHH:MM:SS> [GCS_BUCKET_NAME=bucket] [GOOGLE_CLOUD_PROJECT=project]"; exit 1; fi; \
	export GOOGLE_CLOUD_PROJECT=$${GOOGLE_CLOUD_PROJECT:-pickle-devops-dev} && \
	export GCS_BUCKET_NAME=$${GCS_BUCKET_NAME:-caprid-videos-demo} && \
	source venv/bin/activate && \
	PYTHONPATH=./src python src/extract_clip.py "$$EVENT_TIME" \
'

%:
	@: