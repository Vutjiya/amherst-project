#!/bin/bash
# Batch process all 8 negative set towns
# Each town will get ~875 cutouts (~438 panoramas)
# Uses same settings as Amherst collection
# Creates separate directories and metadata files for each town

# Town coordinates (latitude, longitude)
# Format: "town_name:lat:lng:downtown_lat:downtown_lng"
declare -a TOWNS=(
    "hanover:43.7022:-72.2892:43.7022:-72.2892"
    "newhaven:41.3083:-72.9279:41.3083:-72.9279"
    "cambridge:42.3736:-71.1097:42.3736:-71.1097"
    "princeton:40.3573:-74.6672:40.3573:-74.6672"
    "annapolis:38.9784:-76.4922:38.9784:-76.4922"
    "charlottesville:38.0293:-78.4787:38.0293:-78.4787"
    "annarbor:42.2808:-83.7430:42.2808:-83.7430"
    "oberlin:41.2939:-82.2174:41.2939:-82.2174"
)

# Parameters
MAX_PANORAMAS=500  # ~875 cutouts (438 * 2)
WORKERS=8
RADIUS=0.04
OSM_MAX_DISTANCE=50.0
DELAY=0.1

# Base directories (relative to project root; assume script is run from project root)
DOWNLOAD_DIR="./data/test_data"
CUTOUT_DIR="./data/cutouts"
CACHE_DIR="./cache"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Processing 8 Negative Set Towns"
echo "Target: ~875 cutouts per town (~438 panoramas)"
echo "Each town will get its own directory and metadata files"
echo "=========================================="
echo ""

# Process each town
for town_info in "${TOWNS[@]}"; do
    IFS=':' read -r town_name lat lng downtown_lat downtown_lng <<< "$town_info"
    
    # Use town_name_cutouts as the city-name to create separate directories
    town_cutout_dir="${town_name}_cutouts"
    
    echo "=========================================="
    echo "Processing: $town_name"
    echo "Location: $lat, $lng"
    echo "Cutout directory: $CUTOUT_DIR/$town_cutout_dir"
    echo "=========================================="
    
    # Process panoramas and save cutouts (skip metadata creation - we'll do it separately)
    python3 -m dataset_tool.main \
        --download-dir "$DOWNLOAD_DIR" \
        --cutout-dir "$CUTOUT_DIR" \
        --location "$lat" "$lng" \
        --city-name "$town_cutout_dir" \
        --radius "$RADIUS" \
        --max-panoramas "$MAX_PANORAMAS" \
        --workers "$WORKERS" \
        --use-osm-building-filter \
        --osm-max-distance-m "$OSM_MAX_DISTANCE" \
        --osm-cache-dir "$CACHE_DIR" \
        --delay-between-panoramas "$DELAY" \
        --skip-metadata
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully processed $town_name cutouts"
        
        # Extract metadata and mapping for this town only
        echo "Extracting metadata and mapping for $town_name..."
        python3 "$SCRIPT_DIR/extract_town_metadata.py" "$town_name"
        
        if [ $? -eq 0 ]; then
            echo "✓ Successfully created metadata and mapping for $town_name"
        else
            echo "✗ Error creating metadata/mapping for $town_name"
        fi
    else
        echo "✗ Error processing $town_name - continuing with next town"
    fi
    
    echo ""
    echo "Waiting 5 seconds before next town..."
    sleep 5
    echo ""
done

echo "=========================================="
echo "All towns processed!"
echo ""
echo "Results:"
echo "  Cutout directories: $CUTOUT_DIR/*_cutouts/"
echo "  Metadata files: $DOWNLOAD_DIR/*_metadata.pkl"
echo "  Mapping files: $DOWNLOAD_DIR/*_mapping.txt"
echo "=========================================="

