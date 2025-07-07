#!/bin/bash
cd "$(dirname "$0")/.."
VENV_PYTHON="$(pwd)/venv/bin/python3"
PYTHONPATH=. "$VENV_PYTHON" -m src.processing.rolling_buffer