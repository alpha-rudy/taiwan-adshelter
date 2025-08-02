#!/usr/bin/env python3
"""
ADS (Air Defense Shelter) DBSCAN Clustering Tool

This script uses DBSCAN (Density-Based Spatial Clustering of Applications with Noise) 
to generate clustered nodes for different zoom levels from the original 
NPA_Taiwan_ADShelter.osm file. DBSCAN is particularly good for geographic data as it 
can find arbitrarily shaped clusters and automatically identifies noise points.

Zoom Level Guidelines:
- Z17: All individual nodes (original data) - suitable for detailed view
- Z16: DBSCAN clusters for medium density view
- Z15: Larger DBSCAN clusters for overview

DBSCAN clustering approach:
- Z16: eps=400m, min_samples=3 (detailed clusters)
- Z15: eps=1000m, min_samples=5 (overview clusters)
"""

import xml.etree.ElementTree as ET
import math
import argparse
import os
from typing import Dict, List, Tuple, NamedTuple

# Optional imports for distance-based clustering
try:
    import numpy as np
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False
    print("Warning: DBSCAN clustering libraries not available. Install with:")
    print("pip install scikit-learn numpy")


class Node(NamedTuple):
    """Represents an OSM node with its attributes."""
    id: str
    lat: float
    lon: float
    tags: Dict[str, str]


class Cluster(NamedTuple):
    """Represents a cluster of nodes."""
    center_lat: float
    center_lon: float
    node_count: int
    total_capacity: int
    nodes: List[Node]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in meters.
    
    Args:
        lat1, lon1: Latitude and longitude of first point in decimal degrees
        lat2, lon2: Latitude and longitude of second point in decimal degrees
    
    Returns:
        Distance in meters
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in meters
    r = 6371000
    
    return c * r


def parse_osm_file(filepath: str) -> List[Node]:
    """Parse OSM file and extract all nodes."""
    print(f"Parsing OSM file: {filepath}")
    
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    nodes = []
    for node_elem in root.findall('node'):
        node_id = node_elem.get('id')
        lat_str = node_elem.get('lat')
        lon_str = node_elem.get('lon')
        
        if not lat_str or not lon_str:
            continue
            
        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            continue
        
        # Extract tags
        tags = {}
        for tag_elem in node_elem.findall('tag'):
            key = tag_elem.get('k')
            value = tag_elem.get('v')
            if key and value:
                tags[key] = value
        
        nodes.append(Node(node_id, lat, lon, tags))
    
    print(f"Parsed {len(nodes)} nodes")
    return nodes


