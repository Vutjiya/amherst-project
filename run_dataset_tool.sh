#!/bin/bash
# Clean command to run the dataset tool module
# Uses FAST OSM building filter (centroid-based, not full polygons)
# Ensures photos are of buildings, not just trees/sky in rural areas

python3 -m dataset_tool.main \
    --download-dir ./dataset_tool/test_data \
    --cutout-dir ./dataset_tool/test_cutouts \
    --location 42.3709 -72.5190 \
    --city-name amherst \
    --radius 0.04 \
    --max-panoramas 10 \
    --workers 4 \
    --use-osm-building-filter \
    --osm-max-distance-m 50.0 \
    --osm-cache-dir ./cache
