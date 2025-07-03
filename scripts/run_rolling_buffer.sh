#!/bin/bash
cd "$(dirname "$0")/.."
source venv/bin/activate
PYTHONPATH=. python -m src.processing.rolling_buffer