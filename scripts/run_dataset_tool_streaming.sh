#!/bin/bash
# Download panoramas and save cutouts locally
# Perfect for large datasets (14,000+ cutouts)
# Uses FAST OSM building filter to ensure photos are of buildings

python3 -m dataset_tool.main \
    --download-dir ./data/test_data \
    --cutout-dir ./data/cutouts \
    --location 42.3709 -72.5190 \
    --city-name amherst \
    --radius 0.04 \
    --max-panoramas 20 \
    --workers 8 \
    --use-osm-building-filter \
    --osm-max-distance-m 50.0 \
    --osm-cache-dir ./cache \
    --delay-between-panoramas 0.1

