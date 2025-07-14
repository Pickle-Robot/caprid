#!/bin/bash
cd "$(dirname "$0")/.."
VENV_PYTHON="$(pwd)/venv/bin/python3"
PYTHONPATH="$(pwd)/src" "$VENV_PYTHON" -m processing.rolling_buffer