"""
Quick test script to run the tool on a small dataset.

This script helps you test the tool with just a few panoramas.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from streetview_dataset_tool.config import Config
from streetview_dataset_tool.main import download_dataset


def create_test_files(download_dir: str, num_panoramas: int = 3):
    """
    Create minimal test files for download.txt and mapping.txt.
    
    You'll need to replace the panorama IDs with real ones from Google Street View.
    """
    download_dir = Path(download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a minimal download.txt with placeholder IDs
    download_txt = download_dir / 'download.txt'
    with open(download_txt, 'w') as f:
        for i in range(num_panoramas):
            # Replace these with real panorama IDs!
            # You can find panorama IDs using Google Street View or the panorama finder
            f.write(f"PANORAMA_ID_{i+1}\n")
    
    print(f"Created {download_txt}")
    print("⚠️  IMPORTANT: Replace the placeholder IDs with real panorama IDs!")
    
    # Create a minimal mapping.txt
    # Format: idx yaw pitch filename cityname
    mapping_txt = download_dir / 'mapping.txt'
    with open(mapping_txt, 'w') as f:
        for i in range(num_panoramas):
            # Create 2 cutouts per panorama (east and west views)
            f.write(f"{i} 90.0 -4 test_{i}_east.JPG test_city\n")
            f.write(f"{i} 270.0 -4 test_{i}_west.JPG test_city\n")
    
    print(f"Created {mapping_txt}")
    print("\nTest files created! Now:")
    print("1. Edit download.txt and replace PANORAMA_ID_* with real panorama IDs")
    print("2. Run: python -m streetview_dataset_tool.main --download-dir <dir> --cutout-dir <dir> --max-panoramas 3")


def main():
    parser = argparse.ArgumentParser(
        description='Test the Street View dataset tool with a small dataset'
    )
    parser.add_argument(
        '--create-test-files',
        action='store_true',
        help='Create sample download.txt and mapping.txt files'
    )
    parser.add_argument(
        '--download-dir',
        type=str,
        default='./test_data',
        help='Directory containing download.txt and mapping.txt'
    )
    parser.add_argument(
        '--cutout-dir',
        type=str,
        default='./test_cutouts',
        help='Directory where cutouts will be saved'
    )
    parser.add_argument(
        '--dataset-name',
        type=str,
        default='test_dataset.pkl',
        help='Output dataset metadata filename'
    )
    parser.add_argument(
        '--max-panoramas',
        type=int,
        default=3,
        help='Maximum number of panoramas to process (default: 3)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of parallel workers (default: 1 for testing)'
    )
    
    args = parser.parse_args()
    
    if args.create_test_files:
        create_test_files(args.download_dir, args.max_panoramas)
        return
    
    # Run the tool
    config = Config(
        download_dir=args.download_dir,
        cutout_dir=args.cutout_dir,
        dataset_name=args.dataset_name
    )
    
    print("Running tool on small test dataset...")
    print(f"  Download dir: {config.download_dir}")
    print(f"  Cutout dir: {config.cutout_dir}")
    print(f"  Max panoramas: {args.max_panoramas}")
    print(f"  Workers: {args.workers}")
    print()
    
    download_dataset(
        config,
        num_workers=args.workers,
        max_panoramas=args.max_panoramas
    )


if __name__ == '__main__':
    main()

