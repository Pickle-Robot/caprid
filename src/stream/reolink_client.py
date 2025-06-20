import requests
import cv2
import numpy as np
from typing import Optional, Generator
import logging
import urllib3

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
        self.logger = logging.getLogger(__name__)
        
    def authenticate(self) -> bool:
        """Authenticate with the Reolink camera - tries multiple methods"""
        
        # Method 1: Try standard API endpoint
        if self._try_standard_auth():
            return True
            
        # Method 2: Try HTTPS if HTTP failed
        if self._try_https_auth():
            return True
            
        # Method 3: Try alternative ports
        for alt_port in [8000, 443, 9000]:
            if alt_port != self.port:
                self.logger.info(f"Trying alternative port: {alt_port}")
                if self._try_auth_with_port(alt_port):
                    self.port = alt_port  # Update port if successful
                    return True
        
        self.logger.error("All authentication methods failed")
        return False
    
    def _try_standard_auth(self) -> bool:
        """Try standard HTTP authentication"""
        auth_url = f"http://{self.host}:{self.port}/cgi-bin/api.cgi"
        return self._attempt_auth(auth_url, "HTTP")
    
    def _try_https_auth(self) -> bool:
        """Try HTTPS authentication"""
        https_port = 443 if self.port == 80 else self.port
        auth_url = f"https://{self.host}:{https_port}/cgi-bin/api.cgi"
        return self._attempt_auth(auth_url, "HTTPS")
    
    def _try_auth_with_port(self, port: int) -> bool:
        """Try authentication with alternative port"""
        auth_url = f"http://{self.host}:{port}/cgi-bin/api.cgi"
        return self._attempt_auth(auth_url, f"HTTP on port {port}")
    
    def _attempt_auth(self, auth_url: str, method_name: str) -> bool:
        """Attempt authentication with given URL"""
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
            self.logger.info(f"Trying {method_name}: {auth_url}")
            response = requests.post(auth_url, json=[auth_data], timeout=10, verify=False)
            
            if response.status_code == 200:
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                
                if 'application/json' in content_type or response.text.strip().startswith('['):
                    try:
                        result = response.json()
                        if result and len(result) > 0 and result[0].get("code") == 0:
                            self.token = result[0]["value"]["Token"]["name"]
                            self.logger.info(f"Successfully authenticated via {method_name}")
                            return True
                        else:
                            error_code = result[0].get("code") if result and len(result) > 0 else "unknown"
                            self.logger.warning(f"{method_name} auth failed with code: {error_code}")
                    except (ValueError, KeyError, IndexError) as e:
                        self.logger.warning(f"{method_name} JSON parsing failed: {e}")
                else:
                    self.logger.warning(f"{method_name} returned HTML instead of JSON - wrong endpoint")
            else:
                self.logger.warning(f"{method_name} returned status: {response.status_code}")
                
        except requests.exceptions.SSLError as e:
            self.logger.warning(f"{method_name} SSL error: {e}")
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"{method_name} connection error: {e}")
        except requests.exceptions.Timeout:
            self.logger.warning(f"{method_name} timeout")
        except Exception as e:
            self.logger.warning(f"{method_name} failed: {e}")
            
        return False
    
    def get_stream_url(self, channel: int = 0, stream_type: str = "main") -> str:
        """Get the RTSP stream URL"""
        # Reolink RTSP URL format
        return f"rtsp://{self.username}:{self.password}@{self.host}:554/h264Preview_{channel+1:02d}_{stream_type}"
    
    def get_video_stream(self, channel: int = 0) -> Optional[cv2.VideoCapture]:
        """Get OpenCV VideoCapture object for the stream"""
        # Try different RTSP URL formats
        stream_urls = [
            f"rtsp://{self.username}:{self.password}@{self.host}:554/h264Preview_{channel+1:02d}_main",
            f"rtsp://{self.username}:{self.password}@{self.host}:554/Preview_{channel+1:02d}_main",
            f"rtsp://{self.username}:{self.password}@{self.host}:554/cam/realmonitor?channel={channel+1}&subtype=0",
            f"rtsp://{self.username}:{self.password}@{self.host}:554/live"
        ]
        
        for stream_url in stream_urls:
            self.logger.info(f"Trying stream URL: rtsp://{self.username}:***@{self.host}:554/...")
            cap = cv2.VideoCapture(stream_url)
            
            if cap.isOpened():
                # Test if we can actually read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.logger.info(f"Successfully opened stream with URL format")
                    # Reset to beginning
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    return cap
                else:
                    cap.release()
                    self.logger.warning(f"Stream opened but couldn't read frame")
            else:
                self.logger.warning(f"Failed to open stream with this URL format")
        
        self.logger.error("Failed to open video stream with any URL format")
        return None