"""
Example usage of the Street View Dataset Tool

This script demonstrates how to use the tool programmatically.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from streetview_dataset_tool import (
    download_panorama,
    extract_cutout,
    create_dataset_metadata,
)
from streetview_dataset_tool.config import Config
from streetview_dataset_tool.panorama_finder import get_panorama_ids_from_file, parse_mapping_file
from PIL import Image
import numpy as np


def example_single_panorama():
    """Example: Download and extract a single panorama."""
    print("Example 1: Download and extract single panorama")
    
    # Download a panorama
    panoid = "your_panorama_id_here"
    panorama = download_panorama(panoid)
    
    if panorama is not None:
        print(f"Downloaded panorama: {panorama.shape}")
        
        # Extract a cutout looking east (90 degrees) with slight downward pitch
        cutout = extract_cutout(panorama, yaw=90, pitch=-4)
        
        # Save the cutout
        Image.fromarray(cutout).save("example_cutout.jpg")
        print("Saved cutout to example_cutout.jpg")
    else:
        print("Failed to download panorama")


def example_batch_processing():
    """Example: Process multiple panoramas."""
    print("\nExample 2: Batch processing")
    
    # Setup configuration
    config = Config(
        download_dir="./data",
        cutout_dir="./cutouts",
        dataset_name="my_dataset.pkl"
    )
    
    # Read panorama IDs
    panorama_ids = get_panorama_ids_from_file(str(config.download_txt))
    print(f"Found {len(panorama_ids)} panoramas")
    
    # Read mappings
    mappings = parse_mapping_file(str(config.mapping_txt))
    print(f"Found {len(mappings)} cutout specifications")
    
    # Process first 5 panoramas as example
    for i, panoid in enumerate(panorama_ids[:5]):
        print(f"\nProcessing panorama {i+1}/{min(5, len(panorama_ids))}: {panoid}")
        
        panorama = download_panorama(panoid)
        if panorama is None:
            continue
        
        # Find mappings for this panorama
        pano_mappings = [m for m in mappings if m['Idx'] == i]
        
        for mapping in pano_mappings:
            cutout = extract_cutout(
                panorama,
                yaw=mapping['yawRel'],
                pitch=mapping['pitch']
            )
            
            # Save cutout
            output_path = Path(config.cutout_dir) / mapping['savedir'] / mapping['fname']
            output_path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(cutout).save(output_path)
            print(f"  Saved: {output_path}")


def example_create_metadata():
    """Example: Create metadata from existing cutouts."""
    print("\nExample 3: Create metadata")
    
    metadata = create_dataset_metadata(
        cutout_dir="./cutouts",
        output_file="./dataset.pkl",
        output_format='pickle'
    )
    
    print(f"Created metadata for {len(metadata)} images")
    print(f"Sample entry: {metadata[0] if metadata else 'No images found'}")


def example_custom_extraction():
    """Example: Custom cutout extraction with different parameters."""
    print("\nExample 4: Custom extraction")
    
    # Download panorama
    panoid = "your_panorama_id_here"
    panorama = download_panorama(panoid)
    
    if panorama is not None:
        # Extract cutout with bilinear interpolation (better quality)
        from streetview_dataset_tool.extract import extract_cutout
        
        # You can modify extract.py to use bilinear_interp instead of iminterpnn
        # For now, this uses the default nearest neighbor
        
        # Extract multiple views
        views = [
            (0, -4),    # North, slight down
            (90, -4),   # East, slight down
            (180, -4),  # South, slight down
            (270, -4),  # West, slight down
        ]
        
        for yaw, pitch in views:
            cutout = extract_cutout(panorama, yaw=yaw, pitch=pitch)
            filename = f"cutout_{yaw}_{pitch}.jpg"
            Image.fromarray(cutout).save(filename)
            print(f"Saved {filename}")


if __name__ == "__main__":
    print("Street View Dataset Tool - Examples")
    print("=" * 50)
    
    # Uncomment the example you want to run:
    # example_single_panorama()
    # example_batch_processing()
    # example_create_metadata()
    # example_custom_extraction()
    
    print("\nNote: Uncomment examples in the script to run them.")
    print("Make sure to update panorama IDs and file paths first!")

