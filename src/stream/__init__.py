"""
Stream handling module for Reolink cameras.

This module provides classes for connecting to Reolink cameras,
managing video streams, and recording segments.
"""

from .reolink_client import ReolinkClient
from .stream_handler import StreamHandler

__all__ = [
    "ReolinkClient",
    "StreamHandler"
]
