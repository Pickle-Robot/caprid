import cv2
import time
import threading
import numpy as np
from typing import Callable, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import deque
import logging
import os

class StreamHandler:
    """Handle video stream processing and frame management"""
    
    def __init__(self, video_capture: cv2.VideoCapture, buffer_seconds: int = 30):
        self.cap = video_capture
        self.is_running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Frame buffer for segment recording
        self.buffer_seconds = buffer_seconds
        self.frame_buffer = deque(maxlen=buffer_seconds * 30)  # Assuming 30 FPS
        self.buffer_lock = threading.Lock()
        
        # Recording state (simplified - no longer needed for active recordings)
        self.recording_lock = threading.Lock()
        
    def start_stream(self, frame_callback: Optional[Callable] = None):
        """Start processing the video stream"""
        self.is_running = True
        thread = threading.Thread(target=self._stream_loop, args=(frame_callback,))
        thread.daemon = True
        thread.start()
        return thread
    
    def _stream_loop(self, frame_callback: Optional[Callable] = None):
        """Main stream processing loop"""
        while self.is_running:
            ret, frame = self.cap.read()
            
            if not ret:
                self.logger.warning("Failed to read frame from stream")
                time.sleep(0.1)
                continue
            
            current_time = datetime.now()
            
            # Update current frame
            with self.frame_lock:
                self.current_frame = frame.copy()
            
            # Add frame to buffer with timestamp
            with self.buffer_lock:
                self.frame_buffer.append((current_time, frame.copy()))
            
            if frame_callback:
                try:
                    frame_callback(frame)
                except Exception as e:
                    self.logger.error(f"Error in frame callback: {e}")
            
            time.sleep(0.033)  # ~30 FPS
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get the most recent frame"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def stop_stream(self):
        """Stop the stream processing"""
        self.is_running = False
        if self.cap:
            self.cap.release()
