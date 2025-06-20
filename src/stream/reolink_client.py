import requests
import cv2
import numpy as np
from typing import Optional, Generator
import logging

class ReolinkClient:
    """Client for connecting to Reolink cameras and handling video streams"""
    
    def __init__(self, host: str, username: str, password: str, port: int = 80):
        self.logger = logging.getLogger(__name__)
        self.host = self._normalize_host(host)
        self.username = username
        self.password = password
        self.port = port
        self.token = None
        
    def _normalize_host(self, host: str) -> str:
        """Normalize host to handle various hostname formats"""
        # Remove protocol if present
        if host.startswith('http://'):
            host = host[7:]
        elif host.startswith('https://'):
            host = host[8:]
        
        # Remove trailing slash
        host = host.rstrip('/')
        
        # Remove port if present in hostname
        if ':' in host and not host.count(':') > 1:  # IPv4 with port, not IPv6
            host = host.split(':')[0]
        
        self.logger.info(f"Normalized host: {host}")
        return host
        
    def _resolve_host(self) -> str:
        """Resolve hostname to IP address if needed"""
        import socket
        try:
            # Try to resolve hostname to IP
            ip_address = socket.gethostbyname(self.host)
            if ip_address != self.host:
                self.logger.info(f"Resolved hostname {self.host} to IP {ip_address}")
            return ip_address
        except socket.gaierror as e:
            self.logger.warning(f"Could not resolve hostname {self.host}: {e}")
            # Return original host, might still work
            return self.host
        
    def authenticate(self) -> bool:
        """Authenticate with the Reolink camera"""
        # Resolve hostname if needed
        resolved_host = self._resolve_host()
        
        # Use HTTP explicitly (not HTTPS)
        auth_url = f"http://{resolved_host}:{self.port}/cgi-bin/api.cgi"
        
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
            self.logger.info(f"Attempting authentication to: {auth_url}")
            
            # Disable SSL warnings for self-signed certificates
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.post(auth_url, json=[auth_data], timeout=10, verify=False)
            if response.status_code == 200:
                result = response.json()
                if result[0]["code"] == 0:
                    self.token = result[0]["value"]["Token"]["name"]
                    self.logger.info("Successfully authenticated with Reolink camera")
                    return True
                else:
                    self.logger.error(f"Authentication failed with code: {result[0]['code']}")
            
            self.logger.error(f"Failed to authenticate with Reolink camera. Status: {response.status_code}")
            return False
            
        except requests.exceptions.SSLError as e:
            self.logger.error(f"SSL Error: {e}")
            # Try HTTPS if HTTP fails with SSL error
            return self._try_https_authentication(resolved_host)
            
        except requests.RequestException as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def _try_https_authentication(self, resolved_host: str) -> bool:
        """Try HTTPS authentication if HTTP fails"""
        self.logger.info("Trying HTTPS authentication...")
        auth_url = f"https://{resolved_host}:{self.port}/cgi-bin/api.cgi"
        
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
                result = response.json()
                if result[0]["code"] == 0:
                    self.token = result[0]["value"]["Token"]["name"]
                    self.logger.info("Successfully authenticated with Reolink camera via HTTPS")
                    return True
            
            self.logger.error(f"HTTPS authentication also failed. Status: {response.status_code}")
            return False
            
        except Exception as e:
            self.logger.error(f"HTTPS authentication error: {e}")
            return False
    
    def get_stream_url(self, channel: int = 0, stream_type: str = "main") -> str:
        """Get the RTSP stream URL"""
        # Use resolved host for RTSP URL
        resolved_host = self._resolve_host()
        # Reolink RTSP URL format
        return f"rtsp://{self.username}:{self.password}@{resolved_host}:554/h264Preview_{channel+1:02d}_{stream_type}"
    
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

