#!/bin/bash
cd "$(dirname "$0")/.."
source venv/bin/activate
PYTHONPATH=. python3 -m src.processing.rolling_buffer