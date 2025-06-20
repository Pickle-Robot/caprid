import requests
import cv2
import numpy as np
from typing import Optional, Generator
import logging

class ReolinkClient:
    """Client for connecting to Reolink cameras and handling video streams"""
    
    def __init__(self, host: str, username: str, password: str, port: int = 80):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.token = None
        self.logger = logging.getLogger(__name__)
        
    def authenticate(self) -> bool:
        """Authenticate with the Reolink camera"""
        auth_url = f"http://{self.host}:{self.port}/cgi-bin/api.cgi"
        
        auth_data = {
            "cmd": "Login",
            "action": 0,
            "param": {
                "User": {
                    "userName": self.username,
                    "password": self.password
                }
            }
        }
        
        try:
            response = requests.post(auth_url, json=[auth_data], timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result[0]["code"] == 0:
                    self.token = result[0]["value"]["Token"]["name"]
                    self.logger.info("Successfully authenticated with Reolink camera")
                    return True
            
            self.logger.error("Failed to authenticate with Reolink camera")
            return False
            
        except requests.RequestException as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def get_stream_url(self, channel: int = 0, stream_type: str = "main") -> str:
        """Get the RTSP stream URL"""
        # Reolink RTSP URL format
        return f"rtsp://{self.username}:{self.password}@{self.host}:554/h264Preview_{channel+1:02d}_{stream_type}"
    
    def get_video_stream(self, channel: int = 0) -> Optional[cv2.VideoCapture]:
        """Get OpenCV VideoCapture object for the stream"""
        stream_url = self.get_stream_url(channel)
        cap = cv2.VideoCapture(stream_url)
        
        if cap.isOpened():
            self.logger.info(f"Successfully opened stream: {stream_url}")
            return cap
        else:
            self.logger.error(f"Failed to open stream: {stream_url}")
            return None