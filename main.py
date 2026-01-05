"""
Main script for downloading panoramas and extracting cutouts.

This is the Python equivalent of streetview_download.m
"""

import argparse
from pathlib import Path
from tqdm import tqdm
from multiprocessing import Pool, cpu_count

from .config import Config
from .download import download_panorama
from .extract import extract_cutouts_from_panorama
from .metadata import create_dataset_metadata
from .panorama_finder import get_panorama_ids_from_file, parse_mapping_file


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


def download_dataset(config: Config, 
                    num_workers: int = None,
                    max_panoramas: int = None):
    """
    Main function to download panoramas and extract cutouts.
    
    Args:
        config: Configuration object
        num_workers: Number of parallel workers (None = auto-detect)
        max_panoramas: Maximum number of panoramas to process (None = all)
    """
    # Validate configuration
    config.validate()
    
    # Read panorama IDs
    print("Reading panorama IDs...")
    panorama_ids = get_panorama_ids_from_file(str(config.download_txt))
    
    if max_panoramas:
        panorama_ids = panorama_ids[:max_panoramas]
    
    print(f"Found {len(panorama_ids)} panoramas to process")
    
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
    args_list = []
    for idx, panoid in enumerate(panorama_ids):
        if idx in mappings_by_pano:
            args_list.append((
                panoid,
                idx,
                mappings_by_pano[idx],
                str(config.cutout_dir)
            ))
    
    # Process panoramas
    if num_workers is None:
        num_workers = min(cpu_count(), 8)  # Limit to 8 to avoid overwhelming servers
    
    print(f"Processing {len(args_list)} panoramas with {num_workers} workers...")
    
    if num_workers == 1:
        # Sequential processing
        results = []
        for args in tqdm(args_list, desc="Processing panoramas"):
            results.append(process_single_panorama(args))
    else:
        # Parallel processing
        with Pool(processes=num_workers) as pool:
            results = list(tqdm(
                pool.imap(process_single_panorama, args_list),
                total=len(args_list),
                desc="Processing panoramas"
            ))
    
    # Summary
    successful = sum(1 for _, success, _ in results if success)
    total_cutouts = sum(num for _, _, num in results)
    
    print(f"\nCompleted:")
    print(f"  Successful panoramas: {successful}/{len(args_list)}")
    print(f"  Total cutouts extracted: {total_cutouts}")
    
    # Create metadata file
    print("\nCreating dataset metadata...")
    create_dataset_metadata(
        str(config.cutout_dir),
        str(config.dataset_path),
        output_format='pickle'
    )
    
    print(f"\nDataset creation complete!")
    print(f"  Cutouts: {config.cutout_dir}")
    print(f"  Metadata: {config.dataset_path}")


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Download Google Street View panoramas and extract cutouts'
    )
    parser.add_argument(
        '--download-dir',
        type=str,
        required=True,
        help='Directory containing download.txt and mapping.txt'
    )
    parser.add_argument(
        '--cutout-dir',
        type=str,
        required=True,
        help='Directory where cutouts will be saved'
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
        help='Maximum number of panoramas to process (default: all)'
    )
    
    args = parser.parse_args()
    
    config = Config(
        download_dir=args.download_dir,
        cutout_dir=args.cutout_dir,
        dataset_name=args.dataset_name
    )
    
    download_dataset(
        config,
        num_workers=args.workers,
        max_panoramas=args.max_panoramas
    )


if __name__ == '__main__':
    main()

