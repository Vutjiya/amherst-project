#!/bin/bash
# Clean command to run the dataset tool module

python3 -m dataset_tool.main \
    --download-dir ./test_data \
    --cutout-dir ./test_cutouts \
    --location 42.3709 -72.5190 \
    --city-name amherst \
    --radius 0.06 \
    --max-panoramas 10 \
    --workers 1
