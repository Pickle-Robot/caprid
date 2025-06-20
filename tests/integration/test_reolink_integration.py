"""
Integration tests for Reolink Stream Processor.

These tests require actual hardware or network access and test
the integration between components.
"""

import unittest
import os
import time
from datetime import datetime, timedelta
import tempfile
import shutil

from src.config.settings import Settings
from src.stream.reolink_client import ReolinkClient
from src.stream.stream_handler import StreamHandler
from src.processing.video_processor import VideoProcessor


class TestReolinkIntegration(unittest.TestCase):
    """Integration tests for complete Reolink workflow."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Skip integration tests if no camera configured
        cls.skip_tests = False
        
        try:
            cls.settings = Settings("test_config.yaml")
            cls.config = cls.settings.config
            
            # Check if test camera is configured
            if (not cls.config.get('reolink', {}).get('host') or 
                cls.config['reolink']['host'] == '192.168.1.100'):
                cls.skip_tests = True
                
        except Exception:
            cls.skip_tests = True
        
        # Create temporary directory for test outputs
        cls.temp_dir = tempfile.mkdtemp()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        if hasattr(cls, 'temp_dir'):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def setUp(self):
        """Set up for each test."""
        if self.skip_tests:
            self.skipTest("No test camera configured")
        
        self.client = ReolinkClient(
            host=self.config['reolink']['host'],
            username=self.config['reolink']['username'],
            password=self.config['reolink']['password'],
            port=self.config['reolink']['port']
        )
    
    def test_camera_authentication(self):
        """Test authenticating with real camera."""
        result = self.client.authenticate()
        self.assertTrue(result, "Failed to authenticate with test camera")
        self.assertIsNotNone(self.client.token, "No token received")
    
    def test_video_stream_connection(self):
        """Test connecting to video stream."""
        # Authenticate first
        auth_result = self.client.authenticate()
        self.assertTrue(auth_result, "Authentication failed")
        
        # Get video stream
        cap = self.client.get_video_stream(self.config['reolink']['channel'])
        self.assertIsNotNone(cap, "Failed to get video stream")
        
        try:
            # Test reading a frame
            ret, frame = cap.read()
            self.assertTrue(ret, "Failed to read frame from stream")
            self.assertIsNotNone(frame, "Frame is None")
            self.assertEqual(len(frame.shape), 3, "Frame should have 3 dimensions")
        finally:
            cap.release()
    
    def test_full_streaming_workflow(self):
        """Test complete streaming and processing workflow."""
        # Authenticate and get stream
        auth_result = self.client.authenticate()
        self.assertTrue(auth_result)
        
        cap = self.client.get_video_stream(self.config['reolink']['channel'])
        self.assertIsNotNone(cap)
        
        try:
            # Create stream handler
            stream_handler = StreamHandler(cap, buffer_seconds=30)
            processor = VideoProcessor()
            
            # Start streaming
            stream_thread = stream_handler.start_stream()
            
            # Wait for buffer to populate
            time.sleep(5)
            
            # Test getting current frame
            current_frame = stream_handler.get_current_frame()
            self.assertIsNotNone(current_frame)
            
            # Test motion detection
            has_motion = processor.detect_motion(current_frame)
            self.assertIsInstance(has_motion, bool)
            
            # Test frame processing
            resized_frame = processor.resize_frame(current_frame, 320, 240)
            self.assertEqual(resized_frame.shape, (240, 320, 3))
            
            # Test frame saving
            output_path = os.path.join(self.temp_dir, "test_frame.jpg")
            save_result = processor.save_frame(current_frame, output_path)
            self.assertTrue(save_result)
            self.assertTrue(os.path.exists(output_path))
            
        finally:
            stream_handler.stop_stream()
    
    def test_segment_recording_integration(self):
        """Test recording video segments from live stream."""
        # Authenticate and get stream
        auth_result = self.client.authenticate()
        self.assertTrue(auth_result)
        
        cap = self.client.get_video_stream(self.config['reolink']['channel'])
        self.assertIsNotNone(cap)
        
        try:
            # Create stream handler with larger buffer for testing
            stream_handler = StreamHandler(cap, buffer_seconds=60)
            
            # Start streaming and wait for buffer
            stream_thread = stream_handler.start_stream()
            time.sleep(10)  # Allow buffer to populate
            
            # Record a historical segment
            now = datetime.now()
            start_time = now - timedelta(seconds=5)
            end_time = now
            
            output_path = os.path.join(self.temp_dir, "integration_test_segment.mp4")
            recording_id = stream_handler.start_segment_recording(
                start_time, end_time, output_path
            )
            
            self.assertIsNotNone(recording_id)
            
            # Wait a moment for recording to complete
            time.sleep(2)
            
            # Check that output file was created
            self.assertTrue(os.path.exists(output_path))
            
            # Check file size (should be > 0)
            file_size = os.path.getsize(output_path)
            self.assertGreater(file_size, 0)
            
        finally:
            stream_handler.stop_stream()
    
    def test_multiple_segments_recording(self):
        """Test recording multiple segments simultaneously."""
        # Authenticate and get stream
        auth_result = self.client.authenticate()
        self.assertTrue(auth_result)
        
        cap = self.client.get_video_stream(self.config['reolink']['channel'])
        self.assertIsNotNone(cap)
        
        try:
            stream_handler = StreamHandler(cap, buffer_seconds=60)
            stream_thread = stream_handler.start_stream()
            time.sleep(15)  # Allow buffer to populate
            
            # Record multiple segments
            now = datetime.now()
            timestamps = [
                (now - timedelta(seconds=12), now - timedelta(seconds=10)),
                (now - timedelta(seconds=8), now - timedelta(seconds=6)),
                (now - timedelta(seconds=4), now - timedelta(seconds=2))
            ]
            
            recording_ids = stream_handler.record_segment_from_timestamps(
                timestamps, self.temp_dir
            )
            
            self.assertEqual(len(recording_ids), 3)
            
            # Wait for recordings to complete
            time.sleep(3)
            
            # Check that all files were created
            for i, recording_id in enumerate(recording_ids):
                # Files are named based on timestamps
                files = [f for f in os.listdir(self.temp_dir) if f.endswith('.mp4')]
                self.assertGreaterEqual(len(files), i + 1)
            
        finally:
            stream_handler.stop_stream()


class TestConfigurationIntegration(unittest.TestCase):
    """Test configuration loading and application setup."""
    
    def test_default_configuration_loading(self):
        """Test loading default configuration."""
        settings = Settings()
        config = settings.config
        
        # Check required sections exist
        self.assertIn('reolink', config)
        self.assertIn('stream', config)
        self.assertIn('processing', config)
        
        # Check default values
        self.assertEqual(config['reolink']['port'], 80)
        self.assertEqual(config['stream']['fps'], 15)
        self.assertFalse(config['processing']['save_frames'])
    
    def test_environment_variable_override(self):
        """Test that environment variables override config."""
        # Set environment variable
        os.environ['REOLINK_HOST'] = 'test.example.com'
        
        try:
            settings = Settings()
            config = settings.config
            
            self.assertEqual(config['reolink']['host'], 'test.example.com')
        finally:
            # Clean up
            if 'REOLINK_HOST' in os.environ:
                del os.environ['REOLINK_HOST']


# Test configuration file for integration tests
TEST_CONFIG_YAML = """
# test_config.yaml - Configuration for integration testing

reolink:
  host: "192.168.1.100"  # Update with your test camera IP
  username: "admin"
  password: "password"   # Update with your test camera password
  port: 80
  channel: 0

stream:
  resolution: "HD"
  fps: 15
  timeout: 30

processing:
  save_frames: false
  output_dir: "./test_output"
  enable_motion_detection: true
  motion_threshold: 1000

logging:
  level: "DEBUG"
  file: "test_integration.log"
"""

if __name__ == '__main__':
    # Create test config file if it doesn't exist
    if not os.path.exists('test_config.yaml'):
        with open('test_config.yaml', 'w') as f:
            f.write(TEST_CONFIG_YAML)
        print("Created test_config.yaml - please update with your camera details")
    
    unittest.main()