# Quick Test Guide

This guide shows you how to test the tool with just a few panoramas.

## Step 1: Create Test Files

First, create a small test dataset:

```bash
# Create test files (this creates placeholders - you'll need real panorama IDs)
python -m streetview_dataset_tool.test_small_dataset --create-test-files --download-dir ./test_data --max-panoramas 3
```

This creates:
- `test_data/download.txt` - List of panorama IDs (you need to replace with real IDs)
- `test_data/mapping.txt` - Cutout specifications

## Step 2: Get Real Panorama IDs

You need to replace the placeholder IDs in `download.txt` with real Google Street View panorama IDs.

**Option A: Use the panorama finder** (if available in the tool)
```python
from streetview_dataset_tool import get_panorama_ids
# Get panorama IDs for a location
```

**Option B: Manually find panorama IDs**
- Go to Google Street View
- Find a location you want to test
- The panorama ID is in the URL or can be extracted from the page

**Option C: Use a small known dataset**
If you have existing panorama IDs, just edit `test_data/download.txt`:
```
abc123xyz
def456uvw
ghi789rst
```

## Step 3: Run the Test

```bash
python -m streetview_dataset_tool.main \
    --download-dir ./test_data \
    --cutout-dir ./test_cutouts \
    --dataset-name test_dataset.pkl \
    --max-panoramas 3 \
    --workers 1
```

Or use the test script:
```bash
python -m streetview_dataset_tool.test_small_dataset \
    --download-dir ./test_data \
    --cutout-dir ./test_cutouts \
    --max-panoramas 3 \
    --workers 1
```

## Step 4: Verify Results

After running, you should see:
- `test_cutouts/` directory with extracted images
- `test_data/test_dataset.pkl` with metadata

Check the output:
```bash
ls -la test_cutouts/
ls -la test_data/test_dataset.pkl
```

## Minimal Example (Single Panorama)

For the absolute simplest test, you can use the example script:

```python
from streetview_dataset_tool import download_panorama, extract_cutout
from PIL import Image

# Download a single panorama (replace with real ID)
panoid = "YOUR_PANORAMA_ID_HERE"
panorama = download_panorama(panoid)

if panorama is not None:
    # Extract a cutout looking east
    cutout = extract_cutout(panorama, yaw=90, pitch=-4)
    Image.fromarray(cutout).save("test_cutout.jpg")
    print("Success! Check test_cutout.jpg")
else:
    print("Failed to download panorama")
```

## Troubleshooting

- **No panorama IDs?** You need real Google Street View panorama IDs. Check the README for how to find them.
- **Download fails?** Check your internet connection and Google's rate limits.
- **File not found errors?** Make sure `download.txt` and `mapping.txt` exist in the download-dir.

