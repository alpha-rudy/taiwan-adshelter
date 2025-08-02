# ADS Node Clustering - Method Comparison

This document compares the three clustering algorithms implemented for Taiwan Air Defense Shelter data:

## 🔄 Clustering Methods Available

### 1. Grid-Based Clustering (`cluster_ads_nodes.py`)
- **Algorithm**: Spatial grid division
- **Parameters**: Fixed grid cell sizes (500m for Z16, 1000m for Z15)
- **Pros**: Predictable, regular distribution, good for administrative use
- **Cons**: May split natural groupings, less adaptive to density variations

### 2. HDBSCAN Clustering (`cluster_ads_hdbscan.py`)
- **Algorithm**: Hierarchical Density-Based Spatial Clustering
- **Parameters**: min_cluster_size, min_samples, cluster_selection_epsilon
- **Pros**: Hierarchical, handles varying densities, respects geographic barriers
- **Cons**: More complex parameters, requires additional libraries

### 3. DBSCAN Clustering (`cluster_ads_dbscan.py`)
- **Algorithm**: Density-Based Spatial Clustering with Noise
- **Parameters**: eps (distance threshold), min_samples
- **Pros**: Finds arbitrarily shaped clusters, excellent noise detection
- **Cons**: Sensitive to parameter tuning, less hierarchical structure

### 4. K-means Clustering (`cluster_ads_kmeans.py`)
- **Algorithm**: Centroid-based partitional clustering
- **Parameters**: k (number of clusters), automatically determined or specified
- **Pros**: Even distribution, fast, predictable results, high multi-node cluster ratio
- **Cons**: Assumes spherical clusters, sensitive to outliers

## 📊 Performance Comparison

| Method  | Z16 Clusters | Z16 Compression | Z15 Clusters | Z15 Compression | Z14 Clusters | Z14 Compression | Z13 Clusters | Z13 Compression | Z12 Clusters | Z12 Compression | Multi-node % | Characteristics |
|---------|--------------|----------------|--------------|-----------------|--------------|-----------------|--------------|-----------------|--------------|-----------------|--------------|-----------------|
| Grid    | 8,436        | 9.6:1          | 4,090        | 19.8:1          | -            | -               | -            | -               | -            | -               | 67-70%       | Regular, predictable |
| HDBSCAN | 3,004        | 27.0:1         | 1,301        | 62.3:1          | -            | -               | -            | -               | -            | -               | 24-41%       | Hierarchical, natural |
| DBSCAN  | 3,117        | 26.0:1         | 1,409        | 57.6:1          | -            | -               | -            | -               | -            | -               | 18-26%       | Density-aware, noise handling |
| K-means | 3,244        | 25.0:1         | 1,351        | 60.0:1          | 540          | 150.2:1         | 270          | 300.4:1         | 120          | 675.8:1         | 93-97%       | Balanced, even distribution |

### K-means Extended Zoom Levels

K-means is the only method that supports zoom levels below Z15, providing excellent compression ratios for national and regional views:

| Zoom Level | Clusters | Compression Ratio | Avg Cluster Size | Use Case |
|------------|----------|-------------------|------------------|----------|
| Z16        | 3,244    | 25.0:1           | 25 nodes         | City level detail |
| Z15        | 1,351    | 60.0:1           | 60 nodes         | Regional overview |
| Z14        | 540      | 150.2:1          | 150 nodes        | Provincial view |
| Z13        | 270      | 300.4:1          | 300 nodes        | Regional clusters |
| Z12        | 120      | 675.8:1          | 676 nodes        | National overview |

## 🎯 Use Case Recommendations

### For Web Maps
- **Best choice**: HDBSCAN
- **Reason**: Hierarchical structure provides smooth transitions between zoom levels

### For Mobile Apps
- **Best choice**: DBSCAN
- **Reason**: Highest compression ratios, minimal bandwidth usage

### For Administrative Use
- **Best choice**: Grid-based
- **Reason**: Predictable, regular distribution aligned with administrative boundaries

### For Emergency Response
- **Best choice**: HDBSCAN
- **Reason**: Respects geographic barriers and natural access patterns

### For Data Analysis
- **Best choice**: DBSCAN
- **Reason**: Identifies natural population centers and density patterns

## 🛠️ Usage Commands

### Generate All Clustering Methods
```bash
make clusters-all
```

### Generate Specific Methods
```bash
make clusters-grid     # Grid-based clustering
make clusters-hdbscan  # HDBSCAN clustering  
make clusters-dbscan   # DBSCAN clustering
make clusters-kmeans   # K-means clustering (Z12-Z16)
```

