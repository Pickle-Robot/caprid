import yaml
import os
from typing import Dict, Any

class Settings:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration if file doesn't exist"""
        return {
            'reolink': {
                'host': os.getenv('REOLINK_HOST', '192.168.1.100'),
                'username': os.getenv('REOLINK_USER', 'admin'),
                'password': os.getenv('REOLINK_PASS', ''),
                'port': int(os.getenv('REOLINK_PORT', 80)),
                'channel': int(os.getenv('REOLINK_CHANNEL', 0))
            },
            'stream': {
                'resolution': 'HD',  # HD, FHD, 4K
                'fps': 15,
                'timeout': 30
            },
            'processing': {
                'save_frames': False,
                'output_dir': './output',
                'enable_motion_detection': False,
                'segment_recording': {
                    'enabled': True,
                    'format': 'mp4',
                    'fps': 30,
                    'quality': 'high'
                }
            }
        }