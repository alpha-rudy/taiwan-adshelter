#!/usr/bin/env python3
"""
ADS (Air Defense Shelter) K-means Clustering Tool

This script uses K-means clustering to generate clustered nodes for different zoom levels 
from the original NPA_Taiwan_ADShelter.osm file. K-means creates evenly distributed 
clusters and can be configured to produce a specific number of clusters for optimal 
map display density.

Zoom Level Guidelines:
- Z17: All individual nodes (original data) - suitable for detailed view
- Z16: K-means clusters for medium density view
- Z15: Fewer K-means clusters for overview
- Z14: Significantly fewer clusters for regional view
- Z13: Very few clusters for provincial view
- Z12: Minimal clusters for national view

K-means clustering approach:
- Z16: Auto-determined k (~3000-5000 clusters) based on density
- Z15: Auto-determined k (~1000-2000 clusters) based on density
- Z14: Auto-determined k (~400-800 clusters) based on density
- Z13: Auto-determined k (~150-400 clusters) based on density
- Z12: Auto-determined k (~50-150 clusters) based on density
- Can also specify exact number of clusters
"""

import xml.etree.ElementTree as ET
import math
import argparse
import os
from typing import Dict, List, Tuple, NamedTuple

# Optional imports for K-means clustering
try:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False
    print("Warning: K-means clustering libraries not available. Install with:")
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


