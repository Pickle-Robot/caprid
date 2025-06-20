"""
Unit tests for video processing components.
"""

import unittest
import numpy as np
import cv2
import tempfile
import os

from src.processing.video_processor import VideoProcessor


class TestVideoProcessor(unittest.TestCase):
    """Test cases for VideoProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = VideoProcessor()
        
        # Create test frames
        self.test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        self.static_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_processor_initialization(self):
        """Test VideoProcessor initializes correctly."""
        self.assertIsNotNone(self.processor.background_subtractor)
    
    def test_motion_detection_no_motion(self):
        """Test motion detection with static frames."""
        # Feed several static frames to establish background
        for _ in range(10):
            self.processor.detect_motion(self.static_frame)
        
        # Test with same static frame - should detect no motion
        has_motion = self.processor.detect_motion(self.static_frame)
        self.assertFalse(has_motion)
    
    def test_motion_detection_with_motion(self):
        """Test motion detection with changing frames."""
        # Establish background with static frames
        for _ in range(10):
            self.processor.detect_motion(self.static_frame)
        
        # Create frame with significant change
        motion_frame = self.static_frame.copy()
        motion_frame[100:200, 100:200] = 255  # White square
        
        has_motion = self.processor.detect_motion(motion_frame, threshold=500)
        self.assertTrue(has_motion)
    
    def test_resize_frame(self):
        """Test frame resizing."""
        resized = self.processor.resize_frame(self.test_frame, 320, 240)
        
        self.assertEqual(resized.shape, (240, 320, 3))
        self.assertEqual(resized.dtype, self.test_frame.dtype)
    
    def test_apply_filters_grayscale(self):
        """Test grayscale filter."""
        filtered = self.processor.apply_filters(self.test_frame, grayscale=True)
        
        # Should still be 3-channel but grayscale
        self.assertEqual(filtered.shape, self.test_frame.shape)
        
        # Check if it's actually grayscale (all channels should be equal)
        self.assertTrue(np.array_equal(filtered[:,:,0], filtered[:,:,1]))
        self.assertTrue(np.array_equal(filtered[:,:,1], filtered[:,:,2]))
    
    def test_apply_filters_blur(self):
        """Test blur filter."""
        filtered = self.processor.apply_filters(self.test_frame, blur=True)
        
        self.assertEqual(filtered.shape, self.test_frame.shape)
        # Blurred image should be different from original
        self.assertFalse(np.array_equal(filtered, self.test_frame))
    
    def test_apply_filters_combined(self):
        """Test applying multiple filters."""
        filtered = self.processor.apply_filters(
            self.test_frame, 
            blur=True, 
            grayscale=True
        )
        
        self.assertEqual(filtered.shape, self.test_frame.shape)
    
    def test_save_frame_success(self):
        """Test successful frame saving."""
        output_path = os.path.join(self.temp_dir, "test_frame.jpg")
        
        result = self.processor.save_frame(self.test_frame, output_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
    
    def test_save_frame_invalid_path(self):
        """Test frame saving with invalid path."""
        invalid_path = "/invalid/path/frame.jpg"
        
        result = self.processor.save_frame(self.test_frame, invalid_path)
        
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()