import cv2
import numpy as np
from typing import Optional, List, Tuple

class VideoProcessor:
    """Process video frames for basic computer vision tasks"""
    
    def __init__(self):
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2()
        
    def detect_motion(self, frame: np.ndarray, threshold: int = 1000) -> bool:
        """Simple motion detection using background subtraction"""
        fg_mask = self.background_subtractor.apply(frame)
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            if cv2.contourArea(contour) > threshold:
                return True
        return False
        
    def resize_frame(self, frame: np.ndarray, width: int, height: int) -> np.ndarray:
        """Resize frame to specified dimensions"""
        return cv2.resize(frame, (width, height))
    
    def apply_filters(self, frame: np.ndarray, blur: bool = False, 
                     grayscale: bool = False) -> np.ndarray:
        """Apply basic image processing filters"""
        processed = frame.copy()
        
        if grayscale:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        
        if blur:
            processed = cv2.GaussianBlur(processed, (15, 15), 0)
        
        return processed
    
    def save_frame(self, frame: np.ndarray, filename: str) -> bool:
        """Save frame to disk"""
        try:
            return cv2.imwrite(filename, frame)
        except Exception as e:
            print(f"Error saving frame: {e}")
            return False