def cluster_nodes_dbscan(nodes: List[Node], zoom_level: int) -> List[Cluster]:
    """
    Cluster nodes using DBSCAN (Density-Based Spatial Clustering).
    
    Args:
        nodes: List of nodes to cluster
        zoom_level: Target zoom level for clustering parameters
    
    Returns:
        List of clusters
    """
    if not CLUSTERING_AVAILABLE:
        raise ImportError("DBSCAN and required libraries not available")
    
    if not nodes:
        return []
    
    # Parameters for different zoom levels
    clustering_params = {
        16: {
            'eps_meters': 400,      # 400 meters radius
            'min_samples': 3,       # minimum 3 points to form a cluster
            'description': 'detailed clusters'
        },
        15: {
            'eps_meters': 1000,     # 1000 meters radius  
            'min_samples': 5,       # minimum 5 points to form a cluster
            'description': 'overview clusters'
        },
        14: {
            'eps_meters': 2000,     # 2000 meters radius
            'min_samples': 8,       # minimum 8 points to form a cluster
            'description': 'large overview clusters'
        }
    }
    
    params = clustering_params.get(zoom_level, clustering_params[15])
    
    print(f"Clustering with DBSCAN for Z{zoom_level}")
    print(f"Parameters: eps={params['eps_meters']}m, min_samples={params['min_samples']} ({params['description']})")
    
    # Convert coordinates to a format suitable for clustering
    # Use projected coordinates (approximate meters from center)
    center_lat = sum(node.lat for node in nodes) / len(nodes)
    center_lon = sum(node.lon for node in nodes) / len(nodes)
    
    print(f"Reference point: {center_lat:.6f}, {center_lon:.6f}")
    
    # Convert to approximate meters from center point
    coordinates = []
    for node in nodes:
        # Simple equirectangular projection (good enough for Taiwan's size)
        x = (node.lon - center_lon) * 111000 * math.cos(math.radians(center_lat))
        y = (node.lat - center_lat) * 111000
        coordinates.append([x, y])
    
    coordinates = np.array(coordinates)
    
    # Convert eps from meters to coordinate units
    eps_coordinate_units = params['eps_meters']
    
    # Perform DBSCAN clustering
    dbscan = DBSCAN(
        eps=eps_coordinate_units,
        min_samples=params['min_samples'],
        metric='euclidean'
    )
    
    cluster_labels = dbscan.fit_predict(coordinates)
    
    # Group nodes by cluster
    clusters_dict = {}
    noise_nodes = []
    
    for i, label in enumerate(cluster_labels):
        if label == -1:  # Noise point
            noise_nodes.append(nodes[i])
        else:
            if label not in clusters_dict:
                clusters_dict[label] = []
            clusters_dict[label].append(nodes[i])
    
    # Create cluster objects
    clusters = []
    
    # Handle clustered nodes
    for label, cluster_nodes in clusters_dict.items():
        if len(cluster_nodes) < params['min_samples']:
            # This shouldn't happen with DBSCAN, but safety check
            noise_nodes.extend(cluster_nodes)
            continue
            
        # Calculate cluster center (average position)
        center_lat = sum(node.lat for node in cluster_nodes) / len(cluster_nodes)
        center_lon = sum(node.lon for node in cluster_nodes) / len(cluster_nodes)
        
        # Calculate total capacity
        total_capacity = 0
        for node in cluster_nodes:
            cap_str = node.tags.get('cap', '0')
            try:
                capacity = int(cap_str)
                total_capacity += capacity
            except ValueError:
                pass
        
        cluster = Cluster(
            center_lat=center_lat,
            center_lon=center_lon,
            node_count=len(cluster_nodes),
            total_capacity=total_capacity,
            nodes=cluster_nodes
        )
        clusters.append(cluster)
    
    # Handle noise points as individual clusters
    for node in noise_nodes:
        capacity = 0
        cap_str = node.tags.get('cap', '0')
        try:
            capacity = int(cap_str)
        except ValueError:
            pass
            
        cluster = Cluster(
            center_lat=node.lat,
            center_lon=node.lon,
            node_count=1,
            total_capacity=capacity,
            nodes=[node]
        )
        clusters.append(cluster)
    
    print(f"Created {len(clusters)} clusters from {len(nodes)} nodes")
    print(f"  - {len(clusters_dict)} DBSCAN clusters")
    print(f"  - {len(noise_nodes)} noise points (individual nodes)")
    
    # Calculate some statistics
    if clusters_dict:
        cluster_sizes = [len(cluster_nodes) for cluster_nodes in clusters_dict.values()]
        print(f"  - Cluster size: min={min(cluster_sizes)}, max={max(cluster_sizes)}, avg={sum(cluster_sizes)/len(cluster_sizes):.1f}")
    
    return clusters


