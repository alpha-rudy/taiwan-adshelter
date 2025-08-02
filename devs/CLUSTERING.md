# ADS Node Clustering Tool

This tool generates clustered nodes for different zoom levels from the Taiwan Air Defense Shelter (ADS) OSM data using HDBSCAN (Hierarchical Density-Based Spatial Clustering). It provides appropriate node density for different map zoom levels while preserving important shelter information through distance-based clustering.

## Overview

The original `NPA_Taiwan_ADShelter.osm` contains 81,101 individual air defense shelter nodes, which is perfect for zoom level 17 (Z17) but too dense for lower zoom levels. This tool creates clustered versions using HDBSCAN suitable for:

- **Z16**: 3,004 clusters (27.0:1 compression) - Natural clustering with 300m proximity
- **Z15**: 1,301 clusters (62.3:1 compression) - Larger clusters with 800m proximity

## Features

- **HDBSCAN clustering**: Uses distance-based density clustering for natural groupings
- **Adaptive clustering**: Handles varying density areas intelligently
- **Noise detection**: Identifies and preserves isolated important shelters
- **Capacity aggregation**: Combines the capacity of all shelters in each cluster
- **Smart tagging**: Preserves important metadata about the cluster
- **OSM-compatible output**: Generates valid OSM XML files

## Usage

### Basic Usage

Generate default Z16 and Z15 clusters:
```bash
python3 tools/cluster_ads_nodes.py build/NPA_Taiwan_ADShelter.osm
```

### Advanced Usage

Custom zoom levels:
```bash
python3 tools/cluster_ads_nodes.py build/NPA_Taiwan_ADShelter.osm --zoom-levels 16 15 14
```

Custom grid sizes:
```bash
python3 tools/cluster_ads_nodes.py build/NPA_Taiwan_ADShelter.osm --zoom-levels 16 15 --grid-sizes 300 800
```

Custom output directory:
```bash
python3 tools/cluster_ads_nodes.py build/NPA_Taiwan_ADShelter.osm --output-dir output/
```

### Using Makefile

Generate clusters as part of the build process:
```bash
make clusters
```

Or include in the full build:
```bash
make all
```

## Grid Size Recommendations

| Zoom Level | Grid Size | Description | Node Count |
|------------|-----------|-------------|------------|
| Z17 | Original | Individual shelters | 81,101 |
| Z16 | 300-600m | Detailed clusters | ~8,000-12,000 |
| Z15 | 800-1200m | Medium clusters | ~3,000-6,000 |
| Z14 | 1500-2500m | Large clusters | ~1,500-3,000 |
| Z13 | 3000-5000m | Very large clusters | ~500-1,500 |

## Cluster Tags

Each cluster node includes the following tags:

| Tag | Description | Example |
|-----|-------------|---------|
| `amenity` | Set to `air_defense_shelter_cluster` | `air_defense_shelter_cluster` |
| `cluster:zoom_level` | Target zoom level | `16` |
| `cluster:node_count` | Number of original nodes | `5` |
| `cluster:total_capacity` | Sum of all shelter capacities | `15000` |
| `name` | Descriptive cluster name | `ADS Cluster (5 shelters, 15000 capacity)` |
| `cluster:primary_city` | Most represented city | `臺北市` |
| `cluster:primary_authority` | Authority of largest shelter | `臺北市政府` |

## Files Generated

- `NPA_Taiwan_ADShelter_Z16.osm` - Z16 clustered data (500m grid)
- `NPA_Taiwan_ADShelter_Z15.osm` - Z15 clustered data (1000m grid)

## Algorithm Details

### Grid-Based Clustering

1. **Grid Cell Calculation**: The algorithm divides Taiwan into a grid based on the specified grid size in meters
2. **Node Assignment**: Each shelter is assigned to a grid cell based on its coordinates
3. **Cluster Creation**: All shelters in the same grid cell form a cluster
4. **Center Calculation**: The cluster center is the average position of all shelters in the grid cell
5. **Aggregation**: Capacity and other attributes are aggregated for the entire cluster

### Coordinate System

- Uses Taiwan's approximate center latitude (24.33°N) as reference for longitude distance calculations
- Converts between geographic coordinates (lat/lon) and metric distances
- Accounts for latitude-dependent longitude scaling

## Performance

- Processing time: ~10-30 seconds for 81K nodes
- Memory usage: ~100-200MB
- Output file sizes:
  - Z16: ~5MB (8,436 clusters)
  - Z15: ~2.5MB (4,090 clusters)

## Map Display Recommendations

### Zoom Level Usage

- **Z17+**: Use original individual shelter data
- **Z16**: Use Z16 clustered data (shows neighborhood-level detail)
- **Z15**: Use Z15 clustered data (shows district-level overview)
- **Z14-**: Consider generating additional cluster levels for city/county overview

### Styling Suggestions

- Use different symbols/colors for clusters vs individual shelters
- Scale cluster symbols based on capacity or node count
- Show cluster information in popup/tooltip
- Consider heat map visualization for lower zoom levels

## Troubleshooting

### Common Issues

1. **Memory errors**: Reduce the number of nodes or increase system memory
2. **Grid too small**: Results in too many clusters; increase grid size
3. **Grid too large**: Results in too few clusters; decrease grid size
4. **Coordinate errors**: Check input data for invalid lat/lon values

### Validation

Check cluster file integrity:
```bash
# Count clusters
grep -c "^<node" build/NPA_Taiwan_ADShelter_Z16.osm

# Validate XML
xmllint --noout build/NPA_Taiwan_ADShelter_Z16.osm
```

## Technical Notes

- Uses Python 3.6+ standard library (no external dependencies)
- Generates negative node IDs starting from -2000 to avoid conflicts
- Preserves XML formatting and encoding
- Thread-safe and suitable for automation

## Future Enhancements

Potential improvements:
- K-means clustering for more uniform cluster sizes
- Population-weighted clustering
- Dynamic grid sizing based on shelter density
- Support for other output formats (GeoJSON, etc.)
- Interactive cluster exploration tools
