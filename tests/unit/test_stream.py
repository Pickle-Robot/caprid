"""
Unit tests for stream handling components.

Tests the stream handler and related functionality in isolation
using mocks and fixtures.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import cv2
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os

from src.stream.stream_handler import StreamHandler
from src.stream.reolink_client import ReolinkClient


class TestStreamHandler(unittest.TestCase):
    """Test cases for StreamHandler class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_cap = Mock(spec=cv2.VideoCapture)
        self.mock_cap.isOpened.return_value = True
        self.mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        
        self.stream_handler = StreamHandler(self.mock_cap, buffer_seconds=10)
        
        # Create temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after each test method."""
        self.stream_handler.stop_stream()
        
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_stream_handler_initialization(self):
        """Test StreamHandler initializes correctly."""
        self.assertFalse(self.stream_handler.is_running)
        self.assertIsNone(self.stream_handler.current_frame)
        self.assertEqual(len(self.stream_handler.frame_buffer), 0)
    
    def test_start_stream(self):
        """Test starting the video stream."""
        thread = self.stream_handler.start_stream()
        self.assertTrue(self.stream_handler.is_running)
        self.assertIsNotNone(thread)
        
        # Wait a bit for thread to process frames
        import time
        time.sleep(0.1)
        
        # Check that frames are being captured
        self.assertIsNotNone(self.stream_handler.get_current_frame())
    
    def test_get_current_frame(self):
        """Test getting the current frame."""
        # Before starting stream
        self.assertIsNone(self.stream_handler.get_current_frame())
        
        # After starting stream
        self.stream_handler.start_stream()
        import time
        time.sleep(0.1)  # Allow time for frame capture
        
        frame = self.stream_handler.get_current_frame()
        self.assertIsNotNone(frame)
        self.assertEqual(frame.shape, (480, 640, 3))
    
    @patch('cv2.VideoWriter')
    def test_segment_recording_historical(self, mock_video_writer):
        """Test recording a historical segment."""
        mock_writer = Mock()
        mock_video_writer.return_value = mock_writer
        mock_writer.isOpened.return_value = True
        
        # Start stream to populate buffer
        self.stream_handler.start_stream()
        import time
        time.sleep(0.2)  # Allow buffer to populate
        
        # Record a historical segment
        now = datetime.now()
        start_time = now - timedelta(seconds=5)
        end_time = now - timedelta(seconds=2)
        
        output_path = os.path.join(self.temp_dir, "test_segment.mp4")
        recording_id = self.stream_handler.start_segment_recording(
            start_time, end_time, output_path
        )
        
        self.assertIsNotNone(recording_id)
        mock_video_writer.assert_called_once()
        mock_writer.write.assert_called()
        mock_writer.release.assert_called_once()
    
    @patch('cv2.VideoWriter')
    def test_segment_recording_mixed(self, mock_video_writer):
        """Test recording a mixed segment (past to present)."""
        mock_writer = Mock()
        mock_video_writer.return_value = mock_writer
        mock_writer.isOpened.return_value = True
        
        # Start stream to populate buffer
        self.stream_handler.start_stream()
        import time
        time.sleep(0.2)
        
        # Record from past to now
        now = datetime.now()
        start_time = now - timedelta(seconds=3)
        end_time = now  # Current time
        
        output_path = os.path.join(self.temp_dir, "test_mixed.mp4")
        recording_id = self.stream_handler.start_segment_recording(
            start_time, end_time, output_path
        )
        
        self.assertIsNotNone(recording_id)
        mock_video_writer.assert_called_once()
    
    def test_future_end_time_adjustment(self):
        """Test that future end times get adjusted to current time."""
        with patch('cv2.VideoWriter') as mock_video_writer:
            mock_writer = Mock()
            mock_video_writer.return_value = mock_writer
            mock_writer.isOpened.return_value = True
            
            self.stream_handler.start_stream()
            import time
            time.sleep(0.1)
            
            # Try to record with future end time
            now = datetime.now()
            start_time = now - timedelta(seconds=5)
            end_time = now + timedelta(seconds=10)  # Future
            
            output_path = os.path.join(self.temp_dir, "test_future.mp4")
            
            with patch.object(self.stream_handler, 'logger') as mock_logger:
                recording_id = self.stream_handler.start_segment_recording(
                    start_time, end_time, output_path
                )
                
                # Should log a warning about adjusting end time
                mock_logger.warning.assert_called()
    
    def test_record_multiple_segments(self):
        """Test recording multiple segments from timestamp list."""
        with patch('cv2.VideoWriter') as mock_video_writer:
            mock_writer = Mock()
            mock_video_writer.return_value = mock_writer
            mock_writer.isOpened.return_value = True
            
            self.stream_handler.start_stream()
            import time
            time.sleep(0.2)
            
            now = datetime.now()
            timestamps = [
                (now - timedelta(seconds=10), now - timedelta(seconds=8)),
                (now - timedelta(seconds=6), now - timedelta(seconds=4)),
                (now - timedelta(seconds=2), now)
            ]
            
            recording_ids = self.stream_handler.record_segment_from_timestamps(
                timestamps, self.temp_dir
            )
            
            self.assertEqual(len(recording_ids), 3)
            self.assertEqual(mock_video_writer.call_count, 3)


