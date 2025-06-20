import requests
import cv2
import numpy as np
from typing import Optional, Generator
import logging
import urllib3
from requests.auth import HTTPBasicAuth

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ReolinkClient:
    """Client for connecting to Reolink cameras and handling video streams"""
    
    def __init__(self, host: str, username: str, password: str, port: int = 80):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.token = None
        self.auth_method = None
        self.logger = logging.getLogger(__name__)
        
    def authenticate(self) -> bool:
        """Authenticate with the Reolink camera using the best available method"""
        
        # Method 1: Try HTTP Basic Auth (works with your camera!)
        if self._try_basic_auth():
            return True
            
        # Method 2: Try RTSP direct (fallback, also works with your camera!)
        if self._try_rtsp_auth():
            return True
            
        # Method 3: Try original API method (if others fail)
        if self._try_api_auth():
            return True
        
        self.logger.error("All authentication methods failed")
        return False
    
    def _try_basic_auth(self) -> bool:
        """Try HTTP Basic Authentication"""
        self.logger.info("Trying HTTP Basic Authentication...")
        
        # Test different ports for Basic Auth
        test_ports = [self.port, 80, 443]
        protocols = ['https', 'http'] if self.port == 443 else ['http', 'https']
        
        for protocol in protocols:
            for port in test_ports:
                try:
                    url = f"{protocol}://{self.host}:{port}/"
                    self.logger.info(f"Testing Basic Auth: {url}")
                    
                    response = requests.get(url, auth=HTTPBasicAuth(self.username, self.password), 
                                          timeout=10, verify=False)
                    
                    if response.status_code == 200:
                        self.logger.info(f"✅ HTTP Basic Auth successful via {protocol}:{port}")
                        self.auth_method = "basic"
                        self.port = port  # Update port if different
                        return True
                    elif response.status_code == 401:
                        self.logger.warning(f"❌ Basic Auth failed: Invalid credentials")
                    else:
                        self.logger.debug(f"Basic Auth {protocol}:{port} returned: {response.status_code}")
                        
                except Exception as e:
                    self.logger.debug(f"Basic Auth {protocol}:{port} error: {e}")
        
        return False
    
    def _try_rtsp_auth(self) -> bool:
        """Test RTSP authentication as a fallback"""
        self.logger.info("Testing RTSP authentication as fallback...")
        
        # Test if we can open an RTSP stream
        test_cap = self.get_video_stream(channel=0)
        if test_cap:
            test_cap.release()
            self.logger.info("✅ RTSP authentication successful")
            self.auth_method = "rtsp"
            return True
        
        return False
    
    def _try_api_auth(self) -> bool:
        """Try original API authentication method"""
        self.logger.info("Trying original API authentication...")
        
        auth_url = f"https://{self.host}:{self.port}/cgi-bin/api.cgi"
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
            response = requests.post(auth_url, json=[auth_data], timeout=10, verify=False)
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result and len(result) > 0 and result[0].get("code") == 0:
                        token_data = result[0].get("value", {}).get("Token")
                        if token_data and "name" in token_data:
                            self.token = token_data["name"]
                            self.logger.info("✅ API authentication successful")
                            self.auth_method = "api"
                            return True
                except ValueError:
                    pass
        except Exception as e:
            self.logger.debug(f"API auth failed: {e}")
        
        return False
    
    def get_stream_url(self, channel: int = 0, stream_type: str = "main") -> str:
        """Get the RTSP stream URL"""
        return f"rtsp://{self.username}:{self.password}@{self.host}:554/h264Preview_{channel+1:02d}_{stream_type}"
    
    def get_video_stream(self, channel: int = 0) -> Optional[cv2.VideoCapture]:
        """Get OpenCV VideoCapture object for the stream"""
        
        # Known working RTSP URL patterns for your camera type
        stream_urls = [
            f"rtsp://{self.username}:{self.password}@{self.host}:554/h264Preview_{channel+1:02d}_main",
            f"rtsp://{self.username}:{self.password}@{self.host}:554/h264Preview_{channel+1:02d}_sub",
            f"rtsp://{self.username}:{self.password}@{self.host}:554/Preview_{channel+1:02d}_main",
            f"rtsp://{self.username}:{self.password}@{self.host}:554/cam/realmonitor?channel={channel+1}&subtype=0",
            f"rtsp://{self.username}:{self.password}@{self.host}:554/live",
            f"rtsp://{self.username}:{self.password}@{self.host}:554/stream1"
        ]
        
        for i, stream_url in enumerate(stream_urls, 1):
            self.logger.info(f"Trying RTSP URL format {i}/{len(stream_urls)}")
            
            try:
                cap = cv2.VideoCapture(stream_url)
                
                # Optimize settings to reduce h264 errors
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer
                cap.set(cv2.CAP_PROP_FPS, 15)        # Limit FPS to reduce errors
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('H','2','6','4'))
                
                # Try to set transport protocol to TCP (more reliable than UDP)
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
                
                if cap.isOpened():
                    # Test if we can actually read a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        self.logger.info(f"✅ RTSP stream opened successfully with format {i}")
                        self.logger.info(f"📺 Frame dimensions: {frame.shape}")
                        
                        # Reset to beginning
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