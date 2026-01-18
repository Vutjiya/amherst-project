"""
Fast OpenStreetMap building filtering using building centroids instead of full polygons.

This is much faster than querying full building geometries.
"""

import math
from typing import List, Tuple, Optional
from pathlib import Path
import pickle
import hashlib

try:
    from shapely.geometry import Point, MultiPoint
    import requests
    OSM_AVAILABLE = True
except ImportError:
    OSM_AVAILABLE = False

# Cache for building centroids
_building_cache = {}


def get_building_centroids_overpass(bounds: Tuple[float, float, float, float],
                                   cache_dir: Optional[Path] = None,
                                   use_cache: bool = True) -> Optional[List[Tuple[float, float]]]:
    """
    Query OpenStreetMap for building centroids using direct Overpass API.
    This is MUCH faster than querying full building geometries.
    
    Args:
        bounds: (north, south, east, west) bounding box in degrees
        cache_dir: Directory to cache building data (optional)
        use_cache: Whether to use cached data if available
        
    Returns:
        List of (lat, lon) tuples for building centroids, or None if query fails
    """
    if not OSM_AVAILABLE:
        raise ImportError(
            "shapely and requests are required for OSM building filtering. "
            "Install with: pip install shapely requests"
        )
    
    # Create cache key from bounds
    cache_key = f"{bounds[0]:.6f}_{bounds[1]:.6f}_{bounds[2]:.6f}_{bounds[3]:.6f}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
    
    # Check in-memory cache
    if use_cache and cache_key in _building_cache:
        print(f"Using cached building centroids ({len(_building_cache[cache_key])} buildings)")
        return _building_cache[cache_key]
    
    # Check disk cache
    if use_cache and cache_dir:
        cache_file = cache_dir / f"building_centroids_{cache_hash}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    centroids = pickle.load(f)
                print(f"Loaded {len(centroids)} building centroids from cache")
                _building_cache[cache_key] = centroids
                return centroids
            except Exception as e:
                print(f"Failed to load cache file: {e}")
    
    # Query Overpass API for building centers
    print(f"Querying OSM for building locations (fast centroid query)...")
    north, south, east, west = bounds
    print(f"  Bounds: N={north:.6f}, S={south:.6f}, E={east:.6f}, W={west:.6f}")
    
    try:
        # Overpass QL query for building centroids only
        # This returns center points, not full geometries - much faster!
        overpass_query = f"""
        [out:json][timeout:60];
        (
          way["building"]({south},{west},{north},{east});
          relation["building"]({south},{west},{north},{east});
        );
        out center;
        """
        
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        response = requests.post(
            overpass_url,
            data={'data': overpass_query},
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract centroids from response
        centroids = []
        for element in data.get('elements', []):
            if 'center' in element:
                # For ways/relations with center
                lat = element['center']['lat']
                lon = element['center']['lon']
                centroids.append((lat, lon))
            elif 'lat' in element and 'lon' in element:
                # For nodes
                lat = element['lat']
                lon = element['lon']
                centroids.append((lat, lon))
        
        print(f"Found {len(centroids)} buildings in OSM")
        
        # Cache the result
        if use_cache:
            _building_cache[cache_key] = centroids
            if cache_dir:
                cache_dir.mkdir(parents=True, exist_ok=True)
                try:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(centroids, f)
                    print(f"Cached building centroids to: {cache_file}")
                except Exception as e:
                    print(f"Failed to save cache: {e}")
        
        return centroids
        
    except Exception as e:
        print(f"Error querying OSM for buildings: {e}")
        print("Continuing without building filter...")
        return None


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great circle distance in meters between two points.
    """
    R = 6371000  # Earth radius in meters
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def is_near_building_fast(lat: float, lon: float,
                         building_centroids: List[Tuple[float, float]],
                         max_distance_m: float = 50.0) -> bool:
    """
    Check if a location is within max_distance_m of any building centroid.
    Uses simple distance calculation for speed.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        building_centroids: List of (lat, lon) tuples for building centers
        max_distance_m: Maximum distance in meters
        
    Returns:
        True if location is within max_distance_m of a building
    """
    if not building_centroids or len(building_centroids) == 0:
        return False
    
    # For speed, first do a rough filter using degree-based bounding box
    # At ~42°N latitude: 1° lat ≈ 111km, 1° lon ≈ 82km
    lat_deg_per_m = 1 / 111000
    lon_deg_per_m = 1 / (111000 * math.cos(math.radians(lat)))
    
    max_lat_diff = max_distance_m * lat_deg_per_m
    max_lon_diff = max_distance_m * lon_deg_per_m
    
    # Quick bounding box filter
    nearby_candidates = [
        (b_lat, b_lon) for b_lat, b_lon in building_centroids
        if abs(b_lat - lat) <= max_lat_diff and abs(b_lon - lon) <= max_lon_diff
    ]
    
    if not nearby_candidates:
        return False
    
    # Check actual distances for candidates
    for b_lat, b_lon in nearby_candidates:
        distance = haversine_distance_m(lat, lon, b_lat, b_lon)
        if distance <= max_distance_m:
            return True
    
    return False


def filter_locations_near_buildings_fast(candidate_locations: List[Tuple[float, float]],
                                        bounds: Tuple[float, float, float, float],
                                        max_distance_m: float = 50.0,
                                        cache_dir: Optional[Path] = None) -> List[Tuple[float, float]]:
    """
    Filter candidate locations to only those near buildings using fast centroid-based approach.
    
    Args:
        candidate_locations: List of (lat, lon) tuples
        bounds: (north, south, east, west) bounding box for OSM query
        max_distance_m: Maximum distance in meters to consider "near" a building
        cache_dir: Directory to cache building data
        
    Returns:
        Filtered list of locations near buildings
    """
    if not OSM_AVAILABLE:
        print("Warning: OSM libraries not available. Skipping building filter.")
        return candidate_locations
    
    # Get building centroids for this area
    building_centroids = get_building_centroids_overpass(bounds, cache_dir=cache_dir)
    
    if building_centroids is None or len(building_centroids) == 0:
        print("Warning: No buildings found in OSM. Skipping building filter.")
        return candidate_locations
    
    print(f"Filtering {len(candidate_locations)} candidates against {len(building_centroids)} buildings...")
    
    # Filter candidates
    filtered = []
    for lat, lon in candidate_locations:
        if is_near_building_fast(lat, lon, building_centroids, max_distance_m):
            filtered.append((lat, lon))
    
    pct = len(filtered)/len(candidate_locations)*100 if candidate_locations else 0
    print(f"Filtered to {len(filtered)} locations near buildings ({pct:.1f}%)")
    
    return filtered


def get_building_bounds_for_location(location: Tuple[float, float], 
                                    radius: float,
                                    candidate_locations: Optional[List[Tuple[float, float]]] = None) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box for OSM query based on location and radius.
    
    Args:
        location: (latitude, longitude) tuple
        radius: Search radius in degrees
        candidate_locations: Optional list of (lat, lon) candidates for tighter bounds
        
    Returns:
        (north, south, east, west) bounding box
    """
    if candidate_locations and len(candidate_locations) > 0:
        lats = [lat for lat, lon in candidate_locations]
        lons = [lon for lat, lon in candidate_locations]
        
        # Add small buffer for max_distance_m check (0.001° ≈ 111m)
        buffer = 0.001
        north = max(lats) + buffer
        south = min(lats) - buffer
        east = max(lons) + buffer
        west = min(lons) - buffer
        
        return (north, south, east, west)
    else:
        lat, lon = location
        north = lat + radius
        south = lat - radius
        east = lon + radius / abs(math.cos(math.radians(lat)))
        west = lon - radius / abs(math.cos(math.radians(lat)))
        return (north, south, east, west)
