"""
Reolink Stream Processor

A Python package for connecting to Reolink cameras, processing video streams,
and recording historical segments with motion detection capabilities.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Package-level imports for easy access
from .config.settings import Settings
from .stream.reolink_client import ReolinkClient
from .stream.stream_handler import StreamHandler
from .processing.video_processor import VideoProcessor

__all__ = [
    "Settings",
    "ReolinkClient", 
    "StreamHandler",
    "VideoProcessor"
]