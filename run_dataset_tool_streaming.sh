#!/bin/bash
# Stream panoramas directly to Hugging Face (no disk storage)
# Perfect for large datasets (14,000+ cutouts)
# Uses FAST OSM building filter to ensure photos are of buildings

python3 -m dataset_tool.main \
    --download-dir ./dataset_tool/test_data \
    --location 42.3709 -72.5190 \
    --city-name amherst \
    --radius 0.04 \
    --max-panoramas 10 \
    --workers 4 \
    --use-osm-building-filter \
    --osm-max-distance-m 50.0 \
    --osm-cache-dir ./cache \
    --upload-to-hf \
    --hf-repo-id jonathanliu72/amherst-dataset \
    --hf-repo-type dataset
