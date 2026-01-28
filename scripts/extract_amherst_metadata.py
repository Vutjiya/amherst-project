#!/usr/bin/env python3
"""
Temporary script to extract metadata and mapping.txt for Amherst cutouts only.
Saves metadata to amherst_metadata.pkl and mapping.txt to amherst_mapping.txt
in the test_data directory.
"""

import sys
from pathlib import Path
from collections import defaultdict

# Add dataset_tool to path
sys.path.insert(0, str(Path(__file__).parent))

from dataset_tool.metadata import create_dataset_metadata

def extract_amherst_metadata():
    """Extract metadata and mapping.txt for Amherst cutouts only."""
    cutout_dir = Path("./data/cutouts")
    metadata_output = Path("./data/test_data/amherst_metadata.pkl")
    mapping_output = Path("./data/test_data/amherst_mapping.txt")
    
    # Ensure output directory exists
    metadata_output.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if Amherst directory exists
    amherst_dir = cutout_dir / "amherst"
    if not amherst_dir.exists():
        print(f"Error: Amherst cutout directory not found: {amherst_dir}")
        return
    
    # Get all Amherst cutout files
    amherst_files = sorted(list(amherst_dir.glob("*.JPG")) + list(amherst_dir.glob("*.jpg")))
    print(f"Found {len(amherst_files)} Amherst cutouts")
    
    if len(amherst_files) == 0:
        print("Warning: No Amherst cutouts found!")
        return
    
    # Group cutouts by panorama (same lat/lng = same panorama)
    panorama_groups = defaultdict(list)
    
    for img_file in amherst_files:
        # Parse filename: lat_lng_yaw_pitch.JPG
        filename = img_file.stem
        parts = filename.split('_')
        
        if len(parts) < 4:
            print(f"Warning: Could not parse filename {filename}, skipping")
            continue
        
        try:
            lat = float(parts[0])
            lng = float(parts[1])
            yaw = float(parts[2])
            pitch = float(parts[3])
            
            # Use lat/lng as key to group by panorama
            panorama_key = (lat, lng)
            panorama_groups[panorama_key].append({
                'filename': img_file.name,
                'yaw': yaw,
                'pitch': pitch
            })
        except ValueError:
            print(f"Warning: Could not parse coordinates from {filename}, skipping")
            continue
    
    print(f"Found {len(panorama_groups)} unique panoramas")
    
    # Generate mapping.txt
    print(f"\nGenerating mapping.txt...")
    with open(mapping_output, 'w') as f:
        for pano_idx, (panorama_key, cutouts) in enumerate(sorted(panorama_groups.items())):
            # Sort cutouts by yaw for consistency
            cutouts_sorted = sorted(cutouts, key=lambda x: x['yaw'])
            
            for cutout in cutouts_sorted:
                # Format: idx yaw pitch filename cityname
                f.write(f"{pano_idx} {cutout['yaw']:.1f} {cutout['pitch']:.1f} {cutout['filename']} amherst\n")
    
    print(f"✓ Generated mapping.txt with {len(panorama_groups)} panoramas")
    print(f"  Saved to: {mapping_output}")
    
    # Create metadata file
    print(f"\nExtracting metadata...")
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_cutout_dir = Path(temp_dir) / "cutouts"
        temp_cutout_dir.mkdir(parents=True)
        
        # Copy only Amherst directory
        temp_amherst_dir = temp_cutout_dir / "amherst"
        shutil.copytree(amherst_dir, temp_amherst_dir)
        
        print(f"Creating metadata file...")
        print(f"Output will be saved to: {metadata_output}")
        
        # Create metadata (will only process Amherst since it's the only city)
        metadata = create_dataset_metadata(
            str(temp_cutout_dir),
            str(metadata_output),
            output_format='pickle'
        )
        
        print(f"\n✓ Successfully extracted metadata for {len(metadata)} Amherst cutouts")
        print(f"  Saved to: {metadata_output}")

if __name__ == "__main__":
    extract_amherst_metadata()

