"""
Create dataset metadata file from extracted cutouts.

Based on code by Carl Doersch (cdoersch at cs dot cmu dot edu)
"""

import os
import re
import json
import pickle
from pathlib import Path
from PIL import Image
import random


def create_dataset_metadata(cutout_dir, output_file, output_format='pickle'):
    """
    Scan cutout directory and create metadata file.
    
    Args:
        cutout_dir: Directory containing city subdirectories with images
        output_file: Path to output metadata file
        output_format: 'pickle' (Python) or 'json' (human-readable)
        
    Returns:
        List of image metadata dictionaries
    """
    cutout_path = Path(cutout_dir)
    
    if not cutout_path.exists():
        raise ValueError(f"Cutout directory does not exist: {cutout_dir}")
    
    imgs = []
    
    # Get all city directories
    city_dirs = sorted([d for d in cutout_path.iterdir() 
                       if d.is_dir() and not d.name.startswith('.')])
    
    for city_dir in city_dirs:
        city_name = city_dir.name
        print(f"Processing city: {city_name}")
        
        # Get all image files
        image_files = sorted([f for f in city_dir.glob('*.JPG') + city_dir.glob('*.jpg')])
        
        # Random seed based on city name for consistent train/test split
        random.seed(hash(city_name) % (2**32))
        indices = list(range(len(image_files)))
        random.shuffle(indices)
        
        # Process each image
        for idx, img_file in enumerate(image_files):
            # Parse filename: lat_lng_yaw_pitch.JPG
            filename = img_file.stem
            parts = filename.split('_')
            
            if len(parts) < 2:
                print(f"Warning: Could not parse filename {filename}, skipping")
                continue
            
            try:
                lat = float(parts[0])
                lng = float(parts[1])
            except ValueError:
                print(f"Warning: Could not parse coordinates from {filename}, skipping")
                continue
            
            # Get image size
            try:
                img = Image.open(img_file)
                imsize = list(img.size[::-1])  # [height, width]
            except Exception as e:
                print(f"Warning: Could not read image {img_file}: {e}")
                continue
            
            # Create metadata entry
            metadata = {
                'fullname': f"{city_name}/{img_file.name}",
                'city': city_name,
                'imsize': imsize,
                'istrain': (indices[idx] < len(image_files) / 2),
                'lat': lat,
                'lng': lng
            }
            
            imgs.append(metadata)
    
    # Save metadata
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if output_format == 'pickle':
        with open(output_path, 'wb') as f:
            pickle.dump(imgs, f)
        print(f"Saved metadata to {output_path} (pickle format)")
    elif output_format == 'json':
        with open(output_path, 'w') as f:
            json.dump(imgs, f, indent=2)
        print(f"Saved metadata to {output_path} (JSON format)")
    else:
        raise ValueError(f"Unknown output format: {output_format}")
    
    print(f"Total images: {len(imgs)}")
    return imgs

