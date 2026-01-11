"""
Find Google Street View panorama IDs near specified cities.

This replaces the streetview_panoid.html JavaScript tool with a Python implementation.
"""

import random
import time
import os
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env from the streetview_dataset_tool directory (where this file is located)
    _current_dir = Path(__file__).parent  # streetview_dataset_tool directory
    
    # Try loading .env from streetview_dataset_tool directory first, then current working directory
    env_loaded = load_dotenv(_current_dir / '.env')  # Try streetview_dataset_tool/.env first
    if not env_loaded:
        load_dotenv('.env')  # Fallback to current working directory
except ImportError:
    # python-dotenv not installed, continue without it
    pass

def get_panorama_ids_google_api(location: Tuple[float, float], 
                                 radius: float = 0.012,
                                 max_panoramas: int = 10,
                                 api_key: Optional[str] = None) -> List[Tuple[str, float, float]]:
    """
    Get panorama IDs with GPS coordinates using Google Street View Metadata API.
    
    Note: This requires a Google API key and may have usage limits.
    
    Args:
        location: (latitude, longitude) tuple
        radius: Search radius in degrees
        max_panoramas: Maximum number of panoramas to find
        api_key: Google Maps API key (optional, can use environment variable)
        
    Returns:
        List of tuples: (panorama_id, latitude, longitude)
    """
    try:
        import requests
    except ImportError:
        raise ImportError("requests package required. Install with: pip install requests")
    
    if api_key is None:
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    if api_key is None or api_key.strip() == '':
        _current_dir = Path(__file__).parent
        raise ValueError(
            f"Google Maps API key required. "
            f"Set GOOGLE_MAPS_API_KEY environment variable, add it to a .env file in {_current_dir}, "
            f"or pass api_key parameter"
        )
    
    panorama_data = []
    seen_ids = set()
    
    lat, lng = location
    
    # Use Street View Metadata API to get panorama IDs with GPS coordinates
    for attempt in range(max_panoramas * 10):  # Try more locations than needed
        if len(panorama_data) >= max_panoramas:
            break
            
        # Random location within radius
        offset_lat = random.uniform(-radius, radius)
        offset_lng = random.uniform(-radius, radius) / abs(np.cos(np.radians(lat)))
        
        test_lat = lat + offset_lat
        test_lng = lng + offset_lng
        
        try:
            # Query Street View Metadata API
            url = "https://maps.googleapis.com/maps/api/streetview/metadata"
            params = {
                'location': f"{test_lat},{test_lng}",
                'key': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'OK' and 'pano_id' in data:
                pano_id = data['pano_id']
                
                # Skip if we've seen this panorama ID before
                if pano_id in seen_ids:
                    continue
                
                seen_ids.add(pano_id)
                
                # Get GPS coordinates from metadata
                # Location is in format "lat,lng"
                if 'location' in data:
                    pano_lat = float(data['location']['lat'])
                    pano_lng = float(data['location']['lng'])
                else:
                    # Fallback to search location if metadata doesn't have exact location
                    pano_lat = test_lat
                    pano_lng = test_lng
                
                panorama_data.append((pano_id, pano_lat, pano_lng))
                print(f"Found panorama {len(panorama_data)}/{max_panoramas}: {pano_id} at ({pano_lat:.6f}, {pano_lng:.6f})")
            
            time.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            # Continue searching if this location doesn't have Street View
            continue
    
    print(f"Found {len(panorama_data)} panoramas with GPS coordinates")
    return panorama_data


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