### Compare All Methods
```bash
make compare-clusters  # Detailed comparison with statistics
```

### Individual Scripts
```bash
# Grid-based
python3 tools/cluster_ads_nodes.py build/NPA_Taiwan_ADShelter.osm

# HDBSCAN (requires virtual environment)
source .venv/bin/activate
python3 tools/cluster_ads_hdbscan.py build/NPA_Taiwan_ADShelter.osm

# DBSCAN (requires virtual environment)  
source .venv/bin/activate
python3 tools/cluster_ads_dbscan.py build/NPA_Taiwan_ADShelter.osm

# K-means (requires virtual environment)
source .venv/bin/activate
python3 tools/cluster_ads_kmeans.py build/NPA_Taiwan_ADShelter.osm --zoom-levels 16 15 14 13 12
```

## 📁 Output Files

Each method generates files with different naming patterns:

- **Grid**: `NPA_Taiwan_ADShelter_Z16.osm`, `NPA_Taiwan_ADShelter_Z15.osm`
- **HDBSCAN**: `NPA_Taiwan_ADShelter_HDBSCAN_Z16.osm`, `NPA_Taiwan_ADShelter_HDBSCAN_Z15.osm`
- **DBSCAN**: `NPA_Taiwan_ADShelter_DBSCAN_Z16.osm`, `NPA_Taiwan_ADShelter_DBSCAN_Z15.osm`
- **K-means**: `NPA_Taiwan_ADShelter_KMEANS_Z16.osm`, `NPA_Taiwan_ADShelter_KMEANS_Z15.osm`, `NPA_Taiwan_ADShelter_KMEANS_Z14.osm`, `NPA_Taiwan_ADShelter_KMEANS_Z13.osm`, `NPA_Taiwan_ADShelter_KMEANS_Z12.osm`

## 🏷️ Cluster Tags

All methods generate consistent cluster tags:

| Tag | Description | Example |
|-----|-------------|---------|
| `amenity` | Cluster type identifier | `air_defense_shelter_cluster` |
| `cluster:algorithm` | Clustering method used | `dbscan`, `hdbscan` |
| `cluster:zoom_level` | Target zoom level | `16`, `15` |
| `cluster:node_count` | Number of original shelters | `5` |
| `cluster:total_capacity` | Sum of shelter capacities | `15000` |
| `name` | Display name format | `5/15000` |
| `cluster:primary_city` | Most common city | `臺北市` |
| `cluster:primary_authority` | Authority of largest shelter | `臺北市政府` |

## 🔧 Setup Requirements

### Basic (Grid-based only)
- Python 3.6+
- Standard library only

### Advanced (HDBSCAN/DBSCAN)
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Dependencies
- `hdbscan>=0.8.0`
- `scikit-learn>=1.0.0`
- `numpy>=1.20.0`

## 🔍 Validation

Use the validation script to check clustering quality:

```bash
python3 tools/validate_clustering.py build/NPA_Taiwan_ADShelter.osm \
  --z16-file build/NPA_Taiwan_ADShelter_HDBSCAN_Z16.osm \
  --z15-file build/NPA_Taiwan_ADShelter_HDBSCAN_Z15.osm
```

Validation checks:
- Data integrity and format compliance
- Capacity conservation (total capacity preserved)
- Geographic distribution analysis
- Clustering quality metrics
- Compression efficiency

## 📈 Algorithm Details

### Grid-Based Algorithm
1. Divide Taiwan into regular grid cells
2. Group all shelters within each cell
3. Calculate cluster center as cell centroid
4. Aggregate capacities and metadata

### HDBSCAN Algorithm
1. Build minimum spanning tree of shelter locations
2. Construct hierarchy of clusters at different densities
3. Extract stable clusters based on cluster lifetime
4. Handle noise points as individual clusters

### DBSCAN Algorithm
1. For each shelter, find all neighbors within eps distance
2. If shelter has min_samples neighbors, start a cluster
3. Recursively add density-connected shelters
4. Mark isolated shelters as noise points

## 🚀 Performance Tips

### For Large Datasets
- Use Grid-based for fastest processing
- Consider increasing eps/grid size for Z15
- Use sampling for initial parameter tuning

### For Quality Results
- HDBSCAN for most natural geographic groupings
- DBSCAN for identifying population centers
- Grid-based for consistent, predictable results

### Memory Usage
- Grid-based: ~50-100MB for Taiwan
- HDBSCAN: ~200-500MB for Taiwan  
- DBSCAN: ~100-300MB for Taiwan
