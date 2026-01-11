# Street View Dataset Creation Tool

Python implementation of the dataset creation tool from the "What Makes Paris Look like Paris?" research project.

## Overview

This tool downloads Google Street View panoramas and extracts perspective-view images (cutouts) from them, creating a dataset suitable for visual element discovery algorithms.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

1. **Prepare input files:**
   - `download.txt`: One panorama ID per line
   - `mapping.txt`: Cutout specifications (see format below)

2. **Run the tool:**
   ```bash
   python -m streetview_dataset_tool.main \
       --download-dir /path/to/download \
       --cutout-dir /path/to/cutouts \
       --dataset-name dataset.pkl
   ```

### Command-Line Options

- `--download-dir`: Directory containing `download.txt` and `mapping.txt`
- `--cutout-dir`: Directory where cutout images will be saved
- `--dataset-name`: Output metadata filename (default: `dataset.pkl`)
- `--workers`: Number of parallel workers (default: auto-detect)
- `--max-panoramas`: Limit number of panoramas to process (for testing)

### Programmatic Usage

```python
from streetview_dataset_tool import Config, download_dataset

config = Config(
    download_dir='/path/to/download',
    cutout_dir='/path/to/cutouts',
    dataset_name='dataset.pkl'
)

download_dataset(config, num_workers=8)
```

### Individual Components

```python
from streetview_dataset_tool import download_panorama, extract_cutout

# Download a panorama
panorama = download_panorama('panorama_id_here')

# Extract a cutout
cutout = extract_cutout(panorama, yaw=90, pitch=-4)
```

## File Formats

### download.txt
One panorama ID per line:
```
abc123xyz
def456uvw
...
```

### mapping.txt
Format: `idx yaw pitch filename cityname`
```
0 90.0 -4 48.854766_2.350913_90.0_-4.JPG paris
0 270.0 -4 48.854766_2.350913_270.0_-4.JPG paris
1 90.0 -4 40.714281_-74.006181_90.0_-4.JPG nyc
...
```

## Output

- **Cutout images**: Saved in `cutout_dir/cityname/filename.JPG`
- **Metadata file**: `dataset.pkl` (Python pickle format) or can be saved as JSON

Metadata structure:
```python
[
    {
        'fullname': 'paris/48.854766_2.350913_90.0_-4.JPG',
        'city': 'paris',
        'imsize': [537, 936],  # [height, width]
        'istrain': True,
        'lat': 48.854766,
        'lng': 2.350913
    },
    ...
]
```

## Important Notes

⚠️ **Legal Notice**: Check Google Street View Terms of Service before using this tool. Bulk downloading may violate their terms. Get permission for research use.

## Performance

- **Sequential**: ~5-10 seconds per panorama
- **Parallel (8 workers)**: Can process 50+ panoramas simultaneously
- **Memory**: ~200MB per worker (for 6656×3328 panoramas)

## Troubleshooting

### Panorama download fails
- Check internet connection
- Google may rate-limit requests (tool includes retries)
- Some panorama IDs may be invalid

### Cutout extraction errors
- Ensure panorama is valid (6656×3328 pixels)
- Check that pitch angle is -4 or -28 (or modify code for other angles)

## License

Based on code by:
- Petr Gronat, Michal Havlena, and Jan Knopp
- Carl Doersch (cdoersch at cs dot cmu dot edu)

See original MATLAB code for license information.

