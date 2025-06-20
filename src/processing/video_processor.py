import cv2
import numpy as np
from typing import Optional
import logging

class VideoProcessor:
    """Process video frames for motion detection and basic image operations"""
    
    def __init__(self):
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2()
        self.logger = logging.getLogger(__name__)
        
    def detect_motion(self, frame: np.ndarray, threshold: int = 1000) -> bool:
        """Simple motion detection using background subtraction"""
        try:
            fg_mask = self.background_subtractor.apply(frame)
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                if cv2.contourArea(contour) > threshold:
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Motion detection error: {e}")
            return False
        
    def resize_frame(self, frame: np.ndarray, width: int, height: int) -> np.ndarray:
        """Resize frame to specified dimensions"""
        try:
            return cv2.resize(frame, (width, height))
        except Exception as e:
            self.logger.error(f"Frame resize error: {e}")
            return frame
    
    def apply_filters(self, frame: np.ndarray, blur: bool = False, 
                     grayscale: bool = False) -> np.ndarray:
        """Apply basic image processing filters"""
        try:
            processed = frame.copy()
            
            if grayscale:
                processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
                processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
            
            if blur:
                processed = cv2.GaussianBlur(processed, (15, 15), 0)
            
            return processed
        except Exception as e:
            self.logger.error(f"Filter application error: {e}")
            return frame
    
    def save_frame(self, frame: np.ndarray, filename: str) -> bool:
        """Save frame to disk"""
        try:
            return cv2.imwrite(filename, frame)
        except Exception as e:
            self.logger.error(f"Error saving frame: {e}")
            return False
    
    def get_frame_info(self, frame: np.ndarray) -> dict:
        """Get basic information about a frame"""
        try:
            return {
                'shape': frame.shape,
                'dtype': str(frame.dtype),
                'size_mb': frame.nbytes / (1024 * 1024),
                'channels': frame.shape[2] if len(frame.shape) == 3 else 1
            }
        except Exception as e:
            self.logger.error(f"Error getting frame info: {e}")
            return {}