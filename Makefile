.PHONY: install run test clean docker help run-recording dev

help:	## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $1, $2}'

install:	## Install dependencies and setup
	@chmod +x scripts/install.sh
	@./scripts/install.sh

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