class TestReolinkClient(unittest.TestCase):
    """Test cases for ReolinkClient class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = ReolinkClient(
            host="192.168.1.100",
            username="admin", 
            password="password123",
            port=80
        )
    
    def test_client_initialization(self):
        """Test ReolinkClient initializes correctly."""
        self.assertEqual(self.client.host, "192.168.1.100")
        self.assertEqual(self.client.username, "admin")
        self.assertEqual(self.client.password, "password123")
        self.assertEqual(self.client.port, 80)
        self.assertIsNone(self.client.token)
    
    @patch('requests.post')
    def test_authentication_success(self, mock_post):
        """Test successful authentication."""
        # Mock successful authentication response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            "code": 0,
            "value": {"Token": {"name": "test_token_123"}}
        }]
        mock_post.return_value = mock_response
        
        result = self.client.authenticate()
        
        self.assertTrue(result)
        self.assertEqual(self.client.token, "test_token_123")
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_authentication_failure(self, mock_post):
        """Test failed authentication."""
        # Mock failed authentication response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"code": 1}]  # Error code
        mock_post.return_value = mock_response
        
        result = self.client.authenticate()
        
        self.assertFalse(result)
        self.assertIsNone(self.client.token)
    
    @patch('requests.post')
    def test_authentication_network_error(self, mock_post):
        """Test authentication with network error."""
        mock_post.side_effect = Exception("Network error")
        
        result = self.client.authenticate()
        
        self.assertFalse(result)
        self.assertIsNone(self.client.token)
    
    def test_get_stream_url(self):
        """Test RTSP stream URL generation."""
        url = self.client.get_stream_url(channel=0, stream_type="main")
        expected = "rtsp://admin:password123@192.168.1.100:554/h264Preview_01_main"
        self.assertEqual(url, expected)
        
        # Test different channel
        url2 = self.client.get_stream_url(channel=1, stream_type="sub")
        expected2 = "rtsp://admin:password123@192.168.1.100:554/h264Preview_02_sub"
        self.assertEqual(url2, expected2)
    
    @patch('cv2.VideoCapture')
    def test_get_video_stream_success(self, mock_video_capture):
        """Test successful video stream creation."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_video_capture.return_value = mock_cap
        
        result = self.client.get_video_stream(channel=0)
        
        self.assertIsNotNone(result)
        self.assertEqual(result, mock_cap)
    
    @patch('cv2.VideoCapture')
    def test_get_video_stream_failure(self, mock_video_capture):
        """Test failed video stream creation."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        
        result = self.client.get_video_stream(channel=0)
        
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()