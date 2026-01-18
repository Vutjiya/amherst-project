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
import math

# Try importing OSM building filter (optional dependency)
# Use fast version that queries centroids instead of full polygons
try:
    from .osm_building_filter_fast import (
        get_building_centroids_overpass,
        is_near_building_fast,
        get_building_bounds_for_location,
        filter_locations_near_buildings_fast,
        OSM_AVAILABLE
    )
    # Alias for compatibility
    filter_locations_near_buildings = filter_locations_near_buildings_fast
    is_near_building = is_near_building_fast
    get_building_polygons = get_building_centroids_overpass
except ImportError:
    # OSM filtering not available
    OSM_AVAILABLE = False
    get_building_centroids_overpass = None
    is_near_building_fast = None
    get_building_bounds_for_location = None
    filter_locations_near_buildings_fast = None
    filter_locations_near_buildings = None
    is_near_building = None
    get_building_polygons = None

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


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth (in degrees).
    
    Args:
        lat1, lon1: Latitude and longitude of first point (in degrees)
        lat2, lon2: Latitude and longitude of second point (in degrees)
        
    Returns:
        Distance in degrees (approximate for small distances)
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Convert back to degrees (1 degree ≈ 111 km at equator)
    return math.degrees(c)


def get_panorama_ids_google_api(location: Tuple[float, float], 
                                 radius: float = 0.012,
                                 max_panoramas: int = 10,
                                 api_key: Optional[str] = None,
                                 downtown_center: Optional[Tuple[float, float]] = None,
                                 distance_weight_power: float = 2.0,
                                 use_weighted_sampling: bool = True,
                                 use_osm_building_filter: bool = False,
                                 osm_max_distance_m: float = 30.0,
                                 osm_cache_dir: Optional[Path] = None) -> List[Tuple[str, float, float]]:
    """
    Get panorama IDs with GPS coordinates using Google Street View Metadata API.
    
    Note: This requires a Google API key and may have usage limits.
    
    Args:
        location: (latitude, longitude) tuple for search center
        radius: Search radius in degrees
        max_panoramas: Maximum number of panoramas to find
        api_key: Google Maps API key (optional, can use environment variable)
        downtown_center: (latitude, longitude) tuple for downtown center.
                         If None, uses location as downtown center.
                         Used for weighted sampling to prioritize areas closer to downtown.
        distance_weight_power: Power for distance weighting (default: 2.0).
                               Higher values prioritize downtown more strongly.
                               1.0 = linear, 2.0 = quadratic, 3.0 = cubic
        use_weighted_sampling: If True, use distance-based weighted sampling.
                               If False, use uniform random sampling (original behavior).
        use_osm_building_filter: If True, filter locations to only those near buildings (OSM).
        osm_max_distance_m: Maximum distance in meters to consider "near" a building (default: 30.0).
        osm_cache_dir: Directory to cache OSM building data (optional).
        
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
    
    # Set downtown center (default to search location if not provided)
    if downtown_center is None:
        downtown_center = location
    downtown_lat, downtown_lng = downtown_center
    
    # Generate candidate locations with weighted sampling
    # If using weighted sampling, generate more candidates and weight them
    if use_weighted_sampling:
        num_candidates = max_panoramas * 20  # Generate more candidates for better sampling
        candidate_locations = []
        candidate_weights = []
        
        print(f"Generating {num_candidates} candidate locations with distance-based weighting...")
        print(f"  Downtown center: ({downtown_lat:.6f}, {downtown_lng:.6f})")
        print(f"  Weight power: {distance_weight_power}")
        
        for _ in range(num_candidates):
            # Generate random location within radius
            offset_lat = random.uniform(-radius, radius)
            offset_lng = random.uniform(-radius, radius) / abs(np.cos(np.radians(lat)))
            
            candidate_lat = lat + offset_lat
            candidate_lng = lng + offset_lng
            
            # Calculate distance to downtown center
            distance = haversine_distance(candidate_lat, candidate_lng, 
                                         downtown_lat, downtown_lng)
            
            # Calculate weight: closer locations get higher weight
            # Weight = (max_distance - distance)^power / normalization
            # To avoid division issues, use: 1 / (distance + epsilon)^power
            max_distance = radius * 2  # Approximate max distance
            epsilon = 0.001  # Small value to avoid division by zero
            weight = 1.0 / ((distance + epsilon) ** distance_weight_power)
            
            candidate_locations.append((candidate_lat, candidate_lng))
            candidate_weights.append(weight)
        
        # Normalize weights to probabilities
        total_weight = sum(candidate_weights)
        candidate_weights = [w / total_weight for w in candidate_weights]
        
        print(f"  Generated {len(candidate_locations)} weighted candidate locations")
        
        # Apply OSM building filter if enabled
        if use_osm_building_filter and OSM_AVAILABLE and filter_locations_near_buildings:
            # Use candidate locations for tighter bounding box (faster OSM query)
            bounds = get_building_bounds_for_location(location, radius, candidate_locations)
            print(f"Applying OSM building filter (max distance: {osm_max_distance_m}m)...")
            candidate_locations_filtered = filter_locations_near_buildings(
                candidate_locations,
                bounds,
                max_distance_m=osm_max_distance_m,
                cache_dir=osm_cache_dir
            )
            
            # Update weights for filtered candidates
            if len(candidate_locations_filtered) > 0:
                # Create a set for fast lookup
                filtered_set = set(candidate_locations_filtered)
                
                # Find indices of filtered locations in original list
                filtered_indices = [i for i, loc in enumerate(candidate_locations) if loc in filtered_set]
                
                # Update candidate_locations and weights to only include filtered ones
                candidate_locations = [candidate_locations[i] for i in filtered_indices]
                candidate_weights = [candidate_weights[i] for i in filtered_indices]
                
                # Renormalize weights
                total_weight = sum(candidate_weights)
                if total_weight > 0:
                    candidate_weights = [w / total_weight for w in candidate_weights]
                
                print(f"  After OSM filtering: {len(candidate_locations)} candidate locations")
            else:
                print(f"  Warning: All candidates filtered out by OSM building filter!")
                print(f"  Continuing without OSM filter...")
                use_osm_building_filter = False
        
        # Sample locations from weighted distribution
        # We'll sample sequentially, removing candidates as we use them
        candidate_indices = list(range(len(candidate_locations)))
        sample_size = min(len(candidate_indices), max_panoramas * 10)
        
        if len(candidate_weights) > 0:
            weighted_indices = np.random.choice(
                candidate_indices,
                size=sample_size,
                replace=False,
                p=candidate_weights
            )
        else:
            # Fallback if no weights (shouldn't happen)
            weighted_indices = np.random.choice(
                candidate_indices,
                size=sample_size,
                replace=False
            )
        
        # Try each weighted candidate location
        candidate_queue = list(weighted_indices)
    else:
        # Original uniform random sampling - generate candidates on the fly
        # But we can still pre-generate candidates if OSM filtering is enabled
        if use_osm_building_filter and OSM_AVAILABLE and filter_locations_near_buildings:
            # Generate candidates first for OSM filtering
            num_candidates = max_panoramas * 20
            candidate_locations = []
            print(f"Generating {num_candidates} candidate locations for OSM filtering...")
            
            for _ in range(num_candidates):
                offset_lat = random.uniform(-radius, radius)
                offset_lng = random.uniform(-radius, radius) / abs(np.cos(np.radians(lat)))
                candidate_lat = lat + offset_lat
                candidate_lng = lng + offset_lng
                candidate_locations.append((candidate_lat, candidate_lng))
            
            # Apply OSM building filter
            # Use candidate locations for tighter bounding box (faster OSM query)
            bounds = get_building_bounds_for_location(location, radius, candidate_locations)
            print(f"Applying OSM building filter (max distance: {osm_max_distance_m}m)...")
            candidate_locations = filter_locations_near_buildings(
                candidate_locations,
                bounds,
                max_distance_m=osm_max_distance_m,
                cache_dir=osm_cache_dir
            )
            
            # Create queue from filtered candidates
            candidate_queue = list(range(len(candidate_locations)))
            print(f"  Generated {len(candidate_locations)} candidate locations near buildings")
        else:
            candidate_queue = None
    
    # Use Street View Metadata API to get panorama IDs with GPS coordinates
    max_attempts = max_panoramas * 10  # Try more locations than needed
    attempts = 0
    
    while len(panorama_data) < max_panoramas and attempts < max_attempts:
        attempts += 1
        
        # Get next candidate location
        if candidate_queue is not None and len(candidate_queue) > 0:
            # Use pre-generated candidates (either weighted or OSM-filtered)
            idx = candidate_queue.pop(0)
            test_lat, test_lng = candidate_locations[idx]
        else:
            # Generate random location on the fly (original behavior)
            offset_lat = random.uniform(-radius, radius)
            offset_lng = random.uniform(-radius, radius) / abs(np.cos(np.radians(lat)))
            test_lat = lat + offset_lat
            test_lng = lng + offset_lng
            
            # If OSM filtering is enabled but we're generating on the fly,
            # check if this location is near a building
            if use_osm_building_filter and OSM_AVAILABLE and get_building_centroids_overpass:
                bounds = get_building_bounds_for_location(location, radius, candidate_locations=None)
                building_centroids = get_building_centroids_overpass(bounds, cache_dir=osm_cache_dir)
                if building_centroids is not None and len(building_centroids) > 0:
                    if not is_near_building_fast(test_lat, test_lng, building_centroids, osm_max_distance_m):
                        continue  # Skip this location, try next
        
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
                distance = haversine_distance(pano_lat, pano_lng, downtown_lat, downtown_lng)
                print(f"Found panorama {len(panorama_data)}/{max_panoramas}: {pano_id} at ({pano_lat:.6f}, {pano_lng:.6f}) [distance to downtown: {distance:.4f}°]")
            
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

