#!/usr/bin/env python3
"""
Extract metadata and mapping.txt for a specific town's cutouts.
Usage: python3 extract_town_metadata.py <town_name>
"""

import sys
from pathlib import Path
from collections import defaultdict

# Add dataset_tool to path
sys.path.insert(0, str(Path(__file__).parent))

from dataset_tool.metadata import create_dataset_metadata

def extract_town_metadata(town_name):
    """Extract metadata and mapping.txt for a specific town's cutouts."""
    cutout_dir = Path("./data/cutouts")
    town_cutout_dir_name = f"{town_name}_cutouts"
    metadata_output = Path(f"./data/test_data/{town_name}_metadata.pkl")
    mapping_output = Path(f"./data/test_data/{town_name}_mapping.txt")
    
    # Ensure output directory exists
    metadata_output.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if town directory exists
    town_dir = cutout_dir / town_cutout_dir_name
    if not town_dir.exists():
        print(f"Error: Town cutout directory not found: {town_dir}")
        return False
    
    # Get all cutout files
    town_files = sorted(list(town_dir.glob("*.JPG")) + list(town_dir.glob("*.jpg")))
    print(f"Found {len(town_files)} cutouts for {town_name}")
    
    if len(town_files) == 0:
        print(f"Warning: No cutouts found for {town_name}!")
        return False
    
    # Group cutouts by panorama (same lat/lng = same panorama)
    panorama_groups = defaultdict(list)
    
    for img_file in town_files:
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
    print(f"Generating {town_name}_mapping.txt...")
    with open(mapping_output, 'w') as f:
        for pano_idx, (panorama_key, cutouts) in enumerate(sorted(panorama_groups.items())):
            # Sort cutouts by yaw for consistency
            cutouts_sorted = sorted(cutouts, key=lambda x: x['yaw'])
            
            for cutout in cutouts_sorted:
                # Format: idx yaw pitch filename cityname
                # Use town_cutout_dir_name as cityname to match directory structure
                f.write(f"{pano_idx} {cutout['yaw']:.1f} {cutout['pitch']:.1f} {cutout['filename']} {town_cutout_dir_name}\n")
    
    print(f"✓ Generated mapping.txt with {len(panorama_groups)} panoramas")
    print(f"  Saved to: {mapping_output}")
    
    # Create metadata file
    print(f"Creating metadata file...")
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_cutout_dir = Path(temp_dir) / "cutouts"
        temp_cutout_dir.mkdir(parents=True)
        
        # Copy only this town's directory
        temp_town_dir = temp_cutout_dir / town_cutout_dir_name
        shutil.copytree(town_dir, temp_town_dir)
        
        print(f"Output will be saved to: {metadata_output}")
        
        # Create metadata (will only process this town since it's the only city)
        metadata = create_dataset_metadata(
            str(temp_cutout_dir),
            str(metadata_output),
            output_format='pickle'
        )
        
        print(f"✓ Successfully extracted metadata for {len(metadata)} cutouts")
        print(f"  Saved to: {metadata_output}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_town_metadata.py <town_name>")
        sys.exit(1)
    
    town_name = sys.argv[1]
    success = extract_town_metadata(town_name)
    sys.exit(0 if success else 1)

