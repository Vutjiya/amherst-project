"""
Main script for downloading panoramas and extracting cutouts.

This is the Python equivalent of streetview_download.m
"""

import argparse
from pathlib import Path
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from io import BytesIO

from .config import Config
from .download import download_panorama
from .extract import extract_cutouts_from_panorama, extract_cutout
from .metadata import create_dataset_metadata
from .panorama_finder import get_panorama_ids_google_api, parse_mapping_file
from huggingface_hub import HfApi
from PIL import Image

api = HfApi()


def generate_mapping_file(panorama_data, mapping_path, city_name='amherst', yaw_angles=[90.0, 270.0], pitch=-4.0):
    """
    Generate mapping.txt file with GPS coordinates in filenames.
    
    Args:
        panorama_data: List of tuples (panorama_id, latitude, longitude)
        mapping_path: Path to output mapping.txt file
        city_name: Name of city (used as savedir)
        yaw_angles: List of yaw angles to extract (default: [90.0, 270.0] for east/west)
        pitch: Pitch angle (default: -4.0)
    """
    mapping_path = Path(mapping_path)
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(mapping_path, 'w') as f:
        for idx, (panoid, lat, lng) in enumerate(panorama_data):
            for yaw in yaw_angles:
                # Format: lat_lng_yaw_pitch.JPG (matching expected format)
                # Example: 48.854766_2.350913_90.0_-4.JPG
                # Note: Coordinates keep dots, only separated by underscores between components
                # Round coordinates to 6 decimal places (~0.1 meter precision)
                lat_str = f"{lat:.6f}"
                lng_str = f"{lng:.6f}"
                yaw_str = f"{yaw:.1f}"
                pitch_str = f"{pitch:.1f}"
                
                filename = f"{lat_str}_{lng_str}_{yaw_str}_{pitch_str}.JPG"
                
                # Format: idx yaw pitch filename cityname
                f.write(f"{idx} {yaw} {pitch} {filename} {city_name}\n")
    
    print(f"Generated mapping.txt with {len(panorama_data)} panoramas and {len(yaw_angles)} views each")


def process_single_panorama(args):
    """
    Process a single panorama: download and extract cutouts.
    
    Args:
        args: Tuple of (panoid, pano_idx, mappings, cutout_folder)
        
    Returns:
        Tuple of (pano_idx, success, num_cutouts)
    """
    panoid, pano_idx, mappings, cutout_folder = args
    
    try:
        # Download panorama
        panorama = download_panorama(panoid)
        
        if panorama is None:
            return (pano_idx, False, 0)
        
        # Extract cutouts
        num_cutouts = extract_cutouts_from_panorama(
            panorama, pano_idx, mappings, cutout_folder
        )
        
        return (pano_idx, True, num_cutouts)
        
    except Exception as e:
        print(f"Error processing panorama {pano_idx} ({panoid}): {e}")
        return (pano_idx, False, 0)


def process_and_upload_panorama(args):
    """
    Process a single panorama and upload cutouts directly to Hugging Face (no disk storage).
    
    Args:
        args: Tuple of (panoid, pano_idx, mappings, repo_id, repo_type, city_name)
        
    Returns:
        Tuple of (pano_idx, success, num_cutouts)
    """
    panoid, pano_idx, mappings, repo_id, repo_type, city_name = args
    
    try:
        # Download panorama
        panorama = download_panorama(panoid)
        
        if panorama is None:
            return (pano_idx, False, 0)
        
        # Filter mappings for this panorama
        pano_mappings = [m for m in mappings if m['Idx'] == pano_idx]
        
        if not pano_mappings:
            return (pano_idx, True, 0)
        
        uploaded = 0
        
        # Process each cutout
        for mapping in pano_mappings:
            # Extract cutout
            yaw = mapping['yawRel']
            pitch = mapping['pitch']
            cutout = extract_cutout(panorama, yaw, pitch)
            
            # Convert to JPEG bytes in memory
            img = Image.fromarray(cutout)
            img_bytes = BytesIO()
            img.save(img_bytes, format='JPEG', quality=95)
            img_bytes.seek(0)
            
            # Construct path in repo (e.g., "amherst/42.335999_-72.584693_90.0_-4.0.JPG")
            repo_path = f"{city_name}/{mapping['fname']}"
            
            # Upload directly to Hugging Face
            api.upload_file(
                path_or_fileobj=img_bytes,
                path_in_repo=repo_path,
                repo_id=repo_id,
                repo_type=repo_type,
            )
            
            uploaded += 1
        
        return (pano_idx, True, uploaded)
        
    except Exception as e:
        print(f"Error processing panorama {pano_idx} ({panoid}): {e}")
        return (pano_idx, False, 0)


