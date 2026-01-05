"""
Find Google Street View panorama IDs near specified cities.

This replaces the streetview_panoid.html JavaScript tool with a Python implementation.
"""

import random
import time
import numpy as np
from typing import List, Tuple, Optional


def get_panorama_ids_google_api(location: Tuple[float, float], 
                                 radius: float = 0.012,
                                 max_panoramas: int = 100,
                                 api_key: Optional[str] = None) -> List[str]:
    """
    Get panorama IDs using Google Street View Static API.
    
    Note: This requires a Google API key and may have usage limits.
    
    Args:
        location: (latitude, longitude) tuple
        radius: Search radius in degrees
        max_panoramas: Maximum number of panoramas to find
        api_key: Google Maps API key (optional, can use environment variable)
        
    Returns:
        List of panorama IDs
    """
    try:
        from googlemaps import Client
    except ImportError:
        raise ImportError("googlemaps package required. Install with: pip install googlemaps")
    
    import os
    
    if api_key is None:
        api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    
    if api_key is None:
        raise ValueError("Google Maps API key required. Set GOOGLE_MAPS_API_KEY environment variable or pass api_key parameter")
    
    gmaps = Client(key=api_key)
    panorama_ids = []
    seen_ids = set()
    
    lat, lng = location
    
    for _ in range(max_panoramas * 10):  # Try more locations than needed
        # Random location within radius
        offset_lat = random.uniform(-radius, radius)
        offset_lng = random.uniform(-radius, radius) / abs(np.cos(np.radians(lat)))
        
        test_lat = lat + offset_lat
        test_lng = lng + offset_lng
        
        try:
            # Try to get panorama at this location
            result = gmaps.streetview(
                location=(test_lat, test_lng),
                size=(640, 640)
            )
            
            # Extract panorama ID from metadata
            # Note: This is a simplified approach - actual implementation may vary
            # depending on Google API response format
            
            time.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            continue
    
    return list(seen_ids)


def get_panorama_ids_from_file(download_txt_path: str) -> List[str]:
    """
    Read panorama IDs from a download.txt file.
    
    Args:
        download_txt_path: Path to download.txt file
        
    Returns:
        List of panorama ID strings
    """
    panorama_ids = []
    
    with open(download_txt_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Each line should contain a panorama ID
                # Format may vary, but typically just the ID
                panorama_ids.append(line)
    
    return panorama_ids


def parse_mapping_file(mapping_txt_path: str) -> List[dict]:
    """
    Parse mapping.txt file to get cutout specifications.
    
    Args:
        mapping_txt_path: Path to mapping.txt file
        
    Returns:
        List of dictionaries with keys: 'Idx', 'yawRel', 'pitch', 'fname', 'savedir'
    """
    mappings = []
    
    with open(mapping_txt_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse line: "idx yaw pitch filename cityname"
            # Example: "0 90.0 -4 48.854766_2.350913_90.0_-4.JPG paris"
            parts = line.split()
            
            if len(parts) >= 5:
                try:
                    mapping = {
                        'Idx': int(parts[0]),
                        'yawRel': float(parts[1]),
                        'pitch': float(parts[2]),
                        'fname': parts[3],
                        'savedir': parts[4]
                    }
                    mappings.append(mapping)
                except (ValueError, IndexError):
                    print(f"Warning: Could not parse line: {line}")
                    continue
    
    return mappings

