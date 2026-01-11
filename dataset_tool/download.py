"""
Download Google Street View panoramas.

Based on code by Petr Gronat, Michal Havlena, and Jan Knopp,
and edited by Carl Doersch (cdoersch at cs dot cmu dot edu)

More information:
GRONAT, P., HAVLENA , M., SIVIC , J., AND PAJDLA , T. 2011.
Building streetview datasets for place recognition and city reconstruction. 
Tech. Rep. CTU–CMP–2011–16, Czech Tech Univ.
"""

import random
import time
import os
import requests
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image

# Load environment variables from .env file (if python-dotenv is available)
try:
    from dotenv import load_dotenv
    # Load .env from the streetview_dataset_tool directory
    _current_dir = Path(__file__).parent
    load_dotenv(_current_dir / '.env')
    load_dotenv('.env')  # Fallback to current working directory
except ImportError:
    # python-dotenv not installed, continue without it
    pass


def validate_panorama_id(panoid, api_key=None):
    """
    Validate if a panorama ID is still available using the Metadata API.
    
    Args:
        panoid: Panorama ID to validate
        api_key: Google Maps API key (optional, uses env var if not provided)
        
    Returns:
        True if panorama is valid, False otherwise
    """
    import os
    
    if api_key is None:
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    if api_key is None:
        # If no API key, skip validation (assume valid)
        return True
    
    try:
        # Use Metadata API to check if panorama exists
        url = "https://maps.googleapis.com/maps/api/streetview/metadata"
        params = {
            'pano_id': panoid,
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return data.get('status') == 'OK'
        
    except Exception:
        # If validation fails, assume valid and let download attempt proceed
        return True


def fetch_tile(gzoom, i, j, panoid, server, max_retries=3, retry_delay=5):
    """
    Fetch a single tile from Google Street View servers.
    
    Args:
        gzoom: Zoom level (3 or 4)
        i: Tile X coordinate
        j: Tile Y coordinate
        panoid: Panorama ID
        server: Server number (1-3)
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries (seconds)
        
    Returns:
        PIL Image or None if failed
    """
    url = (f"https://cbks{server}.google.com/"
           f"cbk?output=tile&zoom={gzoom}&x={i}&y={j}&"
           f"cb_client=maps_sv&fover=2&onerr=3&renderer=spherical&v=4&panoid={panoid}")
    
    for trial in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            
            # Check for 400 Bad Request specifically - panorama is invalid or not accessible
            if response.status_code == 400:
                if trial == 0:  # Only print once
                    print(f"Warning: Panorama {panoid} is invalid or not accessible (400 Bad Request) - skipping")
                return None
            
            response.raise_for_status()
            
            # Load image
            img = Image.open(BytesIO(response.content))
            
            # Check if we got an error image (some invalid panoramas return placeholder images)
            if img.size == (1, 1):
                return None
            
            # Convert grayscale to RGB if needed
            if img.mode == 'L':
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            return img
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                # Invalid panorama ID - don't retry
                if trial == 0:
                    print(f"Invalid panorama ID: {panoid} (400 Bad Request)")
                return None
            elif trial < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print(f"Failed to fetch tile ({i}, {j}) after {max_retries} attempts: {e}")
                return None
        except Exception as e:
            if trial < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print(f"Failed to fetch tile ({i}, {j}) after {max_retries} attempts: {e}")
                return None
    
    return None


def download_panorama(panoid, gzoom=4, use_random_server=True, validate_first=True):
    """
    Download a complete panorama by fetching and stitching tiles.
    
    Args:
        panoid: Panorama ID string
        gzoom: Zoom level (default 4, fallback to 3)
        use_random_server: Whether to randomize server selection
        validate_first: Whether to validate panorama ID before downloading (requires API key)
        
    Returns:
        numpy array of panorama image (H, W, 3) as uint8, or None if failed
    """
    # Optionally validate panorama ID first (requires API key)
    if validate_first:
        import os
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if api_key and not validate_panorama_id(panoid, api_key):
            print(f"Skipping invalid panorama ID: {panoid}")
            return None
    
    # Randomize server selection (1-3)
    if use_random_server:
        server = random.randint(1, 3)
    else:
        server = 1
    
    # Try zoom level 4 first
    imtile = fetch_tile(gzoom, 0, 0, panoid, server)
    
    if imtile is None:
        # Try zoom level 3 as fallback
        if gzoom == 4:
            print(f"Panorama {panoid} not found at zoom level 4, trying zoom level 3...")
            gzoom = 3
            server = random.randint(1, 3) if use_random_server else 1
            imtile = fetch_tile(gzoom, 0, 0, panoid, server)
        
        if imtile is None:
            print(f"Panorama {panoid} not available (invalid ID or not accessible)")
            return None
    
    # Define tile grid based on zoom level
    if gzoom == 3:
        tilex = list(range(7))  # 0:6
        tiley = list(range(4))  # 0:3
        tilew = 512
        tileh = 512
        imw = int(6.5 * 512)
    elif gzoom == 4:
        tilex = list(range(13))  # 0:12
        tiley = list(range(7))   # 0:6
        tilew = 512
        tileh = 512
        imw = 13 * 512
    else:
        raise ValueError(f"Unsupported zoom level: {gzoom}")
    
    # Create output image
    im = np.zeros((len(tiley) * tileh, len(tilex) * tilew, 3), dtype=np.uint8)
    
    notfound = False
    
    # Download and stitch tiles
    for i in tilex:
        for j in tiley:
            if i == 0 and j == 0:
                # Already fetched
                imtile_current = imtile
            else:
                imtile_current = fetch_tile(gzoom, i, j, panoid, server)
            
            if imtile_current is not None:
                # Resize to ensure correct dimensions
                if imtile_current.size != (tilew, tileh):
                    imtile_current = imtile_current.resize((tilew, tileh), Image.LANCZOS)
                
                # Convert to numpy array
                tile_array = np.array(imtile_current)
                
                # Place in output image
                y_start = j * tileh
                y_end = (j + 1) * tileh
                x_start = i * tilew
                x_end = (i + 1) * tilew
                
                im[y_start:y_end, x_start:x_end, :] = tile_array
            else:
                notfound = True
    
    if notfound:
        print(f"Warning: Panorama {panoid} may be incomplete (some tiles missing)")
    
    # Crop to half width (panoramas are 360 degrees, we only need 180)
    im = im[:, :imw, :]
    
    # If we used zoom 3, upscale to match zoom 4 size
    if gzoom == 3:
        from PIL import Image
        im_pil = Image.fromarray(im)
        im_pil = im_pil.resize((imw, im.shape[0] * 2), Image.LANCZOS)
        im = np.array(im_pil)
    
    return im

