"""
General Helpers
================
Miscellaneous helper functions.
"""

import os
import uuid
import hashlib
import json
from typing import Any, Dict, Optional
from datetime import datetime


def generate_id(prefix: str = '') -> str:
    """Generate a unique ID."""
    unique_id = str(uuid.uuid4().hex[:8])
    return f"{prefix}_{unique_id}" if prefix else unique_id


def generate_object_id() -> str:
    """Generate a MongoDB-style ObjectId."""
    import bson
    return str(bson.ObjectId())


def hash_string(value: str, algorithm: str = 'sha256') -> str:
    """Hash a string."""
    if algorithm == 'md5':
        return hashlib.md5(value.encode()).hexdigest()
    elif algorithm == 'sha1':
        return hashlib.sha1(value.encode()).hexdigest()
    else:
        return hashlib.sha256(value.encode()).hexdigest()


def load_json_file(filepath: str) -> Dict:
    """Load JSON from file."""
    if not os.path.exists(filepath):
        return {}

    with open(filepath, 'r') as f:
        return json.load(f)


def save_json_file(filepath: str, data: Dict) -> None:
    """Save JSON to file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def safe_get(dictionary: Dict, *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary value."""
    result = dictionary
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Merge two dictionaries."""
    result = dict1.copy()
    result.update(dict2)
    return result


def chunks(lst: list, n: int):
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def remove_none_values(d: Dict) -> Dict:
    """Remove None values from dictionary."""
    return {k: v for k, v in d.items() if v is not None}


def convert_keys_to_str(d: Dict) -> Dict:
    """Convert all dictionary keys to strings."""
    if not isinstance(d, dict):
        return d
    return {str(k): convert_keys_to_str(v) if isinstance(v, dict) else v for k, v in d.items()}


def is_running_in_docker() -> bool:
    """Check if running in Docker."""
    return os.path.exists('/.dockerenv')


def get_env_var(name: str, default: Any = None, required: bool = False) -> Any:
    """Get environment variable with optional default."""
    value = os.environ.get(name, default)
    if required and value is None:
        raise ValueError(f"Required environment variable {name} is not set")
    return value


def parse_boolean(value: Any) -> bool:
    """Parse boolean from various input types."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change."""
    if old_value == 0:
        return 0
    return ((new_value - old_value) / old_value) * 100


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp value between min and max."""
    return max(min_value, min(value, max_value))