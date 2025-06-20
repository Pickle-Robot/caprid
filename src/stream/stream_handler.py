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
    
    def start_segment_recording(self, start_time: datetime, end_time: datetime, 
                               output_path: str, fps: int = 30) -> str:
        """Start recording a segment from start_time to end_time (end_time must be <= now)"""
        recording_id = f"recording_{int(time.time())}"
        current_time = datetime.now()
        
        # Ensure end_time is not in the future
        if end_time > current_time:
            end_time = current_time
            self.logger.warning(f"End time was in future, adjusted to current time: {end_time}")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Get frame dimensions
        if self.current_frame is not None:
            height, width = self.current_frame.shape[:2]
        else:
            self.logger.error("No current frame available for recording")
            return None
        
        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not writer.isOpened():
            self.logger.error(f"Failed to open video writer for {output_path}")
            return None
        
        # Write frames from buffer
        self._write_historical_frames(writer, start_time, end_time)
        
        # Close the writer since we're only dealing with historical data
        writer.release()
        
        self.logger.info(f"Completed segment recording: {recording_id} -> {output_path}")
        return recording_id
    
    def _write_historical_frames(self, writer: cv2.VideoWriter, start_time: datetime, end_time: datetime):
        """Write frames from the buffer that fall within the time range"""
        with self.buffer_lock:
            for timestamp, frame in self.frame_buffer:
                if start_time <= timestamp <= end_time:
                    writer.write(frame)
    
    def _stop_recording(self, recording_id: str):
        """Stop a specific recording (legacy method - no longer used)"""
        pass
    
    def stop_all_recordings(self):
        """Stop all active recordings (legacy method - no longer used)"""
        pass
    
    def record_segment_from_timestamps(self, timestamps: List[Tuple[datetime, datetime]], 
                                     output_dir: str = "./output/segments") -> List[str]:
        """Record multiple segments based on provided timestamp pairs"""
        recording_ids = []
        
        for i, (start_time, end_time) in enumerate(timestamps):
            output_filename = f"segment_{start_time.strftime('%Y%m%d_%H%M%S')}_{end_time.strftime('%H%M%S')}.mp4"
            output_path = os.path.join(output_dir, output_filename)
            
            recording_id = self.start_segment_recording(start_time, end_time, output_path)
            if recording_id:
                recording_ids.append(recording_id)
        
        return recording_ids
    
    def stop_stream(self):
        """Stop the stream processing"""
        self.is_running = False
        if self.cap:
            self.cap.release()
