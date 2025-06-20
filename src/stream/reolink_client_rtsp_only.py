"""
Alternative Reolink client that works with RTSP only (no API authentication needed).
Use this if API authentication fails but RTSP stream works.
"""

import cv2
import numpy as np
from typing import Optional
import logging

class ReolinkRTSPClient:
    """Simplified Reolink client that uses RTSP streams directly"""
    
    def __init__(self, host: str, username: str, password: str, rtsp_port: int = 554):
        self.host = host
        self.username = username
        self.password = password
        self.rtsp_port = rtsp_port
        self.logger = logging.getLogger(__name__)
        
    def authenticate(self) -> bool:
        """Test RTSP authentication by trying to connect to stream"""
        self.logger.info("Testing RTSP authentication...")
        
        # Try to open any stream to verify credentials
        test_cap = self.get_video_stream(channel=0)
        if test_cap:
            test_cap.release()
            self.logger.info("RTSP authentication successful")
            return True
        else:
            self.logger.error("RTSP authentication failed")
            return False
    
    def get_stream_url(self, channel: int = 0, stream_type: str = "main") -> str:
        """Get the RTSP stream URL - tries multiple formats"""
        # Return the first URL format (will try others in get_video_stream)
        return f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/h264Preview_{channel+1:02d}_{stream_type}"
    
    def get_video_stream(self, channel: int = 0) -> Optional[cv2.VideoCapture]:
        """Get OpenCV VideoCapture object - tries multiple RTSP URL formats"""
        
        # Common Reolink RTSP URL patterns
        stream_urls = [
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/h264Preview_{channel+1:02d}_main",
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/h264Preview_{channel+1:02d}_sub",
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/Preview_{channel+1:02d}_main",
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/Preview_{channel+1:02d}_sub",
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/cam/realmonitor?channel={channel+1}&subtype=0",
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/cam/realmonitor?channel={channel+1}&subtype=1",
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/live",
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/stream1",
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/stream2",
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/{channel+1}{1 if stream_type == 'main' else 2}",
            f"rtsp://{self.username}:{self.password}@{self.host}:{self.rtsp_port}/{channel+11}"
        ]
        
        for i, stream_url in enumerate(stream_urls, 1):
            self.logger.info(f"Trying RTSP URL format {i}/{len(stream_urls)}")
            self.logger.debug(f"URL: rtsp://{self.username}:***@{self.host}:{self.rtsp_port}/...")
            
            try:
                cap = cv2.VideoCapture(stream_url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for real-time
                
                if cap.isOpened():
                    # Test if we can actually read a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        self.logger.info(f"✅ RTSP stream opened successfully with format {i}")
                        self.logger.info(f"📺 Frame dimensions: {frame.shape}")
                        
                        # Reset to beginning and return
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        return cap
                    else:
                        self.logger.warning(f"❌ Format {i}: Stream opened but couldn't read frame")
                        cap.release()
                else:
                    self.logger.warning(f"❌ Format {i}: Failed to open stream")
                    
            except Exception as e:
                self.logger.warning(f"❌ Format {i}: Exception - {e}")
        
        self.logger.error("❌ Failed to open RTSP stream with any URL format")
        return None
    
    def test_all_streams(self) -> dict:
        """Test all possible stream combinations and return working ones"""
        working_streams = {}
        
        for channel in range(4):  # Test channels 0-3
            for stream_type in ["main", "sub"]:
                self.logger.info(f"Testing channel {channel}, stream {stream_type}")
                cap = self.get_video_stream(channel)
                if cap:
                    working_streams[f"channel_{channel}_{stream_type}"] = self.get_stream_url(channel, stream_type)
                    cap.release()
        
        return working_streams