def generate_cluster_tags(cluster: Cluster, zoom_level: int) -> Dict[str, str]:
    """Generate tags for a cluster node."""
    tags = {
        'amenity': 'air_defense_shelter_cluster',
        'cluster:algorithm': 'dbscan',
        'cluster:zoom_level': str(zoom_level),
        'cluster:node_count': str(cluster.node_count),
        'cluster:total_capacity': str(cluster.total_capacity),
        'name': f'{cluster.node_count}/{cluster.total_capacity}'
    }
    
    # Add representative information from the largest shelter in the cluster
    if cluster.nodes:
        largest_node = max(cluster.nodes, key=lambda n: int(n.tags.get('cap', '0') or '0'))
        
        # Add some representative tags
        if '所在縣市' in largest_node.tags:
            tags['cluster:primary_city'] = largest_node.tags['所在縣市']
        if '轄管分局' in largest_node.tags:
            tags['cluster:primary_authority'] = largest_node.tags['轄管分局']
    
    return tags


def write_clustered_osm(clusters: List[Cluster], output_filepath: str, zoom_level: int):
    """Write clusters to an OSM file."""
    print(f"Writing {len(clusters)} clusters to: {output_filepath}")
    
    # Create OSM root element
    osm_elem = ET.Element('osm')
    osm_elem.set('version', '0.6')
    osm_elem.set('generator', f'ads-dbscan-cluster-z{zoom_level}')
    
    # Add clustered nodes
    for i, cluster in enumerate(clusters):
        node_elem = ET.SubElement(osm_elem, 'node')
        node_elem.set('id', str(-4000 - i))  # Use negative IDs starting from -4000
        node_elem.set('visible', 'true')
        node_elem.set('lat', f"{cluster.center_lat:.7f}")
        node_elem.set('lon', f"{cluster.center_lon:.7f}")
        
        # Add tags
        tags = generate_cluster_tags(cluster, zoom_level)
        for key, value in tags.items():
            tag_elem = ET.SubElement(node_elem, 'tag')
            tag_elem.set('k', key)
            tag_elem.set('v', value)
    
    # Write to file
    tree = ET.ElementTree(osm_elem)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_filepath, encoding='utf-8', xml_declaration=True)
    print(f"Successfully wrote clustered OSM file: {output_filepath}")


def main():
    parser = argparse.ArgumentParser(description='Cluster ADS nodes using DBSCAN algorithm')
    parser.add_argument('input_file', help='Input OSM file path')
    parser.add_argument('--output-dir', default='build', help='Output directory for clustered files')
    parser.add_argument('--zoom-levels', nargs='+', type=int, default=[16, 15], 
                       help='Zoom levels to generate clusters for')
    parser.add_argument('--eps-values', nargs='+', type=float,
                       help='Custom eps values in meters for each zoom level')
    parser.add_argument('--min-samples', nargs='+', type=int,
                       help='Custom min_samples values for each zoom level')
    
    args = parser.parse_args()
    
    if not CLUSTERING_AVAILABLE:
        print("Error: Required clustering libraries not available.")
        print("Please install with: pip install scikit-learn numpy")
        return
    
    # Parse input file
    nodes = parse_osm_file(args.input_file)
    if not nodes:
        print("No nodes found in input file!")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate clusters for each zoom level
    for i, zoom_level in enumerate(args.zoom_levels):
        print(f"\n--- Processing Zoom Level {zoom_level} ---")
        
        # Override default parameters if provided
        if args.eps_values and i < len(args.eps_values):
            # Modify the clustering function to accept custom parameters
            # For now, we'll create clusters with default parameters
            pass
        
        # Generate clusters using DBSCAN
        clusters = cluster_nodes_dbscan(nodes, zoom_level)
        
        if clusters:
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(args.input_file))[0]
            output_filename = f"{base_name}_DBSCAN_Z{zoom_level}.osm"
            output_filepath = os.path.join(args.output_dir, output_filename)
            
            # Write clustered OSM file
            write_clustered_osm(clusters, output_filepath, zoom_level)
            
            print(f"Z{zoom_level}: {len(clusters)} clusters")
        else:
            print(f"Z{zoom_level}: No clusters generated!")
    
    print("\nDBSCAN clustering completed!")


if __name__ == '__main__':
    main()
