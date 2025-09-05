"""
Simple storage wrapper for liquidation module
"""

import json
import os
from typing import Any, Optional

class Storage:
    """Simple file-based storage"""
    
    def __init__(self, config: dict):
        self.data_dir = config.get('dataDir', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def save(self, key: str, value: Any):
        """Save data to file"""
        file_path = os.path.join(self.data_dir, f"{key}.json")
        with open(file_path, 'w') as f:
            json.dump(value, f, indent=2)
    
    def load(self, key: str) -> Optional[Any]:
        """Load data from file"""
        file_path = os.path.join(self.data_dir, f"{key}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return None