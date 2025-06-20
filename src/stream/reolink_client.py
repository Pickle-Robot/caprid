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
        
        # Try different authentication formats
        auth_formats = [
            # Standard Reolink format
            {
                "cmd": "Login",
                "action": 0,
                "param": {
                    "User": {
                        "userName": self.username,
                        "password": self.password
                    }
                }
            },
            # Alternative format 1
            {
                "cmd": "Login",
                "param": {
                    "User": {
                        "userName": self.username,
                        "password": self.password
                    }
                }
            },
            # Alternative format 2
            {
                "cmd": "Login",
                "param": {
                    "userName": self.username,
                    "password": self.password
                }
            }
        ]
        
        for i, auth_data in enumerate(auth_formats, 1):
            try:
                self.logger.info(f"Trying {method_name} (format {i}): {auth_url}")
                response = requests.post(auth_url, json=[auth_data], timeout=10, verify=False)
                
                if response.status_code == 200:
                    # Check content type
                    content_type = response.headers.get('content-type', '').lower()
                    
                    if 'application/json' in content_type or response.text.strip().startswith('['):
                        try:
                            result = response.json()
                            if result and len(result) > 0:
                                code = result[0].get("code")
                                rsp_code = result[0].get("error", {}).get("rspCode") if result[0].get("error") else None
                                
                                if code == 0:
                                    # Success
                                    token_data = result[0].get("value", {}).get("Token")
                                    if token_data and "name" in token_data:
                                        self.token = token_data["name"]
                                        self.logger.info(f"Successfully authenticated via {method_name} (format {i})")
                                        return True
                                    else:
                                        self.logger.info(f"Login successful via {method_name} but no token received")
                                        return True
                                elif rsp_code == -6:
                                    # Camera requires session-based auth
                                    self.logger.info(f"{method_name} requires session-based authentication")
                                    return self._try_session_auth(auth_url, method_name)
                                else:
                                    self.logger.warning(f"{method_name} format {i} failed with code: {code}")
                        except (ValueError, KeyError, IndexError) as e:
                            self.logger.warning(f"{method_name} format {i} JSON parsing failed: {e}")
                    else:
                        self.logger.warning(f"{method_name} format {i} returned HTML instead of JSON")
                else:
                    self.logger.warning(f"{method_name} format {i} returned status: {response.status_code}")
                    
            except requests.exceptions.SSLError as e:
                self.logger.warning(f"{method_name} format {i} SSL error: {e}")
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"{method_name} format {i} connection error: {e}")
            except requests.exceptions.Timeout:
                self.logger.warning(f"{method_name} format {i} timeout")
            except Exception as e:
                self.logger.warning(f"{method_name} format {i} failed: {e}")
                
        return False
    
    def _try_session_auth(self, auth_url: str, method_name: str) -> bool:
        """Try session-based authentication"""
        self.logger.info(f"Attempting session-based authentication for {method_name}")
        
        session = requests.Session()
        
        try:
            # Step 1: Initialize session (optional, some cameras need this)
            init_data = {"cmd": "GetDevInfo", "action": 0}
            session.post(auth_url, json=[init_data], timeout=10, verify=False)
            
            # Step 2: Login with session
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
            
            response = session.post(auth_url, json=[auth_data], timeout=10, verify=False)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result and len(result) > 0 and result[0].get("code") == 0:
                        token_data = result[0].get("value", {}).get("Token")
                        if token_data and "name" in token_data:
                            self.token = token_data["name"]
                            self.logger.info(f"Session-based authentication successful for {method_name}")
                            return True
                        else:
                            self.logger.info(f"Session-based login successful for {method_name} (no token)")
                            return True
                except (ValueError, KeyError, IndexError) as e:
                    self.logger.warning(f"Session auth JSON parsing failed: {e}")
            
        except Exception as e:
            self.logger.warning(f"Session authentication failed: {e}")
        
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