def download_dataset(config: Config, 
                    num_workers: int = None,
                    max_panoramas: int = None,
                    location: tuple = (42.3709, -72.5190),
                    radius: float = 0.06,
                    api_key: str = None,
                    city_name: str = 'amherst',
                    downtown_center: tuple = None,
                    distance_weight_power: float = 2.0,
                    use_weighted_sampling: bool = True,
                    use_osm_building_filter: bool = False,
                    osm_max_distance_m: float = 30.0,
                    osm_cache_dir: str = None,
                    upload_to_hf: bool = False,
                    hf_repo_id: str = None,
                    hf_repo_type: str = 'dataset'):
    """
    Main function to download panoramas and extract cutouts.
    
    Args:
        config: Configuration object
        num_workers: Number of parallel workers (None = auto-detect)
        max_panoramas: Maximum number of panoramas to process (None = all)
        location: (latitude, longitude) tuple for API search
        radius: Search radius in degrees for API search
        api_key: Google Maps API key (optional, can use environment variable)
        city_name: Name of the city (used for savedir)
        downtown_center: (latitude, longitude) tuple for downtown center for weighted sampling.
                         If None, uses location as downtown center.
        distance_weight_power: Power for distance weighting (default: 2.0).
                               Higher values prioritize downtown more strongly.
        use_weighted_sampling: If True, use distance-based weighted sampling (default: True).
        use_osm_building_filter: If True, filter locations to only those near buildings from OSM.
        osm_max_distance_m: Maximum distance in meters to consider "near" a building (default: 30.0).
        osm_cache_dir: Directory path to cache OSM building data (optional).
    """
    # Validate configuration (mapping.txt still needed)
    if not config.mapping_txt.exists():
        raise FileNotFoundError(f"mapping.txt not found: {config.mapping_txt}")
    
    # Get panorama IDs with GPS coordinates using Google API
    print("Fetching panorama IDs from Google Street View API...")
    if location is None:
        raise ValueError("Location (latitude, longitude) required when using Google API")
    
    # Default downtown center to location if not provided
    if downtown_center is None:
        downtown_center = location
    
    # Convert osm_cache_dir string to Path if provided
    from pathlib import Path
    osm_cache_path = Path(osm_cache_dir) if osm_cache_dir else None
    
    panorama_data = get_panorama_ids_google_api(
        location=location,
        radius=radius,
        max_panoramas=max_panoramas or 100,
        api_key=api_key,
        downtown_center=downtown_center,
        distance_weight_power=distance_weight_power,
        use_weighted_sampling=use_weighted_sampling,
        use_osm_building_filter=use_osm_building_filter,
        osm_max_distance_m=osm_max_distance_m,
        osm_cache_dir=osm_cache_path
    )
    
    if max_panoramas:
        panorama_data = panorama_data[:max_panoramas]
    
    print(f"Found {len(panorama_data)} panoramas with GPS coordinates")
    
    # Generate mapping.txt automatically with GPS coordinates in filenames
    print("Generating mapping.txt with GPS coordinates...")
    generate_mapping_file(panorama_data, config.mapping_txt, city_name=city_name)
    
    # Read mappings
    print("Reading cutout mappings...")
    mappings = parse_mapping_file(str(config.mapping_txt))
    
    # Group mappings by panorama index
    mappings_by_pano = {}
    for m in mappings:
        idx = m['Idx']
        if idx not in mappings_by_pano:
            mappings_by_pano[idx] = []
        mappings_by_pano[idx].append(m)
    
    print(f"Found {len(mappings)} cutout specifications")
    
    # Prepare arguments for parallel processing
    # Extract panorama IDs from panorama_data tuples
    panorama_ids = [pano[0] for pano in panorama_data]
    
    args_list = []
    if upload_to_hf:
        # Streaming upload mode: upload directly to Hugging Face
        if not hf_repo_id:
            raise ValueError("hf_repo_id required when upload_to_hf=True")
        print(f"Streaming mode: Uploading directly to {hf_repo_id} (no disk storage)")
        
        for idx, panoid in enumerate(panorama_ids):
            if idx in mappings_by_pano:
                args_list.append((
                    panoid,
                    idx,
                    mappings,  # Pass full mappings list
                    hf_repo_id,
                    hf_repo_type,
                    city_name
                ))
        
        process_func = process_and_upload_panorama
    else:
        # Standard mode: save to disk
        for idx, panoid in enumerate(panorama_ids):
            if idx in mappings_by_pano:
                args_list.append((
                    panoid,
                    idx,
                    mappings_by_pano[idx],
                    str(config.cutout_dir)
                ))
        
        process_func = process_single_panorama
    
    # Process panoramas
    if num_workers is None:
        num_workers = min(cpu_count(), 8)  # Limit to 8 to avoid overwhelming servers
    
    print(f"Processing {len(args_list)} panoramas with {num_workers} workers...")
    
    if num_workers == 1:
        # Sequential processing
        results = []
        for args in tqdm(args_list, desc="Processing panoramas"):
            results.append(process_func(args))
    else:
        # Parallel processing
        with Pool(processes=num_workers) as pool:
            results = list(tqdm(
                pool.imap(process_func, args_list),
                total=len(args_list),
                desc="Processing panoramas"
            ))
    
    # Summary
    successful = sum(1 for _, success, _ in results if success)
    total_cutouts = sum(num for _, _, num in results)
    failed = len(args_list) - successful
    
    print(f"\nCompleted:")
    print(f"  Successful panoramas: {successful}/{len(args_list)}")
    if failed > 0:
        print(f"  Failed panoramas: {failed} (invalid IDs or not accessible)")
    if upload_to_hf:
        print(f"  Total cutouts uploaded to Hugging Face: {total_cutouts}")
    else:
        print(f"  Total cutouts extracted: {total_cutouts}")
    
    # Create metadata file (only if not streaming)
    if not upload_to_hf:
        print("\nCreating dataset metadata...")
        create_dataset_metadata(
            str(config.cutout_dir),
            str(config.dataset_path),
            output_format='pickle'
        )
        
        print(f"\nDataset creation complete!")
        print(f"  Cutouts: {config.cutout_dir}")
        print(f"  Metadata: {config.dataset_path}")
    else:
        print(f"\nDataset upload complete!")
        print(f"  Repository: {hf_repo_id}")
        print(f"  Total cutouts: {total_cutouts}")


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Download Google Street View panoramas and extract cutouts'
    )
    parser.add_argument(
        '--download-dir',
        type=str,
        required=True,
        help='Directory containing mapping.txt'
    )
    parser.add_argument(
        '--cutout-dir',
        type=str,
        required=False,
        help='Directory where cutouts will be saved (not needed if --upload-to-hf is set)'
    )
    parser.add_argument(
        '--dataset-name',
        type=str,
        default='dataset.pkl',
        help='Output dataset metadata filename'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: auto-detect)'
    )
    parser.add_argument(
        '--max-panoramas',
        type=int,
        default=None,
        help='Maximum number of panoramas to process (default: 100)'
    )
    parser.add_argument(
        '--location',
        type=float,
        nargs=2,
        metavar=('LAT', 'LNG'),
        required=True,
        help='Location to search: latitude longitude (e.g., 48.8566 2.3522 for Paris)'
    )
    parser.add_argument(
        '--radius',
        type=float,
        default=0.012,
        help='Search radius in degrees (default: 0.012)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='Google Maps API key (default: uses GOOGLE_MAPS_API_KEY environment variable)'
    )
    parser.add_argument(
        '--city-name',
        type=str,
        default='paris',
        help='City name for savedir in mapping.txt (default: paris)'
    )
    parser.add_argument(
        '--downtown-center',
        type=float,
        nargs=2,
        metavar=('LAT', 'LNG'),
        default=None,
        help='Downtown center for weighted sampling (default: uses --location as downtown center)'
    )
    parser.add_argument(
        '--distance-weight-power',
        type=float,
        default=2.0,
        help='Power for distance weighting. Higher values prioritize downtown more (default: 2.0)'
    )
    parser.add_argument(
        '--no-weighted-sampling',
        action='store_true',
        help='Disable weighted sampling and use uniform random sampling instead'
    )
    parser.add_argument(
        '--use-osm-building-filter',
        action='store_true',
        help='Enable OSM building footprint filtering (requires osmnx, geopandas, shapely, pyproj)'
    )
    parser.add_argument(
        '--osm-max-distance-m',
        type=float,
        default=30.0,
        help='Maximum distance in meters to consider "near" a building for OSM filtering (default: 30.0)'
    )
    parser.add_argument(
        '--osm-cache-dir',
        type=str,
        default=None,
        help='Directory to cache OSM building data (optional, speeds up subsequent runs)'
    )
    parser.add_argument(
        '--upload-to-hf',
        action='store_true',
        help='Upload cutouts directly to Hugging Face (no disk storage). Requires --hf-repo-id'
    )
    parser.add_argument(
        '--hf-repo-id',
        type=str,
        default=None,
        help='Hugging Face repository ID (e.g., "username/dataset-name"). Required if --upload-to-hf is set'
    )
    parser.add_argument(
        '--hf-repo-type',
        type=str,
        default='dataset',
        choices=['dataset', 'model', 'space'],
        help='Hugging Face repository type (default: dataset)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.upload_to_hf and not args.hf_repo_id:
        parser.error("--hf-repo-id is required when --upload-to-hf is set")
    if not args.upload_to_hf and not args.cutout_dir:
        parser.error("--cutout-dir is required when not using --upload-to-hf")
    
    # Use a dummy cutout_dir if uploading to HF (won't be used)
    cutout_dir = args.cutout_dir or './dummy_cutouts'
    
    config = Config(
        download_dir=args.download_dir,
        cutout_dir=cutout_dir,
        dataset_name=args.dataset_name
    )
    
    location_tuple = (args.location[0], args.location[1])
    downtown_tuple = None
    if args.downtown_center:
        downtown_tuple = (args.downtown_center[0], args.downtown_center[1])
    
    download_dataset(
        config,
        num_workers=args.workers,
        max_panoramas=args.max_panoramas,
        location=location_tuple,
        radius=args.radius,
        api_key=args.api_key,
        city_name=args.city_name,
        downtown_center=downtown_tuple,
        distance_weight_power=args.distance_weight_power,
        use_weighted_sampling=not args.no_weighted_sampling,
        use_osm_building_filter=args.use_osm_building_filter,
        osm_max_distance_m=args.osm_max_distance_m,
        osm_cache_dir=args.osm_cache_dir,
        upload_to_hf=args.upload_to_hf,
        hf_repo_id=args.hf_repo_id,
        hf_repo_type=args.hf_repo_type
    )


if __name__ == '__main__':
    # Test upload to Hugging Face
    # repo_id = 'jonathanliu72/amherst-dataset'
    # repo_type = 'dataset'
    # folder_path = './dataset_tool/test_cutouts'
    
    # try:
    #     print(f"Uploading {folder_path} to {repo_id}...")
    #     api.upload_folder(
    #         folder_path=folder_path,
    #         repo_id=repo_id,
    #         repo_type=repo_type,
    #     )
    #     print(f"Successfully uploaded to {repo_id}!")
        
    # except Exception as e:
    #     print(f"Error uploading to Hugging Face: {e}")
    #     print("\nTroubleshooting:")
    #     print("1. Make sure you're authenticated: huggingface-cli login")
    #     print("2. Or set HUGGINGFACE_HUB_TOKEN environment variable")
    #     print("3. Check that the folder path exists and contains files")
    #     raise
    
    main()