def determine_optimal_k(coordinates: np.ndarray, zoom_level: int, max_k: int = None) -> int:
    """
    Determine optimal number of clusters for K-means based on zoom level and data characteristics.
    
    Args:
        coordinates: Array of node coordinates
        zoom_level: Target zoom level
        max_k: Maximum number of clusters to consider
    
    Returns:
        Optimal number of clusters
    """
    n_points = len(coordinates)
    
    # Target cluster counts based on zoom level and empirical analysis
    target_clusters = {
        16: min(n_points // 25, 4000),   # ~25 nodes per cluster, max 4000 clusters
        15: min(n_points // 60, 1500),   # ~60 nodes per cluster, max 1500 clusters
        14: min(n_points // 150, 600),   # ~150 nodes per cluster, max 600 clusters
        13: min(n_points // 300, 300),   # ~300 nodes per cluster, max 300 clusters
        12: min(n_points // 600, 120)    # ~600 nodes per cluster, max 120 clusters
    }
    
    base_k = target_clusters.get(zoom_level, min(n_points // 50, 2000))
    
    if max_k:
        base_k = min(base_k, max_k)
    
    # Ensure we have at least 2 clusters and don't exceed number of points
    optimal_k = max(2, min(base_k, n_points - 1))
    
    print(f"Determined optimal k={optimal_k} for Z{zoom_level} ({n_points} points)")
    
    return optimal_k


def cluster_nodes_kmeans(nodes: List[Node], zoom_level: int, n_clusters: int = None) -> List[Cluster]:
    """
    Cluster nodes using K-means clustering.
    
    Args:
        nodes: List of nodes to cluster
        zoom_level: Target zoom level for clustering parameters
        n_clusters: Specific number of clusters (if None, will be auto-determined)
    
    Returns:
        List of clusters
    """
    if not CLUSTERING_AVAILABLE:
        raise ImportError("K-means and required libraries not available")
    
    if not nodes:
        return []
    
    print(f"Clustering with K-means for Z{zoom_level}")
    
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
    
    # Determine number of clusters
    if n_clusters is None:
        k = determine_optimal_k(coordinates, zoom_level)
    else:
        k = min(n_clusters, len(nodes) - 1)
    
    print(f"Using k={k} clusters")
    
    # Perform K-means clustering with multiple initializations for stability
    kmeans = KMeans(
        n_clusters=k,
        init='k-means++',  # Smart initialization
        n_init=10,         # Number of random initializations
        max_iter=300,      # Maximum iterations
        random_state=42    # For reproducible results
    )
    
    cluster_labels = kmeans.fit_predict(coordinates)
    
    # Calculate silhouette score for quality assessment
    if len(set(cluster_labels)) > 1:
        silhouette_avg = silhouette_score(coordinates, cluster_labels)
        print(f"Silhouette score: {silhouette_avg:.3f} (higher is better, range: -1 to 1)")
    
    # Group nodes by cluster
    clusters_dict = {}
    for i, label in enumerate(cluster_labels):
        if label not in clusters_dict:
            clusters_dict[label] = []
        clusters_dict[label].append(nodes[i])
    
    # Create cluster objects
    clusters = []
    
    for label, cluster_nodes in clusters_dict.items():
        # Calculate cluster center (average position of assigned nodes)
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
    
    print(f"Created {len(clusters)} clusters from {len(nodes)} nodes")
    
    # Calculate some statistics
    if clusters:
        cluster_sizes = [cluster.node_count for cluster in clusters]
        print(f"  - Cluster size: min={min(cluster_sizes)}, max={max(cluster_sizes)}, avg={sum(cluster_sizes)/len(cluster_sizes):.1f}")
        
        # Calculate average intra-cluster distance
        total_intra_distance = 0
        total_pairs = 0
        for cluster in clusters[:10]:  # Sample first 10 clusters for performance
            if cluster.node_count > 1:
                for i, node1 in enumerate(cluster.nodes):
                    for node2 in cluster.nodes[i+1:]:
                        dist = haversine_distance(node1.lat, node1.lon, node2.lat, node2.lon)
                        total_intra_distance += dist
                        total_pairs += 1
        
        if total_pairs > 0:
            avg_intra_distance = total_intra_distance / total_pairs
            print(f"  - Average intra-cluster distance: {avg_intra_distance:.0f}m (sample of first 10 clusters)")
    
    return clusters


def generate_cluster_tags(cluster: Cluster, zoom_level: int) -> Dict[str, str]:
    """Generate tags for a cluster node."""
    tags = {
        'amenity': 'air_defense_shelter_cluster',
        'cluster:algorithm': 'kmeans',
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
    osm_elem.set('generator', f'ads-kmeans-cluster-z{zoom_level}')
    
    # Add clustered nodes
    for i, cluster in enumerate(clusters):
        node_elem = ET.SubElement(osm_elem, 'node')
        node_elem.set('id', str(-5000 - i))  # Use negative IDs starting from -5000
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
    parser = argparse.ArgumentParser(description='Cluster ADS nodes using K-means algorithm')
    parser.add_argument('input_file', help='Input OSM file path')
    parser.add_argument('--output-dir', default='build', help='Output directory for clustered files')
    parser.add_argument('--zoom-levels', nargs='+', type=int, default=[16, 15, 14, 13, 12], 
                       help='Zoom levels to generate clusters for')
    parser.add_argument('--k-values', nargs='+', type=int,
                       help='Specific number of clusters for each zoom level')
    parser.add_argument('--auto-k', action='store_true', default=True,
                       help='Automatically determine optimal k (default: True)')
    
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
        
        # Determine number of clusters
        n_clusters = None
        if args.k_values and i < len(args.k_values):
            n_clusters = args.k_values[i]
            print(f"Using specified k={n_clusters}")
        elif not args.auto_k:
            print("Error: --k-values required when --auto-k is disabled")
            continue
        
        # Generate clusters using K-means
        clusters = cluster_nodes_kmeans(nodes, zoom_level, n_clusters)
        
        if clusters:
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(args.input_file))[0]
            output_filename = f"{base_name}_KMEANS_Z{zoom_level}.osm"
            output_filepath = os.path.join(args.output_dir, output_filename)
            
            # Write clustered OSM file
            write_clustered_osm(clusters, output_filepath, zoom_level)
            
            print(f"Z{zoom_level}: {len(clusters)} clusters")
        else:
            print(f"Z{zoom_level}: No clusters generated!")
    
    print("\nK-means clustering completed!")


if __name__ == '__main__':
    main()
